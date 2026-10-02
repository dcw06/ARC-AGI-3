"""Stage 1 instruments for reports/evidence_memory_v1_protocol_v2.md (Track 2). No model is called; CPU only.

The model is the reader only. Memory is written by the deterministic faithful writer (writers.Faithful), so Stage 1
tests memory access and representation, not the model's ability to write faithful memory or to complete levels.
The phenomenon measured is loss of access under a restricted context, not necessarily forgetting inside the model.

Contents:
- the reader prompt frame, identical for every arm (one system message describing both package formats);
- evidence-age classes per question (recent / old / mixed / none) against the frozen window;
- recent-control questions: the latest fact in each trajectory whose evidence lies entirely inside the window;
- package-relative truth and per-answer scoring flags (truth-relative and package-relative correctness, unsupported
  assertions, abstentions);
- metrics with exact denominators, aggregated per (family, group), the unit of analysis;
- the primary endpoint (old-evidence factual accuracy under the common token budget), the two predeclared paired
  contrasts, the availability-restricted representation contrast, diagnostics, and a stratified cluster bootstrap;
- token measurement with the pinned tokenizer (tokens.Tokenizer) and the runtime estimate from the measured v3 fit.
"""
import hashlib
import json
import random
import statistics

from research.evidence_memory_v1 import fidelity as F, readers as RD, render as R, schema as S, trajectories as TR, \
    writers as W

ARMS = ('recent_raw', 'state_keyed_raw', 'memory')  # the primary comparison, one common token budget per trajectory
REFERENCE = 'full_history'  # diagnostic only: receives more context; excluded from the primary comparison
HORIZONS = (0, 4, 8, 16)  # distractor delays; 0 = recent evidence, 8 and 16 = old evidence, 4 = transition
RECENT_DELAY, OLD_DELAYS = 0, (8, 16)
VALUES = ('no_observed_change', 'changed_then_returned', 'final_frame_differs')
MAX_TOKENS = 64

# v3 live attempt, cache disabled, same serving stack (scripts/audit_ws3_questionnaire_tokens.py `measurements`,
# recorded in reports/ws3_questionnaire_token_audit.json): seconds per call, per prompt token, per completion token.
FIT = {'per_call': 0.039443079084717836, 'per_prompt_token': 1.4210487578923021e-05,
       'per_completion_token': 0.006418344384022718}
OVERHEAD_ALLOWANCE = {'installation': 282, 'model_startup': 1228, 'other_pre_question': 30,
                      'post_question_finalization': 30}  # the same report's allowance (worse of v2/v3, with factors)
ADMISSION_CUTOFF_SECONDS = 3000

# Decision constants (provisional, protocol v2 §9). None is a model-quality claim.
COMPREHENSION_FLOOR = 0.80  # pilot interpretability floor, not proof of a cause when failed
FORGETTING_DIAGNOSTIC = 0.15  # diagnostic threshold only, never the advancement gate
UNSUPPORTED_MARGIN_POINT, UNSUPPORTED_MARGIN_UPPER = 0.02, 0.05
BOOTSTRAP_SEED, BOOTSTRAP_RESAMPLES = 'evidence-memory-v1-stage1-bootstrap', 10000
CONTRASTS = (('memory', 'recent_raw'), ('memory', 'state_keyed_raw'))  # the two predeclared contrasts

SYSTEM = (
    'You answer questions about evidence from one episode of a grid game. Use only the supplied evidence; do not '
    'guess. The evidence is either transition records or memory entries.\n'
    'A transition record line gives: step, level, segment, state (the first characters of the hash of the frame '
    'before the action), the action, the dispatch status, the visual effect over the returned frames, and the '
    'reported environment events. A visual effect of indeterminate means the outcome was not observed.\n'
    'A memory entry line gives: an id, kind/status, a claim (an action, an effect and where it holds), the steps '
    'of its evidence and counterevidence, and the step it was last reviewed. An observation states what the cited '
    'steps showed in one exact state. A hypothesis is a generalisation; contradicted means a cited step refuted it.\n'
    'States are identified by hash prefixes: a state matches when one prefix starts with the other.\n'
    'Return only one compact JSON object matching the requested answer form, with no rationale or Markdown.')


