from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from arcengine import GameState

from agent.evidence import (
    EvidenceAvailability,
    EvidenceStore,
    EvidenceTier,
    FileBlobStore,
    PackedFrameSequence,
    PackedGrid,
)
from agent.controller import DeterministicFallback
from agent.representation import (
    CoordinateTransform,
    ScenePoint,
    TransformReliability,
    build_feature_bundle,
    build_raw_bundle,
    representation_digest,
)
from agent.state import GameRuntimeState, Observation
from evaluation.m0_profile import (
    bounded_profile_projection,
    inventory_artifact_tree,
    observed_gpu_memory_bytes,
    project_execution_seconds,
    validate_profile_record,
)
from scripts.build_m0_profile_notebook import PROFILE_SPECS, build as build_m0_notebook
from scripts.profile_m0_openai import _stream_fragment, _stream_once


def observation(frames: list[list[list[int]]], *, level: int = 0) -> Observation:
    return Observation.from_value(
        {
            "game_id": "opaque-test",
            "frame": frames,
            "state": "NOT_FINISHED",
            "levels_completed": level,
            "win_levels": 2,
            "guid": "guid-evidence",
            "full_reset": False,
            "available_actions": [1, 6],
        }
    )


class FailingBlobStore:
    def put(self, _digest: str, _payload: bytes) -> None:
        raise OSError("disk unavailable")

    def get(self, _digest: str) -> bytes:
        raise OSError("disk unavailable")


class CorruptingBlobStore:
    """Round-trip once, then return damaged persisted evidence."""

    def __init__(self) -> None:
        self.payload = b""
        self.reads = 0

    def put(self, _digest: str, payload: bytes) -> None:
        self.payload = payload

    def get(self, _digest: str) -> bytes:
        self.reads += 1
        if self.reads == 1:
            return self.payload
        return self.payload[:-1] + bytes([self.payload[-1] ^ 0xFF])


class PackingTests(unittest.TestCase):
    def test_uint8_round_trip_and_stable_hash(self) -> None:
        source = np.array([[0, 255], [7, 9]], dtype=np.int64, order="F")
        packed = PackedGrid.pack(source, frame_index=0)
        restored = packed.unpack()
        self.assertEqual(restored.dtype, np.uint8)
        self.assertTrue(restored.flags.c_contiguous)
        np.testing.assert_array_equal(restored, source)
        self.assertEqual(packed, PackedGrid.pack(source.copy(), frame_index=0))

    def test_sequence_blob_round_trip_is_byte_exact_and_ordered(self) -> None:
        first = np.array([[0, 1], [2, 3]], dtype=np.uint8)
        second = np.array([[3, 2], [1, 0]], dtype=np.uint8)
        sequence = PackedFrameSequence.pack([first, second])
        restored = PackedFrameSequence.from_blob(sequence.to_blob())
        self.assertEqual(restored.canonical_sha256, sequence.canonical_sha256)
        self.assertEqual(restored.to_blob(), sequence.to_blob())
        self.assertNotEqual(
            sequence.canonical_sha256,
            PackedFrameSequence.pack([second, first]).canonical_sha256,
        )

    def test_file_blob_store_round_trip(self) -> None:
        sequence = PackedFrameSequence.pack([np.array([[1]], dtype=np.uint8)])
        with tempfile.TemporaryDirectory() as directory:
            store = FileBlobStore(Path(directory) / "evidence")
            blob = sequence.to_blob()
            store.put(sequence.canonical_sha256, blob)
            self.assertEqual(store.get(sequence.canonical_sha256), blob)


