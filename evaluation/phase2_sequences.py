"""V2 evaluator-only sequence sidecars; the frozen V1 parent remains untouched."""
import base64
import json
from pathlib import Path
import time

from agent.diagnostics import TransitionDiagnosticRecorder, canonical_sha256, replay_bundle
from agent.evidence import PackedFrameSequence

MAX_SEQUENCE_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
MAX_FRAMES = 256


class SequenceRecorder(TransitionDiagnosticRecorder):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sequences = []
        self.sequence_bytes = 0
        self.capture_cpu_seconds = 0.0

    def finish_acknowledged(self, before, after, evidence):
        started = time.process_time()
        item = {"iteration": self._pending.iteration, "transition_id": evidence.transition_id,
                "sequence_sha256": evidence.sequence_sha256, "availability": "omitted_capacity",
                "blob_base64": None, "blob_bytes": 0}
        try:
            # Bound before packing, including per-frame metadata overhead.
            estimate = sum(frame.nbytes for frame in after.frames) + 256 * len(after.frames) + 1024
            if (len(self.sequences) < self.capacity and len(after.frames) <= MAX_FRAMES
                    and estimate <= MAX_SEQUENCE_BYTES
                    and self.sequence_bytes + estimate <= MAX_TOTAL_BYTES):
                sequence = PackedFrameSequence.pack(after.frames)
                if sequence.canonical_sha256 != evidence.sequence_sha256:
                    raise ValueError("sequence hash differs from transition")
                blob = sequence.to_blob()
                item.update(availability="exact", blob_base64=base64.b64encode(blob).decode(), blob_bytes=len(blob))
                self.sequence_bytes += len(blob)
        except Exception as exc:
            item["availability"] = "capture_error"
            self.capture_error("sequence_capture", exc)
        if len(self.sequences) >= self.capacity:
            removed = self.sequences.pop(0)
            self.sequence_bytes -= removed["blob_bytes"]
        self.sequences.append(item)
        self.capture_cpu_seconds += time.process_time() - started
        super().finish_acknowledged(before, after, evidence)

    def sequence_bundle(self):
        core = {"schema_version": 2, "run_id": self.run_id,
                "parent_bundle_sha256": self.bundle()["bundle_sha256"],
                "visibility": "evaluator_only_never_policy", "sequences": self.sequences,
                "retained_blob_bytes": self.sequence_bytes, "capture_cpu_seconds": self.capture_cpu_seconds}
        return {**core, "sha256": canonical_sha256(core)}

    def write(self, path):
        result = super().write(path)
        from scripts.run_e1_whole_run import _write_atomic
        _write_atomic(Path(str(path) + ".sequences"), self.sequence_bundle())
        return result


def validate_sequences(sidecar, bundle):
    replay_bundle(bundle)
    if (sidecar["schema_version"] != 2 or sidecar["run_id"] != bundle["run_id"]
            or sidecar["parent_bundle_sha256"] != bundle["bundle_sha256"]
            or sidecar["visibility"] != "evaluator_only_never_policy"
            or sidecar["sha256"] != canonical_sha256({k:v for k,v in sidecar.items() if k != "sha256"})):
        raise ValueError("sequence sidecar provenance mismatch")
    records = {r["iteration"]:r for r in bundle["records"] if r["transition"]}
    if len(sidecar["sequences"]) != len(records) or len(records) > 256:
        raise ValueError("incomplete sequence inventory")
    seen, resolved, total = set(), set(), 0
    for item in sidecar["sequences"]:
        if item["iteration"] in seen:
            raise ValueError("duplicate sequence iteration")
        seen.add(item["iteration"])
        record = records[item["iteration"]]
        if (item["transition_id"] != record["transition"]["transition_id"]
                or item["sequence_sha256"] != record["transition"]["sequence_sha256"]):
            raise ValueError("sequence references another transition")
        if item["availability"] != "exact":
            if item["availability"] not in {"omitted_capacity", "capture_error"} or item["blob_base64"] is not None or item["blob_bytes"] != 0:
                raise ValueError("invalid omission record")
            continue
        if len(item["blob_base64"]) > (MAX_SEQUENCE_BYTES * 4 // 3 + 4):
            raise ValueError("sequence exceeds byte ceiling")
        blob = base64.b64decode(item["blob_base64"], validate=True)
        total += len(blob)
        if len(blob) != item["blob_bytes"] or len(blob) > MAX_SEQUENCE_BYTES or total > MAX_TOTAL_BYTES:
            raise ValueError("sequence byte accounting mismatch")
        sequence = PackedFrameSequence.from_blob(blob)
        if (sequence.canonical_sha256 != item["sequence_sha256"]
                or len(sequence.frames) != record["transition"]["frame_count"]
                or len(sequence.frames) > MAX_FRAMES
                or sequence.final.content_sha256 != record["post"]["frame_content_sha256"]):
            raise ValueError("sequence content differs from parent transition")
        resolved.add(bundle["run_id"] + "/" + item["transition_id"])
    if total != sidecar["retained_blob_bytes"]:
        raise ValueError("total sequence byte accounting mismatch")
    return resolved
