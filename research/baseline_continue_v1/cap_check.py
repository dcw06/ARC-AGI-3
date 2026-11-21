"""Offline checks on the action caps, from the saved play. No model call, no network.

1. The card score when every game is cut at a share of its cap.
2. The card score when a game also ends once its open level has used k times that level's human count.
3. Where each game stood when it stopped.
4. How the official standard-harness runs (ARC Prize's recordings) ended their unsolved games.

A cut is a prefix of the saved play, so 1 and 2 are exact for rules that stop a game earlier. They say
nothing about play past the cap.

Usage (project environment): .venv/bin/python -m research.baseline_continue_v1.cap_check
"""
import json

from research.baseline_continue_v1 import replay_scorecard as rs

CAPS = rs.ROOT / 'reports/baseline_continue_v1/action_caps_human.json'
OFFICIAL_RUNS = rs.ROOT / 'reports/arc_agi3_loss_audit/data/recordings_audit.json'


def card(plan, human, cut):
    """(card score, actions, levels) when each game's saved play is cut to cut(game, steps)."""
    score = actions = levels = 0
    for game, saved in plan.items():
        steps = cut(game, saved['steps'])
        used, done = rs.level_actions(steps, len(human[game]))
        score += rs.game_score(used, human[game], done)[0]
        actions += len(steps)
        levels += done
    return score / len(plan), actions, levels


def level_limit(human, k):
    """Cut a game at the action where its open level reaches k times the level's human count."""
    def cut(game, steps):
        level = used = 0
        for i, step in enumerate(steps):
            if step['before_levels'] != level:
                level, used = step['before_levels'], 0
            used += 1
            if level < len(human[game]) and used >= k * human[game][level] and step['levels'] == level:
                return steps[:i + 1]
        return steps
    return cut


if __name__ == '__main__':
    official = rs.saved_summary()['official_scorecard']
    human = {e['id']: e['runs'][0]['level_baseline_actions'] for e in official['environments']}
    caps = {g['game']: g['action_cap'] for g in json.loads(CAPS.read_text())['games']}
    plan = rs.recorded()
    name = lambda game: game.split('-')[0]

    print('1. every game cut at a share of its cap')
    for share in (0.25, 0.5, 0.75, 1.0):
        s, a, l = card(plan, human, lambda g, st: st[:int(round(share * caps[name(g)]))])
        print('   %3d%% | actions %6d | levels %3d | score %.2f' % (100 * share, a, l, s))

    print('2. same caps, and a game ends when its open level has used k times the human count')
    for k in (2, 3, 5, 8):
        s, a, l = card(plan, human, level_limit(human, k))
        print('   k %d | actions %6d | levels %3d | score %.2f' % (k, a, l, s))

    print('3. where each game stood when it stopped')
    on_open = total = 0
    for game, saved in plan.items():
        used, done = rs.level_actions(saved['steps'], len(human[game]))
        total += len(saved['steps'])
        if done == len(human[game]):
            print('   %s  cap %5d  used %5d  solved' % (name(game), caps[name(game)], len(saved['steps'])))
            continue
        on_open += used[done]
        print('   %s  cap %5d  used %5d  %d of %d  open level %d: %4d actions, human %3d, %.1f times' % (
            name(game), caps[name(game)], len(saved['steps']), done, len(human[game]), done + 1, used[done],
            human[game][done], used[done] / human[game][done]))
    print('   actions on levels still open at the end: %d of %d' % (on_open, total))

    print('4. official standard-harness runs: unsolved games that ended at exactly 5 times the human count on the open level')
    runs = json.loads(OFFICIAL_RUNS.read_text())
    for run in ('opus5-standard-high', 'astra-standard-high'):
        same, other = [], []
        for game, row in runs[run].items():
            done = row['levels_completed']
            if done < len(human[game]):
                (same if row['unfinished'] == 5 * human[game][done] else other).append(
                    '%s level %d: %d against %d' % (name(game), done + 1, row['unfinished'], 5 * human[game][done]))
        print('   %s: %d of %d | not: %s' % (run, len(same), len(same) + len(other), '; '.join(other) or 'none'))
