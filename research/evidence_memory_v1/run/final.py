"""The registered two-session Stage 1 analysis (hand-written). The only source of scientific results.

Each session is independently evaluated HERE, on its exact retained output and its own frozen set
(`evaluate_session`): the derived evaluator (lifecycle receipts, server evidence, call order, request hashes,
timing, token parity, cancellations, technical completeness) runs with that session's frozen set, and the result is
bound to a digest of its inputs taken before and after evaluation: every file in the output tree, the run manifest,
call log and run index, the frozen set, and the evaluator's source. No evaluation is ever accepted from outside.

`pooled_analysis(sessions, binding)` refuses (`status: refused`, reasons only: no accuracy, contrast, stability or
verdict) unless:
- exactly two sessions are given, labelled A and B, each once;
- each session's frozen set hashes to the value registered for that label in `binding`, and names that session;
- both frozen sets share one seed commitment, case source, version, model, window and horizons, split groups 0-11
  and share no probes;
- (by default) the case source is `withheld` and the evaluation mode `live`; the development stand-in and rehearsal
  evaluations are accepted only with `require_withheld=False`, and the result is labelled so;
- each session's evaluation is bound to exactly the inputs being pooled (the evaluated-input digest equals the
  current one, and names the same frozen set), so a stale or substituted successful evaluation is refused;
- each evaluation is technically complete with a complete run, and each retained run names its frozen set;
- each session's technical status, recomputed here from the retained answers, is `session_technically_valid`
  (every scheduled call answered; invalid answers at most 2% per arm in every pass).
Only then are both sessions' pass-1 answers pooled into one analysis (protocol.analyze_rows) and both repeats into one
stability report. The analysis runs once, on the pool; no per-session scientific result is ever produced.

    python -m research.evidence_memory_v1.run.final --binding binding.json \\
        --session A frozen_a.json output_a --session B frozen_b.json output_b [--rehearsal-seconds N]
(POSIX: the evaluator and the evidence loader are the reviewed stack's.)
"""
import argparse
import contextlib
import hashlib
import json
from pathlib import Path

from research.evidence_memory_v1 import protocol as P
from research.evidence_memory_v1 import stage1 as ST
from research.evidence_memory_v1.run import score as SC

SHARED = ('seed_sha256', 'case_source', 'version', 'model', 'window', 'horizons')
RUN_FILES = {'run_manifest': 'worker/run/manifest.json', 'run_calls': 'worker/run/calls.jsonl',
             'run_index': 'worker/run/run.json'}
EVALUATOR_SOURCES = ('evaluate.py', 'score.py', 'evidence.py', 'probes.py', 'schedule.py', 'service.py', 'final.py')


def frozen_sha256(frozen):
    return hashlib.sha256(ST.encode(frozen)).hexdigest()


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inputs_digest(output, frozen_bytes):
    """The exact inputs of one session's evaluation and pooling."""
    output = Path(output)
    files = sorted(p for p in output.rglob('*') if p.is_file())
    tree = hashlib.sha256(json.dumps([[p.relative_to(output).as_posix(), _sha(p)] for p in files],
                                     separators=(',', ':')).encode()).hexdigest()
    here = Path(__file__).parent
    evaluator = hashlib.sha256(json.dumps([[name, _sha(here / name)] for name in EVALUATOR_SOURCES],
                                          separators=(',', ':')).encode()).hexdigest()
    run = {name: (_sha(output / rel) if (output / rel).is_file() else None) for name, rel in RUN_FILES.items()}
    return {'output_tree': tree, **run, 'frozen_set': hashlib.sha256(frozen_bytes).hexdigest(),
            'evaluator_source': evaluator}


@contextlib.contextmanager
def _frozen_for_evaluation(frozen, digest):
    """Run the derived evaluator against this session's frozen set (it reads run.probes.load_frozen at call time)."""
    from research.evidence_memory_v1.run import probes
    original = probes.load_frozen
    probes.load_frozen = lambda path=None: (frozen, digest)
    try:
        yield
    finally:
        probes.load_frozen = original


def independent_evaluation(output, frozen, digest, mode, rehearsal_seconds):
    from research.evidence_memory_v1.run.evaluate import evaluate_output
    with _frozen_for_evaluation(frozen, digest):
        return evaluate_output(output, mode=mode, rehearsal_seconds=rehearsal_seconds)


def retained_run(output):
    from research.evidence_memory_v1.run.evidence import load_verified
    return load_verified(Path(output) / 'worker/run')


def scored_passes(frozen, run):
    from research.action_effect_history_v1.service import request_hash
    contexts = {c['context_id']: c for c in frozen['contexts']}
    probes = {p['probe_id']: p for p in frozen['probes']}
    passes = {'pass_1': {}, 'pass_2': {}}
    for call in run['calls']:
        probe = probes.get(call.get('probe_id'))
        if probe is None or call.get('request_sha256') != request_hash(ST.build_request(contexts[probe['context_id']], probe)):
            raise ValueError('a retained call does not match the frozen set')
        if call.get('status') != 'answered':
            continue
        passes[call['pass_id']][call['probe_id']] = (
            SC.score(probe, call['response']) if call.get('finish_reason') == 'stop'
            else {'probe_id': probe['probe_id'], 'valid': False, 'correct': False, 'error': 'truncated'})
    return passes


