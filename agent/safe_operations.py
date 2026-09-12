"""Proposal-local, non-Turing-complete E1C safe-operation worker."""

from __future__ import annotations

import multiprocessing as mp
import os
import platform
import queue
import time
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np


SAFE_OPERATIONS = frozenset(
    {
        "array_shape",
        "cell_value",
        "palette",
        "changed_cells",
        "change_bounding_box",
        "connected_components",
        "region_summary",
        "translation_candidates",
    }
)


class SafeOperationError(ValueError):
    """A request is outside the frozen safe-operation authority."""


@dataclass(frozen=True, slots=True)
class SafeOperationLimits:
    invocations_per_proposal: int = 7
    cpu_seconds_per_invocation: int = 2
    memory_bytes: int = 256 * 1024 * 1024
    output_bytes_per_invocation: int = 8192
    wall_seconds_per_invocation: float = 3.0
    wall_seconds_per_proposal: float = 14.0
    output_bytes_per_proposal: int = 8192


def _grid(value: Any) -> np.ndarray:
    result = np.asarray(value)
    if result.ndim != 2 or not np.issubdtype(result.dtype, np.integer):
        raise SafeOperationError("safe-operation grids must be two-dimensional integers")
    if result.size and (int(result.min()) < 0 or int(result.max()) > 255):
        raise SafeOperationError("safe-operation grids must fit uint8")
    packed = np.array(result, dtype=np.uint8, order="C", copy=True)
    packed.setflags(write=False)
    return packed


def _bbox(mask: np.ndarray) -> list[int] | None:
    locations = np.argwhere(mask)
    if not locations.size:
        return None
    top, left = locations.min(axis=0)
    bottom, right = locations.max(axis=0)
    return [int(top), int(left), int(bottom), int(right)]


def _components(grid: np.ndarray) -> list[dict[str, Any]]:
    visited = np.zeros(grid.shape, dtype=bool)
    result: list[dict[str, Any]] = []
    rows, columns = grid.shape
    for row in range(rows):
        for column in range(columns):
            if visited[row, column]:
                continue
            color = int(grid[row, column])
            stack = [(row, column)]
            visited[row, column] = True
            cells: list[tuple[int, int]] = []
            while stack:
                current = stack.pop()
                cells.append(current)
                for neighbor in (
                    (current[0] - 1, current[1]),
                    (current[0] + 1, current[1]),
                    (current[0], current[1] - 1),
                    (current[0], current[1] + 1),
                ):
                    nr, nc = neighbor
                    if (
                        0 <= nr < rows
                        and 0 <= nc < columns
                        and not visited[nr, nc]
                        and int(grid[nr, nc]) == color
                    ):
                        visited[nr, nc] = True
                        stack.append(neighbor)
            cell_array = np.asarray(cells, dtype=np.int64)
            result.append(
                {
                    "color": color,
                    "size": len(cells),
                    "bounding_box": [
                        int(cell_array[:, 0].min()),
                        int(cell_array[:, 1].min()),
                        int(cell_array[:, 0].max()),
                        int(cell_array[:, 1].max()),
                    ],
                    "cells": [[int(r), int(c)] for r, c in sorted(cells)],
                }
            )
    return result


def execute_safe_operation(
    operation: str,
    arrays: Mapping[str, Any],
    arguments: Mapping[str, Any] | None = None,
) -> Any:
    """Execute exactly one registered total operation over supplied arrays."""
    if operation not in SAFE_OPERATIONS:
        raise SafeOperationError(f"unsupported safe operation: {operation}")
    if not isinstance(arguments, Mapping):
        arguments = {}
    allowed_arrays = {str(name): _grid(value) for name, value in arrays.items()}

    def named(field: str = "array") -> np.ndarray:
        default = field if field in allowed_arrays else "current"
        name = arguments.get(field, default)
        if not isinstance(name, str) or name not in allowed_arrays:
            raise SafeOperationError(f"unknown array reference: {name!r}")
        return allowed_arrays[name]

    if operation == "array_shape":
        return list(named().shape)
    if operation == "cell_value":
        grid = named()
        row, column = arguments.get("row"), arguments.get("column")
        if isinstance(row, bool) or isinstance(column, bool) or not isinstance(row, int) or not isinstance(column, int):
            raise SafeOperationError("row and column must be integers")
        if not (0 <= row < grid.shape[0] and 0 <= column < grid.shape[1]):
            raise SafeOperationError("cell lies outside the selected array")
        return int(grid[row, column])
    if operation == "palette":
        values, counts = np.unique(named(), return_counts=True)
        return {str(int(value)): int(count) for value, count in zip(values, counts)}

    if operation == "connected_components":
        return _components(named())
    if operation == "region_summary":
        return [
            {key: value for key, value in component.items() if key != "cells"}
            for component in _components(named())
        ]

    before, after = named("before"), named("after")
    if before.shape != after.shape:
        raise SafeOperationError("before and after arrays must have equal shapes")
    changed = before != after
    if operation == "changed_cells":
        return [[int(row), int(column)] for row, column in np.argwhere(changed)]
    if operation == "change_bounding_box":
        return _bbox(changed)

    before_components = _components(before)
    after_components = _components(after)
    candidates: list[dict[str, int]] = []
    for left in before_components:
        for right in after_components:
            if left["color"] != right["color"] or left["size"] != right["size"]:
                continue
            left_cells = left["cells"]
            right_cells = right["cells"]
            row_delta = right_cells[0][0] - left_cells[0][0]
            column_delta = right_cells[0][1] - left_cells[0][1]
            translated = sorted(
                [[row + row_delta, column + column_delta] for row, column in left_cells]
            )
            if translated == right_cells:
                candidates.append(
                    {
                        "color": left["color"],
                        "size": left["size"],
                        "row_delta": row_delta,
                        "column_delta": column_delta,
                    }
                )
    return candidates


