import copy,json,unittest
from unittest.mock import patch
from certification.phase4_coordinates_v1.cases import generate,load,BASELINE,EXPLICIT
from certification.phase4_coordinates_v1.score import truth,classify,evaluate

class CoordinatesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.rows=generate()
    def test_coverage_and_transposes(self):
        self.assertEqual(len(self.rows),56)
        for row in self.rows:
            a,b=truth(row);self.assertNotEqual(a,b)
            p=json.loads(row['request']['messages'][1]['content'])
            self.assertEqual(row['stratum']=='boundary',p['x'] in (0,row['size']-1) or p['y'] in (0,row['size']-1))
            partner=next(r for r in self.rows if r['source_group']==row['source_group'] and r['condition']==row['condition'] and
                json.loads(r['request']['messages'][1]['content'])['x']==p['y'] and json.loads(r['request']['messages'][1]['content'])['y']==p['x'])
            self.assertEqual(truth(partner),(b,a))
    def test_wording_only_and_no_answer_metadata(self):
        for i in range(0,len(self.rows),2):
            a,b=[copy.deepcopy(r['request']) for r in self.rows[i:i+2]]
            x,y=[json.loads(r['messages'][1]['content']) for r in (a,b)]
            self.assertEqual({x.pop('instruction'),y.pop('instruction')},{BASELINE,EXPLICIT});self.assertEqual(x,y)
            self.assertEqual(set(x),{'kind','grid','x','y'})
            a['messages'][1]['content']='';b['messages'][1]['content']='';self.assertEqual(a,b)
        prior=json.loads(__import__('pathlib').Path('certification/phase4_grounding_v1/cases.json').read_bytes())
        self.assertEqual(self.rows[0]['request']['messages'][0],prior[0]['request']['messages'][0])
    def test_all_scoring_branches(self):
        c=self.rows[0];a,b=truth(c)
        for color,label in [(a,'correct'),(b,'transposed'),(next(v for v in range(16) if v not in (a,b)),'other_valid')]:self.assertEqual(classify(c,json.dumps({'color':color})),label)
        for text in ('{}','{"color":true}','{"color":1,"color":2}','not json','{"color":16}','{"color":1,"extra":2}'):
            self.assertEqual(classify(c,text),'malformed')
    def responses(self):return [{'case_id':c['case_id'],'request_sha256':c['request_sha256'],'status':'received','content':json.dumps({'color':truth(c)[1]})} for c in self.rows]
    def test_wrong_answers_are_outcomes_and_missing_is_failure(self):
        rows=self.responses();r=evaluate(self.rows,rows);self.assertTrue(r['technical_passed']);self.assertEqual(r['by_condition']['baseline']['exact_accuracy'],0)
        rows[0].pop('content');rows[0].update(status='missing',error='transport failure');r=evaluate(self.rows,rows);self.assertFalse(r['technical_passed'])
    def test_reordered_duplicated_omitted_altered(self):
        for rows in (self.rows[::-1],self.rows[:-1],self.rows[:-1]+[self.rows[0]]):
            with patch('pathlib.Path.read_bytes',return_value=json.dumps(rows).encode()),patch('certification.phase4_coordinates_v1.cases.generate',return_value=self.rows),self.assertRaises(ValueError):load()
        for rows in (self.responses()[::-1],self.responses()[:-1],self.responses()[:-1]+[self.responses()[0]]):
            with self.assertRaises(ValueError):evaluate(self.rows,rows)
        rows=self.responses();rows[0]['request_sha256']='changed'
        with self.assertRaises(ValueError):evaluate(self.rows,rows)
    def test_coordinate_bounds_and_ambiguity(self):
        c=copy.deepcopy(self.rows[0]);p=json.loads(c['request']['messages'][1]['content'])
        for x,y in ((-1,0),(64,0),(True,1),(1,1)):
            p.update(x=x,y=y);c['request']['messages'][1]['content']=json.dumps(p)
            with self.assertRaises(ValueError):truth(c)

if __name__=='__main__':unittest.main()
