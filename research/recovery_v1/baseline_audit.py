"""Recovery measures on saved play: our November 6 run and the 100 public recordings. No model calls.

Usage: baseline_audit.py <out_dir>
Writes baseline.json (every table below) into out_dir.

  nov6            where the 100 actions of each game went, and the unfinished level against its human baseline
  notes           how often the agent's notes were unchanged from one action to the next
  recovery        per source: attempts and actions by outcome, resets by kind, dead-end and return measures
  reset_by_game   what RESET returned, by game, over every source
  undo_by_game    which games offer ACTION7 and whether it brought the earlier board back
  replay          whether the same actions from the same level-start board gave the same boards again
"""
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claude_arc_v1 import recovery  # noqa: E402
from recovery_v1 import measures as M, traces  # noqa: E402
from recovery_v1.simulate_checks import observation  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BASELINES = ROOT / 'reports/arc_agi3_loss_audit/data/headroom.json'


def short(game):
    return game.split('-')[0]


def live_stale_runs(trace):
    """{level: longest run without a new board} as the live tracker would have counted it during play."""
    tracker = recovery.Tracker(trace['initial'])
    before, longest = observation(trace['initial'], 0, 'NOT_FINISHED'), Counter()
    for i, step in enumerate(trace['steps']):
        after = observation(step['frame'], step['lc'], step['state'])
        decision = SimpleNamespace(action_id=0 if step['a'] == 'RESET' else int(step['a'][-1]), action_data={})
        level = tracker.level
        facts = tracker.record('t%d' % (i + 1), decision, before, after, by_model=step['by'] == 'model')
        longest[level] = max(longest[level], facts['stale'])
        before = after
    return longest


def nov6_table(ours, human, best):
    rows, totals = [], Counter()
    for game, trace in ours.items():
        attempts = M.annotate(trace, M.counter_mask(trace))
        spent = Counter()
        for a in attempts:
            spent[a['level']] += a['n'] + (a['reset'] is not None)
            kind = 'failed' if a['outcome'] in ('game_over', 'abandoned') else a['outcome']
            totals[kind] += a['n']
            totals['resets'] += a['reset'] is not None
        final = trace['steps'][-1]
        row = {'game': short(game), 'actions': len(trace['steps']), 'levels_completed': final['lc'],
               'game_overs': sum(s['state'] == 'GAME_OVER' for s in trace['steps']),
               'resets': sum(s['a'] == 'RESET' for s in trace['steps'])}
        if final['state'] != 'WIN':
            # The level the game stopped on, whether or not any action was taken on it after the last
            # completion or reset.
            level = final['lc']
            on_level = [a for a in attempts if a['level'] == level]
            row.update(unfinished_level=level + 1, spent_on_it=spent[level], human=human[game][level],
                       best_known=best[game][level], ratio_to_human=round(spent[level] / human[game][level], 2),
                       longest_stale_run_hindsight=max((a['longest_stale_run'] for a in on_level), default=0),
                       longest_stale_run_live=live_stale_runs(trace)[level])
        rows.append(row)
    unfinished = [r for r in rows if 'unfinished_level' in r]
    bands = Counter()
    for r in unfinished:
        band = 'under_human' if r['ratio_to_human'] < 1 else 'one_to_two' if r['ratio_to_human'] < 2 else 'over_two'
        bands[band + '_games'] += 1
        bands[band + '_actions'] += r['spent_on_it']
    return {'rows': rows, 'actions_by_outcome': dict(totals), 'unfinished_bands': dict(bands)}


def notes_table(ours):
    """Three readings of 'memory did not change' between consecutive model actions."""
    out = Counter()
    for trace in ours.values():
        previous = None
        for step in trace['steps']:
            if step['by'] != 'model' or step['notes'] is None:
                continue
            if previous is not None:
                out['pairs'] += 1
                out['identical'] += step['notes'] == previous
                out['same_ids_and_status'] += ({(i, s) for i, _, s in step['notes']}
                                               == {(i, s) for i, _, s in previous})
                settled = lambda notes: {(i, s) for i, _, s in notes if s != 'tentative'}
                out['same_settled_claims'] += settled(step['notes']) == settled(previous)
            previous = step['notes']
    return dict(out)


