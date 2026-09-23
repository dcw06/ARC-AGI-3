"""Initial-mask metrics only; prose and later object identity need adjudication."""
import itertools,json
from pathlib import Path
from fractions import Fraction
from certification.phase4_integrated_v2.request_contract import cells
def evaluate_inventory(answer):
 ref=json.loads((Path(__file__).resolve().parents[2]/'reports/integrated_case_v1/geometry_reference.json').read_bytes())
 objects=answer['objects']
 def boxcells(box):
  x0,y0,x1,y1=box
  return {(x,y) for y in range(y0,y1+1) for x in range(x0,x1+1)}
 pred=[boxcells(o['bbox']) for o in objects];truth=[boxcells(o['bbox']) for o in ref['objects']]
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
   'bbox_iou':float(overlap),'localized':overlap>=Fraction(4,5),'contour_accuracy':'not_in_coarse_inventory_see_decision_target_contour',
   'bbox_exact':False if i is None else objects[i]['bbox']==ref['objects'][j]['bbox']})
 used={i for j,i in enumerate(best[1]) if i is not None and iou(pred[i],truth[j])>0}
 return {'bbox_matches':rows,'unmatched_prediction_ids':[o['id'] for i,o in enumerate(objects) if i not in used],
  'prose_geometry_markings_and_context_regions':'pending_rubric_adjudication','reference_not_sent_to_model':True}
def evaluate_target_contour(spans):
 """Cell-level contour score of a declared target against the initial-frame masks only."""
 ref=json.loads((Path(__file__).resolve().parents[2]/'reports/integrated_case_v1/geometry_reference.json').read_bytes())
 pred=cells(spans)
 if not pred:return None
 rows=[]
 for o in ref['objects']:
  truth={tuple(c) for c in o['cells']};inter=len(pred&truth)
  rows.append((Fraction(inter,len(pred|truth)),o['id'],inter,len(truth)))
 # max() keeps the first reference on exact ties, so order is the frozen reference order.
 score,rid,inter,size=max(rows,key=lambda r:r[0])
 return {'best_reference':rid if score>0 else None,'cell_iou':float(score),'cell_precision':float(Fraction(inter,len(pred))),
  'cell_recall':float(Fraction(inter,size)),'mask_exact':score==1,'predicted_cells':len(pred),'reference_not_sent_to_model':True}
