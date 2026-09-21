"""Deterministic CPU test fixtures; incapable of model or solving evidence."""
import json
from types import SimpleNamespace
import numpy as np
from arcengine import GameState
from agent.framework_adapter import LocalFrameworkAdapter
from certification.phase4_transient_v2.contract import digest

class FakeArcade:
    def __init__(self,row):self.row=row
    def open_scorecard(self,tags=None):return 'fixture-'+self.row['episode_id']
    def close_scorecard(self,card):return SimpleNamespace(model_dump=lambda:{'card_id':card})
    def make(self,game_id,**kwargs):
        row=self.row
        class Env:
            count=0
            def observation(self):
                return SimpleNamespace(game_id=game_id,guid='fixture-'+row['episode_id'],
                    frame=([np.full((8,8),14,dtype=np.uint8)] if self.count else [])+[np.full((8,8),self.count%2,dtype=np.uint8)],state=GameState.WIN if self.count==3 else GameState.NOT_FINISHED,
                    levels_completed=int(self.count==3),win_levels=1,available_actions=[1,6],full_reset=False)
            def step(self,action,data=None,reasoning=None):self.count+=1;return self.observation()
        env=Env();env.observation_space=env.observation();return env

def adapter_factory(row):return LocalFrameworkAdapter(FakeArcade(row),seed_by_game={row['game_id']:0})

class ScriptedService:
    startup_seconds=0;artifact={};canary_audit={'status':'scripted_not_target'}
    def __init__(self):self.audit_records=[]
    def complete(self,request):
        payload=json.loads(request['messages'][1]['content'])['observation']
        legal=payload['legal_actions'];action=1 if 1 in legal else next(a for a in legal if a!=0)
        content=json.dumps({'action':{'action_id':action,'action_data':{'x':12,'y':34} if action==6 else {}}})
        self.audit_records.append({'request_sha256':digest(request),'tokenizer_prompt_tokens':10,
            'server_prompt_tokens':10,'server_completion_tokens':29,'service_seconds':0})
        return SimpleNamespace(content=content,prompt_tokens=10,completion_tokens=29)
