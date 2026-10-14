"""Second, deliberately separate derivation of fixture answers and support IDs."""
import json


def _key(action, observation):
    serialized_action = json.dumps(action, sort_keys=True, separators=(",", ":"))
    signals = observation.get("signals", {})
    if not signals:
        return serialized_action
    return json.dumps({"action": action, "signals": signals}, sort_keys=True, separators=(",", ":"))


def _outcome(record):
    before = record["pre_observation"]["frames"][-1]
    frames = record["returned_frames"]
    differences = [frame != before for frame in frames]
    if not any(differences):
        return "no_change"
    if not differences[0] and any(differences[1:]):
        return "delayed_change"
    if not differences[-1]:
        return "transient_change"
    return "changed"


def derive(scenario):
    mechanisms = scenario["mechanisms"]
    viable = list(mechanisms)
    trace = []
    support = []
    for record in scenario["history"]:
        if record["dispatch_status"] != "acknowledged":
            trace.append({"record_id": record["record_id"], "remaining": [m["mechanism_id"] for m in viable]})
            continue
        observed = _outcome(record)
        query = _key(record["action"], record["pre_observation"])
        viable = [m for m in viable if m["outcomes"].get(query) == observed]
        support.append(record["record_id"])
        trace.append({"record_id": record["record_id"], "observed": observed,
                      "remaining": [m["mechanism_id"] for m in viable]})
    if not viable:
        raise ValueError("independent derivation found no compatible mechanism")
    proposal_key = _key(scenario["proposed_action"], scenario["current_observation"])
    predictions = {m["outcomes"][proposal_key] for m in viable}
    determined = len(predictions) == 1
    return {
        "scenario_id": scenario["scenario_id"],
        "status": "determined" if determined else "not_determined",
        "prediction": next(iter(predictions)) if determined else None,
        "compatible_mechanism_ids": [m["mechanism_id"] for m in viable],
        "declared_mechanism_count": len(mechanisms),
        "supporting_evidence_ids": support,
        "compatibility_trace": trace,
        "scope": "declared_mechanism_space_only",
    }