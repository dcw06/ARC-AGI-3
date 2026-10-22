"""Fresh-engine reconstruction of multi-level plans and durable encounter memory."""
import math
from research.initial_geometry_assistance_v1.geometry import digest
from .controller import run_levels


def audit_levels(initial, retained, replay_factory, *, max_levels=3, action_cap=384,
                 per_level_cap=128, memory=None):
    stops=[e for e in retained if e['kind']=='admission_stop']
    if len(stops)>1:
        raise ValueError('multiple deadline stops')
    if stops:
        e=stops[0]
        if (set(e)!={'kind','check_index','overrun_seconds'} or type(e['check_index']) is not int or e['check_index']<1
                or type(e['overrun_seconds']) not in (int,float) or not math.isfinite(e['overrun_seconds'])
                or not 0<=e['overrun_seconds']<300):
            raise ValueError('invalid deadline receipt')
    checks=0
    def now():
        nonlocal checks
        checks+=1
        return stops[0]['overrun_seconds'] if stops and checks==stops[0]['check_index'] else -1
    events=[]
    result=run_levels(initial,replay_factory(),events.append,deadline=0,now=now,max_levels=max_levels,
                      action_cap=action_cap,per_level_cap=per_level_cap,memory=memory)
    if digest(events)!=digest(retained):
        raise ValueError('Objects, memory, plans, transitions or final result differ from independent replay')
    return dict(content_replay_verified=True,result=result,new_model_generations=0,lifecycle_certified=False,
                qualification='Fresh-engine visible-evidence replay, not new GPU certification.')