def question_text(question):
    where = f"the exact state {question['state'][:10]} at level {question['level']}"
    if question['kind'] == 'recall':
        return (f"Question: in {where}, which visual effects have been observed for "
                f"{R.action_text(question['action'])}?\n"
                f'Answer form: {{"values": [...]}} with one or more of {", ".join(VALUES)}; or {{"values": '
                f'["no_evidence"]}} if the evidence shows no observed outcome of this action in this exact state.')
    return (f"Question: the current state is {where}. Goal: {question['goal']}.\n"
            f"Candidates: {json.dumps(question['candidates'], sort_keys=True, separators=(',', ':'))}\n"
            f'Answer form: {{"choice": <one candidate exactly as listed>}}.')


def reader_messages(package_text, question):
    """The chat messages for one reader call; identical in form for every arm."""
    return [{'role': 'system', 'content': SYSTEM},
            {'role': 'user', 'content': 'Evidence:\n' + (package_text or '(none)') + '\n\n' + question_text(question)}]


def _actions(question):
    return [question['action']] if question['kind'] == 'recall' else question['candidates']


def evidence_class(records, question, window=RD.WINDOW):
    """'recent' when every observed outcome bearing on the question lies in the last `window` transitions, 'old'
    when none does, 'mixed' otherwise, 'none' when no observed outcome bears on it."""
    known = F.facts(records)
    steps = [f['step'] for f in known.values() if f['level'] == question['level'] and f['state'] == question['state']
             and f['action'] in _actions(question) and f['visual'] is not None]
    if not steps:
        return 'none'
    first_recent = len(records) - window
    inside = [s >= first_recent for s in steps]
    return 'recent' if all(inside) else 'old' if not any(inside) else 'mixed'


def recent_control(trajectory, window=RD.WINDOW):
    """A recall question about the latest observed fact whose evidence lies entirely in the window, or None."""
    records = trajectory['records']
    idx = S.index(records)
    for record in reversed(records[-window:]):
        info = idx[S.record_key(record)]
        if info['visual'] is None:
            continue
        question = {'kind': 'recall', 'level': info['level'], 'state': info['state'], 'action': info['action'],
                    'control': 'recent'}
        if evidence_class(records, question, window) == 'recent':
            return question
    return None


def questions(trajectory):
    """Scheduled questions: the family questions, then the recent control (answers never included)."""
    out = [{**{k: v for k, v in q.items() if k != 'expected_answer'}, 'control': 'family'}
           for q in trajectory['evaluator_only']['expected']['questions']]
    control = recent_control(trajectory)
    return out + ([control] if control else [])


def arm_contents(trajectory, memory, measure):
    """{arm: (rendered evidence, package records or memory entries)} under the common budget, plus the reference."""
    idx = S.index(trajectory['records'])
    p = RD.packages(trajectory, memory, measure=measure)
    return p, {'recent_raw': (R.records_text(p['recent_raw']['records'], idx), p['recent_raw']['records']),
               'state_keyed_raw': (R.records_text(p['state_keyed_raw']['records'], idx), p['state_keyed_raw']['records']),
               'memory': (R.memory_text(p['memory']['entries']), p['memory']['entries']),
               REFERENCE: (R.records_text(trajectory['records'], idx), trajectory['records'])}


def package_truth(arm, content, question):
    """What the package itself supports: the answer an exact reader of only this package would give."""
    if arm == 'memory':
        values = lambda a: RD._memory_values(content, question, a)
    else:
        values = lambda a: [v for v in F.gold(content, {**question, 'kind': 'recall', 'action': a}) if v != 'no_evidence']
    if question['kind'] == 'recall':
        return values(question['action']) or ['no_evidence']
    changed = [c for c in question['candidates'] if 'final_frame_differs' in values(c)]
    return changed or [c for c in question['candidates'] if 'no_observed_change' not in values(c)]


