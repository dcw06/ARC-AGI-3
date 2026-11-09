# Level 5 insights (solved; 16 wasted actions in attempt 0 + RESET + ~51 actions in attempt 1)
- KEY NEW FACT: red gravity blocks are NOT consumed. Clicking red toggles gravity; the red's animation shrinks it, BUT the red then moves 1 tile in the new gravity direction... More precisely, it was seen at a NEW place later (L5: start-room red at world tile row -1 k=4 was gone, but a red appeared at the top of the k=6 shaft (screen 1-5 cols 49-53 when the player was in the upper room)). Treat red as "relocates", not "disappears": before assuming you are stuck, scan the whole map (walk around) for reds.
  Earlier belief "red is single-use / parity unwinnable" was WRONG and cost a RESET.
- ACTION7 (undo) after a red click restored the state completely (gravity + red); it's a normal undo.
- Clicking pink does nothing.
- Hazard purple b0b: walking horizontally under a down-facing hazard with gravity DOWN was safe (fell away immediately).
- Orange X tiles can be clicked to become solid floors (used to stop falls onto upward-facing hazards and to bridge).
- Winning route: R x5, click red (fall to corridor), L x4, click corridor red (rise back to start room top, gravity up), R,R, L,L (into upper room via k=4 shaft), click X k=3 to solid, L,L (rise to top area), R,R,R (to under k=6 shaft), click red found above shaft (gravity down, fall), click X (orange) to make floor, L x3, click orange to open, R,R (fall through shaft), L,L (fall under hazards safely), click X at k=4 and k=5 in start-room bottom row to make floor, R,R,R,R (fall down k=6 shaft into corridor lower row with gravity down), L x6 -> horizontal move onto pink = WIN.
- Lesson: when a mechanic appears to make the level unwinnable, the belief is probably wrong — explore the rest of the map first rather than RESET.
