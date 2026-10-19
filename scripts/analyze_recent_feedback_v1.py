"""Apply prospective descriptive metrics only after exact-input independent validation."""
import argparse
import json
from pathlib import Path
import sys
SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.live_io import sha, write_new
from research.recent_feedback_v1.analysis import episode_metrics
from research.recent_feedback_v1.live_contract import check_cases, protocol
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'inputs', 'review-lock', 'evaluation', 'lifecycle', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args()
    OUTPUT = args.run
    evaluated = json.loads((args.evaluation).read_bytes())
    lifecycle = json.loads((args.lifecycle).read_bytes())
    evidence = digest({p.relative_to(OUTPUT).as_posix(): sha(p) for p in sorted(OUTPUT.rglob('*')) if p.is_file()})
    if (evaluated['technically_complete'] is not True or lifecycle['passed'] is not True or
            evaluated['run_evidence_sha256'] != evidence or
            evaluated['review_lock_sha256'] != sha(args.review_lock) or
            evaluated['input_manifest_sha256'] != sha(args.inputs/'manifest.json')):
        raise ValueError('independent evaluation missing, stale or bound to different inputs')
    cases = check_cases(json.loads((args.inputs/'cases.json').read_bytes())['cases'])
    names = {c['case_id']: c['game_id'].split('-')[0] for c in cases}
    episodes = []
    for row in evaluated['episodes']:
        path = OUTPUT/(row['case_id']+'-'+row['arm']+'.jsonl')
        events = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
        metrics = episode_metrics(events)
        if metrics['dispatched_actions'] != row['dispatches'] or metrics['decisions'] != row['policy_calls']:
            raise ValueError('descriptive counters differ from independent evaluator')
        prediction = metrics['prediction']
        if (prediction['asserted'] != row['known_visible_change_predictions'] or
                prediction['correct_assertions'] != row['correct_visible_change_predictions']):
            raise ValueError('prediction counters differ')
        episodes.append(dict(row, game=names[row['case_id']], metrics=metrics))
    arms = {}
    for arm in ('recent_raw', 'recent_summary'):
        rows = [e for e in episodes if e['arm'] == arm]
        arms[arm] = {'first_level_completions': sum(e['first_level_complete'] for e in rows),
            'games': len(rows), 'policy_calls': sum(e['policy_calls'] for e in rows),
            'dispatches': sum(e['dispatches'] for e in rows),
            'invalid_answers': sum(e['stop_reason'] == 'invalid_answer' for e in rows),
            'known_predictions': sum(e['known_visible_change_predictions'] for e in rows),
            'correct_known_predictions': sum(e['correct_visible_change_predictions'] for e in rows),
            'unknown_predictions': sum(e['unknown_visible_change_predictions'] for e in rows),
            'distinct_full_actions_sum': sum(e['metrics']['distinct_full_actions'] for e in rows),
            'visibly_changed_steps': sum(e['metrics']['visibly_changed_steps'] for e in rows),
            'consecutive_repeat': {k: sum(e['metrics']['consecutive_repeat'][k] for e in rows)
                                   for k in ('eligible', 'repeated', 'unexecuted')},
            'repeat_after_unchanged': {stratum: {k: sum(e['metrics']['repeat_after_unchanged'][stratum][k] for e in rows)
                      for k in ('eligible', 'repeated', 'unexecuted')}
                      for stratum in ('all', 'same_grid', 'different_grid')}}
    transport = [json.loads(line) for line in (OUTPUT/'transport.jsonl').read_text(encoding='utf-8').splitlines()]
    resource_rows = []
    for i, event in enumerate(transport):
        if event['kind'] != 'HTTP_request': continue
        response = transport[i+2]
        if response['kind'] != 'HTTP_response' or response['id'] != event['id']:
            raise ValueError('retained transport order differs')
        usage = json.loads(response['raw'])['usage']
        resource_rows.append({'arm': event['id'].split('/')[1] if '/' in event['id'] else 'canary', **usage})
    resources = {arm: {k: sum(e[k] for e in resource_rows if e['arm'] == arm)
                       for k in ('prompt_tokens', 'completion_tokens', 'total_tokens')}
                 for arm in ('recent_raw', 'recent_summary', 'canary')}
    current = digest({p.relative_to(OUTPUT).as_posix(): sha(p) for p in sorted(OUTPUT.rglob('*')) if p.is_file()})
    if evidence != current: raise ValueError('evidence changed during aggregation')
    summary = {'schema': 'recent_feedback_completed_aggregate_v1', 'technically_complete': True,
        'review_lock_sha256': evaluated['review_lock_sha256'], 'run_evidence_sha256': current,
        'independent_evaluation_sha256': sha(args.evaluation),
        'frozen_protocol_sha256': sha(SOURCE/'research/recent_feedback_v1/live_protocol.json'),
        'analysis_sha256': sha(SOURCE/'research/recent_feedback_v1/analysis.py'),
        'aggregation_producer_sha256': sha(Path(__file__)),
        'evaluation_lifecycle_sha256': sha(args.lifecycle),
        'metric_definitions': protocol()['secondary'], 'arms': arms, 'episodes': episodes, 'tokens': resources,
        'qualification': 'Six exposed starts, one pair per game, 24 actions. Both arms receive reviewed initial geometry. Descriptive interface comparison, not proof of general gameplay, object discovery or memory benefit.'}
    write_new(args.output, summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ('episodes', 'metric_definitions')}), flush=True)
