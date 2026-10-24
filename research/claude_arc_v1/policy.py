"""Same text-grid policy for either backend; no teacher rules or solutions."""
import json
from agent.action import ActionDecision, serialize_action
from .config import STAGES, strict_json

SYSTEM = (
    'You control an unfamiliar ARC game. Infer its goal and mechanics only from supplied observations. '
    'Choose exactly one currently legal action. Do not assume action names imply effects. '
    'Only ACTION6 takes x,y integer coordinates from 0 to 63. Other actions take empty action_data. '
    'Never reset (action 0). Return one JSON object matching output_contract, no Markdown. '
    'Changes, counters and visual resemblance do not by themselves establish progress, object identity or causality.'
)
PREDICATES = ('any_frame_changed', 'final_frame_changed', 'level_increased')


def observation_value(observation):
    return {'game_id': observation.game_id, 'frames': [f.tolist() for f in observation.frames], 'state': observation.state.name,
            'levels_completed': observation.levels_completed, 'available_actions': list(observation.available_actions),
            'win_levels': observation.win_levels, 'full_reset': observation.full_reset,
            'observation_sha256': observation.canonical_hash}


class Policy:
    def __init__(self, config):
        self.config = config
        self.history, self.hypotheses = [], []

    @property
    def rank(self):
        return STAGES.index(self.config.stage)

    def request(self, observation):
        contract = {'action': {'action_id': 'one legal integer from 1 to 7', 'action_data': 'x,y for ACTION6; otherwise {}'}}
        instructions = []
        evidence = {'current': observation_value(observation)}
        if self.rank >= 1:
            evidence['history'] = self.history[-self.config.history_limit:]
            evidence['history_omitted'] = max(0, len(self.history) - self.config.history_limit)
        if self.rank >= 2:
            evidence['hypotheses'] = self.hypotheses
            contract['hypotheses'] = [{'id': 'short ID', 'statement': 'testable claim',
                'status': 'tentative|supported_locally|contradicted', 'evidence_ids': ['supplied transition ID']}]
            instructions.append('Keep competing hypotheses; tie each claim to available evidence. An empty list is allowed.')
        if self.rank >= 3:
            contract['experiment'] = 'brief distinguishing purpose for this action, or empty string'
            instructions.append('When useful, choose an action whose possible outcomes distinguish surviving explanations.')
        if self.rank >= 4:
            contract['prediction'] = {p: 'boolean or null when unknown' for p in PREDICATES}
            instructions.append('Record prospective observable predictions; previous prediction checks are in history.')
        if self.rank >= 5:
            contract['plan'] = ['up to four short prospective steps; only the first action is executed now']
            instructions.append('Use supported local relationships to pursue the inferred goal; revise after contradictory feedback.')
        payload = {'evidence': evidence, 'output_contract': contract, 'procedure': instructions}
        return {'model': self.config.model, 'messages': [{'role': 'system', 'content': SYSTEM},
                {'role': 'user', 'content': json.dumps(payload, separators=(',', ':'), allow_nan=False)}],
                'max_tokens': self.config.max_output_tokens}

    def parse(self, text, observation):
        value = strict_json(text)
        expected = {'action'} | ({'hypotheses'} if self.rank >= 2 else set())
        expected |= {'experiment'} if self.rank >= 3 else set()
        expected |= {'prediction'} if self.rank >= 4 else set()
        expected |= {'plan'} if self.rank >= 5 else set()
        if not isinstance(value, dict) or set(value) != expected:
            raise ValueError('response does not match stage contract; no repair or fallback')
        action = value['action']
        if (not isinstance(action, dict) or set(action) != {'action_id', 'action_data'}
                or type(action['action_id']) is not int or not 1 <= action['action_id'] <= 7
                or not isinstance(action['action_data'], dict)):
            raise ValueError('invalid action shape/type')
        data = action['action_data']
        if action['action_id'] == 6 and (set(data) != {'x', 'y'} or any(type(data[k]) is not int for k in data)):
            raise ValueError('click needs strictly integer x,y')
        decision = ActionDecision(action['action_id'], data, source='api_evaluation')
        serialize_action(decision, game_id=observation.game_id, guid=observation.guid,
                         legal_actions=observation.available_actions, allow_level_reset=False)
        if self.rank >= 2:
            hypotheses = value['hypotheses']
            allowed = {h['transition_id'] for h in self.history[-self.config.history_limit:]}
            # Previously stored claims retain explicit provenance even when raw records have left the prompt.
            allowed |= {r for h in self.hypotheses for r in h['evidence_ids']}
            if not isinstance(hypotheses, list) or len(hypotheses) > 8:
                raise ValueError('at most eight hypotheses')
            ids = set()
            for h in hypotheses:
                if not isinstance(h, dict) or set(h) != {'id', 'statement', 'status', 'evidence_ids'}:
                    raise ValueError('invalid hypothesis shape')
                if (not isinstance(h['id'], str) or not 1 <= len(h['id']) <= 64 or h['id'] in ids
                        or not isinstance(h['statement'], str) or not 1 <= len(h['statement']) <= 1000
                        or h['status'] not in ('tentative', 'supported_locally', 'contradicted')
                        or not isinstance(h['evidence_ids'], list) or any(not isinstance(r, str) for r in h['evidence_ids'])
                        or len(set(h['evidence_ids'])) != len(h['evidence_ids']) or not set(h['evidence_ids']) <= allowed):
                    raise ValueError('invalid hypothesis or unavailable evidence reference')
                if h['status'] != 'tentative' and not h['evidence_ids']:
                    raise ValueError('asserted hypothesis status needs evidence')
                ids.add(h['id'])
        if self.rank >= 3 and (not isinstance(value['experiment'], str) or len(value['experiment']) > 1000):
            raise ValueError('invalid experiment statement')
        if self.rank >= 4 and (not isinstance(value['prediction'], dict) or set(value['prediction']) != set(PREDICATES)
                or any(v is not None and type(v) is not bool for v in value['prediction'].values())):
            raise ValueError('invalid prediction')
        if self.rank >= 5 and (not isinstance(value['plan'], list) or len(value['plan']) > 4
                or any(not isinstance(s, str) or len(s) > 500 for s in value['plan'])):
            raise ValueError('invalid bounded plan')
        return decision, value

    def observe(self, before, decision, after, answer):
        import numpy as np
        same_size = all(f.shape == before.latest_frame.shape for f in after.frames)
        facts = {p: None for p in PREDICATES}
        if same_size:
            facts['any_frame_changed'] = any(not np.array_equal(before.latest_frame, f) for f in after.frames)
            facts['final_frame_changed'] = not np.array_equal(before.latest_frame, after.latest_frame)
        facts['level_increased'] = after.levels_completed > before.levels_completed
        checks = {p: {'predicted': answer.get('prediction', {}).get(p), 'observed': facts[p],
                      'correct': (answer.get('prediction', {}).get(p) == facts[p])
                      if facts[p] is not None and answer.get('prediction', {}).get(p) is not None else None}
                  for p in PREDICATES} if self.rank >= 4 else {}
        transition = {'transition_id': 't' + str(len(self.history) + 1),
            'before': observation_value(before), 'action': {'action_id': decision.action_id, 'action_data': dict(decision.action_data)},
            'dispatch': 'acknowledged', 'after': observation_value(after), 'observed': facts,
            'prediction_checks': checks}
        self.history.append(transition)
        if self.rank >= 2:
            self.hypotheses = answer['hypotheses']
            if facts['level_increased']:
                # Do not carry layout-specific coordinates/claims to the next level automatically.
                self.hypotheses = []
        return transition
