"""Code review of amendment S2 (October 13, 2026): one shared trajectory identity covering policy and reflection
calls; a limitation derived from the observed counts; actual spend apart from analysis cost; launch-time records read
once with explicit validation failures; and acceptance of a sample committed under the first S2 rule text only when
the corrected rule draws it exactly. CPU only; synthetic episodes and records in temporary directories."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from research.stagnation_supervision_runtime_v2 import pooled as P, report as R, selfreview as SR
from tests import test_ssv_runtime_v2_r2_gaps as fixtures
label_population, SPEC = fixtures.label_population, fixtures.SPEC


def policy_call(n, response='r', status='valid', started=1.0):
    return {'request_sha256': f'q{n}', 'response_sha256': f'{response}{n}', 'status': status, 'finish_reason': 'stop',
            'response_bytes': 60, 'response_truncated': False, 'server_prompt_tokens': 100,
            'server_completion_tokens': 5, 'tokenizer_prompt_tokens': 100, 'pre_hash': f'h{n}',
            'started_at': started, 'returned_at': started + 0.5}


def event(index, delivered, request='rq', error=None, valid=True, latency=1.0):
    return {'action_index': index, 'outcome': 'called', 'due': True, 'delivered': delivered,
            'record_id': f'any-episode#{index}',
            'call': {'request_sha256': request, 'error': error, 'parsed': {'valid': valid}, 'latency_s': latency}}


def population():
    """label_population with call projections, so the identity sees policy calls too."""
    eps = label_population()
    for e in eps:
        e['policy_calls'] = [SR.call_projection(policy_call(n), SR.POLICY_CALL_FIELDS) for n in range(3)]
        e['reflection_calls'] = []
    return eps


def twin(eps, name):
    return next(e for e in eps if e['episode'] == name)


def block_pairs_agree(test, eps):
    """The shared identity: reproducibility, the distinct section and the draw agree pair by pair."""
    blocks = P.reproducibility(eps, SPEC, 40)['block_2_vs_block_1']
    excluded = {row['episode'] for row in SR.distinct(eps)[1]}
    test.assertEqual({row['block_2'] for row in blocks if row['identical_trajectory']}, excluded)
    sample = SR.sample_for(eps, SPEC, 40)
    test.assertEqual({row['episode'] for row in sample['amendment_s2']['duplicates_excluded']}, excluded)
    return excluded


class SharedIdentity(unittest.TestCase):
    def test_identical_actions_with_different_delivered_reflections_are_distinct(self):
        eps = population()
        a, b = twin(eps, 'b1-wa30-periodic'), twin(eps, 'b2-wa30-periodic')
        a['reflection_evidence'] = {'events': [event(9, 'try left')]}
        b['reflection_evidence'] = {'events': [event(9, 'try right')]}
        self.assertEqual([r for r in a['records']], [r for r in b['records']])  # identical actions and frames
        excluded = block_pairs_agree(self, eps)
        self.assertNotIn('b2-wa30-periodic', excluded)
        self.assertEqual(len(excluded), 11)
        self.assertEqual(P.reproducibility(eps, SPEC, 40)['distinct_main_trajectories']['wa30/periodic'], 2)

    def test_undelivered_reflections_differing_in_status_are_distinct(self):
        eps = population()
        a, b = twin(eps, 'b1-wa30-triggered'), twin(eps, 'b2-wa30-triggered')
        a['reflections'] = [{'status': 'received', 'valid': False, 'input_tokens': 10, 'output_tokens': 3, 'latency_s': 1.0}]
        b['reflections'] = [{'status': 'failed', 'valid': False, 'input_tokens': 10, 'output_tokens': 0, 'latency_s': 1.0}]
        self.assertNotIn('b2-wa30-triggered', block_pairs_agree(self, eps))
        kept = P.compute_distinct(eps, SPEC, 40)
        self.assertEqual(kept['reliability']['triggered']['failed_reflections'], 1)  # the failure is no longer hidden

    def test_policy_response_and_reflection_request_differences_are_distinct(self):
        eps = population()
        twin(eps, 'b2-ar25-continuation')['policy_calls'][1]['response_sha256'] = 'other'
        changed = twin(eps, 'b2-ar25-periodic')
        changed['reflection_calls'] = [SR.call_projection({'request_sha256': 'x', 'response_sha256': 'y',
                                                           'status': 'received'}, SR.REFLECTION_CALL_FIELDS)]
        twin(eps, 'b1-ar25-periodic')['reflection_calls'] = [SR.call_projection(
            {'request_sha256': 'x2', 'response_sha256': 'y', 'status': 'received'}, SR.REFLECTION_CALL_FIELDS)]
        excluded = block_pairs_agree(self, eps)
        self.assertNotIn('b2-ar25-continuation', excluded)
        self.assertNotIn('b2-ar25-periodic', excluded)

    def test_timing_and_identifiers_do_not_matter(self):
        eps = population()
        a, b = twin(eps, 'b1-ls20-periodic'), twin(eps, 'b2-ls20-periodic')
        a['reflection_evidence'] = {'events': [event(9, 'same', latency=1.0)]}
        b['reflection_evidence'] = {'events': [event(9, 'same', latency=9.0)]}
        a['policy_calls'] = [SR.call_projection(policy_call(n, started=1.0), SR.POLICY_CALL_FIELDS) for n in range(3)]
        b['policy_calls'] = [SR.call_projection(policy_call(n, started=50.0), SR.POLICY_CALL_FIELDS) for n in range(3)]
        a['reflections'] = [{'status': 'received', 'valid': True, 'input_tokens': 1, 'output_tokens': 1, 'latency_s': 0.1}]
        b['reflections'] = [{'status': 'received', 'valid': True, 'input_tokens': 1, 'output_tokens': 1, 'latency_s': 7.0}]
        self.assertEqual(SR.trajectory_signature(a), SR.trajectory_signature(b))
        renamed = dict(b, episode='zz-other', session='9', pair_id='p', block=7)
        self.assertEqual(SR.trajectory_signature(a), SR.trajectory_signature(renamed))
        self.assertIn('b2-ls20-periodic', block_pairs_agree(self, eps))

    def test_excluded_fields_are_documented_and_never_projected(self):
        self.assertTrue(SR.SIGNATURE_EXCLUDES['timing'] and SR.SIGNATURE_EXCLUDES['identifiers'])
        for fields in (SR.POLICY_CALL_FIELDS, SR.REFLECTION_CALL_FIELDS):
            self.assertFalse({'started_at', 'returned_at', 'latency_s', 'request', 'response'} & set(fields))
            self.assertTrue({'request_sha256', 'response_sha256', 'status'} <= set(fields))
        self.assertIn(SR.SIGNATURE_VERSION, SR.DISTINCT_RULE)


class DerivedLimitation(unittest.TestCase):
    def test_statement_follows_the_observed_counts(self):
        eps = population()
        one = P.compute_distinct(eps, SPEC, 40)['distinct_trajectories_per_game_and_arm']
        self.assertEqual(set(one.values()), {1})
        self.assertIn('one distinct trajectory per game and arm (12 in all)', P.distinct_limitation(one))
        twin(eps, 'b2-wa30-periodic')['policy_calls'][0]['response_sha256'] = 'other'
        mixed = P.compute_distinct(eps, SPEC, 40)['distinct_trajectories_per_game_and_arm']
        self.assertEqual(mixed['wa30/periodic'], 2)
        statement = P.distinct_limitation(mixed)
        self.assertIn('1 to 2 distinct trajectories per game and arm (13 in all)', statement)
        self.assertNotIn('variation between games only', statement)


class SpendDenominators(unittest.TestCase):
    def test_actual_spend_includes_repeats_and_duplicates_apart_from_analysis_cost(self):
        eps = population()
        for e in eps:
            e['reflections'] = [{'status': 'received', 'valid': True, 'input_tokens': 10, 'output_tokens': 2,
                                 'latency_s': 1.0}] if e['arm'] != 'continuation' else []
        twin(eps, 'b1-ar25-continuation')['policy_calls'].append(
            SR.call_projection(policy_call(9, status='transport_error'), SR.POLICY_CALL_FIELDS))
        spent = P.spend(eps)
        self.assertEqual((spent['episodes'], spent['repeats']), (25, 1))
        self.assertEqual(spent['policy']['calls'], 25 * 3 + 1)
        self.assertEqual(spent['policy']['charged_prompt_tokens'], 25 * 3 * 100)  # the failed call is not charged
        self.assertEqual(spent['reflection_by_arm']['by_arm']['periodic']['calls'], 8)
        distinct = P.compute_distinct(eps, SPEC, 40)
        self.assertEqual(distinct['analysis_cost']['by_arm']['periodic']['calls'], 4)
        self.assertIn('not actual spend', distinct['analysis_cost']['denominator'])
        self.assertIn('repeats and exact duplicates', spent['denominator'])
        self.assertNotIn('realised_cost', distinct)
        self.assertIn('realised_cost', distinct['not_reported_here'])


def write(path, value):
    Path(path).write_text(value if isinstance(value, str) else json.dumps(value), encoding='utf-8')
    return path


class Evaluate(unittest.TestCase):
    """evaluate_sessions with the study reports and episode rebuild mocked; every other step is real."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.current = {'technically_complete': True, 'target_accepted': True, 'endpoints': {'x': 1},
                        'review_lock': {'sha256': 'b' * 64, 'verified': True}}
        self.records = {s: write(self.folder / f'{s}.json', self.current) for s in ('1', '2')}
        self.launch = write(self.folder / 'launch.json', dict(self.current, review_lock={'sha256': 'a' * 64}))
        self.episodes = population()

    def tearDown(self):
        self.tmp.cleanup()

    def execution(self, bound):
        return write(self.folder / 'execution.json', {'session1_evaluation': {'sha256': bound}})

    def annotations(self, sample):
        record = SR.template(sample)
        for name, items in record['annotations'].items():
            for item in items:
                for field in SR.FIELDS[sample['strata'][name]['kind']]:
                    item[field] = 'unclear'
        path = write(self.folder / 'annotations.json', record)
        return path, P.sha256_file(path)

    def run_evaluate(self, *, mode='live', execution=None, launch=None, annotations=None, digest='0' * 64,
                     commitment=None):
        session1 = [e for e in self.episodes if e['session'] == '1']
        session2 = [e for e in self.episodes if e['session'] == '2']
        rehearsal = {} if mode == 'live' else {'specs': {s: {'limits': {'actions_per_episode': 40}} for s in '12'},
                                               'internal_seconds': {'1': 1, '2': 1}}
        with mock.patch.object(R, 'study_report', return_value=self.current), \
                mock.patch('research.stagnation_supervision_v1.closed_loop.bridge.session_spec',
                           return_value={'limits': {'actions_per_episode': 40}}), \
                mock.patch.object(P, 'session_episodes', side_effect=[session1, session2]):
            return P.evaluate_sessions({'1': self.folder, '2': self.folder}, self.records, mode=mode,
                                       annotations=annotations or self.folder / 'missing-annotations.json',
                                       annotations_sha256=digest, session2_execution=execution,
                                       session1_launch_record=launch, annotations_commitment=commitment, **rehearsal)

    def binding(self, result):
        return [p for p in result['problems'] if 'session' in p and 'self-review' not in p]


