- Parallel take_action calls in one block silently executed only the first; the tool should error or warn on the others.
- Parsing turn_*.txt for previous levels needed a custom parser; a wmlib.load_level_frames(level) helper would help.

- Level 5: the builder confidently confirmed my wrong 'red is consumed, level unwinnable' belief (it only saw the parts of the map I had explored), which led to a costly RESET. A reminder like 'unexplored map regions may contain more objects' in the no-plan reports would help.

- Level 6: wmlib.animation_grids with root= for archived attempts needed trial-and-error (directory path vs event dict); a single documented 'load all frames incl. animations for level L attempt A' helper would save time.
