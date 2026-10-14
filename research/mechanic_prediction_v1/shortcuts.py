"""Deterministic shortcut baselines computed from visible trajectory evidence."""
from research.mechanic_prediction_v1.fixtures import visible_outcome


SHORTCUTS = (
    "repeat_last_observed_outcome", "ignore_coordinates", "assume_available_means_effective",
    "failed_dispatch_means_no_change", "final_frame_only", "always_no_change",
    "always_unknown", "most_recent_rule_everywhere",
)


def _acknowledged(scenario):
    return [record for record in scenario["history"]
            if record["dispatch_status"] == "acknowledged"]


def _last_category(scenario):
    records = _acknowledged(scenario)
    if not records:
        return "no_change"
    record = records[-1]
    return visible_outcome(record["pre_observation"]["frames"][-1], record["returned_frames"])


def _category(scenario, name):
    records = _acknowledged(scenario)
    proposed = scenario["proposed_action"]
    if name == "always_no_change":
        return "no_change"
    if name == "always_unknown":
        return "unknown"
    if name == "repeat_last_observed_outcome":
        return _last_category(scenario)
    if name == "most_recent_rule_everywhere":
        return _last_category(scenario)
    if name == "ignore_coordinates":
        matching = [record for record in records if record["action"]["action_id"] == proposed["action_id"]]
        if not matching:
            return "no_change"
        record = matching[-1]
        return visible_outcome(record["pre_observation"]["frames"][-1], record["returned_frames"])
    if name == "assume_available_means_effective":
        return "changed" if proposed["action_id"] in scenario["current_available_actions"] else "no_change"
    if name == "failed_dispatch_means_no_change":
        if any(record["dispatch_status"] == "dispatch_failed"
               and record["action"]["action_id"] == proposed["action_id"] for record in scenario["history"]):
            return "no_change"
        return _last_category(scenario)
    if name == "final_frame_only":
        if not records:
            return "no_change"
        record = records[-1]
        before = record["pre_observation"]["frames"][-1]
        final = record["returned_frames"][-1]
        return "changed" if final != before else "no_change"
    raise ValueError("unknown shortcut baseline")


def response(scenario, shortcut):
    if shortcut not in SHORTCUTS:
        raise ValueError("unknown shortcut baseline")
    category = _category(scenario, shortcut)
    records = _acknowledged(scenario)
    evidence_ids = [records[-1]["record_id"]] if records else [scenario["history"][-1]["record_id"]]
    return {"prediction": category, "evidence_ids": evidence_ids,
            "status": "not_determined" if category == "unknown" else "determined"}