def _apply_child_limits(limits: SafeOperationLimits) -> None:
    os.environ.clear()
    os.environ.update({"LANG": "C", "LC_ALL": "C", "PYTHONHASHSEED": "0"})
    if platform.system() != "Linux":
        return
    import resource

    resource.setrlimit(
        resource.RLIMIT_CPU,
        (limits.cpu_seconds_per_invocation, limits.cpu_seconds_per_invocation),
    )
    # CPython + NumPy already map more than the proposal allowance on many
    # Linux builds. Bound *additional* child address space so the worker stays
    # functional while still preventing proposal-driven growth.
    current_pages = int(Path("/proc/self/statm").read_text().split()[0])
    address_space_cap = current_pages * os.sysconf("SC_PAGE_SIZE") + limits.memory_bytes
    resource.setrlimit(resource.RLIMIT_AS, (address_space_cap, address_space_cap))
    resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (16, 16))


def _child(
    output: Any,
    operation: str,
    arrays: Mapping[str, Any],
    arguments: Mapping[str, Any],
    limits: SafeOperationLimits,
) -> None:
    try:
        _apply_child_limits(limits)
        output.put((True, execute_safe_operation(operation, arrays, arguments)))
    except BaseException as exc:
        output.put((False, f"{type(exc).__name__}: {exc}"))


class SafeOperationWorkspace:
    """Spawn-isolated workspace with a proposal-local invocation budget."""

    def __init__(
        self,
        arrays: Mapping[str, Any],
        *,
        limits: SafeOperationLimits | None = None,
    ) -> None:
        self.arrays = MappingProxyType({str(key): _grid(value) for key, value in arrays.items()})
        self.limits = limits or SafeOperationLimits()
        self.invocations = 0
        self._started = time.monotonic()
        self._output_bytes = 0

    def invoke(self, operation: str, arguments: Mapping[str, Any] | None = None) -> Any:
        if self.invocations >= self.limits.invocations_per_proposal:
            raise SafeOperationError("safe-operation invocation budget exhausted")
        remaining = self.limits.wall_seconds_per_proposal - (time.monotonic() - self._started)
        if remaining <= 0:
            raise SafeOperationError("safe-operation proposal time budget exhausted")
        self.invocations += 1
        context = mp.get_context("spawn")
        output = context.Queue(maxsize=1)
        process = context.Process(
            target=_child,
            args=(output, operation, dict(self.arrays), dict(arguments or {}), self.limits),
            daemon=True,
        )
        process.start()
        process.join(min(self.limits.wall_seconds_per_invocation, remaining))
        if process.is_alive():
            process.terminate()
            process.join(1)
            raise SafeOperationError("safe operation exceeded wall-clock limit")
        try:
            # A multiprocessing queue's feeder may flush just after the child
            # exits.  A short bounded read avoids treating that benign race as
            # silent workspace loss.
            succeeded, value = output.get(timeout=0.5)
        except queue.Empty as exc:
            raise SafeOperationError("safe operation worker returned no result") from exc
        if not succeeded:
            raise SafeOperationError(str(value))
        import json

        encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        if len(encoded) > self.limits.output_bytes_per_invocation:
            raise SafeOperationError("safe operation output exceeds byte limit")
        self._output_bytes += len(encoded)
        if self._output_bytes > self.limits.output_bytes_per_proposal:
            raise SafeOperationError("safe-operation proposal output budget exhausted")
        return value
