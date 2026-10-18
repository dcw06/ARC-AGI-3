"""Audit retained certified evidence on CPU; never queries a provider or engine.

Detailed observations and examples are private outputs. Only summary counts
are printed. The external evaluation pin must come from the retained review.
"""
import argparse
import base64
import html
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from certification.phase4_multimodal_preflight_v3.images import png
from research.feedback_availability_v1 import episode_feedback
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.live_evaluation import lines
from research.initial_geometry_assistance_v1.live_io import sha, write_new
from research.initial_geometry_assistance_v1.live_operator import verify_review
from research.initial_geometry_assistance_v1.live_runtime import verify_inputs
from research.initial_geometry_assistance_v1.live_worker import MODEL


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'inputs', 'review', 'evaluation', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    parser.add_argument('--evaluation-pin', required=True)
    args = parser.parse_args()
    lock, lock_pin = verify_review(args.review, ROOT)
    if sha(args.evaluation) != args.evaluation_pin:
        raise ValueError('independent evaluation differs from external pin')
    evaluation = json.loads(args.evaluation.read_bytes())
    evidence_pin = digest({p.relative_to(args.run).as_posix(): sha(p)
                           for p in sorted(args.run.rglob('*')) if p.is_file()})
    if (evaluation.get('technically_complete') is not True or evaluation['review_lock_sha256'] != lock_pin or
            evaluation['run_evidence_sha256'] != evidence_pin):
        raise ValueError('run differs from independently complete evaluation')
    verify_inputs(args.inputs, lock['input_manifest_sha256'])
    cases = json.loads((args.inputs/'cases.json').read_bytes())['cases']
    expected = [(c['case_id'], a) for c in cases for a in c['order']]
    if [(e['case_id'], e['arm']) for e in evaluation['episodes']] != expected:
        raise ValueError('episode inventory differs')
    results, examples = [], []
    for case in cases:
        for arm in case['order']:
            events = lines(args.run/(case['case_id']+'-'+arm+'.jsonl'))
            result = episode_feedback(case, arm, events, model=MODEL)
            if result['summary']['decisions'] != 24:
                raise ValueError('audit expects the certified 24-action episodes')
            results.append(result)
            if arm == 'reviewed':
                # Examples are selected descriptively, never used to fit a
                # success threshold or mutate the original run evidence.
                chosen = next((r for r in result['decisions']
                               if r['visible_same_action_unchanged_grid_steps']), result['decisions'][min(3, len(result['decisions'])-1)])
                event = next(e for e in events if e['kind'] == 'transition' and e['step'] == chosen['step'])
                images = ['data:image/png;base64,'+base64.b64encode(png(event[k]['grid'], cell=7)).decode()
                          for k in ('before', 'after')]
                examples.append({'game_id': case['game_id'], 'arm': arm, 'row': chosen, 'images': images})
    args.output.mkdir(parents=True, exist_ok=False)
    audit = {'schema': 'feedback_availability_retrospective_v1', 'evaluation_sha256': args.evaluation_pin,
             'run_evidence_sha256': evidence_pin, 'review_lock_sha256': lock_pin, 'episodes': results,
             'producer_sha256': {name: sha(ROOT/name) for name in
                ('research/feedback_availability_v1.py', 'scripts/audit_feedback_availability_v1.py')},
             'new_model_requests': 0, 'new_game_actions': 0, 'provider_writes': 0, 'GPU_jobs': 0,
             'qualification': 'Retrospective availability, not proof of attention, causal understanding or hidden-state equality.'}
    write_new(args.output/'audit.json', audit)
    summary = [{'game_id': r['game_id'], 'arm': r['arm'], **r['summary']} for r in results]
    write_new(args.output/'summary.json', {'episodes': summary, 'audit_sha256': sha(args.output/'audit.json')})
    sections = []
    for example in examples:
        row = example['row']
        sections.append('<section><h2>'+html.escape(example['game_id'])+' / reviewed / step '+str(row['step'])+
                        '</h2><p>Before action → after action. This is retained evidence, not a new run.</p><div>'+''.join(
                            '<img width="448" height="448" src="'+url+'">' for url in example['images'])+
                        '</div><pre>'+html.escape(json.dumps({k: v for k, v in row.items() if k != 'subsequent_outcome'}, indent=2))+
                        '</pre><p>Subsequent changed cells: '+str(row['subsequent_outcome']['changed_cell_count'])+'</p></section>')
    page = '<!doctype html><meta charset="utf-8"><title>Private feedback audit</title><style>body{font-family:system-ui;margin:24px;background:#fafafa}section{margin:32px 0}img{image-rendering:pixelated;margin:8px;border:1px solid #aaa}pre{white-space:pre-wrap}</style><h1>Private retained feedback examples</h1><p>Evidence visibility does not establish that the model understood it. Changed pixels are not automatically progress.</p>'+''.join(sections)
    with (args.output/'index.html').open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(page)
    print(json.dumps({'summary': summary, 'audit_sha256': sha(args.output/'audit.json'),
                      'new_model_requests': 0, 'new_game_actions': 0, 'GPU_jobs': 0}), flush=True)


if __name__ == '__main__':
    main()
