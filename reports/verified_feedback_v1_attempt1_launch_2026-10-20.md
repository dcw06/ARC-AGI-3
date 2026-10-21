# Verified executed feedback v1: attempt 1 submitted

The owner authorized the final reviewed package and one GPU attempt. One private
submission created version 1; the provider status read after submission was
**RUNNING**. Results and technical completion have not yet been evaluated.
No ongoing watcher was started.

| Binding or check | Recorded result |
| --- | --- |
| Reviewed source commit | `bf79c9e77af32c9413e035097df778e0753c0853` |
| Private review-lock SHA256 | `3a1aa3e4295c79c76dbf8728e0b29e493d0a01bc74fd6d6ad8e10b8605d66e0a` |
| Written launch notebook SHA256 | `132f719c33cde606a5f8d4c7801187d60b715f7dc96b95f3b438b3968f69e11e` |
| Published-source comparison | All 87 review-bound files match the pushed commit |
| Last pre-send preflight | `2026-10-21T03:21:10.515034+00:00` (October 20 locally), all seven checks passed |
| Authorization | Fresh source/use/compute records bind the final lock, protocol and scoped evidence |
| Reservation and claim | Fresh single-use reservation and consumed launch claim; one durable provider-send intent |
| Provider writes | Exactly one SaveKernel call, no provider errors or rejected sources, no retries |
| Saved-package verification | Exact source, authority, privacy, accelerator request, image and attachments match |
| Previous attempts | All 456 inventoried historical files unchanged; previous pilot remains complete |

The launch changes only the declared authority-data slot in the review notebook.
The private operation records remain git-ignored under
`.cache/github-review/verified-feedback-live-v1-2026-10-20/stage-r2/gpu-execution-attempt1/`.
The notebook identity, private model binding, credentials and raw provider
snapshots are omitted from this public record.

| Authorized resource | Limit or setting |
| --- | --- |
| GPU | Exactly one RTX PRO 6000; requested and echoed by the provider, actual allocation still requires runtime verification |
| Time | Requested session timeout 3,600 s; worker 3,300 s; admission cutoff 3,000 s; cleanup reserve 300 s |
| Generations / counted model HTTP requests | At most 33: one canary plus 32 study generations |
| New tokens | Canary at most 16; each study generation at most 256 |
| Offline actions including resets | At most 84 |
| Local scorecards | At most 16 |
| Online game calls / online scorecards / leaderboard submissions | Zero |
| Access and network | Private account-only notebook and raw outputs; internet and TPU off; sanitized summaries only |
| Attempts / automatic retries | One / zero |

The provider did not echo the dataset version suffixes or session timeout in
its saved-source response. Version-1 dataset inventories were checked before
sending, and the request explicitly supplied the timeout and version bindings.
The requested timeout does not prove a full-job wall-clock cap; the owner has
accepted that allocation, mounting, setup and release may add time. The runtime
must refuse an allocated accelerator that differs from the authorized GPU.

This is a launch record, not evidence of an experimental outcome. Collection
must retain provider completion, the return witness, saved-source binding and
manifest hashes before independent evaluation. The study remains descriptive on
eight exposed, correlated checkpoints; supplied retrospective labels cannot earn
model-understanding credit.
