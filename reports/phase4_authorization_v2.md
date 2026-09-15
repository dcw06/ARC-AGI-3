# Phase 4 V2 — single-attempt authorization

Authority: the user's explicit instruction in this conversation to checkpoint V2,
authorize one eight-hour maximum reservation, upload V2 once as a private unscored
Kaggle run, download/evaluate outputs and reconcile provider runtime including failures.

- Reviewed source checkpoint: `7f85a80`.
- Execution lock: `config/phase4_execution_lock_v2.json`.
- Execution lock SHA-256: `1f0fd4014fb6170c3673513ea504225e101dd98e8c1ada4f8c9b1a9aede6780d`.
- Maximum reservation: 28,800 seconds; one attempt; no automatic retries.
- V2 only. V1 remains a superseded historical artifact.
- Private, unscored fixture-service prescreen; no H1/H2 use or scored submission.
- Startup, installation, failures and missing outputs remain charged/reserved
  until provider attempt inventory and runtime are reconciled.
- A pass does not complete Phase 4 or establish real-game throughput.

The execution-lock digest above will be checked against the current V2 lock
before reservation. The resulting attempt and provider version are recorded
separately as execution evidence.
