"""Target-hardware M0 artifact, measurement, and projection helpers."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


REQUIRED_MEASUREMENTS = (
    "cold_load_seconds",
    "first_token_seconds",
    "decode_tokens_per_second",
    "cancellation_seconds",
    "peak_vram_bytes",
    "peak_ram_bytes",
    "offline_artifact_bytes",
)


@dataclass(frozen=True, slots=True)
class ArtifactInventory:
    tree_sha256: str
    file_count: int
    total_bytes: int


def inventory_artifact_tree(root: str | Path) -> ArtifactInventory:
    """Hash an offline artifact deterministically; symlinks fail closed."""
    base = Path(root).resolve()
    if not base.is_dir():
        raise ValueError("artifact root must be a directory")
    digest = hashlib.sha256(b"arc3-artifact-tree-v1\0")
    count = 0
    total = 0
    for path in sorted(base.rglob("*"), key=lambda item: item.relative_to(base).as_posix()):
        if path.is_symlink():
            raise ValueError(f"artifact tree contains a symlink: {path.relative_to(base)}")
        if not path.is_file():
            continue
        relative = path.relative_to(base).as_posix().encode()
        size = path.stat().st_size
        file_digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                file_digest.update(chunk)
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(size.to_bytes(8, "big"))
        digest.update(file_digest.digest())
        count += 1
        total += size
    if not count:
        raise ValueError("artifact tree is empty")
    return ArtifactInventory(digest.hexdigest(), count, total)


def project_execution_seconds(
    *,
    cold_load_seconds: float,
    request_latency_seconds: float,
    request_count: int,
    measured_concurrency: int,
    safety_factor: float = 1.25,
) -> float:
    """Conservative batch projection from a measured concurrent request trial."""
    values = (cold_load_seconds, request_latency_seconds, safety_factor)
    if any(not math.isfinite(value) or value < 0 for value in values):
        raise ValueError("projection inputs must be finite and non-negative")
    if request_count < 0 or measured_concurrency < 1 or safety_factor < 1:
        raise ValueError("projection count/concurrency/safety factor is invalid")
    batches = math.ceil(request_count / measured_concurrency)
    return cold_load_seconds + safety_factor * batches * request_latency_seconds


def observed_gpu_memory_bytes(description: str) -> int:
    """Extract the single-GPU MiB total emitted by the frozen nvidia-smi query."""
    match = re.search(r",\s*(\d+)\s*,\s*[^;,]+(?:;|$)", description)
    if match is None:
        raise ValueError("observed GPU description has no unambiguous memory total")
    return int(match.group(1)) * 1024 * 1024


def bounded_profile_projection(
    record: Mapping[str, Any],
    *,
    request_count: int,
    safety_factor: float,
) -> float:
    """Reproject a raw profile against the declared production call ceiling."""
    measurements = record.get("measurements")
    projection = record.get("projection")
    if not isinstance(measurements, Mapping) or not isinstance(projection, Mapping):
        raise ValueError("profile has no measurements/projection")
    concurrent = measurements.get("concurrent_trials")
    concurrency = projection.get("measured_concurrency")
    if (
        not isinstance(concurrent, list)
        or not concurrent
        or not isinstance(concurrency, int)
        or isinstance(concurrency, bool)
        or concurrency < 1
    ):
        raise ValueError("profile has no valid concurrent trial set")
    latencies = [
        item.get("elapsed_seconds") for item in concurrent if isinstance(item, Mapping)
    ]
    if len(latencies) != len(concurrent) or any(
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value < 0
        for value in latencies
    ):
        raise ValueError("profile concurrent latencies are invalid")
    # With the frozen eight-trial protocol this prospective p95 order statistic
    # is the observed maximum, deliberately guarding rather than averaging.
    latency_guard = sorted(float(value) for value in latencies)[
        min(len(latencies) - 1, math.ceil(0.95 * len(latencies)) - 1)
    ]
    return project_execution_seconds(
        cold_load_seconds=float(measurements["cold_load_seconds"]),
        request_latency_seconds=latency_guard,
        request_count=request_count,
        measured_concurrency=concurrency,
        safety_factor=safety_factor,
    )


def validate_profile_record(record: Mapping[str, Any], candidate: Mapping[str, Any]) -> tuple[str, ...]:
    """Return validation failures without converting missing evidence into defaults."""
    failures: list[str] = []
    if record.get("schema_version") != 1:
        failures.append("schema_version")
    for field in ("candidate_id", "model_id", "model_revision", "engine"):
        expected_field = "revision" if field == "model_revision" else field
        if record.get(field) != candidate.get(expected_field):
            failures.append(f"candidate_match:{field}")
    measurements = record.get("measurements")
    if not isinstance(measurements, Mapping):
        failures.append("measurements")
    else:
        for field in REQUIRED_MEASUREMENTS:
            value = measurements.get(field)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
                failures.append(f"measurement:{field}")
            elif value < 0 or (field in {"decode_tokens_per_second", "offline_artifact_bytes"} and value == 0):
                failures.append(f"measurement:{field}")
    artifact = record.get("artifact")
    if not isinstance(artifact, Mapping) or not _is_sha256(artifact.get("tree_sha256")):
        failures.append("artifact:tree_sha256")
    if candidate.get("artifact_sha256") not in (None, artifact.get("tree_sha256") if isinstance(artifact, Mapping) else None):
        failures.append("artifact:candidate_hash")
    return tuple(failures)


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)
