"""Second, deliberately separate derivation of fixture answers and support IDs."""

PREDICTIONS = {"no_change", "changed", "delayed_change", "transient_change"}


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


def _rule_prediction(hypothesis, action, observation):
    data = action["action_data"]
    signals = observation.get("signals", {})
    target = signals.get("target")
    coordinates = [data.get("x"), data.get("y")] if set(data) == {"x", "y"} else None
    for rule in hypothesis["rules"]:
        if rule["action_id"] is not None and rule["action_id"] != action["action_id"]:
            continue
        if rule["mode"] != "any" and rule["mode"] != signals.get("mode"):
            continue
        relation = rule["coordinate_relation"]
        if relation == "none" and coordinates is not None:
            continue
        if relation == "target" and coordinates != target:
            continue
        if relation == "adjacent" and (coordinates is None or target is None
                or abs(coordinates[0] - target[0]) + abs(coordinates[1] - target[1]) != 1):
            continue
        if relation not in {"any", "none", "target", "adjacent"}:
            raise ValueError("independent key: unknown coordinate relation")
        if rule["outcome"] not in PREDICTIONS:
            raise ValueError("independent key: unknown outcome")
        return rule["outcome"]
    if hypothesis["default_outcome"] not in PREDICTIONS:
        raise ValueError("independent key: unknown default outcome")
    return hypothesis["default_outcome"]


def derive(scenario):
    mechanisms = scenario["mechanisms"]
    viable = list(mechanisms)
    trace = []
    support = []
    for record in scenario["history"]:
        if record["dispatch_status"] != "acknowledged":
            trace.append({"record_id": record["record_id"], "remaining": [m["hypothesis_id"] for m in viable]})
            continue
        observed = _outcome(record)
        viable = [m for m in viable if _rule_prediction(m, record["action"], record["pre_observation"]) == observed]
        support.append(record["record_id"])
        trace.append({"record_id": record["record_id"], "observed": observed,
                  "remaining": [m["hypothesis_id"] for m in viable]})
    if not viable:
        raise ValueError("independent derivation found no compatible mechanism")
    predictions = {_rule_prediction(m, scenario["proposed_action"], scenario["current_observation"])
                   for m in viable}
    determined = len(predictions) == 1
    return {
        "scenario_id": scenario["scenario_id"],
        "status": "determined" if determined else "not_determined",
        "prediction": next(iter(predictions)) if determined else None,
        "compatible_mechanism_ids": [m["hypothesis_id"] for m in viable],
        "declared_mechanism_count": len(mechanisms),
        "supporting_evidence_ids": support,
        "compatibility_trace": trace,
        "scope": "declared_mechanism_space_only",
    }