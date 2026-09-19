"""Frozen prompts and lossless observation records; no environment operations."""
import hashlib,json
from certification.phase4_closed_loop_v1.request_contract import protocol,validate_request
from pathlib import Path
import numpy as np
from arcengine import GameState
from agent.state import Observation
from agent.representation import build_raw_bundle
from certification.phase4_closed_loop_v1.action_contract import response_format,request_legal_actions

ROOT=Path(__file__).resolve().parents[2]
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

def request_for(state,arm):
    spec=protocol()
    messages=[{'role':'system','content':spec['prompts'][arm]['text']},
        {'role':'user','content':json.dumps({'observation':build_raw_bundle(state.observation,state.evidence,recent_limit=1).policy_payload()},sort_keys=True,separators=(',',':'))}]
    return {'model':spec['model_binding']['model_id'],'messages':messages,'temperature':0,'seed':0,
        'max_tokens':128,'chat_template_kwargs':{'enable_thinking':False},
        'response_format':response_format(request_legal_actions(messages))}


def pack(obs):
    value={'game_id':obs.game_id,'guid':obs.guid,'state':obs.state.value,
        'levels_completed':obs.levels_completed,'win_levels':obs.win_levels,
        'available_actions':list(obs.available_actions),'full_reset':obs.full_reset,
        'frames':[f.tolist() for f in obs.frames],'canonical_hash':obs.canonical_hash}
    return value

def unpack(value):
    for k in ('levels_completed','win_levels'):
        if type(value[k]) is not int or value[k]<0:raise ValueError('invalid level counter')
    if value['levels_completed']>value['win_levels']:raise ValueError('level counter exceeds game total')
    frames=[]
    for raw in value['frames']:
        grid=np.asarray(raw)
        if grid.ndim!=2 or not grid.size or not np.issubdtype(grid.dtype,np.integer) or grid.min()<0 or grid.max()>255:
            raise ValueError('lossy observation')
        frames.append(np.ascontiguousarray(grid,dtype=np.uint8))
    if not frames:raise ValueError('no frames')
    obs=Observation(value['game_id'],tuple(frames),GameState(value['state']),value['levels_completed'],
        value['win_levels'],value['guid'],tuple(value['available_actions']),value['full_reset'])
    if obs.canonical_hash!=value['canonical_hash']:raise ValueError('observation hash')
    return obs
