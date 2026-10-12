"""Amendment S2 (owner decision, October 12, 2026): block 2 replayed block 1 exactly, so the self-review draws from
distinct trajectories only, the pooled evaluation adds a distinct-trajectory headline beside the frozen analysis, and
a session-1 evaluation re-run under a later review lock may stand in for the launch-time record it equals. CPU only;
synthetic episodes and records in temporary directories."""
import copy
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest import mock

from research.stagnation_supervision_runtime_v2 import pooled as P, report as R, selfreview as SR
from tests import test_ssv_runtime_v2_r2_gaps as fixtures
label_population, SPEC = fixtures.label_population, fixtures.SPEC


def events(*rows, latency=1.0):
    return {'events': [{'action_index': i, 'outcome': 'called', 'delivered': text, 'call': {'latency_s': latency}}
                       for i, text in rows]}


class DistinctTrajectories(unittest.TestCase):
    def setUp(self):
        self.episodes = label_population()  # block 2 repeats block 1's records and deliveries exactly

    def test_exact_block_two_copies_are_excluded_and_bound_to_their_originals(self):
        kept, excluded = SR.distinct(self.episodes)
        self.assertEqual(sorted(e['episode'] for e in kept),
                         sorted(e['episode'] for e in self.episodes if e['block'] == 1 and not e['repeat']))
        self.assertEqual(len(excluded), 12)
        for row in excluded:
            self.assertEqual(row['duplicate_of'], {'session': '1', 'episode': row['episode'].replace('b2-', 'b1-', 1)})
        self.assertNotIn('r1-ar25-continuation', [e['episode'] for e in kept] + [r['episode'] for r in excluded])

    def test_a_block_two_episode_that_differs_is_kept(self):
        changed = copy.deepcopy(self.episodes)
        target = next(e for e in changed if e['episode'] == 'b2-wa30-periodic')
        target['delivered'] = [9]
        kept, excluded = SR.distinct(changed)
        self.assertIn('b2-wa30-periodic', [e['episode'] for e in kept])
        self.assertEqual(len(excluded), 11)

    def test_signature_ignores_timing_but_not_delivered_reflections(self):
        a = copy.deepcopy(self.episodes[0])
        a['reflection_evidence'] = events((9, 'try left'), latency=1.0)
        b = copy.deepcopy(a)
        b['reflection_evidence'] = events((9, 'try left'), latency=7.5)
        c = copy.deepcopy(a)
        c['reflection_evidence'] = events((9, 'try right'))
        self.assertEqual(SR.trajectory_signature(a), SR.trajectory_signature(b))
        self.assertNotEqual(SR.trajectory_signature(a), SR.trajectory_signature(c))

    def test_the_sample_is_the_s1_draw_over_distinct_trajectories_with_exclusions_bound(self):
        sample = SR.sample_for(self.episodes, SPEC, 40)
        block1 = [e for e in self.episodes if e['block'] == 1]
        self.assertEqual(sample['strata'], SR.draw(SR.candidates(block1, SPEC, 40))['strata'])
        self.assertEqual(len(sample['amendment_s2']['duplicates_excluded']), 12)
        self.assertFalse([i for row in sample['strata'].values() for i in row['selected'] if i['session'] == '2'])
        shuffled = list(self.episodes)
        random.Random(11).shuffle(shuffled)
        self.assertEqual(SR.sample_for(shuffled, SPEC, 40)['sample_sha256'], sample['sample_sha256'])
        tampered = copy.deepcopy(sample)
        tampered['amendment_s2']['duplicates_excluded'].pop()
        with self.assertRaisesRegex(ValueError, 'sample digest'):
            SR.validate(tampered, SR.template(tampered))

    def test_without_duplicates_the_strata_equal_the_s1_draw(self):
        block1 = [e for e in self.episodes if e['block'] == 1]
        sample = SR.sample_for(block1, SPEC, 40)
        self.assertEqual(sample['strata'], SR.draw(SR.candidates(block1, SPEC, 40))['strata'])
        self.assertEqual(sample['amendment_s2']['duplicates_excluded'], [])


