# Level 0 insights (solved in 15 actions)
- Player: 5x5 piece (blue 9 + yellow b edge, black border) in cyan (a) corridors; black-with-grey-dots (5/3) is wall.
- ACTION3/ACTION4 move player left/right by 6 cells (one tile). Grid of 6-cell tiles.
- Player "floats up": whenever there's open cyan (or a gap) above it, it rises automatically until blocked (camera scrolls to follow).
- Green blocks (e, 5x5 with 3-corners) are destructible: ACTION6 click on a green block removes it (costs an action). Removing one in a wall row opens a gap -> player rises through it if directly below, or when moving under it.
- Goal: reach the pink plus (7) tile. Moving onto it completed the level.
- Row 63: purple (f) bar grows by 1 per action = action counter / budget (64 max?).
- Strategy: find route upward to pink; click green blocks that sit between player and next corridor; move horizontally under the gap.
- ACTION7 untested (likely undo).