class LaunchRecordReading(Evaluate):
    def test_missing_malformed_or_non_object_records_are_explicit_failures(self):
        execution = self.execution(P.sha256_file(self.launch))
        for content, error in ((None, 'FileNotFoundError'), ('{"truncated": ', 'JSONDecodeError'), ('[1, 2]', 'ValueError')):
            with self.subTest(error=error):
                path = self.folder / f'launch-{error}.json'
                if content is not None:
                    write(path, content)
                result = self.run_evaluate(execution=execution, launch=path)
                self.assertIn(f'session-1 launch-time evaluation unreadable or malformed ({error})', result['problems'])
                self.assertIsNone(result['pooled'])
        write(self.folder / 'bad-execution.json', 'not json')
        result = self.run_evaluate(execution=self.folder / 'bad-execution.json', launch=self.launch)
        self.assertIn('session-2 execution lock unreadable or malformed (JSONDecodeError)', result['problems'])
        write(self.records['1'], '')
        result = self.run_evaluate(execution=execution, launch=self.launch)
        self.assertIn('session 1: retained evaluation unreadable or malformed (JSONDecodeError)', result['problems'])

    def test_each_record_is_read_once_and_the_hashed_bytes_are_compared(self):
        execution = self.execution(P.sha256_file(self.launch))
        reads, original = [], Path.read_bytes

        def counting(path):
            reads.append(Path(path).name)
            return original(path)
        with mock.patch.object(Path, 'read_bytes', autospec=True, side_effect=counting):
            result = self.run_evaluate(execution=execution, launch=self.launch)
        self.assertEqual(self.binding(result), [])
        self.assertEqual((reads.count('launch.json'), reads.count('execution.json'), reads.count('1.json')), (1, 1, 1))
        self.assertEqual(result['sessions']['1']['launch_record_content_sha256'],
                         result['sessions']['1']['record_content_sha256'])

    def test_the_branch_without_a_launch_record_still_binds_the_retained_record(self):
        result = self.run_evaluate(execution=self.execution('f' * 64))
        self.assertIn('session-2 execution lock does not bind the retained session-1 evaluation', result['problems'])
        result = self.run_evaluate(execution=self.execution(P.sha256_file(self.records['1'])))
        self.assertEqual(self.binding(result), [])
        result = self.run_evaluate(execution=None)
        self.assertIn('session-2 execution lock not supplied', result['problems'])

    def test_a_supplied_launch_record_is_checked_in_rehearsal_mode_too(self):
        write(self.launch, dict(self.current, endpoints={'x': 2}, review_lock={'sha256': 'a' * 64}))
        result = self.run_evaluate(mode='rehearsal', execution=self.execution(P.sha256_file(self.launch)),
                                   launch=self.launch)
        self.assertIn('session-1 re-evaluation differs from the launch-time evaluation beyond the evaluating lock',
                      result['problems'])
        result = self.run_evaluate(mode='rehearsal', launch=self.launch)
        self.assertIn('session-2 execution lock not supplied', result['problems'])


