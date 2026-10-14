"""Scenario-clustered endpoints and baseline summaries for the prediction benchmark."""
from collections import defaultdict

from research.mechanic_prediction_v1.schema import validate_response


def score(scenarios, keys, responses):
    rows = []
    for scenario in scenarios:
        scenario_id = scenario["scenario_id"]
        key = keys[scenario_id]
        raw = responses.get(scenario_id)
        valid_ids = [record["record_id"] for record in scenario["history"]]
        try:
            parsed = validate_response(raw, valid_ids)
            valid = True
        except (TypeError, ValueError):
            parsed = None
            valid = False
        determined = key["status"] == "determined"
        correct = bool(valid and determined and parsed["status"] == "determined"
                       and parsed["prediction"] == key["prediction"])
        unsupported = bool(valid and not determined and parsed["status"] == "determined")
        supported_refs = set(key["supporting_evidence_ids"])
        refs = set(parsed["evidence_ids"]) if valid else set()
        rows.append({
            "scenario_id": scenario_id, "family": scenario["family"], "split": scenario["split"],
            "truth_status": key["status"], "prediction_accuracy": correct,
            "unsupported_certainty": unsupported,
            "evidence_references_valid": bool(valid and refs <= set(valid_ids)),
            "evidence_references_supported": bool(valid and refs and refs <= supported_refs),
            "valid_output": valid,
        })
    return _aggregate(rows)


def _aggregate(rows):
    groups = defaultdict(list)
    groups["all"] = rows
    for row in rows:
        groups[f"split:{row['split']}"].append(row)
        groups[f"family:{row['family']}"].append(row)
    result = {"analysis_unit": "scenario", "scenario_count": len(rows), "groups": {}}
    for name, values in sorted(groups.items()):
        determinate = [row for row in values if row["truth_status"] == "determined"]
        underdetermined = [row for row in values if row["truth_status"] == "not_determined"]
        result["groups"][name] = {
            "scenario_count": len(values),
            "determinate_count": len(determinate),
            "underdetermined_count": len(underdetermined),
            "prediction_accuracy_on_determinable": _rate(sum(row["prediction_accuracy"] for row in determinate), len(determinate)),
            "unsupported_certainty_on_underdetermined": _rate(sum(row["unsupported_certainty"] for row in underdetermined), len(underdetermined)),
            "evidence_reference_correctness": _rate(sum(row["evidence_references_supported"] for row in values), len(values)),
            "valid_output_rate": _rate(sum(row["valid_output"] for row in values), len(values)),
        }
    result["scenario_rows"] = rows
    return result


def _rate(numerator, denominator):
    return None if not denominator else numerator / denominator


def shortcut_report(scenarios, keys):
    from research.mechanic_prediction_v1.shortcuts import SHORTCUTS, response

    reports = {}
    for shortcut in SHORTCUTS:
        outputs = {scenario["scenario_id"]: response(scenario, shortcut) for scenario in scenarios}
        summary = score(scenarios, keys, outputs)
        rows = {row["scenario_id"]: row for row in summary["scenario_rows"]}
        evaluation_ids = {scenario_id for scenario_id, row in rows.items()
                          if row["split"] == "evaluation" and row["truth_status"] == "determined"}
        wrong = [scenario_id for scenario_id in evaluation_ids if not rows[scenario_id]["prediction_accuracy"]]
        reports[shortcut] = {
            "summary": summary["groups"]["all"],
            "development_summary": summary["groups"]["split:development"],
            "evaluation_summary": summary["groups"]["split:evaluation"],
            "wrong_determinable_scenarios": sorted(wrong),
        }
    strongest = max(SHORTCUTS, key=lambda name: reports[name]["development_summary"]["prediction_accuracy_on_determinable"] or 0)
    return {"shortcuts": reports, "strongest_declared_shortcut": strongest,
            "strongest_wrong_determinable_scenarios": reports[strongest]["wrong_determinable_scenarios"],
            "strongest_selection_split": "development", "strongest_evaluation_summary": reports[strongest]["evaluation_summary"]}