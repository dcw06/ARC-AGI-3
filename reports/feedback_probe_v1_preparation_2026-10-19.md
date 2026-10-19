# Feedback-to-probe diagnostic: CPU preparation

The [next diagnostic plan](../research_plan_feedback_probe_v1_2026-10-19.md) is
implemented and validated locally. **No neural inference, provider upload,
Kaggle job, approval, reservation or GPU launch occurred.** The scripted
responses demonstrate integration, not model recognition or gameplay ability.

The question is whether an agent can recognize displayed action feedback,
choose and faithfully execute an alternative experiment, and respond to the
result. This follows the owner's study guide's Days 11–14 and its distinction
between replay, prospective prediction and decision benefit.

## Prepared design

| Component | Prepared behavior |
| --- | --- |
| Source evidence | Exact certified recent-feedback run; evaluation and whole-evidence digest checked against protocol pins |
| Selection | Earliest eligible checkpoint per game/stratum at steps 2–20; previous events only, no next response or outcome |
| Cases | Eight checkpoints across six games: four unchanged and four changed controls; missing strata reported |
| Recognition | Eight separate stateless factual questions; keys stored separately from model inputs; answers never enter policy context |
| Policy comparison | Same original raw policy versus one constant probe instruction; unchanged geometry, images, controls and output contract |
| Restoration | Fresh seed-0 reset plus the exact prefix; every full observation verified before inference |
| Continuation | At most four new actions per condition; absolute source step/history preserved; repetition and unknown predictions allowed |
| Evaluation | Full request/body reconstruction, action legality, faithful dispatch, prefix chain, terminal reasons and independent engine replay |

| Game | Unchanged | Changed |
| --- | --- | --- |
| ls20 | None | Step 2 |
| s5i5 | None | Step 2 |
| cd82 | Step 2 | Step 3 |
| ft09 | Step 2 | None |
| ka59 | Step 2 | Step 3 |
| sc25 | Step 2 | None |

These are exposed development states, with overlapping adjacent checkpoints
in cd82/ka59. They are not eight independent game replications. In the retained
cd82/ka59 trajectories, repetition after an unchanged observation later produces
a visible change. This motivates retaining repeat-required guards, not using
future outcomes to select or coach an alternative.

## Validation

| Check | Result |
| --- | --- |
| New diagnostic tests | **53 distinct tests passed** on Windows and Linux, zero failures/errors/skips |
| Reproduction | Fresh-process rebuild reproduces the CPU draft lock and all prepared artifact bytes exactly |
| Recognition/parser guards | Strict keys/types, duplicate/non-finite rejection, exact coordinates, separate abstention/coverage, no answer leakage or conversation carryover |
| Continuation guards | Hidden/delayed effects where repetition succeeds, incorrect restoration, legal-action drift, invalid replies, deadline closure and interruption cleanup |
| Independent content mutations | Altered prompts/model/settings, missing prefix evidence, changed observations/actions, terminal labels and counters are rejected |
| Fresh offline game environment | 31 hash-pinned wheels installed into a new isolated interpreter; no package downloads |
| Connected rehearsal | **73 scripted loopback HTTP completions**, including eight recognition replies and 64 policy replies plus one canary |
| Checkpoint execution | **16 restored continuations and 16 independent engine replays** passed |
| Engine accounting, each pass | 16 bootstrap resets, 36 retained-prefix dispatches, 64 continuation dispatches, 16 local scorecards |
| Combined CPU playback/replay cost | 232 offline actions including resets, 32 local scorecards; replay costs kept separate from study costs |
| Native processor | Pinned Transformers **4.57.6** independently matched all **73** prompt counts; maximum **4,687**, below the prospective **8,192** ceiling |
| Lifecycle | **215.37 s** including fresh installation and Linux tests; owned groups absent and temporary environment removed |
| Network/compute | Linux namespace with loopback only; GPU disabled; zero neural generations and provider writes |
| Independent integration review | No material issue found in selection, answer separation, accounting or scripted-result interpretation |

Scripted recognition uses reference answers intentionally, so it cannot be
reported as 8/8 model accuracy. Scripted continuation outcomes likewise cannot
show improvement over the completed model baseline. Token checks cover these
prepared/scripted contexts; future neural trajectories still require prompt
admission checks before every request.

## Bound artifacts and reproduction

| Artifact | SHA256 |
| --- | --- |
| CPU draft lock | `c905ef008d01268fcd316cbfaccb9e78a9c2b61eba4ae7feb98e1d0b9e30a923` |
| Prepared manifest | `26eb2af7713f4661ce7c310ca55982455a1d06cb2dfe09b04bfef7449b57e1d5` |
| CPU protocol | `62f4af4d195527be1c3ac651c36c76be9b829fc7671e348f35d7b0836ba0433b` |
| Certified source evaluation | `87ea70eef1454d2a7ede72d79b0c1190a9b11d5c96706b133c3bbc06c53e7391` |
| Certified source evidence digest | `8f4a01b0f5b206f861ad169f2dd94c5ef2dc115c83c0785cfef5c5f3ea4403c7` |

Producers: [prepare_feedback_probe_v1.py](../scripts/prepare_feedback_probe_v1.py),
[rehearse_feedback_probe_v1.py](../scripts/rehearse_feedback_probe_v1.py) and
[audit_feedback_probe_tokens_v1.py](../scripts/audit_feedback_probe_tokens_v1.py).
The preparation verifier checks the external CPU lock pin, source hashes and
complete artifact inventory before any scripted request. The rehearsal requires
an externally supervised process group and loopback-only network namespace.
Private keys, restored prefixes, raw prompts and CPU receipts stay git-ignored.
Existing certified evidence and all consumed attempts remain unchanged.

## Remaining before a real model test

Build a separately reviewed bounded live package with immutable image/model,
attachments, credential-free children, ownership-safe cleanup and final deadline
accounting. Exclude reference keys from inference inputs. Recheck scoped use and
obtain fresh package-bound authorization and a single-use reservation.

For this design the proposed maxima are **73 generations, 116 offline actions
including restoration and 16 local scorecards**, with zero online game calls.
The 16-scorecard requirement differs from the previous attempt's 12-card scope;
no old approval or consumed reservation covers it. This CPU draft is not a live
launch package and contains no mechanism to authorize or submit a GPU job.