class MalformedNestedInputs(Evaluate):
    """Second review (October 13): malformed nested fields and non-finite numbers are reported validation failures,
    never crashes, and no pooled result is produced."""

    def withheld(self, result, problem):
        self.assertIn(problem, result['problems'])
        self.assertIsNone(result['pooled'])
        self.assertIsNone(result['pooled_distinct'])

    def test_execution_binding_must_be_an_object_holding_a_digest(self):
        message = 'session-2 execution lock: session1_evaluation is not an object with a SHA-256 digest'
        for value in ([1], None, 'abc', {}, {'sha256': 5}, {'sha256': 'f' * 63}, {'sha256': 'F' * 64}, {'sha256': [1]}):
            for launch in (self.launch, None):
                with self.subTest(value=value, launch=launch is not None):
                    execution = write(self.folder / 'execution.json', {'session1_evaluation': value})
                    self.withheld(self.run_evaluate(execution=execution, launch=launch), message)

    def test_non_finite_numbers_are_rejected_before_any_comparison(self):
        good = json.dumps(self.current)
        for token in ('NaN', 'Infinity', '-Infinity', '1e999', '-1e999'):
            bad = good[:-1] + f', "extra": {token}}}'
            for name, what in (('1.json', 'session 1: retained evaluation'), ('2.json', 'session 2: retained evaluation'),
                               ('launch.json', 'session-1 launch-time evaluation'),
                               ('execution.json', 'session-2 execution lock')):
                with self.subTest(token=token, file=name):
                    for path in self.records.values():
                        write(path, good)
                    write(self.launch, dict(self.current, review_lock={'sha256': 'a' * 64}))
                    execution = self.execution(P.sha256_file(self.launch))
                    if name == 'execution.json':
                        write(execution, json.dumps({'session1_evaluation': {'sha256': P.sha256_file(self.launch)}})[:-1]
                              + f', "extra": {token}}}')
                    else:
                        write(self.folder / name, bad)
                    self.withheld(self.run_evaluate(execution=execution, launch=self.launch),
                                  f'{what} unreadable or malformed (ValueError)')

    def test_malformed_annotations_and_commitment_receipts_are_reported(self):
        execution = self.execution(P.sha256_file(self.launch))
        sample = SR.sample_for(self.episodes, SPEC, 40, inputs=P.inputs_digest(
            [e for e in self.episodes if e['session'] == '1'] + [e for e in self.episodes if e['session'] == '2']))
        path, _ = self.annotations(sample)
        record = json.loads(path.read_bytes())
        for broken in ({**record, 'annotations': {name: [1] * len(items) for name, items in record['annotations'].items()}},
                       [record], {**record, 'reviewer': float('nan')}):
            with self.subTest(broken=type(broken).__name__):
                text = json.dumps(broken)  # NaN is written as the bare token, which the strict reader refuses
                write(path, text)
                result = self.run_evaluate(mode='rehearsal', annotations=path, digest=P.sha256_file(path))
                self.assertIsNone(result['pooled'])
                self.assertTrue(any(p.startswith('self-review (amendment S1): ValueError') for p in result['problems']))
        write(path, json.dumps(record))
        for receipt in ([1], {'commit': 5, 'repository': '/x'}, {'commit': 'a' * 40, 'repository': ['x']},
                        '{"commit": NaN}'):
            with self.subTest(receipt=receipt):
                receipt_path = write(self.folder / 'receipt.json', receipt)
                result = self.run_evaluate(execution=execution, launch=self.launch, annotations=path,
                                           digest=P.sha256_file(path), commitment=receipt_path)
                self.assertIsNone(result['pooled'])
                self.assertTrue(any(p.startswith('self-review (amendment S1): ValueError') for p in result['problems']),
                                result['problems'])

    def test_validate_and_the_strict_reader_directly(self):
        sample = SR.sample_for(self.episodes, SPEC, 40)
        record = SR.template(sample)
        name = next(iter(record['annotations']))
        record['annotations'][name] = [1]
        for annotations in (record, [record], None):
            with self.assertRaises(ValueError):
                SR.validate(sample, annotations)
        for token in ('NaN', 'Infinity', '-Infinity', '1e999'):
            with self.assertRaises(ValueError):
                SR.strict_json('{"x": %s}' % token)
        self.assertEqual(SR.strict_json('{"x": 1.5, "y": 1e300, "z": 10}'), {'x': 1.5, 'y': 1e300, 'z': 10})


