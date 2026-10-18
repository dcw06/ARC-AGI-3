"""Independent uncued request/token/mask replay; references remain local."""
import json
import math
from pathlib import Path
from types import SimpleNamespace

from . import deployment as D
from .decoding import decode_inventory
from .evaluation import verified_preparation, validate_review
from .inference import sha, metadata_value
from .masks import seed_masks
from .prepare import requests_for, MAX_NEW_TOKENS
from .scoring import score_frame
from .supervisor import SCOPE, verify_packet
from research.molmopoint_identification_v1.adapter import MODEL, REVISION, verify_snapshot
from research.object_identification_v1.mount_check import canonical
from certification.phase4_multimodal_preflight_v3.images import grid_from_png


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def validate_completion(output, provider_status, stdout, runtime_pin, *, expected_files):
    root = Path(output)
    raw, witness_raw = (root/'result.json').read_bytes(), (root/'completion-witness.json').read_bytes()
    result, witness = json.loads(raw), json.loads(witness_raw)
    elapsed = witness.get('elapsed_after_receipt_write_seconds')
    if (provider_status != 'COMPLETE' or 'OBJECT_BOUNDARIES_RETURNED '+sha(witness_raw) not in stdout.splitlines()
            or witness.get('result_sha256') != sha(raw) or witness.get('provider_COMPLETE_required') is not True
            or not number(elapsed) or not 0 < elapsed < SCOPE['worker_seconds']
            or result.get('status') != 'provisional_complete' or result.get('runtime_lock_sha256') != runtime_pin
            or canonical(result.get('scope')) != canonical(SCOPE)
            or any(result.get(k) for k in ('error_type','error','cleanup_error'))
            or type(result.get('generation_requests')) is not int or result['generation_requests'] != 6
            or result.get('gpu_cleanup_verified') is not True or result.get('temporary_environment_removed') is not True
            or result.get('cleanup',{}).get('groups_absent') is not True
            or result['cleanup'].get('error') or result['cleanup'].get('interrupted')):
        raise ValueError('incomplete, interrupted, over-budget or unbound lifecycle')
    actual = {p.relative_to(root).as_posix():sha(p.read_bytes()) for p in root.rglob('*')
              if p.is_file() and p.name not in ('result.json','completion-witness.json')}
    if actual != result['output_sha256']: raise ValueError('retained output manifest differs')
    if (set(expected_files) != {'wheelhouse','model','inputs'} or
            any(type(v) is not int or v <= 0 for v in expected_files.values()) or
            set(result['datasets']) != set(expected_files) or any(
                type(result['datasets'][k].get('files_checked')) is not int or
                result['datasets'][k]['files_checked'] != count or
                result['datasets'][k].get('all_sha256_matched') is not True for k,count in expected_files.items())
            or result.get('agent_input_staging',{}).get('files_checked') != 7
            or result['agent_input_staging'].get('all_sha256_matched') is not True
            or not result.get('gpu',{}).get('uuid') or 'RTX PRO 6000' not in result.get('gpu',{}).get('name','')
            or any(type(result.get(k)) is not int or result[k] != 0 for k in ('game_actions','scorecards'))):
        raise ValueError('mounted bytes, input staging, GPU or zero-action scope not established')
    return True


