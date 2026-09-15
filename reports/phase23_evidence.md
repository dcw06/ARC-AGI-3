# Phase 2–3 evidence restoration and validation scopes

The versioned `evidence/phase23-closure-v1.zip` and
`config/phase23_evidence_package.json` preserve the no-treatment closure.
Keep both files together in version control or an explicitly identified evidence
store. The descriptor pins the archive SHA-256 and every member's size and hash.
Missing or changed evidence is a validation failure, not a reason to skip checks.

The package contains the two fresh cd82 run envelopes, their execution lock,
the evidence review, accounting confirmation, closure-time configuration and
Python validators and source. It does not include model weights, game environment
source, credentials, or an installed Python environment. It supports verification
of the recorded closure, not rerunning model inference or recovering Phase 1 data.

## Commands

Use Python 3.12 with the project dependencies pinned in the Makefile installed.
No GPU, API credentials, network access or holdout access is needed for these
validation commands once dependencies are installed.

```bash
# Historical fact, independent of later source/ledger/registry changes:
make validate-phase23-history
# Equivalent explicit validator mode:
.venv/bin/python scripts/validate_phase3.py --historical

# Current applicability; intentionally rejects drift or later ledger changes:
.venv/bin/python scripts/validate_phase3.py --current --require-exit

# Restore and validate in a NEW directory (existing destinations are refused):
.venv/bin/python scripts/phase23_evidence.py restore --destination /private/tmp/phase23-restored-v1
```

Historical verification restores to a temporary directory automatically. Explicit
restoration retains the snapshot for inspection. To use externally stored files,
pass `--archive /path/to/phase23-closure-v1.zip` and
`--descriptor /path/to/phase23_evidence_package.json` to `verify` or `restore`.
Trust the version-controlled descriptor before executing archived Python code;
checksums detect changes, not an untrusted publisher.

Accounting events retain their original bytes and historical absolute references.
`config/evidence_path_map.json` binds those references to checksummed paths inside
the selected checkout. A missing local file fails validation even if the original
workspace still exists. Archived validation uses archived source and closure-time
ledger state, rather than ignoring later H1 events or relaxing source hashes.

Historical success means the recorded conditional disposition is verifiable.
It does not imply current eligibility, an H1 pass, an implemented H1 runner, or
permission to run a future candidate. Current applicability must be assessed
separately; later decisions must be append-only superseding records. Never
overwrite this package to accommodate subsequent development—use a new version.

The historical selection and hardening reports describe their own earlier gates;
the current closure records are `config/phase2_closure.json` and
`config/phase3_decision.json`. Generic admission beyond the frozen cd82 protocol
remains deferred until a justified investigation requires it.