def score(output, question, truth, package):
    """Flags for one answer. Invalid outputs (response schema, readers.validate_response) are retained and never
    correct, unsupported or abstaining."""
    result = RD.score(output, question, truth)
    flags = {'valid': result['valid'], 'correct_truth': result['correct'], 'correct_package': False,
             'unsupported': False, 'abstained': False}
    if not result['valid']:
        return {**flags, 'answer': 'invalid:' + str(output), 'output': output, 'error': result['error']}
    answer = json.loads(output)
    flags['answer'] = json.dumps(answer, sort_keys=True, separators=(',', ':'))
    if question['kind'] == 'recall':
        values = answer['values']
        flags['correct_package'] = sorted(values) == sorted(package)
        flags['abstained'] = values == ['no_evidence']
        flags['unsupported'] = any(v != 'no_evidence' and v not in package for v in values)
    else:
        flags['correct_package'] = answer['choice'] in package
    return flags


def rows(trajectory, arm, read, measure=len, memory=None):
    """One scored row per scheduled question for one arm; `read(messages, question)` returns the output text."""
    memory = memory or W.run_writer(W.Faithful(), trajectory)['memory']
    _, contents = arm_contents(trajectory, memory, measure)
    text, content = contents[arm]
    out = []
    for n, q in enumerate(questions(trajectory)):
        truth = F.gold(trajectory['records'], q)
        package = package_truth(arm, content, q)
        messages = reader_messages(text, q)
        out.append({'trajectory': trajectory['id'], 'family': trajectory['family'], 'group': trajectory['group'],
                    'delay': trajectory['delay'], 'arm': arm, 'question': n, 'kind': q['kind'], 'control': q['control'],
                    'evidence': evidence_class(trajectory['records'], q), 'truth': truth, 'package': package,
                    **score(read(messages, q), q, truth, package)})
    return out


def oracle_read(arm, content):
    """An exact reader of the package (information availability, not model ability)."""
    def read(messages, question):
        package = package_truth(arm, content, question)
        if question['kind'] == 'recall':
            return json.dumps({'values': package})
        return json.dumps({'choice': package[0] if package else question['candidates'][0]})
    return read


def _group_mean(rows_, keep, hit):
    """Macro mean over families of per-group means; denominators are the rows passing `keep`."""
    groups = {}
    for r in rows_:
        if keep(r):
            groups.setdefault((r['family'], r['group']), []).append(hit(r))
    if not groups:
        return None, 0, 0
    families = {}
    for (family, _), hits in groups.items():
        families.setdefault(family, []).append(sum(hits) / len(hits))
    value = statistics.mean(statistics.mean(v) for v in families.values())
    return round(value, 3), len(groups), sum(len(h) for h in groups.values())


def _factual(r):
    return r['kind'] == 'recall' and r['truth'] != ['no_evidence']


def forgetting_effect(rows_):
    """Per (family, group): accuracy on its family questions with recent evidence at delay 0 minus accuracy on its
    family questions with old evidence at delays 8 and 16; macro mean over families. Only groups with both enter.
    Returns (effect, groups, questions)."""
    recent, old = {}, {}
    for r in rows_:
        if not (_factual(r) and r['control'] == 'family'):
            continue
        key = (r['family'], r['group'])
        if r['evidence'] == 'recent' and r['delay'] == RECENT_DELAY:
            recent.setdefault(key, []).append(r['correct_truth'])
        elif r['evidence'] == 'old' and r['delay'] in OLD_DELAYS:
            old.setdefault(key, []).append(r['correct_truth'])
    both = sorted(set(recent) & set(old))
    if not both:
        return None, 0, 0
    families = {}
    for key in both:
        families.setdefault(key[0], []).append(sum(recent[key]) / len(recent[key]) - sum(old[key]) / len(old[key]))
    return (round(statistics.mean(statistics.mean(v) for v in families.values()), 3), len(both),
            sum(len(recent[k]) + len(old[k]) for k in both))


