"""Bounded iterative-deepening DFS on the current visible terrain model."""
from research.ls20_dfs_v1.planner import point, DIRECTIONS, STEP


def iddfs(terrain, start, *, blocked=(), max_depth=96, max_nodes=50000, check=lambda:None):
    """Search shortest depths first, without dispatching or simulating the game.

    Optimality concerns only this unweighted, supplied-footprint graph; it says
    nothing about unknown object effects or the environment's actual rules.
    """
    start=point(start);goal=point(terrain.goal)
    if type(max_depth) is not int or not 0<=max_depth<=96:
        raise ValueError('depth cap required')
    if type(max_nodes) is not int or not 1<=max_nodes<=50000:
        raise ValueError('expansion cap required')
    if any((start[i]-goal[i])%STEP for i in (0,1)):
        return dict(status='no_route',action_ids=[],centers=[],expanded_nodes=0,visited_nodes=1)
    blocked=set(blocked);edges={};expanded=0;seen={start}
    class SearchCap(Exception):pass
    def distance(p):return (abs(p[0]-goal[0])+abs(p[1]-goal[1]))//STEP
    def adjacent(p):
        if p not in edges:
            rows=[]
            for action in DIRECTIONS:
                check()
                target=None if (p,action) in blocked else terrain.edge(p,action)
                if target is not None:rows.append((distance(target),action,target))
            edges[p]=[(a,q) for _,a,q in sorted(rows)]
        return edges[p]
    def visit(p,remaining,path,actions,best):
        nonlocal expanded
        check()
        if p==goal:return actions[:],path[:]
        if remaining<=0 or distance(p)>remaining:return None
        if expanded>=max_nodes:raise SearchCap()
        expanded+=1;seen.add(p)
        for action,q in adjacent(p):
            if q in path or best.get(q,-1)>=remaining-1:continue
            best[q]=remaining-1
            answer=visit(q,remaining-1,path+[q],actions+[action],best)
            if answer is not None:return answer
        return None
    try:
        for limit in range(distance(start),max_depth+1):
            answer=visit(start,limit,[start],[],{start:limit})
            if answer is not None:
                actions,centers=answer
                return dict(status='route',action_ids=actions,centers=[list(p) for p in centers],
                            expanded_nodes=expanded,visited_nodes=len(seen),algorithm='iterative_deepening_DFS')
    except SearchCap:
        return dict(status='search_cap',action_ids=[],centers=[],expanded_nodes=expanded,visited_nodes=len(seen))
    return dict(status='no_route',action_ids=[],centers=[],expanded_nodes=expanded,visited_nodes=len(seen))
