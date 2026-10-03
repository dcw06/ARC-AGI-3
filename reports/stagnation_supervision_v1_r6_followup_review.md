# R6 follow-up: approval provenance, attachments and accounting

No new launch, reservation or approval was created. The attempt remains consumed.
The historical R6 launcher, approval records, notebook, responses, claim and prior
archive manifests are preserved unchanged; the successor repair is not a launch
package and is not wired into any submission entrypoint.

## Approval correction

The agent used the next-steps user message beginning "Next: implement and review
the explicitly no-retry Kaggle adapter" as both source and launch approval. That
message exists in the conversation, but no separate explicit R6 confirmation or
platform message ID was found. Hard-coding its text into prepare() did not
independently establish the two approval decisions. Prior statements that this
provided explicit, separately evidenced R6 approvals were too strong.

approval-provenance-reconciliation.json retains the context reference, original
text and interpretation limitation. It does not retroactively manufacture user
approval. The new consume_explicit_approvals helper is read-only: it requires
source and launch confirmation provenance and hash bindings. It rejects the
historical records. JSON declarations are audit evidence, not signatures or proof
of who authored a message; the designated operator must retain actual confirmation
references. No new approvals have been recorded.

## Attachment repair

The successor adapter retains the received body/hash before checking all dataset,
model, competition and kernel invalid-source fields (camelCase and snake_case).
Any nonempty or malformed rejection field raises and writes a consumed,
no-retry failure disposition. HTTP 200 and a URL are not attachment acceptance.
The actual archived rejected-dataset response is a regression fixture.

Preflight requires the exact declared source inventory plus fresh (five-minute),
identity-bound successful read receipts for every required source. Missing,
denied, stale, duplicate or mismatched receipts block submission. This is a
validator contract, not a completed provider-access integration: future read-only
adapters must derive normalized receipts from raw provider responses and verify
source identity. No successful access receipts were fabricated here. Model and
competition accessibility have not been newly verified. Read access still does
not prove mount presence or install compatibility, so post-submission validation
remains required. The historical live package is not repaired in place.

Four offline tests passed, covering the archived response, rejected dataset/model/
competition/kernel fields, retained failure evidence, no second POST, denied
preflight with zero POSTs, stale/missing/identity checks, and approval provenance.
The historical no-retry adapter and its tests remain unchanged.

## Read-only provider investigation

Authenticated ListDatasetFiles for driessmit1/arc3-vllm-h100-wheelhouse-v3 returns
403 PERMISSION_DENIED: Permission 'datasets.get' was denied. This establishes
that the configured account cannot access the referenced wheelhouse through this
API. It does not distinguish private/removed resources, a wrong reference, or
other access restrictions. No alternate wheelhouse was substituted, dataset
modified or access policy changed. Owner-side access verification is needed
before any replacement package can be considered.

Kaggle still reports CANCEL_ACKNOWLEDGED. The current account quota snapshot
reports GPU timeUsed=0s, timeReserved=0s, totalTimeAllowed=108000s, with refresh
2026-10-10T00:00:00Z. There is no comparable retained prelaunch quota snapshot.
These account-wide values cannot determine this attempt's duration or billing,
especially across a possible quota refresh. Exact GPU/billed seconds and
independent process/GPU cleanup remain unknown. The one-use claim stays consumed.

## Next boundary

Resolve wheelhouse access read-only, complete provider-specific preflight receipt
construction, review a successor package, and obtain separate explicit source,
replacement-compute/budget and launch decisions before another attempt. This work
requests none of those decisions and launches nothing. Real GPU timing, the
second qualified continuation control, and Phase 4 certification remain open.
