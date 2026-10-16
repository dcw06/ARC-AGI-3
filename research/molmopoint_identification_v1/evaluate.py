"""CPU replay and exact target hits. References are never inference inputs."""
import json
import math
from pathlib import Path
from types import SimpleNamespace

from .adapter import decode_generation, verify_snapshot
from .supervisor import SCOPE, verify_packet
from .inference import requests_for, sha, metadata_value
from .scoring import score_target
from research.object_identification_v1.mount_check import canonical


def validate_completion(output, provider_status, cell_stdout, runtime_lock_sha256, *, expected_files=None):
    """A saved success receipt alone never certifies a finished lifecycle."""
    output = Path(output)
    raw = (output/'result.json').read_bytes()
    witness_raw = (output/'completion-witness.json').read_bytes()
    result, witness = json.loads(raw),json.loads(witness_raw)
    elapsed = witness['elapsed_after_receipt_write_seconds']
    if (provider_status != 'COMPLETE' or 'MOLMOPOINT_RETURNED '+sha(witness_raw) not in cell_stdout.splitlines()
            or witness['result_sha256'] != sha(raw) or witness.get('provider_COMPLETE_required') is not True
            or type(elapsed) not in (int,float) or not math.isfinite(elapsed) or not 0 < elapsed < 3300
            or result.get('status') != 'provisional_complete'
            or result['runtime_lock_sha256'] != runtime_lock_sha256
            or canonical(result['scope']) != canonical(SCOPE)
            or any(result.get(k) for k in ('error_type','error','cleanup_error'))
            or result.get('generation_requests') != 6 or result.get('gpu_cleanup_verified') is not True
            or result.get('temporary_environment_removed') is not True
            or result['cleanup'].get('groups_absent') is not True
            or result['cleanup'].get('error') or result['cleanup'].get('interrupted')):
        raise ValueError('incomplete, interrupted, over-budget or unbound lifecycle')
    actual = {p.relative_to(output).as_posix():sha(p.read_bytes()) for p in output.rglob('*')
              if p.is_file() and p.name not in ('result.json','completion-witness.json')}
    if actual != result['output_sha256']:
        raise ValueError('retained output files differ from lifecycle manifest')
    # Production collection supplies counts from its verified review protocol.
    # Retained review-r1 fixtures remain readable with their original inventory.
    counts={'wheelhouse':177,'model':33,'inputs':9} if expected_files is None else expected_files
    if (set(counts)!={'wheelhouse','model','inputs'} or
            any(type(n) is not int or not 0<n<=1000 for n in counts.values())):
        raise ValueError('bound dataset file counts required')
    if (set(result['datasets'])!=set(counts) or any(
            result['datasets'][k]['files_checked']!=n or
            result['datasets'][k]['all_sha256_matched'] is not True for k,n in counts.items())
            or not result.get('gpu',{}).get('uuid') or
            'RTX PRO 6000' not in result.get('gpu',{}).get('name','')
            or result.get('game_actions')!=0 or result.get('scorecards')!=0):
        raise ValueError('mounted bytes, GPU identity or zero-action scope not established')
    return True


