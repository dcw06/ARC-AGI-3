"""Amendment S1 self-review (frozen protocol v2 §7): draw the seeded sample, then check the annotations (CPU only).

    python scripts/stagnation_supervision_selfreview.py draw --session1 OUT1 --session2 OUT2 --out FOLDER
        rebuilds both sessions' episodes with the frozen evaluator (each must have no problem), draws the sample
        from the decision-point lists only and writes FOLDER/sample.json and FOLDER/annotations.json (an empty
        template). It prints counts per stratum and never computes an arm-level summary.
    python scripts/stagnation_supervision_selfreview.py check --sample FOLDER/sample.json --annotations FILE
        validates the completed annotations against the sample and prints their SHA-256, which the pooled
        evaluation requires (commit the annotations before running it).
Rehearsal evidence needs --mode rehearsal and the same schedule/horizon overrides the session evaluation used.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def specs(args):
    from research.stagnation_supervision_v1.closed_loop.bridge import session_spec
    from research.stagnation_supervision_v1.closed_loop.runner import protocol
    out = {}
    for s in ('1', '2'):
        spec = session_spec(protocol(), s)
        if args.mode == 'rehearsal' and args.rehearsal_actions is not None:
            spec = {**spec, 'limits': {**spec['limits'], 'actions_per_episode': args.rehearsal_actions}}
        out[s] = spec
    return out


def main():
    from research.stagnation_supervision_v1 import thresholds as S
    from research.stagnation_supervision_runtime_v2 import pooled as P, selfreview as SR
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    d = sub.add_parser('draw')
    d.add_argument('--session1', required=True, type=Path)
    d.add_argument('--session2', required=True, type=Path)
    d.add_argument('--out', required=True, type=Path)
    d.add_argument('--mode', choices=('live', 'rehearsal'), default='live')
    d.add_argument('--rehearsal-actions', type=int)
    c = sub.add_parser('check')
    c.add_argument('--sample', required=True, type=Path)
    c.add_argument('--annotations', required=True, type=Path)
    args = parser.parse_args()
    if args.command == 'draw':
        if args.mode == 'live' and args.rehearsal_actions is not None:
            parser.error('rehearsal overrides cannot be used for live evidence')
        trigger, spec = S.load(), specs(args)
        episodes = []
        for s, folder in (('1', args.session1), ('2', args.session2)):
            episodes += P.session_episodes(folder / 'worker/run', spec[s], trigger, s)
        horizon = spec['1']['limits']['actions_per_episode']
        sample = SR.draw(SR.candidates(episodes, trigger, horizon), inputs=P.inputs_digest(episodes))
        args.out.mkdir(parents=True, exist_ok=False)  # a drawn sample is never redrawn in place
        (args.out / 'sample.json').write_text(json.dumps(sample, indent=1, sort_keys=True) + '\n', encoding='utf-8')
        (args.out / 'annotations.json').write_text(json.dumps(SR.template(sample), indent=1) + '\n', encoding='utf-8')
        print(json.dumps({'sample_sha256': sample['sample_sha256'], 'shortfall': sample['shortfall'],
                          'strata': {n: {'candidates': r['candidates'], 'selected': len(r['selected'])}
                                     for n, r in sample['strata'].items()}}, indent=1))
        return 0
    sample = json.loads(args.sample.read_bytes())
    summary = SR.validate(sample, json.loads(args.annotations.read_bytes()))
    print(json.dumps({'annotations_sha256': hashlib.sha256(args.annotations.read_bytes()).hexdigest(), **summary},
                     indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