def replay_case(request, admitted, detail, raw, model, processor, encoded, image_bytes, eos, number_in_run):
    """Reconstruct a case without trusting reported decode validity or masks."""
    pin = sha(canonical(request))
    raw_keys = {'request','request_sha256','generated_token_ids','prompt_token_ids','eos_token_ids',
        'prompt_tokens','completion_tokens','finish_reason','raw_text_with_special_tokens','metadata',
        'decode_valid','points','generation_parameters','generation_started_at_monotonic',
        'call_deadline_monotonic','generated_at_monotonic','generation_seconds'}
    if set(raw) != raw_keys: raise ValueError('raw generation evidence is incomplete or altered')
    if (canonical(admitted.get('request')) != canonical(request) or admitted.get('request_sha256') != pin
            or type(admitted.get('call_number')) is not int or admitted['call_number'] != number_in_run
            or canonical(detail.get('request')) != canonical(request) or detail.get('request_sha256') != pin):
        raise ValueError('frozen request/admission differs')
    for key,value in raw.items():
        if key in ('decode_valid','points'): continue
        if canonical(detail.get(key)) != canonical(value): raise ValueError('raw output differs: '+key)
    if raw.get('decode_valid') is not False or raw.get('points') != []:
        raise ValueError('raw output was not retained before decoding')
    metadata = encoded['metadata']
    prompt_ids = encoded['input_ids'][0].tolist()
    if (canonical(prompt_ids) != canonical(detail['prompt_token_ids']) or
            canonical(metadata_value(metadata)) != canonical(detail['metadata'])):
        raise ValueError('independent processor replay differs')
    ids = detail['generated_token_ids']
    if (type(ids) is not list or not 1 <= len(ids) <= MAX_NEW_TOKENS or
            any(type(v) is not int or v < 0 for v in ids) or
            any(type(detail.get(k)) is not int for k in ('prompt_tokens','completion_tokens'))):
        raise ValueError('bounded strict integer tokens required')
    times = [admitted.get('admitted_at_monotonic')] + [detail.get(k) for k in (
        'generation_started_at_monotonic','generated_at_monotonic','case_finalized_at_monotonic','call_deadline_monotonic')]
    if (not all(number(t) for t in times) or not times[0] <= times[1] <= times[2] <= times[3] < times[4]
            or not 0 < times[4]-times[1] <= 180
            or not number(detail.get('generation_seconds')) or detail['generation_seconds'] < 0):
        raise ValueError('generation/finalization outside bounded admission')
    finish = 'stop' if ids[-1] in eos else 'length' if len(ids)==MAX_NEW_TOKENS else 'interrupted'
    text = processor.post_process_image_text_to_text([ids],skip_special_tokens=False,clean_up_tokenization_spaces=False)[0]
    if (detail['finish_reason'] != finish or detail['eos_token_ids'] != eos
            or detail['completion_tokens'] != len(ids) or detail['prompt_tokens'] != len(prompt_ids)
            or detail['raw_text_with_special_tokens'] != text
            or canonical(detail['generation_parameters']) != canonical(dict(max_new_tokens=MAX_NEW_TOKENS,do_sample=False,num_beams=1))):
        raise ValueError('frozen generation contract differs')
    decoded,error = None,None
    try: decoded = decode_inventory(model,processor,ids,metadata,(448,448),finish_reason=finish)
    except ValueError as exc: error = str(exc)
    if detail['decode_valid'] is not (decoded is not None): raise ValueError('decode validity differs')
    if decoded is not None and any(canonical(detail[key]) != canonical(decoded[key]) for key in ('points','native_points','point_sequence')):
        raise ValueError('native point replay differs')
    if decoded is None and detail['points'] != []: raise ValueError('invalid output supplies points')
    grid = grid_from_png(image_bytes,cell=7)
    if sha(canonical(grid)) != request['grid_sha256'] or detail['grid_sha256'] != request['grid_sha256']:
        raise ValueError('image/grid differs')
    objects = seed_masks(grid,decoded['points']) if decoded else []
    if canonical(objects) != canonical(detail['objects']): raise ValueError('independent pixel-mask replay differs')
    return dict(case_id=request['case_id'],response_valid=decoded is not None,response_error=error,
                objects=objects,completion_tokens=len(ids),passing_verdict=None)


