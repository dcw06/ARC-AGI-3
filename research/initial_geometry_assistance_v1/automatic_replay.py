"""Reproduce the retained automatic arm from evidence, never from trust flags.

No inference: replay native MolmoPoint tokens with the pinned processor/decoder,
verify saved deployment and completion, then project retained SAM logits using
the frozen predicted-quality selection. The legacy comparison bytes are output
only AFTER those checks. Raw evidence stays private.
"""
import hashlib
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path, PurePosixPath
import socket

from .geometry import canonical

QUALIFICATION = (
    'Exact-original short-prompt control. New verified native seeds only; original SAM policy,CPU FP32 and unchanged '
    'externally hash-bound owner reference. Invalid/empty frames remain in all-board denominators; no salvage, repair '
    'or reference-based mask selection. No new GPU or MolmoPoint inference during segmentation/replay.')
SOURCE_SCOPE = (
    'Runtime lifecycle, saved deployment source/settings and independent scientific replay pass for the restored '
    'exact-original short prompt. No generalization, gameplay or boundary competence claim follows.')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def confined(root, name):
    rel = PurePosixPath(name)
    require(not rel.is_absolute() and '..' not in rel.parts and '\\' not in name and ':' not in name,
            'unsafe evidence path')
    path = root.joinpath(*rel.parts)
    require(not path.is_symlink() and path.resolve().is_relative_to(root.resolve()), 'unsafe evidence member')
    return path


def verify_provenance(control, protocol):
    """Check an externally protocol-bound inventory before reading flags/data."""
    control = Path(control)
    manifest_path = Path(__file__).with_name('automatic_provenance.json')
    raw = manifest_path.read_bytes()
    require(sha(raw) == protocol['automatic_provenance_manifest_sha256'], 'automatic provenance manifest differs')
    manifest = json.loads(raw)
    require(manifest['schema'] == 'retained_automatic_evidence_provenance_v1', 'unknown automatic provenance schema')
    for name, pin in manifest['control_files_sha256'].items():
        require(sha(confined(control, name).read_bytes()) == pin, 'retained evidence differs: '+name)
    require(manifest['automatic_masks_sha256'] == protocol['automatic_masks_sha256'], 'automatic artifact pin differs')
    require(manifest['source_evaluation_sha256'] == protocol['automatic_source_evaluation_sha256'],
            'automatic source pin differs')
    return manifest


def replay_source(control, checkpoint, protocol):
    """Recompute deployment, lifecycle and native decode; ignore supplied flags."""
    from research.object_discovery_boundaries_v1 import deployment as D, operations as G
    from research.object_discovery_boundaries_v1.live_evaluation import evaluate, validate_completion
    collection = control/'gpu-attempt1-terminal-collection-r1'
    package = control/'gpu-live-review-r1'
    manifest_raw = (collection/'collection-manifest.json').read_bytes()
    for name, pin in json.loads(manifest_raw).items():
        require(sha(confined(collection, name).read_bytes()) == pin, 'collected artifact differs: '+name)
    record = G.load(collection/'collection.json')
    require(record['provider_status'] == 'COMPLETE' and not record.get('collection_error_type'), 'incomplete collection')
    snapshot = G.load(collection/'saved-package-snapshot.json')
    saved_book = json.loads(snapshot['source'])
    # Re-run the actual saved-source/settings/authority check, not its recorded yes/no result.
    G.validate_saved(snapshot, saved_book, package, D.authority_from(saved_book), record['expected_version'])
    entries = []
    for log in sorted(collection.glob('provider-*.log')):
        require(log.name in json.loads(manifest_raw), 'unbound provider log')
        entries.extend(json.loads(log.read_bytes()))
    stdout = ''.join(row.get('data', '') for row in entries if row.get('stream_name') == 'stdout')
    output = collection/'outputs/object-discovery-boundaries-v1'
    runtime = G.load(package/'runtime/protocol.json')
    validate_completion(output, 'COMPLETE', stdout, sha((package/'runtime/runtime-lock.json').read_bytes()),
                        expected_files={d['kind']: len(d['files']) for d in runtime['datasets']})
    result = evaluate(control/'preparation-r1', output/'worker', checkpoint, package)
    result.update(lifecycle_certified=True, provider_COMPLETE_and_completion_witness_still_required=False,
                  provider_status='COMPLETE', collection_manifest_sha256=sha(manifest_raw),
                  model_weights_loaded_during_evaluation=False, network_attempts=0, new_GPU_jobs=0,
                  target_identity_matches=True, deployment_guard_passed=True,
                  deployment_identity_warning_preserved=False, certification_scope=SOURCE_SCOPE)
    rebuilt = canonical(result)
    require(sha(rebuilt) == protocol['automatic_source_evaluation_sha256'], 'replayed native source evaluation differs')
    require(rebuilt == (control/'control-independent-evaluation-r1.json').read_bytes(), 'stored source evaluation differs')
    return result


