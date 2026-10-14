"""Finite, declared-mechanism adjudication for novel-action predictions."""
import json


STATUSES = {"acknowledged", "dispatch_failed", "outcome_unknown"}


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


def adjudicate(mechanisms, history, proposed_action, proposed_observation=None):
    """Return the evidence-supported prediction over the declared mechanism set.

    Mechanisms map canonical action JSON to observable outcome values. Failed or
    unobserved dispatches constrain no mechanism. A repeated proposed action is
    rejected so the scored prediction cannot be answered by exact recall.
    """
    if type(mechanisms) is not list or len(mechanisms) < 2:
        raise ValueError("at least two declared mechanisms are required")
    proposal_key = query_key(proposed_action, proposed_observation)
    history_keys = set()
    for record in history:
        status = _status(record) if type(record) is dict else None
        if type(record) is not dict or status not in STATUSES:
            raise ValueError("invalid history dispatch status")
        key = action_key(record.get("action"))
        history_keys.add(key)
        if status == "acknowledged":
            if "observed_outcome" not in record:
                raise ValueError("acknowledged records need an observed outcome")
        elif "observed_outcome" in record:
            raise ValueError("unobserved dispatch cannot carry an observed outcome")
    if proposal_key in history_keys:
        raise ValueError("proposed action-coordinate pair is not novel")

    compatible = []
    for mechanism in mechanisms:
        if (type(mechanism) is not dict or not {"mechanism_id", "outcomes"} <= set(mechanism)
            or set(mechanism) - {"mechanism_id", "outcomes", "explanation"}
                or type(mechanism["mechanism_id"]) is not str
                or type(mechanism["outcomes"]) is not dict):
            raise ValueError("invalid declared mechanism")
        outcomes = mechanism["outcomes"]
        consistent = True
        for record in history:
            if _status(record) != "acknowledged":
                continue
            key = query_key(record["action"], record.get("pre_observation"))
            if key not in outcomes or outcomes[key] != record["observed_outcome"]:
                consistent = False
                break
        if consistent:
            compatible.append(mechanism)
    if not compatible:
        raise ValueError("no declared mechanism is consistent with the supplied evidence")
    if any(proposal_key not in mechanism["outcomes"] for mechanism in compatible):
        raise ValueError("a compatible mechanism lacks a proposed-action prediction")

    predictions = {json.dumps(m["outcomes"][proposal_key], sort_keys=True, separators=(",", ":"))
                   for m in compatible}
    determined = len(predictions) == 1
    prediction = json.loads(next(iter(predictions))) if determined else None
    return {
        "status": "determined" if determined else "not_determined",
        "prediction": prediction,
        "compatible_mechanism_ids": [m["mechanism_id"] for m in compatible],
        "declared_mechanism_count": len(mechanisms),
    }