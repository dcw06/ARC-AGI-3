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
HEX_NOTE = (' Grids are text. final_frame lists rows from y=0 (top) downward; each row reads "yy|" then the '
            'row\'s cells as hexadecimal colours (0-f) in groups of 8 separated by spaces, so the cell at column x is '
            'character x%8 of group x//8 (both counted from 0). ACTION6 clicks cell (x, y). changed_cells lists '
            'runs [x_first, x_last, y, before, after] of cells your action changed, with colours in the same hex digits.')
CHANGED_RUN_LIMIT = 64
HEX = '0123456789abcdef'


RESET_NOTE = (' After GAME_OVER the controller itself restarts the current level (RESET, shown in history as '
              'action 0); it counts as an action, and your notes are kept.')


def system_prompt(config):
    return (SYSTEM + (HEX_NOTE if config.grid_encoding == 'hex_rows' else '')
            + (RESET_NOTE if config.resets_per_game else ''))


def hex_rows(frame):
    import numpy as np
    frame = np.asarray(frame)
    if frame.ndim != 2 or frame.size == 0 or frame.min() < 0 or frame.max() > 15:
        return None
    rows = []
    for y, row in enumerate(frame):
        text = ''.join(HEX[int(v)] for v in row)
        # Row label and groups of 8: counting columns in an unbroken 64-character run drifted in the smoke run.
        rows.append('%02d|' % y + ' '.join(text[i:i + 8] for i in range(0, len(text), 8)))
    return rows


def prompt_observation(observation, encoding):
    """What the model reads. Evidence keeps observation_value; this only changes the prompt text."""
    if encoding == 'json':
        return observation_value(observation)
    rows = hex_rows(observation.latest_frame)
    if rows is None:  # outside the 16-colour palette: fall back to the exact integer form
        return observation_value(observation)
    return {'game_id': observation.game_id, 'state': observation.state.name,
            'levels_completed': observation.levels_completed, 'win_levels': observation.win_levels,
            'available_actions': list(observation.available_actions), 'full_reset': observation.full_reset,
            'intermediate_frames_omitted': len(observation.frames) - 1, 'final_frame': rows}


def changed_cells(before, after):
    import numpy as np
    old, new = np.asarray(before), np.asarray(after)
    if old.shape != new.shape:
        return {'shape_changed': True}
    ys, xs = np.nonzero(old != new)
    if not len(xs):
        return []
    # Same-row runs of cells with one (before, after) colour pair; a moved sprite is a few runs, not dozens of cells.
    runs = []
    for y, x in zip(ys.tolist(), xs.tolist()):
        pair = (HEX[int(old[y, x]) & 15] if old[y, x] < 16 else str(int(old[y, x])),
                HEX[int(new[y, x]) & 15] if new[y, x] < 16 else str(int(new[y, x])))
        if runs and runs[-1][2] == y and runs[-1][1] == x - 1 and (runs[-1][3], runs[-1][4]) == pair:
            runs[-1][1] = x
        else:
            runs.append([x, x, y, pair[0], pair[1]])
    if len(runs) > CHANGED_RUN_LIMIT:
        return {'cells': int(len(xs)), 'runs': len(runs), 'listed': False,
                'bounding_box': {'x_first': int(xs.min()), 'x_last': int(xs.max()),
                                 'y_first': int(ys.min()), 'y_last': int(ys.max())}}
    return runs


def compact_transition(transition, before, after, observation_ids=False):
    shown = prompt_observation(after, 'hex_rows')
    if observation_ids:
        shown = {'observation_id': 'o' + transition['transition_id'][1:], **shown}
    return {'transition_id': transition['transition_id'], 'action': transition['action'],
            'observed': transition['observed'], 'prediction_checks': transition['prediction_checks'],
            'changed_cells': changed_cells(before.latest_frame, after.latest_frame), 'after': shown}