def reconstruct_objects(points, arrays):
    """Independently reconstruct all SAM cells from raw logits and qualities."""
    import numpy as np
    import torch
    import torch.nn.functional as F
    from research.object_discovery_boundaries_v1 import sam21 as S
    n = len(points)
    S.point_prompts(points)
    require(set(arrays) == {'pred_masks', 'iou_scores', 'original_sizes', 'input_points', 'input_labels'},
            'SAM raw inventory differs')
    logits, scores = arrays['pred_masks'], arrays['iou_scores']
    require(logits.shape == (1, n, 3, 256, 256) and np.isfinite(logits).all() and
            scores.shape == (1, n, 3) and np.isfinite(scores).all(), 'SAM raw shape/values differ')
    require(logits.dtype == np.float32 and scores.dtype == np.float32, 'SAM CPU FP32 evidence required')
    require(np.array_equal(arrays['original_sizes'], [[448, 448]]), 'SAM original size differs')
    expected = np.array(S.point_prompts(points)['input_points'], dtype=np.float32)*(1024/448)
    require(arrays['input_points'].shape == expected.shape and
            np.allclose(arrays['input_points'], expected, rtol=0, atol=1e-4) and
            np.array_equal(arrays['input_labels'], np.ones((1, n, 1), dtype=np.int64)), 'processor points/labels differ')
    expanded = F.interpolate(torch.from_numpy(logits[0]), size=(448, 448), mode='bilinear', align_corners=False).numpy()
    objects = []
    for i, point in enumerate(points):
        k = int(np.argmax(scores[0, i]))
        majority = (expanded[i, k] > 0).reshape(64, 7, 64, 7).sum(axis=(1, 3)) >= 25
        cells = [[int(x), int(y)] for y, x in np.argwhere(majority)]
        objects.append(S.proposal(i+1, point, cells, scores[0, i].tolist(), k))
    return objects


@contextmanager
def offline_cpu():
    """Even a swallowed network attempt makes this replay fail."""
    values = {'CUDA_VISIBLE_DEVICES': '', 'NVIDIA_VISIBLE_DEVICES': 'void', 'HF_HUB_OFFLINE': '1',
              'TRANSFORMERS_OFFLINE': '1', 'HF_HUB_DISABLE_TELEMETRY': '1', 'MPLBACKEND': 'Agg'}
    old = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    connect, create = socket.socket.connect, socket.create_connection
    attempted = []
    def refuse(*args, **kwargs):
        attempted.append(True)
        raise PermissionError('automatic evidence replay: network forbidden')
    socket.socket.connect = socket.create_connection = refuse
    try:
        yield
        require(not attempted, 'automatic replay attempted networking')
    finally:
        socket.socket.connect, socket.create_connection = connect, create
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def replay_comparison(control_root, checkpoint, acquisition_path):
    with offline_cpu():
        return _replay_comparison(control_root, checkpoint, acquisition_path)


