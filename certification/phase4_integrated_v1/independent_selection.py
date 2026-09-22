"""Independent selection reconstruction from retained observations, not worker claims."""
import json
from certification.phase4_closed_loop_v1.contract import request_for as historical_request

def expected(previous):
    if previous is None:return None
    pre=previous[0]['frames'][-1];frames=previous[1]['frames']
    all_grids=[pre,*frames]
    if not 1<=len(frames)<=64:raise ValueError('replay frame count')
    shape=(len(pre),len(pre[0]))
    if not all(1<=n<=64 for n in shape):raise ValueError('replay dimensions')
    for grid in all_grids:
        if len(grid)!=shape[0] or any(len(row)!=shape[1] for row in grid):raise ValueError('replay shape change')
        if any(type(cell) is not int or not 0<=cell<=15 for row in grid for cell in row):raise ValueError('replay palette')
    eligible=[]
    for index in range(len(frames)-1):
        frame=frames[index]
        if frame!=pre and frame!=frames[-1]:
            count=sum(frame[y][x]!=pre[y][x] for y in range(shape[0]) for x in range(shape[1]))
            eligible.append((-count,index))
    if not eligible:return None
    index=min(eligible)[1]
    return {'grid':frames[index],'frame_index_zero_based':index,'returned_frame_count':len(frames)}

def verify_request(request,history,row,previous):
    baseline=historical_request(history,'no_concrete_examples');baseline['seed']=row['request_seed']
    value=expected(previous)
    if row['arm']=='transient':
        payload=json.loads(baseline['messages'][1]['content'])
        payload['observation']['last_transition_intermediate_grid']=value
        baseline['messages'][1]['content']=json.dumps(payload,sort_keys=True,separators=(',',':'))
    elif row['arm']!='control':raise ValueError('replay arm')
    if request!=baseline:raise ValueError('independent transient/request binding')
    if len(json.dumps(request,sort_keys=True,separators=(',',':'),allow_nan=False).encode())>65536:
        raise ValueError('replay request ceiling')
    if len(json.dumps(request,allow_nan=False).encode())>65536:raise ValueError('replay transport ceiling')
    if len(json.dumps(value,sort_keys=True,separators=(',',':')).encode())>16384:
        raise ValueError('replay selected ceiling')
