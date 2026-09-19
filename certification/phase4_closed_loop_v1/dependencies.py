"""Make prepared interpreter trees read-only; restore directory access for removal."""
from pathlib import Path
import stat

def freeze(root):
    for role in ('model','game'):
        tree=Path(root)/role/'venv'
        paths=[tree,*tree.rglob('*')]
        for path in paths:
            if path.is_symlink(): continue  # Never chmod the external base interpreter.
            path.chmod(stat.S_IMODE(path.stat().st_mode)&~0o222)

def thaw(root):
    for role in ('model','game'):
        tree=Path(root)/role/'venv'
        if tree.exists():
            for path in [tree,*tree.rglob('*')]:
                if not path.is_symlink() and path.is_dir():
                    path.chmod(stat.S_IMODE(path.stat().st_mode)|0o700)
