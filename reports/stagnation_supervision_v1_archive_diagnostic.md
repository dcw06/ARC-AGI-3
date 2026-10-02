# Stagnation supervision v1: archive diagnostic (CPU only; descriptive, not validation)

| | |
|---|---|
| Code | `research/stagnation_supervision_v1/archive_diagnostic.py` |
| Retained result (write-once) | `reports/stagnation_supervision_v1_archive_diagnostic.json` |
| Test | `tests/test_stagnation_supervision_v1_archive.py` (the result reproduces exactly from the locked archive) |

**What ran.** The frozen detector, unchanged, observed the 144 archived development transitions of
action-effect-history v1: 12 episodes of 12 steps over ar25, s5i5 and wa30, with a baseline and a history arm in two
blocks.
- **Frozen inputs.** `trigger_spec.json`, `detector.py` and `thresholds.py` are byte-identical; their SHA-256 hashes
  are recorded in the result and tested. The parameters are `state_action_recurrence = 2` and
  `tiny_effect_repeat = 10`, with a cooldown of 6.
- **View.** Full-frame, unmasked fingerprints. The masks module was not used.
- **Archive access.** The archive was opened only after its SHA-256 matched the lock in
  `reports/action_effect_history_v1_archive.json`, and each episode member only after its own locked hash matched.
- **Raw rebuild.** Raw transitions were rebuilt with the replay script's own `verified_zip`, `raw_step` and
  `parse_action`, imported rather than copied.
- **Not used.** No GPU, no model, no tuning.

**These 144 transitions have no independent stagnation labels.** All categories below are descriptive. The traces
were not used to choose or change any threshold, and they are not an independent validation of the detector.

## Candidate categories (defined before the run)

The definitions are in the module docstring, committed in c666332 before the detector was run on these traces. Only
acknowledged steps count, and patterns are checked within one segment.

**Repeated-action patterns:**

| Code | Name | Definition |
|---|---|---|
| M1 | Exact repeat, no change | The same (pre-frame, exact action) at least twice with `no_observed_change` |
| M2 | Same action, no change | The same exact action at least twice with `no_observed_change`, whatever the pre-frame |
| M3 | Action-id no-change streak | At least 3 consecutive steps with the same action id (coordinates may differ), each `no_observed_change` |
| M4 | Repeated tiny effect | At least 3 consecutive identical actions, each changing 1–4 cells of the final frame |

**Candidate missed repeated-action episode.** Some pattern qualifies, and the detector neither triggers nor fires
under cooldown at any step from the qualifying step to the end of the segment.

**Potential false interruption.** A trigger where at least one of the last 3 acknowledged steps reached a final frame
not seen earlier in the segment, meaning observed change into new states was ongoing. This is a proxy: a new frame
is not progress.

## Results per game

| Game | Episodes | Triggers | Episodes with a trigger | Firing steps (incl. cooldown-suppressed) | Candidate missed repeated-action episodes | Candidate false interruptions | Patterns found | Distinct pre-frames / steps |
|---|---|---|---|---|---|---|---|---|
| ar25 | 4 | 8 | 4 | 36 | 0 | 0 | M1 ×10, M2 ×10, M3 ×2 | 4 / 48 |
| s5i5 | 4 | 2 | 2 | 6 | 2 (4 patterns) | 2 | M4 ×6 | 48 / 48 |
| wa30 | 4 | 1 | 1 | 1 | 0 | 1 | none | 44 / 48 |
| **total** | 12 | **11** | 7 | 43 | **2** | **3** | | |

**Every trigger.** Full traces are in the JSON.

| Episode | Step | Signal | Value | Cited evidence | Candidate false interruption? | Note |
|---|---|---|---|---|---|---|
| b1-ar25-baseline | 1 | state_action_recurrence | 2 | [0, 1] | no | |
| b1-ar25-baseline | 7 | state_action_recurrence | 4 | [2, 7] | no | |
| b1-ar25-history | 1 | state_action_recurrence | 2 | [0, 1] | no | |
| b1-ar25-history | 7 | state_action_recurrence | 3 | [4, 7] | no | |
| b2-ar25-baseline | 1 | state_action_recurrence | 2 | [0, 1] | no | |
| b2-ar25-baseline | 7 | state_action_recurrence | 5 | [4, 7] | no | |
| b2-ar25-history | 1 | state_action_recurrence | 2 | [0, 1] | no | |
| b2-ar25-history | 7 | state_action_recurrence | 3 | [4, 7] | no | |
| b1-s5i5-history | 9 | tiny_effect_repeat | 10 | [0..9] | yes | Every step changed 1–2 step-bar cells, so every frame is new |
| b2-s5i5-history | 9 | tiny_effect_repeat | 10 | [0..9] | yes | Same pattern |
| b2-wa30-baseline | 7 | state_action_recurrence | 2 | [6, 7] | yes | Action 2 changed 0 cells at step 6 and was repeated from the same frame at step 7 (1 cell). Step 5 had moved the block 28 cells. |

**What happened in each game:**
- **ar25.** Every frame is identical in every episode: 1 distinct pre-frame per episode. Every click and every
  ACTION7 changed 0 cells. Exact (frame, action) repeats begin at step 1, so the detector triggers at steps 1 and 7
  in all four episodes, with the cooldown suppressing the steps in between. There are no misses, and no trigger
  happened during observed change.
- **s5i5, the step bar.** Every action changes 1–2 cells of the bottom-row step bar. Under the full-frame
  fingerprint, every s5i5 frame is unique (48 of 48), so `state_action_recurrence` can never fire there.
  - **History arms:** the same cell (11, 10) was clicked 12 times. The detector fired only through
    `tiny_effect_repeat`, at step 9 (the 10th action), which leaves 2 of 12 actions after any intervention.
  - **Baseline arms:** they mixed four positions. Their identical-click runs reached only 3–6 actions, so they
    are the 2 candidate missed episodes (M4 at steps 3–5 and 9–11 in each).
  - **The declared region:** transition_evidence_v2 has a declared region for this step bar. Using it in the
    detector is a separate, separately versioned experiment and was not done here. The blind spot stays open.
- **wa30.** A block moves 24–33 cells on most actions. Frames are almost all new (44 of 48 pre-frames distinct),
  including the baseline arms that alternate ACTION2 and ACTION3. The single trigger came from a 0-cell step
  followed by the same action from the unchanged frame. It is flagged as a candidate false interruption only because
  the block had moved into a new frame 2 steps earlier.

**Dispatch status, terminal states and resets.**
- All 144 dispatches were acknowledged: no failed, unknown or missing observations, so the detector's evidence
  rules for those cases were not exercised by this archive.
- No environment events were reported: no level completion, terminal state or reset.
- Each episode is one segment, and the detector's statistics start fresh in each episode.

## Qualifications

- **Triggers are not interventions.** The detector fires on these archived trajectories in 7 of 12 episodes, but
  the archive was played without any intervention, so it shows nothing about whether intervening helps.
- **What zero triggers would have meant.** It would have meant this detector cannot show an intervention effect on
  these 12-step archived episodes. It would not have shown that supervision cannot help, or that the detector never
  fires in longer episodes.
- **Short episodes.** 12 steps barely accommodate the cooldown of 6. In s5i5 the only trigger comes at action 10 of
  12.
- **Proxy categories.** The candidate categories are mechanical proxies chosen before the run. "Missed" and "false
  interruption" here mean "matches the stated pattern", not "was wrong".
- **Not a sample.** Three development games and two arms whose actions repeat across blocks are not a sample of
  real play. Blocks 1 and 2 of the history arm are near-identical: same actions, same triggers.
