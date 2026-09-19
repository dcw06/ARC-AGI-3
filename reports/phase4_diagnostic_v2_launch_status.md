# Diagnostic v2: launch blocked pending explicit authorization

The response-retention repair is frozen in
`notebooks/phase4-action-diagnostic-v2-review-r1/`. The review receipt records
18 passing tests and a passing 45-case CPU diagnostic with verified cleanup.
No target model inference has been performed for diagnostic v2.

Automatic approval review rejected the proposed Kaggle GPU launch before the
command executed: the response "ok continue" was insufficient explicit approval
for an external compute job consuming a fresh one-hour reservation. The agent's
earlier interpretation and announcement of authorization were too broad.

Local verification found no launch claim, prelaunch receipt, or launch receipt.
The external ledger contained only a local reserve entry, not a provider
reservation. The compute authorization now records zero authorized seconds and
pending explicit authorization; source approval is pending explicit confirmation.
The ledger preserves the original entry and appends its local withdrawal.
This is not a provider billing reconciliation or a claim about historical jobs.

The prepared `phase4-diagnostic-v2-pilot-launch-ready-r1` package is superseded
and **must not be submitted**: it embeds the earlier, withdrawn approval records.
Its bytes are retained for audit only. After explicit approval, prepare a fresh
package and bound reservation using accurate approval records. Do not reuse the
withdrawn ledger. The local launch command's `--verify-only` check now fails
closed before any provider call. Its generic "already claimed" error reflects
the withdrawn ledger's extra event, not an actual launch claim.

Requested scope for separate confirmation: approve frozen source lock
`4c3cbe6204b310fcf1111604b7bccc7417f283220709619f02f62be4cb20d82c`
and separately authorize one private, offline RTX PRO 6000 diagnostic v2 job,
at most 3,600 provider seconds and 3,300 startup-inclusive internal seconds,
45 diagnostic completions plus one canary, no automatic retries, no full pilot.
Production certification, production admission capacity, and exact historical
billing reconciliation remain open.
