# Kaggle support request: enforce a one-hour scored GPU job cap

**Draft only; not sent.** The owner reconfirmed the full-job cap and selected the support-request path. No
upload, reservation, GPU job or scored submission has been made for this candidate.

Send through [Kaggle Support](https://www.kaggle.com/contact) while signed in. Copy the subject and message below.
No credentials, private dataset references, model contents or notebook attachments are needed for this question.

## Subject

ARC-AGI-3: supported 3,600-second cap for an RTX PRO 6000 scoring rerun

## Message

Hello Kaggle Support,

I am preparing one private notebook submission to `arc-prize-2026-arc-agi-3`, requesting exactly one
`NvidiaRtxPro6000`. My budget requires an enforced maximum of 3,600 seconds for the **entire GPU job**,
including platform setup, dataset/model mounting, notebook execution and termination. A timeout beginning
only at the first notebook cell would not meet this requirement.

In my installed client (`kaggle` 2.2.4, `kagglesdk` 0.1.37), `kernels_push(timeout=3600)` sets
`ApiSaveKernelRequest.session_timeout_seconds`. However, `competition_submit_code` uses
`ApiCreateCodeSubmissionRequest`, whose fields contain no timeout. I have not launched or scored this candidate,
and do not want to spend a submission or GPU allocation to test whether timeout inheritance works.

Could you confirm:

1. Does a saved notebook's `session_timeout_seconds=3600` carry into, and get enforced on, its ARC-AGI-3
   competition scoring rerun? If not, what supported UI setting or API request can a participant use to set a
   per-scoring-job 3,600-second cap? I am not requesting a change to the competition-wide runtime settings.
2. Precisely when does that timer begin and end? Does it include GPU allocation/setup and dataset/model mounting
   before the first cell, including a stalled or failed mount? Please distinguish any unallocated queue time
   from time while the job holds a GPU.
3. At the limit, does Kaggle terminate the job and release its GPU even if the notebook never starts, becomes
   unresponsive, or my local computer loses internet access?
4. What configuration or read-only receipt lets me verify the effective 3,600-second cap and exactly one
   `NvidiaRtxPro6000` for the scoring rerun before launching it? If this is unsupported for participant submissions,
   please say so explicitly.

I will keep the scoring submission unlaunched until I can establish this enforced cap. Thank you.

## Evidence and interpretation

| Checked | What it establishes | What remains unproven |
| --- | --- | --- |
| Installed SDK schemas, inspected without authentication or provider calls | SaveKernel has `session_timeout_seconds`; CreateCodeSubmission has six fields and no timeout | Whether the backend inherits a saved version's timeout; when its clock starts |
| [Current official CLI source](https://github.com/Kaggle/kaggle-cli/blob/main/src/kaggle/api/kaggle_api_extended.py) | Notebook save and scored submission are separate requests | A full-job per-submission cap |
| [Official notebook documentation](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels.md) | `kernels push --timeout` is documented for notebook execution | Its effect on a scoring rerun or pre-cell mounting |
| [Official competition-host documentation](https://github.com/Kaggle/kaggle-cli/blob/main/docs/competition_creation.md) | Hosts can configure competition runtime caps | A participant-controlled cap for one scoring job |
| Installed `ApiCancelKernelSessionRequest` | Cancellation accepts a kernel session ID | Identification/control of a scoring rerun, guaranteed termination latency, or offline enforcement |

A local polling/cancellation watchdog cannot supply the required guarantee: it depends on network access and
provider responsiveness, and control of the scored session is unverified. The draft's internal deadline starts
inside the first cell and therefore cannot bound prior setup or mounting. Neither is accepted as a substitute.

Retained local evidence: `cap_and_cancel_sdk_inspection.json` and its standard-library-only inspection script in
the git-ignored scored-submission preparation directory. They record zero provider calls and no authentication.

## Resolution criteria

A useful positive reply must identify the supported per-job setting, confirm it applies to the **scoring rerun**,
and define coverage of allocation/setup/mounting and forced termination/GPU release. Retain that reply and its
configuration evidence before treating the cap gate as resolved. An answer describing only the competition's
global runtime limit, notebook execution time, expected runtime or best-effort cancellation is insufficient.

If Kaggle confirms that this is unsupported, keep the full-job cap and leave the scoring submission blocked.
Do not infer a budget waiver. If the cap is resolved, still complete the exact private package review, pinned-image
and production gateway validation, and required scoped launch records before submission.
