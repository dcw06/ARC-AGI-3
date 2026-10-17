"""Bounded offline CPU SAM 2.1 comparison; no new MolmoPoint calls or gameplay."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from research.object_discovery_boundaries_v1 import sam21 as S
from research.object_discovery_boundaries_v1.granularity_worker import inputs_for
from research.object_identification_v1.mount_check import canonical


def sha(raw):return hashlib.sha256(raw).hexdigest()


def run(inputs,checkpoint,acquisition_path,policy_path,output):
    started=time.monotonic();deadline=started+1200
    inputs,checkpoint,output=map(Path,(inputs,checkpoint,output))
    if output.exists():raise FileExistsError('preserve every earlier attempt')
    policy_raw=Path(policy_path).read_bytes();policy=json.loads(policy_raw)
    if (canonical(policy['policy'])!=canonical(S.POLICY) or policy['execution_device']!='cpu' or
            policy['dtype']!='float32' or policy['threads']!=4 or policy['total_worker_seconds']!=1200 or
            policy['per_frame_seconds']!=240 or policy['references_available_to_inference'] is not False or
            policy['adapter_sha256']!=sha((ROOT/'research/object_discovery_boundaries_v1/sam21.py').read_bytes())):
        raise ValueError('frozen comparison policy differs')
    manifest_raw=(inputs/'manifest.json').read_bytes();manifest=json.loads(manifest_raw)
    if sha(manifest_raw)!=policy['seed_manifest_sha256']:raise ValueError('seed manifest differs')
    # Shared strict inventory, streamed file hash and frame-to-PNG checks.
    # Updating the local manifest cannot rebind a seed frame to another board.
    frames=inputs_for(inputs)
    acquisition_raw=Path(acquisition_path).read_bytes();acquisition=json.loads(acquisition_raw)
    if sha(acquisition_raw)!=policy['checkpoint_acquisition_sha256'] or acquisition['revision']!=S.REVISION:
        raise ValueError('checkpoint pin differs')
    for name,row in acquisition['files'].items():
        path=checkpoint/name
        if path.is_symlink() or not path.resolve().is_relative_to(checkpoint.resolve()):raise ValueError('unsafe checkpoint file')
        h=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(4*1024*1024),b''):h.update(block)
        if path.stat().st_size!=row['bytes'] or h.hexdigest()!=row['sha256']:raise ValueError('checkpoint bytes differ')
    os.environ.update(CUDA_VISIBLE_DEVICES='',NVIDIA_VISIBLE_DEVICES='void',HF_HUB_OFFLINE='1',
        TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',MPLBACKEND='Agg')
    attempted=[]
    def refuse(*args,**kwargs):attempted.append(True);raise PermissionError('offline SAM CPU comparison')
    original_connect,original_create=socket.socket.connect,socket.create_connection
    socket.socket.connect=socket.create_connection=refuse
    def expired(*args):raise TimeoutError('bounded SAM CPU comparison deadline')
    old_handler=signal.signal(signal.SIGALRM,expired)
    output.mkdir(parents=True)
    def write(name,value):
        with (output/name).open('xb') as stream:stream.write(canonical(value))
    result=dict(status='incomplete',policy_sha256=sha(policy_raw),seed_manifest_sha256=sha(manifest_raw),
        model=S.MODEL,revision=S.REVISION,execution_device='cpu',dtype='float32',frames=[],
        GPU_jobs=0,new_MolmoPoint_generations=0,game_actions=0,automatic_retries=0)
    try:
        signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.monotonic()))
        import torch,numpy as np,transformers
        from transformers import Sam2Model,Sam2Processor
        from PIL import Image
        if transformers.__version__!='4.57.1' or torch.__version__!='2.10.0+cpu':raise ValueError('CPU runtime differs')
        if torch.cuda.is_initialized():raise ValueError('CUDA initialized')
        torch.set_num_threads(4);torch.set_num_interop_threads(1);torch.manual_seed(0)
        # Explicit image model/processor. The published checkpoint also carries
        # video-only weights, which are recorded rather than silently replaced.
        model,loading=Sam2Model.from_pretrained(checkpoint,local_files_only=True,trust_remote_code=False,
            use_safetensors=True,torch_dtype=torch.float32,output_loading_info=True)
        model.eval()
        write('loading-info.json',loading)
        if loading.get('missing_keys') or loading.get('mismatched_keys') or loading.get('error_msgs'):
            raise ValueError('image model weights incomplete or mismatched')
        if any(p.device.type!='cpu' or p.is_floating_point() and p.dtype!=torch.float32 for p in model.parameters()):
            raise ValueError('CPU FP32 model placement differs')
        processor=Sam2Processor.from_pretrained(checkpoint,local_files_only=True,trust_remote_code=False)
        result.update(transformers=transformers.__version__,torch=torch.__version__,
                      image_model_parameters=sum(p.numel() for p in model.parameters()),
                      loading_info_sha256=sha((output/'loading-info.json').read_bytes()))
        print(json.dumps(dict(stage='SAM_image_model_loaded',parameters=result['image_model_parameters'],
            missing_keys=len(loading.get('missing_keys',[])),video_only_unused_keys=len(loading.get('unexpected_keys',[])))),flush=True)
        for frame in frames:
            name=frame['case_id']
            if not frame['source_response_valid'] or not frame['points']:
                row=dict(case_id=name,source_response_valid=frame['source_response_valid'],skipped=True,
                    reason='invalid source response; no partial salvage' if not frame['source_response_valid'] else 'empty valid inventory',objects=[])
                write(name+'.json',row);result['frames'].append(row);continue
            frame_started=time.monotonic();until=min(deadline,frame_started+240)
            signal.setitimer(signal.ITIMER_REAL,max(.001,until-time.monotonic()))
            prompts=S.point_prompts(frame['points'])
            admission=dict(case_id=name,input_image_sha256=frame['image_sha256'],seed_points=frame['points'],
                point_prompts=prompts,multimask_output=True,admitted_at_monotonic=frame_started,
                deadline_monotonic=until,policy_sha256=sha(policy_raw))
            write(name+'-admission.json',admission)
            with Image.open(inputs/(name+'.png')) as image:
                if image.size!=(448,448) or image.mode!='RGB':raise ValueError('original plain448 image required')
                encoded=processor(images=image,**prompts,return_tensors='pt')
            if encoded['original_sizes'].tolist()!=[[448,448]]:raise ValueError('original image coordinate frame differs')
            # Verify the processor scaled x/y to its fixed 1024px encoder frame.
            expected=torch.tensor(prompts['input_points'],dtype=encoded['input_points'].dtype)*(1024/448)
            if not torch.allclose(encoded['input_points'],expected,rtol=0,atol=1e-4):raise ValueError('processor seed scaling differs')
            with torch.inference_mode():outputs=model(**encoded,multimask_output=True)
            # Durable raw logits/quality before choosing or projecting any mask.
            with (output/(name+'-raw.npz')).open('xb') as stream:
                np.savez_compressed(stream,pred_masks=outputs.pred_masks.detach().cpu().numpy(),
                    iou_scores=outputs.iou_scores.detach().cpu().numpy(),
                    original_sizes=encoded['original_sizes'].cpu().numpy(),
                    input_points=encoded['input_points'].cpu().numpy(),input_labels=encoded['input_labels'].cpu().numpy())
            expanded=processor.post_process_masks(outputs.pred_masks.cpu(),encoded['original_sizes'],
                binarize=False,mask_threshold=0.,max_hole_area=0.,max_sprinkle_area=0.,
                apply_non_overlapping_constraints=False)[0]
            scores=outputs.iou_scores[0].tolist();objects=[]
            if tuple(expanded.shape)!=(len(frame['points']),3,448,448):raise ValueError('SAM per-object multimask shape differs')
            for index,(point,quality) in enumerate(zip(frame['points'],scores),1):
                selected=S.select_candidate(quality)
                mask=S.mask_from_logits(expanded[index-1,selected].tolist())
                objects.append(S.proposal(index,point,mask,quality,selected))
            row=dict(case_id=name,source_response_valid=True,skipped=False,seed_points=frame['points'],objects=objects,
                processed_input_points=encoded['input_points'].tolist(),input_labels=encoded['input_labels'].tolist(),
                raw_sha256=sha((output/(name+'-raw.npz')).read_bytes()),frame_seconds=time.monotonic()-frame_started)
            write(name+'.json',row)
            if time.monotonic()>=until:raise TimeoutError('SAM frame finalization overrun')
            result['frames'].append(row)
            print(json.dumps(dict(case_id=name,seeds=len(objects),empty_masks=sum(r['empty_mask'] for r in objects),
                seconds=round(row['frame_seconds'],3))),flush=True)
        if attempted or torch.cuda.is_initialized():raise ValueError('CPU/offline constraints violated')
        result.update(status='complete',network_attempts=0,cuda_initialized=False,pretrained_SAM_segmentation=True,
            image_forward_calls=sum(not r['skipped'] for r in result['frames']),
            seed_segmentations=sum(len(r['objects']) for r in result['frames']))
    except BaseException as exc:
        result.update(error_type=type(exc).__name__,error=str(exc)[:1200]);raise
    finally:
        try:
            result['elapsed_before_receipt_seconds']=time.monotonic()-started
            result['output_sha256']={p.name:sha(p.read_bytes()) for p in output.iterdir() if p.is_file()}
            write('result.json',result)
            if result['status']=='complete':
                if time.monotonic()>=deadline:raise TimeoutError('SAM CPU finalization overrun')
                write('completion-witness.json',dict(result_sha256=sha((output/'result.json').read_bytes()),
                    elapsed_after_receipt_seconds=time.monotonic()-started))
                if time.monotonic()>=deadline:raise TimeoutError('SAM CPU witness overrun')
                print('SAM21_CPU_RETURNED '+sha((output/'completion-witness.json').read_bytes()),flush=True)
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old_handler)
            socket.socket.connect,socket.create_connection=original_connect,original_create
    return result


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    for n in ('inputs','checkpoint','acquisition','policy','output'):cli.add_argument('--'+n,required=True)
    a=cli.parse_args();run(a.inputs,a.checkpoint,a.acquisition,a.policy,a.output)
