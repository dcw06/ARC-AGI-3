"""Generated visual trajectories for the finite mechanic-prediction benchmark."""
import copy

from research.mechanic_prediction_v1.oracle import action_key, query_key


OUTCOMES = ("no_change", "changed", "delayed_change", "transient_change")
FAMILIES = (
    "click_grounding", "movement_constraints", "delayed_effects", "transient_effects",
    "object_correspondence", "state_dependence", "coordinate_specificity", "contradiction",
)


def action(action_id, x=None, y=None):
    data = {} if x is None and y is None else {"x": x, "y": y}
    return {"action_id": action_id, "action_data": data}


def _grid(x, y):
    grid = [[9 for _ in range(8)] for _ in range(8)]
    grid[y][x] = 1
    grid[y][x + 1] = 2
    grid[y + 1][x] = 1
    grid[y + 1][x + 1] = 1
    return grid


def _changed(frame, x, y):
    result = copy.deepcopy(frame)
    result[y][x] = 3 if result[y][x] != 3 else 1
    return result


def _move_region(frame, x, y):
    result = copy.deepcopy(frame)
    for dy in range(2):
        for dx in range(2):
            result[y + dy][x + dx] = 9
    for dy, row in enumerate(((1, 2), (1, 1))):
        for dx, value in enumerate(row):
            result[y + dy][x + dx + 1] = value
    return result


def _frames(frame, outcome, x, y):
    changed = _changed(frame, x, y)
    if outcome == "no_change":
        return [copy.deepcopy(frame)]
    if outcome == "changed":
        return [changed]
    if outcome == "delayed_change":
        return [copy.deepcopy(frame), changed]
    if outcome == "transient_change":
        return [changed, copy.deepcopy(frame)]
    if outcome == "moved":
        return [_move_region(frame, x, y)]
    raise ValueError("unknown fixture outcome")


def visible_outcome(before, returned_frames):
    """Classify only the supplied frame sequence, never a hidden game rule."""
    if type(returned_frames) is not list or not returned_frames:
        raise ValueError("an observed transition needs returned frames")
    changed = [frame != before for frame in returned_frames]
    if not any(changed):
        return "no_change"
    if not changed[0] and any(changed[1:]):
        return "delayed_change"
    if changed[-1] is False:
        return "transient_change"
    return "changed"


def _events(family, x, y):
    click = lambda px, py: action(6, px, py)
    plain = action
    if family == "click_grounding":
        return [(click(x, y), "acknowledged", "no_change", "active", [1, 2, 3, 4, 5, 6, 7])], click(x + 1, y)
    if family == "movement_constraints":
        return [
            (plain(1), "dispatch_failed", None, "active", [2, 3, 4, 5, 6, 7]),
            (plain(2), "acknowledged", "no_change", "active", [1, 2, 3, 4, 5, 6, 7]),
        ], plain(3)
    if family == "delayed_effects":
        return [(plain(5), "acknowledged", "delayed_change", "active", [1, 2, 3, 4, 5, 6, 7])], plain(3)
    if family == "transient_effects":
        return [(plain(4), "acknowledged", "transient_change", "active", [1, 2, 3, 4, 5, 6, 7])], click(x + 1, y)
    if family == "object_correspondence":
        return [
            (plain(7), "outcome_unknown", None, "active", [1, 2, 3, 4, 5, 6, 7]),
            (plain(1), "acknowledged", "moved", "active", [1, 2, 3, 4, 5, 6, 7]),
        ], click(x + 1, y)
    if family == "state_dependence":
        return [(click(x, y), "acknowledged", "changed", "inactive", [1, 2, 3, 4, 5, 6, 7])], click(x + 1, y)
    if family == "coordinate_specificity":
        return [(click(x, y), "acknowledged", "changed", "active", [1, 2, 3, 4, 5, 6, 7])], click(x + 1, y)
    if family == "contradiction":
        return [
            (plain(5), "acknowledged", "no_change", "inactive", [1, 2, 3, 4, 5, 6, 7]),
            (plain(5), "acknowledged", "changed", "inactive", [1, 2, 3, 4, 5, 6, 7]),
        ], plain(3)
    raise ValueError("unknown challenge family")


