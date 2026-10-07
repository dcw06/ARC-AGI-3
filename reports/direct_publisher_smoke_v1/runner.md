# Direct-publisher runtime smoke runner

Prepared October 6, 2026. This is a separate source-review candidate for consuming the existing publisher dataset. No GPU run, provider submission, real reservation or approval was made. The original R2 redistribution decisions are unchanged.

The runtime runner is implemented in `certification/direct_publisher_smoke_v1/`. Its controller derives from the reviewed `wheelhouse-r2-smoke-v1` commit `b07e2b2`; original source hashes are recorded in `controller_origin.json`. The historical CPU intake proposal, its five input bindings and its preflight review snapshot remain unchanged. Current runtime settings are in the new `protocol.json`, not the historical proposal's preparation-status fields.

## Changes from the R2 runtime path

The integrity adapter accepts the publisher's flat mount: 174 wheel files plus the three bound metadata files. It requires no R2 `bundle-manifest.json`, creates no replacement dataset and does not copy the wheel payload into a new bundle. It checks exact file inventory, every wheel size and streamed SHA-256 against the trusted inventory, the bound publisher metadata, identical package/version pins and the trusted local hash-pinned lock.

Offline installation uses the verified flat mount as `--find-links` and the embedded `trusted_requirements.lock` as `-r`, with `--no-index --no-cache-dir --require-hashes --only-binary=:all:`. The publisher's unhashed lock is never the installation requirements file. Hashing and installation share the first-cell installation deadline; each hash chunk checks that deadline. Fixture input overrides are forbidden in live mode. The attached directory must be unambiguous.

The fresh venv is created with `--without-pip`; host-image pip (22.3 or newer) manages that interpreter through `--python` for installation and dependency checking. The runtime/import checks use the isolated venv directly. Missing host pip fails without a bootstrap download. The [bootstrap fix and validation](offline_bootstrap_fix_2026-10-07.md) explain this source-review change. CPU rehearsals require a Python interpreter with pip installed.

Model/runtime, server command, sampling and the request plan retain the pinned smoke settings: Qwen3-VL-30B-A3B-Instruct-FP8, one RTX PRO 6000, CPython 3.12, torch 2.10.0+cu128, vLLM 0.19.0, transformers 4.57.6 and numpy 2.2.6. These are proposed compatibility requirements, not evidence that the current Kaggle image or GPU has been verified. A mismatch fails without upgrading packages.

Venv creation, pip installation, pip check and import checks now each own a registered process group, in addition to the model server. The controller retains each owner before spawning, defers handled shutdown signals through PID/group registration, and treats uncertain ownership as unverified. Commands terminate the entire group on timeout/interruption and also check for children left behind by a successfully exited parent. Linux subreaper mode adopts orphaned descendants; scoped waits reap those children without consuming unrelated child statuses. The previous subreaper setting is restored after lifecycle cleanup. Import output uses a bounded log tail rather than a pipe that a surviving child could hold open.

Cleanup receipts retain every installation/import group and the model-server group. Overall process absence and GPU cleanup depend on all those groups being absent. Request cap/deadlines, cancellation probes and cleanup escalation are retained. An explicit final lifecycle deadline covers installation-group cleanup, GPU cleanup, retained logs, temporary environment/source removal and evidence finalization/publication. An overrun always fails; emergency termination and failure-evidence retention remain possible afterwards.

## Gates before live effects

The new gate runs before installation, model verification or a GPU query. All source files, the protocol, trusted inventory, trusted lock and intake proposal must match the selected review lock. The consuming kernel/account binding remains unresolved in this published candidate.

| Gate | Required evidence |
|---|---|
| Account and dataset version | Scoped attachment receipt and hash-bound provider evidence confirming the authenticated account and exact dataset reference/version. Public HTTP 200 is insufficient. |
| Direct installation/use permission | Reviewer outcome for the actual deployment facts, exact dataset, trusted artifacts and installation lock; no outstanding conditions; assessment and licence evidence bound by hash. This is separate from redistribution approval. |
| Mounted wheel bytes | CPU integrity receipt for all 174 actual mounted wheels, the exact inventory/lock and requested dataset version. The live runner verifies the mounted bytes again before installation. |
| Source review and compute | Separate source and compute approvals bound to the review lock and every evidence file; compute also binds the full protocol, dataset, source approval and frozen limits. R2 approvals cannot satisfy this scope. |
| Single attempt | Bound execution lock, unconsumed reservation and exclusive launch claim; a durable launch receipt is written before provider submission. Uncertain/rejected submissions spend the attempt and cannot retry automatically. |

