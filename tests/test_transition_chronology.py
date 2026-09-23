import copy
import unittest
from research.perception_v1 import transitions
from research.perception_v1.fixtures import digest
from tests import test_perception_v1_local as fixtures


class ChronologyTests(unittest.TestCase):
    def successor(self, previous, committed, started, returned):
        intent=copy.deepcopy(previous['intent'])
        intent.update(step=intent['step']+1,before=previous['after'],
                      before_sha256=previous['after_sha256'],committed_at=committed)
        return transitions.finalize(intent,intent_sha256=digest(intent),
            dispatch={'action':intent['action'],'acknowledged':True,
                      'started_at':started,'returned_at':returned},
            after=previous['after'],update=previous['model_update'])

    def test_backdated_and_overlapping_chains_rejected(self):
        previous=fixtures.TransitionTests().record()  # Returns at 3.0 on the shared clock.
        for times in ((0.5,1.0,2.0),(2.5,2.75,4.0),(2.5,4.0,5.0)):
            with self.subTest(times=times):
                record=self.successor(previous,*times)
                self.assertTrue(transitions.verify(record))  # Internally ordered alone.
                with self.assertRaisesRegex(ValueError,'episode chronology'):
                    transitions.verify(record,previous)

    def test_boundary_equality_and_later_records_accepted(self):
        previous=fixtures.TransitionTests().record()
        for times in ((3.0,3.0,3.0),(3.0,3.5,4.0),(4.0,5.0,6.0)):
            with self.subTest(times=times):
                self.assertTrue(transitions.verify(self.successor(previous,*times),previous))

    def test_predecessor_timestamp_cannot_bypass_validation(self):
        previous=fixtures.TransitionTests().record();record=self.successor(previous,3,4,5)
        for returned in (float('nan'),float('inf'),-1,True):
            changed=copy.deepcopy(previous);changed['dispatch']['returned_at']=returned
            with self.subTest(returned=returned),self.assertRaises(ValueError):
                transitions.verify(record,changed)

if __name__=='__main__':unittest.main()
