# ls20 k=4 floor-color and cross-navigation pilot

**The single authorized GPU attempt completed and independently validated. The
starting-floor estimate matched the exposed pixels, but the VLM did not reach
the cross within 24 moves.** See the [completed results](ls20_knn_path_v1_attempt1_results_2026-10-21.md).

The proposed test uses kNN to estimate the color beneath the player, asks the
VLM to judge the path color, then lets it choose actions toward the white cross.
If uncertain, it first probes different nearby color regions and reassesses.

| Component | Frozen choice |
| --- | --- |
| kNN | k=4, native-screen Euclidean distance, unweighted color plurality |
| Training evidence | Initial visible board only; full player footprint, cross and bottom interface excluded |
| Tied vote | null; no arbitrary color assignment |
| Initial estimate | Dark gray (color3): 3 votes; darker gray (color4): 1 vote |
| VLM assessment | Independent path-color ID or null; no forced agreement with kNN |
| Uncertainty fallback | Up to8 VLM-chosen exploratory moves, then one reassessment |
| Evidence after a probe | Targeted region, actual displacement and before/after images; blocked and moved are distinct |
| Route | Chosen by the VLM; no solved action sequence or correction |
| Stop goal | Player center equals the initial white cross center |
| Level completion | Reported separately from cross arrival |

Trying nearby colors cannot guarantee that every color is reachable. Moving
without a special event can show that a location is traversable; it does not
establish a color's general role. A blocked move does not prove its color caused
the block. Untried regions remain untested and the VLM may remain uncertain.

Visible player/cross geometry and controls are supplied explicitly. This is an
assisted exposed-board pilot, not object discovery, a level-solving claim, or a
controlled comparison proving a kNN benefit. The detector is board-specific.

| Validation | Result |
| --- | --- |
| New contract tests | 17 passed |
| Connected Linux regression suite including new tests | 186 passed; no failures or skips |
| Real-engine CPU positive control | Six actual transitions reach cross; independent replay agrees |
| Real-engine CPU uncertainty control | Eight probes include colors3/4 and both blocked/successful movement; reassessment and cross arrival replay correctly |
| Longest tested native prompt | 5178 tokens; below8192 |
| Exact package | Byte-identical rebuild; 65 review-source hashes verified |
| Missing-authority notebook/launch | Refuse before installation or creating a reservation |
| CPU cleanup | Owned groups absent; temporary environment removed |
| Read-only Kaggle readiness | Account, quota, unused target, dataset versions/inventories, model access and game wheels pass |
| Model inference / GPU jobs / provider writes | Zero / zero / zero |

CPU responses were scripted software controls. Actual VLM color judgment and
navigation performance remain unmeasured. Actual accelerator allocation can
only be verified by the guarded runtime of an authorized attempt.

| Binding | SHA256 |
| --- | --- |
| Final private review lock | `e603c754197474550ecbb47e40dc7f59c2b5d0907a1a49fcbdd912e02fd48328` |
| Input manifest | `2dee9f065ab4b1a9193b7308e4c13f4e2f676ee60f779487b90817fe12e83ae5` |
| Review notebook | `d535e017f3d2e455104cd0a79f7c5cdd0754b5fc10ef9acb7639879395b79bb5` |
| CPU source archive | `b34d993413dabbf24fbd62ddc43637a0403a7d6f507982add025693733e659cb` |

Proposed one-attempt limits: one RTX PRO 6000; requested session timeout3600 s,
worker3300 s and admission cutoff3000 s; at most27 model requests/generations
(one canary, up to2 assessments, up to24 action replies),25 offline actions
including reset, one local scorecard. Canary max16 new tokens; other replies
max256. Zero online calls/submissions; private account-only, internet/TPU off,
no automatic retries. Provider overhead may extend total beyond one hour.

Lock-bound source/use and compute approval, fresh preflight, and a single-use
reservation/claim were completed. The claim is consumed. All earlier attempts
remain preserved; no automatic retry or watcher was started. [Implementation](../research/ls20_knn_path_v1/README.md).


## Authorized submission

| Check | Result |
| --- | --- |
| Executed source | `0176ffc851b4f54fd986031efa49a1d3ca9642cb`; all 65 review-source hashes match the published commit |
| Approved private review lock | `e603c754197474550ecbb47e40dc7f59c2b5d0907a1a49fcbdd912e02fd48328` |
| Owner approval | Exact response retained privately, bound to source, use and compute scope |
| Fresh preflight | Account, quota, unused target, source versions/inventories, private model access and game wheels pass |
| Written notebook | Only the declared authority data slot changed |
| Provider writes | One SaveKernel call and one durable send intent; no retry |
| Provider response | Version 1; no provider error or rejected source |
| Saved notebook | Exact source, authority, privacy, offline settings, immutable image, requested shape and attachments verified |
| GPU | Runtime verified one NVIDIA RTX PRO 6000 Blackwell Server Edition |
| Run result | Technically complete with cleanup verified; VLM chose color 3 but cross arrival failed at the 24-action cap |

The provider does not echo the dataset version labels or requested session
timeout in its saved-source response. Versioned outgoing bindings and fresh
source inventories were checked. Runtime wheel/model checks still apply.
The 3,600-second timeout is requested and the worker enforces 3,300 seconds;
provider overhead may extend total time, as approved. This attempt is consumed
and preserved, even if it fails. No further attempt is authorized.
