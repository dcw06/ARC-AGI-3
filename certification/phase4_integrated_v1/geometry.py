"""Initial-mask metrics only; prose and later object identity need adjudication."""
import itertools,json
from pathlib import Path
from fractions import Fraction
from certification.phase4_integrated_v1.request_contract import cells
def evaluate_inventory(answer):
 ref=json.loads((Path(__file__).resolve().parents[2]/'reports/integrated_case_v1/geometry_reference.json').read_bytes())
 objects=answer['objects'];pred=[cells(o['spans']) for o in objects];truth=[{tuple(p) for p in o['cells']} for o in ref['objects']]
 def iou(a,b):return Fraction(len(a&b),len(a|b)) if a|b else Fraction(0)
 # Map each reference to a distinct prediction or missing; exact rational ties.
 options=[None]+list(range(len(pred)));best=None;bestscore=Fraction(-1)
 for assignment in itertools.product(options,repeat=3):
  chosen=[i for i in assignment if i is not None]
  if len(set(chosen))!=len(chosen):continue
  score=sum((iou(pred[i],truth[j]) for j,i in enumerate(assignment) if i is not None),Fraction(0))
  tie=tuple(999 if i is None else i for i in assignment)
  if score>bestscore or score==bestscore and tie<best[0]:bestscore=score;best=(tie,assignment)
 rows=[]
 for j,i in enumerate(best[1]):
  overlap=Fraction(0) if i is None else iou(pred[i],truth[j])
  rows.append({'reference':ref['objects'][j]['id'],'prediction_id':None if i is None or overlap==0 else objects[i]['id'],
   'iou':float(overlap),'localized':overlap>=Fraction(4,5),'silhouette_exact':False if i is None else pred[i]==truth[j],
   'bbox_exact':False if i is None else objects[i]['bbox']==ref['objects'][j]['bbox']})
 used={i for j,i in enumerate(best[1]) if i is not None and iou(pred[i],truth[j])>0}
 return {'mask_matches':rows,'unmatched_prediction_ids':[o['id'] for i,o in enumerate(objects) if i not in used],
  'prose_geometry_markings_and_context_regions':'pending_rubric_adjudication','reference_not_sent_to_model':True}
