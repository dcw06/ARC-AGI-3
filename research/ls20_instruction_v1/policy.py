"""Full-action VLM policy with supplied rules, but no route or object masks."""
from copy import deepcopy
import json
from certification.phase4_multimodal_preflight_v3.images import png, data_url
from research.initial_geometry_assistance_v1.policy import check_observation, parse_answer
from .live_contract import MODEL, ACTION_CAP

SYSTEM=(
    'Play level 1 of the pixel game using the supplied controls and rules. '
    'You must choose and plan the actions yourself from the images; no solved route is supplied. '
    'Use exactly one legal action per reply, with no reset or batch. '
    'Images are 448 by 448 with no annotations. Each native cell is a 7 by 7 pixel block. '
    'x increases right; y increases down. Initial and previous images are historical, not current. '
    'Inspect the current player position, obstacles, reference pattern and target pattern. '
    'Use the actual observed result of each action to adjust the next choice. '
    'Do not assume a visual change or a matching pattern alone means the level completed; '
    'completion is confirmed only by the recorded level counter. '
    'Return only compact JSON with exactly action_id, action_data and predicted_visible_change. '
    'action_id is 1, 2, 3 or 4; action_data is always {}. '
    'predicted_visible_change is yes, no or unknown. No explanations or additional fields.'
)

def make_request(initial,current,history,instructions):
    check_observation(initial); check_observation(current)
    if (not isinstance(instructions,str) or not instructions.strip() or
        len(history)>=ACTION_CAP or current['legal_actions']!=[1,2,3,4]):
        raise ValueError('instruction episode scope differs')
    content=[{'type':'text','text':instructions}, {'type':'text','text':json.dumps({
        'decision_index':len(history),'action_cap':ACTION_CAP,'current_state':current['state'],
        'current_levels_completed':current['levels_completed'],'legal_actions':current['legal_actions'],
        'executed_actions':[deepcopy(r['action']) for r in history]},sort_keys=True)}]
    def image(label,grid):
        content.extend([{'type':'text','text':label},{'type':'image_url','image_url':{'url':data_url(png(grid,cell=7))}}])
    image('Initial level-1 image (historical):',initial['grid'])
    for entry in history[-2:]:
        content.append({'type':'text','text':json.dumps({'previous_action':entry['action'],'step':entry['step']},sort_keys=True)})
        image('Previous before:',entry['before']['grid']);image('Previous after:',entry['after']['grid'])
    image('Current image: choose the next action here.',current['grid'])
    return dict(model=MODEL,messages=[{'role':'system','content':SYSTEM},{'role':'user','content':content}],
        max_tokens=256,temperature=0,seed=0,chat_template_kwargs={'enable_thinking':False},
        response_format={'type':'json_object'})

def parse(text,legal):
    value=parse_answer(text,legal)
    if value['action_id'] not in (1,2,3,4) or value['action_data']:
        raise ValueError('only directional actions are in this pilot')
    return value