class CommittedSample(Evaluate):
    """A sample committed under the first S2 rule text binds only if the corrected rule draws it exactly."""

    def inputs(self):
        return P.inputs_digest([e for e in self.episodes if e['session'] == '1']
                               + [e for e in self.episodes if e['session'] == '2'])

    def test_a_v1_sample_with_the_same_selection_is_accepted_and_labelled(self):
        legacy = SR.sample_for(self.episodes, SPEC, 40, inputs=self.inputs(), rule=SR.DISTINCT_RULE_V1)
        path, digest = self.annotations(legacy)
        result = self.run_evaluate(mode='rehearsal', annotations=path, digest=digest)
        self.assertEqual(result['problems'], [])
        self.assertTrue(result['self_review']['sample_rule'].startswith('v1 rule text'))
        self.assertIsNotNone(result['pooled_distinct'])
        self.assertEqual(len(result['pooled_distinct']['duplicates_excluded']), 12)

    def test_a_v1_sample_with_a_different_selection_is_refused(self):
        weaker = copy.deepcopy(self.episodes)
        twin(self.episodes, 'b2-wa30-periodic')['reflection_evidence'] = {'events': [event(9, 'other text')]}
        twin(self.episodes, 'b1-wa30-periodic')['reflection_evidence'] = {'events': [event(9, 'first text')]}
        legacy = SR.sample_for(weaker, SPEC, 40, inputs=self.inputs(), rule=SR.DISTINCT_RULE_V1)
        path, digest = self.annotations(legacy)
        result = self.run_evaluate(mode='rehearsal', annotations=path, digest=digest)
        self.assertIsNone(result['pooled'])
        self.assertTrue(any('annotations are not bound to this sample' in p for p in result['problems']))

    def test_a_corrected_sample_binds_directly(self):
        sample = SR.sample_for(self.episodes, SPEC, 40, inputs=self.inputs())
        path, digest = self.annotations(sample)
        result = self.run_evaluate(mode='rehearsal', annotations=path, digest=digest)
        self.assertEqual(result['problems'], [])
        self.assertEqual(result['self_review']['sample_rule'], SR.SIGNATURE_VERSION)
        self.assertEqual(result['limitations'][-1],
                         P.distinct_limitation(result['pooled_distinct']['distinct_trajectories_per_game_and_arm']))
        self.assertEqual(set(result['cost_denominators']), {'spend', 'pooled.realised_cost', 'pooled_distinct.analysis_cost'})


if __name__ == '__main__':
    unittest.main()
