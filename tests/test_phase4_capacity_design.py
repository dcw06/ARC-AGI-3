import copy
import unittest

from certification.phase4_v5.capacity import estimate


class CapacityDesignTests(unittest.TestCase):
    def requests(self):
        return [dict(request_id=str(i), submitted_seconds=0,
                     service_started_seconds=0, completed_seconds=i + .5,
                     outcome='completed', error=None) for i in range(8)]

    def test_separate_nominal_guard_and_headroom(self):
        result = estimate(0, 8, self.requests())
        self.assertEqual(result['C_nominal'], 19800)
        self.assertEqual(result['conservative_requests_per_wall_second'], .8)
        self.assertEqual(result['service_headroom_seconds'], 3960)
        self.assertEqual(result['effective_service_seconds'], 15840)
        self.assertEqual(result['C_admit_candidate'], 12672)
        self.assertIsNone(result['C_admit'])
        self.assertFalse(result['subsequent_admission_authorized'])

    def test_concurrent_durations_are_not_summed(self):
        rows = self.requests()
        for r in rows:
            r['completed_seconds'] = 8
        result = estimate(0, 8, rows)
        self.assertEqual(result['C_nominal'], 19800)
        self.assertEqual(result['window_completed_requests'], [0] * 7 + [8])
        self.assertEqual(result['C_admit_candidate'], 0)

    def test_idle_finalization_tail_is_not_discarded(self):
        a = estimate(0, 8, self.requests())
        b = estimate(0, 16, self.requests())
        self.assertEqual(b['C_nominal'], a['C_nominal'] // 2)
        self.assertEqual(b['C_admit_candidate'], 0)

    def test_invalid_missing_failed_and_duplicate_evidence_rejected(self):
        for mutate in (
            lambda r: r[0].update(request_id='1'),
            lambda r: r[0].pop('completed_seconds'),
            lambda r: r[0].update(completed_seconds=float('nan')),
            lambda r: r[0].update(completed_seconds=True),
            lambda r: r[0].update(service_started_seconds=2),
            lambda r: r[0].update(error='timeout'),
            lambda r: r[0].update(outcome='canceled'),
        ):
            rows = copy.deepcopy(self.requests()); mutate(rows)
            with self.assertRaises(ValueError):
                estimate(0, 8, rows)
        for start, end, rows in [(0, 0, self.requests()), (0, 8, []),
                                 (False, 8, self.requests()), (0, float('inf'), self.requests())]:
            with self.assertRaises(ValueError):
                estimate(start, end, rows)


if __name__ == '__main__':
    unittest.main()
