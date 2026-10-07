# Direct-publisher CPU verification follow-up

October 6, 2026. One private CPU-only notebook completed on Kaggle. No packages were installed, no model was attached or loaded, and no GPU smoke test was launched or authorized. Account identity, provider metadata and participant facts remain local and are excluded from this report.

## Completed evidence

- Authentication matched the intended consuming account. That account could list the version-1 dataset files and attach the dataset reference to the private CPU notebook.
- Provider metadata confirmed private visibility, GPU/TPU/internet disabled, the expected dataset reference, and notebook code matching the prepared CPU verifier. This visibility field is not evidence of the complete collaborator ACL.
- The actual mounted dataset passed the exact inventory, metadata, package/version pins, size and SHA-256 checks for all **174 wheels**, totaling **5,185,992,159 bytes**. Hashing completed in **209.687 seconds**, including the verifier's explicit final deadline check.
- The unchanged, account-free integrity output is retained in [cpu_integrity_receipt_2026-10-06.json](cpu_integrity_receipt_2026-10-06.json). This is actual mounted-wheel evidence, not a fixture rehearsal or GPU compatibility result.
- A local private successor runtime review snapshot resolves the consuming account binding. All runtime Python sources, model settings and compute limits match the published r1 candidate; only the protocol's kernel ID changes. Its source bindings validate, and its CPU review check refuses at the live gate before installation or GPU activity. No approval files were created.

The verification notebook derives from the unchanged five-input CPU preflight snapshot in `notebooks/direct-publisher-smoke-v1-preflight-review-r1/`; its private metadata requested `driessmit1/arc3-vllm-h100-wheelhouse-v3/1`. The provider-returned notebook source was compared with the prepared code. Provider metadata/status and the downloaded output are retained in the local private operations folder for review. No notebook ID, private account data, participant facts, token, or provider session information is published here.

## Exact-version limitation

The provider's pulled metadata returns `driessmit1/arc3-vllm-h100-wheelhouse-v3` without a version suffix. A fresh dataset-view response reports current version **1**, and all mounted bytes match the trusted inventory and publisher metadata previously retained for version 1. This corroborates content identity to the intended version; it does not establish an explicit provider attachment-version ID or a durable version pin. The requested version and the provider's current version are separate observations.

At the initial CPU review, the private account receipt was **partially verified**: identity/reference attachment were established, but exact attachment-version confirmation was missing. That partial receipt and the original byte-verifier output are preserved. The byte verifier's false account/version flags describe its own scope and are not overwritten by subsequent evidence.

## Follow-up: saved-run Input panel confirmation

The operator inspected the completed CPU notebook's saved-run Input panel, selected the exact dataset reference, and reported **Version 1**. This is a user observation of the provider UI; it is not an API version echo, an agent-observed screenshot or a machine-generated version-probe result.

The private account receipt is now **verified** for the reviewed dataset reference/version, using authenticated provider identity/reference evidence plus that saved-run UI observation. Its provider evidence binds the retained metadata, exact observation and actual 174-wheel byte receipt by SHA-256. Those bindings and the private source snapshot validate. The previous partial record is retained for chronology. Account, notebook and participant details remain private.

No additional job or session was started for this confirmation. A possible provider-version probe was prepared but not submitted and supplies no operational evidence. No permission, source approval or compute authorization was created; the live gate still refuses. This closes the completed run's attachment-version question. It does not establish a durable pin for a future GPU notebook: revalidate that notebook's attachment before final launch approval, and retain the runner's live byte rechecks.

## Remaining gates

| Gate | Current outcome | Required next evidence |
|---|---|---|
| Account and version | Complete for the reviewed CPU run: authenticated identity/reference and user-observed saved-run version 1, retained privately. | Bind that evidence to final approvals; revalidate the future launch notebook's attachment. |
| Mounted wheel bytes | Complete: 174/174 actual wheels verified. | Bind this receipt to final approvals; reverify mounted bytes at live installation. |
| Direct-use permission | Private deployment facts and [review addendum](use_review_addendum.md) prepared; no reviewer outcome. | Select the actual smoke-test recipient/output scope, resolve governing terms/acceptance/provenance, and obtain the scoped outcome. |
| Final source/compute | Private account-bound source snapshot and exact compute proposal prepared, without approvals or reservation. | Review the final source and complete evidence bindings; obtain separate source approval and explicit authorization for the frozen one-attempt GPU limits. |

Proposed compute remains one RTX PRO 6000, at most 3,600 authorized lifecycle seconds, 3,420 internal seconds, 12 counted requests, one attempt and zero automatic retries. These are reviewable proposal values, not authorization. The original 174 redistribution decisions and the R2 bundle findings remain unchanged.