def evaluate(preparation, worker, model_folder, review_package):
    """Rebuild prompts, image metadata and native points without loading weights."""
    from research.object_identification_v1.deployment import verify_review
    review_package=Path(review_package)
    review_pin=verify_review(review_package)
    verify_packet(review_package/'runtime')
    binding=json.loads((review_package/'evaluation-binding.json').read_bytes())
    source_root=Path(__file__).resolve().parents[2]
    for name,expected in binding['source_sha256'].items():
        if sha((source_root/name).read_bytes()) != expected:
            raise ValueError('evaluating checkout differs from reviewed source')
    for name,expected in binding['references_sha256'].items():
        if sha((Path(preparation)/name).read_bytes()) != expected:
            raise ValueError('references differ from frozen review binding')
    protocol=json.loads((review_package/'runtime/protocol.json').read_bytes())
    images=next(d for d in protocol['datasets'] if d['kind']=='inputs')['files']
    for row in images:
        if row['name'].endswith(('.png','.jsonl')) and sha((Path(preparation)/'inputs'/row['name']).read_bytes())!=row['sha256']:
            raise ValueError('model input differs from reviewed manifest')
    verify_snapshot(model_folder)
    from PIL import Image
    from transformers import AutoProcessor
    from transformers.dynamic_module_utils import get_class_from_dynamic_module
    preparation, worker = Path(preparation), Path(worker)
    requests = requests_for(preparation/'inputs')
    # Caller verifies the frozen checkpoint manifest. Import its pinned decoder,
    # not its weights. The only model methods here use config, not parameters.
    cls = get_class_from_dynamic_module('modeling_molmo_point.MolmoPointForConditionalGeneration',
                                      str(model_folder),local_files_only=True)
    config = json.loads((Path(model_folder)/'config.json').read_bytes())
    model = SimpleNamespace(config=SimpleNamespace(**config))
    model.extract_image_points = lambda *args: cls.extract_image_points(model,*args)
    processor = AutoProcessor.from_pretrained(str(model_folder),trust_remote_code=True,
        local_files_only=True,padding_side='left',use_fast=False)
    refs = {r['case_id']:r for r in json.loads((preparation/'references/answers.json').read_bytes())}
    targets = json.loads((preparation/'references/selected-targets.json').read_bytes())
    if len(targets)!=6 or [t['case_id'] for t in targets] != [r['case_id'] for r in requests]:
        raise ValueError('six frozen target references required')
    rows, hashes = [], {}
    for number,(request,target) in enumerate(zip(requests,targets),1):
        case = request['case_id']
        detail_raw = (worker/(case+'.json')).read_bytes()
        hashes[case+'.json'] = sha(detail_raw)
        detail = json.loads(detail_raw)
        admitted = json.loads((worker/(case+'-admission.json')).read_bytes())
        if (canonical(detail['request']) != canonical(request) or
                detail['request_sha256'] != sha(canonical(request)) or
                canonical(admitted['request']) != canonical(request) or admitted['call_number'] != number or
                admitted['request_sha256'] != sha(canonical(request))):
            raise ValueError('request/admission replay differs')
        with Image.open(preparation/request['image']) as image:
            encoded = processor.apply_chat_template([{'role':'user','content':[
                {'type':'text','text':request['prompt']},{'type':'image','image':image}]}],
                tokenize=True,add_generation_prompt=True,return_tensors='pt',return_dict=True,
                padding=True,return_pointing_metadata=True)
        metadata = encoded.pop('metadata')
        if canonical(encoded['input_ids'][0].tolist()) != canonical(detail['prompt_token_ids']):
            raise ValueError('prompt tokens differ from independent processor replay')
        serial = metadata_value(metadata)
        # JSON-normalize tuples/lists before comparing, retaining every numeric value.
        if canonical(serial) != canonical(detail['metadata']):
            raise ValueError('pointing metadata differs from image replay')
        ids = detail['generated_token_ids']
        if (type(ids) is not list or not 1 <= len(ids) <= 1024 or
                any(type(v) is not int or v < 0 for v in ids) or
                any(type(detail[k]) is not int for k in ('prompt_tokens','completion_tokens'))):
            raise ValueError('strict bounded integer token evidence required')
        times=[detail[k] for k in ('generation_started_at_monotonic','generated_at_monotonic',
                                  'case_finalized_at_monotonic','call_deadline_monotonic')]
        if (any(type(t) not in (int,float) or not math.isfinite(t) for t in times) or
                not admitted['admitted_at_monotonic'] <= times[0] <= times[1] <= times[2] < times[3] or
                not 0 < times[3]-times[0] <= 180):
            raise ValueError('generation evidence outside its bounded admission')
        eos = json.loads((Path(model_folder)/'generation_config.json').read_bytes())['eos_token_id']
        eos = [eos] if type(eos) is int else eos
        finish = 'stop' if ids and ids[-1] in eos else 'length' if len(ids)==1024 else 'interrupted'
        raw_text = processor.post_process_image_text_to_text([ids],skip_special_tokens=False,
                                                           clean_up_tokenization_spaces=False)[0]
        if (detail['finish_reason'] != finish or detail['eos_token_ids'] != eos or
                detail['completion_tokens'] != len(ids) or detail['prompt_tokens'] != len(detail['prompt_token_ids']) or
                detail['raw_text_with_special_tokens'] != raw_text or
                detail['generation_parameters'] != {'max_new_tokens':1024,'do_sample':False,'num_beams':1}):
            raise ValueError('generation contract/raw output differs')
        decoded, error = None, None
        try:
            decoded = decode_generation(model,processor,ids,metadata,(448,448),finish_reason=finish)
        except ValueError as exc:
            error = str(exc)
        if (detail['decode_valid'] is not (decoded is not None) or
                decoded is not None and any(canonical(detail[key]) != canonical(decoded[key])
                                           for key in ('points','native_points','point_sequence'))):
            raise ValueError('native decoder replay differs')
        region = next(r for r in refs[case]['regions'] if r['id']==target['target_region_id'])
        if target['prompt'] != request['prompt'] or sha(canonical(region)) != target['reference_region_sha256']:
            raise ValueError('frozen prompt/target reference differs')
        score = score_target(refs[case],target['target_region_id'],decoded['points'] if decoded else [])
        if decoded is None:
            score.update(response_valid=False,target_hit=False,response_error=error)
        rows.append(score)
    summary = json.loads((worker/'worker.json').read_bytes())
    if summary['generation_requests'] != 6 or summary['game_actions'] != 0:
        raise ValueError('worker summary differs from six retained calls')
    return dict(schema='molmopoint_targeted448_evaluation_v1',cases=rows,
                replay_verified=True,worker_input_sha256=hashes,review_lock_sha256=review_pin,
                target_hits=sum(r['target_hit'] for r in rows),
                valid_responses=sum(r['response_valid'] for r in rows),
                qualification='Six exposed, cued targets; no object discovery, obstacle, extent or gameplay claim.',
                lifecycle_certified=False,provider_COMPLETE_and_completion_witness_still_required=True)
