"""Markdown tables for the recovery report, printed from data/baseline.json and data/checks.json.

Usage: tables.py <data_dir>
"""
import json
import sys
from pathlib import Path

NAMES = {'nov6-ours': 'Ours, 6 Nov (Opus 5.5, 100-action cap)',
         'opus5-standard-high': 'Official standard harness, Opus 5',
         'astra-standard-high': 'Official standard harness, GPT-6 Astra',
         'astra-adapter-high': 'Provider adapter, GPT-6 Astra',
         'tycho-opus5_orchestrator': 'Tycho, Opus 5'}
ORDER = list(NAMES)


def pct(part, whole):
    return '%.1f%%' % (100 * part / whole) if whole else '-'


def recovery(base):
    print('| Source | Actions | Levels done | In completed attempts | In failed attempts, resets included | '
          'In the unfinished last attempt | Resets after game over | Resets chosen from a live position | '
          'Retries that completed the level |')
    print('|---|---|---|---|---|---|---|---|---|')
    for label in ORDER:
        r = base['recovery'][label]
        failed = r.get('dead_end_loss', 0)
        open_ = r.get('actions_open', 0) + r.get('actions_game_over_final', 0)
        print('| %s | %s | %d | %s | %s | %s | %d | %d | %d of %d |' % (
            NAMES[label], format(r['actions'], ','), r['levels_completed'],
            pct(r['actions_completed'], r['actions']), pct(failed, r['actions']), pct(open_, r['actions']),
            r.get('attempts_game_over', 0), r.get('attempts_abandoned', 0),
            r.get('retries_completed', 0), r.get('retries', 0)))


def returns(base):
    print('| Source | Retries | Median length of the failed attempt (game over / chosen) | '
          'Median actions without a new board at its end | Opening actions repeated exactly, median (mean) | '
          'Furthest earlier point returned to, median (mean) | Actions to get back there, median (mean) | '
          'Share of all actions spent getting back |')
    print('|---|---|---|---|---|---|---|---|')
    for label in ORDER:
        r = base['recovery'][label]
        over, chosen = r.get('len_game_over'), r.get('len_abandoned')
        tails = [r[k]['median'] for k in ('stale_tail_game_over', 'stale_tail_abandoned') if k in r]
        print('| %s | %d | %s / %s | %s | %s (%s) | %s (%s) | %s (%s) | %s |' % (
            NAMES[label], r['retries'], over['median'] if over else '-', chosen['median'] if chosen else '-',
            ' / '.join('%g' % t for t in tails), r['common_prefix']['median'], r['common_prefix']['mean'],
            r['regained_at']['median'], r['regained_at']['mean'], r['regain_cost']['median'],
            r['regain_cost']['mean'], pct(r['regain_cost_actions'], r['actions'])))


def games(base):
    print('| Game | Actions offered | Resets seen | After game over | Level kept | Board equal to the level start | '
          'ACTION7 uses that could be tested | Earlier board back, counter ignored | Within 2 cells |')
    print('|---|---|---|---|---|---|---|---|---|')
    for game, undo in base['undo_by_game'].items():
        reset = base['reset_by_game'].get(game, {})
        n = reset.get('resets', 0)
        cells = ['-'] * 3
        if undo['action7_offered']:
            t = undo.get('testable', 0)
            cells = [str(t), '%d' % undo.get('restored_ignoring_counter', 0) if t else '-',
                     '%d' % undo.get('restored_within_2_cells', 0) if t else '-']
        print('| %s | %s | %d | %s | %s | %s | %s |' % (
            game, ' '.join(map(str, undo['actions_offered'])), n, reset.get('after_game_over', 0) if n else '-',
            '%d of %d' % (reset['level_kept'], n) if n else 'not seen',
            '%d of %d' % (reset['board_equals_level_start'], n) if n else 'not seen', ' | '.join(cells)))


def unfinished(base):
    print('| Game | Unfinished level | Actions spent on it | Human baseline | Ratio | Game overs in the game | '
          'Longest run without a new board: during play | ... with hindsight |')
    print('|---|---|---|---|---|---|---|---|')
    rows = [r for r in base['nov6']['rows'] if 'unfinished_level' in r]
    for r in sorted(rows, key=lambda r: -r['ratio_to_human']):
        print('| %s | %d | %d | %d | %.2f | %d | %d | %d |' % (
            r['game'], r['unfinished_level'], r['spent_on_it'], r['human'], r['ratio_to_human'], r['game_overs'],
            r['longest_stale_run_live'], r['longest_stale_run_hindsight']))


