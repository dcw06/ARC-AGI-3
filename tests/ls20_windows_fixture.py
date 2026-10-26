"""Evaluator-owned public-observation fixtures; no rule supplied to W1."""
import copy
import json
from pathlib import Path

from research.action_effect_v1.records import effect_record
from research.ls20_discovery_windows.contract import digest, normalize_observation

PRODUCER = 'f4bf522e96b1642bed8772c29f153bfe44f98bd5'


def obs(grid=None, *, state='NOT_FINISHED', level=0, legal=None, frames=None, reset=False):
    return normalize_observation(dict(frames=frames if frames is not None else [grid or [[0, 0]]],
        state=state, levels_completed=level, legal_actions=legal if legal is not None else [1, 2], full_reset=reset))


def action(ident=1, **data):
    return dict(action_id=ident, action_data=data)


class RawMemory:
    """M1-schema-compatible raw-only test double, not another scene extractor."""
    def __init__(self, initial=None):
        self.current = initial or obs()
        self.segment = 0
        self.value = dict(version='ls20_discovery_mac_m1_v1', episode_id='toy-episode',
            initial=copy.deepcopy(self.current), transitions=[], observations=[], scenes=[],
            identity_candidates=[], events=[], hypotheses=[], suspended=False)
        self._ingest(self.current, None)

    def _ingest(self, observation, ident):
        for frame in observation['frames']:
            self.value['observations'].append(dict(id=f"o{len(self.value['observations'])}",
                kind='raw_observation', segment=self.segment, transition_id=ident,
                grid=copy.deepcopy(frame), sha256=digest(frame)))

    def snapshot(self):
        return copy.deepcopy(self.value)

    def append(self, act, outcome, *, elapsed_seconds=0.0):
        ident = f"t{len(self.value['transitions'])}"
        entry = dict(id=ident, episode_id=self.value['episode_id'], segment=self.segment,
            action=copy.deepcopy(act), outcome=copy.deepcopy(outcome), elapsed_seconds=elapsed_seconds,
            before_observation_id=self.value['observations'][-1]['id'], before_sha256=digest(self.current),
            after_sha256=None, after_observation_id=None, effect=effect_record(self.current,act,outcome))
        if outcome['status']=='acknowledged':
            post=outcome['post']
            if post['full_reset'] or post['levels_completed']!=self.current['levels_completed']:
                self.segment+=1
            self._ingest(post,ident)
            entry.update(after_sha256=digest(post), after_observation_id=self.value['observations'][-1]['id'])
            self.current=copy.deepcopy(post)
        self.value['suspended']=outcome['status']=='outcome_unknown'
        self.value['transitions'].append(entry)
        return copy.deepcopy(entry)

    def save(self, path):
        payload=self.snapshot()
        Path(path).write_text(json.dumps(dict(payload=payload,sha256=digest(payload))),encoding='utf-8')


def observe(memory, post, ident=1):
    return memory.append(action(ident), dict(status='acknowledged', post=post))