def is_old(r):
    """A primary-endpoint question: factual family recall with old evidence, at an old delay."""
    return _factual(r) and r['control'] == 'family' and r['evidence'] == 'old' and r['delay'] in OLD_DELAYS


def is_recent(r):
    return _factual(r) and r['control'] == 'family' and r['evidence'] == 'recent' and r['delay'] == RECENT_DELAY


def metrics(rows_):
    """The Stage 1 metrics for one arm's rows. Each value is (macro mean, groups, questions).
    `old_evidence_accuracy` is the primary endpoint; every other entry is a diagnostic or a reported rate."""
    factual = _factual
    return {
        'old_evidence_accuracy': _group_mean(rows_, is_old, lambda r: r['correct_truth']),
        'forgetting_effect': forgetting_effect(rows_),
        'factual_accuracy_recent_family': _group_mean(rows_, is_recent, lambda r: r['correct_truth']),
        'factual_accuracy_recent_control_at_old_delays': _group_mean(
            rows_, lambda r: factual(r) and r['control'] == 'recent' and r['delay'] in OLD_DELAYS,
            lambda r: r['correct_truth']),
        'decision_accuracy_old': _group_mean(rows_, lambda r: r['kind'] == 'decision' and r['delay'] in OLD_DELAYS
                                             and r['evidence'] in ('old', 'none'), lambda r: r['correct_truth']),
        'unsupported_rate': _group_mean(rows_, lambda r: r['kind'] == 'recall', lambda r: r['unsupported']),
        'abstention_when_package_lacks_evidence': _group_mean(
            rows_, lambda r: r['kind'] == 'recall' and r['package'] == ['no_evidence'], lambda r: r['abstained']),
        'abstention_when_package_has_evidence': _group_mean(
            rows_, lambda r: r['kind'] == 'recall' and r['package'] != ['no_evidence'], lambda r: r['abstained']),
        'reading_accuracy_package_has_evidence': _group_mean(
            rows_, lambda r: r['kind'] == 'recall' and r['package'] != ['no_evidence'], lambda r: r['correct_package']),
        'invalid_rate': _group_mean(rows_, lambda r: True, lambda r: not r['valid']),
    }


def cases(seed=TR.SEED, partition=TR.PARTITION, groups_per_family=2, horizons=HORIZONS):
    """Trajectories for every (family, group) at every horizon; a group shares its construction prefix across
    horizons (the seed depends on family and group index, not on the delay)."""
    out = []
    for family in TR.FAMILIES:
        for group in range(groups_per_family):
            for delay in horizons:
                t = TR.build(family, group, delay, seed=seed, partition=partition)
                t['group'] = group
                out.append(t)
    return out


def estimate_seconds(calls, completion='key_x2'):
    """Planning estimate from the measured v3 fit: calls are (prompt_tokens, key_completion_tokens)."""
    total = 0.0
    for prompt, key in calls:
        completion_tokens = MAX_TOKENS if completion == 'cap' else min(MAX_TOKENS, 2 * key)
        total += FIT['per_call'] + FIT['per_prompt_token'] * prompt + FIT['per_completion_token'] * completion_tokens
    return total


def key_completion(question, truth):
    answer = {'values': truth} if question['kind'] == 'recall' else {'choice': truth[0]}
    return json.dumps(answer, separators=(',', ':'))


# ---- the primary endpoint, the predeclared contrasts and the bootstrap (protocol v2 §8-§9)

def _macro(values):
    """Macro mean over families of the mean over that family's groups."""
    return statistics.mean(statistics.mean(v) for v in values.values())


