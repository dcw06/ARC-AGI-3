# Level 2 insights (solved in 34 actions, no deaths)
- Same core: 6px tiles; ACTION3/4 move one tile left/right; player auto-rises through open tiles; camera scrolls; green (e) removed by click; purple (f, b0b bottom) ceiling hazards; pink plus (7) = goal (moving horizontally onto it, ACTION4, won). Row 63 = action counter.
- NEW: orange (c) blocks are TOGGLES. ACTION6 on solid orange -> small orange X (passable, player rises/moves through). ACTION6 on X -> solid orange (wall). Used both to open paths and to create ceilings that stop rising before purple hazards.
- Typical pattern: clear/toggle a row of tiles above to make a horizontal corridor at the stop height, then walk; rising stops under first solid.
- Strategy: dump full grid with print after each scroll; plan column rises; clicks use current screen coords (change after each scroll).
- Expect next levels to combine green/orange/purple with possibly new block types; check each new type with one click.
