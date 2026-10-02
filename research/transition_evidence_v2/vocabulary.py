"""Transition evidence vocabulary, version 2 (draft, not frozen).

Version 2 keeps every version 1 dimension and value unchanged (re-exported below) and adds:
- a stable record identifier;
- the observation context before every action, including failed and unknown dispatches;
- the available actions the environment reported before and after an action;
- an optional masked view: the same measurements restricted to cells outside a supplied mask, with the mask and its
  provenance retained. The unmasked measurements remain the record's primary measurements.

A mask states where changes are set aside. It never states why a region changes: the record does not call a region
a counter, a timer or a HUD.
"""
from research.transition_evidence_v1.vocabulary import *  # noqa: F401,F403  (version 1 values are unchanged)
from research.transition_evidence_v1 import vocabulary as _V1

VERSION = 'transition_evidence_v2'
V1_VERSION = _V1.VERSION

# Where a mask came from. Declared masks are written by a person or a producer from stated evidence; an
# online mask is proposed by a detector from earlier transitions of the same episode only (reserved: no detector
# is part of this draft).
DECLARED, DETECTED_ONLINE = 'declared', 'detected_online'
MASK_PROVENANCE = (DECLARED, DETECTED_ONLINE)

# Action ids that can appear in a reported available-action list: the ARC interface's vocabulary, RESET (0) and
# ACTION1..ACTION7, as bounded by the repository's ARC diagnostic action schema (evidence_comprehension_v1
# ACTION_SCHEMA, action_id 0..7). Whether a policy may *choose* RESET is a separate rule (the arc_action_v12
# action validator); this vocabulary only says which reported ids exist.
ACTION_VOCABULARY = tuple(range(8))
