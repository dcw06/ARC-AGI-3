"""CPU verification of the frozen detector and its integration with supervision and outcomes (hand-written).

Read-only over the unchanged science (detector.py, supervision.py, intervention.py, outcomes.py, thresholds.py,
trigger_spec.json, fixtures.py): nothing here changes a threshold, label, window, cap or endpoint. Sections:

  causality             the detector, triggers, supervision decisions, reflection requests and transition records
                        at step t depend only on records 0..t (prefix replays on all 152 fixture trajectories);
  thresholds            state_action_recurrence fires at the 2nd exact (frame, action) repeat, tiny_effect_repeat at
                        the 10th identical <=4-cell action; cooldown 6; failed dispatches neither extend nor break a
                        streak, unknown outcomes break it; all values read from the frozen trigger spec;
  continuation          false-intervention rates on the held-out hard negatives and, descriptively, on the archived
                        real development play under the protocol's LC labels;
  terminal_and_failures terminal states, resets, level changes, unobserved states, failed/unknown dispatches,
                        reflection exceptions and non-stop finishes in the supervision layer and the outcome windows;
  display_vs_progress   moving displays and oscillation versus genuine escape and level completion, synthetic and
                        (descriptively) on ls20 itself, keeping loop exit, state novelty, oscillation, false
                        interruptions and completed levels as separate quantities.
`display_report` is the descriptive ls20 display/oscillation report the 2026-10-02 retention decision requires. It is
post hoc, reads retained frames only and feeds no endpoint, label, gate or decision.
"""
import copy
import hashlib
import json
from pathlib import Path

from research.stagnation_supervision_v1 import detector as D, fixtures as F, intervention as I
from research.stagnation_supervision_v1 import outcomes as O, supervision as SV, thresholds as S
from research.stagnation_supervision_v1.closed_loop import bridge as B
from research.transition_evidence_v2 import transition as T2, vocabulary as V

ROOT = Path(__file__).resolve().parents[2]
BOTTOM_ROWS_FROM = 60  # the display region used by the post-hoc Tier B inspection (tier_b_inspection.BOTTOM_ROWS_FROM)
VERSION = 'stagnation_supervision_runtime_v2_detector_verification_v1'


# ---------------------------------------------------------------------------------------------------- helpers

def frame(size=12, fill=0, cells=()):
    grid = [[fill] * size for _ in range(size)]
    for x, y, colour in cells:
        grid[y][x] = colour
    return grid


class Script:
    """Raw transitions (transition_evidence input format) for constructed scenarios."""

    def __init__(self, episode='scenario', available=(1, 2, 3, 4, 6)):
        self.episode, self.available, self.raws = episode, list(available), []
        self.levels = 0

    def obs(self, grid, state='NOT_FINISHED', full_reset=False):
        return {'frames': [copy.deepcopy(grid)], 'levels_completed': self.levels, 'state': state,
                'full_reset': full_reset, 'available_actions': list(self.available)}

    def step(self, before, action, after=None, *, outcome='acknowledged', state='NOT_FINISHED', level_up=False,
             reset=False):
        raw = {'identity': {'episode_id': self.episode, 'action_index': len(self.raws)}, 'before': self.obs(before),
               'proposal': None, 'dispatched': copy.deepcopy(action), 'environment_source': 'synthetic_verification'}
        if outcome == 'failed':
            raw['outcome'] = {'status': 'failed', 'reason': 'rejected before acknowledgement'}
        elif outcome == 'outcome_unknown':
            raw['outcome'] = {'status': 'outcome_unknown', 'reason': 'sent; result not observed'}
        else:
            self.levels += int(level_up)
            raw['outcome'] = {'status': 'acknowledged', 'after': self.obs(after, state=state, full_reset=reset)}
        self.raws.append(raw)
        return raw

    def records(self):
        return T2.history(self.raws)


def act(action_id, x=None, y=None):
    return {'action_id': action_id, 'action_data': {} if x is None else {'x': x, 'y': y}}


def spec():
    return S.load()


