"""Frozen decision rules for progress_subgoal_v1 (hash-pinned; committed before any triggering result is examined).

`snapshot()` collects every decision rule from the code that applies it: readiness criteria, family labels, the
over-claim gates (members, affirmative answers, floors, cap), validity and uncertainty thresholds, coverage floors and
selection targets, the arms, the third-arm trigger (including what happens when WS3 v1's result is unavailable), the
evaluation-seed procedure and the package limits. FROZEN is that snapshot as committed; RULES_SHA256 pins its bytes.
Tests require the code to keep producing exactly the frozen rules and the file to keep its pinned hash, so a rule can
change only by a new, visible revision.
"""
import hashlib
import json
from pathlib import Path

VERSION = 'progress_subgoal_v1_decision_rules_r1'
FROZEN = Path(__file__).with_name('decision_rules.json')
RULES_SHA256 = '38c8de63a875e54949fc0ecede9c0dd2b0b603901aad4a3f8348fd6b92089af2'

THIRD_ARM_RULE = {
    'decided': 'after this file is committed, by reading only the WS3 v1 frozen evaluator output (withheld partition), '
               'and recorded in its own commit before the evaluation seed is drawn',
    'add_raw_evidence_arm_only_if': {
        'all_of': ['WS3 v1 evaluator output exists and reports technically_complete == true'],
        'and_any_of': [
            'family claim_progress or claim_causal: candidate-minus-reference paired 95% upper bound < 0',
            'family claim_progress or claim_causal: candidate both-pass accuracy more than 0.05 below the reference',
            'gate false_progress or unsupported_causal_claim: status differs between the two WS3 arms'],
    },
    'otherwise': 'keep_two_arms',
    'otherwise_explicitly_includes': [
        'WS3 v1 has not run or its result is unavailable',
        'WS3 v1 result incomplete',
        'WS3 v1 evidence recovered from an interrupted write',
        'WS3 v1 not technically complete'],
    'limitation_when_not_added': 'the computed-vs-raw comparison is not made on these cases; WS3 v1 (if it runs) '
                                 'remains the only evidence on it',
    'if_added': 'two sessions, each a paired two-arm comparison (raw_evidence vs raw_plus_computed_record; '
                'raw_plus_computed_record vs raw_plus_computed_record_plus_safeguard); arm A repeated',
}
EVALUATION_SEED_RULE = {
    'source': 'secrets.token_bytes(16) (operating-system CSPRNG), hex-encoded: a fresh 128-bit value',
    'drawn': 'after the freeze commit and after the third-arm decision commit',
    'committed': 'only its SHA-256 (of the hex string) and the retention arrangement; the seed itself is never '
                 'committed and is kept outside the repository',
    'use': "questions.build('evaluation', seed=<hex>) and fixtures.generate('evaluation', seed=<hex>, count=30)",
}
PACKAGE_LIMITS = {'sessions': 1, 'maximum_reservation_seconds_per_session': 3600, 'internal_seconds': 3300,
                  'admission_cutoff_seconds': 3000, 'cleanup_reserve_seconds': 300, 'automatic_retries': 0,
                  'maximum_attempts': 1, 'retry_allowance_approved': False,
                  'note': 'estimated runtime is not an authorization ceiling'}


def snapshot():
    from research.evidence_comprehension_v1 import score as S1
    from research.progress_subgoal_v1 import fixtures as F, questions as Q, score as SC
    return {
        'version': VERSION,
        'arms': {'primary': list(Q.PRIMARY_CONDITIONS), 'all': list(Q.ALL_CONDITIONS),
                 'comparisons': {k: list(v) for k, v in Q.COMPARISONS.items()},
                 'system_prompts': Q.SYSTEM_PROMPTS},
        'families': {f: {'answers': Q.ANSWERS[f], 'level': Q.LEVEL[f], 'role': Q.ROLE_OF[f],
                         'uncertain_answer': Q.UNCERTAIN.get(f)} for f in Q.FAMILIES},
        'family_label': {'criterion_accuracy': S1.CRITERION, 'accuracy_floor': S1.ACCURACY_FLOOR,
                         'min_shortcut_disagreement': S1.MIN_SHORTCUT_DISAGREEMENT,
                         'non_diagnostic_best_shortcut': S1.NON_DIAGNOSTIC,
                         'scoring_unit': 'correct in both passes on the decision partition; invalid is incorrect'},
        'over_claim_gates': {g: {'members': [[fam, claim, list(keys)] for fam, claim, keys in spec['members']],
                                 'affirmative': spec['affirmative'], 'valid_opportunity_floor': Q.GATE_FLOORS[g]}
                             for g, spec in Q.OVER_CLAIM_GATES.items()},
        'over_claim_rule': {'cap': SC.OVER_CLAIM_CAP, 'unit': 'contexts',
                            'opportunity': 'a context with a member question that has at least one valid answer',
                            'over_claim': 'a valid affirmative answer to a member question in either pass',
                            'invalid_answers': 'never over-claims; incorrect and counted against validity',
                            'below_floor_status': 'insufficient_valid_opportunities (never a pass)'},
        'validity': {'all_responses_invalid_rate_cap': SC.INVALID_RATE_CAP,
                     'gate_member_responses_invalid_rate_cap': SC.GATE_MEMBER_INVALID_RATE_CAP},
        'uncertainty': {'recall_floor': SC.UNCERTAINTY_RECALL_FLOOR, 'over_hedge_cap': SC.OVER_HEDGE_CAP},
        'readiness': {'eligible_requires': [
            'every decision-partition primary and over-claim-gate answer present in both passes',
            'run evidence not recovered from an interrupted write',
            'both validity caps met',
            'every primary family criterion_met',
            'every over-claim gate passes (floor of valid opportunities and rate <= cap)',
            'uncertainty recall >= floor and over-hedging <= cap'],
            'incomplete_if': ['a required answer is missing', 'recovered evidence'],
            'use': 'only an eligible arm may feed memory or supervision; gameplay connection is outside this protocol'},
        'coverage': {'floors': Q.FLOORS, 'gate_floors': Q.GATE_FLOORS, 'critical_classes': list(Q.CRITICAL_CLASSES),
                     'targets': Q.TARGET, 'target_factor': Q.TARGET_FACTOR,
                     'group_target': {f'{k[0]}:{k[1]}': v for k, v in Q.GROUP_TARGET.items()},
                     'evaluation_count_per_family': F.EVALUATION_COUNT,
                     'family_weights': F.WEIGHT},
        'third_arm_rule': THIRD_ARM_RULE,
        'evaluation_seed_rule': EVALUATION_SEED_RULE,
        'package_limits': PACKAGE_LIMITS,
    }


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=1) + '\n').encode()


if __name__ == '__main__':
    raw = encode(snapshot())
    FROZEN.write_bytes(raw)
    print(hashlib.sha256(raw).hexdigest())
