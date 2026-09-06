"""Strict JSON-compatible YAML registry loader used by Phase 0."""

from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


class ConfigurationError(ValueError):
    pass


def load_registry(path: str | Path) -> Mapping[str, Any]:
    source = Path(path)
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"invalid registry {source.name}: {exc}") from exc
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ConfigurationError(f"unsupported or missing schema_version in {source.name}")
    return MappingProxyType(value)
