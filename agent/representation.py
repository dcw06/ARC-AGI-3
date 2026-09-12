"""Minimal, auditable Phase 0F raw (R) and engineered (E0F) views."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np

from .action import DisplayPoint
from .evidence import CompactDelta, EvidenceStore, PackedGrid, PackedFrameSequence


class TransformReliability(str, Enum):
    EXACT = "exact"
    TESTED = "tested"
    TENTATIVE = "tentative"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class ScenePoint:
    row: int
    column: int

    def __post_init__(self) -> None:
        if isinstance(self.row, bool) or isinstance(self.column, bool):
            raise ValueError("scene coordinates must be integers")
        if self.row < 0 or self.column < 0:
            raise ValueError("scene coordinates cannot be negative")


@dataclass(frozen=True, slots=True)
class CoordinateTransform:
    rows: int
    columns: int
    reliability: TransformReliability

    def __post_init__(self) -> None:
        if self.rows < 1 or self.columns < 1:
            raise ValueError("coordinate transform requires a non-empty scene")

    def scene_to_display(self, point: ScenePoint) -> DisplayPoint:
        if self.reliability not in {TransformReliability.EXACT, TransformReliability.TESTED}:
            raise ValueError("coordinate transform is not reliable enough for action dispatch")
        if point.row >= self.rows or point.column >= self.columns:
            raise ValueError("scene point lies outside the transform")
        x = 0 if self.columns == 1 else round(point.column * 63 / (self.columns - 1))
        y = 0 if self.rows == 1 else round(point.row * 63 / (self.rows - 1))
        return DisplayPoint(x=x, y=y)


@dataclass(frozen=True, slots=True)
class SameColorRegion:
    color: int
    cells: tuple[ScenePoint, ...]
    bounding_box: tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class Translation:
    color: int
    row_delta: int
    column_delta: int
    cell_count: int


@dataclass(frozen=True, slots=True)
class RegionEvent:
    color: int
    cells: tuple[ScenePoint, ...]
    bounding_box: tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class RawObservationBundle:
    """The R policy contract: latest exact frame and bounded raw history only."""

    current_frame: PackedGrid
    state: str
    levels_completed: int
    win_levels: int
    legal_actions: tuple[int, ...]
    previous_final_frame: PackedGrid | None
    recent_actions: tuple[int, ...]
    recent_final_frames: tuple[PackedGrid, ...]
    history_total_transitions: int
    history_omitted_transitions: int
    history_sha256: str | None

    def policy_payload(self) -> dict[str, Any]:
        return {
            "current_grid": self.current_frame.unpack().tolist(),
            "state": self.state,
            "levels_completed": self.levels_completed,
            "win_levels": self.win_levels,
            "legal_actions": list(self.legal_actions),
            "previous_grid": None
            if self.previous_final_frame is None
            else self.previous_final_frame.unpack().tolist(),
            "recent_actions": list(self.recent_actions),
            "recent_final_grids": [frame.unpack().tolist() for frame in self.recent_final_frames],
            "history_compaction": {
                "policy": "visible_recent_transitions_v1",
                "total_transitions": self.history_total_transitions,
                "retained_transitions": len(self.recent_actions),
                "omitted_transitions": self.history_omitted_transitions,
                "history_sha256": self.history_sha256,
            },
        }


@dataclass(frozen=True, slots=True)
class EngineeredFeatures:
    sequence_sha256: str
    final_frame_sha256: str
    frame_count: int
    distinct_frame_count: int
    inter_frame_changed_cells: tuple[int, ...]
    inter_frame_union_bbox: tuple[int, int, int, int] | None
    inter_action_delta: CompactDelta | None
    transient_cells: tuple[ScenePoint, ...]
    palette_added: tuple[int, ...]
    palette_removed: tuple[int, ...]
    regions: tuple[SameColorRegion, ...]
    appearances: tuple[RegionEvent, ...]
    disappearances: tuple[RegionEvent, ...]
    translations: tuple[Translation, ...]
    action6_candidates: tuple[DisplayPoint, ...]


@dataclass(frozen=True, slots=True)
class FeatureObservationBundle:
    raw: RawObservationBundle
    features: EngineeredFeatures

    def policy_payload(self) -> dict[str, Any]:
        """Return the frozen, JSON-native F payload visible to policy code."""
        features = self.features
        return {
            "raw": self.raw.policy_payload(),
            "features": {
                "sequence_sha256": features.sequence_sha256,
                "final_frame_sha256": features.final_frame_sha256,
                "frame_count": features.frame_count,
                "distinct_frame_count": features.distinct_frame_count,
                "inter_frame_changed_cells": list(features.inter_frame_changed_cells),
                "inter_frame_union_bbox": None
                if features.inter_frame_union_bbox is None
                else list(features.inter_frame_union_bbox),
                "inter_action_delta": None
                if features.inter_action_delta is None
                else {
                    "changed_cells": features.inter_action_delta.changed_cells,
                    "bounding_box": None
                    if features.inter_action_delta.bounding_box is None
                    else list(features.inter_action_delta.bounding_box),
                    "palette_added": list(features.inter_action_delta.palette_added),
                    "palette_removed": list(features.inter_action_delta.palette_removed),
                },
                "transient_cells": [[point.row, point.column] for point in features.transient_cells],
                "palette_added": list(features.palette_added),
                "palette_removed": list(features.palette_removed),
                "regions": [
                    {
                        "color": region.color,
                        "cells": [[point.row, point.column] for point in region.cells],
                        "bounding_box": list(region.bounding_box),
                    }
                    for region in features.regions
                ],
                "appearances": [
                    {
                        "color": event.color,
                        "cells": [[point.row, point.column] for point in event.cells],
                        "bounding_box": list(event.bounding_box),
                    }
                    for event in features.appearances
                ],
                "disappearances": [
                    {
                        "color": event.color,
                        "cells": [[point.row, point.column] for point in event.cells],
                        "bounding_box": list(event.bounding_box),
                    }
                    for event in features.disappearances
                ],
                "translations": [
                    {
                        "color": item.color,
                        "row_delta": item.row_delta,
                        "column_delta": item.column_delta,
                        "cell_count": item.cell_count,
                    }
                    for item in features.translations
                ],
                "action6_candidates": [[point.x, point.y] for point in features.action6_candidates],
            },
        }


def build_raw_bundle(
    observation: Any,
    evidence: EvidenceStore | None = None,
    *,
    recent_limit: int | None = None,
) -> RawObservationBundle:
    all_records = evidence.transitions if evidence is not None else ()
    records = all_records
    if recent_limit is not None:
        if recent_limit < 0:
            raise ValueError("recent_limit cannot be negative")
        records = records[-recent_limit:] if recent_limit else ()
    total_transitions = (
        evidence.transition_count if evidence is not None else len(all_records)
    )
    omitted_count = total_transitions - len(records)
    previous = None
    if records:
        latest = records[-1]
        previous = (
            latest.prior_final_frame
            if latest.post_state_hash == observation.canonical_hash
            else latest.final_frame
        )
    return RawObservationBundle(
        current_frame=PackedGrid.pack(observation.latest_frame, frame_index=0),
        state=str(observation.state.value),
        levels_completed=int(observation.levels_completed),
        win_levels=int(observation.win_levels),
        legal_actions=tuple(int(action) for action in observation.available_actions),
        previous_final_frame=previous,
        recent_actions=tuple(record.action_id for record in records),
        recent_final_frames=tuple(record.final_frame for record in records),
        history_total_transitions=total_transitions,
        history_omitted_transitions=omitted_count,
        history_sha256=None
        if evidence is None
        else evidence.transition_history_sha256,
    )


def build_feature_bundle(
    observation: Any,
    evidence: EvidenceStore | None = None,
    *,
    previous_final: PackedGrid | np.ndarray[Any, Any] | None = None,
    transform: CoordinateTransform | None = None,
    recent_limit: int | None = None,
) -> FeatureObservationBundle:
    raw = build_raw_bundle(observation, evidence, recent_limit=recent_limit)
    sequence = PackedFrameSequence.pack(observation.frames)
    arrays = tuple(frame.unpack() for frame in sequence.frames)
    changed_counts: list[int] = []
    union_mask = np.zeros(arrays[-1].shape, dtype=bool)
    comparable = all(array.shape == arrays[-1].shape for array in arrays)
    if comparable:
        for left, right in zip(arrays, arrays[1:]):
            changed = left != right
            changed_counts.append(int(changed.sum()))
            union_mask |= changed
    union_bbox = _mask_bbox(union_mask) if comparable else None

    transient: tuple[ScenePoint, ...] = ()
    if comparable and len(arrays) > 2:
        intermediate_changed = np.logical_or.reduce([frame != arrays[0] for frame in arrays[1:-1]])
        transient = _points(intermediate_changed & (arrays[0] == arrays[-1]))

    before_array: np.ndarray[Any, Any] | None = None
    before_grid: PackedGrid | None = None
    if previous_final is not None:
        before_grid = previous_final if isinstance(previous_final, PackedGrid) else PackedGrid.pack(previous_final, frame_index=0)
        before_array = before_grid.unpack()
    elif evidence is not None and evidence.transitions:
        latest = evidence.transitions[-1]
        before_grid = (
            latest.prior_final_frame
            if latest.post_state_hash == observation.canonical_hash
            else latest.final_frame
        )
        before_array = before_grid.unpack()

    palette_before = set(int(value) for value in np.unique(before_array)) if before_array is not None else set()
    palette_now = set(int(value) for value in np.unique(arrays[-1]))
    inter_action = _delta(before_grid, sequence.final) if before_grid is not None else None
    regions = _regions(arrays[-1])
    before_regions = _regions(before_array) if before_array is not None and before_array.shape == arrays[-1].shape else ()
    appearances, disappearances = _appearance_events(before_regions, regions)
    translations = _translations(before_array, arrays[-1]) if before_array is not None else ()

    active_transform = transform or CoordinateTransform(
        arrays[-1].shape[0], arrays[-1].shape[1], TransformReliability.TESTED
    )
    candidates: list[DisplayPoint] = []
    if 6 in raw.legal_actions and active_transform.reliability in {
        TransformReliability.EXACT,
        TransformReliability.TESTED,
    }:
        for region in regions:
            if region.color == 0:
                continue
            center = region.cells[len(region.cells) // 2]
            candidates.append(active_transform.scene_to_display(center))
            if len(candidates) == 32:
                break

    return FeatureObservationBundle(
        raw=raw,
        features=EngineeredFeatures(
            sequence_sha256=sequence.canonical_sha256,
            final_frame_sha256=sequence.final.content_sha256,
            frame_count=len(sequence.frames),
            distinct_frame_count=len({frame.content_sha256 for frame in sequence.frames}),
            inter_frame_changed_cells=tuple(changed_counts),
            inter_frame_union_bbox=union_bbox,
            inter_action_delta=inter_action,
            transient_cells=transient,
            palette_added=tuple(sorted(palette_now - palette_before)),
            palette_removed=tuple(sorted(palette_before - palette_now)),
            regions=regions,
            appearances=appearances,
            disappearances=disappearances,
            translations=translations,
            action6_candidates=tuple(candidates),
        ),
    )


def representation_digest(bundle: RawObservationBundle | FeatureObservationBundle) -> str:
    """Stable audit digest; not included in the R model-visible payload."""
    raw = bundle.raw if isinstance(bundle, FeatureObservationBundle) else bundle
    manifest: dict[str, Any] = {
        "version": "arc3-representation-v1",
        "raw": raw.policy_payload(),
    }
    if isinstance(bundle, FeatureObservationBundle):
        features = bundle.features
        manifest["features"] = {
            "sequence_sha256": features.sequence_sha256,
            "final_frame_sha256": features.final_frame_sha256,
            "frame_count": features.frame_count,
            "distinct_frame_count": features.distinct_frame_count,
            "inter_frame_changed_cells": features.inter_frame_changed_cells,
            "inter_frame_union_bbox": features.inter_frame_union_bbox,
            "inter_action_delta": None
            if features.inter_action_delta is None
            else (
                features.inter_action_delta.changed_cells,
                features.inter_action_delta.bounding_box,
                features.inter_action_delta.palette_added,
                features.inter_action_delta.palette_removed,
            ),
            "transient_cells": [(p.row, p.column) for p in features.transient_cells],
            "palette_added": features.palette_added,
            "palette_removed": features.palette_removed,
            "regions": [
                (r.color, [(p.row, p.column) for p in r.cells], r.bounding_box)
                for r in features.regions
            ],
            "appearances": [
                (event.color, [(p.row, p.column) for p in event.cells], event.bounding_box)
                for event in features.appearances
            ],
            "disappearances": [
                (event.color, [(p.row, p.column) for p in event.cells], event.bounding_box)
                for event in features.disappearances
            ],
            "translations": [
                (t.color, t.row_delta, t.column_delta, t.cell_count) for t in features.translations
            ],
            "action6_candidates": [(p.x, p.y) for p in features.action6_candidates],
        }
    payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _mask_bbox(mask: np.ndarray[Any, Any]) -> tuple[int, int, int, int] | None:
    locations = np.argwhere(mask)
    if not locations.size:
        return None
    top, left = locations.min(axis=0)
    bottom, right = locations.max(axis=0)
    return int(top), int(left), int(bottom), int(right)


def _points(mask: np.ndarray[Any, Any]) -> tuple[ScenePoint, ...]:
    return tuple(ScenePoint(int(row), int(column)) for row, column in np.argwhere(mask))


def _delta(before: PackedGrid, after: PackedGrid) -> CompactDelta:
    if before.shape != after.shape:
        return CompactDelta(-1, None, (), ())
    left, right = before.unpack(), after.unpack()
    before_palette = set(int(value) for value in np.unique(left))
    after_palette = set(int(value) for value in np.unique(right))
    return CompactDelta(
        changed_cells=int((left != right).sum()),
        bounding_box=_mask_bbox(left != right),
        palette_added=tuple(sorted(after_palette - before_palette)),
        palette_removed=tuple(sorted(before_palette - after_palette)),
    )


def _regions(grid: np.ndarray[Any, Any]) -> tuple[SameColorRegion, ...]:
    rows, columns = grid.shape
    visited = np.zeros(grid.shape, dtype=bool)
    result: list[SameColorRegion] = []
    for row in range(rows):
        for column in range(columns):
            if visited[row, column]:
                continue
            color = int(grid[row, column])
            stack = [(row, column)]
            visited[row, column] = True
            cells: list[ScenePoint] = []
            while stack:
                current_row, current_column = stack.pop()
                cells.append(ScenePoint(current_row, current_column))
                for next_row, next_column in (
                    (current_row - 1, current_column),
                    (current_row + 1, current_column),
                    (current_row, current_column - 1),
                    (current_row, current_column + 1),
                ):
                    if (
                        0 <= next_row < rows
                        and 0 <= next_column < columns
                        and not visited[next_row, next_column]
                        and int(grid[next_row, next_column]) == color
                    ):
                        visited[next_row, next_column] = True
                        stack.append((next_row, next_column))
            cells.sort(key=lambda point: (point.row, point.column))
            cell_tuple = tuple(cells)
            result.append(
                SameColorRegion(
                    color,
                    cell_tuple,
                    (
                        min(point.row for point in cell_tuple),
                        min(point.column for point in cell_tuple),
                        max(point.row for point in cell_tuple),
                        max(point.column for point in cell_tuple),
                    ),
                )
            )
    return tuple(result)


def _translations(
    before: np.ndarray[Any, Any], after: np.ndarray[Any, Any]
) -> tuple[Translation, ...]:
    if before.shape != after.shape:
        return ()
    before_regions = _regions(before)
    after_regions = _regions(after)
    result: list[Translation] = []
    colors = sorted(set(region.color for region in before_regions) & set(region.color for region in after_regions))
    for color in colors:
        left = [region for region in before_regions if region.color == color]
        right = [region for region in after_regions if region.color == color]
        if len(left) != 1 or len(right) != 1 or len(left[0].cells) != len(right[0].cells):
            continue
        row_delta = right[0].cells[0].row - left[0].cells[0].row
        column_delta = right[0].cells[0].column - left[0].cells[0].column
        shifted = {
            (point.row + row_delta, point.column + column_delta) for point in left[0].cells
        }
        target = {(point.row, point.column) for point in right[0].cells}
        if shifted == target and (row_delta or column_delta):
            result.append(Translation(color, row_delta, column_delta, len(target)))
    return tuple(result)


def _appearance_events(
    before: tuple[SameColorRegion, ...], after: tuple[SameColorRegion, ...]
) -> tuple[tuple[RegionEvent, ...], tuple[RegionEvent, ...]]:
    """Conservative events: only colors wholly absent on one side qualify."""
    before_colors = {region.color for region in before}
    after_colors = {region.color for region in after}
    appearances = tuple(
        RegionEvent(region.color, region.cells, region.bounding_box)
        for region in after
        if region.color not in before_colors
    )
    disappearances = tuple(
        RegionEvent(region.color, region.cells, region.bounding_box)
        for region in before
        if region.color not in after_colors
    )
    return appearances, disappearances
