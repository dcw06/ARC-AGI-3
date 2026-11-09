# Level 0 insights (solved in 8 actions)
Game = PEG SOLITAIRE on a board of cells. Cell pitch 6px: cell (r,c) occupies rows 12+6r..15+6r, cols 11+6c..14+6c (4x4 grey '1' square; peg = green 'e' plus-shape).
Board L0: 3x7 top + 4 more rows under cols 4-6 (L-shape). Border color 5, shadow 9.
Mechanics: click a peg -> selects it (dark-grey 3 ring around it); legal landing cells shown with grey '2' ring outline.
Click a highlighted landing cell -> peg jumps over an orthogonally adjacent peg, the jumped peg is removed.
Row 0 HUD: one '1' cell added per click (move counter, any click incl. selection). Probably a budget limit (unknown, 64?).
Goal: reduce to a single peg (won when 1 peg left; position seemed not to matter / or was fine).
Strategy: each jump = 2 clicks (select + target). Plan whole solution with a solver before clicking.
Winning: final jump (3,5)->(5,5) over (4,5) leaving 1 peg.
Note: multiple take_action calls in one turn - only first applied apparently; do one per turn.