def evaluate(preparation, worker, model_folder, review_package):
    review_package, preparation, worker = map(Path,(review_package,preparation,worker))
    review_pin = D.verify_review(review_package)
    verify_packet(review_package/'runtime')
    binding = json.loads((review_package/'evaluation-binding.json').read_bytes())
    root = Path(__file__).resolve().parents[2]
    for name,pin in binding['source_sha256'].items():
        if sha((root/name).read_bytes()) != pin: raise ValueError('evaluating checkout differs')
    for name,pin in binding['reference_files_sha256'].items():
        if sha((review_package/name).read_bytes()) != pin: raise ValueError('reference binding differs')
    owner_review = json.loads((review_package/'references/confirmed-review.json').read_bytes())
    validate_review(owner_review,verified_preparation(preparation))
    protocol = json.loads((review_package/'runtime/protocol.json').read_bytes())
    requests = requests_for(preparation/'inputs',prompt_profile=protocol.get('prompt_profile','legacy_whole_v1'))
    expected_outputs = {'worker.json'} | {r['case_id']+suffix+'.json' for r in requests for suffix in ('','-raw','-admission')}
    if {p.relative_to(worker).as_posix() for p in worker.rglob('*') if p.is_file()} != expected_outputs:
        raise ValueError('exactly six admissions, raw outputs and finalized cases required')
    for row in protocol['agent_input_files']:
        if sha((preparation/'inputs'/row['name']).read_bytes()) != row['sha256']: raise ValueError('uncued input differs')
    verify_snapshot(model_folder)
    from PIL import Image
    from transformers import AutoProcessor
    from transformers.dynamic_module_utils import get_class_from_dynamic_module
    cls = get_class_from_dynamic_module('modeling_molmo_point.MolmoPointForConditionalGeneration',str(model_folder),local_files_only=True)
    config = json.loads((Path(model_folder)/'config.json').read_bytes())
    model = SimpleNamespace(config=SimpleNamespace(**config))
    model.extract_image_points = lambda *args: cls.extract_image_points(model,*args)
    processor = AutoProcessor.from_pretrained(str(model_folder),trust_remote_code=True,local_files_only=True,padding_side='left',use_fast=False)
    eos = json.loads((Path(model_folder)/'generation_config.json').read_bytes())['eos_token_id']
    eos = [eos] if type(eos) is int else eos
    if type(eos) is not list or not eos or any(type(v) is not int for v in eos): raise ValueError('EOS contract differs')
    rows,hashes = [],{}
    for index,(request,frame) in enumerate(zip(requests,owner_review['frames']),1):
        case = request['case_id']
        if case != frame['case_id']: raise ValueError('reference order differs')
        def load(suffix):
            path = worker/(case+suffix+'.json'); raw = path.read_bytes(); hashes[path.name] = sha(raw); return json.loads(raw)
        with Image.open(preparation/request['image']) as image:
            encoded = processor.apply_chat_template([{'role':'user','content':[
                {'type':'text','text':request['prompt']},{'type':'image','image':image}]}],tokenize=True,
                add_generation_prompt=True,return_tensors='pt',return_dict=True,padding=True,return_pointing_metadata=True)
        row = replay_case(request,load('-admission'),load(''),load('-raw'),model,processor,encoded,
                          (preparation/request['image']).read_bytes(),eos,index)
        row['whole_objects'] = score_frame(row['objects'],frame,level='whole',match_iou=binding['match_iou'])
        rows.append(row)
    summary = json.loads((worker/'worker.json').read_bytes())
    expected = dict(generation_requests=6,game_actions=0,scorecards=0,model=MODEL,revision=REVISION,
                    pretrained_weights_loaded=True,execution_device='cuda',automatic_retries=0)
    if canonical(summary) != canonical(expected): raise ValueError('summary differs from six retained calls')
    return dict(schema='object_boundary_uncued_live_evaluation_v1',cases=rows,replay_verified=True,
        worker_input_sha256=hashes,review_lock_sha256=review_pin,valid_responses=sum(r['response_valid'] for r in rows),
        passing_verdict=None,lifecycle_certified=False,provider_COMPLETE_and_completion_witness_still_required=True,
        qualification='Six exposed initial boards; uncued whole-object seeds plus deterministic same-color components. Not model-only segmentation or gameplay.')
