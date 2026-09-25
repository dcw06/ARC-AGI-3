# Stage B R8 completed development pair

**Disposition: technically complete exploratory pair; no demonstrated
solving improvement.** This is not Phase 4 production certification or a
reason to repeat the experiment unchanged.

Kaggle completed private, unscored provider version 1 at
https://www.kaggle.com/code/daichongwei06/arc3-grounded-action-v1-r8,
under consumed attempt `gab1-2b4f10a6f6b949aaa26aa457b9f56272`.
The R11 feedback-output revision passed model startup and canary. The two
arms started from the same frozen visible observation and had separate
offline-development scorecards. The control and structured-target arms each
made two acknowledged `ACTION6` clicks. All 12 model calls were retained;
all requests passed tokenizer/server token parity and completed with
`finish_reason="stop"`.

| Arm | Clicks | Visible state changes | Levels completed | Reviewer-object contacts |
| --- | --- | ---: | ---: | ---: |
| Control | `(16,16)`, `(16,16)` | 0 | 0 | 0 |
| Structured target | `(17,16)`, `(16,16)` | 0 | 0 | 0 |

The target arm's reported target contained its click on both actions, so
the target-to-click consistency measure passed. Neither click contacted a
reviewer-marked visible object. This measure concerns intended coordinates,
not whether the model understood the game's mechanics. With a two-action
horizon and no level progress in either arm, there is no demonstrated
solving benefit from the structured target field. It does not establish
that such a field can never help.

All four sealed predictions were `no_change` and were supported by the
observed transitions. All four feedback assessments said `supported`,
which was correct relative to the committed predictions. However, the
structurally valid feedback responses each set `frame_0_changed=true` even
though no visible cell changed. Independent replay scores all four frame
change judgments wrong. This is a **correctness failure, not a protocol
failure**; R11's frame-bound schema prevented the duplicate/out-of-range
indices that stopped R7. Sealed feedback did not enter subsequent policy
requests, so this run does not test learning from feedback.

The independent evaluator verified all **28** downloaded files against
the provider-output manifest, review/package/attempt bindings, model and
canary evidence, exact trajectory requests and actions, token/finish
evidence, scorecard finalization, deadline compliance, **1,631** monitor
samples, and independent process/GPU/scratch cleanup. No GPU PIDs or
process groups remained; dependency trees were removed. Its replay result
matches the worker and supervisor's recorded results. The frozen replay's
generic interpretation string says “scripted responses”; that string is
inherited from the shared CPU/offline-engine evaluator and is not evidence
that Kaggle used scripted model responses. The host readiness, retained
model-service calls, and target notebook establish the live model path.

The first cell elapsed **562.198 seconds**, including model startup of
**423.462 seconds**. The account-wide GPU `time_used` counter rose from
12,975.5 to 13,547.424 seconds, a **571.924-second** difference. This is
an account-wide observation, not exact provider billing. The one-use
reservation is consumed; no automatic retry is authorized.

The next development investigation should focus on action selection and
grounding, including why both arms clicked outside reviewer-marked objects
and repeated ineffective actions. A separate feedback-perception diagnostic
could test the four false changed-frame judgments. Neither investigation
automatically closes production one-scorecard/110-distinct-game
certification, workload-specific admission limits, or billing reconciliation.

Portable read-only replay after checking out the project and retaining the
archive:

```powershell
wsl -d Ubuntu -- /home/jingjing/.local/share/agi/dev-env/bin/python -m scripts.archive_grounded_action_v1_r8 replay
```