def evaluate_session(label, frozen_path, output, *, mode='live', rehearsal_seconds=None,
                     evaluator=independent_evaluation, loader=retained_run):
    """One session, independently evaluated on exactly these inputs and bound to them."""
    raw = Path(frozen_path).read_bytes()
    frozen = json.loads(raw)
    digest = hashlib.sha256(raw).hexdigest()
    before = inputs_digest(output, raw)
    technical = evaluator(output, frozen, digest, mode, rehearsal_seconds)
    run = loader(output)
    passes = scored_passes(frozen, run)
    after = inputs_digest(output, raw)
    return {'label': label, 'frozen': frozen, 'frozen_sha256': digest,
            'run_probe_set_sha256': run.get('probe_set_sha256'), 'passes': passes,
            'technical': technical, 'evaluated_inputs': before, 'inputs': after}


def refusals(sessions, binding, require_withheld=True):
    """Every reason the pooled analysis must not run; an empty list means it may."""
    reasons = []
    labels = [s.get('label') for s in sessions]
    if len(sessions) != 2 or sorted(labels) != sorted(ST.SESSIONS):
        reasons.append(f'both sessions {sorted(ST.SESSIONS)} are required, each exactly once (given {labels})')
    for s in sessions:
        label, frozen = s.get('label'), s.get('frozen') or {}
        digest = frozen_sha256(frozen) if frozen else None
        if s.get('frozen_sha256') != digest:
            reasons.append(f'session {label}: the frozen set does not match its stated hash')
        if label not in binding or binding[label] != digest:
            reasons.append(f'session {label}: the frozen set is not the one registered for session {label}')
        if frozen.get('session') != label:
            reasons.append(f'session {label}: the frozen set names session {frozen.get("session")}')
        if require_withheld and frozen.get('case_source') != 'withheld':
            reasons.append(f'session {label}: case source {frozen.get("case_source")!r} is not withheld')
        evaluated, current = s.get('evaluated_inputs'), s.get('inputs')
        if not evaluated or not current or evaluated != current:
            reasons.append(f'session {label}: the independent evaluation is not bound to the inputs being pooled')
        elif current.get('frozen_set') != digest:
            reasons.append(f'session {label}: the evaluated inputs name a different frozen set')
        technical = s.get('technical') or {}
        if technical.get('technically_complete') is not True or (technical.get('run') or {}).get('status') != 'complete':
            reasons.append(f'session {label}: the independent evaluation is not technically complete')
        if require_withheld and technical.get('mode') != 'live':
            reasons.append(f'session {label}: the evaluation mode is {technical.get("mode")!r}, not live')
        if s.get('run_probe_set_sha256') != digest:
            reasons.append(f'session {label}: the retained run names a different frozen set')
        if frozen and frozen.get('schedule'):
            status = SC.technical(frozen, s.get('passes') or {})['technical_status']
            if status != 'session_technically_valid':
                reasons.append(f'session {label}: recomputed technical status is {status}')
    frozen_sets = [s.get('frozen') or {} for s in sessions]
    if len(frozen_sets) == 2 and all(frozen_sets):
        a, b = frozen_sets
        for name in SHARED:
            if a.get(name) != b.get(name):
                reasons.append(f'the two sessions differ in {name}')
        groups = [set(f.get('groups', ())) for f in frozen_sets]
        if groups[0] & groups[1] or groups[0] | groups[1] != set(range(ST.GROUPS_PER_FAMILY)):
            reasons.append('the two sessions do not split groups 0-11 between them')
        ids = [{p['probe_id'] for p in f.get('probes', ())} for f in frozen_sets]
        if ids[0] & ids[1]:
            reasons.append('the two sessions share probes')
    return reasons


def pooled_rows(sessions):
    """{pass id: rows} over both sessions (each session's rows from its own frozen set)."""
    pooled = {'pass_1': [], 'pass_2': []}
    for s in sorted(sessions, key=lambda s: s['label']):
        for pass_id, rows in SC.rows_by_pass(s['frozen'], s['passes']).items():
            pooled[pass_id] += rows
    return pooled


def pooled_analysis(sessions, binding, require_withheld=True, resamples=P.BOOTSTRAP_RESAMPLES):
    reasons = refusals(sessions, binding, require_withheld)
    if reasons:
        return {'status': 'refused', 'reasons': reasons}
    rows = pooled_rows(sessions)
    by_arm = {arm: [r for r in rows['pass_1'] if r['arm'] == arm] for arm in SC.ARMS}
    analysis = P.analyze_rows(by_arm, resamples=resamples)
    return {'status': 'analysed', 'case_source': sessions[0]['frozen']['case_source'],
            'sessions': {s['label']: {'frozen_sha256': s['frozen_sha256'], 'inputs': s['inputs']} for s in sessions},
            'analysis': analysis, 'stability': P.stability(rows['pass_1'], rows['pass_2']),
            'verdict': analysis['conclusions']['verdict']}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--binding', type=Path, required=True)
    parser.add_argument('--session', nargs=3, action='append', default=[], metavar=('LABEL', 'FROZEN', 'OUTPUT'))
    parser.add_argument('--rehearsal-seconds', type=int, help='evaluate rehearsal outputs (stand-in only)')
    args = parser.parse_args()
    binding = json.loads(args.binding.read_bytes())
    mode = 'rehearsal' if args.rehearsal_seconds else 'live'
    sessions = [evaluate_session(label, frozen, output, mode=mode, rehearsal_seconds=args.rehearsal_seconds)
                for label, frozen, output in args.session]
    result = pooled_analysis(sessions, binding, require_withheld=mode == 'live')
    print(json.dumps(result, indent=1))
    raise SystemExit(0 if result['status'] == 'analysed' else 2)


if __name__ == '__main__':
    main()
