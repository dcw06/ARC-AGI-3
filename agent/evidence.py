"""Bounded, loss-explicit evidence retention for Phase 0F."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections import OrderedDict, deque
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Protocol, Sequence

import numpy as np


GRID_HASH_VERSION = "arc3-grid-v1"
SEQUENCE_HASH_VERSION = "arc3-frame-sequence-v1"
TRANSITION_HISTORY_HASH_VERSION = "arc3-transition-history-v1"


class EvidenceAvailability(str, Enum):
    EXACT = "exact"
    SUMMARIZED = "summarized"
    OMITTED_CAPACITY = "omitted_capacity"
    EVICTED_PRESSURE = "evicted_pressure"
    UNAVAILABLE_STORAGE = "unavailable_storage"
    CORRUPT = "corrupt"


class EvidenceTier(str, Enum):
    T0 = "T0"
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"


class BlobStore(Protocol):
    def put(self, digest: str, payload: bytes) -> None: ...

    def get(self, digest: str) -> bytes: ...


class FileBlobStore:
    """Atomic content-addressed storage rooted at one explicit directory."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, digest: str) -> Path:
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise ValueError("blob digest must be lowercase sha256")
        return self.root / digest[:2] / digest[2:]

    def put(self, digest: str, payload: bytes) -> None:
        target = self._path(digest)
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=".evidence-", dir=target.parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def get(self, digest: str) -> bytes:
        return self._path(digest).read_bytes()


@dataclass(frozen=True, slots=True)
class PackedGrid:
    """Immutable canonical C-order uint8 grid."""

    shape: tuple[int, int]
    frame_index: int
    payload: bytes
    content_sha256: str
    canonical_sha256: str

    @classmethod
    def pack(cls, value: Any, *, frame_index: int) -> "PackedGrid":
        source = np.asarray(value)
        if source.ndim != 2:
            raise ValueError("retained grids must be two-dimensional")
        if not np.issubdtype(source.dtype, np.integer):
            raise ValueError("retained grids must contain integers")
        if source.size and (int(source.min()) < 0 or int(source.max()) > 255):
            raise ValueError("retained grids must fit uint8 without loss")
        packed = np.ascontiguousarray(source, dtype=np.uint8)
        payload = packed.tobytes(order="C")
        content_header = {
            "version": GRID_HASH_VERSION,
            "shape": list(packed.shape),
            "dtype": "uint8",
            "byte_order": "not_applicable",
            "order": "C",
        }
        content_prefix = json.dumps(content_header, sort_keys=True, separators=(",", ":")).encode()
        content_hash = hashlib.sha256(content_prefix + b"\0" + payload).hexdigest()
        canonical_header = {**content_header, "frame_index": frame_index}
        canonical_prefix = json.dumps(canonical_header, sort_keys=True, separators=(",", ":")).encode()
        canonical_hash = hashlib.sha256(canonical_prefix + b"\0" + payload).hexdigest()
        return cls(tuple(int(x) for x in packed.shape), frame_index, payload, content_hash, canonical_hash)

    def unpack(self) -> np.ndarray:
        expected = int(np.prod(self.shape, dtype=np.int64))
        if len(self.payload) != expected:
            raise ValueError("packed grid payload is corrupt")
        result = np.frombuffer(self.payload, dtype=np.uint8).reshape(self.shape).copy(order="C")
        return result


