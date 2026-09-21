# Retained offline inspection artifacts

**Recovery update — September 21, 2026:** Both files listed as missing below were
recovered from local Git blobs with exact historical hashes. The restored generator
reproduced all 11 locked artifacts in a temporary directory. The historical lock
and outputs remain unchanged. See the separately versioned
[ft09 information trace and proposal](../phase4_ft09_information_v1/findings.md)
for the recovery record, observation-only/source-assisted distinction, and a
narrower proposal. The publication-time account below is retained as history.

Open [frames.html](frames.html) locally to inspect all 600 retained actions and
their returned frames. [audit.json](audit.json) contains the per-action analysis;
[source_excerpts.json](source_excerpts.json) contains matched game-source excerpts.
The PNG files illustrate selected cases using a false-color palette.

At publication on September 21, 2026, all 11 retained artifact hashes and the
input evidence archive hash matched the original [inspection lock](inspection-lock.json).
Two files referenced by that lock were absent from the workspace:

- `scripts/inspect_phase4_closed_loop_v1.py`
- `reports/phase4_closed_loop_v1_offline_findings.md`

The original lock is preserved unchanged. This publication is therefore a
partial inspection package: it retains the viewer, numerical audit, illustrations,
and source excerpts, but not the original generator or findings narrative.
Full regeneration from this package alone is not claimed. The lock's historical
validation statement records the earlier inspection, not a new execution of its
missing generator.

The audit records 263 unchanged final-frame transitions, including 108 with
intermediate visual changes. Reduced repetition did not demonstrate improved
level completion. No prompt promotion, policy change, compute authorization, or
GPU launch is part of this publication.
