# ls20 evidence-memory pilot: attempt 1 submitted

Subsequent status: the attempt completed and passed independent validation; level 1
was not completed. See the [results report](ls20_memory_evidence_v1_attempt1_results_2026-10-26.md).
The following records the status observed at submission.

The owner approved review lock `e4c14554…` for one attempt. One private submission
created version 1; the provider status read after submission was **RUNNING**.
Results and technical completion have not yet been evaluated. This is a launch
record, not evidence of an experimental outcome.

| Binding or check | Recorded result |
| --- | --- |
| Executed source commit | `5c5f1e55071894f087deaba63af23a38d8d8d5f3`; all 73 review-bound files match the pushed commit |
| Private review lock | `e4c14554bf22a8af2ecc82acdff89782ff26307a804cff164509666f4a1dd840` |
| Written launch notebook | `af804609415e56546d2e5af4af078ac0daeab3b9c00f301af1fc95189cefd62d`; only the declared authority slot differs from the review notebook |
| Owner approval | Exact response retained privately, bound to the lock, scope and review packet |
| Preflight | Seven read-only checks passed before reservation and again immediately before sending |
| Previous study | Terminal COMPLETE before this submission |
| Reservation and claim | Fresh single-use reservation and consumed launch claim; one durable send intent |
| Provider writes | Exactly one SaveKernel call; no provider error or rejected source; no retry |
| Saved-package verification | Exact source, authority, privacy, offline settings, image, requested accelerator and attachments match |
| Previous attempts | All 861 inventoried files from earlier attempts unchanged |

The launch operator was derived from the run-tested k=4 operator by pinned
substitutions and reviewed before sending: it changes only this study's lock,
commit, branch, modules, approval wording, check values and preservation chain, and
keeps a single provider save call. The read-only collector and evaluator were also
derived and reviewed before launch; only the attempt ID is filled in afterwards.

| Authorized resource | Limit or setting |
| --- | --- |
| GPU | Exactly one RTX PRO 6000; requested, and actual allocation is verified by the runtime |
| Time | Requested session timeout 3,600 s; worker 3,300 s; admission cutoff 3,000 s; cleanup reserve 300 s |
| Generations / counted model HTTP requests | At most 41: one canary plus up to 40 policy replies |
| New tokens | Canary at most 16; each policy reply at most 256 |
| Offline actions including the reset | At most 41 |
| Local scorecards | One |
| Online game calls / scorecards / leaderboard submissions | Zero |
| Access and network | Private account-only notebook and raw outputs; internet and TPU off; sanitized summaries only |
| Attempts / automatic retries | One / zero |

The provider does not echo dataset version labels or the session timeout in its
saved-source response; versioned bindings and fresh inventories were checked
before sending. Provider overhead may extend total time beyond the requested
session timeout, as approved. The attempt is consumed and preserved whatever its
outcome. Private operation records remain git-ignored.
