# Level 3 insights (solved in 23 actions, no deaths)
- NEW: red (8) 5x5 blocks embedded in walls = GRAVITY FLIP. ACTION6 on red toggles gravity direction (up <-> down) for the player; player then falls/rises until blocked; camera follows. Red blocks are clickable even when far from player.
- Rest same: 6px tiles, ACTION3/4 move one tile, green click-removed, purple b0b hazards (only dangerous when rising directly beneath), pink plus = goal (rising into it won).
- Pattern used: rise to top, click red -> fall down through room, clear greens below to open a shaft, walk, click red to flip gravity again, walk under pink in floor row, click red -> rise into pink = win.
- Next levels likely combine red/orange/green/purple; plan direction of gravity before each walk; in down-gravity, hazards may also matter beneath (purple hangs from ceilings, untested when falling).
