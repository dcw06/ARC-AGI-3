"""CPU-only frame binding, reference isolation and scoring on synthetic boards."""
import copy,json,tempfile,unittest
from pathlib import Path
from certification.phase4_multimodal_preflight_v3.images import png
from research.object_discovery_boundaries_v1.reference_audit import canonical,digest
from research.object_discovery_boundaries_v1.prepare import prepare,requests_for,PROMPT
from research.object_discovery_boundaries_v1.evaluation import evaluate
from research.object_discovery_boundaries_v1.sam21 import proposal
from scripts.build_object_boundary_review import build


class Preparation(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.base=Path(temp.name)
        source=self.base/'source';source.mkdir();files={};refs=[]
        for i in range(1,7):
            case=f'board-{i:02d}';grid=[[0]*64 for _ in range(64)];grid[2][2]=i
            pin=digest(canonical(grid));files['source-grids/'+case+'.json']=canonical(grid)
            files['inputs/'+case+'.png']=png(grid,cell=7)
            refs.append(dict(case_id=case,grid_sha256=pin,regions=[dict(id=case+'.entity',label='Synthetic label',
                parent_id=None,grid_sha256=pin,geometry='mask',bbox_xyxy=[2,2,2,2],target_points=[[2,2]])]))
        files['references/answers.json']=canonical(refs)
        for n,v in files.items():p=source/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(v)
        (source/'preparation-manifest.json').write_bytes(canonical({n:digest(v) for n,v in files.items()}))
        self.prep=self.base/'prep';prepare(source,self.prep)
        self.review=json.loads((self.prep/'references/review-draft.json').read_bytes())
        for frame in self.review['frames']:
            frame.update(reviewer='SYNTHETIC ONLY',reference_exhaustive_confirmed=True)
            for r in frame['regions']:r['mask_reviewed']=True
        self.pred=dict(schema='object_boundary_predictions_v1',frames=[dict(case_id=f['case_id'],grid_sha256=f['grid_sha256'],
            model_response_valid=True,objects=[dict(id='candidate',level='whole',cells=[[2,2]])]) for f in self.review['frames']])

    def score(self):
        a=self.base/'review.json';b=self.base/'pred.json';a.write_bytes(canonical(self.review));b.write_bytes(canonical(self.pred))
        return evaluate(self.prep,a,b)

    def test_inputs_have_one_generic_prompt_no_reference_metadata(self):
        requests=requests_for(self.prep/'inputs')
        self.assertEqual({r['prompt'] for r in requests},{PROMPT})
        self.assertEqual(len(list((self.prep/'inputs').iterdir())),7)
        self.assertNotIn('Synthetic label',(self.prep/'inputs/requests.jsonl').read_text())
        self.assertTrue(all(r['max_new_tokens']==4096 for r in requests))

    def test_target_hint_or_extra_reference_file_refuses(self):
        path=self.prep/'inputs/requests.jsonl';rows=[json.loads(r) for r in path.read_bytes().splitlines()]
        rows[0]['prompt']='Point to the blue square.';path.write_bytes(b''.join(canonical(r) for r in rows))
        with self.assertRaisesRegex(ValueError,'contract differs'):requests_for(self.prep/'inputs')
        (self.prep/'inputs/answers.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'inventory'):requests_for(self.prep/'inputs')

    def test_fully_reviewed_synthetic_masks_score_without_automatic_verdict(self):
        result=self.score();self.assertIsNone(result['passing_verdict'])
        self.assertTrue(all(f['strata']['whole']['exact_mask_fraction']==1 for f in result['frames']))
        self.assertEqual(result['model_calls'],0)

    def test_empty_SAM_masks_reach_full_evaluation_without_losing_denominator(self):
        for frame in self.pred['frames']:
            frame['objects'].append(proposal(2,dict(pixel_xy=[14.1,14.1],cell_xy=[2,2]),[],[.7,.2,.1],0))
        result=self.score()
        for frame in result['frames']:
            score=frame['strata']['whole']
            self.assertEqual(score['prediction_count'],2)
            self.assertEqual(score['matched_count'],1)
            self.assertEqual(score['detection_precision'],.5)
            self.assertEqual(score['false_positive_count'],1)
            self.assertEqual(score['detection_recall'],1)

    def test_invalid_response_counts_as_zero_found_and_is_listed(self):
        self.pred['frames'][0].update(model_response_valid=False,objects=[])
        result=self.score()
        first=result['frames'][0];score=first['strata']['whole']
        self.assertEqual((first['response_valid'],first['format_failure']),(False,True))
        self.assertEqual((score['reference_count'],score['prediction_count'],score['matched_count']),(1,0,0))
        self.assertEqual(score['detection_recall'],0);self.assertIsNone(score['detection_precision'])
        self.assertEqual(result['format_failure_frames'],['board-01'])
        self.assertTrue(all(f['response_valid'] and f['strata']['whole']['detection_recall']==1 for f in result['frames'][1:]))
        self.assertEqual(sum(f['strata']['whole']['reference_count'] for f in result['frames']),6)  # stays in the totals

    def test_invalid_response_with_objects_or_unstated_validity_refuses(self):
        self.pred['frames'][0]['model_response_valid']=False  # still carries its candidate object
        with self.assertRaisesRegex(ValueError,'invalid model response supplies objects'):self.score()
        for value in (None,1,'false'):
            self.pred['frames'][0]['model_response_valid']=value
            with self.assertRaisesRegex(ValueError,'explicit model_response_valid boolean'):self.score()
        del self.pred['frames'][0]['model_response_valid']
        with self.assertRaisesRegex(ValueError,'explicit model_response_valid boolean'):self.score()

    def test_cross_frame_hash_or_changed_grid_refuses(self):
        self.pred['frames'][0]['grid_sha256']=self.pred['frames'][1]['grid_sha256']
        with self.assertRaisesRegex(ValueError,'prediction frame'):self.score()
        self.pred['frames'][0]['grid_sha256']=self.review['frames'][0]['grid_sha256']
        self.review['frames'][0]['grid'][0][0]=8
        with self.assertRaisesRegex(ValueError,'review frame'):self.score()

    def test_unreviewed_mask_and_deleted_source_label_refuse(self):
        self.review['frames'][0]['regions'][0]['mask_reviewed']=False
        with self.assertRaisesRegex(ValueError,'explicit mask'):self.score()
        self.review['frames'][0]['regions']=[]
        with self.assertRaisesRegex(ValueError,'source regions removed'):self.score()

    def test_private_review_page_has_unapproved_labels_and_hover_coordinates(self):
        out=self.base/'page.html';result=build(self.prep,out);text=out.read_text(encoding='utf-8')
        self.assertEqual(result['automatic_review_approvals'],0)
        self.assertIn('Board (x,y)',text);self.assertIn('pointermove',text)
        self.assertIn('"mask_reviewed": false',text)
        with self.assertRaises(FileExistsError):build(self.prep,out)


if __name__=='__main__':unittest.main()
