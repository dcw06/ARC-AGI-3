# Level 1 insights (solved; ~43 actions this attempt + 6 in a failed attempt)
- Mechanics same as level 0: 6px tiles; ACTION3/4 move one tile left/right; player floats UP automatically through open (cyan / cleared) tiles until blocked; camera scrolls to keep player near rows 37-40.
- ACTION6 on a green (e) 5x5 block removes it (one action each). Only ONE take_action executes per turn.
- HAZARD: purple (f) blocks with yellow/white bottom (b 0 b) hanging from ceilings. If the player floats up into the tile directly below one -> GAME_OVER. Plan rise columns to avoid purple columns.
- ACTION7 = UNDO (restores previous state, still costs an action / bar grows).
- Goal: pink plus (7). Floating up into its tile (clicking green directly above player in the pink's column) completed the level.
- Row 63 purple bar = action counter.
- Strategy: map the whole level by scrolling (views shift), find a column path to the pink that does not pass under purple; clear greens in the needed row to traverse horizontally (greens act as walls blocking horizontal movement too). Plan before acting; careful clicks after each scroll — screen coords change after every rise.