def checks(table):
    print('| Trigger | Checks (games) | With the hindsight counter estimate | Levels checked | ... of which completed anyway | '
          'Failed attempts checked | Attempts open at the end checked |')
    print('|---|---|---|---|---|---|---|')
    for name, by in table.items():
        c = by['nov6-ours']
        late = ('%d (%d)' % (c['checks_with_hindsight_counter'], c['games_with_hindsight_counter'])
                if 'checks_with_hindsight_counter' in c else 'same')
        print('| %s | %d (%d) | %s | %d | %d | %d of %d | %d of %d |' % (
            name, c['checks'], c['games_with_a_check'], late, c['levels_checked'], c['levels_checked_and_completed'],
            c.get('checked_failed', 0), c['attempts_failed'],
            c.get('checked_open', 0) + c.get('checked_game_over_final', 0),
            c['attempts_open'] + c.get('attempts_game_over_final', 0)))


def checks_other(table, names):
    print('| Trigger | Source | Checks (games) | Levels checked | ... of which completed anyway |')
    print('|---|---|---|---|---|')
    for name in names:
        for label in ORDER[1:]:
            c = table[name][label]
            print('| %s | %s | %d (%d) | %d | %d |' % (
                name, NAMES[label], c['checks'], c['games_with_a_check'], c['levels_checked'],
                c['levels_checked_and_completed']))


def extras(base):
    print('| Source | In attempts ended by game over | In attempts the agent reset | Chosen resets | ... after a single action | '
          'Levels with a failed attempt | ... completed in the end | Retry actions | ... spent getting back | '
          'First-time cost of that path |')
    print('|---|---|---|---|---|---|---|---|---|---|')
    for tag, note in (('all_games', ''), ('without_su15_sk48', ', without su15 and sk48')):
        for label in ORDER:
            c = base['extras'][tag][label]
            if tag != 'all_games' and label not in ('opus5-standard-high', 'astra-standard-high'):
                continue
            print('| %s%s | %s | %s | %d | %d | %d | %d | %d | %d | %d |' % (
                NAMES[label], note, pct(c.get('actions_in_game_over_attempts_with_reset', 0), c['actions']),
                pct(c.get('actions_in_chosen_reset_attempts_with_reset', 0), c['actions']), c.get('chosen_resets', 0),
                c.get('chosen_after_one_action', 0), c['levels_with_a_failed_attempt'],
                c['of_those_completed_in_the_end'], c.get('retry_actions', 0), c.get('actions_to_get_back', 0),
                c.get('first_time_actions_to_that_point', 0)))
    print()
    print('| Game | Level | Actions on it | Human baseline | Attempts | Game overs | Actions on the current attempt |')
    print('|---|---|---|---|---|---|---|')
    for r in base['pilot_positions']:
        print('| %s | %d | %d | %d | %d | %d | %d |' % (r['game'], r['level'], r['actions_on_level'], r['human_baseline'],
                                                        r['attempts_on_level'], r['game_overs_on_level'],
                                                        r['actions_on_current_attempt']))
    print('stale tail medians', base['extras']['stale_tail_medians'])


def main(folder):
    folder = Path(folder)
    base = json.loads((folder / 'baseline.json').read_text())
    table = json.loads((folder / 'checks.json').read_text())
    for title, call in (('Where actions went', lambda: recovery(base)), ('After a reset', lambda: returns(base)),
                        ('Per game: reset and undo', lambda: games(base)),
                        ('6 Nov unfinished levels', lambda: unfinished(base)),
                        ('Triggers on the 6 Nov run', lambda: checks(table)),
                        ('Triggers on public runs', lambda: checks_other(
                            table, ['no new board for 6', 'level actions at 1.00x human',
                                    'level actions at 1.00x human, not before 30'])),
                        ('Review breakdowns', lambda: extras(base))):
        print('\n### ' + title + '\n')
        call()
    replay = base['replay']
    total = {k: sum(c.get(k, 0) for c in replay.values())
             for k in ('compared', 'same', 'different', 'positions_reached_again', 'positions_reached_by_two_sources')}
    print('\nreplay', total, 'games', len(replay), 'fewest comparisons',
          min((c['compared'], g) for g, c in replay.items()))
    print('notes', base['notes'])
    print('nov6', base['nov6']['actions_by_outcome'], base['nov6']['unfinished_bands'])


if __name__ == '__main__':
    main(sys.argv[1])
