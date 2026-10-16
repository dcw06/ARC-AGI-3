"""CPU-only upstream-decoder reproductions. No model, weights, download or launch."""
import argparse
import ast
import hashlib
import io
import json
import logging
from pathlib import Path
import re
import subprocess
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.molmopoint_identification_v1.adapter import decode_generation
from research.molmopoint_identification_v1.scoring import score_target
from scripts.serve_manual_strategy_worksheet import canonical, private_directory

BASELINE = '52273442461846260868cf726988e1aeb0aadcbe'
BASELINE_ADAPTER_SHA256 = '2878d4ccb2efeca860f47d4448091a20bcaa36232912252700bf740c9ec0ee77'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream-modeling',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--baseline-adapter',type=Path,help='optional retained git-show bytes for cross-OS worktrees')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('preserve previous verification')
    raw = args.upstream_modeling.read_bytes()
    pin = json.loads((ROOT/'research/molmopoint_identification_v1/model_pin.json').read_bytes())
    expected = next(r['reviewed_sha256'] for r in pin['files'] if r['name'] == 'modeling_molmo_point.py')
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('upstream decoder hash differs')
    # Only inspected pure decoder functions execute, never the upstream model module.
    import numpy as np
    tree = ast.parse(raw)
    nodes = [n for n in tree.body if isinstance(n,ast.FunctionDef)
             and n.name in ('get_subpatch_ids','extract_image_points')]
    if len(nodes) != 2:
        raise ValueError('pinned decoder functions missing')
    env = {'np':np,'logger':logging.getLogger('synthetic-decoder-check'),
           'EXTRACT_POINT_TRIPLE':re.compile(r'<POINT_(\d+)> ?<POINT_(\d+)> ?<POINT_(\d+)> ?([0-9]+)')}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'hash-verified-upstream-decoder','exec'),env)
    old_raw = (args.baseline_adapter.read_bytes() if args.baseline_adapter is not None else
               subprocess.run(['git','show',BASELINE+':research/molmopoint_identification_v1/adapter.py'],
                              cwd=ROOT,capture_output=True,check=True).stdout)
    if hashlib.sha256(old_raw).hexdigest() != BASELINE_ADAPTER_SHA256:
        raise ValueError('historical adapter differs from exact 5227344 bytes')
    old = types.ModuleType('historical_adapter_5227344')
    old.__file__ = str(ROOT/'research/molmopoint_identification_v1/adapter.py')
    exec(compile(old_raw,'adapter-at-5227344','exec'),old.__dict__)
    pool = np.arange(16).reshape(4,4)
    mapping = np.arange(16).reshape(4,4)
    metadata = {'token_pooling':pool,'subpatch_mapping':[mapping],'image_sizes':[(448,448)]}
    complete, sentinel = '<POINT_0><POINT_5><POINT_9>0','<POINT_4>'
    cases = [
        ('complete',complete,True,True),
        ('complete_then_patch_fragment',complete+'<POINT_1>',False,False),
        ('complete_then_two_token_fragment',complete+'<POINT_1><POINT_5>',False,False),
        ('complete_then_missing_object_id',complete+'<POINT_1><POINT_5><POINT_9>',False,False),
        ('fragment_only','<POINT_0>',False,False),
        ('leading_fragment','<POINT_1>'+complete,False,False),
        ('sentinel_only',sentinel,True,False),
        ('complete_then_sentinel',complete+sentinel,True,True),
        ('point_after_sentinel',sentinel+complete,False,False),
        ('duplicate_sentinel',sentinel+sentinel,False,False),
    ]
    ref = {'case_id':'synthetic','regions':[{'id':'target','target_points':[[2,2]]}]}
    results = {}
    for label, decoder in [('baseline',old.decode_generation),('fixed',decode_generation)]:
        rows = []
        for name,text,accepted,hit in cases:
            native_calls = []
            def native(text,pool,mappings,sizes):
                native_calls.append(True)
                return env['extract_image_points'](text,pool,mappings,True,'3x3',sizes)
            model = types.SimpleNamespace(config=types.SimpleNamespace(model_type='molmo_point',
                no_more_points_class=True,patch_location='3x3'),extract_image_points=native)
            processor = types.SimpleNamespace(post_process_image_text_to_text=lambda *a,**k:[text])
            row = {'case':name,'expected_accepted':accepted,'expected_target_hit':hit}
            try:
                decoded = decoder(model,processor,[1],metadata,(448,448),finish_reason='stop')
                scored = score_target(ref,'target',decoded['points'])
                row.update(accepted=True,target_hit=scored['target_hit'],decoded_points=len(decoded['points']))
            except ValueError as error:
                row.update(accepted=False,target_hit=False,error=str(error))
            row['native_decoder_calls'] = len(native_calls)
            rows.append(row)
        results[label] = rows
    observed = {r['case']:r for r in results['baseline']}
    reproduced = (observed['complete']['target_hit'] is True
                  and observed['complete_then_patch_fragment']['target_hit'] is True
                  and observed['fragment_only']['accepted'] is True
                  and observed['fragment_only']['decoded_points'] == 0)
    fixed_passes = all(r['accepted'] == r['expected_accepted'] and r['target_hit'] == r['expected_target_hit']
                       and (r['accepted'] or r['native_decoder_calls'] == 0) for r in results['fixed'])
    # Run the retained regression methods against the exact historical adapter too.
    from tests import test_molmopoint_point_sequences as regression
    current = regression.decode_generation
    regression.decode_generation = old.decode_generation
    log = io.StringIO()
    try:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(regression.PointSequenceRegressionTests)
        baseline_tests = unittest.TextTestRunner(stream=log).run(suite)
    finally:
        regression.decode_generation = current
    record = {'baseline_commit':BASELINE,'baseline_adapter_sha256':hashlib.sha256(old_raw).hexdigest(),
        'upstream_decoder_sha256':expected,'baseline_bug_reproduced':reproduced,
        'fixed_cases_passed':fixed_passes,'results':results,
        'baseline_regression_methods_run':baseline_tests.testsRun,
        'baseline_failed_assertions_including_subtests':len(baseline_tests.failures),
        'baseline_regression_errors':len(baseline_tests.errors),
        'model_objects_loaded':0,'model_generations':0,'GPU_calls':0,'provider_calls':0,
        'fixture':'synthetic arrays and tokens, not model outputs',
        'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in [
            'research/molmopoint_identification_v1/adapter.py','tests/test_molmopoint_point_sequences.py',
            'scripts/check_molmopoint_point_sequences.py']}}
    private_directory(args.output)
    (args.output/'verification.json').write_bytes(canonical(record))
    (args.output/'baseline-regression-tests.log').write_text(log.getvalue())
    print(json.dumps({k:v for k,v in record.items() if k not in ('results','source_sha256')},indent=2))
    return 0 if reproduced and fixed_passes and baseline_tests.failures and not baseline_tests.errors else 1


if __name__ == '__main__':
    sys.exit(main())
