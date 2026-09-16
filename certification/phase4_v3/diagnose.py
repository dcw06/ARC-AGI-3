"""Paired fresh-runtime reproduction of post-GAME_OVER dispatch; no model/GPU."""
import argparse
import json
import logging
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from arc_agi import Arcade, OperationMode
from agent.e1_policy import E1Policy, E1ModelBinding
from agent.feature_manifest import load_e1_feature_manifests
from agent.framework_adapter import LocalFrameworkAdapter
from agent.scheduler import QueuedInferenceExecutor
from agent.watchdog import DeadlineWatchdog
from certification.phase4_v1.lifecycle import validate_freeze, IsolatedInference, run_client as old_run
from certification.phase4_v1.local_probe import ScriptedCompletion
from certification.phase4_v2.package import verify_environment_mount
from certification.phase4_v3.lifecycle import run_client as new_run
from certification.phase4_v3.worker import AuditedAdapter


def reproduce(environments):
    verify_environment_mount(environments, json.loads((ROOT / 'reports/phase4_v2_offline_package.json').read_text()))
    _, rows = validate_freeze()
    manifest = load_e1_feature_manifests(ROOT / 'config/e1_feature_manifests.yaml')['E1S-R']
    binding = E1ModelBinding.from_mapping(json.loads((ROOT / 'config/operational_primary.yaml').read_text())['primary']['model_binding'])
    records = []
    logger = logging.getLogger('p4-terminal-diagnostic')
    logger.handlers = [logging.NullHandler()]
    logger.propagate = False
    for base in ('sp80', 'vc33', 's5i5', 'sc25', 'lf52'):
        row = next(r for r in rows if r['game_id'].startswith(base + '-'))
        # Counterbalance fresh old/new pairs; never retry the ambiguous transaction.
        for repetition, order in enumerate((('old', 'new'), ('new', 'old')), 1):
            for arm in order:
                with tempfile.TemporaryDirectory(prefix='p4-terminal-') as scratch:
                    arcade = Arcade(operation_mode=OperationMode.OFFLINE,
                        environments_dir=str(Path(environments).resolve()), recordings_dir=scratch, logger=logger)
                    adapter = AuditedAdapter(LocalFrameworkAdapter(arcade,
                        seed_by_game={row['game_id']: row['environment_seed']}))
                    watchdog = DeadlineWatchdog(60, 10)
                    with QueuedInferenceExecutor(worker_count=8) as queue:
                        def factory(client):
                            return E1Policy(manifest=manifest, binding=binding,
                                client=ScriptedCompletion('none', watchdog),
                                inference=IsolatedInference(queue, row['client_id']), seed=row['request_seed'])
                        record = (old_run if arm == 'old' else new_run)(row, adapter, factory, watchdog)
                    records.append({'arm': arm, 'repetition': repetition, 'record': record,
                                    'dispatch_audit': adapter.audit})
    checks = []
    for base in ('sp80', 'vc33', 's5i5', 'sc25', 'lf52'):
        for repetition in (1, 2):
            pair = {r['arm']: r for r in records if r['record']['game_id'].startswith(base + '-') and r['repetition'] == repetition}
            old, new = pair['old'], pair['new']
            old_result, new_result = old['record']['result'], new['record']['result']
            def actions(audit):
                return [(a['action_id'], a['action_data']) for a in audit]
            passed = (old_result['terminal_reason'] == 'outcome_unknown_quarantine'
                and old['dispatch_audit'][-1]['pre_state'] == 'GAME_OVER'
                and old['dispatch_audit'][-1]['cause'] == 'observation has no rendered frames'
                and new_result['terminal_reason'] == 'game_over'
                and new_result['ambiguous_actions'] == 0
                and actions(old['dispatch_audit'][:-1]) == actions(new['dispatch_audit'])
                and all(r['record']['finalization_status'] == 'acknowledged_local_framework' for r in pair.values()))
            checks.append({'game': base, 'repetition': repetition, 'passed': passed,
                           'acknowledged_before_terminal': new_result['acknowledged_actions']})
    return {'schema_version': 1, 'scope': 'scripted_local_terminal_lifecycle_diagnostic',
            'passed': all(c['passed'] for c in checks), 'checks': checks, 'runs': records,
            'model_inference': False, 'phase4_complete': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--environments', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    result = reproduce(args.environments)
    with args.output.open('x') as f:
        json.dump(result, f, indent=2)
    print(json.dumps({'passed': result['passed'], 'checks': result['checks']}))
    raise SystemExit(0 if result['passed'] else 1)
