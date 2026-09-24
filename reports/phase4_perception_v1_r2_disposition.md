# Paired perception R2: completed development diagnostic

Kaggle notebook [arc3-phase4-perception-v1-r2](https://www.kaggle.com/code/daichongwei06/arc3-phase4-perception-v1-r2), version 1, reached `KernelWorkerStatus.COMPLETE` with no provider failure message. The frozen independent replay returned `passed=true`, no errors and verdict `completed`, exactly matching the Kaggle evaluation. It verified request identity, image processor/token parity, responses and finish reasons, deadlines, monitoring, finalization and independent GPU cleanup. This is technical acceptance of the diagnostic, not perception or gameplay success.

## Results

All ten paired board answers were valid, complete JSON (`finish_reason=stop`). At the frozen object-matching threshold (bounding-box IoU ≥ 1/2), detection recall was **0/11 reference objects for text and 0/11 for images**. The three P1 relationships and the one shape relation in each of P2–P4 earned zero transform credit in both representations. P5 has no same-shape reference relation, so its transform denominator is zero. Each text/image pair is correlated by board; the five boards do not represent five development games.

| Board | Reference objects | Text detected | Image detected | Observed answer pattern |
| --- | ---: | ---: | ---: | --- |
| P1 retained ar25 | 3 | 0 | 0 | Text proposed broad rectangular regions; image proposed six small boxes at different positions. |
| P2 synthetic rotation | 2 | 0 | 0 | Text proposed six repeated boxes; image proposed two boxes offset from the references. |
| P3 synthetic reflection | 2 | 0 | 0 | Text proposed six boxes; image again proposed two offset boxes. |
| P4 synthetic markings | 2 | 0 | 0 | Text proposed six boxes; image proposed two offset boxes. |
| P5 synthetic different shapes | 2 | 0 | 0 | Text proposed six boxes; image proposed two offset boxes. |

For a concrete check, P2's reference boxes are `[8,10,16,18]` and `[38,30,46,38]`. Its image answer gave `[15,15,23,23]` and `[41,41,49,49]`, which do not meet the overlap threshold. The image canary correctly identified `top_left`, color 8, so this was not an image-transport rejection. The text requests also failed object detection. This study gives **no demonstrated advantage for images over raw grids** and identifies object localization as a lead for further grounding work. It does not prove that either representation cannot work, nor that a changed prompt or policy would solve a game.

Both interface-control answers were valid. They emitted the specified click `(7,23)` using action 6, the non-coordinate action 1, and the expected directional list/null. Each nevertheless marked all seven action IDs as taking coordinate arguments, yielding only **1/7** correct argument classifications. These controls supplied interface information and executed no actions; their result is a control-description weakness, not a measured game effect.

## Lifecycle, evidence and accounting

The startup canary passed. Model startup took **618.802 seconds**. All 13 study calls completed within a roughly **45.675-second** request window; their summed service latency was **44.303 seconds**. There were **14 completions total**, including the text startup canary: **53,635 prompt tokens** and **6,222 completion tokens**. No environment actions, scorecards, retries or scored submissions occurred.

Supervisor elapsed was **795.031 seconds** and notebook finalization elapsed **797.068 seconds**, within the 2,280-second internal and 2,400-second provider limits. The independent cleanup record shows zero remaining GPU processes and absent owned process groups; the notebook result confirms source and dependency cleanup. Monitoring covered the worker through teardown.

The SDK account-wide GPU usage changed from **9,881.173 seconds** immediately before launch to **10,687.795 seconds** after completion: **806.622 seconds** observed difference. This can include account-level timing or concurrent usage; it is not an exact per-attempt bill. The Kaggle quota response's raw allowance and SDK seconds conversion disagree, so the raw provider observations are retained. Exact billed seconds remain unknown. Attempt `pc1-ccf1c99ac67e4f3781f6f30b7726fd87` remains consumed; no retry authority exists.

All **24 downloaded files** (3,053,382 bytes) were checked against `phase4_perception_v1_r2_download.json`. The completed archive also contains provider observations and source, compute, reservation and launch receipts:

`evidence/phase4-perception-v1-r2-completed.zip`

SHA-256: `5928b10aabf729ad45db8a72a466b25d70c373228d6732d2679c2591f70b1d37`

Read-only replay from a clean checkout with the project's Linux development environment:

```sh
python scripts/replay_phase4_perception_v1_r2_completed.py
```

The command verifies the R2 source and notebook lock, archive and member hashes, every downloaded file, terminal provider status, and the frozen live evaluator. `phase4_perception_v1_r2_completed_clean_replay.json` records a second replay from an isolated copy of only the frozen notebook sources and archive.

This closes the single perception diagnostic attempt. Production one-scorecard/110-distinct-game certification, workload admission limits, solving performance and exact billing reconciliation remain open. A next development study should first inspect the retained responses and boards for specific localization failures; another unchanged comparison would add little evidence.
