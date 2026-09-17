# Single installation-check session authorization

Recorded at 2026-09-17 08:44:16 UTC.

The user replied **“Yes continue”** to the explicit request:

> Do you authorize one installation-only RTX PRO 6000 session, reserving
> 30 minutes, with a 15-minute internal ceiling and no retries?

This authorizes one private, internet-disabled Kaggle installation check, using
the exact `notebooks/phase4-v6-install-check-proposal-r1` artifacts presented for
approval. The reviewed source lock SHA-256 is
`31919622ba208a936fa7bd5c2cf816e05372a9531063c0b902a9f81ba00b90bf`.
All three source bindings and three artifact hashes were reverified before this
record was created. The historical proposal files remain unchanged; this record
supersedes their zero-authorization status solely for this installation check.

Authority covers one attempt and 1,800 reserved seconds, with a 900-second
internal check ceiling and no automatic retries. Provider time must be reconciled;
the reservation is not a provider-enforced hard stop. Failure or ambiguous upload
does not authorize another attempt. Account allowance and target availability
remain prelaunch checks.

This does not authorize model loading, the eight-hour development pilot, holdout
access, scored submissions, or use of the consumed prescreen reservation.

At authorization recording, no Kaggle credential was detected in project token
files, the WSL API-token environment variable, or recognized `.env` fields.
Upload is blocked pending local credential configuration and authentication.
No launch request has been sent; the attempt is not consumed.

Execution lock: `config/phase4_v6_install_execution_lock.json`.
Separate ledger: `config/phase4_v6_install_compute_ledger.json`.
