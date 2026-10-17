"""Score a retained development comparison; never select a winning granularity."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.object_discovery_boundaries_v1.granularity import condition, assemble, SEMANTIC_CHANNEL
from research.object_discovery_boundaries_v1.granularity_backends import binary_original
from research.object_discovery_boundaries_v1.granularity_runtime import file_sha
from research.object_discovery_boundaries_v1.granularity_worker import inputs_for, write_json
from research.object_discovery_boundaries_v1.scoring import score_frame


def evaluate(frames_dir, inputs, references):
    import numpy as np
    frames_dir = Path(frames_dir)
    manifest = json.loads((frames_dir/'worker-manifest.json').read_bytes())
    if set(manifest) != {p.name for p in frames_dir.iterdir()} - {'worker-manifest.json'}:
        raise ValueError('retained output inventory differs')
    for name, pin in manifest.items():
        path = frames_dir/name
        if Path(name).name != name or path.is_symlink() or file_sha(path) != pin:
            raise ValueError('retained output bytes differ')
    policy = json.loads((frames_dir/'policy.json').read_bytes())
    if policy != condition(policy['model'],policy['mode'],policy['granularity']):
        raise ValueError('retained policy differs')
    seeds = inputs_for(inputs)
    refs = json.loads(Path(references).read_bytes())['frames']
    if [f['case_id'] for f in refs] != [f['case_id'] for f in seeds]:
        raise ValueError('reference/input order differs')
    result = []
    for seed, ref in zip(seeds, refs):
        name = seed['case_id']
        # Bind the reference grids to the actual retained input image. A
        # different board or post-action observation cannot be scored here.
        from certification.phase4_multimodal_preflight_v3.images import grid_from_png
        if ref.get('grid') != grid_from_png((Path(inputs)/(name+'.png')).read_bytes(),cell=7):
            raise ValueError('reference board differs from inference image')
        saved = json.loads((frames_dir/(name+'.json')).read_bytes())
        expected_skip = policy['mode']=='seeded' and (not seed['source_response_valid'] or not seed['points'])
        if saved['case_id'] != name or saved['skipped'] != expected_skip:
            raise ValueError('saved frame/skip rule differs')
        if expected_skip:
            if saved['objects']:
                raise ValueError('invalid seed frame salvaged')
        else:
            metadata = json.loads((frames_dir/(name+'-raw-metadata.json')).read_bytes())
            if saved.get('raw_sha256') != file_sha(frames_dir/(name+'-raw.npz')):
                raise ValueError('frame/raw binding differs')
            with np.load(frames_dir/(name+'-raw.npz'), allow_pickle=False) as arrays:
                masks, qualities = arrays['raw_masks'], arrays['raw_qualities']
                if policy['mode']=='seeded':
                    if policy['model']=='semantic_sam_l':
                        channel=SEMANTIC_CHANNEL[policy['granularity']]
                        selected=[channel]*len(seed['points'])
                    else:
                        selected=np.argmax(qualities,axis=1).tolist()
                    chosen=np.stack([mask[i] for mask,i in zip(masks,selected)])
                    qualities=[float(score[i]) for score,i in zip(qualities,selected)]
                else:
                    chosen=masks
                    qualities=qualities.tolist()
                replay=dict(masks=binary_original(chosen,logits=policy['mode']=='seeded'),qualities=qualities)
                if metadata['qualities'] != qualities:
                    raise ValueError('raw/selected quality differs')
                converted=assemble(replay,policy,seed['points'] if policy['mode']=='seeded' else None)
                if any(saved[k] != value for k,value in converted.items()):
                    raise ValueError('raw mask replay differs from scored proposals')
        result.append(dict(case_id=name,whole=score_frame(saved['objects'],ref),
                           raw_proposal_count=saved.get('raw_proposal_count',0),
                           discarded_by_proposal_budget=saved.get('discarded_by_proposal_budget',0)))
    return dict(policy=policy,reference_sha256=file_sha(references),
                worker_manifest_sha256=file_sha(frames_dir/'worker-manifest.json'),frames=result,
                qualification='One separate development condition on owner-reviewed retained frames. No best-level selection, gameplay, or GPU lifecycle certification.',
                passing_verdict=None)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ('frames','inputs','references','output'):
        parser.add_argument('--'+arg,required=True)
    args=parser.parse_args()
    write_json(args.output,evaluate(args.frames,args.inputs,args.references))
