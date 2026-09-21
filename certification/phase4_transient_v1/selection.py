"""Bounded observation-only selection. Never interprets game semantics."""
import json

FIELD = 'last_transition_intermediate_grid'
MAX_REQUEST_BYTES = 65536
MAX_FIELD_BYTES = 16384
MAX_FRAMES = 64

def encoded(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')

def grid_shape(grid):
    if not isinstance(grid,list) or not 1<=len(grid)<=64:
        raise ValueError('grid rows')
    if not isinstance(grid[0],list) or not 1<=len(grid[0])<=64:
        raise ValueError('grid columns')
    width=len(grid[0])
    if any(not isinstance(row,list) or len(row)!=width or
           any(type(c) is not int or not 0<=c<=15 for c in row) for row in grid):
        raise ValueError('ragged/nonpalette grid')
    return len(grid),width

def select(previous_transition):
    if previous_transition is None:
        return None
    before,after=previous_transition
    pre=before['frames'][-1];shape=grid_shape(pre)
    frames=after['frames']
    if not isinstance(frames,list) or not 1<=len(frames)<=MAX_FRAMES:
        raise ValueError('returned frame limit')
    if any(grid_shape(f)!=shape for f in frames):
        raise ValueError('transition shape change')
    final=frames[-1];winner=None;best=-1
    for index,frame in enumerate(frames[:-1]):
        if frame==pre or frame==final:
            continue
        changed=sum(a!=b for ra,rb in zip(pre,frame) for a,b in zip(ra,rb))
        if changed>best:
            winner={'grid':frame,'frame_index_zero_based':index,'returned_frame_count':len(frames)}
            best=changed
    if len(encoded(winner))>MAX_FIELD_BYTES:
        raise ValueError('selected field byte limit')
    return winner

def enforce_payload(request):
    if max(len(encoded(request)),len(json.dumps(request,allow_nan=False).encode('utf-8')))>MAX_REQUEST_BYTES:
        raise ValueError('request byte limit')
    for message in request.get('messages',[]):
        if not isinstance(message.get('content'),str):
            raise ValueError('text-grid request only')
    # Canary has no observation payload; it still receives the byte/token guards.
    try:
        payload=json.loads(request['messages'][1]['content'])
    except (KeyError,IndexError,json.JSONDecodeError):
        return
    if not isinstance(payload,dict) or 'observation' not in payload:
        return
    obs=payload['observation']
    grid_shape(obs['current_grid'])
    if FIELD in obs and len(encoded(obs[FIELD]))>MAX_FIELD_BYTES:
        raise ValueError('selected field byte limit')
    value=obs.get(FIELD)
    if value is not None:
        if not isinstance(value,dict) or set(value)!={'grid','frame_index_zero_based','returned_frame_count'}:
            raise ValueError('transient field structure')
        if grid_shape(value['grid'])!=grid_shape(obs['current_grid']):
            raise ValueError('selected shape')
        i,n=value['frame_index_zero_based'],value['returned_frame_count']
        if type(i) is not int or type(n) is not int or not 2<=n<=MAX_FRAMES or not 0<=i<n-1:
            raise ValueError('transient index/count')
