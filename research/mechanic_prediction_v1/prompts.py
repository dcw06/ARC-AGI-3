"""Matched reference/candidate requests and independent fixture-understanding probes."""
import json

from research.mechanic_prediction_v1.fixtures import public_scenario
from research.mechanic_prediction_v1.schema import PREDICTIONS, STATUSES


MAX_COMPLETION_TOKENS = 96
SYSTEM_PROMPT = (
    "Predict only observable effects of the proposed action from the supplied evidence. "
    "Do not assume an action's mechanics from its name. Preserve uncertainty when the evidence "
    "does not distinguish possible outcomes. Return one JSON object matching the response schema."
)
CANDIDATE_PROCEDURE = (
    "Before answering, check at least two explanations that fit the observations. "
    "Report a specific effect only when every surviving explanation predicts that same effect; "
    "otherwise use unknown and not_determined. Do not invent explanations or evidence."
)
RESPONSE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["prediction", "evidence_ids", "status"],
    "properties": {
        "prediction": {"type": "string", "enum": sorted(PREDICTIONS)},
        "evidence_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "status": {"type": "string", "enum": sorted(STATUSES)},
    },
}


def _user_evidence(scenario):
    public = public_scenario(scenario)
    question = {
        "evidence": public,
        "question": "Predict the observable effect category of proposed_action before its transition is revealed.",
        "response_schema": RESPONSE_SCHEMA,
    }
    return json.dumps(question, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def render_request(scenario, arm):
    if arm not in {"reference", "candidate"}:
        raise ValueError("unknown experimental arm")
    system = SYSTEM_PROMPT if arm == "reference" else SYSTEM_PROMPT + " " + CANDIDATE_PROCEDURE
    user = _user_evidence(scenario)
    return {
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {"type": "json_schema", "json_schema": RESPONSE_SCHEMA},
        "max_tokens": MAX_COMPLETION_TOKENS,
        "temperature": 0,
        "seed": 0,
    }


GROUNDING_QUESTIONS = {
    "changed_cells": "Which grid coordinates changed between the before frame and the last returned frame of the selected record?",
    "coordinate_action": "Which action records include coordinate arguments?",
    "target_match": "Does the proposed coordinate land on a non-background cell in the current frame?",
    "exact_history_match": "Is the exact proposed action and coordinate pair present in the history?",
    "marked_region_movement": "Which marked visual region changed position? Report only the observed before and after coordinates; do not claim persistent object identity.",
}


def render_grounding_request(scenario, question_id):
    if question_id not in GROUNDING_QUESTIONS:
        raise ValueError("unknown grounding question")
    public = public_scenario(scenario)
    public["background_value"] = 9
    selected = next((record for record in scenario["history"]
                     if record["dispatch_status"] == "acknowledged"), None)
    if selected is None:
        raise ValueError("grounding probe needs an acknowledged record")
    payload = {"evidence": public, "question": GROUNDING_QUESTIONS[question_id]}
    payload["selected_record_id"] = selected["record_id"]
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def scripted_reader(rendered_request):
    """A key-blind parser used to test the rendered request boundary."""
    request = json.loads(rendered_request)
    evidence = json.loads(request["messages"][1]["content"])["evidence"]
    records = evidence["history"]
    references = [record["record_id"] for record in records]
    if not references:
        raise ValueError("scripted reader requires visible evidence")
    return json.dumps({"prediction": "unknown", "evidence_ids": [references[-1]],
                       "status": "not_determined"}, separators=(",", ":"))