class RetentionTests(unittest.TestCase):
    def test_runtime_records_bounded_transition_evidence(self) -> None:
        state = GameRuntimeState(observation([[[0, 0], [0, 0]]]), action_budget_limit=3)
        state.evidence = EvidenceStore(recent_capacity=2, t3_memory_bytes=64)
        state.evidence.capture_t0(state.observation)
        first_id = "transition-0"
        for index in range(3):
            next_observation = observation([[[index + 1, 0], [0, 0]]], level=index)
            state.replace_observation(
                next_observation,
                action_id=1,
                transition_id=first_id if index == 0 else f"transition-{index}",
            )
        self.assertEqual(len(state.evidence.transitions), 2)
        self.assertEqual(state.evidence.t0.observation_hash, state.observation.canonical_hash)
        self.assertEqual(state.evidence.t0.budgets["actions_remaining"], 3)
        self.assertEqual(
            state.evidence.availability(first_id, EvidenceTier.T1),
            EvidenceAvailability.EVICTED_PRESSURE,
        )
        self.assertEqual(
            state.evidence.availability(first_id, EvidenceTier.T3),
            EvidenceAvailability.EVICTED_PRESSURE,
        )

    def test_storage_failure_preserves_t0_and_t1(self) -> None:
        before = observation([[[0, 0], [0, 0]]])
        after = observation([[[0, 1], [0, 0]]])
        store = EvidenceStore(blob_store=FailingBlobStore())
        record = store.record_transition(before, after, action_id=1, transition_id="failed")
        self.assertTrue(store.storage_degraded)
        self.assertIsNotNone(store.t0)
        self.assertEqual(store.t0.observation_hash, after.canonical_hash)
        self.assertEqual(record.availability[EvidenceTier.T1], EvidenceAvailability.EXACT)
        self.assertEqual(
            record.availability[EvidenceTier.T3], EvidenceAvailability.UNAVAILABLE_STORAGE
        )

    def test_storage_failure_preserves_legal_play(self) -> None:
        before = observation([[[0, 0], [0, 0]]])
        after = observation([[[0, 1], [0, 0]]])
        state = GameRuntimeState(before, action_budget_limit=3)
        state.evidence = EvidenceStore(blob_store=FailingBlobStore())
        state.evidence.capture_t0(before)

        state.replace_observation(after, action_id=1, transition_id="degraded")
        decision = DeterministicFallback().propose(state)

        self.assertTrue(state.evidence.storage_degraded)
        self.assertIn(decision.action_id, state.observation.available_actions)
        self.assertEqual(state.evidence.t0.legal_actions, state.observation.available_actions)

    def test_persisted_corruption_is_loss_explicit(self) -> None:
        before = observation([[[0, 0], [0, 0]]])
        after = observation([[[0, 1], [0, 0]]])
        store = EvidenceStore(t3_memory_bytes=0, blob_store=CorruptingBlobStore())
        record = store.record_transition(before, after, action_id=1, transition_id="corrupt")

        self.assertEqual(record.availability[EvidenceTier.T3], EvidenceAvailability.EXACT)
        self.assertIsNone(store.exact_sequence("corrupt"))
        self.assertEqual(
            store.availability("corrupt", EvidenceTier.T3),
            EvidenceAvailability.CORRUPT,
        )

    def test_oversize_optional_sequence_is_explicitly_omitted(self) -> None:
        before = observation([[[0, 0], [0, 0]]])
        after = observation([[[1, 1], [1, 1]], [[2, 2], [2, 2]]])
        store = EvidenceStore(t3_memory_bytes=1)
        record = store.record_transition(before, after, action_id=1, transition_id="large")
        self.assertEqual(record.availability[EvidenceTier.T1], EvidenceAvailability.EXACT)
        self.assertEqual(
            record.availability[EvidenceTier.T3], EvidenceAvailability.OMITTED_CAPACITY
        )
        self.assertIsNone(store.exact_sequence("large"))

    def test_pending_action_and_budget_are_in_t0(self) -> None:
        state = GameRuntimeState(observation([[[0]]]), action_budget_limit=5)
        state.counters.conservative_spent_actions = 2
        state.mark_pending_action("decision-2")
        self.assertEqual(state.evidence.t0.pending_action_reference, "decision-2")
        self.assertEqual(state.evidence.t0.budgets["actions_remaining"], 3)
        state.clear_pending_action()
        self.assertIsNone(state.evidence.t0.pending_action_reference)


