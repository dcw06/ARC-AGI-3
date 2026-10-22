"""VLM color recovery hook; pattern matching and navigation are deterministic."""
import json
from research.ls20_knn_path_v1.policy import body, image, assess_request, parse_assessment, parse
from research.ls20_knn_path_v1.geometry import context

INSTRUCTIONS = (
    'The agent is solving exposed ls20 level1 with supplied directional controls '
    '1 up,2 down,3 left,4 right. A pixel-based matcher compares the current reference '
    'and destination patterns; a deterministic DFS planner handles routing. '
    'Cross contact rotates the reference. The destination is approached only after '
    'an exact observed pattern match; engine level-counter increase alone confirms completion. '
    'You assess path colors or choose bounded exploratory actions only when requested. '
    'Previously confident color judgments may be wrong. Use observed motion, blocked '
    'moves and pixels; do not invent hidden rules, a solved route or inaccessible color tests.'
)
PROBE_SYSTEM = (
    'Choose one exploratory move to test a different nearby color region. '
    'Use supplied observed history; avoid already blocked directed edges and repeated '
    'stationary actions. A blocked move is not proof of a color role. Controls '
    '1 up,2 down,3 left,4 right; no reset, click or batch. Images are 448x448, '
    'native64x64 with7x7 pixels per cell. Return only compact JSON with exactly '
    'action_id,action_data ({}),predicted_visible_change (yes,no,unknown).'
)


def color_request(initial, current, history, reason, previous):
    request = assess_request(initial, INSTRUCTIONS, current, history)
    request['messages'][1]['content'].insert(0,dict(type='text',text=json.dumps(dict(
        reassessment_reason=reason,previous_assessment=previous,controller='pattern matcher and DFS'),sort_keys=True)))
    return request


def probe_request(initial, current, history, assessment, blocked):
    content=[dict(type='text',text=INSTRUCTIONS),dict(type='text',text=json.dumps(dict(
        decision_index=len(history),action_cap=40,path_assessment=assessment,
        geometry_and_knn=context(initial['grid'],current['grid']),
        executed_actions=[r['action'] for r in history],
        blocked_edges=[[list(p),a] for p,a in sorted(blocked)]),sort_keys=True))]
    content+=image('Initial board (historical):',initial['grid'])
    for old in history[-2:]:
        content.append(dict(type='text',text=json.dumps(dict(step=old['step'],action=old['action']),sort_keys=True)))
        content+=image('Previous before:',old['before']['grid'])+image('Previous after:',old['after']['grid'])
    content+=image('Current board: choose one bounded color probe.',current['grid'])
    return body(PROBE_SYSTEM,content)
