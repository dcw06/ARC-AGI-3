import unittest

from research.mechanic_prediction_v1.oracle import adjudicate


def action(x, y):
    return {"action_id": 6, "action_data": {"x": x, "y": y}}


def hypothesis(hypothesis_id, rules=(), default="no_change"):
    return {"hypothesis_id": hypothesis_id, "explanation": "Declared test rule.",
            "rules": list(rules), "default_outcome": default}


def rule(coordinate_relation, outcome, mode="any"):
    return {"action_id": 6, "mode": mode, "coordinate_relation": coordinate_relation,
            "outcome": outcome}


class OracleTests(unittest.TestCase):
    def test_public_rules_determine_compatibility_and_preserve_ambiguity(self):
        observed = action(2, 2)
        proposed = action(3, 2)
        observation = {"signals": {"mode": "active", "target": [2, 2]}}
        hypotheses = [hypothesis("H1", [rule("target", "no_change"), rule("adjacent", "changed")]),
                      hypothesis("H2", [rule("target", "no_change")])]
        result = adjudicate(hypotheses, [{
            "action": observed, "dispatch_status": "acknowledged", "pre_observation": observation,
            "observed_outcome": "no_change",
        }], proposed, observation)
        self.assertEqual(result["status"], "not_determined")
        self.assertIsNone(result["prediction"])
        self.assertEqual(result["compatible_mechanism_ids"], ["H1", "H2"])

    def test_failed_and_unknown_dispatches_constrain_nothing(self):
        proposed = action(3, 2)
        hypotheses = [hypothesis("H1", [rule("adjacent", "changed")]),
                      hypothesis("H2", [rule("adjacent", "changed")])]
        history = [
            {"action": action(1, 2), "dispatch_status": "dispatch_failed"},
            {"action": action(2, 2), "dispatch_status": "outcome_unknown"},
        ]
        observation = {"signals": {"mode": "active", "target": [2, 2]}}
        result = adjudicate(hypotheses, history, proposed, observation)
        self.assertEqual((result["status"], result["prediction"]), ("determined", "changed"))

    def test_exact_action_coordinate_pair_must_be_unobserved(self):
        proposed = action(3, 2)
        hypotheses = [hypothesis("H1"), hypothesis("H2")]
        observation = {"signals": {"mode": "active", "target": [2, 2]}}
        with self.assertRaisesRegex(ValueError, "not novel"):
            adjudicate(hypotheses, [{"action": proposed, "dispatch_status": "dispatch_failed",
                                     "pre_observation": observation}], proposed, observation)

    def test_incompatible_history_is_not_silently_called_unknown(self):
        observed = action(2, 2)
        proposed = action(3, 2)
        observation = {"signals": {"mode": "active", "target": [2, 2]}}
        hypotheses = [hypothesis("H1", [rule("target", "no_change")]),
                      hypothesis("H2", [rule("target", "changed")])]
        with self.assertRaisesRegex(ValueError, "no declared mechanism"):
            adjudicate(hypotheses, [{
                "action": observed, "dispatch_status": "acknowledged", "pre_observation": observation,
                "observed_outcome": "delayed_change",
            }], proposed, observation)


if __name__ == "__main__":
    unittest.main()