import unittest
from human_play.annotations import region


class Regions(unittest.TestCase):
    def setUp(self):
        self.obs={'frames': [[[0,1,2],[3,4,5],[6,7,8]]], 'levels_completed': 2}
        self.body={'name':'绿色长方形','corners':[{'x':2,'y':2},{'x':1,'y':0}],'expected_sequence':7}

    def test_inclusive_row_major_indices_and_visible_colors(self):
        r=region(self.obs,self.body,7)
        self.assertEqual(r['cell_count'],6)
        self.assertEqual([c['index'] for c in r['cells']],[1,2,4,5,7,8])
        self.assertEqual(r['cells'][0],{'x':1,'y':0,'row':0,'column':1,'index':1,'color_index':1})
        self.assertEqual(r['bounds_inclusive'],{'x_min':1,'x_max':2,'y_min':0,'y_max':2})
        self.assertEqual(r['status'],'human_annotation')

    def test_single_cell_and_bad_coordinates(self):
        b={**self.body,'corners':[{'x':0,'y':2}]*2}
        self.assertEqual(region(self.obs,b,7)['cells'][0]['index'],6)
        for p in ({'x':3,'y':0},{'x':True,'y':0},{'x':0,'y':-1}):
            with self.assertRaises(ValueError):region(self.obs,{**b,'corners':[p,p]},7)

    def test_stale_frame_and_blank_name_rejected(self):
        with self.assertRaises(ValueError):region(self.obs,self.body,8)
        with self.assertRaises(ValueError):region(self.obs,{**self.body,'name':' '},7)


if __name__=='__main__':unittest.main()