def _replay_comparison(control_root, checkpoint, acquisition_path):
    """Reference/mask pins and the raw evidence are mandatory, with no bypass."""
    control = Path(control_root)
    protocol = json.loads(Path(__file__).with_name('protocol.json').read_bytes())
    provenance = verify_provenance(control, protocol)
    require(sha(Path(acquisition_path).read_bytes()) == provenance['sam_checkpoint_acquisition_sha256'],
            'SAM acquisition record differs')
    from research.object_discovery_boundaries_v1 import deployment as D, sam21 as S
    from research.object_discovery_boundaries_v1.granularity_worker import inputs_for
    from research.object_discovery_boundaries_v1.scoring import score_frame
    import numpy as np
    import torch
    require(not torch.cuda.is_initialized(), 'replay must remain CPU-only')
    torch.set_num_threads(2)
    source = replay_source(control, checkpoint, protocol)
    policy_raw = (control/'comparison-policy-r1.json').read_bytes()
    policy = json.loads(policy_raw)
    plan_raw = (control/'sam21-postprocessing-plan-r1.json').read_bytes()
    plan = json.loads(plan_raw)
    acquisition = json.loads(Path(acquisition_path).read_bytes())
    require(acquisition['revision'] == S.REVISION and policy['policy'] == S.POLICY and plan['policy'] == S.POLICY,
            'frozen SAM model/policy differs')
    require(policy['source_evaluation_sha256'] == protocol['automatic_source_evaluation_sha256'] and
            policy['frozen_postprocessing_plan_sha256'] == sha(plan_raw) and
            policy['checkpoint_acquisition_sha256'] == sha(Path(acquisition_path).read_bytes()), 'SAM policy lineage differs')
    require(policy['adapter_sha256'] == sha(Path(S.__file__).read_bytes()) == plan['adapter_sha256'], 'SAM adapter drift')
    runner = Path(__file__).resolve().parents[2]/'scripts/run_sam21_retained_seeds.py'
    require(sha(runner.read_bytes()) == plan['runner_sha256'], 'SAM inference runner drift')
    require(D.verify_review(control/'gpu-live-review-r1') == plan['originating_review_lock_sha256'], 'source review differs')
    seeds_raw = (control/'seed-inputs-r1/manifest.json').read_bytes()
    require(policy['seed_manifest_sha256'] == sha(seeds_raw), 'SAM seeds not bound to policy')
    frames = inputs_for(control/'seed-inputs-r1')
    seeds = json.loads((control/'seed-inputs-r1/seeds.json').read_bytes())
    require(seeds['source_evaluation_sha256'] == protocol['automatic_source_evaluation_sha256'] and
            seeds['partial_invalid_points_reused'] is False, 'native seed lineage differs')
    out = control/'cpu-segmentation-attempt1'
    result_raw = (out/'result.json').read_bytes()
    result = json.loads(result_raw)
    witness_raw = (out/'completion-witness.json').read_bytes()
    witness = json.loads(witness_raw)
    elapsed = witness['elapsed_after_receipt_seconds']
    require(type(elapsed) in (int, float) and math.isfinite(elapsed) and 0 < elapsed < 1200 and
            witness['result_sha256'] == sha(result_raw) and result['status'] == 'complete', 'SAM CPU lifecycle differs')
    require('SAM21_CPU_RETURNED '+sha(witness_raw) in (control/'sam-cpu.stdout.log').read_text().splitlines(),
            'SAM CPU return marker missing')
    require(json.loads((control/'sam-cpu-operator-receipt-r1.json').read_bytes())['complete'] is True,
            'SAM CPU operator did not return')
    actual = {p.name: sha(p.read_bytes()) for p in out.iterdir() if p.is_file() and p.name not in ('result.json', 'completion-witness.json')}
    require(actual == result['output_sha256'], 'SAM output manifest differs')
    require(result['policy_sha256'] == sha(policy_raw) and result['seed_manifest_sha256'] == sha(seeds_raw),
            'SAM result/input bindings differ')
    for field in ('GPU_jobs', 'new_MolmoPoint_generations', 'game_actions', 'automatic_retries', 'network_attempts'):
        require(type(result[field]) is int and result[field] == 0, 'SAM scope differs: '+field)
    require(result['cuda_initialized'] is False and result['execution_device'] == 'cpu' and result['dtype'] == 'float32',
            'SAM CPU execution differs')
    reference_raw = (control/'gpu-live-review-r1/references/confirmed-review.json').read_bytes()
    require(sha(reference_raw) == protocol['reference_sha256'], 'owner reference differs before scoring')
    refs = json.loads(reference_raw)['frames']
    expected_ids = [c['case_id'] for c in protocol['cases']]
    require(expected_ids == [f['case_id'] for f in frames] == [f['case_id'] for f in refs] ==
            [f['case_id'] for f in source['cases']] == [f['case_id'] for f in result['frames']], 'frame inventory differs')
    rows = []
    for spec, frame, ref, old in zip(protocol['cases'], frames, refs, source['cases']):
        name = frame['case_id']
        raw_molmo = (control/'gpu-attempt1-terminal-collection-r1/outputs/object-discovery-boundaries-v1/worker'/(name+'.json')).read_bytes()
        require(sha(raw_molmo) == source['worker_input_sha256'][name+'.json'] == frame['retained_case_sha256'],
                'seed points not bound to native case')
        detail = json.loads(raw_molmo)
        require(frame['source_response_valid'] is old['response_valid'] and frame['points'] == detail['points'] and
                frame['image_sha256'] == detail['request']['image_sha256'], 'native seed/image binding differs')
        image_raw = (control/'seed-inputs-r1'/(name+'.png')).read_bytes()
        require(sha(image_raw) == frame['image_sha256'] and image_raw ==
                (control/'preparation-r1/inputs'/(name+'.png')).read_bytes(), 'SAM board differs from native pointing board')
        row = json.loads((out/(name+'.json')).read_bytes())
        require(row == result['frames'][len(rows)] and row['source_response_valid'] is old['response_valid'], 'SAM frame/result differs')
        if not frame['source_response_valid'] or not frame['points']:
            objects = []
            require(row['skipped'] is True and row['objects'] == [], 'invalid source response salvaged')
        else:
            require(row['skipped'] is False and row['seed_points'] == frame['points'], 'SAM seed inventory differs')
            raw_path = out/(name+'-raw.npz')
            require(sha(raw_path.read_bytes()) == row['raw_sha256'], 'SAM logits hash differs')
            admission = json.loads((out/(name+'-admission.json')).read_bytes())
            require(admission['seed_points'] == frame['points'] and admission['point_prompts'] == S.point_prompts(frame['points'])
                    and admission['input_image_sha256'] == frame['image_sha256'] and admission['policy_sha256'] == sha(policy_raw),
                    'SAM admission differs')
            require(type(row['frame_seconds']) in (int, float) and 0 < row['frame_seconds'] < 240, 'SAM frame overrun')
            with np.load(raw_path, allow_pickle=False) as arrays:
                objects = reconstruct_objects(frame['points'], arrays)
            require(canonical(objects) == canonical(row['objects']), 'independently reconstructed SAM objects differ')
        score = score_frame(objects, ref, level='whole', match_iou=.5)
        count = len(objects)
        rows.append(dict(case_id=name, game=spec['game_id'].split('-')[0], source_response_valid=frame['source_response_valid'],
                         fixed_seed_count=count, empty_failed_proposals=sum(not p['cells'] for p in objects),
                         comparison_precision_over_all_seed_proposals=score['matched_count']/count if count else None,
                         unmatched_seed_proposals=count-score['matched_count'], sam21=score,
                         color_component=old['whole_objects'], objects=objects))
    require(type(result['image_forward_calls']) is int and result['image_forward_calls'] == sum(bool(f['points']) for f in frames)
            and type(result['seed_segmentations']) is int and result['seed_segmentations'] == sum(len(f['points']) for f in frames),
            'SAM call/seed totals differ')
    totals = {}
    for key in ('color_component', 'sam21'):
        n = sum(r[key]['reference_count'] for r in rows)
        matches = [m for r in rows for m in r[key]['matches']]
        m, count = len(matches), sum(r['fixed_seed_count'] for r in rows)
        totals[key] = dict(reference_objects=n, seed_proposals=count, matched_masks=m,
                           exact_masks=sum(x['exact_mask'] for x in matches), mask_recall=m/n,
                           precision_over_all_seed_proposals=m/count if count else None,
                           mean_iou_over_all_reference_objects=sum(x['iou'] for x in matches)/n,
                           mean_boundary_F1_over_all_reference_objects=sum(x['boundary_f1'] for x in matches)/n)
    require(not torch.cuda.is_initialized(), 'replay initialized CUDA')
    comparison = dict(schema='sam21_retained_seed_boundary_comparison_v1', frames=rows, totals=totals,
        masks_replayed_without_model_inference=True, reference_sha256=sha(reference_raw),
        policy_sha256=sha(policy_raw), CPU_result_sha256=sha(result_raw),
        source_evaluation_sha256=sha(canonical(source)), seed_manifest_sha256=sha(seeds_raw),
        source_deployment_verified=True, historical_original_attempt_unchanged=True, network_attempts=0, new_GPU_jobs=0,
        new_MolmoPoint_generations=0, passing_verdict=None, qualification=QUALIFICATION)
    require(sha(canonical(comparison)) == protocol['automatic_masks_sha256'], 'rebuilt automatic artifact differs from protocol')
    return comparison