def recovery_table(all_traces):
    by = defaultdict(Counter)
    lists = defaultdict(lambda: defaultdict(list))
    for (label, game), trace in all_traces.items():
        c, keep = by[label], lists[label]
        attempts = M.annotate(trace, M.counter_mask(trace))
        c['games'] += 1
        c['actions'] += len(trace['steps'])
        c['wins'] += trace['steps'][-1]['state'] == 'WIN'
        c['levels_completed'] += trace['steps'][-1]['lc']
        for a in attempts:
            c['attempts_' + a['outcome']] += 1
            c['actions_' + a['outcome']] += a['n']
            c['actions_sent_while_game_over'] += a['after_game_over']
            if a['outcome'] in ('game_over', 'abandoned'):
                c['resets'] += 1
                c['dead_end_loss'] += a['dead_end_loss']
                keep['len_' + a['outcome']].append(a['n'])
                keep['stale_tail_' + a['outcome']].append(a['stale_tail'])
                c['empty_' + a['outcome']] += a['n'] == 0
            if a.get('follows_failed'):
                c['retries'] += 1
                c['retries_' + a['outcome']] += 1
                keep['common_prefix'].append(a['common_prefix'])
                keep['known_ground'].append(a['known_ground'])
                keep['regained_at'].append(a['regained_at'])
                keep['regain_cost'].append(a['regain_cost'])
                c['retry_start_matches'] += a['start_matches']
                c['known_ground_actions'] += a['known_ground']
                c['regain_cost_actions'] += a['regain_cost']
    out = {}
    for label, c in by.items():
        row = dict(c)
        for name, values in lists[label].items():
            row[name] = {'n': len(values), 'median': statistics.median(values), 'mean': round(statistics.mean(values), 1),
                         'max': max(values), 'zero': sum(v == 0 for v in values)}
        out[label] = row
    return out


def reset_table(all_traces):
    by = defaultdict(Counter)
    for (label, game), trace in all_traces.items():
        c = by[short(game)]
        for r in M.reset_facts(trace, M.counter_mask(trace)):
            c['resets'] += 1
            c['after_game_over'] += r['from_state'] == 'GAME_OVER'
            c['level_kept'] += r['level_after'] == r['level_before']
            c['full_reset_flag'] += r['full_reset_flag']
            c['board_equals_level_start'] += r['equals_level_start'] is True
            c['level_start_unknown'] += r['equals_level_start'] is None
            c['sent_right_after_a_reset'] += r['previous_was_reset']
            c['board_already_at_level_start'] += r['board_unchanged_by_reset']
    games = sorted({short(g) for _, g in all_traces})
    return {g: dict(by[g]) for g in games}


def undo_table(all_traces):
    offered, by = defaultdict(set), defaultdict(Counter)
    for (label, game), trace in all_traces.items():
        offered[short(game)] |= set(trace['initial_avail'])
        for step in trace['steps']:
            offered[short(game)] |= set(step['avail'])
        c = by[short(game)]
        for r in M.undo_facts(trace, M.counter_mask(trace)):
            c['uses'] += 1
            if not r['had_target']:
                c['nothing_to_undo'] += 1
            elif not r['undone_action_changed_board']:
                c['undone_action_had_no_effect'] += 1
            else:
                c['testable'] += 1
                c['restored_exact'] += r['restored_exact']
                c['restored_ignoring_counter'] += bool(r['restored_ignoring_counter'])
                c['restored_within_2_cells'] += r['cells_differing_from_target'] <= 2
    return {g: {'actions_offered': sorted(offered[g]), 'action7_offered': 7 in offered[g], **dict(by[g])}
            for g in sorted(offered)}


def replay_table(all_traces):
    """Same level-start board and the same actions so far: is the returned board the same?

    Every attempt is filed under (game, level, exact starting board). Within a file, two attempts that
    share an action prefix are compared board by board along it. Counted once per shared prefix position.
    """
    files = defaultdict(list)
    for (label, game), trace in all_traces.items():
        boards = [trace['initial']] + [s['frame'] for s in trace['steps']]
        for a in M.attempts(trace):
            start = boards[a['first']]
            path = [((s['a'], s['x'], s['y']), s['frame'], s['state'], s['lc'])
                    for s in trace['steps'][a['first']:a['last'] + 1]]
            files[(short(game), a['level'], start.tobytes())].append((label, path))
    by = defaultdict(Counter)
    for (game, level, _), members in files.items():
        seen = {}          # action prefix -> [board bytes, state, lc, sources that reached it, visits]
        for label, path in members:
            prefix = ()
            for action, frame, state, lc in path:
                prefix += (action,)
                first = seen.get(prefix)
                if first is None:
                    seen[prefix] = [frame.tobytes(), state, lc, {label}, 1]
                    continue
                first[3].add(label)
                first[4] += 1
                c = by[game]
                c['compared'] += 1
                same = first[0] == frame.tobytes() and first[1] == state and first[2] == lc
                c['same'] += same
                if not same:
                    c['different'] += 1
                    c['different_first_at_depth_%d' % len(prefix)] += 1
                    break   # later boards along a diverged path are not independent evidence
        c = by[game]
        # Positions (same start, same actions so far) reached more than once, and by more than one source.
        # These two do not depend on the order in which the traces are read.
        c['positions_reached_again'] += sum(1 for v in seen.values() if v[4] > 1)
        c['positions_reached_by_two_sources'] += sum(1 for v in seen.values() if len(v[3]) > 1)
    return {g: dict(c) for g, c in sorted(by.items()) if c['compared']}


