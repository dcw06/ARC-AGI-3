# Candidate action-effect and feedback use: CPU preparation r2

The preceding real-model study improved factual recognition with a computed summary, but all eight paired action sequences stayed identical. This diagnostic asks whether explicit comparison of two candidate effects and review of an observed outcome helps the policy forecast consequences and choose its next action.

**CPU preparation is complete. No neural inference, Kaggle upload, reservation or GPU launch has occurred for this diagnostic.** The prospective design and scripted execution path are reviewable. A bounded live worker, independent live evaluator and exact private launch package remain to be implemented and reviewed.

| Element | Proposed design |
| --- | --- |
| Cases | All eight unchanged, exposed checkpoints across six development games |
| Conditions | Neutral candidate selection versus explicit comparison and outcome review |
| Common evidence | Same factual recent summary, historical initial geometry, recent/current images, two legal full actions and output format |
| Candidates | Repeat the last full action versus a deterministic legal alternative; click alternatives use historical occupied anchors |
| Balancing | A/B assignment swaps every two checkpoints; arm order alternates every checkpoint |
| Decision 1 | Forecast each candidate's changed-cell category, select one, execute its full action |
| Decision 2 | Read the observed change, check the immutable original forecast, forecast again at the new state, select and execute |
| Reference truth | Fresh offline branches for both candidates from the exact same state and action prefix; never included in inference inputs |
| Stops | First-level completion, game over, candidate illegality, invalid output or deadline; no repair, retries or case replacement |

Both conditions return the same compact JSON fields: two candidate forecasts, one selected candidate, whether the previous executed action visibly changed the board, and whether its original magnitude forecast matched. The neutral condition is an active control: it also provides forecasts and review fields. This comparison measures the extra explicit instructions rather than the earlier unrestricted policy. The host dispatches the fixed selected action, so this does not test free target discovery or coordinate selection.

## Endpoint revision before model inference

The binary r1 draft, source archive, input manifest and CPU receipts are preserved, including [its protocol](../research/action_effect_choice_v1/protocol_r1_binary.json). Offline branches showed only **1/8** initial pairs differed on any-cell change, but **4/8** differed in change extent. A resource indicator could change under both controls while the rest of the board behaved differently.

R2 uses these fixed categories: **none (0), 1–4, 5–64, 65+ changed cells, or unknown**. This choice was informed by CPU reference outcomes before any model inference; it is not an independently chosen endpoint or a result from the LLM. Candidate selection and all eight cases remain unchanged. Extent contrasts occur at four checkpoints across three games, including the correlated ka59 pair. Identical-effect pairs stay in the report.

| Primary measure | Required accounting |
| --- | --- |
| Both candidate forecasts | Correct, incorrect, unknown and invalid on full response denominators; contrast opportunities separately |
| Reading the previous result | Accuracy against the actual before/after images and factual summary |
| Checking the original forecast | Compare its immutable count category with the actual result; unknown forecasts separately |
| Paired choices and sequence equality | Full action identity including coordinates; switching is not inherently correct |
| Stopped or missing second decisions | Scheduled checkpoint, not-reached count and reason retained; scheduled and observed denominators separately |

Round-2 forecasts concern a new state and cannot repair round-1 scores retroactively. Correctly reporting that an earlier forecast was unknown is not an accurate original prediction. Unknowns remain explicit and should not be interpreted as proof of inability when the evidence is insufficient. Changed pixels can be interface indicators, and extent is not usefulness, object motion or progress. Unexecuted forecasts require verified reference branches before scoring.

## Completed CPU verification

| Check | Result |
| --- | --- |
| Contract and fault tests | 21 passed on Linux; zero failures, errors or skips |
| Input preparation | 18 inference-eligible files; two builds match byte for byte |
| Scripted replies | 32 injected callbacks, no model server or neural inference |
| Actual offline conditions / deterministic replays | 16 / 16 |
| Fresh reference branches | 48; selected branches match the full actual outcome |
| Native processor audit | 192 request variants, 176 distinct bodies, Transformers 4.57.6 |
| Largest prospective prompt | 5033/8,192 tokens |
| Initial category contrasts | 4/8; all eight cases retained |
| CPU isolation and cleanup | Network isolated, GPU disabled, owned processes absent and temporary environments removed |
| Previous evidence | Completed feedback-summary run and all earlier preservation records unchanged |

Scripted replies deliberately forecast unknown; their scores are not model performance. Counterfactual labels and later input variants generated from branch outcomes stay outside the 18-file inference allowlist. Dynamic request audits cover both possible first choices and every selected-forecast category. Source/input checks, output phase checks, full-action identity, duplicate/invalid output rejection, immutable past-forecast scoring, late-request/dispatch refusal and early stops are tested.

## Proposed live ceiling

| Quantity | Maximum |
| --- | ---: |
| HTTP generations | 33: 32 decisions plus 1 startup canary |
| Conditions / new actions per condition | 16 / 2 |
| Offline study actions including resets | 84: 16 resets, 36 prefix dispatches, 32 new actions |
| Local study scorecards | 16 |
| Online game calls / leaderboard submissions / automatic retries | 0 / 0 / 0 |

Reference-branch and replay CPU costs are accounted separately from proposed study costs. These ceilings are a proposal, not compute authorization. The next implementation phase needs a complete pinned live source closure, bounded transport and lifecycle, independent request/game/counterfactual evaluation, exact private bindings and use review, then fresh lock-bound authorization for one submission.

There are eight correlated, already exposed checkpoints, including overlapping prefixes, and one proposed deterministic attempt. Two new actions do not establish full-game solving, generalization, learning or a hidden cognitive mechanism. Initial click anchors can be stale. The categories are coarse and may miss differences within a bin, delayed effects, hidden state or game usefulness. No post-hoc advancement threshold or significance claim is introduced.

| Retained binding | SHA256 |
| --- | --- |
| Revised CPU input manifest | `ec570d383cbfdc72b02501a97c95d1cfcbaada523a4eccd7818cbfdf802fad3f` |
| Sealed CPU source archive | `9693043d514cd056bc5d5857138ac107e3fbb2f93227c33b5dd7c3f8fb73ace2` |
| CPU rehearsal receipt | `5048c77ef653d1fa023fa8f315bf97ab794cf5de141e2504e0e221727a80c3e7` |
| Native input audit | `7c81507ef90f957a7def5f39fbd2aa5bc15ac70987c56a743c1ce9d20a70cdfe` |

See the [prospective protocol](../research/action_effect_choice_v1/protocol.json), [candidate/request contract](../research/action_effect_choice_v1/interface.py), [scorer](../research/action_effect_choice_v1/scoring.py), [CPU rehearsal](../scripts/rehearse_action_effect_choice_v1.py), and [preceding real-model results](feedback_summary_probe_v1_attempt1_results_2026-10-19.md). Private reference logs and case data are not published.
