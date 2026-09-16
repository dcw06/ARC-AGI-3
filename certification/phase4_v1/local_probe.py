"""Actual offline development environment probe with explicitly fake completions."""
import argparse
import json
import logging
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agent.e1_policy import CompletionResult, E1Policy, E1ModelBinding
from agent.feature_manifest import load_e1_feature_manifests
from agent.framework_adapter import LocalFrameworkAdapter
from agent.scheduler import QueuedInferenceExecutor
from agent.watchdog import DeadlineWatchdog
from certification.phase4_v1.lifecycle import (IsolatedInference, run_client,
                                              evaluate_local_record, validate_freeze)


class ScriptedCompletion:
    def __init__(self, fault, watchdog):
        self.fault, self.watchdog = fault, watchdog

    def complete(self, request):
        if self.fault == 'policy_error':
            raise TimeoutError('injected completion failure; no model used')
        observation = json.loads(request['messages'][-1]['content'])['observation']
        legal = observation['legal_actions']
        action = next((a for a in legal if a != 0), legal[0])
        if self.fault == 'cancel':
            self.watchdog.cancel()
        return CompletionResult(json.dumps({'action': {'action_id': action,
            'action_data': {'x': 0, 'y': 0} if action == 6 else {}}}))


def probe(fault='none'):
    from arc_agi import Arcade, OperationMode
    _, rows = validate_freeze()
    # Frozen ls20 row only: no download, no discovery-based substitution.
    row = next(r for r in rows if r['game_id'] == 'ls20-9607627b')
    row = {**row, 'max_actions': 2}
    watchdog = DeadlineWatchdog(60, 10)
    manifests = load_e1_feature_manifests(ROOT / 'config/e1_feature_manifests.yaml')
    primary = json.loads((ROOT / 'config/operational_primary.yaml').read_text())['primary']
    logger = logging.getLogger('p4-lifecycle-probe')
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    with tempfile.TemporaryDirectory(prefix='p4-lifecycle-local-') as scratch:
        arcade = Arcade(operation_mode=OperationMode.OFFLINE,
                        environments_dir=str(ROOT / 'environment_files'),
                        recordings_dir=scratch, logger=logger)
        adapter = LocalFrameworkAdapter(arcade, seed_by_game={row['game_id']: row['environment_seed']})
        with QueuedInferenceExecutor(maxsize=110, worker_count=8, max_age_seconds=300) as executor:
            def factory(client):
                return E1Policy(manifest=manifests['E1S-R'],
                    binding=E1ModelBinding.from_mapping(primary['model_binding']),
                    client=ScriptedCompletion(fault, watchdog),
                    inference=IsolatedInference(executor, row['client_id']), seed=0)
            record = run_client(row, adapter, factory, watchdog)
    return {'schema_version': 1, 'fault': fault, 'smoke_action_limit': 2,
            'frozen_target_action_limit': 80, 'record': record,
            'evaluation': evaluate_local_record(record, expected_fault=fault)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fault', choices=['none', 'policy_error', 'cancel'], default='none')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    value = probe(args.fault)
    # Exclusive creation prevents overwriting evidence from an earlier exercise.
    with args.output.open('x') as stream:
        json.dump(value, stream, indent=2)
    print(json.dumps(value['evaluation']))
    raise SystemExit(0 if value['evaluation']['passed'] else 1)
