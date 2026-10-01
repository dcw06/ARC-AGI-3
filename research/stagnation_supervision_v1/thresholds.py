"""Threshold selection on development fixtures only, and the frozen trigger specification (Track 3).

The objective was fixed before selection ran:
  1. constraint: at most MAX_FALSE_INTERVENTION_RATE of development trajectories receive any trigger at a
     productive step (a false intervention);
  2. maximise recall: the fraction of positive trajectories with at least one trigger at a stagnant step;
  3. then the fewest false-intervention trajectories, then higher trigger precision, then lower mean latency
     (actions from the first stagnant step to the first correct trigger), then fewer enabled signals, then
     larger (more conservative) thresholds.
The cooldown is a policy constant, not tuned. The unit of analysis is the trajectory: steps of one trajectory are
never treated as independent samples.

`select` refuses any fixture outside the development partition. Run `python -m
research.stagnation_supervision_v1.thresholds` to regenerate trigger_spec.json; the tests check it is reproduced.
"""
import itertools
import json
from pathlib import Path

from research.stagnation_supervision_v1 import detector as D, fixtures as F
from research.transition_evidence_v1 import transition as T

VERSION = 'stagnation_supervision_v1_trigger_spec'
SPEC = Path(__file__).with_name('trigger_spec.json')
COOLDOWN_ACTIONS = 6
MAX_FALSE_INTERVENTION_RATE = 0.10
GRID = {
    'repeat_no_effect': (None, 2, 3, 4, 5),
    'state_action_recurrence': (None, 2, 3, 4),
    'tiny_effect_repeat': (None, 4, 6, 8, 10),
    'novelty_stall': (None, (6, 0), (8, 0), (8, 1), (10, 1), (12, 2)),
    'prediction_failures': (None, 3, 4, 6),
    'no_progress_horizon': (None, 10, 15, 20),
}
NONE = {name: None for name in GRID}
# Declared with the grid, before any evaluation run; reported beside the selected detector, never selected from.
REFERENCES = {
    'repeat_no_effect_only_k3': {'params': {**NONE, 'repeat_no_effect': 3}},
    'no_progress_horizon_only_10': {'params': {**NONE, 'no_progress_horizon': 10}},
    'periodic_every_6': {'period': 6},
}
OBJECTIVE = ('constraint: false-intervention trajectory rate <= 0.10 on development; maximise recall; then fewest '
             'false-intervention trajectories, highest precision, lowest mean latency, fewest enabled signals, '
             'largest thresholds; no_progress_horizon counts observed transitions')


def prepared(generated):
    """[(fixture id, evaluator-only truth, per-step statistics)]; the detector sees only raws and predictions."""
    out = []
    for fixture in generated['fixtures']:
        records = T.history(fixture['raws'])
        out.append((fixture['id'], generated['evaluator_only'][fixture['id']],
                    D.statistics(records, fixture['predictions'])))
    return out


def periodic(step_stats, period):
    """A fixed schedule: a trigger after every `period`-th action, whatever the evidence."""
    return [{'action_index': s['action_index'], 'signals': [{'signal': 'periodic', 'evidence': []}],
             'trigger': (s['action_index'] + 1) % period == 0} for s in step_stats]


