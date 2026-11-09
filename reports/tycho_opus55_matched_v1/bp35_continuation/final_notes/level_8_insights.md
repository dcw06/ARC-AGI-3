# Level 8 insights (attempts 0,1 died; attempt 2 should win in ~68 actions)
- Pink in bottom-left pocket only reachable via left red column k=-2 (falling down when all k=-2 reds below are consumed). Clicked reds become cyan (passable).
- Deaths: rising into tile directly under a 'v' (b0b-bottom) hazard row. Attempt0: rose up k=2 to j=-9 under hazard row j=-10. Attempt1: opened orange row j=-14 at k=2 and rose to j=-22 under top hazard row j=-23.
- Safe entry to top area: open orange at k=5 where purple at (-21,5) stops the rise.
- Top area: row of reds at j=-28 (each click flips gravity, consumed). Green in left wall at (-21,-1) gives access to k=-2.
- Then: flip gravity down with a top red, fall onto next k=-2 red, click it (flip up, rise back), repeat until clear; fall to pink pocket and walk R.
- Tools: l8plan.py (tile map+sim), l8route.py (PLAN), l8ex.py (screen-click translator).
