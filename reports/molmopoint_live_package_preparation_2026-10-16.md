# MolmoPoint live-package preparation — 2026-10-16

Prepared a model-specific private package builder and one-use external operator.
The six plain-448 inputs, prompts, point decoder and scientific scoring are
unchanged. No MolmoPoint GPU generation has run.

| Check | Result |
|---|---|
| Linux CPU / installed-SDK regressions | 117 passed, no failures or skips |
| Bound inference scope | Six generations, at most 1,024 new tokens each |
| Proposed compute | One RTX PRO 6000, requested 3,600 s session, 3,300 s worker |
| Provider overhead | May extend total allocation/setup/mounting/release beyond one hour |
| Actions / scorecards / automatic retries | Zero |
| Launch transport | Exact body and source validation before one consumed send |
| Read-only preflight | Account, quota, absent target, versions, privacy and inventories |
| Private inputs staging | Created once; version, privacy, no collaborators and inventory verified |
| Pinned model staging | Upload in progress; final provider verification pending |
| Source/use/compute approval | Pending the final private package hash |
| Reservation / notebook submission | None |

The builder requires retained provider receipts matching the frozen model and
input manifests. It refuses changed hashes, shared/unverified datasets and
incomplete or stale source validation. It binds 220 mounted files: 177 publisher
files, 34 model files including the accompanying Apache text, and nine inputs.
Every mounted byte is checked again before the isolated 48-package installation.
The earlier owner notebook record establishes catalogue access only; it is not
evidence of a MolmoPoint installation check.

The model card, two new wheel licences and inherited wheel-term provenance can
be retained for the owner's scoped review. Earlier InternVL approval does not
approve MolmoPoint. No claim is made that the full CUDA installation or full
checkpoint loading has been tested. All earlier attempts and packages remain
preserved. Exact hardware, cleanup, post-write witness and independent replay
remain mandatory for completion.
