"""Create a private, non-launchable recognition/transfer CPU snapshot."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.feedback_probe_v1.live_contract import verify_inputs
from research.feedback_probe_v1.live_operator import verify_review
from research.feedback_probe_v1.source_closure import source_inventory
from research.feedback_probe_v1.interface import recognition_key
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.live_io import sha, write_new
from research.feedback_summary_probe_v1.preparation import derive_checkpoints, model_rows, protocol, verify_prepared


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-run', 'source-inputs', 'source-review', 'source-evaluation', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    frozen = protocol()
    source_lock, source_pin = verify_review(args.source_review, ROOT)
    if (source_pin != frozen['source_review_lock_sha256'] or
            sha(args.source_evaluation) != frozen['source_evaluation_sha256'] or
            sha(args.source_inputs/'manifest.json') != frozen['source_input_manifest_sha256']):
        raise ValueError('source artifacts differ from external protocol pins')
    evaluation = json.loads(args.source_evaluation.read_bytes())
    evidence = digest({p.relative_to(args.source_run).as_posix(): sha(p)
                       for p in sorted(args.source_run.rglob('*')) if p.is_file()})
    if (evaluation.get('technically_complete') is not True or
            evaluation['review_lock_sha256'] != source_pin or
            evidence != frozen['source_run_evidence_sha256'] or evaluation['run_evidence_sha256'] != evidence):
        raise ValueError('completed source evidence differs')
    verify_inputs(args.source_inputs, frozen['source_input_manifest_sha256'])
    if sha(args.source_inputs/'checkpoints.json') != frozen['source_checkpoint_file_sha256']:
        raise ValueError('source checkpoint bytes differ')
    original = json.loads((args.source_inputs/'checkpoints.json').read_bytes())
    checkpoints = derive_checkpoints(original['checkpoints'])
    args.output.mkdir(parents=True, exist_ok=False)
    write_new(args.output/'source-checkpoints.json', original)
    write_new(args.output/'checkpoints.json', {'schema': 'feedback_summary_probe_checkpoints_v1', 'checkpoints': checkpoints})
    rows = model_rows(checkpoints)
    for row, body in rows:
        path = args.output/row['path']
        path.parent.mkdir(exist_ok=True)
        write_new(path, body)
    for checkpoint in checkpoints:
        path = args.output/'private-reference-keys'/(checkpoint['checkpoint_id']+'.json')
        path.parent.mkdir(exist_ok=True)
        write_new(path, recognition_key(checkpoint['base_request']))
    maxima = frozen['prospective_maxima']
    if (2*sum(c['decision_step'] for c in checkpoints) != maxima['prefix_dispatches'] or
            len(rows) != 32 or len({c['checkpoint_id'] for c in checkpoints}) != 8):
        raise ValueError('checkpoint scope/cost differs')
    manifest = {'schema': 'feedback_summary_probe_CPU_inputs_v1', 'live_launch_package': False,
        'protocol_sha256': sha(ROOT/'research/feedback_summary_probe_v1/protocol.json'),
        **{k: frozen[k] for k in ('source_review_lock_sha256', 'source_evaluation_sha256',
                                  'source_run_evidence_sha256', 'source_input_manifest_sha256')},
        'source_checkpoint_inventory_sha256': digest(original['checkpoints']),
        'files': {p.relative_to(args.output).as_posix(): sha(p) for p in sorted(args.output.rglob('*')) if p.is_file()},
        'model_input_rows': [row for row, _ in rows], 'prospective_maxima': maxima,
        'future_inference_allowlist': sorted({'checkpoints.json'} | {row['path'] for row, _ in rows}),
        'privacy': 'Private CPU preparation only. Source evidence and reference keys must never enter an inference upload.'}
    write_new(args.output/'manifest.json', manifest)
    entries = set(source_lock['review_sources'])
    entries.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'research/feedback_summary_probe_v1').glob('*') if p.is_file())
    entries.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'tests').glob('test_feedback_summary_probe*'))
    entries.update(('scripts/prepare_feedback_summary_probe_v1.py', 'scripts/rehearse_feedback_summary_probe_v1.py',
                    'scripts/audit_feedback_summary_probe_tokens_v1.py'))
    lock = {'schema': 'feedback_summary_probe_CPU_draft_lock_v1', 'live_launch_package': False,
        'manifest_sha256': sha(args.output/'manifest.json'), 'sources': source_inventory(ROOT, entries),
        'GPU_jobs': 0, 'provider_writes': 0, 'neural_generations': 0}
    write_new(args.output/'draft-lock.json', lock)
    pin = sha(args.output/'draft-lock.json')
    verify_prepared(args.output, pin, ROOT)
    print(json.dumps({'draft_lock_sha256': pin, 'manifest_sha256': lock['manifest_sha256'],
                      **maxima, 'GPU_jobs': 0, 'live_launch_package': False}))


if __name__ == '__main__':
    main()
