# World model notes
- Tile grid 6px (tiles at cols 13+6k, rows offset by scroll); player 5x5 piece (blue 9 + yellow b). ACTION3/4 = move one tile left/right if open (cyan or cleared). After any action, player rises through open tiles until blocked; viewport scrolls vertically to keep player around rows 37-40.
- ACTION6 on green block -> removed (becomes open/black-gap passable). Clicking non-green: no effect observed.
- Purple (f) hanging blocks w/ b-0-b bottom: player rising to the tile directly beneath -> GAME_OVER.
- ACTION7 = undo last action (costs an action).
- Win: player reaches pink plus tile (rises into it).
- Row 63 purple bar = action count.

- Level 2: orange (c) 5x5 block toggles on ACTION6: solid orange <-> small orange X (X is passable/open, player rises through). Win also by horizontal move onto pink tile.
