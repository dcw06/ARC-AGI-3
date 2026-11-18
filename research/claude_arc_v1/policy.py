"""Same text-grid policy for either backend; no teacher rules or solutions."""
import json
from agent.action import ActionDecision, serialize_action
from .config import STAGES, strict_json
from .recovery import REPLAY_NOTE, RESET_ALLOWED, CounterMask
from .things import Inventory

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
LESSONS_NOTE = ('evidence.game_over_lessons are the lessons you wrote after earlier GAME_OVERs in this game. The '
                'controller keeps them for you; they are not part of your hypotheses list and are never dropped.')
LESSON_ASK = ('Your last attempt ended in GAME_OVER at %s. In game_over_lesson, write what it teaches for the rest of '
              'this game. rule: what causes a game over, as a general rule about the objects involved. applies_when: '
              'how to tell, on any board, before acting, that an action would end the same way. Write both so they '
              'hold anywhere in this game, not only at the place where it happened; do not describe a route.')
CHECK_NOTE = ('In lesson_check, test the action you chose against every game_over_lesson: name any lesson that could '
              'apply and say what on the current board shows this action will not end the same way.')
LESSON_LIMIT = 6
IDLE_LIMIT = 6
IDLE_NOTE = ('evidence.no_effect_lessons are the explanations you wrote after earlier actions that changed nothing '
             'in this game, each with its number. The controller keeps them for you; they are not part of your '
             'hypotheses list. At most %d are kept: beyond that, a new lesson that replaces none drops the oldest.'
             % IDLE_LIMIT)
IDLE_CASE_NOTE = ('evidence.no_effect_case keeps an action of yours that left the board as it was (cells the '
                  'controller reads as a step counter aside), with that board and the actions you have taken since. '
                  'in_between says, for each such action, what the frames returned before the last one showed: an '
                  'action can do something on the way and still end on the same board, and that is often why. The '
                  'case stays there until you have explained it.')
IDLE_WAIT = ('No explanation of %s is wanted yet. From your next turn on, write it as soon as what you have seen is '
             'enough to tell why it left the board as it was. You decide when; it must be written once you have taken '
             '%d more action%s at the latest.')
IDLE_MAY = ('You may explain %s now%s. If that is enough to tell why it left the board as it was, write '
            'no_effect_lesson. If it is not, leave no_effect_lesson out and play on; it must be written once you have '
            'taken %d more action%s at the latest.')
IDLE_ASK = 'Explain now why %s left the board as it was%s: write no_effect_lesson.'
IDLE_FORMAT = ('no_effect_lesson has three parts. rule: the rule or mechanic of this game that explains why the action '
               'left the board as it was, stated generally about the objects, colours or positions involved. applies_when: '
               'how to tell, on any board, before acting, that an action would again leave the board as it is. Write both so they hold '
               'anywhere in this game, not only at this place. replaces: if one of your earlier no_effect_lessons '
               'already covers this case, or this case shows it wrong, give its number and write the corrected, more '
               'general lesson in its place; otherwise 0.')
IDLE_COMBINE = ', combining it with what your %d action%s since then showed (%s)'
THINGS_NOTE = ('evidence.things lists what is on the board apart from the large ground regions. The controller finds it '
               'from the cells alone and knows nothing about the game. Things are grouped by look: the same shape and '
               'colours, however turned or mirrored. Each instance has its box [x_first, y_first, x_last, y_last] and the '
               'last action at which its own cells changed (changed_at) or cells right beside it changed '
               '(beside_change_at); untouched means neither has happened on this level. does is your own note about that '
               'look. Things with one look are the same kind of object: what one of them did, the others most likely do '
               'as well. An untouched thing is one you know nothing about yet.')
ALIKE_NOTE = ('evidence.things.alike lists shapes that occur more than once on the board in another colour, another size, or '
              'turned or mirrored; differ_in says how the copies differ. The controller finds them from the cells alone. '
              'When one thing has to match another for something to work, every way the two differ is a candidate for '
              'what still has to be made equal. A difference that something on the board could change, an untouched '
              'thing for instance, is worth removing before you try. A difference that nothing on the board can change '
              'cannot be what is required.')
