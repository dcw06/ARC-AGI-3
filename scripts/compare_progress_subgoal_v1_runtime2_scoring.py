"""Independent-scoring reproduction check (CPU only, read-only; scripted answers, never model results).

1. Re-evaluates a successor rehearsal's retained evidence with scripts/evaluate_progress_subgoal_v1_runtime2.py (its
   harness-declared protocol from the rehearsal folder).
2. Recomputes the same analysis offline, without any HTTP or retained evidence: each scheduled request, in the frozen
   call order, is answered by a fresh instance of the scripted rule the stub used
   (research.progress_subgoal_v1.fake_server.ScriptedAnswers, or the keys for `oracle`), then scored with the
   unchanged score_call rule and analysed with the unchanged score.analyze.
3. Optionally (--old-evidence), evaluates an old-runtime connected rehearsal folder (review r4's runner, same scripted
   rule) with the old evaluator (research/progress_subgoal_v1/evaluate_run.py) and compares its analysis and every
   retained answer with the successor's.

Usage: python scripts/compare_progress_subgoal_v1_runtime2_scoring.py --rehearsal DIR [--policy scripted|oracle]
       [--old-evidence DIR --old-rehearsal-seconds N] [--out FILE]
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def offline_analysis(policy):
    from research.action_effect_history_v1.service import request_hash
    from research.progress_subgoal_v1.evaluate_run import score_call
    from research.progress_subgoal_v1.fake_server import TRUNCATED, ScriptedAnswers
    from research.progress_subgoal_v1.score import analyze
    from research.progress_subgoal_v1_runtime2 import questionnaire as QN
    frozen, _, rows = QN.scheduled(ROOT)
    probes = {p['probe_id']: p for p in frozen['probes']}
    answers = ScriptedAnswers()
    passes, contents = {'pass_1': {}, 'pass_2': {}}, []
    for _, _, pass_id, probe_id, request in rows:
        probe = probes[probe_id]
        content = json.dumps({'answer': probe['key']}) if policy == 'oracle' else answers(json.loads(json.dumps(request)))
        finish = 'stop'
        if content.startswith(TRUNCATED):
            content, finish = content[len(TRUNCATED):], 'length'
        contents.append(content)
        passes[pass_id][probe_id] = score_call(probe, {'finish_reason': finish, 'response': content})
    return analyze(frozen['probes'], {k: v for k, v in passes.items() if v}, 'withheld'), contents, \
        [request_hash(r[4]) for r in rows]


def retained_contents(evidence):
    calls = sorted((Path(evidence) / 'questionnaire/calls').iterdir())
    out = []
    for path in calls:
        record = json.loads(path.read_bytes())
        out.append(json.loads(record['response'])['choices'][0]['message']['content']
                   if record.get('status') == 'answered' else None)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rehearsal', type=Path, required=True, help='a successor rehearsal folder')
    parser.add_argument('--policy', choices=('scripted', 'oracle'), default='scripted')
    parser.add_argument('--old-evidence', type=Path)
    parser.add_argument('--old-rehearsal-seconds', type=int, default=900)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    from scripts.evaluate_progress_subgoal_v1_runtime2 import evaluate_output
    declared = json.loads((args.rehearsal / 'declared-protocol.json').read_bytes())
    value = evaluate_output(args.rehearsal / 'evidence', mode='rehearsal', root=ROOT, protocol=declared)
    expected, contents, _ = offline_analysis(args.policy)
    retained = retained_contents(args.rehearsal / 'evidence')
    record = {'schema': 'progress_subgoal_v1_runtime2_scoring_reproduction_v1',
              'evidence_class': 'scripted_cpu_rehearsal', 'gpu_used': False, 'model_calls': 0,
              'rehearsal': str(args.rehearsal), 'policy': args.policy,
              'successor_technically_complete': value['technically_complete'],
              'successor_gate': value['gate'],
              'retained_answers_equal_offline_scripted_answers': retained == contents,
              'successor_analysis_equals_offline_recomputation': value['analysis'] == expected,
              'note': 'scripted answers; labels and rates here are not results'}
    if args.old_evidence:
        from research.progress_subgoal_v1.evaluate_run import evaluate_output as old_evaluate
        from research.progress_subgoal_v1.evidence import load_verified  # the old runner's verified loader
        old = old_evaluate(args.old_evidence, mode='rehearsal', rehearsal_seconds=args.old_rehearsal_seconds)
        old_calls = load_verified(args.old_evidence / 'worker/run')['calls']
        old_contents = [c.get('response') if c.get('status') == 'answered' else None for c in old_calls]
        record.update(old_evidence=str(args.old_evidence), old_technically_complete=old['technically_complete'],
                      old_gate=old['gate'], old_retained_answers_equal_successor=old_contents == retained,
                      old_analysis_equals_successor_analysis=old['analysis'] == value['analysis'])
    checks = [record['successor_technically_complete'], record['retained_answers_equal_offline_scripted_answers'],
              record['successor_analysis_equals_offline_recomputation']]
    if args.old_evidence:
        checks += [record['old_retained_answers_equal_successor'], record['old_analysis_equals_successor_analysis']]
    record['passed'] = all(checks)
    if args.out:
        args.out.write_bytes((json.dumps(record, sort_keys=True, indent=1) + '\n').encode())
    print(json.dumps(record, indent=1))
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