class RepresentationTests(unittest.TestCase):
    def test_visible_history_compaction_is_stable_and_loss_explicit(self) -> None:
        store = EvidenceStore(recent_capacity=4)
        current = observation([[[0, 0], [0, 0]]])
        for index in range(3):
            following = observation([[[index + 1, 0], [0, 0]]], level=index)
            store.record_transition(
                current,
                following,
                action_id=1,
                transition_id=f"transition-{index}",
            )
            current = following

        first = build_raw_bundle(current, store, recent_limit=1).policy_payload()
        second = build_raw_bundle(current, store, recent_limit=1).policy_payload()
        compaction = first["history_compaction"]
        self.assertEqual(compaction["policy"], "visible_recent_transitions_v1")
        self.assertEqual(compaction["total_transitions"], 3)
        self.assertEqual(compaction["retained_transitions"], 1)
        self.assertEqual(compaction["omitted_transitions"], 2)
        self.assertRegex(compaction["history_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(first, second)

    def test_visible_history_count_and_hash_survive_evidence_eviction(self) -> None:
        store = EvidenceStore(recent_capacity=2)
        current = observation([[[0]]])
        for index in range(5):
            following = observation([[[index + 1]]], level=index)
            store.record_transition(
                current,
                following,
                action_id=1,
                transition_id=f"evicted-{index}",
            )
            current = following
        payload = build_raw_bundle(current, store, recent_limit=1).policy_payload()
        compaction = payload["history_compaction"]
        self.assertEqual(len(store.transitions), 2)
        self.assertEqual(compaction["total_transitions"], 5)
        self.assertEqual(compaction["retained_transitions"], 1)
        self.assertEqual(compaction["omitted_transitions"], 4)
        self.assertEqual(compaction["history_sha256"], store.transition_history_sha256)

    def test_raw_view_cannot_observe_intermediate_frame_cue(self) -> None:
        animated = observation(
            [
                [[0, 0], [0, 0]],
                [[0, 7], [0, 0]],
                [[0, 0], [0, 0]],
            ]
        )
        final_only = observation([[[0, 0], [0, 0]]])
        raw_animated = build_raw_bundle(animated)
        raw_final = build_raw_bundle(final_only)
        self.assertEqual(raw_animated.policy_payload(), raw_final.policy_payload())
        self.assertFalse(hasattr(raw_animated, "features"))
        self.assertNotIn("hash", str(raw_animated.policy_payload()).lower())

        feature = build_feature_bundle(animated)
        self.assertEqual(feature.features.transient_cells, (ScenePoint(0, 1),))
        self.assertEqual(feature.features.frame_count, 3)
        self.assertNotEqual(representation_digest(raw_animated), representation_digest(feature))

    def test_feature_fixtures_are_deterministic(self) -> None:
        before = np.array([[0, 4, 0], [0, 0, 0]], dtype=np.uint8)
        current = observation([[[0, 0, 4], [0, 0, 0]]])
        first = build_feature_bundle(current, previous_final=before)
        second = build_feature_bundle(current, previous_final=before.copy())
        self.assertEqual(first, second)
        self.assertEqual(representation_digest(first), representation_digest(second))
        self.assertEqual(first.features.palette_added, ())
        self.assertEqual(first.features.palette_removed, ())
        self.assertTrue(
            any(item.color == 4 and item.column_delta == 1 for item in first.features.translations)
        )

        appeared = build_feature_bundle(current, previous_final=np.zeros((2, 3), dtype=np.uint8))
        self.assertEqual(appeared.features.palette_added, (4,))
        self.assertEqual(tuple(event.color for event in appeared.features.appearances), (4,))

    def test_coordinate_convention_and_reliability_gate(self) -> None:
        transform = CoordinateTransform(3, 5, TransformReliability.TESTED)
        self.assertEqual(transform.scene_to_display(ScenePoint(0, 0)).x, 0)
        self.assertEqual(transform.scene_to_display(ScenePoint(2, 4)).x, 63)
        self.assertEqual(transform.scene_to_display(ScenePoint(2, 4)).y, 63)
        tentative = CoordinateTransform(3, 5, TransformReliability.TENTATIVE)
        with self.assertRaisesRegex(ValueError, "not reliable"):
            tentative.scene_to_display(ScenePoint(1, 1))

    def test_observation_names_temporal_frames_and_freezes_them(self) -> None:
        item = observation([[[0, 1], [2, 3]], [[3, 2], [1, 0]]])
        self.assertEqual(len(item.frames), 2)
        self.assertFalse(hasattr(item, "layers"))
        with self.assertRaises(ValueError):
            item.frames[0][0, 0] = 9


class M0ProfileTests(unittest.TestCase):
    def test_generated_profile_notebook_is_offline_and_fail_closed(self) -> None:
        for candidate, spec in PROFILE_SPECS.items():
            with self.subTest(candidate=candidate):
                notebook = build_m0_notebook(candidate)
                code_sources = [
                    cell["source"]
                    for cell in notebook["cells"]
                    if cell["cell_type"] == "code"
                ]
                for index, source in enumerate(code_sources):
                    compile(source, f"m0-{candidate}-cell-{index}", "exec")
                combined = "\n".join(code_sources)
                self.assertIn(
                    "44029b360a9c0073e4b0add10703fc3386dc06bf1314f5913a0dad9564144cbb",
                    combined,
                )
                self.assertIn(
                    "bc016164d15664c52911fcd11f4e26e72a483e248f3cc9b59ae02b3fce09cc6a",
                    combined,
                )
                self.assertIn("digest.update(chunk)", combined)
                self.assertIn("missing_files.issubset({'dataset-metadata.json'})", combined)
                self.assertIn(f"len(model_shards) != {spec['shard_count']}", combined)
                self.assertIn(f"len(all_shards) != {spec['safetensor_count']}", combined)
                self.assertIn(spec["candidate_id"], combined)
                self.assertIn("'--projected-requests', '8800'", combined)
                self.assertNotIn("KAGGLE_API_TOKEN", combined)
                self.assertFalse(notebook["metadata"]["kaggle"]["isInternetEnabled"])
                self.assertEqual(
                    notebook["metadata"]["kaggle"]["accelerator"],
                    "nvidiaRtxPro6000",
                )

    def test_vllm_current_and_legacy_reasoning_stream_fields(self) -> None:
        self.assertEqual(_stream_fragment({"reasoning": "current"}), "current")
        self.assertEqual(
            _stream_fragment({"reasoning_content": "legacy"}),
            "legacy",
        )
        self.assertEqual(_stream_fragment({"content": "answer"}), "answer")
        self.assertEqual(_stream_fragment({"role": "assistant"}), "")

    def test_stream_once_consumes_current_vllm_sse_without_buffering(self) -> None:
        lines = [
            'data: {"choices":[{"delta":{"role":"assistant"}}]}',
            'data: {"choices":[{"delta":{"reasoning":"check"}}]}',
            'data: {"choices":[{"delta":{"content":"OK"}}]}',
            'data: {"choices":[],"usage":{"completion_tokens":3}}',
            'data: [DONE]',
        ]
        test_case = self

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def raise_for_status(self) -> None:
                return None

            def iter_lines(self, *, chunk_size: int, decode_unicode: bool):
                test_case.assertEqual(chunk_size, 1)
                test_case.assertTrue(decode_unicode)
                return iter(lines)

        with patch("scripts.profile_m0_openai.requests.post", return_value=FakeResponse()):
            measurement = _stream_once(
                "http://127.0.0.1:8000/v1/chat/completions",
                model_id="Qwen/Qwen3.8-27B-FP8",
                prompt="test",
                max_tokens=8,
                reasoning="low",
                timeout_seconds=10,
            )
        self.assertEqual(measurement["completion_tokens"], 3)
        self.assertEqual(measurement["token_count_source"], "server_usage")
        self.assertGreaterEqual(measurement["first_token_seconds"], 0)

    def test_artifact_tree_hash_is_stable_and_symlinks_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "weights").mkdir()
            (root / "config.json").write_text("{}\n")
            (root / "weights" / "part.bin").write_bytes(b"weights")
            first = inventory_artifact_tree(root)
            second = inventory_artifact_tree(root)
            self.assertEqual(first, second)
            self.assertEqual(first.file_count, 2)
            self.assertEqual(first.total_bytes, 10)
            (root / "link").symlink_to(root / "config.json")
            with self.assertRaisesRegex(ValueError, "symlink"):
                inventory_artifact_tree(root)

    def test_projection_is_explicit_and_conservative(self) -> None:
        projected = project_execution_seconds(
            cold_load_seconds=400,
            request_latency_seconds=20,
            request_count=110,
            measured_concurrency=10,
            safety_factor=1.25,
        )
        self.assertEqual(projected, 675)
        bounded = project_execution_seconds(
            cold_load_seconds=332.25105318,
            request_latency_seconds=3.4053762199997877,
            request_count=110 * 80,
            measured_concurrency=8,
            safety_factor=1.25,
        )
        self.assertAlmostEqual(bounded, 5014.643355679708)
        with self.assertRaises(ValueError):
            project_execution_seconds(
                cold_load_seconds=1,
                request_latency_seconds=1,
                request_count=1,
                measured_concurrency=1,
                safety_factor=0.9,
            )

    def test_bounded_projection_uses_profile_p95_and_gpu_memory_is_parsed(self) -> None:
        record = {
            "measurements": {
                "cold_load_seconds": 100.0,
                "concurrent_trials": [
                    {"elapsed_seconds": value} for value in (1.0, 1.1, 1.2, 2.0)
                ],
            },
            "projection": {"measured_concurrency": 4},
        }
        self.assertEqual(
            bounded_profile_projection(record, request_count=8, safety_factor=1.25),
            105.0,
        )
        self.assertEqual(
            observed_gpu_memory_bytes(
                "NVIDIA RTX PRO 6000 Blackwell Server Edition, 97887, 580.159.04"
            ),
            97887 * 1024 * 1024,
        )
        with self.assertRaises(ValueError):
            observed_gpu_memory_bytes("unavailable")

    def test_profile_candidate_identity_and_measurements_validate(self) -> None:
        candidate = {
            "candidate_id": "candidate",
            "model_id": "owner/model",
            "revision": "a" * 40,
            "engine": "vllm==0.19.0",
        }
        profile = {
            "candidate_id": "candidate",
            "model_id": "owner/model",
            "model_revision": "a" * 40,
            "engine": "vllm==0.19.0",
            "measurements": {
                "cold_load_seconds": 10.0,
                "first_token_seconds": 1.0,
                "decode_tokens_per_second": 50.0,
                "cancellation_seconds": 0.5,
                "peak_vram_bytes": 1,
                "peak_ram_bytes": 1,
                "offline_artifact_bytes": 10,
            },
            "artifact": {"tree_sha256": "b" * 64},
            "schema_version": 1,
        }
        self.assertEqual(validate_profile_record(profile, candidate), ())
        profile["model_revision"] = "c" * 40
        self.assertIn("model_revision", " ".join(validate_profile_record(profile, candidate)))


if __name__ == "__main__":
    unittest.main()
