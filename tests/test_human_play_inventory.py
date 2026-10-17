"""Coordinate artifact integrity, including exact masks versus bounding boxes."""
import copy
import json
import unittest
from human_play.level1_inventory import components, OUT, validate


class Coordinates(unittest.TestCase):
    def test_diagonal_pixels_are_not_merged_by_four_connectivity(self):
        parts=components([[1,0,1],[0,1,0]])
        self.assertEqual(len(parts),6)
        self.assertEqual(sum(p['cell_count'] for p in parts),6)
        self.assertEqual({c['index'] for p in parts for c in p['cells']},set(range(6)))

    def test_saved_masks_all_nine_games(self):
        index=json.loads((OUT/'index.json').read_text())
        self.assertEqual(len(index['games']),9)
        for g in index['games']:
            with self.subTest(game=g['game_id']):
                data=json.loads((OUT/g['file']).read_text())
                validate(data)
                self.assertEqual(sum(p['cell_count'] for p in data['components']),4096)
                self.assertEqual(data['initial_observation']['levels_completed'],0)

    def test_forged_index_and_color_are_rejected(self):
        original=json.loads((OUT/'ar25.json').read_text())
        for field in ('index','color_index'):
            forged=copy.deepcopy(original)
            forged['objects'][0]['cells'][0][field]+=1
            with self.assertRaises(ValueError):validate(forged)

    def test_shape_mask_is_smaller_than_bounding_box(self):
        data=json.loads((OUT/'ar25.json').read_text())
        dots=next(o for o in data['objects'] if '五个白点' in o['name'])
        self.assertEqual([(c['x'],c['y']) for c in dots['cells']],[(19,16),(22,16),(25,16),(25,19),(25,22)])
        b=dots['bounds_inclusive']
        self.assertGreater((b['x_max']-b['x_min']+1)*(b['y_max']-b['y_min']+1),dots['cell_count'])


if __name__=='__main__':unittest.main()
