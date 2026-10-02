"""Detector evaluation on the held-out evaluation partition, with the frozen trigger spec (Track 3).

Reads trigger_spec.json (chosen on development only) and never changes it. Reports the selected detector and the
references declared with the grid. Every error is retained: each false trigger and each missed positive
trajectory is listed with its trajectory, family and step. Run `python -m research.stagnation_supervision_v1.evaluate`
to regenerate evaluation_results.json; the tests check it is reproduced.
"""
import collections
import json
from pathlib import Path

from research.stagnation_supervision_v1 import fixtures as F, thresholds as S

VERSION = 'stagnation_supervision_v1_evaluation'
RESULTS = Path(__file__).with_name('evaluation_results.json')


def by_family(rows):
    out = collections.OrderedDict()
    for r in rows:
        f = out.setdefault(r['family'], {'positive': r['positive'], 'trajectories': 0, 'detected': 0,
                                         'with_false_intervention': 0, 'false_triggers': 0})
        f['trajectories'] += 1
        f['detected'] += bool(r['correct_triggers'])
        f['with_false_intervention'] += bool(r['false_triggers'])
        f['false_triggers'] += len(r['false_triggers'])
    return out


def errors(rows):
    out = []
    for r in rows:
        for i in r['false_triggers']:
            out.append({'kind': 'false_intervention', 'id': r['id'], 'family': r['family'], 'action_index': i})
        if r['positive'] and not r['correct_triggers']:
            out.append({'kind': 'missed_positive', 'id': r['id'], 'family': r['family'],
                        'first_stagnant': r['first_stagnant'], 'length': r['length']})
    return out


def report(generated, spec):
    if generated.get('partition') != 'evaluation':
        raise ValueError('this report is for the held-out evaluation partition')
    data = S.prepared(generated)
    out = {'version': VERSION, 'spec_development_fixtures_sha256': spec['development_fixtures_sha256'],
           'spec_params': spec['params'], 'evaluation_fixtures_sha256': F.digest('evaluation'),
           'cooldown_actions': spec['cooldown_actions'], 'detectors': {}}
    runs = {'selected': {'params': spec['params']}, **spec['references']}
    for name, ref in runs.items():
        metrics, rows = S.score(data, ref.get('params'), spec['cooldown_actions'], detail=True, period=ref.get('period'))
        out['detectors'][name] = {'definition': ref, 'metrics': metrics, 'by_family': by_family(rows),
                                  'errors': errors(rows), 'trajectories': rows}
    return out


if __name__ == '__main__':
    result = report(F.generate('evaluation'), S.load())
    RESULTS.write_text(json.dumps(result, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    for name, d in result['detectors'].items():
        print(name, json.dumps(d['metrics']))