def bootstrap_ci(values, resamples=BOOTSTRAP_RESAMPLES, seed=BOOTSTRAP_SEED, level=0.95):
    """Percentile interval of the macro mean: groups are resampled with replacement within each family (stratified
    cluster bootstrap). `values` is {family: [one value per group]}."""
    rng = random.Random(hashlib.sha256(seed.encode()).hexdigest())
    families = sorted(values)
    stats = sorted(statistics.mean(statistics.mean(rng.choices(values[f], k=len(values[f]))) for f in families)
                   for _ in range(resamples))
    tail = int((1 - level) / 2 * resamples)
    return [round(stats[tail], 4), round(stats[-tail - 1], 4)]


def _summary(values, questions, resamples):
    if not values:
        return {'estimate': None, 'ci95': None, 'groups': 0, 'questions': 0}
    return {'estimate': round(_macro(values), 4), 'ci95': bootstrap_ci(values, resamples),
            'groups': sum(len(v) for v in values.values()), 'questions': questions}


def arm_estimate(rows_, keep, hit=lambda r: r['correct_truth'], resamples=BOOTSTRAP_RESAMPLES):
    groups = {}
    for r in rows_:
        if keep(r):
            groups.setdefault((r['family'], r['group']), []).append(hit(r))
    values = {}
    for (family, _), hits in sorted(groups.items()):
        values.setdefault(family, []).append(sum(hits) / len(hits))
    return _summary(values, sum(len(h) for h in groups.values()), resamples)


def available(row):
    """The package supports the full-history answer: the relevant evidence is in the package."""
    return sorted(map(json.dumps, row['package'])) == sorted(map(json.dumps, row['truth']))


def paired_contrast(rows_a, rows_b, keep, hit=lambda r: r['correct_truth'], eligible=None,
                    resamples=BOOTSTRAP_RESAMPLES):
    """Arm A minus arm B on the same questions: per group, the mean difference over its paired questions; then the
    macro mean over families. `eligible(row_a, row_b)` restricts the pairs (reported as eligible / excluded)."""
    other = {(r['trajectory'], r['question']): r for r in rows_b}
    groups, considered = {}, 0
    for r in rows_a:
        b = other.get((r['trajectory'], r['question']))
        if not keep(r) or b is None:
            continue
        considered += 1
        if eligible is None or eligible(r, b):
            groups.setdefault((r['family'], r['group']), []).append(int(hit(r)) - int(hit(b)))
    values = {}
    for (family, _), diffs in sorted(groups.items()):
        values.setdefault(family, []).append(sum(diffs) / len(diffs))
    used = sum(len(d) for d in groups.values())
    return {**_summary(values, used, resamples), 'eligible_questions': used, 'excluded_questions': considered - used}


def _direction(summary, positive, negative):
    if summary['ci95'] is None:
        return 'not_estimable'
    if summary['ci95'][0] > 0:
        return positive
    if summary['ci95'][1] < 0:
        return negative
    return 'no_difference_detected'


def analyze_rows(rows_by_arm, resamples=BOOTSTRAP_RESAMPLES):
    """Endpoints, contrasts, diagnostics and conclusions from scored rows ({arm: rows}); every arm is required."""
    recall = lambda r: r['kind'] == 'recall'
    primary = {arm: arm_estimate(rows_by_arm[arm], is_old, resamples=resamples) for arm in ARMS}
    reference = arm_estimate(rows_by_arm[REFERENCE], is_old, resamples=resamples)
    memory = rows_by_arm['memory']
    contrasts = {
        'memory_vs_recent_raw': paired_contrast(memory, rows_by_arm['recent_raw'], is_old, resamples=resamples),
        'memory_vs_state_keyed_raw': paired_contrast(memory, rows_by_arm['state_keyed_raw'], is_old,
                                                     resamples=resamples),
        'memory_vs_state_keyed_raw_evidence_in_both': paired_contrast(
            memory, rows_by_arm['state_keyed_raw'], is_old, eligible=lambda a, b: available(a) and available(b),
            resamples=resamples),
    }
    unsupported = paired_contrast(memory, rows_by_arm['recent_raw'], recall, hit=lambda r: r['unsupported'],
                                  resamples=resamples)
    diagnostics = {arm: metrics(rows_by_arm[arm]) for arm in ARMS + (REFERENCE,)}
    result = {'primary_endpoint': primary, 'reference_full_history': reference, 'contrasts': contrasts,
              'unsupported_difference_memory_minus_recent_raw': unsupported, 'diagnostics': diagnostics}
    result['conclusions'] = conclusions(result)
    return result


