# Feedback-summary checkpoint diagnostic: completed attempt

**The computed summary improved factual recognition, but did not change the chosen actions in this pilot.** Changed-case recognition rose from 0/4 to 4/4, while all eight complete paired action sequences remained identical. Neither condition completed a first level within its four new actions.

The attempt is independently technically complete. This report contains sanitized aggregates; raw outputs, notebook bindings, model inputs, scope records and collection/replay receipts remain private. The single attempt is consumed and preserved, together with all previous attempts. No additional GPU run was launched during collection or evaluation.

## Runtime and verification

| Check | Result |
| --- | --- |
| Provider | COMPLETE; exact approved version-1 source, authority and settings verified |
| Physical accelerator | One NVIDIA RTX PRO 6000 Blackwell Server Edition |
| Bounded lifecycle | 1604.19 s (26.74 min) / 3,300 s worker limit |
| HTTP generations | 81/81: 16 recognition, 64 policy, 1 canary |
| Offline actions | 116/116: 16 resets, 36 prefix dispatches, 64 new dispatches |
| Local scorecards | 16; zero online game calls or leaderboard submissions |
| Integrity | All 43 downloaded files and all 41 runtime-manifest members verified; exact return marker present |
| Native token audit | All 81 prompt counts reproduced with pinned Transformers 4.57.6 |
| Largest prompt / completion | 4886/8,192; 76/256 (canary cap 16) |
| Generation endings | All 81 stopped normally; none reached the token limit |
| Independent game replay | All 16 conditions restored and replayed; full requests, actions, observations and totals independently checked |
| Cleanup | Owned process groups absent; zero remaining GPU processes; temporary environments and extracted source removed |
| Verification compute | CPU only, no model inference; verifier process cleanup and temporary removal also verified |

The first read-only output download encountered a connection reset after 29 files. Those bytes and the partial collection record are retained unchanged. A separately recorded missing-file download completed the collection. This was not a second GPU attempt. Both collection passes verified the same saved version and authority; no provider write was made.

## Paired factual recognition

The same five-field stateless question was asked separately under recent-raw and recent-summary conditions. The summary computes facts from the displayed evidence, without hidden rules or future outcomes. Recognition answers never entered policy requests and never selected which continuations ran. Invalid and unknown responses remain incorrect on full denominators.

| Measure | Recent raw | Recent summary |
| --- | ---: | ---: |
| Valid recognition responses | 8/8 | 8/8 |
| All five fields correct | 4/8 | 7/8 |
| Recorded step | 8/8 | 8/8 |
| Recorded full action | 8/8 | 8/8 |
| Listed legal controls | 8/8 | 8/8 |
| Any visible cell change | 4/8 | 8/8 |
| Current grid matches historical before-grid | 4/8 | 7/8 |
| Change detected on changed checkpoints | 0/4 | 4/4 |
| No change correctly reported on unchanged checkpoints | 4/4 | 4/4 |

| Game / source step | Latest transition | Raw correct fields / 5 | Summary correct fields / 5 | Same four full actions |
| --- | --- | ---: | ---: | --- |
| ls20 / 2 | changed | 3 | 5 | yes |
| s5i5 / 2 | changed | 3 | 4 | yes |
| cd82 / 2 | unchanged | 5 | 5 | yes |
| cd82 / 3 | changed | 3 | 5 | yes |
| ft09 / 2 | unchanged | 5 | 5 | yes |
| ka59 / 2 | unchanged | 5 | 5 | yes |
| ka59 / 3 | changed | 3 | 5 | yes |
| sc25 / 2 | unchanged | 5 | 5 | yes |

The remaining summary-recognition error was s5i5's current-grid versus historical before-grid comparison. It correctly reported the visible change there. The raw condition reproduced the earlier pattern of answering no visible change on every checkpoint. Summary-assisted success tests reading supplied computed facts; it does not establish independent visual change detection, object discovery, or knowledge of control functions.