Code checks evidence structure, scope, content and hashes. A reviewer still must establish the authenticity and legal sufficiency of the provider/use evidence; the gate is not a legal decision or cryptographic approval signature. Private recipient/account facts are not included in the published review candidate.

Proposed limits: 3,600 authorized seconds, 3,420 internal seconds, admission cutoff at 3,120 seconds and a 300-second cleanup reserve; one attempt, at most 12 counted server requests, no automatic retry, no environment actions or scorecards. The frozen plan's worst case is 11 HTTP requests. These values are not an authorization.

## CPU review and validation

```powershell
python -m unittest tests.test_direct_publisher_smoke tests.test_direct_publisher_smoke_lifecycle tests.test_direct_publisher_smoke_preflight tests.test_direct_publisher_smoke_install_lifecycle -v
python scripts/direct_publisher_smoke_rehearsal.py
python scripts/direct_publisher_smoke_package.py review-check --revision 2
python scripts/run_direct_publisher_smoke_checks.py --out /tmp/direct-publisher-checks.json --review-revision 2
python scripts/direct_publisher_smoke_package.py launch-build
```

The last command must refuse in this checkout; it cannot submit a notebook. Public runtime review r2 replaces r1 for the changed source; r1 is preserved as historical evidence. The review snapshot embeds every runtime source and trusted input, has GPU/TPU/internet disabled and stops at the live gate. Build output directories are created exclusively so earlier review snapshots are not overwritten. A privately bound operational derivative also needs a successor review; earlier source approvals cannot cover the changed hashes.

CPU rehearsals install tiny fixture wheels into real temporary virtual environments and exercise a scripted local server. Their receipts always state that they are not GPU compatibility evidence. The production mounted wheels and actual model are never used by these rehearsals. Startup/lifecycle tests retain both original reproductions and the additional boundary/overrun cases. The installation and import descendant-timeout regressions fail on clean `500caa6`, with the false cleanup claim and explicit fixture cleanup retained in [install_timeout_baseline_500caa6.json](install_timeout_baseline_500caa6.json). `scripts/reproduce_direct_publisher_install_timeout.py` runs those same tests against a supplied source checkout.

## Private operational handoff

Keep actual provider evidence and the use assessment in `private/direct_publisher_smoke_v1/`. The operational attachment, permission, byte-verification, source/compute approval, execution/reservation and launch files are ignored by Git. The gate's file references must remain within the package root; the launch snapshot embeds their exact bytes and hashes only after every gate passes. Do not publish private facts or fill a real account binding into the public protocol and push it as a routine fix. Resolve those bindings in a separate private checkout, create a successor review snapshot there, and obtain approval for that exact package before compute.

Account/provider record fields are checked in `binding.check_evidence`: `provider_evidence` names a hash-bound JSON record with `authenticated_account` and `dataset_attachments` containing the exact reference, positive integer version and boolean `attachment_confirmed`. Retain the actual provider evidence for reviewer authentication; manually setting these fields is not verification.

The permission record references a hash-bound `use_assessment` with the actual licence holder, recipients/roles, access controls, publication intent, applicable agreements, output/payload handling and licence evidence. Its reviewer outcome must bind the source review lock, full protocol, dataset and trusted inventory/lock, state `permitted_for_reviewed_use`, and leave no outstanding conditions. Both source and compute approvals bind all three receipts and their referenced private evidence via `evidence_bindings`.

The [CPU follow-up](cpu_verification.md) now records actual 174-wheel byte verification and account/version evidence: authenticated identity/reference plus the operator's saved-run Input-panel confirmation of version 1. Private records retain the evidence method and hashes; the original byte receipt is unchanged. Bind them to final approvals and revalidate the future launch attachment. Remaining decisions are the scoped direct-use permission outcome, final privately bound source/evidence review and exact compute authorization. No status field or code change completes those decisions.
