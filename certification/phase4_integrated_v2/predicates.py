"""Observation-only predicate truth; no claims about hidden mechanics."""
from certification.phase4_integrated_v2.request_contract import cells
def changes(before,after):
 if len(before)!=len(after) or any(len(a)!=len(b) for a,b in zip(before,after)):return {'count':-1,'bbox':[]}
 pts=[(x,y) for y,r in enumerate(before) for x,v in enumerate(r) if v!=after[y][x]]
 return {'count':len(pts),'bbox':[min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts)] if pts else []}
def verdict(pred,before,frames,pre_levels,post_levels):
 if pred['kind']=='level_counter_increase':return 'supported' if post_levels>pre_levels else 'contradicted'
 results=[]
 for g in frames if pred['frame']=='any_returned' else frames[-1:]:
  if len(g)!=len(before) or any(len(a)!=len(b) for a,b in zip(g,before)):results.append(None);continue
  pts=cells(pred['spans'],len(before[0]),len(before));kind=pred['kind']
  if kind=='exact_color_at':value=g[pred['y']][pred['x']]==pred['color']
  elif kind=='any_cell_change':value=any(g[y][x]!=before[y][x] for x,y in pts)
  elif kind=='no_cell_change':value=all(g[y][x]==before[y][x] for x,y in pts)
  else:
   # Translation predicate is EXACT color occupancy in the whole frame, not
   # persistent-object identity. Occlusion/extras fail; clipping is unresolved.
   moved={(x+pred['dx'],y+pred['dy']) for x,y in pts}
   if any(not 0<=x<len(g[0]) or not 0<=y<len(g) for x,y in moved):results.append(None);continue
   actual={(x,y) for y,row in enumerate(g) for x,v in enumerate(row) if v==pred['color']}
   value=actual==moved
  results.append(value)
 if True in results:return 'supported'
 return 'unresolved' if None in results else 'contradicted'
