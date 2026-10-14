"""Fixture-only perception and coordinate-grounding answers, separate from prediction."""
from research.mechanic_prediction_v1.schema import validate_grounding_response


def _bbox(cells):
    if not cells:
        return None
    return [min(x for x, _ in cells), min(y for _, y in cells),
            max(x for x, _ in cells), max(y for _, y in cells)]


def grounding_answers(scenario):
    records = scenario["history"]
    changed_cells = {}
    for record in records:
        if record["dispatch_status"] != "acknowledged":
            continue
        before = record["pre_observation"]["frames"][-1]
        after = record["returned_frames"][-1]
        if len(before) != len(after) or len(before[0]) != len(after[0]):
            changed_cells[record["record_id"]] = None
        else:
            changed_cells[record["record_id"]] = [
                [x, y] for y, row in enumerate(after) for x, value in enumerate(row)
                if before[y][x] != value
            ]
    coordinate_action_ids = [record["record_id"] for record in records
                             if record["action"]["action_data"]]
    proposed = scenario["proposed_action"]
    exact_match = any(record["action"] == proposed for record in records)
    x = proposed["action_data"].get("x")
    y = proposed["action_data"].get("y")
    frame = scenario["current_observation"]["frames"][-1]
    target_match = (type(x) is int and type(y) is int and 0 <= y < len(frame)
                    and 0 <= x < len(frame[y]) and frame[y][x] != 9)

    movements = []
    for record in records:
        if record["dispatch_status"] != "acknowledged":
            continue
        before = record["pre_observation"]["frames"][-1]
        after = record["returned_frames"][-1]
        before_cells = [[x, y] for y, row in enumerate(before) for x, value in enumerate(row) if value != 9]
        after_cells = [[x, y] for y, row in enumerate(after) for x, value in enumerate(row) if value != 9]
        if _bbox(before_cells) != _bbox(after_cells) and len(before_cells) == len(after_cells):
            movements.append({"record_id": record["record_id"], "from_bbox": _bbox(before_cells),
                              "to_bbox": _bbox(after_cells)})
    return {"changed_cells_by_record": changed_cells,
            "coordinate_action_record_ids": coordinate_action_ids,
            "proposed_coordinate_hits_visible_region": target_match,
            "exact_proposed_action_coordinate_in_history": exact_match,
            "observed_region_movements": movements}


def diagnostic_answer(scenario, question_id):
    answers = grounding_answers(scenario)
    evidence_ids = [record["record_id"] for record in scenario["history"]]
    if question_id == "changed_cells":
        record = next(record for record in scenario["history"] if record["dispatch_status"] == "acknowledged")
        return answers["changed_cells_by_record"][record["record_id"]], [record["record_id"]]
    if question_id == "coordinate_action":
        return answers["coordinate_action_record_ids"], evidence_ids
    if question_id == "target_match":
        return answers["proposed_coordinate_hits_visible_region"], evidence_ids
    if question_id == "exact_history_match":
        return answers["exact_proposed_action_coordinate_in_history"], evidence_ids
    if question_id == "marked_region_movement":
        movements = answers["observed_region_movements"]
        if not movements:
            raise ValueError("scenario has no observed region movement")
        return movements, [movement["record_id"] for movement in movements]
    raise ValueError("unknown diagnostic question")


def score_grounding(scenario, responses):
    """Score fixture perception/grounding questions independently of mechanic prediction."""
    from research.mechanic_prediction_v1.prompts import GROUNDING_QUESTIONS

    results = {}
    for question_id in GROUNDING_QUESTIONS:
        if question_id == "marked_region_movement" and scenario["family"] != "object_correspondence":
            continue
        expected, supporting_ids = diagnostic_answer(scenario, question_id)
        try:
            parsed = validate_grounding_response(responses[question_id],
                                                 [record["record_id"] for record in scenario["history"]])
            valid = True
        except (KeyError, TypeError, ValueError):
            parsed = None
            valid = False
        results[question_id] = {
            "valid_output": valid,
            "answer_correct": bool(valid and parsed["answer"] == expected),
            "evidence_references_supported": bool(valid and parsed["evidence_ids"]
                                                   and set(parsed["evidence_ids"]) <= set(supporting_ids)),
        }
    return results