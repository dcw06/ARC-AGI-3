import copy
import inspect
import tempfile
import unittest
import zipfile
from pathlib import Path

from research.mechanic_prediction_v1 import fixtures
from research.mechanic_prediction_v1.build import make_bundle, scripted_rehearsal, write_review_package, _schedule
from research.mechanic_prediction_v1.diagnostics import diagnostic_answer, grounding_answers, score_grounding
from research.mechanic_prediction_v1.independent_keys import derive
from research.mechanic_prediction_v1.oracle import action_key, adjudicate
from research.mechanic_prediction_v1.prompts import (
    CANDIDATE_PROCEDURE, GROUNDING_QUESTIONS, MAX_COMPLETION_TOKENS,
    render_grounding_request, render_request, scripted_reader,
)
from research.mechanic_prediction_v1.replay import verify_bundle, verify_scenario
from research.mechanic_prediction_v1.schema import validate_grounding_response, validate_response
from research.mechanic_prediction_v1.score import score


SCENARIOS = fixtures.all_scenarios()
BY_ID = {scenario["scenario_id"]: scenario for scenario in SCENARIOS}
KEYS = {scenario["scenario_id"]: derive(scenario) for scenario in SCENARIOS}


class FixtureAndKeyTests(unittest.TestCase):
    def test_eight_families_balanced_splits_and_deterministic_generation(self):
        self.assertEqual(len(SCENARIOS), 32)
        self.assertEqual(len({scenario["family"] for scenario in SCENARIOS}), 8)
        self.assertEqual(fixtures.generate(), fixtures.generate())
        for family in fixtures.FAMILIES:
            rows = [scenario for scenario in SCENARIOS if scenario["family"] == family]
            self.assertEqual(sum(row["split"] == "development" for row in rows), 2)
            self.assertEqual(sum(row["split"] == "evaluation" for row in rows), 2)

    def test_trajectories_dispatch_status_and_novel_coordinates(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario["scenario_id"]):
                self.assertTrue(verify_scenario(scenario))
                self.assertTrue(all(scenario["proposed_action"] != record["action"] for record in scenario["history"]))
                for record in scenario["history"]:
                    if record["dispatch_status"] != "acknowledged":
                        self.assertEqual(record["returned_frames"], [])
                        self.assertNotIn("observed_outcome", record)

    def test_failed_and_unknown_dispatches_remain_distinct(self):
        statuses = {record["dispatch_status"] for scenario in SCENARIOS for record in scenario["history"]}
        self.assertEqual(statuses, {"acknowledged", "dispatch_failed", "outcome_unknown"})
        movement = next(s for s in SCENARIOS if s["family"] == "movement_constraints")
        self.assertNotIn(1, movement["history"][0]["available_actions"])
        self.assertEqual(movement["history"][0]["dispatch_status"], "dispatch_failed")
        unknown = next(r for s in SCENARIOS for r in s["history"] if r["dispatch_status"] == "outcome_unknown")
        self.assertIsNone(unknown["returned_signals"])
        self.assertEqual(unknown["returned_frames"], [])

    def test_intermediate_frame_categories_are_not_collapsed(self):
        delayed = next(s for s in SCENARIOS if s["family"] == "delayed_effects")
        transient = next(s for s in SCENARIOS if s["family"] == "transient_effects")
        self.assertEqual(len(delayed["history"][0]["returned_frames"]), 2)
        self.assertEqual(fixtures.visible_outcome(delayed["history"][0]["pre_observation"]["frames"][-1],
                                                  delayed["history"][0]["returned_frames"]), "delayed_change")
        self.assertEqual(fixtures.visible_outcome(transient["history"][0]["pre_observation"]["frames"][-1],
                                                  transient["history"][0]["returned_frames"]), "transient_change")

    def test_independent_keys_agree_and_preserve_uncertainty(self):
        statuses = {"determined": 0, "not_determined": 0}
        for scenario in SCENARIOS:
            oracle = adjudicate(scenario["mechanisms"], scenario["history"], scenario["proposed_action"],
                                scenario["current_observation"])
            key = KEYS[scenario["scenario_id"]]
            for field in ("status", "prediction", "compatible_mechanism_ids", "declared_mechanism_count"):
                self.assertEqual(oracle[field], key[field], (scenario["scenario_id"], field))
            self.assertGreaterEqual(key["declared_mechanism_count"], 2)
            statuses[key["status"]] += 1
        self.assertEqual(statuses, {"determined": 16, "not_determined": 16})
        self.assertTrue(all(key["scope"] == "declared_mechanism_space_only" for key in KEYS.values()))

    def test_later_contradiction_eliminates_an_earlier_explanation(self):
        scenario = next(s for s in SCENARIOS if s["family"] == "contradiction")
        trace = KEYS[scenario["scenario_id"]]["compatibility_trace"]
        self.assertIn("rule_a", trace[0]["remaining"])
        self.assertNotIn("rule_a", trace[1]["remaining"])
        self.assertEqual(trace[1]["remaining"], ["rule_b", "rule_c"])

    def test_shortcuts_cannot_solve_determinate_evaluation_set(self):
        report = make_bundle()["shortcuts"]
        self.assertEqual(report["strongest_selection_split"], "development")
        self.assertEqual(report["strongest_declared_shortcut"], "always_no_change")
        self.assertEqual(report["shortcuts"]["always_no_change"]["development_summary"]["prediction_accuracy_on_determinable"], 1)
        self.assertEqual(report["strongest_evaluation_summary"]["prediction_accuracy_on_determinable"], 0)
        self.assertTrue(report["strongest_wrong_determinable_scenarios"])
        self.assertEqual(len(report["strongest_wrong_determinable_scenarios"]), 8)
        self.assertEqual(report["shortcuts"]["always_unknown"]["summary"]["prediction_accuracy_on_determinable"], 0)


