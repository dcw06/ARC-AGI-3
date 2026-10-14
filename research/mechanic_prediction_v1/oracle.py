"""Finite, declared-mechanism adjudication for novel-action predictions."""
import json


STATUSES = {"acknowledged", "dispatch_failed", "outcome_unknown"}
PREDICTIONS = {"no_change", "changed", "delayed_change", "transient_change"}


def action_key(action):
    if (type(action) is not dict or set(action) != {"action_id", "action_data"}
            or type(action["action_id"]) is not int or type(action["action_data"]) is not dict):
        raise ValueError("invalid action")
    return json.dumps(action, sort_keys=True, separators=(",", ":"))


def query_key(action, observation=None):
    key = action_key(action)
    signals = observation.get("signals", {}) if type(observation) is dict else {}
    if not signals:
        return key
    return json.dumps({"action": json.loads(key), "signals": signals}, sort_keys=True, separators=(",", ":"))


def _status(record):
    return record.get("dispatch_status", record.get("status"))


def predict_from_rules(mechanism, action, observation):
    """Apply a fully visible, ordered rule list to one action and observation."""
    data = action["action_data"]
    signals = observation.get("signals", {})
    target = signals.get("target")
    coordinates = [data.get("x"), data.get("y")] if set(data) == {"x", "y"} else None
    for rule in mechanism["rules"]:
        if rule["action_id"] is not None and rule["action_id"] != action["action_id"]:
            continue
        if rule["mode"] != "any" and rule["mode"] != signals.get("mode"):
            continue
        relation = rule["coordinate_relation"]
        if relation == "none" and coordinates is not None:
            continue
        if relation == "target" and coordinates != target:
            continue
        if relation == "adjacent":
            if coordinates is None or target is None or abs(coordinates[0] - target[0]) + abs(coordinates[1] - target[1]) != 1:
                continue
        if relation not in {"any", "none", "target", "adjacent"}:
            raise ValueError("unknown declared coordinate relation")
        if rule["outcome"] not in PREDICTIONS:
            raise ValueError("unknown declared outcome category")
        return rule["outcome"]
    default = mechanism["default_outcome"]
    if default not in PREDICTIONS:
        raise ValueError("unknown declared default outcome")
    return default


def adjudicate(mechanisms, history, proposed_action, proposed_observation=None):
    """Return the evidence-supported prediction over the declared mechanism set.

    Each mechanism is an executable rule set shown to both model arms. Failed or
    unobserved dispatches constrain no mechanism. A repeated proposed action/state
    pair is rejected so the scored prediction cannot be answered by exact recall.
    """
    if type(mechanisms) is not list or len(mechanisms) < 2:
        raise ValueError("at least two declared mechanisms are required")
    proposal_key = query_key(proposed_action, proposed_observation)
    history_keys = set()
    for record in history:
        status = _status(record) if type(record) is dict else None
        if type(record) is not dict or status not in STATUSES:
            raise ValueError("invalid history dispatch status")
        key = query_key(record.get("action"), record.get("pre_observation"))
        history_keys.add(key)
        if status == "acknowledged":
            if "observed_outcome" not in record:
                raise ValueError("acknowledged records need an observed outcome")
        elif "observed_outcome" in record:
            raise ValueError("unobserved dispatch cannot carry an observed outcome")
    if proposal_key in history_keys:
        raise ValueError("proposed action-coordinate and state pair is not novel")

    compatible = []
    for mechanism in mechanisms:
        required = {"hypothesis_id", "explanation", "rules", "default_outcome"}
        if (type(mechanism) is not dict or set(mechanism) != required
                or type(mechanism["hypothesis_id"]) is not str
                or type(mechanism["explanation"]) is not str
                or type(mechanism["rules"]) is not list):
            raise ValueError("invalid declared mechanism")
        consistent = True
        for record in history:
            if _status(record) != "acknowledged":
                continue
            if predict_from_rules(mechanism, record["action"], record["pre_observation"]) != record["observed_outcome"]:
                consistent = False
                break
        if consistent:
            compatible.append(mechanism)
    if not compatible:
        raise ValueError("no declared mechanism is consistent with the supplied evidence")
    predictions = {json.dumps(predict_from_rules(m, proposed_action, proposed_observation or {}),
                              sort_keys=True, separators=(",", ":")) for m in compatible}
    determined = len(predictions) == 1
    prediction = json.loads(next(iter(predictions))) if determined else None
    return {
        "status": "determined" if determined else "not_determined",
        "prediction": prediction,
        "compatible_mechanism_ids": [m["hypothesis_id"] for m in compatible],
        "declared_mechanism_count": len(mechanisms),
    }