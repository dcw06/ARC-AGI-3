"""Bounded VLM calls for colors and probes; DFS chooses navigation actions."""
import json
from research.ls20_knn_path_v1.policy import assess_request, make_request, parse_assessment, parse

INSTRUCTIONS = (
    'Navigate the orange-and-blue block to the initial white cross, using supplied controls '
    '1 up,2 down,3 left,4 right. A deterministic DFS planner handles routing. '
    'Judge path colors from visible evidence and k=4 estimates without inventing a route. '
    'A previously confident color may be wrong: repeated blocked moves or no usable route '
    'trigger reassessment. Distinguish a blocked action from movement with no special event. '
    'If uncertain, return null; do not force a conclusion. In exploration mode prefer '
    'different nearby color regions not already tried; no reset, click, batch or hidden-state '
    'access. Some colors may be unreachable. Reaching the cross is not completing the level.'
)


def color_request(initial, current, history, reason, current_assessment):
    request = assess_request(initial, INSTRUCTIONS, current, history)
    request['messages'][1]['content'].insert(0, dict(type='text', text=json.dumps(dict(
        reassessment_reason=reason, previous_path_assessment=current_assessment,
        navigation_controller='DFS; no route or per-step answer supplied to the VLM'), sort_keys=True)))
    return request


def probe_request(initial, current, history, assessment):
    return make_request(initial, current, history, INSTRUCTIONS, assessment, mode='explore_colors')
