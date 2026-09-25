"""Build the version-4 scripted Stage B record used by the pinned token audit."""
import json
from pathlib import Path

from research.grounded_action_v1.local import ScriptedAdapter, ScriptedService, run
from research.grounded_action_v1.replay import replay_file

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/runs/phase4-grounded-action-v1-r11-local/run.json'


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    result = run(OUT, ScriptedService(), lambda arm: ScriptedAdapter(arm))
    if result['version'] != 'grounded_action_local_v4' or result['status'] != 'complete':
        raise ValueError('scripted R11 record did not complete')
    score = replay_file(OUT)
    if score['calls'] != 12 or score['dispatches'] != 4:
        raise ValueError('scripted R11 replay drift')
    print(json.dumps({'record': str(OUT), 'version': result['version'],
                      'calls': score['calls'], 'dispatches': score['dispatches']}))


if __name__ == '__main__':
    main()