def describe_citable(allowed):
    """Short form of the citable IDs for an error message, e.g. 't1-t40, o0-o40'."""
    def span(prefix):
        numbers = sorted(int(r[1:]) for r in allowed if r[:1] == prefix and r[1:].isdigit())
        if not numbers:
            return None
        if numbers == list(range(numbers[0], numbers[-1] + 1)) and len(numbers) > 2:
            return '%s%d-%s%d' % (prefix, numbers[0], prefix, numbers[-1])
        return ', '.join(prefix + str(k) for k in numbers[-20:])
    other = sorted(r for r in allowed if not (r[:1] in 'to' and r[1:].isdigit()))
    return ', '.join(p for p in (span('t'), span('o')) if p) + (', ' + ', '.join(other[:10]) if other else '') or 'none'


def response_schema(stage):
    """JSON Schema for structured output. Policy.parse still applies every semantic check."""
    rank = STAGES.index(stage)
    properties = {'action': {'type': 'object', 'additionalProperties': False, 'required': ['action_id', 'action_data'],
        'properties': {'action_id': {'type': 'integer', 'minimum': 1, 'maximum': 7},
                       'action_data': {'type': 'object', 'additionalProperties': False,
                                       'properties': {'x': {'type': 'integer', 'minimum': 0, 'maximum': 63},
                                                      'y': {'type': 'integer', 'minimum': 0, 'maximum': 63}}}}}}
    if rank >= 2:
        properties['hypotheses'] = {'type': 'array', 'maxItems': 8, 'items': {'type': 'object',
            'additionalProperties': False, 'required': ['id', 'statement', 'status', 'evidence_ids'],
            'properties': {'id': {'type': 'string', 'minLength': 1, 'maxLength': 64},
                           'statement': {'type': 'string', 'minLength': 1, 'maxLength': 1000},
                           'status': {'enum': ['tentative', 'supported_locally', 'contradicted']},
                           'evidence_ids': {'type': 'array', 'items': {'type': 'string'}}}}}
    if rank >= 3:
        properties['experiment'] = {'type': 'string', 'maxLength': 1000}
    if rank >= 4:
        properties['prediction'] = {'type': 'object', 'additionalProperties': False, 'required': list(PREDICATES),
                                    'properties': {p: {'type': ['boolean', 'null']} for p in PREDICATES}}
    if rank >= 5:
        properties['plan'] = {'type': 'array', 'maxItems': 4, 'items': {'type': 'string', 'maxLength': 500}}
    return {'type': 'object', 'additionalProperties': False, 'required': list(properties), 'properties': properties}


def observation_value(observation):
    return {'game_id': observation.game_id, 'frames': [f.tolist() for f in observation.frames], 'state': observation.state.name,
            'levels_completed': observation.levels_completed, 'available_actions': list(observation.available_actions),
            'win_levels': observation.win_levels, 'full_reset': observation.full_reset,
            'observation_sha256': observation.canonical_hash}


