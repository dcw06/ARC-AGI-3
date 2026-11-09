# Actor beliefs (level 1)
- Same mechanics as level 0: 6px tiles, ACTION3/4 move left/right one tile, player floats up until blocked, camera scrolls. ACTION6 on green removes it. Row 63 = action counter bar (purple grows).
- NEW: purple (f) blocks with yellow/white bottom (b 0 b) hanging from ceilings are HAZARDS: player ending directly under one (rising into tile beneath) -> GAME_OVER (level 1 attempt 0 turn 6).
- Level 1 plan: click (33,39),(27,39), right x3 -> player rises into col 37-41 shaft (view scrolls 48 rows). Then go left by removing greens at rows 37-41 cols 31-35,25-29,19-23,13-17 plus (33,15), rise at col 13-17 into upper cyan room, move right to col 31-35 (no purple), click green column above, rise.
