"""Prepare matched, teacher-forced prompt fixtures; zero inference or gameplay."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.initial_geometry_assistance_v1.geometry import canonical, digest
from research.initial_geometry_assistance_v1.live_io import sha, write_new
from research.initial_geometry_assistance_v1.live_operator import verify_review
from research.initial_geometry_assistance_v1.live_runtime import verify_inputs
from research.initial_geometry_assistance_v1.policy import request_for
from research.recent_feedback_v1.audit import baseline_request
from research.recent_feedback_v1.interface import VARIANTS, request_for_variant


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'inputs', 'review', 'evaluation', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    parser.add_argument('--evaluation-pin', required=True)
    args = parser.parse_args()
    lock, pin = verify_review(args.review, ROOT)
    if sha(args.evaluation) != args.evaluation_pin:
        raise ValueError('evaluation differs from external pin')
    evaluation = json.loads(args.evaluation.read_bytes())
    evidence_pin = digest({p.relative_to(args.run).as_posix(): sha(p)
                           for p in sorted(args.run.rglob('*')) if p.is_file()})
    if (evaluation.get('technically_complete') is not True or evaluation['review_lock_sha256'] != pin or
            evaluation['run_evidence_sha256'] != evidence_pin):
        raise ValueError('run not bound to independently complete evaluation')
    verify_inputs(args.inputs, lock['input_manifest_sha256'])
    cases = json.loads((args.inputs/'cases.json').read_bytes())['cases']
    protocol_path = ROOT/'research/recent_feedback_v1/protocol.json'
    protocol = json.loads(protocol_path.read_bytes())
    if [c['game_id'] for c in cases] != protocol['games']:
        raise ValueError('game order differs')
    args.output.mkdir(parents=True, exist_ok=False)
    rows, max_summary = [], 0
    for case in cases:
        events = [json.loads(line) for line in
                  (args.run/(case['case_id']+'-reviewed.jsonl')).read_text(encoding='utf-8').splitlines()]
        initial, current, history = None, None, []
        for event in events:
            if event['kind'] == 'initial':
                initial = current = event['observation']
            elif event['kind'] == 'request':
                base = request_for(initial, case['geometry']['reviewed'], current, history,
                                   event['step'], protocol['model'])
                if event['body'] != base or event['request_sha256'] != digest(base):
                    raise ValueError('retained baseline prompt differs')
                for variant in VARIANTS:
                    body = request_for_variant(base, variant)
                    if baseline_request(body, variant) != base:
                        raise ValueError('summary replay did not recover exact baseline')
                    name = f"requests/{case['case_id']}-{event['step']:02d}-{variant}.json"
                    path = args.output/name
                    path.parent.mkdir(exist_ok=True)
                    write_new(path, body)
                    if variant == 'recent_summary':
                        max_summary = max(max_summary, len(body['messages'][1]['content'][-1]['text'].encode()))
                    rows.append({'case_id': case['case_id'], 'game_id': case['game_id'], 'variant': variant,
                        'step': event['step'], 'path': name, 'sha256': sha(path),
                        'request_sha256': digest(body), 'base_request_sha256': digest(base),
                        'images': sum(p['type'] == 'image_url' for p in body['messages'][1]['content'])})
            elif event['kind'] == 'transition':
                history.append(event)
                current = event['after']
        if len(history) != 24:
            raise ValueError('expected certified 24-action trajectory')
    if len(rows) != 288:
        raise ValueError('expected 144 paired contexts')
    files = {r['path']: r['sha256'] for r in rows}
    manifest = {'schema': 'recent_feedback_teacher_forced_inputs_v1', 'live_launch_package': False,
        'baseline_review_lock_sha256': pin, 'input_manifest_sha256': lock['input_manifest_sha256'],
        'run_evidence_sha256': evidence_pin, 'independent_evaluation_sha256': args.evaluation_pin,
        'protocol_sha256': sha(protocol_path), 'files': files, 'rows': rows,
        'contexts': 144, 'requests': len(rows), 'maximum_summary_UTF8_bytes': max_summary,
        'qualification': 'Both variants evaluated at identical retained reviewed-arm contexts. No neural responses or prospective gameplay outcomes are generated.'}
    write_new(args.output/'manifest.json', manifest)
    source_names = set(lock['review_sources'])
    source_names.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'research/recent_feedback_v1').glob('*.py'))
    source_names.update(['research/recent_feedback_v1/protocol.json', 'scripts/prepare_recent_feedback_v1.py',
                         'scripts/rehearse_recent_feedback_v1.py', 'scripts/audit_recent_feedback_tokens_v1.py',
                         'tests/test_recent_feedback_v1.py'])
    snapshot = {'schema': 'recent_feedback_CPU_draft_lock_v1', 'live_launch_package': False,
        'manifest_sha256': sha(args.output/'manifest.json'),
        'sources': {name: sha(ROOT/name) for name in sorted(source_names)},
        'baseline_review_lock_sha256': pin, 'new_model_requests': 0, 'new_game_actions': 0,
        'provider_writes': 0, 'GPU_jobs': 0}
    write_new(args.output/'draft-lock.json', snapshot)
    verify_review(args.review, ROOT)
    print(json.dumps({'draft_lock_sha256': sha(args.output/'draft-lock.json'), 'manifest_sha256': snapshot['manifest_sha256'],
        'contexts': 144, 'requests': len(rows), 'max_summary_UTF8_bytes': max_summary,
        'live_launch_package': False, 'GPU_jobs': 0}), flush=True)


if __name__ == '__main__':
    main()
