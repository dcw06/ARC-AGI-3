"""Outcome evaluation (Track 3, stagnation_supervision_v1): detector-defined opportunities, behavioural recovery,
reference labels, false interruptions and realised cost. Records only; no model; the frozen detector is unchanged.

**Opportunities are defined identically in every arm**, including continuation, by the frozen detector running as
an observer (thresholds and cooldown from trigger_spec.json). An opportunity opens at step t, the first detector
firing (signals present, cooldown ignored) such that the next WINDOW actions fall inside the episode horizon. The
next opportunity can open only after that window closes, so windows never overlap. A firing with fewer than WINDOW
actions left in the horizon is counted as `censored_horizon`, not as an opportunity.

**The repetition pattern** of an opportunity is what the firing cited:
- `state_action_recurrence`: the exact (pre-frame fingerprint, action) pairs in its evidence;
- `tiny_effect_repeat`: the identical action whose effects changed at most TINY_CELLS cells.
A later step is an *instance* of the pattern if it repeats a cited pair or repeats the tiny-effect action with an
effect of at most TINY_CELLS cells.

**Behavioural recovery** (not progress) at an opportunity opened at t, assessed over the fixed window
t+1 .. t+WINDOW:
- exit: the first acknowledged, observed step e in the window that is not an instance of the pattern;
- the exit must come early enough to leave a full quiet period: e <= t + WINDOW - QUIET;
- quiet: in steps e+1 .. e+QUIET there is no detector firing and no instance of the pattern;
- `recovered` if both hold; `not_recovered` if every step needed was observed and they do not;
- `indeterminate` if an unknown outcome or missing observation makes the exit or the quiet period undecidable (a
  failed dispatch delivered nothing and is skipped);
- `censored_terminal` if the episode ends (WIN, GAME_OVER) or a reset starts a new segment inside the window before
  recovery is decided. A level completion inside the window is recorded separately (`level_completed_in_window`):
  it is the solving endpoint, not this behavioural one.
New frames and new (state, action) pairs inside the window are reported separately and are never the endpoint: a
moving counter alone can make every frame new.

**Reference labels** (protocol §7, rule-based; never from detector output, arm or outcome), per observed decision
point:
- LC (legitimate-continuation opportunity): at least one of the last 3 acknowledged steps of the segment changed more
  than TINY_CELLS cells into a final frame new to the segment;
- ST (stagnation point): not LC, and each of the last 3 acknowledged steps changed at most TINY_CELLS cells;
- IND: neither (including the first two steps of a segment).
Mechanical novelty labels on a few correlated episodes do not establish that an interruption is genuinely harmful.

Cost is reported as realised (calls, tokens, latency per arm). Equal caps make the reflection arms equal-budget,
not automatically equal-cost.
"""
import hashlib
import json
import math
import random

from research.stagnation_supervision_v1 import detector as D
from research.transition_evidence_v2 import vocabulary as V

VERSION = 'stagnation_supervision_v1_outcomes'
WINDOW = 10
QUIET = 5
RECENT = 3
TINY_CELLS = D.TINY_CELLS
CAP = 0.10
MIN_LC_POINTS = 60
MIN_LC_GAMES = 2
MIN_LC_EPISODES = 4
BOOTSTRAP_RESAMPLES = 10000
BOOTSTRAP_SEED = 'stagnation-supervision-v1-protocol-v2'


def _facts(record):
    m = record['measurements']
    final = m['frames'][-1] if m['frames'] and m['frames'][-1]['valid'] else None
    changed = final['vs_pre']['changed_cells'] if final else None
    observed = (record['dispatch']['status'] == V.ACKNOWLEDGED
                and record['observations']['availability']['status'] != V.MISSING and final is not None)
    return {'index': record['identity']['action_index'], 'segment': record['segment'],
            'dispatch': record['dispatch']['status'], 'observed': observed,
            'fp': record['observations']['before_frames_sha256'][-1],
            'action': D.action_key(record['action']['dispatched']),
            'after': final['sha256'] if final else None,
            'cells': changed['value'] if changed and changed['status'] == 'measured' else None,
            'events': record['environment']['events'], 'progress': record['progress']['status']}