def score(prepared_fixtures, params=None, cooldown=COOLDOWN_ACTIONS, detail=False, period=None):
    """Trajectory-level metrics. A trigger after step t is correct when step t is labelled stagnant."""
    rows = []
    for fid, truth, stats in prepared_fixtures:
        decisions = periodic(stats, period) if period else D.triggers(stats, params, cooldown)
        labels = truth['labels']
        fired = [d for d in decisions if d['trigger']]
        correct = [d['action_index'] for d in fired if labels[d['action_index']] == F.STAGNANT]
        false = [d['action_index'] for d in fired if labels[d['action_index']] == F.PRODUCTIVE]
        stagnant = [i for i, label in enumerate(labels) if label == F.STAGNANT]
        rows.append({'id': fid, 'family': truth['family'], 'positive': truth['positive'], 'length': len(labels),
                     'first_stagnant': stagnant[0] if stagnant else None, 'triggers': [d['action_index'] for d in fired],
                     'correct_triggers': correct, 'false_triggers': false,
                     'latency': correct[0] - stagnant[0] if correct and stagnant else None,
                     'signals': sorted({s['signal'] for d in fired for s in d['signals']})})
    positives = [r for r in rows if r['positive']]
    all_triggers = sum(len(r['triggers']) for r in rows)
    correct = sum(len(r['correct_triggers']) for r in rows)
    latencies = [r['latency'] for r in rows if r['latency'] is not None]
    metrics = {
        'trajectories': len(rows), 'positive_trajectories': len(positives),
        'hard_negative_trajectories': len(rows) - len(positives),
        'detected_positive_trajectories': sum(bool(r['correct_triggers']) for r in positives),
        'recall': sum(bool(r['correct_triggers']) for r in positives) / len(positives) if positives else None,
        'triggers': all_triggers, 'correct_triggers': correct, 'false_triggers': all_triggers - correct,
        'precision': correct / all_triggers if all_triggers else None,
        'false_intervention_trajectories': sum(bool(r['false_triggers']) for r in rows),
        'false_intervention_rate': sum(bool(r['false_triggers']) for r in rows) / len(rows),
        'hard_negatives_with_false_intervention': sum(bool(r['false_triggers']) for r in rows if not r['positive']),
        'premature_triggers_in_positive_trajectories': sum(len(r['false_triggers']) for r in positives),
        'mean_latency_actions': sum(latencies) / len(latencies) if latencies else None,
    }
    return (metrics, rows) if detail else metrics


def candidates():
    names = list(GRID)
    for values in itertools.product(*(GRID[n] for n in names)):
        yield {n: (list(v) if isinstance(v, tuple) else v) for n, v in zip(names, values)}


def _rank(params, m):
    enabled = [v for v in params.values() if v is not None]
    size = sum(v if isinstance(v, int) else v[0] - v[1] for v in enabled)
    return (-(m['recall'] or 0), m['false_intervention_trajectories'], -(m['precision'] or 0),
            m['mean_latency_actions'] if m['mean_latency_actions'] is not None else float('inf'), len(enabled), -size)


def select(generated):
    if generated.get('partition') != 'development' or any(f['partition'] != 'development' for f in generated['fixtures']):
        raise ValueError('thresholds are chosen on the development partition only')
    data = prepared(generated)
    best, evaluated = None, 0
    for params in candidates():
        evaluated += 1
        m = score(data, params)
        if m['false_intervention_rate'] > MAX_FALSE_INTERVENTION_RATE:
            continue
        if best is None or _rank(params, m) < _rank(*best):
            best = (params, m)
    params, metrics = best
    return {'version': VERSION, 'detector': D.VERSION, 'selected_on': 'development partition only',
            'development_fixtures_sha256': F.digest('development'), 'objective': OBJECTIVE,
            'grid': {k: [list(v) if isinstance(v, tuple) else v for v in vals] for k, vals in GRID.items()},
            'candidates_evaluated': evaluated, 'references': REFERENCES, 'cooldown_actions': COOLDOWN_ACTIONS,
            'tiny_cells': D.TINY_CELLS,
            'params': params, 'development_metrics': metrics}


def load():
    return json.loads(SPEC.read_text(encoding='utf-8'))


def encode(spec):
    return json.dumps(spec, indent=1, sort_keys=True) + '\n'


if __name__ == '__main__':
    spec = select(F.generate('development'))
    SPEC.write_text(encode(spec), encoding='utf-8')
    print(json.dumps({'params': spec['params'], 'development_metrics': spec['development_metrics']}, indent=1))