def valid_reflection(request_text, last_action=1):
    content = json.loads(request_text.split('Evidence:\n', 1)[1])
    shown = [e['action_index'] for e in content['evidence']]
    legal = [a for a in content['available_actions'] if a != 6] or [content['available_actions'][0]]
    choice = next((a for a in legal if a != last_action), legal[0])
    return json.dumps({'observed_pattern': 'The same action repeats with no lasting change.',
                       'evidence_refs': shown[-2:], 'assumption_to_reconsider': 'That repeating it will help.',
                       'distinguishing_test': {'description': 'Try a different action once.',
                                               'actions': [{'action_id': choice, 'action_data': {}}]}})


def responder(script=None):
    """A reflection service double: each item is 'valid', 'length', 'raise' or a raw text."""
    queue = list(script or [])

    def call(text):
        item = queue.pop(0) if queue else 'valid'
        if item == 'raise':
            raise ConnectionError('verification transport failure')
        if item == 'length':
            return {'text': '{"truncated', 'input_tokens': 100, 'output_tokens': 400, 'finish_reason': 'length',
                    'latency_s': 0.0}
        body = valid_reflection(text) if item == 'valid' else item
        return {'text': body, 'input_tokens': 100, 'output_tokens': 50, 'finish_reason': 'stop', 'latency_s': 0.0}
    return call


def supervise(raws, arm='triggered', outputs=None, episode_actions=40, remaining=None):
    sup = SV.Supervisor(arm, spec(), responder(outputs), B.EXPERIMENT_POLICY, clock=lambda: 0.0,
                        episode_actions=episode_actions, token_counter=lambda text: 100)
    events = []
    for i, raw in enumerate(raws):
        after = (raw['outcome'].get('after') or {}).get('state')
        ended = raw['outcome']['status'] != 'acknowledged' or after in ('WIN', 'GAME_OVER')
        events.append(sup.observe(raw, remaining_actions=0 if ended else (
            remaining[i] if remaining else episode_actions - (i + 1))))
    return sup, events


def _strip(event):
    value = copy.deepcopy(event)
    if 'call' in value:
        value['call'].pop('latency_s', None)
    return value


# ---------------------------------------------------------------------------------------------------- sections