def conclusions(result):
    """The predeclared reading of an analysis. Each conclusion stands alone: beating recent history does not show
    an advantage over retrieval, and a failed comprehension floor makes the experiment uninterpretable."""
    d = result['diagnostics']
    reading = {arm: d[arm]['reading_accuracy_package_has_evidence'][0] for arm in ARMS}
    recent = d['recent_raw']['factual_accuracy_recent_family'][0]
    interpretable = (all(v is not None and v >= COMPREHENSION_FLOOR for v in reading.values())
                     and recent is not None and recent >= COMPREHENSION_FLOOR)
    c = result['contrasts']
    u = result['unsupported_difference_memory_minus_recent_raw']
    safety = ('not_estimable' if u['ci95'] is None else
              'within_margin' if u['estimate'] <= UNSUPPORTED_MARGIN_POINT and u['ci95'][1] <= UNSUPPORTED_MARGIN_UPPER
              else 'outside_margin')
    forgetting = d['recent_raw']['forgetting_effect'][0]
    out = {
        'interpretable': interpretable,
        'comprehension': {'reading_accuracy': reading, 'recent_raw_recent_evidence_accuracy': recent,
                          'floor': COMPREHENSION_FLOOR},
        'access_vs_recent_history': _direction(c['memory_vs_recent_raw'], 'memory_preserves_access',
                                               'memory_loses_access'),
        'improvement_over_retrieval': _direction(c['memory_vs_state_keyed_raw'], 'memory_improves_over_retrieval',
                                                 'memory_worse_than_retrieval'),
        'representation_with_evidence_in_both': _direction(c['memory_vs_state_keyed_raw_evidence_in_both'],
                                                           'representation_helps', 'representation_hurts'),
        'unsupported_claims': safety,
        'loss_of_access_in_recent_history_diagnostic': None if forgetting is None else forgetting >= FORGETTING_DIAGNOSTIC,
    }
    if not interpretable:
        out['verdict'] = 'not_interpretable_cannot_isolate_retention_from_comprehension'
    elif out['access_vs_recent_history'] == 'memory_preserves_access' and safety == 'within_margin':
        out['verdict'] = ('memory_preserves_access_and_improves_over_retrieval'
                          if out['improvement_over_retrieval'] == 'memory_improves_over_retrieval'
                          else 'memory_preserves_access_not_shown_over_retrieval')
    elif out['access_vs_recent_history'] == 'memory_preserves_access':
        out['verdict'] = 'memory_preserves_access_unsupported_claims_outside_margin'
    else:
        out['verdict'] = 'access_preservation_not_shown'
    return out


def stability(pass_1_rows, pass_2_rows):
    """Response stability on the preselected repeat: the share of repeated questions answered identically. It
    measures repeatability of one deterministic configuration, not additional independent samples."""
    first = {(r['arm'], r['trajectory'], r['question']): r for r in pass_1_rows}
    by_arm = {}
    for r in pass_2_rows:
        a = first.get((r['arm'], r['trajectory'], r['question']))
        if a is not None:
            row = by_arm.setdefault(r['arm'], [0, 0])
            row[0] += a['answer'] == r['answer']
            row[1] += 1
    return {'repeated_questions': sum(v[1] for v in by_arm.values()),
            'identical': sum(v[0] for v in by_arm.values()),
            'by_arm': {arm: {'identical': v[0], 'repeated': v[1]} for arm, v in sorted(by_arm.items())}}
