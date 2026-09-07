"""Validate Kaggle credentials and kernel metadata without exposing secrets."""

from __future__ import annotations

import json
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    token = ROOT / ".kaggle" / "access_token"
    if not token.is_file() or token.stat().st_size == 0:
        print("KAGGLE_CONFIG_INVALID token_missing")
        return 2
    mode = stat.S_IMODE(token.stat().st_mode)
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        print("KAGGLE_CONFIG_INVALID token_permissions")
        return 2
    if len(token.read_text(encoding="utf-8").strip().splitlines()) != 1:
        print("KAGGLE_CONFIG_INVALID token_format")
        return 2
    metadata = json.loads((ROOT / "notebooks" / "kernel-metadata.json").read_text())
    kernel_id = str(metadata.get("id", ""))
    if not kernel_id or "REPLACE_WITH_YOUR_USERNAME" in kernel_id or "/" not in kernel_id:
        print("KAGGLE_CONFIG_INVALID kernel_id")
        return 2
    if metadata.get("enable_internet") is not False:
        print("KAGGLE_CONFIG_INVALID internet")
        return 2
    print("KAGGLE_CONFIG_VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
