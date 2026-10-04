"""The registered two-session Stage 1 analysis (hand-written). The only source of scientific results.

`pooled_analysis(sessions, binding)` refuses (`status: refused`, reasons only: no accuracy, contrast, stability or
verdict) unless:
- exactly two sessions are given, labelled A and B, each once;
- each session's frozen question set hashes to the value registered for that label in `binding` (the package's
  registered frozen-set hashes), and names that session itself;
- both frozen sets share one seed commitment, case source, version, model, window and horizons, their groups are
  disjoint and together cover groups 0-11, and their probes are disjoint;
- (by default) the case source is `withheld`; the development stand-in is accepted only with
  `require_withheld=False`, for rehearsal, and the result is labelled so;
- each session's retained run names its frozen set (`run_probe_set_sha256`), its independent evaluation is
  technically complete, and its technical status, recomputed here from the retained answers, is
  `session_technically_valid` (every scheduled call answered; invalid answers at most 2% per arm).
Only then are both sessions' pass-1 answers pooled into one analysis (protocol.analyze_rows: the primary endpoint,
both contrasts, the restricted representation contrast, diagnostics, conclusions) and both repeats into one
stability report. The analysis runs once, on the pool; no per-session scientific result is ever produced.

    python -m research.evidence_memory_v1.run.final --binding binding.json \\
        --session A evaluation_a.json frozen_a.json output_a --session B evaluation_b.json frozen_b.json output_b
(POSIX: it reads the retained call logs with the reviewed evidence loader.)
"""
import argparse
import hashlib
import json
from pathlib import Path

from research.evidence_memory_v1 import protocol as P
from research.evidence_memory_v1 import stage1 as ST
from research.evidence_memory_v1.run import score as SC

SHARED = ('seed_sha256', 'case_source', 'version', 'model', 'window', 'horizons')


def frozen_sha256(frozen):
    return hashlib.sha256(ST.encode(frozen)).hexdigest()


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
        if s.get('run_probe_set_sha256') != digest:
            reasons.append(f'session {label}: the retained run names a different frozen set')
        technical = s.get('technical') or {}
        if technical.get('technically_complete') is not True:
            reasons.append(f'session {label}: the independent evaluation is not technically complete')
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
            'sessions': {s['label']: s['frozen_sha256'] for s in sessions},
            'analysis': analysis, 'stability': P.stability(rows['pass_1'], rows['pass_2']),
            'verdict': analysis['conclusions']['verdict']}


def load_session(label, evaluation_path, frozen_path, output):
    """One session from its saved independent evaluation, frozen set and retained run (POSIX loader)."""
    from research.action_effect_history_v1.service import request_hash
    from research.evidence_memory_v1.run.evidence import load_verified
    raw = Path(frozen_path).read_bytes()
    frozen = json.loads(raw)
    run = load_verified(Path(output) / 'worker/run')
    contexts = {c['context_id']: c for c in frozen['contexts']}
    probes = {p['probe_id']: p for p in frozen['probes']}
    passes = {'pass_1': {}, 'pass_2': {}}
    for call in run['calls']:
        probe = probes.get(call.get('probe_id'))
        if probe is None or call.get('request_sha256') != request_hash(ST.build_request(contexts[probe['context_id']], probe)):
            raise ValueError(f'session {label}: a retained call does not match the frozen set')
        if call.get('status') != 'answered':
            continue
        passes[call['pass_id']][call['probe_id']] = (
            SC.score(probe, call['response']) if call.get('finish_reason') == 'stop'
            else {'probe_id': probe['probe_id'], 'valid': False, 'correct': False, 'error': 'truncated'})
    return {'label': label, 'frozen': frozen, 'frozen_sha256': hashlib.sha256(raw).hexdigest(),
            'run_probe_set_sha256': run.get('probe_set_sha256'),
            'technical': json.loads(Path(evaluation_path).read_bytes()), 'passes': passes}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--binding', type=Path, required=True)
    parser.add_argument('--session', nargs=4, action='append', default=[],
                        metavar=('LABEL', 'EVALUATION', 'FROZEN', 'OUTPUT'))
    args = parser.parse_args()
    binding = json.loads(args.binding.read_bytes())
    sessions = [load_session(*spec) for spec in args.session]
    result = pooled_analysis(sessions, binding)
    print(json.dumps(result, indent=1))
    raise SystemExit(0 if result['status'] == 'analysed' else 2)


if __name__ == '__main__':
    main()
