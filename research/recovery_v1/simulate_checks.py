"""When would each recovery-check trigger have fired on saved play? No model calls.

The saved traces are passed through the tracker the live controller uses (research/claude_arc_v1/recovery.py),
so the simulated checks are the checks a run would make, up to the first one: a real check may change
what the agent does next, and nothing after it is predicted here.

For every trigger and source this reports how many checks fire, in how many games, and, for the first
check in each attempt, how that attempt actually ended and how many of its actions came after the check
(the most a reset at that moment could have saved).

Usage: simulate_checks.py <out_dir>   writes checks.json
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claude_arc_v1 import recovery  # noqa: E402
from recovery_v1 import measures as M, traces  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BASELINES = ROOT / 'reports/arc_agi3_loss_audit/data/headroom.json'


def trigger(name, **kw):
    base = dict(stall_window=0, stall_same_notes=False, stall_level_ratio=0, stall_level_floor=0, level_baselines={})
    return name, SimpleNamespace(**{**base, **kw})


def triggers(baselines):
    out = [trigger('no new board for %d' % n, stall_window=n) for n in (2, 3, 4, 6, 8, 10)]
    out += [trigger('no new board for %d, same notes' % n, stall_window=n, stall_same_notes=True) for n in (2, 3, 4, 6)]
    out += [trigger('level actions at %.2fx human' % r, stall_level_ratio=r, level_baselines=baselines)
            for r in (0.75, 1.0, 1.5, 2.0)]
    out += [trigger('level actions at 1.00x human, not before 30', stall_level_ratio=1.0, stall_level_floor=30,
                    level_baselines=baselines)]
    return out


def observation(frame, level, state):
    return SimpleNamespace(latest_frame=frame, levels_completed=level, state=SimpleNamespace(name=state),
                           canonical_hash='')


def simulate(trace, config, hindsight=False):
    """[(step index, reasons)] for the checks this trigger would make, each before the action at that index.

    With hindsight the tracker is given, from the first action, the counter cells estimated from the whole
    trace. No live run can know them; the difference shows how much the board signal depends on the estimate.
    """
    tracker = recovery.Tracker(trace['initial'])
    if hindsight:
        last, level = trace['initial'], 0
        for step in trace['steps']:
            if step['a'] == 'RESET' or step['lc'] != level:
                tracker.counter.restart()
            elif step['state'] == 'NOT_FINISHED':
                tracker.counter.update(last, step['frame'])
            last, level = step['frame'], step['lc']
        tracker.counter.restart()
        tracker.keys = {tracker.counter.key(trace['initial'])}
    before = observation(trace['initial'], 0, 'NOT_FINISHED')
    fired = []
    for i, step in enumerate(trace['steps']):
        if step['a'] != 'RESET' and before.state.name != 'GAME_OVER':
            baseline = recovery.baseline_for(config, trace['game'], tracker.level)
            reasons = tracker.due(config, baseline)
            if reasons:
                fired.append((i, reasons, tracker.level))
                tracker.checked(reasons, None, baseline)
        after = observation(step['frame'], step['lc'], step['state'])
        action_id = 0 if step['a'] == 'RESET' else int(step['a'][-1])
        decision = SimpleNamespace(action_id=action_id, action_data={})
        notes = None if step['notes'] is None else [{'id': i_, 'status': s_} for i_, _, s_ in step['notes']]
        tracker.record('t%d' % (i + 1), decision, before, after, by_model=step['by'] == 'model', notes=notes)
        before = after
    return fired


def summarise(all_traces, config):
    by = defaultdict(Counter)
    for (label, game), trace in all_traces.items():
        c = by[label]
        fired = simulate(trace, config)
        attempts = M.attempts(trace)
        c['checks'] += len(fired)
        c['games_with_a_check'] += bool(fired)
        if config.stall_window:
            late = simulate(trace, config, hindsight=True)
            c['checks_with_hindsight_counter'] += len(late)
            c['games_with_hindsight_counter'] += bool(late)
        first = {}
        levels = {level for _, _, level in fired}
        done = trace['steps'][-1]['lc'] + (trace['steps'][-1]['state'] == 'WIN')
        c['levels_checked'] += len(levels)
        c['levels_checked_and_completed'] += sum(level < done for level in levels)
        for index, _, _ in fired:
            for n, a in enumerate(attempts):
                if a['first'] <= index <= a['last'] + 1 and n not in first:
                    first[n] = index
        for n, a in enumerate(attempts):
            kind = 'failed' if a['outcome'] in ('game_over', 'abandoned') else a['outcome']
            c['attempts_' + kind] += 1
            c['actions_' + kind] += a['n']
            if n in first:
                c['checked_' + kind] += 1
                c['actions_after_first_check_' + kind] += a['last'] + 1 - first[n]
    return {label: dict(c) for label, c in by.items()}


def main(out_dir):
    out_dir = Path(out_dir)
    data = json.loads(BASELINES.read_text())
    baselines = {g.split('-')[0]: v['baseline'] for g, v in data['meta'].items()}
    everything = {('nov6-ours', g): t for g, t in traces.load_events().items()}
    everything.update(traces.load_recordings())
    result = {name: summarise(everything, config) for name, config in triggers(baselines)}
    (out_dir / 'checks.json').write_text(json.dumps(result, indent=1) + '\n')
    return result


if __name__ == '__main__':
    table = main(sys.argv[1])
    kinds = ('completed', 'failed', 'open', 'game_over_final')
    for name, by in table.items():
        print('==', name)
        for label, c in by.items():
            parts = ['%s %d/%d (%d after)' % (k, c.get('checked_' + k, 0), c.get('attempts_' + k, 0),
                                              c.get('actions_after_first_check_' + k, 0)) for k in kinds
                     if c.get('attempts_' + k)]
            print('  %-26s checks %4d in %2d games | %s' % (label, c['checks'], c['games_with_a_check'], '; '.join(parts)))
