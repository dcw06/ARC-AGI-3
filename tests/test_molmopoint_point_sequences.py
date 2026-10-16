"""Regression: unfinished native point tokens must never reach target-hit scoring."""
import re
from types import SimpleNamespace
import unittest

from research.molmopoint_identification_v1.adapter import decode_generation
from research.molmopoint_identification_v1.scoring import score_target


class PointSequenceRegressionTests(unittest.TestCase):
    complete = '<POINT_0><POINT_5><POINT_9>0'
    sentinel = '<POINT_4>'  # Four patches; no-more-points occupies index four.

    def decode(self, text):
        # Reproduce the upstream decoder's permissive complete-sequence matching.
        model = SimpleNamespace(config=SimpleNamespace(model_type='molmo_point',
            no_more_points_class=True,patch_location='3x3'),
            extract_image_points=lambda text,*args:[
                [int(match.group(1)),0,20.0,28.0] for match in re.finditer(
                    r'<POINT_\d+> ?<POINT_\d+> ?<POINT_\d+> ?([0-9]+)',text)])
        processor = SimpleNamespace(post_process_image_text_to_text=lambda *args,**kwargs:[text])
        metadata = {'token_pooling':SimpleNamespace(shape=(4,4)),
                    'subpatch_mapping':'not-needed-by-this-fixture','image_sizes':[(512,512)]}
        return decode_generation(model,processor,[42],metadata,(512,512),finish_reason='stop')

    def hit(self, text):
        result = self.decode(text)
        ref = {'case_id':'synthetic','regions':[{'id':'target','target_points':[[2,3]]}]}
        return score_target(ref,'target',result['points'])

    def test_complete_point_still_earns_target_hit(self):
        self.assertTrue(self.hit(self.complete)['target_hit'])

    def test_complete_point_then_unfinished_second_point_refused(self):
        for tail in ['<POINT_1>','<POINT_1><POINT_5>','<POINT_1><POINT_5><POINT_9>']:
            with self.subTest(tail=tail),self.assertRaises(ValueError):
                self.hit(self.complete+tail)

    def test_only_unfinished_point_is_invalid_not_empty_detection(self):
        for fragment in ['<POINT_0>','<POINT_0><POINT_5>','<POINT_0><POINT_5><POINT_9>']:
            with self.subTest(fragment=fragment),self.assertRaises(ValueError):
                self.decode(fragment)

    def test_unfinished_prefix_cannot_be_skipped_before_complete_point(self):
        with self.assertRaises(ValueError):
            self.hit('<POINT_1>'+self.complete)

    def test_no_more_points_sentinel_alone_is_valid_empty_detection(self):
        result = self.hit('<points>'+self.sentinel+'</points><|im_end|>')
        self.assertTrue(result['response_valid'])
        self.assertFalse(result['target_hit'])
        self.assertEqual(result['point_count'],0)

    def test_complete_point_then_sentinel_preserves_hit(self):
        self.assertTrue(self.hit('<points>'+self.complete+self.sentinel+'</points><|im_end|>')['target_hit'])

    def test_points_and_duplicate_sentinels_after_sentinel_refused(self):
        for text in [self.sentinel+self.complete,self.sentinel+self.sentinel]:
            with self.subTest(text=text),self.assertRaises(ValueError):
                self.decode(text)

    def test_sentinel_cannot_replace_subpatch_location_or_object_id(self):
        for text in ['<POINT_0>'+self.sentinel,
                     '<POINT_0><POINT_5>'+self.sentinel,
                     '<POINT_0><POINT_5><POINT_9>'+self.sentinel]:
            with self.subTest(text=text),self.assertRaises(ValueError):
                self.decode(text)

    def test_malformed_marker_and_wrong_token_roles_refused(self):
        for text in [self.complete+'<POINT_', '<POINT_X>', '<POINT_0',
                     '<POINT_5><POINT_0><POINT_9>0', '<POINT_0><POINT_9><POINT_5>0',
                     '<POINT_0><POINT_5><POINT_18>0']:
            with self.subTest(text=text),self.assertRaises(ValueError):
                self.decode(text)

    def test_valid_complete_sequences_and_plain_text_are_not_trimmed(self):
        text = 'Targets: '+self.complete+' <POINT_1> <POINT_6> <POINT_13> 1'+self.sentinel
        result = self.decode(text)
        self.assertEqual(result['raw_text_with_special_tokens'],text)
        self.assertEqual(len(result['points']),2)
        self.assertEqual(self.decode('No objects found.<|im_end|>')['points'],[])


if __name__ == '__main__':
    unittest.main()