class DistinctPooledSection(unittest.TestCase):
    def test_distinct_section_uses_each_trajectory_once(self):
        episodes = label_population()
        distinct = P.compute_distinct(episodes, SPEC, 40)
        block1 = [e for e in episodes if e['block'] == 1 and not e['repeat']]
        primary = [e for e in block1 if e['game'] in P.PRIMARY_GAMES]
        self.assertEqual(distinct['primary']['by_arm'], P.recovery(primary, SPEC, 40))
        self.assertEqual({arm: row['episodes'] for arm, row in distinct['primary']['by_arm'].items()},
                         dict.fromkeys(P.ARMS, 3))
        self.assertEqual(set(distinct['by_game']), set(P.GAMES))
        self.assertEqual(len(distinct['duplicates_excluded']), 12)
        self.assertTrue(distinct['advancement'].startswith('not recomputed'))
        frozen = P.compute(episodes, SPEC, 40)  # the frozen analysis is unchanged and counts both copies
        self.assertEqual({arm: row['episodes'] for arm, row in frozen['primary']['by_arm'].items()},
                         dict.fromkeys(P.ARMS, 6))


class LaunchTimeSessionOneRecord(unittest.TestCase):
    """The session-2 execution lock binds the launch-time session-1 record; a re-evaluation under a later lock may
    stand in for it only if the two are equal apart from the evaluating lock."""

    def evaluate(self, launch_change=None, bind_current=False):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            current = {'technically_complete': True, 'target_accepted': True, 'endpoints': {'x': 1},
                       'review_lock': {'sha256': 'b' * 64, 'verified': True}}
            launch = dict(current, review_lock={'sha256': 'a' * 64, 'verified': True})
            if launch_change:
                launch_change(launch)
            paths = {s: folder / f'{s}.json' for s in ('1', '2')}
            for path in paths.values():
                path.write_text(json.dumps(current), encoding='utf-8')
            launch_path = folder / 'launch.json'
            launch_path.write_text(json.dumps(launch), encoding='utf-8')
            execution = folder / 'execution.json'
            bound = P.sha256_file(paths['1'] if bind_current else launch_path)
            execution.write_text(json.dumps({'session1_evaluation': {'sha256': bound}}), encoding='utf-8')
            with mock.patch.object(R, 'study_report', return_value=current), \
                    mock.patch('research.stagnation_supervision_v1.closed_loop.bridge.session_spec',
                               return_value={'limits': {'actions_per_episode': 40}}), \
                    mock.patch.object(P, 'session_episodes', side_effect=[label_population(), []]):
                return P.evaluate_sessions({'1': folder, '2': folder}, paths, annotations='/nonexistent',
                                           annotations_sha256='0' * 64, session2_execution=execution,
                                           session1_launch_record=launch_path)

    def binding_problems(self, result):
        return [p for p in result['problems'] if 'session-1' in p or 'execution lock' in p]

    def test_equal_apart_from_the_lock_is_accepted(self):
        result = self.evaluate()
        self.assertEqual(self.binding_problems(result), [])
        self.assertIsNotNone(result['sessions']['1']['launch_record_sha256'])
        self.assertIsNone(result['pooled'])  # still refused: no committed self-review
        self.assertTrue(any('self-review' in p for p in result['problems']))

    def test_any_other_difference_is_refused(self):
        result = self.evaluate(lambda r: r.update(endpoints={'x': 2}))
        self.assertIn('session-1 re-evaluation differs from the launch-time evaluation beyond the evaluating lock',
                      result['problems'])
        self.assertIsNone(result['pooled_distinct'])

    def test_a_launch_record_the_execution_lock_does_not_bind_is_refused(self):
        result = self.evaluate(bind_current=True)
        self.assertIn('session-2 execution lock does not bind the supplied launch-time session-1 evaluation',
                      result['problems'])


if __name__ == '__main__':
    unittest.main()