THING_NOTE_ASK = ('thing_note is optional. Write it when you have just seen what a look does: look is its letter, does is '
                  'what happens when you act on such a thing or reach it, said generally ("nothing" if it does nothing). '
                  'It replaces your earlier note for that look and is kept for the whole game, on later levels too. '
                  'Leave it out otherwise.')
THING_CHECK_ASK = ('In thing_check say which thing your action is aimed at. If a thing has the same look as one whose effect '
                   'you have seen, say whether using it would serve the goal here. If you do not yet know how to complete '
                   'the level and things are still untouched, say which one you will reach next, or why not.')
IDLE_CHECK_NOTE = ('In lesson_check, test the action you chose against every no_effect_lesson: name any lesson that '
                   'could apply and say what on the current board shows this action will change the board.')
BOTH_CHECK_NOTE = ('In lesson_check, test the action you chose against every game_over_lesson and every '
                   'no_effect_lesson: name any lesson that could apply and say what on the current board shows this '
                   'action will change the board and will not end the game.')
# The benchmark's own rule (ARC-AGI-3 scoring methodology), with nothing about how to play.
OBJECTIVE = (' Scoring: only completed levels score. A completed level scores (H / A) squared, capped at 1.15, '
             'where A is the number of actions you used on that level and H is the number a person needed when '
             'playing it for the first time. Every action you send counts in A, including one that changes nothing.')
GAME_OVER_NOTE = ('evidence.game_overs keeps every earlier action on this level that ended in GAME_OVER, with the '
                  'board before it and the board it produced. It stays available as evidence however long ago it '
                  'happened: cite its transition_id.')


def system_prompt(config):
    base = SYSTEM.replace('Never reset (action 0). ', RESET_ALLOWED) if config.model_may_reset else SYSTEM
    return (base + (HEX_NOTE if config.grid_encoding == 'hex_rows' else '')
            + (RESET_NOTE if config.resets_per_game else '')
            + (REPLAY_NOTE if config.replay_after_reset else '')
            + (OBJECTIVE if config.state_objective else ''))


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