def extras(all_traces, human):
    """Breakdowns asked for in review: by kind of failure, by level, per retry, and without the two loop games."""
    out = {}
    for skip, tag in (((), 'all_games'), (('su15', 'sk48'), 'without_su15_sk48')):
        by = defaultdict(Counter)
        for (label, game), trace in all_traces.items():
            if short(game) in skip:
                continue
            c = by[label]
            rows = M.annotate(trace, M.counter_mask(trace))
            c['actions'] += len(trace['steps'])
            failed_levels, done = set(), trace['steps'][-1]['lc'] + (trace['steps'][-1]['state'] == 'WIN')
            for a in rows:
                if a['outcome'] == 'game_over':
                    c['actions_in_game_over_attempts_with_reset'] += a['n'] + 1
                    c['stale_tail_attempt_sum'] += a['stale_tail']
                    c['stale_tail_level_sum'] += a['stale_tail_level']
                    failed_levels.add(a['level'])
                elif a['outcome'] == 'abandoned':
                    c['actions_in_chosen_reset_attempts_with_reset'] += a['n'] + 1
                    c['chosen_resets'] += 1
                    c['chosen_after_one_action'] += a['n'] == 1
                    c['chosen_after_one_action_that_was_action7'] += (a['n'] == 1 and a['_actions'][0][0] == 'ACTION7')
                    failed_levels.add(a['level'])
                if a.get('follows_failed') and a['n']:
                    c['retries'] += 1
                    c['retry_actions'] += a['n']
                    c['actions_to_get_back'] += a['regain_cost']
                    c['first_time_actions_to_that_point'] += a['regained_at']
                    c['retries_that_got_back_slower_than_first_time'] += a['regain_cost'] > a['regained_at']
                    c['retries_with_no_return'] += a['regained_at'] == 0
            c['levels_with_a_failed_attempt'] += len(failed_levels)
            c['of_those_completed_in_the_end'] += sum(level < done for level in failed_levels)
        out[tag] = {label: dict(c) for label, c in by.items()}
    tails = defaultdict(lambda: defaultdict(list))
    for (label, game), trace in all_traces.items():
        for a in M.annotate(trace, M.counter_mask(trace)):
            if a['outcome'] in ('game_over', 'abandoned'):
                tails[label]['attempt'].append(a['stale_tail'])
                tails[label]['level'].append(a['stale_tail_level'])
    out['stale_tail_medians'] = {label: {k: statistics.median(v) for k, v in d.items()} for label, d in tails.items()}
    return out


def pilot_positions(ours, human, games, at=100):
    """Where each pilot game stands after its first `at` saved actions."""
    rows = []
    for game, trace in ours.items():
        if short(game) not in games:
            continue
        cut = dict(trace, steps=trace['steps'][:at])
        attempts = M.attempts(cut)
        level = cut['steps'][-1]['lc']
        on_level = [a for a in attempts if a['level'] == level]
        spent = sum(a['n'] + (a['reset'] is not None) for a in on_level)
        last = attempts[-1]
        rows.append({'game': short(game), 'level': level + 1, 'actions_on_level': spent,
                     'human_baseline': human[game][level], 'attempts_on_level': len(on_level),
                     'game_overs_on_level': sum(a['outcome'] == 'game_over' for a in on_level),
                     'actions_on_current_attempt': last['n'] if last['reset'] is None else 0,
                     'state': cut['steps'][-1]['state']})
    return rows


def main(out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = json.loads(BASELINES.read_text())
    human = {g: v['baseline'] for g, v in data['meta'].items()}
    ours = traces.load_events()
    everything = {('nov6-ours', g): t for g, t in ours.items()}
    everything.update(traces.load_recordings())
    result = {
        'sources': dict(Counter(label for label, _ in everything)),
        'nov6': nov6_table(ours, human, data['best']),
        'notes': notes_table(ours),
        'recovery': recovery_table(everything),
        'reset_by_game': reset_table(everything),
        'undo_by_game': undo_table(everything),
        'replay': replay_table(everything),
        'extras': extras(everything, human),
        'pilot_positions': pilot_positions(ours, human, ('tn36', 'su15', 'bp35', 'cd82', 'lf52')),
    }
    (out_dir / 'baseline.json').write_text(json.dumps(result, indent=1, default=int) + '\n')
    return result


if __name__ == '__main__':
    r = main(sys.argv[1])
    print(json.dumps({k: r[k] for k in ('sources', 'notes', 'recovery', 'replay')}, indent=1, default=int))
    print(json.dumps(r['nov6']['actions_by_outcome']), json.dumps(r['nov6']['unfinished_bands']))