class RequestAndSchemaTests(unittest.TestCase):
    def test_matched_evidence_bytes_and_no_label_leakage(self):
        for scenario in SCENARIOS:
            reference = render_request(scenario, "reference")
            candidate = render_request(scenario, "candidate")
            ref_user = reference["messages"][1]["content"]
            cand_user = candidate["messages"][1]["content"]
            self.assertEqual(ref_user.encode(), cand_user.encode())
            self.assertEqual(candidate["messages"][0]["content"],
                             reference["messages"][0]["content"] + " " + CANDIDATE_PROCEDURE)
            for leaked in (scenario["family"], scenario["scenario_id"], "observed_outcome", "mechanisms", "explanation", scenario["split"]):
                self.assertNotIn(leaked, ref_user)
            self.assertIn("returned_frames", ref_user)
            self.assertIn("available_actions", ref_user)

    def test_grounding_probes_are_separate_and_identity_conservative(self):
        scenario = next(s for s in SCENARIOS if s["family"] == "object_correspondence")
        answers = grounding_answers(scenario)
        self.assertEqual(answers["observed_region_movements"][0]["from_bbox"], [2, 2, 3, 3])
        self.assertEqual(answers["observed_region_movements"][0]["to_bbox"], [3, 2, 4, 3])
        self.assertFalse(answers["exact_proposed_action_coordinate_in_history"])
        request = render_grounding_request(scenario, "marked_region_movement")
        self.assertIn("do not claim persistent object identity", request)
        self.assertNotIn("prediction\":\"", request)
        self.assertTrue(GROUNDING_QUESTIONS)
        validate_grounding_response({"answer": True, "evidence_ids": ["R2"]}, ["R1", "R2"])
        responses = {
            question_id: {"answer": diagnostic_answer(scenario, question_id)[0],
                          "evidence_ids": diagnostic_answer(scenario, question_id)[1]}
            for question_id in GROUNDING_QUESTIONS
        }
        self.assertTrue(all(row["answer_correct"] and row["evidence_references_supported"]
                            for row in score_grounding(scenario, responses).values()))

    def test_scripted_reader_only_parses_rendered_request(self):
        self.assertEqual(list(inspect.signature(scripted_reader).parameters), ["rendered_request"])
        result = scripted_rehearsal(make_bundle())
        self.assertEqual(result["scripted_request_count"], 64)
        self.assertEqual(result["valid_outputs"], 64)
        self.assertIn("rendered request JSON only", result["reader_input_contract"])

    def test_response_validation_rejects_without_repair(self):
        valid_ids = ["R1"]
        valid = {"prediction": "unknown", "evidence_ids": ["R1"], "status": "not_determined"}
        self.assertEqual(validate_response(valid, valid_ids), valid)
        invalid = [
            "not json",
            {**valid, "extra": True},
            {"prediction": "repaired", "evidence_ids": ["R1"], "status": "determined"},
            {"prediction": "unknown", "evidence_ids": ["missing"], "status": "not_determined"},
            {"prediction": "unknown", "evidence_ids": ["R1", "R1"], "status": "not_determined"},
            {"prediction": "unknown", "evidence_ids": ["R1"], "status": "determined"},
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_response(value, valid_ids)

    def test_duplicate_requests_and_caps_are_detected(self):
        with self.assertRaisesRegex(ValueError, "duplicate rendered"):
            _schedule([SCENARIOS[0], SCENARIOS[0]])
        bundle = make_bundle()
        self.assertEqual(bundle["schedule"]["request_count"], 64)
        self.assertEqual(bundle["token_audit"]["completion_token_ceiling"], MAX_COMPLETION_TOKENS)
        self.assertLessEqual(bundle["token_audit"]["maximum_request_utf8_bytes"], 16_384)
        self.assertEqual(bundle["token_audit"]["duplicate_request_count"], 0)
        self.assertEqual(bundle["token_audit"]["token_count_status"], "not_measured; UTF-8 byte measurements are not represented as model tokens")

    def test_scenario_level_scoring_separates_abstention(self):
        bundle = make_bundle()
        responses = {}
        for scenario in SCENARIOS:
            request = render_request(scenario, "reference")
            import json
            rendered = json.dumps(request, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            responses[scenario["scenario_id"]] = scripted_reader(rendered)
        result = score(SCENARIOS, {row["scenario_id"]: row for row in bundle["keys"]["cases"]}, responses)
        overall = result["groups"]["all"]
        self.assertEqual(result["analysis_unit"], "scenario")
        self.assertEqual(overall["determinate_count"], 16)
        self.assertEqual(overall["underdetermined_count"], 16)
        self.assertEqual(overall["prediction_accuracy_on_determinable"], 0)
        self.assertEqual(overall["unsupported_certainty_on_underdetermined"], 0)


class ReplayTests(unittest.TestCase):
    def test_bundle_replays(self):
        self.assertEqual(verify_bundle(make_bundle())["status"], "verified")

    def test_forged_evidence_fails_even_when_manifest_is_updated(self):
        from research.mechanic_prediction_v1.build import sha256

        bundle = make_bundle()
        forged = copy.deepcopy(bundle)
        forged["fixtures"]["cases"][0]["evidence"]["initial_observation"]["frames"][0][0][0] = 8
        forged["manifest"]["sha256"]["fixtures"] = sha256(forged["fixtures"])
        with self.assertRaisesRegex(ValueError, "manifest differs from the frozen"):
            verify_bundle(forged)

    def test_gpu_disabled_review_package_is_reproducible(self):
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "review"
            result = write_review_package(repo_root, output)
            archive_path = Path(result["archive"])
            self.assertTrue(archive_path.is_file())
            with zipfile.ZipFile(archive_path) as archive:
                names = archive.namelist()
                self.assertIn("research/mechanic_prediction_v1/fixtures.py", names)
                self.assertIn("reports/mechanic_prediction_v1/prediction_protocol.md", names)
                manifest = archive.read("reports/mechanic_prediction_v1/gpu_disabled_review/review_manifest.json").decode()
                self.assertIn('"gpu_enabled":false', manifest)
                self.assertIn('"old_authorizations_reused":false', manifest)


if __name__ == "__main__":
    unittest.main()