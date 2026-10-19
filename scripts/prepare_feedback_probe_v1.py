"""Freeze checkpoint inputs, separate reference keys and source bindings on CPU."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.live_io import sha, write_new
from research.initial_geometry_assistance_v1.live_operator import verify_review
from research.initial_geometry_assistance_v1.live_worker import MODEL
from research.recent_feedback_v1.live_contract import verify_inputs
from research.feedback_probe_v1.checkpoints import checked_checkpoint, select_checkpoints
from research.feedback_probe_v1.interface import VARIANTS, policy_request, recognition_key, recognition_request
from research.feedback_probe_v1.preparation import verify_prepared
from research.feedback_probe_v1.source_closure import source_inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'inputs', 'review', 'evaluation', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    protocol_path = ROOT/'research/feedback_probe_v1/protocol.json'
    protocol = json.loads(protocol_path.read_bytes())
    lock, pin = verify_review(args.review, ROOT)
    if (pin != protocol['source_review_lock_sha256'] or
            sha(args.evaluation) != protocol['source_evaluation_sha256']):
        raise ValueError('source review/evaluation not externally frozen')
    evaluation = json.loads(args.evaluation.read_bytes())
    evidence = digest({p.relative_to(args.run).as_posix(): sha(p) for p in sorted(args.run.rglob('*')) if p.is_file()})
    if (evaluation['technically_complete'] is not True or evaluation['review_lock_sha256'] != pin or
            evidence != protocol['source_run_evidence_sha256'] or evaluation['run_evidence_sha256'] != evidence):
        raise ValueError('source run differs from independently complete exact evidence')
    verify_inputs(args.inputs, lock['input_manifest_sha256'])
    cases = json.loads((args.inputs/'cases.json').read_bytes())['cases']
    selected, missing = [], {}
    for case in cases:
        events = [json.loads(line) for line in (args.run/(case['case_id']+'-recent_raw.jsonl')).read_text(encoding='utf-8').splitlines()]
        rows = select_checkpoints(case, events, model=MODEL)
        missing[case['game_id']] = sorted({'changed', 'unchanged'} - {r['stratum'] for r in rows})
        for row in rows:
            checked_checkpoint(row, model=MODEL)
            row['order'] = list(VARIANTS if len(selected) % 2 == 0 else reversed(VARIANTS))
            selected.append(row)
    args.output.mkdir(parents=True, exist_ok=False)
    write_new(args.output/'checkpoints.json', {'schema': 'feedback_probe_checkpoints_v1', 'checkpoints': selected})
    rows = []
    for checkpoint in selected:
        identity = checkpoint['checkpoint_id']
        for kind in (*VARIANTS, 'recognition'):
            body = (recognition_request(checkpoint['base_request']) if kind == 'recognition' else
                    policy_request(checkpoint['base_request'], kind))
            path = args.output/'model-inputs'/(identity+'-'+kind+'.json')
            path.parent.mkdir(exist_ok=True)
            write_new(path, body)
            rows.append({'checkpoint_id': identity, 'kind': kind, 'path': path.relative_to(args.output).as_posix(),
                         'request_sha256': digest(body)})
        path = args.output/'private-reference-keys'/(identity+'.json')
        path.parent.mkdir(exist_ok=True)
        write_new(path, recognition_key(checkpoint['base_request']))
    prefix_sum = sum(c['decision_step'] for c in selected)
    ceilings = {'checkpoints': len(selected), 'policy_conditions': 2*len(selected),
        'policy_generations': 8*len(selected), 'recognition_generations': len(selected), 'startup_canary': 1,
        'total_generations': 9*len(selected)+1, 'prefix_dispatches': 2*prefix_sum,
        'continuation_dispatches': 8*len(selected), 'bootstrap_resets': 2*len(selected),
        'offline_actions_including_restoration': 2*prefix_sum+10*len(selected), 'local_scorecards': 2*len(selected)}
    files = {p.relative_to(args.output).as_posix(): sha(p) for p in sorted(args.output.rglob('*')) if p.is_file()}
    manifest = {'schema': 'feedback_probe_CPU_inputs_v1', 'live_launch_package': False,
        'protocol_sha256': sha(protocol_path), 'source_review_lock_sha256': pin,
        'source_evaluation_sha256': sha(args.evaluation), 'source_run_evidence_sha256': evidence,
        'source_input_manifest_sha256': lock['input_manifest_sha256'],
        'files': files, 'model_input_rows': rows, 'missing_strata': missing, 'prospective_maxima': ceilings,
        'privacy': 'Private CPU draft. Reference keys are not model inputs and must be excluded from any future inference upload.',
        'qualification': 'Case selection uses only the prefix before the checkpoint. No next action/outcome is supplied or used to select it.'}
    write_new(args.output/'manifest.json', manifest)
    sources = set(lock['review_sources'])
    sources.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'research/feedback_probe_v1').glob('*.py'))
    sources.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'tests').glob('test_feedback_probe_*v1.py'))
    sources.update(['research/feedback_probe_v1/protocol.json', 'scripts/prepare_feedback_probe_v1.py',
                    'scripts/rehearse_feedback_probe_v1.py', 'scripts/audit_feedback_probe_tokens_v1.py'])
    snapshot = {'schema': 'feedback_probe_CPU_draft_lock_v1', 'live_launch_package': False,
        'manifest_sha256': sha(args.output/'manifest.json'), 'sources': source_inventory(ROOT, sources),
        'source_review_lock_sha256': pin, 'new_model_generations': 0, 'new_game_actions': 0,
        'provider_writes': 0, 'GPU_jobs': 0}
    write_new(args.output/'draft-lock.json', snapshot)
    draft_pin = sha(args.output/'draft-lock.json')
    verify_prepared(args.output, draft_pin, ROOT)
    verify_review(args.review, ROOT)
    print(json.dumps({'draft_lock_sha256': draft_pin, 'manifest_sha256': snapshot['manifest_sha256'],
                      **ceilings, 'live_launch_package': False, 'GPU_jobs': 0}), flush=True)


if __name__ == '__main__': main()