def response_schema(stage, config=None):
    """JSON Schema for structured output. Policy.parse still applies every semantic check.

    With the recovery switches off (or no config) this is the schema of the control. The recovery fields
    are optional here because one schema serves the whole run; parse requires them exactly when asked for.
    """
    rank = STAGES.index(stage)
    lowest = 0 if config is not None and config.model_may_reset else 1
    properties = {'action': {'type': 'object', 'additionalProperties': False, 'required': ['action_id', 'action_data'],
        'properties': {'action_id': {'type': 'integer', 'minimum': lowest, 'maximum': 7},
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
    required = list(properties)
    if config is not None and (config.stall_window or config.stall_level_ratio):
        properties['recovery'] = {'type': 'object', 'additionalProperties': False, 'required': ['choice', 'reason'],
                                  'properties': {'choice': {'enum': ['continue', 'reset']},
                                                 'reason': {'type': 'string', 'maxLength': 1000}}}
    if config is not None and config.replay_after_reset:
        properties['replay'] = {'type': 'integer', 'minimum': 0}
    if config is not None and config.game_over_lessons:
        text = {'type': 'string', 'minLength': 1, 'maxLength': 600}
        properties['game_over_lesson'] = {'type': 'object', 'additionalProperties': False,
                                          'required': ['rule', 'applies_when'],
                                          'properties': {'rule': text, 'applies_when': text}}
        if config.lesson_check:
            properties['lesson_check'] = text
    if config is not None and config.no_effect_lessons:
        text = {'type': 'string', 'minLength': 1, 'maxLength': 600}
        if config.lesson_check:
            properties.setdefault('lesson_check', text)
        properties['no_effect_lesson'] = {'type': 'object', 'additionalProperties': False,
                                          'required': ['rule', 'applies_when', 'replaces'],
                                          'properties': {'rule': text, 'applies_when': text,
                                                         'replaces': {'type': 'integer', 'minimum': 0}}}
    if config is not None and config.object_ledger:
        properties['thing_check'] = {'type': 'string', 'minLength': 1, 'maxLength': 400}
        properties['thing_note'] = {'type': 'object', 'additionalProperties': False, 'required': ['look', 'does'],
                                    'properties': {'look': {'type': 'string', 'minLength': 1, 'maxLength': 3},
                                                   'does': {'type': 'string', 'minLength': 1, 'maxLength': 300}}}
    return {'type': 'object', 'additionalProperties': False, 'required': required, 'properties': properties}


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
        self.lessons = []  # game-over lessons, kept for the whole game (memory fix; empty in the control)
        self.idle = []     # no-effect lessons, kept for the whole game (empty unless no_effect_lessons)
        self.idle_case = None           # the action that changed nothing and still has to be explained, or None
        self.counter = CounterMask()    # which cells are a step counter, learned as play goes on
        self.inventory = Inventory()    # the things on the board and what has happened at each (object_ledger)
        self.thing_notes = {}           # look letter -> the agent's note of what that look does, for the whole game
        self.looks_shown = set()        # the look letters in the request now being answered

    @property
    def rank(self):
        return STAGES.index(self.config.stage)

    def idle_state(self):
        """(may explain now, must explain now) for the open no-effect case.

        With no_effect_wait 0 the explanation is due on the next turn. Otherwise the agent decides: it may
        write it once at least one further action of its own has followed, and must once no_effect_wait have."""
        case = self.idle_case
        if not case or not self.config.no_effect_lessons:
            return False, False
        limit, taken = self.config.no_effect_wait, len(case['since'])
        return (True, True) if not limit else (taken >= 1, taken >= limit)

    def request(self, observation, rejection=None, recovery=None):
        """recovery (recovery study only): {'check': facts or None, 'offer': ended attempt or None, ...}."""
        contract = {'action': {'action_id': 'one legal integer from 1 to 7', 'action_data': 'x,y for ACTION6; otherwise {}'}}
        if self.config.model_may_reset:
            contract['action']['action_id'] = 'one legal integer from 1 to 7, or 0 to reset the level'
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
        if self.config.game_over_lessons:
            if self.lessons:
                evidence['game_over_lessons'] = self.lessons
                instructions.append(LESSONS_NOTE)
            due = self.lesson_due()
            if due:
                contract['game_over_lesson'] = {'rule': 'general rule, at most 600 characters',
                                                'applies_when': 'how to recognise it elsewhere, at most 600 characters'}
                instructions.append(LESSON_ASK % due)
            if self.config.lesson_check and self.lessons and not (self.config.no_effect_lessons and self.idle):
                contract['lesson_check'] = 'one or two sentences, at most 600 characters'
                instructions.append(CHECK_NOTE)
        if self.config.no_effect_lessons:
            if self.idle:
                evidence['no_effect_lessons'] = [{'number': n, **item} for n, item in enumerate(self.idle, 1)]
                instructions.append(IDLE_NOTE)
            case = self.idle_case
            if case:
                since, limit = case['since'], self.config.no_effect_wait
                may, must = self.idle_state()
                evidence['no_effect_case'] = {
                    'transition_id': case['transition_id'], 'action': case['action'],
                    # with no action since, the board is the one already shown as current
                    'board': case['board'] if since else 'same as evidence.current.final_frame',
                    'actions_since': since, 'of_those_also_changed_nothing': case['nothing'],
                    'in_between': case['in_between']}
                instructions.append(IDLE_CASE_NOTE)
                plural = lambda n: '' if n == 1 else 's'
                if may:
                    contract['no_effect_lesson'] = {'rule': 'general rule, at most 600 characters',
                                                    'applies_when': 'how to recognise it before acting, at most 600 characters',
                                                    'replaces': 'number of the earlier lesson this one replaces, or 0'}
                    combine = IDLE_COMBINE % (len(since), plural(len(since)), ', '.join(since)) if since else ''
                    left = limit - len(since)
                    instructions.append(IDLE_ASK % (case['transition_id'], combine) if must else
                                        IDLE_MAY % (case['transition_id'], combine, left, plural(left)))
                    instructions.append(IDLE_FORMAT)
                else:
                    instructions.append(IDLE_WAIT % (case['transition_id'], limit, plural(limit)))
            if self.config.lesson_check and self.idle:
                contract['lesson_check'] = 'one or two sentences, at most 600 characters'
                instructions.append(BOTH_CHECK_NOTE if self.lessons else IDLE_CHECK_NOTE)
        if self.config.object_ledger:
            listing = self.inventory.listing(observation.latest_frame, self.thing_notes)
            self.looks_shown = {look['look'] for look in listing['looks']}
            if self.looks_shown:
                evidence['things'] = listing
                contract['thing_check'] = 'one or two sentences, at most 400 characters'
                contract['thing_note'] = {'look': 'the letter of a look in evidence.things',
                                          'does': 'what that kind of thing does, at most 300 characters'}
                instructions.extend((THINGS_NOTE, THING_NOTE_ASK, THING_CHECK_ASK))
                if self.config.pattern_relations:
                    alike = self.inventory.alike(observation.latest_frame)
                    if alike:
                        listing['alike'] = alike
                        instructions.append(ALIKE_NOTE)
        if self.config.pin_game_overs:
            pinned = self.game_overs(observation.levels_completed)
            if pinned:
                evidence['game_overs'] = pinned
                instructions.append(GAME_OVER_NOTE)
        if recovery and recovery.get('check'):
            evidence['recovery_check'] = recovery['check']
            contract['recovery'] = {'choice': 'continue|reset', 'reason': 'the observation that decides it'}
            instructions.append('A recovery check is due: read evidence.recovery_check and answer in recovery.')
        if recovery and recovery.get('offer'):
            evidence['replay_offer'] = recovery['offer']
            contract['replay'] = 'whole number from 0 to %d' % recovery['offer']['largest_replay']
            instructions.append('You have just been reset: read evidence.replay_offer and set replay.')
        payload = {'evidence': evidence, 'output_contract': contract, 'procedure': instructions}
        if rejection:
            # Only on a retry after the controller rejected a reply; no game action was sent in between.
            payload['previous_reply_rejected'] = str(rejection)[:500]
        return {'model': self.config.model, 'messages': [{'role': 'system', 'content': system_prompt(self.config)},
                {'role': 'user', 'content': json.dumps(payload, separators=(',', ':'), allow_nan=False)}],
                'max_tokens': self.config.max_output_tokens}

    def in_between(self, before, after):
        """What an action showed on the way to a board equal to the one it started from: the changes in the
        returned frame that differed most from that board (step-counter cells aside). The model is otherwise
        never shown the frames before the last one."""
        import numpy as np
        base, mask = np.asarray(before.latest_frame), self.counter.mask
        peak, most = None, 0
        for frame in after.frames[:-1]:
            frame = np.asarray(frame)
            if frame.shape != base.shape:
                continue
            differs = frame != base
            if mask is not None and mask.shape == differs.shape:
                differs = differs & ~mask
            if int(differs.sum()) > most:
                peak, most = frame, int(differs.sum())
        if peak is None:
            return 'no frame in between differed from the board'
        return {'frames_returned': len(after.frames), 'cells_that_differed': most,
                'changes_in_that_frame': changed_cells(base, peak)}

    def lesson_due(self):
        """The fatal transition's id when the last thing that happened is the reset after a GAME_OVER
        for which no lesson has been written yet; otherwise None."""
        if len(self.history) < 2:
            return None
        reset, fatal = self.history[-1], self.history[-2]
        if reset['action']['action_id'] != 0 or reset['before']['state'] != 'GAME_OVER':
            return None
        if any(lesson['after'] == fatal['transition_id'] for lesson in self.lessons):
            return None
        return fatal['transition_id']

    def game_overs(self, level):
        """The current level's most recent actions that ended in GAME_OVER, as evidence that never scrolls away."""
        import numpy as np

        def board(value):
            frame = np.asarray(value['frames'][-1])
            return hex_rows(frame) or frame.tolist()
        records = []
        for index, transition in enumerate(self.history):
            before, after = transition['before'], transition['after']
            if after['state'] != 'GAME_OVER' or before['levels_completed'] != level:
                continue
            records.append({'transition_id': transition['transition_id'], 'action': transition['action'],
                            'frames_returned': len(after['frames']),
                            'before': {'observation_id': 'o%d' % index, 'final_frame': board(before)},
                            'after': {'observation_id': 'o%d' % (index + 1), 'state': 'GAME_OVER',
                                      'final_frame': board(after)}})
        return records[-self.config.pin_game_overs:]

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

    def parse(self, text, observation, recovery=None):
        value = strict_json(text)
        check = bool(recovery and recovery.get('check'))
        offer = recovery.get('offer') if recovery else None
        due = self.lesson_due() if self.config.game_over_lessons else None
        may_explain, must_explain = self.idle_state()
        checking = bool(self.config.lesson_check and (self.lessons or self.idle))
        if isinstance(value, dict) and self.config.game_over_lessons:
            if not due:
                value.pop('game_over_lesson', None)
            elif 'game_over_lesson' not in value:
                raise ValueError('your last attempt ended in GAME_OVER: write game_over_lesson {rule, applies_when}')
            if not checking:
                value.pop('lesson_check', None)
            elif 'lesson_check' not in value:
                raise ValueError('lesson_check is required while game_over_lessons exist' if not self.config.no_effect_lessons
                                 else 'lesson_check is required while lessons exist')
        if isinstance(value, dict) and self.config.no_effect_lessons:
            if not may_explain or (not must_explain and value.get('no_effect_lesson') is None):
                value.pop('no_effect_lesson', None)       # not asked for, or "not yet" while the choice is the agent's
            elif 'no_effect_lesson' not in value:
                raise ValueError('your action %s changed nothing and must be explained now: write no_effect_lesson '
                                 '{rule, applies_when, replaces}' % self.idle_case['transition_id'])
            if not checking:
                value.pop('lesson_check', None)
            elif 'lesson_check' not in value:
                raise ValueError('lesson_check is required while lessons exist')
        explaining = isinstance(value, dict) and may_explain and 'no_effect_lesson' in value
        looks = self.looks_shown if self.config.object_ledger else set()
        if isinstance(value, dict) and self.config.object_ledger:
            if not looks or value.get('thing_note') is None:
                value.pop('thing_note', None)             # optional, and meaningless with nothing listed
            if not looks:
                value.pop('thing_check', None)
            elif 'thing_check' not in value:
                raise ValueError('thing_check is required: say which thing in evidence.things your action is aimed at')
        noting = isinstance(value, dict) and bool(looks) and 'thing_note' in value
        if isinstance(value, dict):
            # One schema serves the whole run, so a reply may carry a recovery field nobody asked for this
            # turn. It is dropped, not rejected. In the control the schema has no such field.
            if not check and (self.config.stall_window or self.config.stall_level_ratio):
                value.pop('recovery', None)
            if not offer and self.config.replay_after_reset and value.get('replay') == 0:
                value.pop('replay')
            if check and 'recovery' not in value:
                raise ValueError('a recovery check is due: answer it in recovery {choice, reason}')
            if offer and 'replay' not in value:
                raise ValueError('a replay offer is present: set replay (0 for none)')
            if not offer and 'replay' in value and self.config.replay_after_reset:
                raise ValueError('replay is only available on the turn after a reset, when replay_offer is present')
        expected = {'action'} | ({'hypotheses'} if self.rank >= 2 else set())
        expected |= ({'recovery'} if check else set()) | ({'replay'} if offer else set())
        expected |= ({'game_over_lesson'} if due else set()) | ({'lesson_check'} if checking else set())
        expected |= {'no_effect_lesson'} if explaining else set()
        expected |= ({'thing_check'} if looks else set()) | ({'thing_note'} if noting else set())
        expected |= {'experiment'} if self.rank >= 3 else set()
        expected |= {'prediction'} if self.rank >= 4 else set()
        expected |= {'plan'} if self.rank >= 5 else set()
        if not isinstance(value, dict) or set(value) != expected:
            raise ValueError('response does not match stage contract; no repair or fallback')
        action = value['action']
        if due:
            lesson = value['game_over_lesson']
            if (not isinstance(lesson, dict) or set(lesson) != {'rule', 'applies_when'}
                    or any(not isinstance(v, str) or not 1 <= len(v) <= 600 for v in lesson.values())):
                raise ValueError('game_over_lesson needs rule and applies_when, each 1 to 600 characters')
        if checking and (not isinstance(value['lesson_check'], str) or not 1 <= len(value['lesson_check']) <= 600):
            raise ValueError('lesson_check must be 1 to 600 characters')
        if looks and (not isinstance(value['thing_check'], str) or not 1 <= len(value['thing_check']) <= 400):
            raise ValueError('thing_check must be 1 to 400 characters')
        if noting:
            note = value['thing_note']
            if (not isinstance(note, dict) or set(note) != {'look', 'does'} or not isinstance(note['does'], str)
                    or not 1 <= len(note['does']) <= 300):
                raise ValueError('thing_note needs look and does (1 to 300 characters)')
            if note['look'] not in looks:
                raise ValueError('thing_note.look must be the letter of a look in evidence.things: %s'
                                 % ', '.join(sorted(looks, key=lambda s: (len(s), s))))
        if explaining:
            lesson = value['no_effect_lesson']
            if (not isinstance(lesson, dict) or set(lesson) != {'rule', 'applies_when', 'replaces'}
                    or any(not isinstance(lesson[k], str) or not 1 <= len(lesson[k]) <= 600 for k in ('rule', 'applies_when'))):
                raise ValueError('no_effect_lesson needs rule and applies_when, each 1 to 600 characters, and replaces')
            if type(lesson['replaces']) is not int or not 0 <= lesson['replaces'] <= len(self.idle):
                raise ValueError('no_effect_lesson.replaces must be 0 or the number of an existing lesson (1 to %d)'
                                 % len(self.idle))
        lowest = 0 if self.config.model_may_reset else 1
        if (not isinstance(action, dict) or set(action) != {'action_id', 'action_data'}
                or type(action['action_id']) is not int or not lowest <= action['action_id'] <= 7
                or not isinstance(action['action_data'], dict)):
            raise ValueError('invalid action shape/type')
        data = action['action_data']
        resetting = action['action_id'] == 0
        if resetting:
            if data:
                raise ValueError('a reset takes empty action_data')
            if not recovery or not recovery.get('may_reset'):
                raise ValueError('reset refused: no action has been taken on this attempt yet')
            if self.config.recovery_pricing and not recovery['reset_pays_back']:
                raise ValueError('reset refused: too few actions remain for a new attempt')
        if check:
            answer = value['recovery']
            if (not isinstance(answer, dict) or set(answer) != {'choice', 'reason'}
                    or answer['choice'] not in ('continue', 'reset')
                    or not isinstance(answer['reason'], str) or len(answer['reason']) > 1000):
                raise ValueError('recovery needs choice "continue" or "reset" and a reason of at most 1000 characters')
            if (answer['choice'] == 'reset') != resetting:
                raise ValueError('recovery.choice and the action disagree: a reset is action 0')
        if offer:
            count = value['replay']
            if type(count) is not int or not 0 <= count <= offer['largest_replay']:
                raise ValueError('replay must be a whole number from 0 to %d' % offer['largest_replay'])
        if action['action_id'] == 6 and (set(data) != {'x', 'y'} or any(type(data[k]) is not int for k in data)):
            raise ValueError('click needs strictly integer x,y')
        decision = ActionDecision(action['action_id'], data, source='api_evaluation')
        serialize_action(decision, game_id=observation.game_id, guid=observation.guid,
                         legal_actions=observation.available_actions, allow_level_reset=resetting)
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
        if 'game_over_lesson' in answer:
            # Written on the turn after the reset that followed a GAME_OVER; kept for the rest of the game.
            fatal = self.lesson_due()
            self.lessons = (self.lessons + [{'after': fatal, 'level': before.levels_completed + 1,
                                             **answer['game_over_lesson']}])[-LESSON_LIMIT:]
        if self.config.no_effect_lessons:
            tid = transition['transition_id']
            if 'no_effect_lesson' in answer:
                # Written once enough actions have followed the one that changed nothing; kept for the rest of
                # the game. A lesson that replaces an earlier one takes its place, so the list stays short.
                lesson = answer['no_effect_lesson']
                item = {'after': self.idle_case['transition_id'], 'through': 't%d' % len(self.history),
                        'level': before.levels_completed + 1, 'rule': lesson['rule'], 'applies_when': lesson['applies_when']}
                if lesson['replaces']:
                    self.idle = self.idle[:lesson['replaces'] - 1] + [item] + self.idle[lesson['replaces']:]
                else:
                    self.idle = (self.idle + [item])[-IDLE_LIMIT:]
                self.idle_case = None
            if self.idle_case is not None and decision.action_id != 0:
                self.idle_case['since'].append(tid)     # one of the agent's own actions that follow it
            nothing = False
            if decision.action_id == 0 or facts['level_increased']:
                self.counter.restart()      # a new attempt: the counter may run again from its start
            elif before.state.name == 'NOT_FINISHED' and after.state.name == 'NOT_FINISHED':
                self.counter.update(before.latest_frame, after.latest_frame)
                nothing = self.counter.key(before.latest_frame) == self.counter.key(after.latest_frame)
            if nothing and self.idle_case is None and decision.source != 'controller_resume':
                # (a saved action repeated when a run is resumed teaches the counter but opens no case: the
                # agent has no turn there in which it could explain it)
                frame = np.asarray(before.latest_frame)
                self.idle_case = {'transition_id': tid, 'action': transition['action'],
                                  'board': hex_rows(frame) or frame.tolist(), 'since': [], 'nothing': [],
                                  'in_between': {tid: self.in_between(before, after)}}
            elif nothing and self.idle_case is not None:
                self.idle_case['nothing'].append(tid)     # a further one while the case is open: explained together
                self.idle_case['in_between'][tid] = self.in_between(before, after)
        if self.config.object_ledger:
            if not self.config.no_effect_lessons:     # otherwise the step counter was learned just above
                if decision.action_id == 0 or facts['level_increased']:
                    self.counter.restart()
                elif before.state.name == 'NOT_FINISHED' and after.state.name == 'NOT_FINISHED':
                    self.counter.update(before.latest_frame, after.latest_frame)
            if 'thing_note' in answer:
                self.thing_notes[answer['thing_note']['look']] = answer['thing_note']['does']
            if facts['level_increased']:
                self.inventory.new_level()            # a new board: nothing has happened at its things yet
            elif decision.action_id != 0:
                data = decision.action_data
                self.inventory.observe(before.latest_frame, after.frames, transition['transition_id'],
                                       click=(data['x'], data['y']) if decision.action_id == 6 else None,
                                       ignore=self.counter.mask)
        self.history.append(transition)
        if self.config.grid_encoding == 'hex_rows':
            self.compact.append(compact_transition(transition, before, after, self.config.observation_evidence_ids))
        if self.rank >= 2:
            self.hypotheses = answer['hypotheses']
            if facts['level_increased'] and self.config.clear_hypotheses_on_level:
                # Do not carry layout-specific coordinates/claims to the next level automatically.
                self.hypotheses = []
        return transition