def _scenario(family, index):
    x = 2 + index % 3
    y = 2 + (index // 2)
    initial = {"frames": [_grid(x, y)], "signals": {"mode": "active"}}
    events, proposal = _events(family, x, y)
    history = []
    current = copy.deepcopy(initial)
    previous_status = None
    for step, (chosen_action, status, outcome, next_mode, available) in enumerate(events, 1):
        before = copy.deepcopy(current)
        source = ("initial_observation" if step == 1 else
                  "returned_observation" if previous_status == "acknowledged" else
                  "unchanged_after_dispatch_failure" if previous_status == "dispatch_failed" else
                  "fresh_observation_after_unknown")
        record = {
            "record_id": f"R{step}", "pre_observation": before, "action": chosen_action,
            "available_actions": available, "dispatch_status": status,
            "pre_observation_source": source, "returned_frames": [], "returned_signals": None,
        }
        if status == "acknowledged":
            record["returned_frames"] = _frames(before["frames"][-1], outcome, x, y)
            record["returned_signals"] = {"mode": next_mode}
            record["observed_outcome"] = visible_outcome(before["frames"][-1], record["returned_frames"])
            current = {"frames": [copy.deepcopy(record["returned_frames"][-1])],
                       "signals": copy.deepcopy(record["returned_signals"])}
        else:
            current = copy.deepcopy(before)
        history.append(record)
        previous_status = status

    underdetermined = index in (0, 2)
    determinate_outcome = "no_change" if index == 1 else "delayed_change"
    proposal_outcomes = ("changed", "no_change") if underdetermined else (determinate_outcome, determinate_outcome)
    if family == "contradiction":
        mechanisms = [
            {"mechanism_id": "rule_a", "explanation": "The same control has the same effect in every observed state.", "outcomes": {}},
            {"mechanism_id": "rule_b", "explanation": "The effect depends on the exposed mode.", "outcomes": {}},
            {"mechanism_id": "rule_c", "explanation": "A second state-conditioned rule fits the observations.", "outcomes": {}},
            {"mechanism_id": "rule_d", "explanation": "The first no-change record was not representative.", "outcomes": {}},
        ]
    else:
        descriptions = {
            "click_grounding": ("The click affects only the exact marked coordinate.", "The click is ineffective in this state."),
            "movement_constraints": ("A barrier blocks the path despite an otherwise legal movement.", "The earlier action was unavailable, while a different legal direction can move."),
            "delayed_effects": ("The action schedules a later visible change.", "The action can be followed by an unrelated later change."),
            "transient_effects": ("The action briefly changes the frame and then restores it.", "A separate frame refresh caused the temporary difference."),
            "object_correspondence": ("The later action still addresses the same moving object.", "A visually similar region may be a replacement object."),
            "state_dependence": ("The click works in either exposed mode.", "The click works only in the active mode."),
            "coordinate_specificity": ("The effect is tied to one exact coordinate.", "The effect also applies to nearby coordinates."),
        }
        first, second = descriptions[family]
        mechanisms = [
            {"mechanism_id": "rule_a", "explanation": first, "outcomes": {}},
            {"mechanism_id": "rule_b", "explanation": second, "outcomes": {}},
        ]

    for mechanism in mechanisms:
        for record in history:
            if record["dispatch_status"] == "acknowledged":
                mechanism["outcomes"][query_key(record["action"], record["pre_observation"])] = record["observed_outcome"]

    proposal_context = copy.deepcopy(current)
    proposal_key = query_key(proposal, proposal_context)
    if family == "contradiction":
        first_record, second_record = history
        mechanisms[0]["outcomes"][query_key(second_record["action"], second_record["pre_observation"])] = "no_change"
        mechanisms[3]["outcomes"][query_key(first_record["action"], first_record["pre_observation"])] = "changed"
        mechanisms[0]["outcomes"][proposal_key] = proposal_outcomes[0]
        mechanisms[1]["outcomes"][proposal_key] = proposal_outcomes[0]
        mechanisms[2]["outcomes"][proposal_key] = proposal_outcomes[1]
        mechanisms[3]["outcomes"][proposal_key] = proposal_outcomes[1]
    else:
        mechanisms[0]["outcomes"][proposal_key] = proposal_outcomes[0]
        mechanisms[1]["outcomes"][proposal_key] = proposal_outcomes[1]

    return {
        "scenario_id": f"S{FAMILIES.index(family) + 1:02d}-{index + 1:02d}",
        "split": "development" if index < 2 else "evaluation",
        "family": family,
        "initial_observation": initial,
        "history": history,
        "current_observation": proposal_context,
        "current_available_actions": [1, 2, 3, 4, 5, 6, 7],
        "proposed_action": proposal,
        "mechanisms": mechanisms,
    }


def all_scenarios():
    return [_scenario(family, index) for family in FAMILIES for index in range(4)]


def public_scenario(scenario):
    public = {key: copy.deepcopy(value) for key, value in scenario.items()
              if key not in {"scenario_id", "split", "family", "mechanisms"}}
    for record in public["history"]:
        record.pop("observed_outcome", None)
    return public


def generate():
    return {"version": "mechanic_prediction_fixtures_v1",
            "scope": "Synthetic finite mechanism space; not an enumeration of every real-world explanation.",
            "scenarios": all_scenarios()}