def observer(records, spec, predictions=None):
    """Per-step detector signals (cooldown ignored: an opportunity is any firing)."""
    stats = D.statistics(records, predictions)
    return [D.signals(s, spec['params']) for s in stats]


def _pattern(signals, facts):
    pairs, tiny = set(), set()
    for s in signals:
        if s['signal'] == 'state_action_recurrence':
            pairs |= {(facts[i]['fp'], facts[i]['action']) for i in s['evidence']}
        elif s['signal'] == 'tiny_effect_repeat':
            tiny |= {facts[i]['action'] for i in s['evidence']}
        else:  # other signals are disabled in the frozen spec; their evidence pairs stand in for the pattern
            pairs |= {(facts[i]['fp'], facts[i]['action']) for i in s['evidence']}
    return pairs, tiny


def _instance(f, pattern):
    pairs, tiny = pattern
    return (f['fp'], f['action']) in pairs or (f['action'] in tiny and f['cells'] is not None
                                                and f['cells'] <= TINY_CELLS)


def _window_novelty(facts, t, end):
    seen_frames, seen_pairs = set(), set()
    for f in facts[:t + 1]:
        if f['segment'] == facts[t]['segment']:
            seen_frames |= {f['fp']} | ({f['after']} if f['after'] else set())
            seen_pairs.add((f['fp'], f['action']))
    new_frames = new_pairs = 0
    for f in facts[t + 1:end + 1]:
        if f['observed'] and f['after'] not in seen_frames:
            new_frames += 1
        if f['observed'] and (f['fp'], f['action']) not in seen_pairs:
            new_pairs += 1
        seen_frames |= {f['fp']} | ({f['after']} if f['after'] else set())
        seen_pairs.add((f['fp'], f['action']))
    return new_frames, new_pairs


def assess(facts, firing, t, horizon):
    """One opportunity opened at t (see module docstring)."""
    pattern = _pattern(firing[t], facts)
    end = t + WINDOW
    window = [f for f in facts if t < f['index'] <= end]
    out = {'opened_at': t, 'signals': sorted({s['signal'] for s in firing[t]}),
           'pattern': {'pairs': sorted([list(p) for p in pattern[0]]), 'tiny_actions': sorted(pattern[1])},
           'window': [t + 1, end], 'level_completed_in_window': any(V.LEVEL_COMPLETED in f['events'] for f in window)}
    out['new_frames_in_window'], out['new_state_action_pairs_in_window'] = _window_novelty(facts, t, min(end, len(facts) - 1))
    boundary = next((f['index'] for f in window if f['segment'] != facts[t]['segment']), None)
    ended = len(facts) - 1 < end
    exit_step, status = None, None
    for f in window:
        if boundary is not None and f['index'] >= boundary:
            break
        if f['dispatch'] == V.FAILED:
            continue  # nothing was delivered: neither an exit nor an instance
        if not f['observed']:
            status = 'indeterminate'  # an unknown or unobserved step: whether the pattern continued is unknown
            break
        if not _instance(f, pattern):
            exit_step = f['index']
            break
    if status is None and exit_step is None:
        if boundary is not None or ended:
            status = 'censored_terminal'
        else:
            status = 'not_recovered'
    if exit_step is not None:
        if exit_step > end - QUIET:
            status = 'not_recovered'
        else:
            quiet = [f for f in facts if exit_step < f['index'] <= exit_step + QUIET]
            if boundary is not None and boundary <= exit_step + QUIET or len(quiet) < QUIET:
                status = 'censored_terminal'
            elif any(firing[f['index']] or _instance(f, pattern) for f in quiet if f['observed']):
                status = 'not_recovered'
            elif any(not f['observed'] and f['dispatch'] != V.FAILED for f in quiet):
                status = 'indeterminate'
            else:
                status = 'recovered'
    out.update(exit_at=exit_step, actions_to_exit=None if exit_step is None else exit_step - t, status=status)
    return out


def opportunities(records, spec, horizon, predictions=None):
    """All opportunities of one episode (records: transition history in order; horizon: actions per episode)."""
    facts = [_facts(r) for r in records]
    firing = observer(records, spec, predictions)
    out, censored, t = [], [], 0
    while t < len(facts):
        if firing[t]:
            if t + WINDOW > horizon - 1:
                censored.append(t)
                t += 1
                continue
            out.append(assess(facts, firing, t, horizon))
            t += WINDOW + 1
            continue
        t += 1
    return {'opportunities': out, 'censored_horizon_firings': censored,
            'firing_steps': [i for i, f in enumerate(firing) if f]}


