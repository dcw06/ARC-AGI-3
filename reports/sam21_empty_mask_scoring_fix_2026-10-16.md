# SAM empty-mask scoring integration fix

The reviewer reproduced a valid integration defect on `1dd4ffb`: the SAM
adapter retained an empty mask as a failed proposal, but the shared validator
rejected it before scoring. An adapter-to-scorer regression reproduces that
exception against the exact baseline source.

The shared validator now accepts empty occupied-cell and boundary lists only
when the prediction explicitly declares `empty_mask: true`. The flag must be
a real boolean and agree with the cells. A supplied empty-mask bounding box
must be null, and a supplied boundary must be empty. Unmarked empty masks,
contradictory flags, malformed coordinates and empty reference masks still
refuse validation.

Empty predictions remain in the selected hierarchy's proposal count. They
have zero IoU with every nonempty reference, cannot match, and count as
unmatched proposals. For complete reference inventories they lower precision
and increase the unmatched/false-positive count under that inventory. For
incomplete inventories precision remains unavailable and the proposal stays
unadjudicated. A correct mask plus an empty mask therefore has precision
1/2, not 1/1.

| Verification | Result |
|---|---|
| Baseline `1dd4ffb` | New adapter-to-scorer regression raises the reported strict-mask exception |
| Fixed Linux/Python 3.12 suite | 73 tests passed, zero failures, errors or skips |
| Full evaluation regression | Empty SAM mask traverses frame/source validation and remains in the denominator |
| Edge cases | All-empty proposals, empty/incomplete inventories, hierarchy separation, strict flag types and inconsistent metadata covered |
| Retained outputs | All six SAM and component frame score dictionaries are identical in the original Linux/Python 3.12 environment |
| Saved-logit replay | Corrected evaluator passes every proposal directly to scoring; the complete evaluation reproduces byte for byte |
| Original masks | All 22 SAM masks nonempty; no cells, seeds, references or candidate selections changed |
| Reported SAM result | Still 12/37 IoU matches, 6/37 exact masks, 12/22 precision |
| New inference / GPU / provider calls | Zero / zero / zero |

The original comparison, validation receipts, private inference files and
consumed attempts are preserved. The historical source locks are not rewritten
to cover the fix. [Source-bound validation](sam21_empty_mask_scoring_fix_validation_2026-10-16.json).

A separate human-seed condition would help isolate SAM's boundary extraction
from MolmoPoint's missing or misplaced seeds. It should preserve these results
and use the same candidate-selection, projection and scoring rules; it is not
part of this code fix.
