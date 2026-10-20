# Action-effect choice diagnostic: retained attempt, 2026-10-20

**The attempt is independently certified technically complete. The planned forecast-and-choice comparison is not informative: 15 of 16 conditions stopped on invalid answers, leaving only one condition with executed study actions.** This is primarily an interface-compliance result, not evidence of an advantage for either instruction, successful planning, or object-recognition ability.

The study compared a neutral instruction with an explicit compare-and-review instruction at the same eight exposed checkpoints. Both conditions received identical historical geometry, recent observations and factual summary, two fixed legal full-action candidates, and the same output fields. Each condition allowed two decisions. The extent-category r2 design and its CPU-selected endpoint chronology remain unchanged; the binary draft and all previous attempts are preserved.

| Certification / resource | Retained result | Ceiling or requirement |
| --- | --- | --- |
| Provider status | COMPLETE; one submission, no retry | One attempt |
| Accelerator | One NVIDIA RTX PRO 6000 Blackwell Server Edition | One RTX PRO 6000 |
| Bounded lifecycle elapsed | 1,456.18 s, approximately 24 min 16 s | 3,300 s worker; 3,600 s requested session timeout |
| HTTP generations | 18: one canary and 17 study replies | 33 |
| Study decision slots | 32 scheduled; 17 answered; 15 unreached | All scheduled slots retained |
| Study replies | 2 valid; 15 invalid | No repair or automatic retry |
| New study actions | 2 | 32 |
| Restored prefix actions / resets | 36 / 16 | 36 / 16 |
| Total offline actions including resets | 54 | 84 |
| Local scorecards closed | 16 | 16 |
| Online game calls / competition submissions | 0 / 0 | 0 / 0 |
| Independent native prompt counts | All 18 matched pinned Transformers 4.57.6; maximum 5,003 | 8,192 prompt tokens |
| Generation endings | All 18 ended normally with `stop`; maximum 49 new tokens | 256 per study reply; 16 for the canary |
| GPU cleanup | Verified; zero remaining GPU processes | Required |
| Owned-process and temporary-source cleanup | Verified | Required |
| New level completions | 0 | Descriptive only; just one condition executed new actions |

Elapsed time starts with notebook execution; it does not establish a cap on provider allocation, mounting, setup or release outside that lifecycle. Provider overhead beyond the requested hour was previously accepted. Collection and evaluation made no provider writes or new GPU launches.

## Reply validity and scoring

| Measure | Neutral choice | Compare and review |
| --- | --- | --- |
| Scheduled decision slots | 16 | 16 |
| Answered | 9 | 8 |
| Valid replies | 2 | 0 |
| Invalid replies | 7 | 8 |
| Unreached decision slots | 7 | 8 |
| Conditions executing both new actions | 1 of 8 | 0 of 8 |

There are no checkpoint pairs in which both conditions executed their two-action sequence. The table therefore does not support an action-choice or forecast-accuracy advantage for either instruction.

| Candidate forecast category under frozen strict scoring | Slots |
| --- | --- |
| Invalid whole reply | 30 |
| Unreached decision | 30 |
| Unknown in a valid reply | 3 |
| Incorrect known forecast in a valid reply | 1 |
| Correct forecast in a valid reply | 0 |
| Total scheduled candidate forecast slots | 64 |

This is **not 64 observed incorrect predictions**. Sixty slots were invalid or never reached. The single known forecast in a valid reply was incorrect. Original invalid replies are retained and receive no partial credit or post-hoc conversion.

## What failed

The first reply of each restored condition had to set both retrospective fields to `not_applicable`: there was no earlier decision within this new study condition. Only one of the sixteen first replies satisfied that phase contract.

- Eleven first refusals were reported as `invalid observed_previous_change`.
- Four first refusals were reported as `candidate prediction enum`; these replies used numeric zero or its string form rather than the permitted category `none`. These four also failed the first-reply phase requirement, so the two counts describe the validator's first error rather than non-overlapping underlying mistakes.
- No reply ran out of tokens. Every completion ended normally, and all remained far below the output limit.

**Likely explanation, not a demonstrated internal mechanism:** the prompts displayed restored game history at game steps two or three but described the new condition's first and second decisions in prose. The model often supplied retrospective values for the visible history instead of treating this as the first study decision. The request used JSON-object generation, which ensured JSON syntax but did not enforce phase-specific enum values or types. CPU scripted checks established software behavior; they did not establish model compliance with this interface.

The host correctly refused those outputs before dispatching an action. The original protocol, prompts, parser, limits and evidence were not changed after observing the replies.

## Independent validation and retention

All 43 downloaded files match their collection hashes. The runtime's 41 evidence members match the final manifest; the exact post-write witness and return marker are present. The saved version, source, authority and supported provider metadata match the reviewed package. The timeout and version-one source labels were checked in the outbound request; Kaggle does not echo those fields in the saved snapshot. Actual mounted bytes were checked before installation. Independent evaluation used the sealed prelaunch sources, independently reproduced native counts, and replayed every retained full observation and request.

CPU verification used 16 trajectory replays and 34 fresh candidate-reference branches, including the actual first action before scoring the sole second decision. The 50 evaluation engines performed 150 dispatches and closed all 50 local scorecards. Full observation/reference journals and their hashes remain private, separate from inference inputs. Evaluation process groups and temporary environments were removed within their own deadline.

| Binding | SHA256 |
| --- | --- |
| Reviewed private package | `bbd0c28f61eedc84db0e30c8c6fd261e941a6f544f96ecacae2e73d829514e21` |
| Inference manifest | `3dca6dc3a8602e9a7f7686ef18900ff5845ee4878a137b533d8b08f23da6d423` |
| Independent live evaluation | `679ecdfba12e4d43b3c7f9141cf513889fcff674bb1980ce2beaeda03386d345` |
| Retained run evidence | `ac179436fa56721a8898d7f2834bab2d807e1d5628c0efd63ab1fa572d1f8de9` |

The attempt is consumed and preserved. Raw replies, game observations, provider records, approvals and evaluation journals remain private and account-only; this report contains aggregates and sanitized error descriptions only.

The recommended next step is an explicit study-decision phase and validated phase-specific structured-output constraints, followed by a small format-compliance pilot before another full comparison. Such a change needs a new frozen revision and fresh compute authorization; this result does not authorize a rerun or retroactive repair of the retained answers.