## Subsequent policy behavior

Each condition restored its own fresh seed-0 game and exact recorded prefix before acting. The policy and initial historical geometry were unchanged. Only the supplied recent-feedback summary distinguished the conditions. Condition order alternated across checkpoints.

| Measure | Recent raw | Recent summary |
| --- | ---: | ---: |
| Legal, faithfully executed new actions | 32/32 | 32/32 |
| Invalid policy answers | 0 | 0 |
| First level completed within four new actions | 0/8 | 0/8 |
| Visibly changed transitions | 18 | 18 |
| Distinct full actions, summed within conditions | 10 | 10 |
| Repeated full action after an unchanged full observation | 14/14 | 14/14 |
| Prospective change predictions with a yes/no answer | 0/32 | 5/32 |
| Correct yes/no change predictions | 0 | 2 |
| Unknown prospective change predictions | 32 | 27 |

First full actions were identical at **8/8** checkpoints. Complete four-action sequences were identical at **8/8**, including click coordinates. Consequently, these paired game trajectories and outcomes were also the same. Every condition ended at the four-action cap.

The summary produced five non-unknown prospective change predictions: two correct and three incorrect; 27 remained unknown. Raw feedback produced 32 unknown predictions, so its covered-prediction accuracy is not estimable. This does not establish improved prospective prediction. Changed pixels may be an interface indicator or an unhelpful action, and repetition is not intrinsically wrong in every game.

| Cost, excluding shared canary | Recent raw | Recent summary |
| --- | ---: | ---: |
| Generations | 40 | 40 |
| Prompt tokens | 124,731 | 133,338 |
| Completion tokens | 1,370 | 1,351 |

## Interpretation and limits

Making past differences explicit improved factual answers on these checkpoints. That improvement did not transfer to a different action sequence or a completed first level within the short continuation. Recognition was measured in separate calls, so the experiment does not prove that a particular policy call internally recognized or ignored a fact, nor does it identify why the actions stayed unchanged.

The next research question should concern how explicit observed consequences enter action selection: for example, whether requiring a candidate-action comparison or a short testable action-effect hypothesis changes decisions. Such a follow-up would change the intervention and needs a separate frozen design, review and authorization; none is launched or authorized by this report. Do not treat this result as evidence that increasing prompt length alone improves gameplay.

These are eight exposed, correlated checkpoints across six development games, including overlapping cd82/ka59 prefixes, under one deterministic attempt. The conditions compare an entire added text interface, not arithmetic in isolation from redundancy or token overhead. Four actions cannot establish full-game solving or lack of benefit at longer horizons. No significance, generalization, causal mediation, official score, or promotion claim is made.

## Retained bindings

| Artifact | SHA256 |
| --- | --- |
| Reviewed private package | `03e05660e1ff24e92799843c273c565f3aed66b745d9399ad85797c013fdebb1` |
| Independent evaluation | `29f46d944e9cbcf093f60e048ed7e8cc485ae1a3078865720db3a65c9b863843` |
| Complete retained run evidence | `6ea342e12ec43f7f7374f4715b9c76c2b439d344db7a93f673dec9af87cb6cb2` |
| Independent CPU lifecycle | `3c90920a2f436711993c8422feebd75f2e09214a48ebea921df00a4a0dc3d065` |
| Input manifest | `33590dbcc599c6feaca3ce1460c5649a65e1c5de6056f3526c64c3e03a02e92e` |

The [prelaunch review](feedback_summary_probe_live_review_2026-10-19.md), [submission record](feedback_summary_probe_submission_2026-10-19.md), [frozen live protocol](../research/feedback_summary_probe_live_v1/live_protocol.json), [independent evaluator](../research/feedback_summary_probe_live_v1/live_evaluation.py) and [independent summary arithmetic audit](../research/feedback_summary_probe_v1/audit.py) remain available. The earlier [feedback-probe result](feedback_probe_v1_attempt2_results_2026-10-19.md) is preserved separately.
