"""Keep one game's continuation going until it has played a given number of new actions.

A run that is paused by the computer sleeping resumes by itself on wake, but the model call that was in
flight can time out three times in a row, which ends the run. This starts `continue_run.py run <game>`
and, whenever that stops short of the target for any reason, waits and starts it again from the last
saved action, after the free check. Each start is the same command a person would type; nothing in a
run is changed.

    keep_going.py <game> <new actions> --caps <file> --resets <n>

It gives up after MAX_EMPTY_STARTS starts in a row that add no action (a usage limit, no network).

Usage (project environment): .venv/bin/python -m research.baseline_continue_v1.keep_going wa30 550 --caps ... --resets 50
"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / '.cache/claude_arc_runs'
WAIT_SECONDS = 300          # between a start that stopped short and the next one
MAX_EMPTY_STARTS = 4        # starts in a row that add no action before giving up


def last_run(game):
    """(folder, actions, solved) of the game's run with the most actions; the newest one on a tie."""
    best = None
    for folder in sorted(RUNS.glob('baseline-continue-%s-2*' % game)):
        count, last = 0, None
        with (folder / 'events.jsonl').open(encoding='utf-8') as handle:
            for line in handle:
                if '"kind":"transition"' in line and line.endswith('\n'):
                    count, last = count + 1, line
        if best is None or count >= best[1]:
            best = (folder, count, bool(last) and json.loads(last)['after']['state'] == 'WIN')
    return best


def stop_reason(folder):
    for path in sorted(RUNS.glob('baseline-continue-2*.json'), reverse=True):
        for entry in json.loads(path.read_text())['games']:
            if entry['folder'] == str(folder.relative_to(ROOT)):
                return entry.get('stop_reason')
    return None


def say(*parts):
    print(time.strftime('%Y-%m-%d %H:%M:%S'), 'keep_going:', *parts, flush=True)


if __name__ == '__main__':
    if len(sys.argv) < 3 or '--caps' not in sys.argv:
        raise SystemExit(__doc__)
    game, new, options = sys.argv[1], int(sys.argv[2]), sys.argv[3:]      # options go to continue_run unchanged
    table = json.loads((ROOT / options[options.index('--caps') + 1]).read_text())['games']
    table_cap = next(g['action_cap'] for g in table if g['game'] == game)
    folder, done, solved = last_run(game)
    target, empty = min(done + new, table_cap), 0
    base = [sys.executable, '-u', '-m', 'research.baseline_continue_v1.continue_run']
    say(game, 'has', done, 'actions; target', target)
    while not solved and done < target:
        extend = ['--extend', '%s=%s' % (game, folder.relative_to(ROOT))]
        if subprocess.run(base + ['check', game] + options + extend, cwd=ROOT, stdout=subprocess.DEVNULL).returncode:
            say('the free check failed for', folder.name, '- stopping')
            sys.exit(2)
        say('start from action', done)
        subprocess.run(base + ['run', game, '--budget', str(target - done)] + options + extend, cwd=ROOT)
        before = done
        folder, done, solved = last_run(game)
        say('stopped at action', done, '| reason', stop_reason(folder), '| run', folder.name)
        if solved or done >= target:
            break
        empty = empty + 1 if done == before else 0
        if empty >= MAX_EMPTY_STARTS:
            say('no new action in', empty, 'starts in a row - stopping')
            sys.exit(1)
        time.sleep(WAIT_SECONDS)
    say('finished at action', done, '| solved', solved)