@dataclass(frozen=True, slots=True)
class PackedFrameSequence:
    frames: tuple[PackedGrid, ...]
    canonical_sha256: str
    byte_size: int

    @classmethod
    def pack(cls, values: Sequence[Any]) -> "PackedFrameSequence":
        if not values:
            raise ValueError("an evidence sequence requires at least one frame")
        frames = tuple(PackedGrid.pack(value, frame_index=index) for index, value in enumerate(values))
        digest = hashlib.sha256((SEQUENCE_HASH_VERSION + "\0").encode())
        for frame in frames:
            digest.update(bytes.fromhex(frame.canonical_sha256))
        return cls(frames, digest.hexdigest(), sum(len(frame.payload) for frame in frames))

    @property
    def final(self) -> PackedGrid:
        return self.frames[-1]

    def to_blob(self) -> bytes:
        header = {
            "version": SEQUENCE_HASH_VERSION,
            "frames": [
                {"shape": list(frame.shape), "frame_index": frame.frame_index, "bytes": len(frame.payload)}
                for frame in self.frames
            ],
        }
        encoded = json.dumps(header, sort_keys=True, separators=(",", ":")).encode()
        return len(encoded).to_bytes(8, "big") + encoded + b"".join(frame.payload for frame in self.frames)

    @classmethod
    def from_blob(cls, blob: bytes) -> "PackedFrameSequence":
        if len(blob) < 8:
            raise ValueError("frame-sequence blob is corrupt")
        header_size = int.from_bytes(blob[:8], "big")
        try:
            header = json.loads(blob[8 : 8 + header_size])
        except Exception as exc:
            raise ValueError("frame-sequence header is corrupt") from exc
        if header.get("version") != SEQUENCE_HASH_VERSION:
            raise ValueError("unknown frame-sequence version")
        cursor = 8 + header_size
        values: list[np.ndarray] = []
        for expected_index, item in enumerate(header.get("frames", [])):
            if item.get("frame_index") != expected_index:
                raise ValueError("frame order is corrupt")
            size = int(item["bytes"])
            shape = tuple(int(x) for x in item["shape"])
            payload = blob[cursor : cursor + size]
            if len(payload) != size:
                raise ValueError("frame payload is truncated")
            values.append(np.frombuffer(payload, dtype=np.uint8).reshape(shape).copy(order="C"))
            cursor += size
        if cursor != len(blob) or not values:
            raise ValueError("frame-sequence blob has trailing or missing data")
        return cls.pack(values)


@dataclass(frozen=True, slots=True)
class CompactDelta:
    changed_cells: int
    bounding_box: tuple[int, int, int, int] | None
    palette_added: tuple[int, ...]
    palette_removed: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class T0Snapshot:
    final_frame: PackedGrid
    state: str
    levels_completed: int
    win_levels: int
    legal_actions: tuple[int, ...]
    budgets: Mapping[str, int]
    pending_action_reference: str | None
    observation_hash: str


@dataclass(frozen=True, slots=True)
class TransitionEvidence:
    transition_id: str
    action_id: int
    action_data: Mapping[str, Any]
    pre_state_hash: str
    post_state_hash: str
    prior_final_frame: PackedGrid
    final_frame: PackedGrid
    sequence_sha256: str
    frame_count: int
    distinct_frame_count: int
    delta: CompactDelta
    availability: Mapping[EvidenceTier, EvidenceAvailability]


@dataclass(frozen=True, slots=True)
class EvidenceLossEvent:
    transition_id: str
    tier: EvidenceTier
    availability: EvidenceAvailability


def _compact_delta(before: PackedGrid, after: PackedGrid) -> CompactDelta:
    if before.shape != after.shape:
        return CompactDelta(-1, None, (), ())
    left, right = before.unpack(), after.unpack()
    changed = left != right
    locations = np.argwhere(changed)
    bbox = None
    if locations.size:
        top, left_col = locations.min(axis=0)
        bottom, right_col = locations.max(axis=0)
        bbox = (int(top), int(left_col), int(bottom), int(right_col))
    before_palette = set(int(x) for x in np.unique(left))
    after_palette = set(int(x) for x in np.unique(right))
    return CompactDelta(
        int(changed.sum()),
        bbox,
        tuple(sorted(after_palette - before_palette)),
        tuple(sorted(before_palette - after_palette)),
    )


