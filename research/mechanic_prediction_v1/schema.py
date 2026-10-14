"""Strict prediction response contract. Invalid outputs are rejected, never repaired."""
import json


PREDICTIONS = {"no_change", "changed", "delayed_change", "transient_change", "unknown"}
STATUSES = {"determined", "not_determined"}
RESPONSE_KEYS = {"prediction", "evidence_ids", "status"}


def validate_response(value, valid_evidence_ids):
    if type(value) is str:
        try:
            value = json.loads(value, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
        except (json.JSONDecodeError, ValueError) as error:
            raise ValueError("response must be valid JSON") from error
    if type(value) is not dict or set(value) != RESPONSE_KEYS:
        raise ValueError("response fields do not match the frozen schema")
    if type(value["prediction"]) is not str or value["prediction"] not in PREDICTIONS:
        raise ValueError("invalid prediction category")
    if type(value["status"]) is not str or value["status"] not in STATUSES:
        raise ValueError("invalid determination status")
    if (value["prediction"] == "unknown") != (value["status"] == "not_determined"):
        raise ValueError("unknown prediction and not_determined status must agree")
    ids = value["evidence_ids"]
    if type(ids) is not list or not ids or any(type(item) is not str for item in ids):
        raise ValueError("evidence_ids must be a non-empty string list")
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate evidence reference")
    if not set(ids) <= set(valid_evidence_ids):
        raise ValueError("evidence reference does not exist in the rendered request")
    return value


def validate_grounding_response(value, valid_evidence_ids):
    """Separate diagnostic schema; grounding is not mixed into prediction scoring."""
    if type(value) is str:
        try:
            value = json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError("response must be valid JSON") from error
    if type(value) is not dict or set(value) != {"answer", "evidence_ids"}:
        raise ValueError("grounding response fields")
    if type(value["answer"]) not in (str, bool, list):
        raise ValueError("invalid grounding answer type")
    if type(value["evidence_ids"]) is not list or not set(value["evidence_ids"]) <= set(valid_evidence_ids):
        raise ValueError("invalid grounding evidence references")
    return value