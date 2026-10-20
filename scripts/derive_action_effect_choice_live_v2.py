"""Derive a separate bounded format pilot from hash-pinned reviewed v1 sources."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace(text, before, after, count=None):
    actual = text.count(before)
    if not actual or (count is not None and actual != count):
        raise ValueError('derivation template differs: '+before)
    return text.replace(before, after)


def derive():
    pins = json.loads(Path(__file__).with_suffix('.parents.json').read_bytes())
    files = {}
    for name, pin in pins.items():
        raw = (ROOT/name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != pin: raise ValueError('parent changed: '+name)
        text = raw.decode().replace('action_effect_choice_live_v1', 'action_effect_choice_live_v2')
        text = text.replace('action_effect_choice_v1', 'action_effect_choice_v2')
        text = text.replace('action_effect_live_fixture', 'action_effect_pilot_fixture')
        text = text.replace('test_action_effect_live_', 'test_action_effect_pilot_')
        text = text.replace('ACTION_EFFECT_CHOICE_', 'ACTION_EFFECT_CHOICE_V2_')
        for label in ('worker', 'private_runtime', 'return_witness', 'live_review_lock', 'readonly_preflight',
                      'independent_content', 'independent_evaluation'):
            text = text.replace('action_effect_choice_'+label+'_v1', 'action_effect_choice_'+label+'_v2')
        text = text.replace('action-effect-choice-', 'action-effect-choice-v2-')
        leaf = Path(name).name
        if leaf == 'live_worker.py':
            text = replace(text, 'len(ids) > 33', 'len(ids) > 9', 1)
            text = replace(text, 'super().__init__(plan, 33, clock)', 'super().__init__(plan, 9, clock)', 1)
            text = replace(text, 'resets >= 16', 'resets >= 4', 1)
            text = replace(text, 'dispatches >= 68', 'dispatches >= 16', 1)
            text = replace(text, 'closes >= 16', 'closes >= 4', 1)
        elif leaf == 'live_runtime.py':
            for before, after in (("'generations': 33, 'counted_HTTP_requests': 33", "'generations': 9, 'counted_HTTP_requests': 9"),
                    ("'checkpoints': 8, 'policy_conditions': 16", "'checkpoints': 2, 'policy_conditions': 4"),
                    ("'policy_actions': 32, 'prefix_dispatches': 36, 'bootstrap_resets': 16, 'offline_engine_actions': 84",
                     "'policy_actions': 8, 'prefix_dispatches': 8, 'bootstrap_resets': 4, 'offline_engine_actions': 20"),
                    ("'local_scorecards': 16", "'local_scorecards': 4"), ("len(worker['conditions']) != 16", "len(worker['conditions']) != 4")):
                text = replace(text, before, after, 1)
        elif leaf == 'audit.py':
            for before, after in (("maximum_model_requests'), 33", "maximum_model_requests'), 9"),
                    ('resets != 16 or closes != 16 or prefix_dispatches != 36 or len(summaries) != 16 or len(rows) != 32',
                     'resets != 4 or closes != 4 or prefix_dispatches != 8 or len(summaries) != 4 or len(rows) != 8'),
                    ('new_dispatches <= 32','new_dispatches <= 8'), ('resets+dispatches > 84','resets+dispatches > 20'),
                    ('len(calls) > 33','len(calls) > 9'), ('scheduled_candidate_forecasts=64','scheduled_candidate_forecasts=16')):
                text = replace(text, before, after, 1)
            text = replace(text, "return dict(schema='action_effect_choice_independent_content_v2'",
                "coverage = dict(scheduled=8, reached=sum(r['observed'] for r in rows),\n"
                "                    valid=sum(r['observed'] and r['score']['valid'] for r in rows))\n"
                "    return dict(format_only=True, phase_coverage=coverage,\n"
                "        format_coverage_complete=coverage['reached']==coverage['valid']==8,\n"
                "        schema='action_effect_choice_independent_content_v2'", 1)
        elif leaf == 'live_evaluation.py':
            text = replace(text, "'lifecycle_certified': True, 'outcome_claim_permitted': True", "'lifecycle_certified': True, 'outcome_claim_permitted': False", 1)
            text = replace(text, 'Eight correlated exposed checkpoints across six games; paired descriptive results only. Provider lifecycle and independent content replay both passed.',
                'Four exposed compatibility conditions; phase-specific format coverage only. No arm advantage, forecast accuracy or gameplay advancement claim.', 1)
        elif leaf == 'live_package.py':
            text = replace(text, 'def creation_title(kernel_id):', '''def reviewed_scope_files(scope_review):
    scope_review = Path(scope_review)
    files = {p.relative_to(scope_review).as_posix(): p.read_bytes()
             for p in scope_review.rglob('*') if p.is_file()}
    if not files or any(p.is_symlink() for p in scope_review.rglob('*')):
        raise ValueError('private scoped-use evidence missing/unsafe')
    name = 'model-dataset-inventory.json'
    if name not in files:
        raise ValueError('root model inventory required by read-only preflight')
    rows = json.loads(files[name]).get('files')
    if (type(rows) is not list or len(rows) != 20 or
            any(type(row) is not dict or type(row.get('path')) is not str or not row['path'] or
                type(row.get('bytes')) is not int or row['bytes'] <= 0 for row in rows) or
            len({row['path'] for row in rows}) != 20):
        raise ValueError('complete unique 20-file model inventory required')
    return files


def creation_title(kernel_id):''', 1)
            text = replace(text, "scope_files = {p.relative_to(scope_review).as_posix(): p.read_bytes() for p in scope_review.rglob('*') if p.is_file()}",
                'scope_files = reviewed_scope_files(scope_review)', 1)
            text = replace(text, 'Private paired candidate-forecast and two-action diagnostic.', 'Private phase-specific format-only pilot: four conditions, at most nine generations.', 1)
            text = replace(text, "'research/action_effect_choice_live_v2/audit.py']", "'research/action_effect_choice_live_v2/audit.py', 'research/action_effect_choice_v2/interface.py']", 1)
        elif leaf == 'rehearse_action_effect_choice_live_v1.py':
            text = replace(text, "expected_replay['bootstrap'] < 16", "expected_replay['bootstrap'] < 4", 1)
        elif leaf == 'action_effect_live_fixture.py':
            text = replace(text, 'derive(values)', 'derive(values)', 2)  # preserve the pinned full inventory before slicing
            text = replace(text, 'return values', 'return values[:2]', 1)
            text = replace(text, "write_new(inputs/'candidate-pairs.json', derive(values))",
                "from research.action_effect_choice_v2.interface import candidates, VARIANTS\n"
                "    write_new(inputs/'candidate-pairs.json', [dict(checkpoint_id=cp['checkpoint_id'],\n"
                "        candidates=candidates(cp,i), order=list(VARIANTS if i%2==0 else reversed(VARIANTS))) for i,cp in enumerate(values)])", 1)
        elif leaf.startswith('test_action_effect_live_'):
            # Preserve adversarial tests; update only the frozen pilot counts.
            text = re.sub(r'\b33\b', '9', text).replace('_33_', '_9_')
            for before, after in (('(16, 68, 16)','(4, 16, 4)'),('(9, 36, 32, 84, 16)','(9, 8, 8, 20, 4)'),
                                  ("['conditions']), 16", "['conditions']), 4"),
                                  ("['issued'], 17", "['issued'], 5"), ("['dispatch_attempts'], 36", "['dispatch_attempts'], 8"),
                                  ("['closed_scorecards'], 16", "['closed_scorecards'], 4"),
                                  ("['generations'], 17", "['generations'], 5"),
                                  ("['scheduled_candidate_forecasts'], 64", "['scheduled_candidate_forecasts'], 16"),
                                  ("result['decisions']), 16", "result['decisions']), 4")):
                text = text.replace(before, after)
            if leaf.endswith('_worker.py'):
                text = replace(text, 'from research.action_effect_choice_v2.preparation import derive',
                    'from research.action_effect_choice_v2.interface import candidates', 1)
                text = replace(text, 'json.dumps(derive(checkpoints()))',
                    "json.dumps([dict(checkpoint_id=cp['checkpoint_id'],candidates=candidates(cp,i)) for i,cp in enumerate(checkpoints())])", 1)
        target = name.replace('action_effect_choice_live_v1', 'action_effect_choice_live_v2')
        target = target.replace('action_effect_live_fixture', 'action_effect_pilot_fixture').replace('test_action_effect_live_', 'test_action_effect_pilot_')
        target = target.replace('scripts/build_action_effect_choice_live_v1.py','scripts/build_action_effect_choice_live_v2.py')
        target = target.replace('scripts/rehearse_action_effect_choice_live_v1.py','scripts/rehearse_action_effect_choice_live_v2.py')
        files[target] = text
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--check', action='store_true'); args=parser.parse_args()
    files=derive()
    for name,text in files.items():
        path=ROOT/name
        if args.check:
            if path.read_bytes()!=text.encode(): raise ValueError('derived file changed: '+name)
        else:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(text.encode())
    print(json.dumps({'matched':True,'derived_files':len(files),'GPU_jobs':0}))


if __name__=='__main__':main()
