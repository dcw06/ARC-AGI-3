# Actor beliefs (level 8)
Same mechanics as L0-7. Tile (j,k): world row 1+6j (turn0 screen coords), col 13+6k; k=-2 = left red column.
Top region: j=-23 'v' hazard row k=0..7 (rising to j=-22 in k>=0 = DEATH, happened attempt 1). j=-21: green in left wall k=-1, purple at k=5. j=-28 row of reds (k=-1..7) visible from j=-22.
Pink at (11,0); reachable by falling down k=-2 (all k=-2 reds must be consumed: clicked reds turn cyan) to (11,-2) then R,R.
Full verified-in-sim route in l8route.PLAN (68 actions); executor l8ex.next_action(i) gives screen click for step i (i = turn index in current attempt).
