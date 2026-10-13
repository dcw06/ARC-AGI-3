"""Offline bindings for the benchmark's project import closure and retained inputs.

Resolve static imports (including imports inside functions) without executing
modules. Standard-library/site packages are not project sources. Existing local
package initializers are included; all other local imports recurse. Dynamic
project imports would need an explicit seed before being introduced here.
"""
import ast
import hashlib
import json
from pathlib import Path

REFERENCE_AUDIT = 'reports/ws3_questionnaire_token_audit.json'
ARCHIVE_LOCKS = ('reports/action_effect_history_v1_archive.json',
                 'reports/perception_stage_b_r8_archive.json')


def _inside(root, relative):
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('unsafe dependency path: ' + str(relative))
    result = root / path
    if not result.resolve().is_relative_to(root.resolve()):
        raise ValueError('dependency escapes checkout: ' + str(relative))
    return result


def source_paths(root):
    root = Path(root)
    pending = list((root / 'research/conditional_transfer_v1').glob('*.py'))
    if not pending:
        raise ValueError('benchmark source package is missing')
    found = set()

    def add(module):
        if not module:
            return
        parts = module.split('.')
        for length in range(1, len(parts) + 1):
            initializer = _inside(root, Path(*parts[:length]) / '__init__.py')
            if initializer.is_file():
                pending.append(initializer)
        source = _inside(root, Path(*parts).with_suffix('.py'))
        if source.is_file():
            pending.append(source)

    while pending:
        path = pending.pop()
        relative = path.relative_to(root)
        _inside(root, relative)
        if relative in found:
            continue
        found.add(relative)
        parts = list(relative.with_suffix('').parts)
        package = parts[:-1]  # both module.py and package/__init__.py
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'), filename=str(relative))):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                base = package[:len(package) - node.level + 1] if node.level else []
                if node.module:
                    base += node.module.split('.')
                module = '.'.join(base)
                add(module)
                for alias in node.names:
                    if alias.name != '*':
                        add('.'.join(base + [alias.name]))
    return sorted(path.as_posix() for path in found)


def source_hashes(root):
    root = Path(root)
    return {name: hashlib.sha256(_inside(root, name).read_bytes()).hexdigest()
            for name in source_paths(root)}


def input_hashes(root):
    root = Path(root)
    names = {REFERENCE_AUDIT, 'reports/conditional_transfer_v1/protocol.md', *ARCHIVE_LOCKS}
    for name in ARCHIVE_LOCKS:
        lock = json.loads(_inside(root, name).read_bytes())
        archive = lock['archive']
        if not isinstance(archive, str):
            raise ValueError('archive dependency must have a relative path')
        _inside(root, archive)
        names.add(archive)
    return {name: hashlib.sha256(_inside(root, name).read_bytes()).hexdigest()
            for name in sorted(names)}


def verify_bindings(package, root):
    """Refuse changed or omitted bindings even if current fixture outputs match."""
    package = Path(package)
    for name, expected in (('source_hashes.json', source_hashes(root)),
                           ('input_hashes.json', input_hashes(root))):
        recorded = json.loads((package / name).read_bytes())
        if recorded != expected:
            raise ValueError('dependency bindings differ: ' + name)


def verify_tokenizer_reference(tokenizer, root, checker):
    root = Path(root)
    path = _inside(root, REFERENCE_AUDIT)
    raw = path.read_bytes()
    rows = json.loads(raw)['requests']
    ids = [row['probe_id'] for row in rows]
    if not ids or any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('tokenizer reference audit has missing or duplicate probes')
    checked, mismatches = checker(tokenizer)
    if type(checked) is not int or checked != len(ids) or not isinstance(mismatches, list) or mismatches:
        raise ValueError('tokenizer reference verification failed or has incomplete coverage')
    if path.read_bytes() != raw:
        raise ValueError('tokenizer reference audit changed during verification')
    return {'verified': True, 'checked': checked, 'expected': len(ids), 'mismatches': 0,
            'reference_audit_sha256': hashlib.sha256(raw).hexdigest()}
