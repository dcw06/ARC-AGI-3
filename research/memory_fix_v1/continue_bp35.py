"""Play bp35 level 2 from its start on the local game, with or without the game-over memory fix.

Every run begins by repeating the 17 saved level-1 actions of the 6 November run (no model call; every
observation must hash to the saved one), so the agent starts level 2 with the saved board and notes. It then
plays with its own choices until level 2 is solved or 100 new actions are used. No ARC service, no scorecard.

    control         the 6 November harness, unchanged
    lessons_check   plus game_over_lessons and lesson_check

    continue_bp35.py <arm> <run name> --send      one run: up to 100 model calls on the Claude subscription
    continue_bp35.py control <run name> --dry-run feeds the saved replies instead of calling a model; the run
                                                  must then reproduce the saved level-2 play action for action
    continue_bp35.py summary <run folder>...      per-run numbers from finished runs

Usage (project environment), from the repository root.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from agent.e1_policy import CompletionResult  # noqa: E402
from research.claude_arc_v1 import audit, config as C, run  # noqa: E402
from research.claude_arc_v1.backends import Budget, ClaudeCodeBackend  # noqa: E402
from research.memory_fix_v1 import bp35_local  # noqa: E402
from research.memory_fix_v1.local_arc import LocalBp35  # noqa: E402

CONTROL = ROOT / 'config/claude_arc_v1.opus55_competition.json'
SAVED = '.cache/claude_arc_runs/opus55-competition-20261106T054112Z/events.jsonl'
RUNS = ROOT / '.cache/claude_arc_runs'
LEVEL_ONE = 17        # the saved run completed level 1 with its 17th action
NEW_ACTIONS = 100
ARMS = {'control': {}, 'lessons_check': {'game_over_lessons': True, 'lesson_check': True}}


def settings(arm):
    return C.Config(**{**json.loads(CONTROL.read_text()), 'mode': 'online', 'games': ['bp35'],
                       'resume_events': SAVED, 'resume_actions': LEVEL_ONE,
                       'max_actions_per_game': LEVEL_ONE + NEW_ACTIONS, 'stop_after_levels': 2,
                       # one call per new action, with room for replies the controller sends back
                       'max_model_calls': NEW_ACTIONS + 60, **ARMS[arm]})


class SavedReplies:
    """Stands in for the model in a dry run: answers with what the model said on 6 November."""

    def __init__(self, config):
        self.config, self.budget, self.last_record = config, Budget(config), None
        self.replies, pending = [], None
        with (ROOT / SAVED).open() as handle:
            for line in handle:
                if bp35_local.GAME_ID not in line or '"kind":"model_' not in line:
                    continue
                event = json.loads(line)
                if event.get('game_id') != bp35_local.GAME_ID:
                    continue
                if event['kind'] == 'model_entered':
                    pending = event['action_index']
                elif event['kind'] == 'model_returned' and pending >= LEVEL_ONE:
                    self.replies.append(event['content'])

    def complete(self, request):
        reserved = self.budget.reserve()
        if not self.replies:
            raise KeyboardInterrupt()      # the saved run ends here
        self.budget.settle(reserved, 10, 10)
        self.last_record = {'outcome': 'saved_reply'}
        return CompletionResult(self.replies.pop(0), 10, 10, 0)


def play(arm, name, dry_run):
    config = settings(arm)
    folder = RUNS / name
    backend = SavedReplies(config) if dry_run else ClaudeCodeBackend(config, Budget(config))
    began = time.time()
    result = run.evaluate(config, backend, LocalBp35(), run.Evidence(folder))
    row = result['games'][0] if result['games'] else {}
    print(json.dumps({'run': name, 'arm': arm, 'minutes': round((time.time() - began) / 60, 1),
                      'problems': result['problems'], **{k: row.get(k) for k in (
                          'actions_acknowledged', 'levels_completed', 'stop_reason', 'level_resets', 'final_state')}}))
    return folder


def summary(folder):
    """What happened on level 2 in one finished run, read from its event log."""
    folder = Path(folder)
    events = [json.loads(line) for line in (folder / 'events.jsonl').read_text().splitlines()]
    config = next(e['config'] for e in events if e['kind'] == 'configuration')
    steps = [e for e in events if e['kind'] == 'transition']
    level_two = [s for s in steps if s['before']['levels_completed'] == 1]
    solved = any(s['after']['levels_completed'] >= 2 for s in level_two)
    deaths = [i for i, s in enumerate(level_two, 1) if s['after']['state'] == 'GAME_OVER']
    lessons = [json.loads(e['content']).get('game_over_lesson') for e in events if e['kind'] == 'model_returned']
    calls = [e for e in events if e['kind'] == 'model_returned']
    rejected = sum(e['kind'] == 'model_failed_retrying' for e in events)
    try:
        audit.audit(folder)
        audited = 'passes'
    except Exception as exc:
        audited = 'fails: %s' % exc
    final = next(e['summary'] for e in events if e['kind'] == 'summary')
    return {'run': folder.name,
            'memory': 'lessons and check' if config.get('game_over_lessons') else 'unchanged',
            'level_2_solved': solved, 'actions_on_level_2': len(level_two),
            'game_overs_on_level_2': len(deaths), 'at_level_2_action': deaths,
            'lessons_written': sum(l is not None for l in lessons),
            'model_calls': len(calls), 'replies_sent_back': rejected,
            'stop_reason': final['games'][0]['stop_reason'] if final['games'] else None,
            'problems': final['problems'], 'audit': audited}


if __name__ == '__main__':
    if sys.argv[1] == 'summary':
        for path in sys.argv[2:]:
            print(json.dumps(summary(path)))
    else:
        arm, name, flag = sys.argv[1], sys.argv[2], sys.argv[3]
        if flag not in ('--send', '--dry-run') or arm not in ARMS:
            raise SystemExit(__doc__)
        play(arm, name, flag == '--dry-run')
