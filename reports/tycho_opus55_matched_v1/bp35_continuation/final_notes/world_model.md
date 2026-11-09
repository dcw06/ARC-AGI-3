# World model notes
- Tile grid 6px (tiles at cols 13+6k, rows offset by scroll); player 5x5 piece (blue 9 + yellow b). ACTION3/4 = move one tile left/right if open (cyan or cleared). After any action, player rises through open tiles until blocked; viewport scrolls vertically to keep player around rows 37-40.
- ACTION6 on green block -> removed (becomes open/black-gap passable). Clicking non-green: no effect observed.
- Purple (f) hanging blocks w/ b-0-b bottom: player rising to the tile directly beneath -> GAME_OVER.
- ACTION7 = undo last action (costs an action).
- Win: player reaches pink plus tile (rises into it).
- Row 63 purple bar = action count.

- Level 2: orange (c) 5x5 block toggles on ACTION6: solid orange <-> small orange X (X is passable/open, player rises through). Win also by horizontal move onto pink tile.

- Level 3: red (8) block ACTION6 -> toggles gravity (player moves down until blocked when gravity down; up when up). Win by rising into pink after flipping gravity back up.

- Level 4: same rules; red gravity blocks appear to be consumed after click (disappear). Win again by horizontal move onto pink. Keep green tiles directly beneath purple hazards as ceilings. Only one take_action is committed per turn.

- Level 5: red is NOT consumed permanently — after a click it disappears from its spot but a red appeared elsewhere later (top of k=6 shaft above upper room). Do not hard-code 'red consumed => parity unwinnable'. ACTION7 undo after red click fully restores. Horizontal move onto pink (gravity down, lower corridor) won. Walking under a down-facing hazard with gravity down is safe. Orange X can be clicked solid to act as floor when gravity is down.

- Level 6: left column cols 1-5 = stack of red tiles (one per tile row); clicking ANY red flips gravity and turns that red cyan. Win by falling into pink (gravity down). Tools: stitch.py (world map from frames incl. animations), l6solver.py (tile classifier + settle), l6bfs.py (BFS w/ restricted orange set, visible-only clicks). Camera: player at screen row 37 when gravity up, 27 when down (approx).

- Level 7: purple blocks (f, 3fff3 corners, not the b0b hazards): ACTION6 on purple removes it and spawns purple in each 4-neighbour cell that is open cyan (not the player cell, existing purples unchanged). Acts as a "spreading stepping-stone" tool: click purple above to climb, purple beside to create floors/walls. Hazard rule unchanged (rising into tile directly under b0b = death). Win again = entering pink (horizontal move with gravity down).
