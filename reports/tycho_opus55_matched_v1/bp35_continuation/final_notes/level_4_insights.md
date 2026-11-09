# Level 4 insights (solved in 35 actions, no deaths)
- Same mechanics: 6px tiles, ACTION3/4 move one tile, player rises/falls (gravity) until blocked, camera follows. Green click-removed, orange toggles solid<->X, red toggles gravity, purple b0b hazards, pink plus = goal (moving horizontally onto it at top row won).
- IMPORTANT: only ONE take_action per assistant turn is committed; parallel take_action calls are dropped (only the first executes).
- Red gravity blocks may be single-use (red 8 disappeared from map after clicking; later another red appeared further down). Clicking a non-interactive tile wastes an action (bar grows, nothing else).
- Wasted ~10 actions exploring the lower area (gravity down, orange toggles) — the actual solution was short: from start, go to the shaft below the top-right green stack, clear the bottom row of greens (row under purple-hazard row keep!), rise into that cleared row, walk left into the pink room, rise to top, step onto pink.
- LESSON: before descending, check whether the goal is reachable directly from the start area by clearing greens; the top greens row under purple hazards should be kept as a ceiling.
