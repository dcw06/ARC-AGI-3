import copy,unittest
from scripts.build_grounding_diagnostic_v1 import answer,build,verify_answers,validate_grid

class GroundingTests(unittest.TestCase):
    def test_disconnected_inclusive_bbox_and_row_major(self):
        self.assertEqual(answer({'kind':'locate','color':2,'grid':[[0,0,2],[2,0,0]]}),
            {'count':2,'bbox':[0,0,2,1],'first':{'x':2,'y':0}})
    def test_coordinate_axes(self):
        self.assertEqual(answer({'kind':'coordinate','grid':[[0,2],[3,0]],'x':1,'y':0}),{'color':2})
    def test_null_changes(self):
        self.assertEqual(answer({'kind':'changes','before':[[1,0]],'after':[[1,0]]}),
            {'count':0,'bbox':None,'first':None,'first_change':None})
    def test_changed_colors(self):
        self.assertEqual(answer({'kind':'changes','before':[[1,0],[0,0]],'after':[[1,4],[3,0]]}),
            {'count':2,'bbox':[0,0,1,1],'first':{'x':1,'y':0},'first_change':{'before':0,'after':4}})
    def test_invalid_frames(self):
        for grid in ([],[[True]],[[16]],[[1],[1,2]]):
            with self.assertRaises(ValueError):validate_grid(grid)
        with self.assertRaises(ValueError):answer({'kind':'changes','before':[[0]],'after':[[0,0]]})
    def test_retained_cases_and_independent_answer_check(self):
        data=build();verify_answers(data);self.assertEqual(len(data['cases.json']),12)
        for kind in ('locate','coordinate','changes'):
            self.assertEqual(sum(c['task']['kind']==kind for c in data['cases.json']),4)
        altered=copy.deepcopy(data);altered['answers.json'][0]['expected']['count']+=1
        with self.assertRaises(AssertionError):verify_answers(altered)

if __name__=='__main__':unittest.main()