def labels(records):
    """LC / ST / IND per decision point (after each record), by the frozen rule."""
    facts = [_facts(r) for r in records]
    out = []
    for i, f in enumerate(facts):
        segment = [g for g in facts[:i + 1] if g['segment'] == f['segment']]
        seen, novel = set(), []
        for g in segment:
            seen.add(g['fp'])
            novel.append(g['observed'] and g['after'] not in seen)
            if g['after']:
                seen.add(g['after'])
        acked = [(g, n) for g, n in zip(segment, novel) if g['observed']]
        recent = acked[-RECENT:]
        if not f['observed']:
            label = 'UNOBSERVED'
        elif any(n and g['cells'] is not None and g['cells'] > TINY_CELLS for g, n in recent):
            label = 'LC'
        elif len(recent) == RECENT and all(g['cells'] is not None and g['cells'] <= TINY_CELLS for g, _ in recent):
            label = 'ST'
        else:
            label = 'IND'
        out.append(label)
    return out


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return None
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [max(0.0, centre - half), min(1.0, centre + half)]


def cluster_bootstrap(per_episode, resamples=BOOTSTRAP_RESAMPLES, seed=BOOTSTRAP_SEED):
    """95% percentile interval of sum(k)/sum(n), resampling episodes. per_episode: [(k, n)]."""
    usable = [(k, n) for k, n in per_episode if n]
    if not usable:
        return None
    rng = random.Random(hashlib.sha256(seed.encode()).hexdigest())
    rates = []
    for _ in range(resamples):
        draw = [usable[rng.randrange(len(usable))] for _ in usable]
        rates.append(sum(k for k, _ in draw) / sum(n for _, n in draw))
    rates.sort()
    return [rates[int(0.025 * resamples)], rates[int(0.975 * resamples) - 1]]


def _interruptions_all(episodes, arm, *, what='detector_triggers'):
    """False-interruption rate in one arm: interruptions at LC points over LC points.
    episodes: [{'arm', 'game', 'records', 'triggers': [step...], 'calls': [step...]}]. `what` selects detector
    triggers (cooldown applied, as evaluated) or reflection calls actually made."""
    per, games = [], set()
    for e in episodes:
        if e['arm'] != arm:
            continue
        lab = labels(e['records'])
        lc = [i for i, l in enumerate(lab) if l == 'LC']
        hits = set(e['triggers'] if what == 'detector_triggers' else e['calls'])
        per.append((sum(1 for i in lc if i in hits), len(lc)))
        if lc:
            games.add(e['game'])
    k, n = sum(p[0] for p in per), sum(p[1] for p in per)
    episodes_with_lc = sum(1 for p in per if p[1])
    interval_w, interval_b = wilson(k, n), cluster_bootstrap(per)
    upper = max(interval_w[1], interval_b[1]) if interval_w and interval_b else None
    enough = n >= MIN_LC_POINTS and len(games) >= MIN_LC_GAMES and episodes_with_lc >= MIN_LC_EPISODES
    if not enough:
        status = 'not_certifiable_minimum_not_met'
    elif upper <= CAP:
        status = 'within_provisional_cap'
    else:
        status = 'exceeds_provisional_cap'
    return {'arm': arm, 'counted': what, 'interruptions_at_lc': k, 'lc_points': n, 'rate': k / n if n else None,
            'wilson_95': interval_w, 'episode_cluster_bootstrap_95': interval_b, 'upper_bound_used': upper,
            'lc_games': len(games), 'episodes_with_lc': episodes_with_lc, 'status': status,
            'limitation': 'mechanical novelty labels and a few correlated episodes do not establish that an '
                          'interruption is genuinely harmful; a provisional benchmark gate, not certification'}


GATE_ELIGIBLE_CONTROLS = frozenset({'wa30'})
EXPLORATORY_ONLY = frozenset({'ls20'})


