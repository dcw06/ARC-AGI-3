"""The registered two-session analysis on the successor runtime: run/final.py's rules, unchanged, over this runtime's
retained outputs (hand-written wrapper). The only source of scientific results.

Only the inputs differ from run/final.py: each session's output tree is the verified lifecycle's evidence folder, its
run log lives under study/run/, and its independent evaluation is successor/evaluate.py (the verified lifecycle's
receipts plus run/evaluate.py's call checks). Everything that decides whether and how to analyse is run/final.py's:
`refusals` (both sessions, each once, registered frozen sets, shared commitments, the 0-11 group split, withheld and
live by default, bound and technically complete evaluations, recomputed technical validity) and `pooled_analysis`
(pass-1 answers of both sessions pooled into protocol.analyze_rows, both repeats into one stability report).

The registered frozen-set hashes default to the session protocols' bindings (`experiment.frozen_set_sha256`), which
the review lock and the approvals cover.

    python -m research.evidence_memory_v1.successor.final --session A <output_a> --session B <output_b> [--rehearsal]
"""
import argparse
import hashlib
import json
from pathlib import Path

from research.evidence_memory_v1.run import final as RF
from research.evidence_memory_v1.successor import evaluate as EV
from research.evidence_memory_v1.successor import plan as PL

ROOT = Path(__file__).resolve().parents[3]
RUN_FILES = {'run_manifest': 'study/run/manifest.json', 'run_calls': 'study/run/calls.jsonl',
             'run_index': 'study/run/run.json'}
EVALUATOR_SOURCES = tuple('research/evidence_memory_v1/' + name for name in (
    'successor/evaluate.py', 'successor/final.py', 'successor/plan.py', 'run/evaluate.py', 'run/score.py',
    'run/evidence.py', 'run/probes.py', 'run/schedule.py', 'run/service.py', 'run/transport.py', 'run/final.py',
    'protocol.py', 'readers.py', 'stage1.py'))


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inputs_digest(output, frozen_bytes, root=ROOT):
    """The exact inputs of one session's evaluation and pooling: every retained file, the run log, the frozen set
    and the evaluator's sources."""
    output = Path(output)
    files = sorted(p for p in output.rglob('*') if p.is_file())
    tree = hashlib.sha256(json.dumps([[p.relative_to(output).as_posix(), _sha(p)] for p in files],
                                     separators=(',', ':')).encode()).hexdigest()
    evaluator = hashlib.sha256(json.dumps([[name, _sha(Path(root) / name)] for name in EVALUATOR_SOURCES],
                                          separators=(',', ':')).encode()).hexdigest()
    run = {name: (_sha(output / rel) if (output / rel).is_file() else None) for name, rel in RUN_FILES.items()}
    return {'output_tree': tree, **run, 'frozen_set': hashlib.sha256(frozen_bytes).hexdigest(),
            'evaluator_source': evaluator}


def retained_run(output):
    from research.evidence_memory_v1.run.evidence import load_verified
    return load_verified(Path(output) / 'study/run')


def evaluate_session(label, output, *, mode='live', rehearsal_limits=None, root=ROOT, frozen_path=None,
                     evaluator=EV.evaluate_output, loader=retained_run):
    """One session, independently evaluated here on exactly these inputs, and bound to them."""
    package = PL.SESSIONS[label]['package']
    raw = Path(frozen_path or Path(root) / package / PL.FROZEN_NAME).read_bytes()
    frozen, digest = json.loads(raw), hashlib.sha256(raw).hexdigest()
    before = inputs_digest(output, raw, root)
    technical = evaluator(output, label, mode=mode, rehearsal_limits=rehearsal_limits, root=root,
                          frozen=(frozen, digest))
    session = {'label': label, 'frozen': frozen, 'frozen_sha256': digest, 'technical': technical}
    try:
        run = loader(output)
        session.update(run_probe_set_sha256=run.get('probe_set_sha256'), passes=RF.scored_passes(frozen, run))
    except Exception as exc:  # evidence that does not verify yields no answers; the session is then refused
        session.update(run_probe_set_sha256=None, passes={}, load_error=type(exc).__name__ + ': ' + str(exc)[:200])
    session.update(evaluated_inputs=before, inputs=inputs_digest(output, raw, root))
    return session


def registered_binding(root=ROOT):
    """{label: frozen-set SHA-256} as each session's reviewed protocol registers it."""
    return {label: EV.session_protocol(root, label)[0]['experiment']['frozen_set_sha256'] for label in PL.SESSIONS}


def pooled_analysis(sessions, binding=None, require_withheld=True, root=ROOT, **kwargs):
    return RF.pooled_analysis(sessions, registered_binding(root) if binding is None else binding,
                              require_withheld=require_withheld, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--session', nargs=2, action='append', default=[], metavar=('LABEL', 'OUTPUT'))
    parser.add_argument('--rehearsal', action='store_true', help='evaluate rehearsal outputs (stand-in only)')
    args = parser.parse_args()
    mode = 'rehearsal' if args.rehearsal else 'live'
    sessions = []
    for label, output in args.session:
        limits = None
        if args.rehearsal:
            import importlib
            limits = importlib.import_module(PL.SESSIONS[label]['module'] + '.rehearsal').rehearsal_limits(ROOT)
        sessions.append(evaluate_session(label, output, mode=mode, rehearsal_limits=limits))
    result = pooled_analysis(sessions, require_withheld=mode == 'live')
    print(json.dumps(result, indent=1))
    raise SystemExit(0 if result['status'] == 'analysed' else 2)


if __name__ == '__main__':
    main()
