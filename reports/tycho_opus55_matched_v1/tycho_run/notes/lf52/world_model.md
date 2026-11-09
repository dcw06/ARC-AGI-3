# World model notes (for builder)
- Peg solitaire. Boards of grey cells at 6px pitch; peg = green plus. Click peg -> select (dark-grey 3
  ring) + landing cells highlighted with grey 2 ring. Click highlighted cell -> jump, middle peg removed.
- Carrier (yellow b border, orange c fill, 6x6 box) lives on black wire paths (color 5). ACTION1/2/3/4 =
  up/down/left/right moves it 6px along the wire. When positioned at a virtual cell adjacent to a board
  (same row, one pitch outside edge), it acts as a board cell: can receive a jumped peg and the peg in it
  can jump onto the board. Peg in carrier is drawn green inside orange.
- Win: total pegs across all boards+carriers == 1 (level 0 and 1).
- Stuck state: pegs turn grey, purple key appears at bottom-left (rows 51-63, cols 2-12); click key ->
  reset of board (counter continues).
- Row 0: action counter (one cell per action).