class EvidenceStore:
    """Bounded RAM evidence with explicit degradation and optional persistence."""

    def __init__(
        self,
        *,
        recent_capacity: int = 16,
        t3_memory_bytes: int = 4 * 1024 * 1024,
        blob_store: BlobStore | None = None,
    ) -> None:
        if recent_capacity < 1 or t3_memory_bytes < 0:
            raise ValueError("evidence capacities must be non-negative and non-zero where required")
        self.recent_capacity = recent_capacity
        self.t3_memory_bytes = t3_memory_bytes
        self.blob_store = blob_store
        self.t0: T0Snapshot | None = None
        self.storage_degraded = False
        self._records: deque[TransitionEvidence] = deque()
        self._t3: OrderedDict[str, PackedFrameSequence] = OrderedDict()
        self._t3_bytes = 0
        self._loss_events: deque[EvidenceLossEvent] = deque(maxlen=recent_capacity * 4)
        self._sequence_blob_refs: dict[str, str] = {}
        self._transition_count = 0
        self._transition_history_sha256 = hashlib.sha256(
            TRANSITION_HISTORY_HASH_VERSION.encode()
        ).hexdigest()

    @property
    def transitions(self) -> tuple[TransitionEvidence, ...]:
        return tuple(self._records)

    @property
    def loss_events(self) -> tuple[EvidenceLossEvent, ...]:
        return tuple(self._loss_events)

    @property
    def memory_bytes(self) -> int:
        t1 = sum(
            len(record.prior_final_frame.payload) + len(record.final_frame.payload)
            for record in self._records
        )
        return t1 + self._t3_bytes + (len(self.t0.final_frame.payload) if self.t0 else 0)

    @property
    def transition_count(self) -> int:
        return self._transition_count

    @property
    def transition_history_sha256(self) -> str | None:
        return self._transition_history_sha256 if self._transition_count else None

    def capture_t0(
        self,
        observation: Any,
        *,
        budgets: Mapping[str, int] | None = None,
        pending_action_reference: str | None = None,
    ) -> T0Snapshot:
        final_frame = PackedGrid.pack(observation.latest_frame, frame_index=0)
        snapshot = T0Snapshot(
            final_frame=final_frame,
            state=str(observation.state.value),
            levels_completed=int(observation.levels_completed),
            win_levels=int(observation.win_levels),
            legal_actions=tuple(int(x) for x in observation.available_actions),
            budgets=MappingProxyType({key: int(value) for key, value in (budgets or {}).items()}),
            pending_action_reference=pending_action_reference,
            observation_hash=str(observation.canonical_hash),
        )
        self.t0 = snapshot
        return snapshot

    def record_transition(
        self,
        before: Any,
        after: Any,
        *,
        action_id: int,
        action_data: Mapping[str, Any] | None = None,
        transition_id: str | None = None,
        budgets: Mapping[str, int] | None = None,
    ) -> TransitionEvidence:
        # T0 is committed before any optional storage operation.
        current = self.capture_t0(after, budgets=budgets)
        before_sequence = PackedFrameSequence.pack(before.frames)
        sequence = PackedFrameSequence.pack(after.frames)
        identifier = transition_id or hashlib.sha256(
            f"{before.canonical_hash}:{after.canonical_hash}:{action_id}".encode()
        ).hexdigest()[:24]
        availability = {
            EvidenceTier.T0: EvidenceAvailability.EXACT,
            EvidenceTier.T1: EvidenceAvailability.EXACT,
            EvidenceTier.T2: EvidenceAvailability.SUMMARIZED,
            EvidenceTier.T3: EvidenceAvailability.EXACT,
        }

        blob = sequence.to_blob()
        persisted = False
        if self.blob_store is not None:
            try:
                self.blob_store.put(sequence.canonical_sha256, blob)
                if self.blob_store.get(sequence.canonical_sha256) != blob:
                    raise IOError("content-addressed evidence did not round-trip")
                self._sequence_blob_refs[identifier] = sequence.canonical_sha256
                persisted = True
            except Exception:
                self.storage_degraded = True
                availability[EvidenceTier.T3] = EvidenceAvailability.UNAVAILABLE_STORAGE

        if sequence.byte_size > self.t3_memory_bytes and not persisted and self.blob_store is None:
            availability[EvidenceTier.T3] = EvidenceAvailability.OMITTED_CAPACITY
        elif availability[EvidenceTier.T3] is EvidenceAvailability.EXACT:
            if sequence.byte_size <= self.t3_memory_bytes:
                self._retain_t3(identifier, sequence)

        record = TransitionEvidence(
            transition_id=identifier,
            action_id=int(action_id),
            action_data=MappingProxyType(dict(action_data or {})),
            pre_state_hash=str(before.canonical_hash),
            post_state_hash=current.observation_hash,
            prior_final_frame=before_sequence.final,
            final_frame=sequence.final,
            sequence_sha256=sequence.canonical_sha256,
            frame_count=len(sequence.frames),
            distinct_frame_count=len({frame.content_sha256 for frame in sequence.frames}),
            delta=_compact_delta(before_sequence.final, sequence.final),
            availability=MappingProxyType(availability),
        )
        history_payload = json.dumps(
            {
                "action_id": record.action_id,
                "action_data": dict(record.action_data),
                "pre_state_hash": record.pre_state_hash,
                "post_state_hash": record.post_state_hash,
                "prior_frame_sha256": record.prior_final_frame.content_sha256,
                "final_frame_sha256": record.final_frame.content_sha256,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        self._transition_history_sha256 = hashlib.sha256(
            bytes.fromhex(self._transition_history_sha256) + history_payload
        ).hexdigest()
        self._transition_count += 1
        self._append_record(record)
        return record

    def exact_sequence(self, transition_id: str) -> PackedFrameSequence | None:
        if transition_id in self._t3:
            return self._t3[transition_id]
        digest = self._sequence_blob_refs.get(transition_id)
        if digest and self.blob_store is not None:
            try:
                sequence = PackedFrameSequence.from_blob(self.blob_store.get(digest))
                if sequence.canonical_sha256 != digest:
                    raise ValueError("stored sequence does not match its content address")
                return sequence
            except Exception:
                self.storage_degraded = True
                self._loss_events.append(
                    EvidenceLossEvent(transition_id, EvidenceTier.T3, EvidenceAvailability.CORRUPT)
                )
        return None

    def availability(self, transition_id: str, tier: EvidenceTier) -> EvidenceAvailability | None:
        for event in reversed(self._loss_events):
            if event.transition_id == transition_id and event.tier is tier:
                return event.availability
        for record in self._records:
            if record.transition_id == transition_id:
                return record.availability[tier]
        return None

    def _retain_t3(self, transition_id: str, sequence: PackedFrameSequence) -> None:
        while self._t3 and self._t3_bytes + sequence.byte_size > self.t3_memory_bytes:
            evicted_id, evicted = self._t3.popitem(last=False)
            self._t3_bytes -= evicted.byte_size
            if evicted_id not in self._sequence_blob_refs:
                self._loss_events.append(
                    EvidenceLossEvent(evicted_id, EvidenceTier.T3, EvidenceAvailability.EVICTED_PRESSURE)
                )
        if sequence.byte_size <= self.t3_memory_bytes:
            self._t3[transition_id] = sequence
            self._t3_bytes += sequence.byte_size

    def _append_record(self, record: TransitionEvidence) -> None:
        if len(self._records) >= self.recent_capacity:
            evicted = self._records.popleft()
            for tier in (EvidenceTier.T1, EvidenceTier.T2):
                self._loss_events.append(
                    EvidenceLossEvent(evicted.transition_id, tier, EvidenceAvailability.EVICTED_PRESSURE)
                )
            sequence = self._t3.pop(evicted.transition_id, None)
            if sequence is not None:
                self._t3_bytes -= sequence.byte_size
            # The live index is bounded together with transition metadata.
            # Persisted content may remain deduplicated on disk, but it cannot
            # be silently presented as addressable transition evidence.
            self._sequence_blob_refs.pop(evicted.transition_id, None)
            self._loss_events.append(
                EvidenceLossEvent(
                    evicted.transition_id, EvidenceTier.T3, EvidenceAvailability.EVICTED_PRESSURE
                )
            )
        self._records.append(record)
