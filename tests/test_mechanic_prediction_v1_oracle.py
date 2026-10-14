import unittest

from research.mechanic_prediction_v1.oracle import action_key, adjudicate


def action(x, y):
    return {"action_id": 6, "action_data": {"x": x, "y": y}}


class OracleTests(unittest.TestCase):
    def test_ambiguous_history_does_not_reveal_hidden_truth(self):
        observed = action(2, 2)
        proposed = action(3, 2)
        mechanisms = [
            {"mechanism_id": "left_rule", "outcomes": {
                action_key(observed): {"changed": False},
                action_key(proposed): {"changed": True, "cell": [3, 2]},
            }},
            {"mechanism_id": "right_rule", "outcomes": {
                action_key(observed): {"changed": False},
                action_key(proposed): {"changed": False},
            }},
        ]
        result = adjudicate(mechanisms, [{
            "action": observed, "status": "acknowledged", "observed_outcome": {"changed": False},
        }], proposed)
        self.assertEqual(result["status"], "not_determined")
        self.assertIsNone(result["prediction"])
        self.assertEqual(result["compatible_mechanism_ids"], ["left_rule", "right_rule"])

    def test_failed_and_unknown_dispatches_constrain_nothing(self):
        proposed = action(3, 2)
        mechanisms = [
            {"mechanism_id": "a", "outcomes": {action_key(proposed): {"changed": True}}},
            {"mechanism_id": "b", "outcomes": {action_key(proposed): {"changed": True}}},
        ]
        history = [
            {"action": action(1, 2), "status": "dispatch_failed"},
            {"action": action(2, 2), "status": "outcome_unknown"},
        ]
        self.assertEqual(adjudicate(mechanisms, history, proposed)["status"], "determined")

    def test_exact_action_coordinate_pair_must_be_unobserved(self):
        proposed = action(3, 2)
        mechanisms = [
            {"mechanism_id": name, "outcomes": {action_key(proposed): {"changed": False}}}
            for name in ("a", "b")
        ]
        with self.assertRaisesRegex(ValueError, "not novel"):
            adjudicate(mechanisms, [{"action": proposed, "status": "dispatch_failed"}], proposed)

    def test_incompatible_history_is_not_silently_called_unknown(self):
        observed = action(2, 2)
        proposed = action(3, 2)
        mechanisms = [
            {"mechanism_id": name, "outcomes": {
                action_key(observed): {"changed": False},
                action_key(proposed): {"changed": False},
            }} for name in ("a", "b")
        ]
        with self.assertRaisesRegex(ValueError, "no declared mechanism"):
            adjudicate(mechanisms, [{
                "action": observed, "status": "acknowledged", "observed_outcome": {"changed": True},
            }], proposed)


if __name__ == "__main__":
    unittest.main()