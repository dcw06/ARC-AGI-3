"""Close repository Python imports without executing them, then copy only pins.

Entrypoints include executable scripts and explicit local dynamic/subprocess
targets. Literal imports, including imports inside functions, are followed.
Non-Python entrypoints are retained as opaque, hash-bound data. Verification in
a full checkout permits unrelated files; execution packages should use the
fresh, closed tree returned by ``write_source_payload`` instead of that checkout.
"""
import ast
import hashlib
from importlib.machinery import all_suffixes
from pathlib import Path, PurePosixPath
import stat


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _linked(path):
    try:
        info = path.lstat()
    except OSError as exc:
        raise ValueError('missing source/artifact path: '+str(path)) from exc
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0))


def safe_member(root, name):
    """Return an existing regular file under root; reject native link escapes."""
    root = Path(root)
    if (type(name) is not str or not name or '\\' in name or ':' in name or
            PurePosixPath(name).is_absolute() or PurePosixPath(name).as_posix() != name or
            any(part in ('', '.', '..') for part in name.split('/'))):
        raise ValueError('unsafe source/artifact member: '+str(name))
    if _linked(root):
        raise ValueError('linked source/artifact root')
    path = root
    for part in name.split('/'):
        path = path / part
        if _linked(path):
            raise ValueError('linked source/artifact member: '+name)
    if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('source/artifact member escapes root: '+name)
    return path


def _exists(root, name):
    path = root / name
    # lexists equivalent: dangling links must be rejected, not treated as absent.
    if path.exists() or path.is_symlink():
        return safe_member(root, name)
    return None


def _module_files(root, parts):
    """Conservative local candidates for Python's root-relative module lookup."""
    if not parts or any(not part.isidentifier() for part in parts):
        return set()
    found = set()
    for index in range(len(parts)):
        base = '/'.join(parts[:index+1])
        package = base+'/__init__.py'
        module = base+'.py'
        for suffix in set(all_suffixes()) - {'.py'}:
            for candidate in (base+suffix, base+'/__init__'+suffix):
                if _exists(root, candidate) is not None:
                    raise ValueError('non-source local import candidate: '+candidate)
        package_path = _exists(root, package)
        module_path = _exists(root, module)
        if package_path is not None:
            found.add(package)
        if module_path is not None:
            found.add(module)
        if module_path is not None and package_path is None:
            # In ``from module import attribute`` the final component is often
            # an attribute, not a submodule. Retain the module candidate and
            # stop here; a newly added package shadow still changes inventory.
            break
        # Namespace parents can be directories without an initializer.
        directory = root / base
        if directory.exists() and _linked(directory):
            raise ValueError('linked import directory: '+base)
        if not directory.is_dir():
            break
    return found


def _imports(tree, package):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split('.')
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                if node.level > len(package):
                    raise ValueError('relative import escapes its package')
                base = package[:len(package)-node.level+1]
            else:
                base = []
            base = base + (node.module.split('.') if node.module else [])
            yield base
            for alias in node.names:
                if alias.name != '*':
                    yield base + alias.name.split('.')
        elif isinstance(node, ast.Call) and node.args:
            function = node.func
            literal_import = (isinstance(function, ast.Name) and function.id == '__import__' or
                              isinstance(function, ast.Attribute) and function.attr == 'import_module')
            if literal_import and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                name = node.args[0].value
                if not name.startswith('.'):
                    yield name.split('.')


def source_inventory(root, entrypoints):
    """Hash explicit files plus their local source imports and package parents.

    No repository code is imported. Nonliteral dynamic local module names and
    subprocess entrypoints must be supplied explicitly by the package builder.
    """
    root = Path(root)
    pending, result = set(entrypoints), {}
    while pending:
        name = min(pending)
        pending.remove(name)
        if name in result:
            continue
        path = safe_member(root, name)
        raw = path.read_bytes()
        result[name] = _hash(raw)
        if path.suffix != '.py':
            continue
        parts = name.split('/')
        package = parts[:-1]
        for depth in range(1, len(package)+1):
            initializer = '/'.join(package[:depth])+'/__init__.py'
            if _exists(root, initializer) is not None:
                pending.add(initializer)
        try:
            tree = ast.parse(raw, filename=name)
        except (SyntaxError, UnicodeError) as exc:
            raise ValueError('cannot inspect source imports: '+name) from exc
        for module in _imports(tree, package):
            pending.update(_module_files(root, module))
    return dict(sorted(result.items()))


def verify_source_inventory(root, expected, *, closed=False):
    """Reject source drift and new import candidates under the same trusted pin."""
    if type(expected) is not dict or not expected:
        raise ValueError('empty or invalid approved source inventory')
    actual = source_inventory(root, expected)
    if actual != expected:
        changed = sorted(name for name in set(actual) | set(expected) if actual.get(name) != expected.get(name))
        raise ValueError('approved source closure changed: '+', '.join(changed))
    if closed:
        files = {p.relative_to(root).as_posix() for p in Path(root).rglob('*') if p.is_file() or p.is_symlink()}
        if files != set(expected):
            raise ValueError('unexpected files in closed source payload')
    return expected


def source_payload(root, expected):
    """Return only verified approved bytes, safe for a fresh source archive."""
    verify_source_inventory(root, expected)
    payload = {name: safe_member(root, name).read_bytes() for name in sorted(expected)}
    if any(_hash(raw) != expected[name] for name, raw in payload.items()):
        raise ValueError('source changed while reading approved payload')
    return payload


def write_source_payload(root, expected, destination):
    """Extract into a new directory; refuse overlays and unapproved members."""
    payload = source_payload(root, expected)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    for name, raw in payload.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    verify_source_inventory(destination, expected, closed=True)
    return destination