class Policy:
    def __init__(self, config):
        self.config = config
        self.history, self.hypotheses = [], []
        self.compact = []  # prompt-only renderings, aligned with history

    @property
    def rank(self):
        return STAGES.index(self.config.stage)

    def request(self, observation, rejection=None):
        contract = {'action': {'action_id': 'one legal integer from 1 to 7', 'action_data': 'x,y for ACTION6; otherwise {}'}}
        instructions = []
        encoding = self.config.grid_encoding
        evidence = {'current': prompt_observation(observation, encoding)}
        if self.config.observation_evidence_ids:
            evidence['current'] = {'observation_id': 'o%d' % len(self.history), **evidence['current']}
        if encoding == 'hex_rows' and evidence['current'].get('final_frame') is None:
            encoding = 'json'  # keep current and history in one representation
        if self.rank >= 1:
            shown = self.compact if encoding == 'hex_rows' else self.history
            evidence['history'] = shown[-self.config.history_limit:]
            evidence['history_omitted'] = max(0, len(self.history) - self.config.history_limit)
            if encoding == 'hex_rows':
                evidence['history'] = self.trim_boards(evidence['history'])
        if self.rank >= 2:
            evidence['hypotheses'] = self.hypotheses
            cite = 'supplied transition or observation ID' if self.config.observation_evidence_ids else 'supplied transition ID'
            contract['hypotheses'] = [{'id': 'short ID', 'statement': 'testable claim',
                'status': 'tentative|supported_locally|contradicted', 'evidence_ids': [cite]}]
            instructions.append('Keep competing hypotheses; tie each claim to available evidence. An empty list is allowed.')
            if self.config.observation_evidence_ids:
                instructions.append('evidence_ids may cite any transition so far (t1..t%d) or observed board (o0 is the '
                                    'initial board, oN the board after tN; o%d is the current board), including ones no '
                                    'longer shown. A status other than tentative needs at least one such ID.'
                                    % (len(self.history), len(self.history)))
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
        if rejection:
            # Only on a retry after the controller rejected a reply; no game action was sent in between.
            payload['previous_reply_rejected'] = str(rejection)[:500]
        return {'model': self.config.model, 'messages': [{'role': 'system', 'content': system_prompt(self.config)},
                {'role': 'user', 'content': json.dumps(payload, separators=(',', ':'), allow_nan=False)}],
                'max_tokens': self.config.max_output_tokens}

    def trim_boards(self, history):
        """Prompt-only: drop boards the model already has or that are older than history_board_limit entries."""
        limit, trimmed = self.config.history_board_limit, []
        for age, entry in zip(range(len(history) - 1, -1, -1), history):
            if not isinstance(entry['after'].get('final_frame'), list):
                trimmed.append(entry)
                continue
            if age == 0:  # the newest transition's result is the current board: never send it twice
                note = 'same as evidence.current.final_frame'
            elif limit and age >= limit:
                note = 'omitted (older than the %d newest entries); see changed_cells' % limit
            else:
                trimmed.append(entry)
                continue
            trimmed.append({**entry, 'after': {**entry['after'], 'final_frame': note}})
        return trimmed

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
            if self.config.observation_evidence_ids:
                # Every recorded transition and board is citable: each one is in the evidence log, so provenance holds.
                n = len(self.history)
                allowed |= {'t%d' % k for k in range(1, n + 1)} | {'o%d' % k for k in range(n + 1)}
            # Previously stored claims retain explicit provenance even when raw records have left the prompt.
            allowed |= {r for h in self.hypotheses for r in h['evidence_ids']}
            if not isinstance(hypotheses, list) or len(hypotheses) > 8:
                raise ValueError('at most eight hypotheses')
            ids = set()
            for h in hypotheses:
                if not isinstance(h, dict) or set(h) != {'id', 'statement', 'status', 'evidence_ids'}:
                    raise ValueError('invalid hypothesis shape')
                # Specific reasons: the retry receives this text and can only fix what it names.
                if not isinstance(h['id'], str) or not 1 <= len(h['id']) <= 64:
                    raise ValueError('hypothesis id must be a string of 1-64 characters')
                if h['id'] in ids:
                    raise ValueError('duplicate hypothesis id %r' % h['id'])
                if not isinstance(h['statement'], str) or not 1 <= len(h['statement']) <= 1000:
                    raise ValueError('hypothesis %r statement must be 1-1000 characters' % h['id'])
                if h['status'] not in ('tentative', 'supported_locally', 'contradicted'):
                    raise ValueError('hypothesis %r has an unknown status' % h['id'])
                if not isinstance(h['evidence_ids'], list) or any(not isinstance(r, str) for r in h['evidence_ids']):
                    raise ValueError('hypothesis %r evidence_ids must be a list of strings' % h['id'])
                if len(set(h['evidence_ids'])) != len(h['evidence_ids']):
                    raise ValueError('hypothesis %r repeats an evidence id' % h['id'])
                unavailable = sorted(set(h['evidence_ids']) - allowed)
                if unavailable:
                    raise ValueError('hypothesis %r cites unavailable evidence %s; citable: %s' % (
                        h['id'], unavailable, describe_citable(allowed)))
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
        if self.config.grid_encoding == 'hex_rows':
            self.compact.append(compact_transition(transition, before, after, self.config.observation_evidence_ids))
        if self.rank >= 2:
            self.hypotheses = answer['hypotheses']
            if facts['level_increased'] and self.config.clear_hypotheses_on_level:
                # Do not carry layout-specific coordinates/claims to the next level automatically.
                self.hypotheses = []
        return transition