def interruptions(episodes, arm, *, what='detector_triggers'):
    """R2: descriptive labels never qualify exploratory cases as continuation controls.

Only the reviewed wa30 control is currently eligible. A second validated control
requires a separately reviewed reference decision; this study cannot meet that
minimum merely by producing mechanically novel frames in ls20.
"""
    eligible, excluded = [], set()
    for episode in episodes:
        game = episode['game'].split('-', 1)[0]
        if game in GATE_ELIGIBLE_CONTROLS and game not in EXPLORATORY_ONLY:
            eligible.append({**episode, 'game': game})
        elif episode['arm'] == arm:
            excluded.add(game)
    result = _interruptions_all(eligible, arm, what=what)
    descriptive = _interruptions_all(episodes, arm, what=what)
    descriptive['status'] = 'descriptive_only'
    return {**result, 'gate_policy': 'reviewed_continuation_controls_r2',
            'eligible_controls': sorted(GATE_ELIGIBLE_CONTROLS - EXPLORATORY_ONLY),
            'excluded_exploratory_or_unvalidated_games': sorted(excluded),
            'descriptive_all_cases': descriptive}


def realised_cost(episodes):
    """Per arm: reflection calls, outcomes, charged tokens and latency, from each episode's retained reflection rows.
    episodes: [{'arm', 'reflections': [{'status', 'input_tokens', 'output_tokens', 'latency_s', 'valid'}...]}]."""
    out = {}
    for e in episodes:
        a = out.setdefault(e['arm'], {'episodes': 0, 'calls': 0, 'valid': 0, 'invalid': 0, 'failed': 0,
                                      'input_tokens': 0, 'output_tokens': 0, 'latency_s': 0.0, 'calls_per_episode': []})
        a['episodes'] += 1
        rows = e.get('reflections') or []
        a['calls_per_episode'].append(len(rows))
        for r in rows:
            a['calls'] += 1
            a['valid'] += r.get('valid') is True
            a['failed'] += r.get('status') == 'failed'
            a['invalid'] += r.get('status') != 'failed' and r.get('valid') is not True
            a['input_tokens'] += r.get('input_tokens') or 0
            a['output_tokens'] += r.get('output_tokens') or 0
            a['latency_s'] += r.get('latency_s') or 0.0
    for a in out.values():
        a['tokens'] = a['input_tokens'] + a['output_tokens']
    note = 'periodic and triggered share caps (equal budget); realised calls, tokens and latency may differ'
    p, t = out.get('periodic'), out.get('triggered')
    ratio = (t['tokens'] / p['tokens']) if p and t and p['tokens'] else None
    return {'by_arm': out, 'triggered_to_periodic_token_ratio': ratio, 'note': note}


def recovery_summary(episodes, spec, horizon):
    """Per arm: opportunities, recovery statuses, actions to exit, novelty counts, level completions."""
    out = {}
    for e in episodes:
        result = opportunities(e['records'], spec, horizon)
        a = out.setdefault(e['arm'], {'episodes': 0, 'opportunities': 0, 'status': {}, 'actions_to_exit': [],
                                      'new_frames_in_window': 0, 'new_state_action_pairs_in_window': 0,
                                      'censored_horizon_firings': 0, 'level_completed_in_window': 0,
                                      'per_episode': []})
        a['episodes'] += 1
        a['censored_horizon_firings'] += len(result['censored_horizon_firings'])
        recovered = 0
        for o in result['opportunities']:
            a['opportunities'] += 1
            a['status'][o['status']] = a['status'].get(o['status'], 0) + 1
            recovered += o['status'] == 'recovered'
            if o['actions_to_exit'] is not None:
                a['actions_to_exit'].append(o['actions_to_exit'])
            a['new_frames_in_window'] += o['new_frames_in_window']
            a['new_state_action_pairs_in_window'] += o['new_state_action_pairs_in_window']
            a['level_completed_in_window'] += o['level_completed_in_window']
        a['per_episode'].append({'episode': e.get('episode'), 'opportunities': len(result['opportunities']),
                                 'recovered': recovered})
    for a in out.values():
        decided = sum(a['status'].get(s, 0) for s in ('recovered', 'not_recovered'))
        a['recovery_rate_decided'] = a['status'].get('recovered', 0) / decided if decided else None
    return out


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
