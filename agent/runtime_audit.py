"""Fail-closed validation of the exact mounted Phase 0 runtime."""

from __future__ import annotations

import hashlib
import inspect
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

import arc_agi.api
import arc_agi.base
import arc_agi.remote_wrapper
import arc_agi.scorecard
import arcengine.enums
from arcengine import ActionInput, GameAction, MAX_REASONING_BYTES

from .action import wire_json_bytes


RUNTIME_PROFILES = {
    "local_2026_09_06": {
        "distributions": {
            "arc-agi": "0.9.9",
            "arcengine": "0.9.3",
            "requests": "2.34.2",
            "numpy": "2.5.2",
            "pydantic": "2.13.5",
        },
        "source_hashes": {
            "arc_agi.base": "42973618f223096d6269422352980e85bdf6b2b51dcb42e7390f96164b0f994f",
            "arc_agi.remote_wrapper": "f1ea41c656117408351ca260b6159e7c6acf7200c45d5d05cfaa1ce0a3cf1206",
            "arc_agi.api": "07a82fa2b00cf2214c573a9027a628af67c9fdbd9c31b66e6250a9aa12c30ec5",
            "arc_agi.scorecard": "1cc830e48008bec60b8a98ae14d3e9312e8408f102a9878bad42744aa9e489b7",
            "arcengine.enums": "94ebef48f6fe950a18679a1b991c366e8e28c32ab58c9335f385e19bea21950e",
        },
    },
    "kaggle_2026_09_07": {
        "distributions": {
            "arc-agi": "0.9.8",
            "arcengine": "0.9.3",
            "requests": "2.33.1",
            "numpy": "2.4.4",
            "pydantic": "2.13.2",
        },
        "source_hashes": {
            "arc_agi.base": "42973618f223096d6269422352980e85bdf6b2b51dcb42e7390f96164b0f994f",
            "arc_agi.remote_wrapper": "ebe8fd0a5ab2d5f65600f072fb22cf1de21c347a55b8c5ef569d6d7305c520e5",
            "arc_agi.api": "07a82fa2b00cf2214c573a9027a628af67c9fdbd9c31b66e6250a9aa12c30ec5",
            "arc_agi.scorecard": "1cc830e48008bec60b8a98ae14d3e9312e8408f102a9878bad42744aa9e489b7",
            "arcengine.enums": "94ebef48f6fe950a18679a1b991c366e8e28c32ab58c9335f385e19bea21950e",
        },
    },
}


@dataclass(frozen=True, slots=True)
class RuntimeAudit:
    profile: str
    passed: bool
    checks: tuple[str, ...]
    failures: tuple[str, ...]


def _source_hash(module: object) -> str:
    path = Path(inspect.getfile(module))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_mounted_runtime(profile: str = "local_2026_09_06") -> RuntimeAudit:
    if profile not in RUNTIME_PROFILES:
        raise ValueError(f"unknown runtime profile: {profile}")
    expected_profile = RUNTIME_PROFILES[profile]
    checks: list[str] = []
    failures: list[str] = []

    def record(label: str, condition: bool) -> None:
        (checks if condition else failures).append(label)

    for distribution, expected in expected_profile["distributions"].items():
        record(f"distribution:{distribution}", version(distribution) == expected)
    modules = {
        "arc_agi.base": arc_agi.base,
        "arc_agi.remote_wrapper": arc_agi.remote_wrapper,
        "arc_agi.api": arc_agi.api,
        "arc_agi.scorecard": arc_agi.scorecard,
        "arcengine.enums": arcengine.enums,
    }
    for name, module in modules.items():
        record(f"source:{name}", _source_hash(module) == expected_profile["source_hashes"][name])

    record("reasoning:max_constant", MAX_REASONING_BYTES == 16_384)
    try:
        ActionInput(id=GameAction.ACTION1, reasoning="a" * 16_382)
        exact_ok = True
    except Exception:
        exact_ok = False
    record("reasoning:exact_16k", exact_ok)
    try:
        ActionInput(id=GameAction.ACTION1, reasoning="a" * 16_383)
        above_rejected = False
    except Exception:
        above_rejected = True
    record("reasoning:over_16k_rejected", above_rejected)

    body = {"game_id": "opaque", "guid": "opaque", "reasoning": '{"probe": true}'}
    from requests import Request

    prepared = Request("POST", "http://gateway/api/cmd/ACTION1", json=body).prepare()
    record("requests:json_wire_bytes", prepared.body == wire_json_bytes(body))

    from arc_agi import Arcade
    from arc_agi.remote_wrapper import RemoteEnvironmentWrapper

    make_parameters = inspect.signature(Arcade.make).parameters
    step_parameters = inspect.signature(RemoteEnvironmentWrapper.step).parameters
    record("signature:arcade_make", {"game_id", "scorecard_id"}.issubset(make_parameters))
    record("signature:remote_step", {"action", "data", "reasoning"}.issubset(step_parameters))
    return RuntimeAudit(profile, not failures, tuple(checks), tuple(failures))
