"""Synthetic M1/M2 diagnostics. Goals and dynamics remain evaluator-owned."""
import argparse
import html
import json
import hashlib
from pathlib import Path
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.ls20_discovery_mac import EvidenceMemory
from research.ls20_discovery_mac.memory import normalize_observation, digest
from research.ls20_discovery_mac.models import predict, plan, fit, state_key, current
from research.ls20_discovery_mac.object_effects import transition_effects
from research.ls20_discovery_mac.prospective import execute, verify


def obs(p, width=5, color=2):
    return dict(grid=[[color if x == p else 0 for x in range(width)]], state='NOT_FINISHED',
                levels_completed=0, legal_actions=[1, 2])


def action(n):
    return dict(action_id=n, action_data={})


def clone(snapshot):
    m = EvidenceMemory(snapshot['episode_id'], snapshot['initial'])
    for t in snapshot['transitions']:
        m.append(t['action'], t['outcome'], elapsed_seconds=t['elapsed_seconds'])
    return m


def run(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    started = perf_counter()
    # Fixed evaluator environment: action 1 toggles 0/1; action 2 toggles 0/2.
    # These rules never enter the predictor or planner. Training is supplied, not exploration.
    def response(position, n):
        return (1 if position == 0 else 0) if n == 1 else (2 if position == 0 else 0)
    m, position = EvidenceMemory('branching-toy', obs(0)), 0
    for n in [1, 1, 2, 2] * 2:
        position = response(position, n)
        execute(m, action(n), lambda a, p=position: dict(status='acknowledged', post=obs(p)), output/'training')
    frozen = m.snapshot()
    objective = dict(kind='supplied_diagnostic_goal', state_key=state_key(normalize_observation(obs(2))))
    rows = []
    for mode in ('reactive', 'prediction_only', 'bounded_planning'):
        memory, position, correct, covered, expansions = clone(frozen), 0, 0, 0, 0
        moves, success = 0, False
        for _ in range(4):
            # Same lowest-ID reactive policy in the first two arms; prediction-only
            # deliberately does not change policy. Planner uses the same frozen edges.
            p = plan(frozen, objective) if moves == 0 and mode == 'bounded_planning' else None
            n = p['actions'][0]['action_id'] if p and p['actions'] else 1
            if p:
                expansions += p['expansions']
            position = response(position, n)
            result = execute(memory, action(n), lambda a, pos=position: dict(status='acknowledged', post=obs(pos)),
                             output/mode, planned=p)
            covered += result['scored']; correct += result['correct']; moves += 1
            if position == 2:
                success = True
                break
        rows.append(dict(mode=mode, moves=moves, success=success, covered=covered,
                         correct=correct, expansions=expansions, verification=verify(output/mode)))
    # Same prediction algorithm, three input history lengths at the same visible state.
    short = EvidenceMemory('short-history', obs(0))
    for t in frozen['transitions'][-2:]:
        short.append(t['action'], t['outcome'])
    minimal = EvidenceMemory('current-only', obs(0))
    retention = [dict(view=name, status=predict(mem.snapshot(), action(2))['status'],
                      transition_count=len(mem.snapshot()['transitions']),
                      snapshot_bytes=len(json.dumps(mem.snapshot()).encode()))
                 for name, mem in [('current_only', minimal), ('last_two', short), ('persistent', m)]]
    # Deliberate dynamics counterexample: the formerly supported action now has no effect.
    contradicted = clone(frozen)
    p = plan(contradicted.snapshot(), objective)
    failure = execute(contradicted, action(2), lambda a: dict(status='acknowledged', post=obs(0)),
                      output/'counterexample', planned=p)
    revised = plan(contradicted.snapshot(), objective)
    assert failure['plan_invalidated'] and revised['status'] == 'request_probe'
    # Prospective displacement generalization: two supports, then new position,
    # followed by a blocker that falsifies the constant-displacement candidate.
    moving = EvidenceMemory('translation-toy', obs(0, 8))
    movement = []
    for position in (1, 2, 3, 3):
        movement.append(execute(moving, action(1), lambda a, p=position: dict(status='acknowledged', post=obs(p, 8)), output/'translation'))
    assert any(s['scored'] and s['correct'] for s in movement[2]['object_scores'])
    assert any(s['scored'] and not s['correct'] for s in movement[3]['object_scores'])
    translation_retired = sum(x['status'] == 'contradicted' for x in fit(moving.snapshot())['translation_candidates'])
    verification = {name: verify(output/name) for name in ('training', 'counterexample', 'translation')}
    payload = dict(version='mac_m1_m2_diagnostic_v1', training_attempts=8, comparison=rows,
        memory_comparison=retention, counterexample=failure, revised_plan=revised,
        translation_results=movement, contradicted_translation_candidates=translation_retired,
        verification=verification, elapsed_seconds=perf_counter()-started,
        model_calls=0, gpu_jobs=0, real_game_actions=0,
        assistance=['scripted training actions', 'supplied diagnostic goal', 'exact visible-state graph'],
        limitations='Constructed demonstration, not autonomous exploration, held-out benchmark or game solving.')
    payload['total_synthetic_dispatches'] = 8 + sum(r['moves'] for r in rows) + 1 + len(movement)
    source_root = Path(__file__).resolve().parents[1]
    files = list((source_root/'research/ls20_discovery_mac').glob('*.py')) + [
        source_root/'research/action_effect_v1/records.py', Path(__file__).resolve()]
    payload['source_sha256'] = {str(p.relative_to(source_root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted(files)}
    (output/'summary.json').write_text(json.dumps(payload, indent=2)+'\n')
    (output/'object-effects.json').write_text(json.dumps(transition_effects(moving.snapshot()), indent=2)+'\n')
    (output/'models.json').write_text(json.dumps(fit(moving.snapshot()), indent=2)+'\n')
    table = ''.join('<tr>'+''.join(f'<td>{html.escape(str(row[k]))}</td>' for k in ('mode','moves','success','covered','correct','expansions'))+'</tr>' for row in rows)
    (output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Mac M1/M2 diagnostic</title><style>body{font:16px system-ui;max-width:1000px;margin:40px auto;color:#17324d}td,th{padding:12px;border-bottom:1px solid #ccd}pre{white-space:pre-wrap;background:#f4f6fa;padding:20px}</style><h1>M1/M2 synthetic diagnostic</h1><p>Scripted training, supplied goal. No real game, GPU or model calls.</p><table><tr><th>Policy</th><th>Moves</th><th>Goal reached</th><th>Covered</th><th>Correct</th><th>Expansions</th></tr>'+table+'</table><h2>Counterexample</h2><p>The supported edge fails. Its plan is invalidated; replanning requests a probe.</p><details><summary>Full evidence summary</summary><pre>'+html.escape(json.dumps(payload,indent=2))+'</pre></details>')
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    run(parser.parse_args().output)
