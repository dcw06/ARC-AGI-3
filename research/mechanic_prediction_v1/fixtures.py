"""Generated visual trajectories for the finite mechanic-prediction benchmark."""
import copy

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


def _rule(action_id, mode, coordinate_relation, outcome):
    return {"action_id": action_id, "mode": mode,
            "coordinate_relation": coordinate_relation, "outcome": outcome}


def _hypothesis(hypothesis_id, explanation, rules):
    return {"hypothesis_id": hypothesis_id, "explanation": explanation,
            "rules": rules, "default_outcome": "no_change"}


def _hypotheses(family, family_index, index, proposal_outcomes):
    first, second = proposal_outcomes
    if family == "click_grounding":
        return [
            _hypothesis("H1", "An exact-target click and an adjacent click can have different effects.",
                        [_rule(6, "any", "target", "no_change"), _rule(6, "any", "adjacent", first)]),
            _hypothesis("H2", "Clicks on this marked region do not alter the returned grid.",
                        [_rule(6, "any", "target", "no_change"), _rule(6, "any", "adjacent", second)]),
        ]
    if family == "movement_constraints":
        return [
            _hypothesis("H1", "Action 2 is ineffective here; action 3 has the first listed effect.",
                        [_rule(2, "any", "none", "no_change"), _rule(3, "any", "none", first)]),
            _hypothesis("H2", "Action 2 is ineffective here; action 3 has the second listed effect.",
                        [_rule(2, "any", "none", "no_change"), _rule(3, "any", "none", second)]),
        ]
    if family == "delayed_effects":
        return [
            _hypothesis("H1", "Action 5 returns a delayed change; action 3 follows the first listed rule.",
                        [_rule(5, "any", "none", "delayed_change"), _rule(3, "any", "none", first)]),
            _hypothesis("H2", "Action 5 returns a delayed change; action 3 follows the second listed rule.",
                        [_rule(5, "any", "none", "delayed_change"), _rule(3, "any", "none", second)]),
        ]
    if family == "transient_effects":
        return [
            _hypothesis("H1", "Action 4 is transient; a neighboring click follows the first listed rule.",
                        [_rule(4, "any", "none", "transient_change"), _rule(6, "any", "adjacent", first)]),
            _hypothesis("H2", "Action 4 is transient; a neighboring click follows the second listed rule.",
                        [_rule(4, "any", "none", "transient_change"), _rule(6, "any", "adjacent", second)]),
        ]
    if family == "object_correspondence":
        return [
            _hypothesis("H1", "Action 1 changed the marked region; a neighboring click follows the first rule.",
                        [_rule(1, "any", "none", "changed"), _rule(6, "any", "adjacent", first)]),
            _hypothesis("H2", "Action 1 changed the marked region; a neighboring click follows the second rule.",
                        [_rule(1, "any", "none", "changed"), _rule(6, "any", "adjacent", second)]),
        ]
    if family == "state_dependence":
        alternate = OUTCOMES[(OUTCOMES.index(second) + 1) % len(OUTCOMES)]
        return [
            _hypothesis("H1", "An adjacent click has the same effect in active and inactive modes.",
                        [_rule(6, "active", "target", "changed"), _rule(6, "inactive", "target", "changed"),
                         _rule(6, "any", "adjacent", first)]),
            _hypothesis("H2", "An adjacent click has different effects in active and inactive modes.",
                        [_rule(6, "active", "target", "changed"), _rule(6, "active", "adjacent", alternate),
                         _rule(6, "inactive", "adjacent", second)]),
        ]
    if family == "coordinate_specificity":
        return [
            _hypothesis("H1", "Any coordinate click has the first listed effect after the observed target click.",
                        [_rule(6, "active", "target", "changed"), _rule(6, "active", "adjacent", first)]),
            _hypothesis("H2", "Only the exact marked coordinate has the second listed effect.",
                        [_rule(6, "active", "target", "changed"), _rule(6, "active", "adjacent", second)]),
        ]
    if family == "contradiction":
        return [
            _hypothesis("H1", "Action 5 always leaves the frame unchanged.",
                        [_rule(5, "any", "none", "no_change")]),
            _hypothesis("H2", "Action 5 changes by mode; action 3 follows the first listed rule.",
                        [_rule(5, "active", "none", "no_change"), _rule(5, "inactive", "none", "changed"),
                         _rule(3, "inactive", "none", first)]),
            _hypothesis("H3", "Action 5 changes by mode; action 3 follows the second listed rule.",
                        [_rule(5, "active", "none", "no_change"), _rule(5, "inactive", "none", "changed"),
                         _rule(3, "inactive", "none", second)]),
            _hypothesis("H4", "Action 5 always changes the frame.",
                        [_rule(5, "any", "none", "changed")]),
        ]
    raise ValueError("unknown challenge family")


def _scenario(family, index):
    family_index = FAMILIES.index(family)
    position = ((1, 1), (5, 1), (1, 5), (5, 5))[(index + family_index) % 4]
    x, y = position
    initial = {"frames": [_grid(x, y)], "signals": {"mode": "active", "target": [x, y]}}
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
            record["returned_signals"] = {"mode": next_mode, "target": [x, y]}
            record["observed_outcome"] = visible_outcome(before["frames"][-1], record["returned_frames"])
            current = {"frames": [copy.deepcopy(record["returned_frames"][-1])],
                       "signals": {**copy.deepcopy(record["returned_signals"]), "target": [x, y]}}
        else:
            current = copy.deepcopy(before)
        history.append(record)
        previous_status = status

    proposal_context = copy.deepcopy(current)
    underdetermined = index in (0, 2)
    if underdetermined:
        pair = (("changed", "no_change"), ("delayed_change", "transient_change"))[(family_index + index // 2) % 2]
    else:
        outcome = OUTCOMES[(family_index // 4) * 2 + (family_index % 4) // 2]
        pair = (outcome, outcome)
    mechanisms = _hypotheses(family, family_index, index, pair)

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
    public["candidate_hypotheses"] = copy.deepcopy(scenario["mechanisms"])
    for record in public["history"]:
        record.pop("observed_outcome", None)
    return public


def generate():
    return {"version": "mechanic_prediction_fixtures_v1",
            "scope": "Synthetic finite mechanism space; not an enumeration of every real-world explanation.",
            "scenarios": all_scenarios()}