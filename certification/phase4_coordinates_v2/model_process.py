"""Fail-closed lifecycle for the Phase 1 operational model policy."""

from __future__ import annotations

import importlib.metadata
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import requests

from certification.phase4_coordinates_v2.model_config import ConfigurationError, load_registry
from certification.phase4_coordinates_v2.model_transport import E1ModelBinding


@dataclass(frozen=True, slots=True)
class OperationalPrimary:
    cell_id: str
    operational_label: str
    binding: E1ModelBinding
    model_path: Path
    model_tree_sha256: str
    required_files: tuple[str, ...]
    shard_glob: str
    shard_count: int
    launch_spec_path: Path
    base_url: str
    readiness_timeout_seconds: float
    completion_canary_timeout_seconds: float
    request_timeout_seconds: float
    scratch_log: Path
    hard_seconds: float
    finalization_reserve_seconds: float
    queue_capacity: int
    queue_workers: int
    queue_max_age_seconds: float
    max_new_tokens: int
    request_seed: int


def _exact_mapping(value: Any, required: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or not required <= set(value):
        raise ConfigurationError(f"{label} is incomplete")
    return value


def load_operational_primary(root: str | Path) -> OperationalPrimary:
    source_root = Path(root)
    registry = load_registry(source_root / "config/operational_primary.yaml")
    if registry.get("status") != "active_provisional_primary":
        raise ConfigurationError("operational primary is not active")
    primary = _exact_mapping(
        registry.get("primary"),
        {"cell_id", "operational_label", "model_binding", "model_artifact", "launch_spec", "server", "runtime", "inference"},
        "operational primary",
    )
    if primary.get("cell_id") != "E1S-R" or primary.get("operational_label") != "Provisional primary":
        raise ConfigurationError("only frozen provisional E1S-R may be operational")
    binding = E1ModelBinding.from_mapping(primary["model_binding"])
    artifact = _exact_mapping(
        primary["model_artifact"],
        {"mounted_path", "tree_sha256", "required_files", "shard_glob", "shard_count"},
        "model artifact",
    )
    server = _exact_mapping(
        primary["server"],
        {"base_url", "readiness_timeout_seconds", "completion_canary_timeout_seconds", "request_timeout_seconds", "scratch_log"},
        "model server",
    )
    runtime = _exact_mapping(
        primary["runtime"],
        {"hard_seconds", "finalization_reserve_seconds", "deadline_basis"},
        "runtime envelope",
    )
    inference = _exact_mapping(
        primary["inference"],
        {"queue_policy", "capacity", "worker_count", "max_age_seconds", "max_new_tokens", "request_seed"},
        "inference contract",
    )
    if (
        inference.get("queue_policy") != "minimum_fair_v1"
        or inference.get("capacity") != 110
        or inference.get("worker_count") != 8
        or inference.get("max_age_seconds") != 300
    ):
        raise ConfigurationError("operational queue contract drifted")
    if (
        runtime.get("hard_seconds") != 27_540
        or runtime.get("finalization_reserve_seconds") != 600
        or runtime.get("deadline_basis") != "full_lifecycle_including_model_load"
    ):
        raise ConfigurationError("operational runtime envelope drifted")
    model_path = Path(os.getenv("ARC_MODEL_PATH", str(artifact["mounted_path"])))
    return OperationalPrimary(
        cell_id=str(primary["cell_id"]),
        operational_label=str(primary["operational_label"]),
        binding=binding,
        model_path=model_path,
        model_tree_sha256=str(artifact["tree_sha256"]),
        required_files=tuple(str(item) for item in artifact["required_files"]),
        shard_glob=str(artifact["shard_glob"]),
        shard_count=int(artifact["shard_count"]),
        launch_spec_path=source_root / str(primary["launch_spec"]),
        base_url=str(server["base_url"]),
        readiness_timeout_seconds=float(server["readiness_timeout_seconds"]),
        completion_canary_timeout_seconds=float(server["completion_canary_timeout_seconds"]),
        request_timeout_seconds=float(server["request_timeout_seconds"]),
        scratch_log=Path(str(server["scratch_log"])),
        hard_seconds=float(runtime["hard_seconds"]),
        finalization_reserve_seconds=float(runtime["finalization_reserve_seconds"]),
        queue_capacity=int(inference["capacity"]),
        queue_workers=int(inference["worker_count"]),
        queue_max_age_seconds=float(inference["max_age_seconds"]),
        max_new_tokens=int(inference["max_new_tokens"]),
        request_seed=int(inference["request_seed"]),
    )


class ModelService:
    """Own one local vLLM process and its non-retained log."""

    def __init__(self, primary: OperationalPrimary) -> None:
        self.primary = primary
        self.process: subprocess.Popen[bytes] | None = None
        self._log: Any = None

    def _argv_and_env(self) -> tuple[list[str], dict[str, str]]:
        spec = json.loads(self.primary.launch_spec_path.read_text())
        expected = {
            "candidate_id": self.primary.binding.candidate_id,
            "model_id": self.primary.binding.model_id,
            "model_revision": self.primary.binding.revision,
            "engine": self.primary.binding.engine,
            "reasoning_setting": self.primary.binding.reasoning_setting,
            "base_url": self.primary.base_url,
        }
        if any(spec.get(key) != value for key, value in expected.items()):
            raise ConfigurationError("operational launch specification drifted")
        argv = [
            str(item).replace("{python}", sys.executable).replace("{model_path}", str(self.primary.model_path))
            for item in spec.get("argv", [])
        ]
        if not argv or argv[:3] != [sys.executable, "-m", "vllm.entrypoints.openai.api_server"]:
            raise ConfigurationError("operational model launch command is invalid")
        environment = os.environ.copy()
        environment.update({str(key): str(value) for key, value in spec.get("env", {}).items()})
        environment["PYTHONUNBUFFERED"] = "1"
        return argv, environment

    def start(self) -> float:
        if self.process is not None:
            raise RuntimeError("model service already started")
        if not self.primary.model_path.is_dir():
            raise FileNotFoundError("operational model artifact is not mounted")
        missing = [name for name in self.primary.required_files if not (self.primary.model_path / name).is_file()]
        shards = sorted(self.primary.model_path.glob(self.primary.shard_glob))
        if missing or len(shards) != self.primary.shard_count:
            raise RuntimeError("operational model artifact layout drifted")
        expected_packages = {"vllm": "0.19.0", "torch": "2.10.0", "transformers": "4.57.6"}
        for package, expected in expected_packages.items():
            observed = importlib.metadata.version(package).split("+")[0]
            if observed != expected:
                raise RuntimeError(f"operational package drifted: {package}")
        argv, environment = self._argv_and_env()
        self.primary.scratch_log.parent.mkdir(parents=True, exist_ok=True)
        self._log = self.primary.scratch_log.open("wb")
        started = time.monotonic()
        self.process = subprocess.Popen(argv, env=environment, stdout=self._log, stderr=subprocess.STDOUT)
        deadline = started + self.primary.readiness_timeout_seconds
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                self.close()
                raise RuntimeError("operational model server exited before readiness")
            try:
                response = requests.get(f"{self.primary.base_url}/models", timeout=2)
                if response.ok:
                    self._completion_canary()
                    return time.monotonic() - started
            except requests.RequestException:
                pass
            time.sleep(1)
        self.close()
        raise TimeoutError("operational model readiness timeout")

    def _completion_canary(self) -> None:
        """Prove the configured model can complete before any environment call."""

        response = requests.post(
            f"{self.primary.base_url.rstrip('/')}/chat/completions",
            json={
                "model": self.primary.binding.model_id,
                "messages": [
                    {"role": "system", "content": "Reply with exactly OK."},
                    {"role": "user", "content": "Ready?"},
                ],
                "temperature": 0,
                "seed": self.primary.request_seed,
                "max_tokens": 8,
                "chat_template_kwargs": {"enable_thinking": False},
            },
            timeout=self.primary.completion_canary_timeout_seconds,
        )
        response.raise_for_status()
        value = response.json()
        try:
            content = value["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("operational completion canary returned no content") from exc
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("operational completion canary returned empty content")

    def close(self) -> None:
        process, self.process = self.process, None
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=60)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=30)
        if self._log is not None:
            self._log.close()
            self._log = None

    def __enter__(self) -> "ModelService":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