def causality():
    params, cooldown = spec()['params'], spec()['cooldown_actions']
    checked = steps = 0
    failures = []
    for partition in ('development', 'evaluation'):
        generated = F.generate(partition)
        for fixture in generated['fixtures']:
            raws = fixture['raws']
            records = T2.history(raws)
            stats = D.statistics(records)
            full = [D.signals(s, params) for s in stats]
            triggers = D.triggers(stats, params, cooldown)
            for t in range(len(records)):
                prefix_records = T2.history(raws[:t + 1])
                if json.dumps(prefix_records[-1], sort_keys=True) != json.dumps(records[t], sort_keys=True):
                    failures.append(f"{fixture['id']}: transition record {t} depends on later raws")
                prefix_stats = D.statistics(prefix_records)
                if D.signals(prefix_stats[-1], params) != full[t]:
                    failures.append(f"{fixture['id']}: detector signals at {t} depend on later records")
                if D.triggers(prefix_stats, params, cooldown)[-1] != triggers[t]:
                    failures.append(f"{fixture['id']}: trigger decision at {t} depends on later records")
                request_full = I.build_request(records, t, 'triggered', full[t])
                request_prefix = I.build_request(prefix_records, t, 'triggered', full[t])
                if request_full['text'] != request_prefix['text']:
                    failures.append(f"{fixture['id']}: reflection request at {t} sees later records")
                steps += 1
            # Supervision decisions (both reflection arms) at every step equal those of a prefix-only replay.
            for arm in ('periodic', 'triggered'):
                horizon = max(len(raws), 1)
                _, events = supervise([dict(r, identity={**r['identity'], 'episode_id': fixture['id']}) for r in raws],
                                      arm=arm, episode_actions=horizon)
                for t in sorted({0, len(raws) // 2, len(raws) - 1}):
                    _, prefix = supervise([dict(r, identity={**r['identity'], 'episode_id': fixture['id']})
                                           for r in raws[:t + 1]], arm=arm, episode_actions=horizon,
                                          remaining=[horizon - (i + 1) for i in range(t + 1)])
                    if _strip(prefix[t]) != _strip(events[t]):
                        failures.append(f"{fixture['id']} {arm}: supervision event {t} depends on later records")
            checked += 1
    return {'passed': not failures, 'trajectories': checked, 'steps_prefix_replayed': steps, 'failures': failures[:20]}


def thresholds():
    frozen = spec()
    expected = {'repeat_no_effect': None, 'state_action_recurrence': 2, 'tiny_effect_repeat': 10, 'novelty_stall': None,
                'prediction_failures': None, 'no_progress_horizon': None}
    out = {'spec_params': frozen['params'], 'cooldown_actions': frozen['cooldown_actions'], 'tiny_cells': frozen['tiny_cells']}
    problems = []
    if frozen['params'] != expected or frozen['cooldown_actions'] != 6 or frozen['tiny_cells'] != 4 or D.TINY_CELLS != 4:
        problems.append('frozen trigger values differ from protocol v2')
    params = frozen['params']

    def firing(raws):
        return [sorted(s['signal'] for s in D.signals(st, params)) for st in D.statistics(T2.history(raws))]

    static = frame()
    s = Script()
    s.step(static, act(5), static)
    s.step(static, act(5), static)
    fired = firing(s.raws)
    out['recurrence_second_repeat'] = fired
    if fired != [[], ['state_action_recurrence']]:
        problems.append('state_action_recurrence must fire at the 2nd exact repeat only')
    s = Script()
    for a in (1, 2, 1):
        s.step(static, act(a), static)
    if firing(s.raws) != [[], [], ['state_action_recurrence']]:
        problems.append('alternating actions must not count as one pair')

    def counter_run(n, cells_per_step=1, inserts=None):
        script, current = Script(), 0
        inserts = inserts or {}
        for i in range(n):
            before = frame(cells=[(k % 12, 11 - k // 12, 9) for k in range(current)])
            kind = inserts.get(i)
            if kind in ('failed', 'outcome_unknown'):
                script.step(before, act(6, 3, 3), outcome=kind)
                if kind == 'outcome_unknown':
                    current += cells_per_step
                continue
            current += cells_per_step
            script.step(before, act(6, 3, 3), frame(cells=[(k % 12, 11 - k // 12, 9) for k in range(current)]))
        return script.raws

    fired = firing(counter_run(10))
    out['tiny_streak_first_firing_index'] = next((i for i, f in enumerate(fired) if f), None)
    if out['tiny_streak_first_firing_index'] != 9 or any(fired[:9]):
        problems.append('tiny_effect_repeat must fire at the 10th identical tiny action, never earlier')
    fired = firing(counter_run(11, inserts={4: 'failed'}))
    out['tiny_streak_with_failed_dispatch_first_firing_index'] = next((i for i, f in enumerate(fired) if f), None)
    if out['tiny_streak_with_failed_dispatch_first_firing_index'] != 10:
        problems.append('a failed dispatch must neither extend nor break the streak')
    fired = firing(counter_run(16, inserts={4: 'outcome_unknown'}))
    out['tiny_streak_with_unknown_outcome_first_firing_index'] = next((i for i, f in enumerate(fired) if f), None)
    if out['tiny_streak_with_unknown_outcome_first_firing_index'] != 14:  # streak restarts at 5: 5..14 is ten
        problems.append('an unknown outcome must break the streak')

    def painted(per_step):
        """Cumulative painting: every frame is new and every step changes exactly `per_step` cells."""
        script, cells = Script(), []
        for i in range(10):
            before = frame(cells=cells)
            cells = cells + [((len(cells) + k) % 12, (len(cells) + k) // 12, 5) for k in range(per_step)]
            script.step(before, act(6, 3, 3), frame(cells=cells))
        return firing(script.raws)
    four, five = painted(4), painted(5)
    out['four_cells_tiny'], out['five_cells_tiny'] = bool(four[9]), bool(five[9])
    if not four[9] or any(five):
        problems.append('the 4-cell boundary is inclusive and 5 cells are not tiny')
    # Cooldown: consecutive firings trigger at t and again only from t + 6.
    s = Script()
    for _ in range(14):
        s.step(static, act(5), static)
    decisions = D.triggers(D.statistics(s.records()), params, frozen['cooldown_actions'])
    out['cooldown_trigger_steps'] = [d['action_index'] for d in decisions if d['trigger']]
    if out['cooldown_trigger_steps'] != [1, 7, 13]:
        problems.append('cooldown of 6 actions not applied')
    out['passed'] = not problems
    out['problems'] = problems
    return out


def continuation():
    data = S.prepared(F.generate('evaluation'))
    metrics, rows = S.score(data, spec()['params'], detail=True)
    families = sorted({r['family'] for r in rows if r['false_triggers']})
    retained = json.loads((ROOT / 'research/stagnation_supervision_v1/evaluation_results.json').read_bytes())
    held_out = {'false_intervention_trajectories': metrics['false_intervention_trajectories'],
                'trajectories': metrics['trajectories'], 'hard_negatives_with_false_intervention':
                    metrics['hard_negatives_with_false_intervention'], 'hard_negatives': metrics['hard_negative_trajectories'],
                'families_with_false_interventions': families, 'recall': metrics['recall'], 'precision': metrics['precision']}
    from research.stagnation_supervision_v1 import archive_diagnostic as A
    _, episodes = A.episodes()
    real = {}
    for episode, raws in episodes:
        records = T2.history(raws)
        labels = O.labels(records)
        triggers = [d['action_index'] for d in D.triggers(D.statistics(records), spec()['params'],
                                                           spec()['cooldown_actions']) if d['trigger']]
        game = episode['game_id'].split('-')[0]
        g = real.setdefault(game, {'episodes': 0, 'steps': 0, 'triggers': 0, 'lc_points': 0, 'st_points': 0,
                                   'triggers_at_lc': 0, 'trigger_steps_at_lc': []})
        g['episodes'] += 1
        g['steps'] += len(records)
        g['triggers'] += len(triggers)
        g['lc_points'] += labels.count('LC')
        g['st_points'] += labels.count('ST')
        hits = [t for t in triggers if labels[t] == 'LC']
        g['triggers_at_lc'] += len(hits)
        g['trigger_steps_at_lc'] += [f"{episode['episode_id']}@{t}" for t in hits]
    return {'held_out_fixtures': held_out,
            'held_out_matches_retained_results': metrics == retained['detectors']['selected']['metrics'],
            'archived_real_development_play': real,
            'note': ('Descriptive. The archive is 12-step episodes of exposed development play without intervention; '
                     'labels are the frozen mechanical LC/ST rule, not independent judgements.'),
            'passed': (metrics['false_intervention_trajectories'] == 4 and families == ['delayed_effect']
                       and metrics['hard_negatives_with_false_intervention'] == 4)}


def terminal_and_failures():
    problems, out = [], {}
    static = frame()
    # Terminal state at a firing step: no reflection, remaining 0.
    s = Script()
    s.step(static, act(5), static)
    s.step(static, act(5), static, state='GAME_OVER')
    _, events = supervise(s.raws)
    out['terminal'] = {k: events[1].get(k) for k in ('outcome', 'remaining_actions', 'detector_signals')}
    if events[1]['outcome'] != 'suppressed_terminal_state' or events[1]['remaining_actions'] != 0 or 'call' in events[1]:
        problems.append('terminal state must suppress reflection with 0 remaining actions')
    # Level change at a firing step suppresses; statistics restart in the new segment.
    s = Script()
    s.step(static, act(5), static)
    s.step(static, act(5), static, level_up=True)
    s.step(static, act(5), static)
    _, events = supervise(s.raws)
    out['level_change'] = [e['outcome'] for e in events]
    if events[1]['outcome'] != 'suppressed_segment_boundary' or events[2]['detector_signals']:
        problems.append('a level change must suppress reflection and clear detector statistics')
    s = Script()
    s.step(static, act(5), static)
    s.step(static, act(5), static, reset=True)
    s.step(static, act(5), static)
    _, events = supervise(s.raws)
    out['reset'] = [e['outcome'] for e in events]
    if events[1]['outcome'] != 'suppressed_segment_boundary' or events[2]['detector_signals']:
        problems.append('a reset must suppress reflection and clear detector statistics')
    # Failed dispatches alone never fire; an unknown outcome defers a due reflection.
    s = Script()
    for _ in range(6):
        s.step(static, act(5), outcome='failed')
    _, events = supervise(s.raws)
    out['failed_only_firings'] = sum(bool(e['detector_signals']) for e in events)
    if out['failed_only_firings']:
        problems.append('failed dispatches must never fire the detector')
    s = Script()
    for i in range(10):
        before = frame(cells=[(i, 4, 2)])
        s.step(before, act(5), frame(cells=[(i + 1, 4, 2)]) if i != 9 else None,
               outcome='outcome_unknown' if i == 9 else 'acknowledged')
    _, events = supervise(s.raws, arm='periodic')  # runner semantics: an unknown outcome ends play (0 remaining)
    out['unknown_at_periodic_due_runner'] = events[9]['outcome']
    direct = SV.Supervisor('periodic', spec(), responder(), B.EXPERIMENT_POLICY, clock=lambda: 0.0, episode_actions=40,
                           token_counter=lambda text: 100)
    for i, raw in enumerate(s.raws):
        last = direct.observe(raw, remaining_actions=40 - (i + 1))  # supervision rule alone: state unobserved
    out['unknown_at_periodic_due_rule'] = last['outcome']
    if (out['unknown_at_periodic_due_runner'] != 'suppressed_insufficient_remaining_actions'
            or out['unknown_at_periodic_due_rule'] != 'deferred_unobserved_state'):
        problems.append('an unobserved state must not receive a reflection')
    # Reflection transport failure and a non-stop finish: charged, retained, invalid, nothing delivered.
    s = Script()
    for _ in range(14):
        s.step(static, act(5), static)
    sup, events = supervise(s.raws, outputs=['raise', 'length'])
    calls = [e for e in events if e['outcome'] == 'called']
    out['failure_calls'] = [{'error': c['call']['error'] is not None, 'finish': c['call']['finish_reason'],
                             'valid': c['call']['parsed']['valid'], 'delivered': c['delivered'],
                             'charged_tokens': c['call']['input_tokens'] + c['call']['output_tokens']} for c in calls]
    first_two, later = calls[:2], calls[2:]
    if (len(first_two) != 2 or any(c['call']['parsed']['valid'] or c['delivered'] for c in first_two)
            or any(c['call']['input_tokens'] <= 0 for c in first_two)
            or [c['call']['error'] is not None for c in first_two] != [True, False]
            or first_two[1]['call']['finish_reason'] != 'length'
            or any(e.get('suggestion_cleared') for e in events)
            or not later or not later[0]['call']['parsed']['valid'] or sup.suggestion is None
            or sup.suggestion['issued_after_action'] != later[0]['action_index']):
        problems.append('failed and length-finished reflections must be charged, invalid and undelivered; '
                        'only a later valid reflection delivers a suggestion')
    # Insufficient remaining actions: no reflection after action index 29 of 40.
    s = Script()
    for i in range(30):  # distinct pre-frames and >4-cell changes: nothing fires before action 30
        s.step(frame(cells=[(x, i % 12, 1 + i // 12) for x in range(6)]), act(5),
               frame(cells=[(x, (i + 1) % 12, 1 + (i + 1) // 12) for x in range(6)]))
    for _ in range(10):
        s.step(static, act(5), static)  # the first repeat (action 31) fires with 8 actions left
    _, events = supervise(s.raws, arm='triggered', episode_actions=40)
    out['late_firing'] = {k: events[31].get(k) for k in ('outcome', 'remaining_actions')}
    out['calls_after_index_29'] = sum(e['outcome'] == 'called' for e in events if e['action_index'] > 29)
    if (not events[31]['detector_signals'] or events[31]['outcome'] != 'suppressed_insufficient_remaining_actions'
            or out['calls_after_index_29']):
        problems.append('no reflection may be issued when fewer than 10 actions remain')
    # Outcome windows: a terminal state inside the window censors; an unknown outcome is indeterminate.
    s = Script()
    s.step(static, act(5), static)
    s.step(static, act(5), static)
    s.step(static, act(1), frame(cells=[(1, 1, 2)]))
    s.step(frame(cells=[(1, 1, 2)]), act(2), frame(cells=[(2, 1, 2)]), state='GAME_OVER')
    result = O.opportunities(s.records(), spec(), horizon=40)
    out['terminal_in_window'] = [o['status'] for o in result['opportunities']]
    if out['terminal_in_window'] != ['censored_terminal']:
        problems.append('an episode ending inside the window must be censored')
    s = Script()
    s.step(static, act(5), static)
    s.step(static, act(5), static)
    s.step(static, act(1), outcome='outcome_unknown')
    for i in range(10):
        s.step(frame(cells=[(i, 2, 4)]), act(2), frame(cells=[(i + 1, 2, 4)]))
    result = O.opportunities(s.records(), spec(), horizon=40)
    out['unknown_in_window'] = [o['status'] for o in result['opportunities']]
    if out['unknown_in_window'][:1] != ['indeterminate']:
        problems.append('an unknown outcome inside the window must make the opportunity indeterminate')
    out['passed'] = not problems
    out['problems'] = problems
    out['runner_level'] = ('transport failure, storage exhaustion, cancellation, slow transport, monitor exit, '
                           'surviving children and model-startup failure are exercised end to end by the connected '
                           'rehearsal fault matrix (tests/test_stagnation_supervision_v1_connected.py and the runtime '
                           'v2 connected tests); each ends without retry and without an outcome result')
    return out


def display_report(raws, records=None, bottom_rows_from=BOTTOM_ROWS_FROM):
    """Descriptive per-episode display/oscillation facts (post hoc; never an endpoint, label or gate input)."""
    records = records if records is not None else T2.history(raws)
    labels = O.labels(records)
    params, cooldown = spec()['params'], spec()['cooldown_actions']
    firings = [i for i, s in enumerate(D.statistics(records)) if D.signals(s, params)]
    triggers = [d['action_index'] for d in D.triggers(D.statistics(records), params, cooldown) if d['trigger']]
    seen_full, seen_upper, segment = set(), set(), None
    steps = []
    for raw, record, label in zip(raws, records, labels):
        if record['segment'] != segment:
            segment, seen_full, seen_upper = record['segment'], set(), set()
        pre = raw['before']['frames'][-1]
        seen_full.add(json.dumps(pre))
        seen_upper.add(json.dumps(pre[:bottom_rows_from]))
        row = {'step': record['identity']['action_index'], 'label': label}
        if raw['outcome']['status'] == 'acknowledged' and raw['outcome']['after']['frames']:
            post = raw['outcome']['after']['frames'][-1]
            changed = [(x, y) for y, (a, b) in enumerate(zip(pre, post)) for x, (p, q) in enumerate(zip(a, b)) if p != q]
            full, upper = json.dumps(post), json.dumps(post[:bottom_rows_from])
            row.update(changed_cells=len(changed), changed_in_display_rows=sum(y >= bottom_rows_from for _, y in changed),
                       full_frame_new=full not in seen_full, frame_above_display_new=upper not in seen_upper,
                       frame_above_display_revisited=upper in seen_upper)
            seen_full.add(full)
            seen_upper.add(upper)
        steps.append(row)
    observed = [r for r in steps if 'changed_cells' in r]
    display_only = [r for r in observed if r['changed_cells'] and r['changed_cells'] == r['changed_in_display_rows']]
    levels = sum(r['environment']['reported']['levels_completed_after'] - r['environment']['reported']['levels_completed_before']
                 for r in records if r['environment'].get('reported'))
    return {'steps': len(steps), 'observed_steps': len(observed),
            'state_novelty': {'full_frame_new_steps': sum(r['full_frame_new'] for r in observed),
                              'frame_above_display_new_steps': sum(r['frame_above_display_new'] for r in observed)},
            'oscillation': {'frame_above_display_revisit_steps': sum(r['frame_above_display_revisited'] for r in observed)},
            'display_only_change_steps': len(display_only),
            'labels': {k: labels.count(k) for k in ('LC', 'ST', 'IND', 'UNOBSERVED')},
            'detector': {'firing_steps': firings, 'triggers': triggers},
            'completed_levels': levels,
            'display_rows_from': bottom_rows_from,
            'scope': 'descriptive post-hoc report; not an endpoint, label, gate, mask or detector input'}


def display_vs_progress(ls20=True):
    problems, out = [], {}
    size, display_row = 64, 63

    def board(position, counter):
        cells = [(x, display_row, 7) for x in range(counter % 64)]
        cells += [(position + dx, 30 + dy, 4) for dx in range(4) for dy in range(4)]
        return frame(size, cells=cells)

    # 1. Oscillation under a moving display: every full frame is new, the detector cannot see the loop.
    s = Script(available=(1, 2, 3, 4))
    for i in range(40):
        before, after = board(10 + 6 * (i % 2), i), board(10 + 6 * ((i + 1) % 2), i + 1)
        s.step(before, act(3 if i % 2 == 0 else 4), after)
    records = s.records()
    report = display_report(s.raws, records)
    recovery = O.opportunities(records, spec(), horizon=40)
    out['oscillation_with_display'] = {**report, 'opportunities': len(recovery['opportunities'])}
    if (report['state_novelty']['full_frame_new_steps'] != 40 or report['oscillation']['frame_above_display_revisit_steps'] < 38
            or report['detector']['firing_steps'] or report['completed_levels'] != 0):
        problems.append('display-driven novelty during oscillation must stay visible as oscillation, not progress')
    # 2. Counter-only repeat: a tiny-effect loop fires; continuing it is not recovery although every frame is new.
    s = Script()
    for i in range(30):
        s.step(board(10, i), act(6, 5, 5), board(10, i + 1))
    records = s.records()
    recovery = O.opportunities(records, spec(), horizon=40)
    first = recovery['opportunities'][0] if recovery['opportunities'] else {}
    out['counter_only_repeat'] = {'first_opportunity': {k: first.get(k) for k in ('opened_at', 'signals', 'status',
                                                                                  'new_frames_in_window',
                                                                                  'level_completed_in_window')},
                                  'labels': display_report(s.raws, records)['labels']}
    if first.get('status') != 'not_recovered' or first.get('new_frames_in_window') != 10 or first.get('level_completed_in_window'):
        problems.append('a moving counter must not turn a continued loop into recovery or solving credit')
    # 3. Genuine escape: exit from the cited pattern into new playfield states, then a reported level completion.
    s = Script()
    for i in range(10):
        s.step(board(10, i), act(6, 5, 5), board(10, i + 1))
    for j in range(8):
        s.step(board(10 + 4 * j, 10 + j), act(4), board(14 + 4 * j, 11 + j), level_up=(j == 7))
    records = s.records()
    recovery = O.opportunities(records, spec(), horizon=40)
    first = recovery['opportunities'][0]
    report = display_report(s.raws, records)
    out['genuine_escape'] = {'status': first['status'], 'actions_to_exit': first['actions_to_exit'],
                             'level_completed_in_window': first['level_completed_in_window'],
                             'completed_levels': report['completed_levels']}
    if first['status'] != 'recovered' or not first['level_completed_in_window'] or report['completed_levels'] != 1:
        problems.append('a genuine exit followed by a reported level must count as recovery and one completed level')
    # 4. Solving credit comes only from environment-reported level increases, never from frame novelty.
    out['solving_source'] = 'levels_completed deltas reported by the environment (closed_loop.evaluate.evaluate_episode)'
    if ls20:
        out['ls20_engine'] = ls20_descriptive()
        osc = out['ls20_engine']['policies']['alternate_1_2']
        if osc['detector']['firing_steps'] or osc['completed_levels']:
            problems.append('ls20 oscillation unexpectedly fired the detector or completed a level')
    out['passed'] = not problems
    out['problems'] = problems
    return out


def ls20_descriptive(steps=40):
    """ls20 under three fixed scripted policies on the offline engine (CPU, no model, game seed 0, no reset)."""
    import tempfile
    from research.grounded_action_v1.engine import restore_game_mount
    from research.stagnation_supervision_v1.tier_b_probe import observation
    policies = {'alternate_1_2': lambda i: 1 + i % 2, 'rotate_1_2_3_4': lambda i: 1 + i % 4, 'repeat_1': lambda i: 1}
    out = {'game_id': 'ls20-9607627b', 'steps': steps, 'post_hoc': True, 'policies': {},
           'display_rows_from': BOTTOM_ROWS_FROM,
           'note': ('Descriptive only (like the post-hoc Tier B inspection): three fixed policies, no model, '
                    'no selection, no endpoint. It shows what the frozen full-frame detector and LC labels see on ls20.')}
    with tempfile.TemporaryDirectory(prefix='ssv-rt2-ls20-') as folder:
        games = restore_game_mount(Path(folder) / 'games')
        for name, policy in policies.items():
            raws = play('ls20-9607627b', games, Path(folder) / 'rec' / name, policy, steps)
            report = display_report(raws)
            report['actions'] = [r['dispatched']['action_id'] for r in raws]
            report['terminal'] = raws[-1]['outcome'].get('after', {}).get('state') if raws else None
            out['policies'][name] = report
    return out


def play(game_id, games, recordings, policy, steps):
    from arc_agi import Arcade, OperationMode
    from arcengine import GameState
    from agent.action import ActionDecision
    from agent.framework_adapter import LocalFrameworkAdapter
    from research.stagnation_supervision_v1.tier_b_probe import observation
    adapter = LocalFrameworkAdapter(Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=str(games),
                                           recordings_dir=str(recordings)), seed_by_game={game_id: 0})
    adapter.open_scorecard(tags=['stagnation-supervision-runtime-v2-verification'])
    raws, client = [], None
    try:
        client = adapter.bootstrap(game_id)
        obs = client.observation
        for i in range(steps):
            if obs.state in (GameState.WIN, GameState.GAME_OVER):
                break
            action = {'action_id': policy(i), 'action_data': {}}
            raw = {'identity': {'episode_id': 'verification-' + game_id, 'action_index': i}, 'before': observation(obs),
                   'proposal': None, 'dispatched': action, 'environment_source': 'offline_development_engine_scripted'}
            post = adapter.dispatch(client, ActionDecision(**action, source='runtime_v2_verification',
                                                           decision_id=f'verification-{game_id}-{i}'))
            raw['outcome'] = {'status': 'acknowledged', 'after': observation(post)}
            raws.append(raw)
            obs = post
    finally:
        if client is not None:
            adapter.finalize_client(client)
        adapter.close_scorecard()
    return raws


def run(ls20=True):
    sections = {'causality': causality(), 'thresholds': thresholds(), 'continuation': continuation(),
                'terminal_and_failures': terminal_and_failures(), 'display_vs_progress': display_vs_progress(ls20)}
    frozen = {name: hashlib.sha256((ROOT / 'research/stagnation_supervision_v1' / name).read_bytes()).hexdigest()
              for name in ('trigger_spec.json', 'detector.py', 'supervision.py', 'intervention.py', 'outcomes.py',
                           'thresholds.py', 'fixtures.py')}
    return {'version': VERSION, 'frozen_files_sha256': frozen, 'gpu_runs': 0, 'model_calls': 0,
            'passed': all(s['passed'] for s in sections.values()), **sections}
