"""Scoped retained-output enforcement for handled execution paths."""

from __future__ import annotations

import shutil
from pathlib import Path


class OutputPolicyError(RuntimeError):
    pass


def enforce_retained_allowlist(
    root: str | Path,
    *,
    allowed_names: frozenset[str] = frozenset({"submission.parquet"}),
    remove_allowed: bool = False,
) -> tuple[str, ...]:
    resolved = Path(root).resolve()
    if str(resolved) in {"/", str(Path.home().resolve())}:
        raise OutputPolicyError("refusing a broad retained-output root")
    resolved.mkdir(parents=True, exist_ok=True)
    removed: list[str] = []
    for child in resolved.iterdir():
        if child.name in allowed_names and not remove_allowed:
            continue
        if child.is_symlink() or child.is_file():
            child.unlink()
        elif child.is_dir():
            shutil.rmtree(child)
        else:
            raise OutputPolicyError(f"unsupported output entry: {child.name}")
        removed.append(child.name)
    return tuple(sorted(removed))
