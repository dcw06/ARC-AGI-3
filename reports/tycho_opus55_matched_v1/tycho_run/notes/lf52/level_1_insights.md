# Level 1 insights (solved; 13 wasted + RESET + 40 actions — could be ~22 optimal)
Game = PEG SOLITAIRE across multiple boards connected by black wires (color 5, 2-px wide).
- Boards: white frame, grey 4x4 cells at 6px pitch, pegs = green 'e' plus shapes.
- CARRIER: yellow(b)/orange(c) 6x6 box sitting on a wire. It is a movable single cell.
  ACTION1-4 (up/down/left/right) move the carrier 6px along the wire (only along wire path; moves into
  impossible directions just count a turn).
- Carrier counts as a board cell when docked adjacent to a board edge (positioned exactly where the
  next cell (r, c±1) would be). Pegs can jump INTO the carrier (it shows grey '2' landing ring) and
  out of it onto another board.
- Strategy used: on top board (1 row of pegs), jumps 1->3, 3->5 leaves peg at c=5; move carrier to
  dock at top board right side (cell (1,7)); peg at (1,5)? Actually: jumps c1 over c2 -> c3, c3 over c4 -> c5,
  then c5 over c6 -> carrier (removes c6). Carrier with peg then travels the wire to dock left of
  bottom board cell (1,0); jump carrier peg over (1,0) -> (1,1). One peg left => WIN.
- Clicking a peg with no moves: wasted click. When stuck (no legal moves), pegs grey out and a purple
  key appears bottom-left; clicking it resets the board (but move counter keeps going).
- Row 0 HUD: one '1' per action (all actions incl. moves). Budget probably 64.
- Efficiency: plan the full route first: move carrier to dock first (wire moves), then jumps.
  Note: wire length matters; count steps = wire distance / 6.
Next level likely: more boards / carriers / longer wires; maybe multiple carriers or carrier must ferry
several pegs.
