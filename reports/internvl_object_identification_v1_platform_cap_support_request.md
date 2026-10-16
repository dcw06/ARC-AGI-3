# Kaggle support draft: full-job cap for an ordinary private notebook

Updated October 16, 2026. **Draft only; not sent. No GPU launch or upload is authorized here.**

This question concerns the InternVL identification probe's ordinary notebook run, not
the earlier scored competition rerun. The latter has a separate unresolved timeout-
inheritance issue. Do not transfer that issue to an ordinary run without checking.

Submit through [Kaggle Support](https://www.kaggle.com/contact). No credentials,
private boards, model files or private dataset identifiers are needed for this question.

## Subject

Does a notebook session timeout include RTX PRO 6000 allocation and pre-cell mounting?

## Message

Hello Kaggle Support,

I am preparing a private, account-only ARC-AGI-3 development notebook using one
`NvidiaRtxPro6000`. It is an ordinary Save & Run All notebook, **not a scored competition
submission**. It makes six image-only model requests and dispatches no game actions.

My requirement is a provider-enforced maximum of 3,600 seconds for the **entire GPU job**,
including platform setup, model/dataset mounting, execution and GPU release. I will not
launch unless I can establish that this cap is enforced independently of my computer,
network connection and notebook code.

The installed `kaggle` 2.2.4 client sends `ApiSaveKernelRequest.session_timeout_seconds`
when given `kernels_push(timeout=3600)`. The `kagglesdk` 0.1.37 documentation says that
the session is terminated after the specified runtime. It does not define when this
clock starts or whether a stalled mount before the first cell is covered.

Could you confirm:

1. Does this field bound time holding the GPU **before the first cell**, including image
   setup and model/dataset mounting, or only execution after setup completes?
2. What precisely starts and stops the timer? Please distinguish unallocated queue time
   from time after a GPU is allocated.
3. At expiry, does the backend terminate and release the GPU even if mounting or setup
   is stuck and no notebook cell has executed? Is there additional termination/grace
   time outside the configured limit, and how should that be included in a strict cap?
4. Which supported request or setting supplies this guarantee, and what read-only
   configuration/receipt can verify the effective cap before launching?

If the API field does not cover the whole interval, is there another supported per-job
setting that does? Please say explicitly if this requirement cannot be guaranteed.

I am not asking for a change to the competition-wide runtime limit. Thank you.

## Evidence and resolution rule

The [official CLI kernel reference](https://github.com/Kaggle/kaggle-cli/blob/main/skills/references/kernels.md)
documents a timeout for notebook pushes. Installed source inspection confirms the field
is sent to the provider. Neither source establishes pre-cell coverage or release latency.
No GPU experiment has been used to infer enforcement.
The official CLI reference was rechecked on October 16; it still describes a run-time
limit without specifying allocation-through-release coverage. The two successful
GPU-disabled CPU checks establish mounted bytes and isolated installation, not this cap.

Keep the gate unresolved until a supported mechanism's coverage and termination bound
meet the full-job requirement. Expected short runtime, a worker timer, successful runs
below one hour and a network-dependent cancellation watcher do not establish it.
Retain any provider reply with the exact reviewed launch configuration. A positive reply
would resolve this provider question, not automatically authorize compute or certify the
model/runtime/input bindings.
