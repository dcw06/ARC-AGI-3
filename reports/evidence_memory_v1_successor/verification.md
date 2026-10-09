# Track 2 successor: CPU verification record

**Environment.** WSL Ubuntu 24.04, CPython 3.12.3, no GPU.

**Scope.** These are CPU-only checks with scripted (stub) answers and fixture wheels. They are not GPU, model,
throughput or outcome evidence. No provider was contacted.

**Clone.** Everything below was run in a fresh clone of `track2-successor-runtime-v1` at `9655dbf`. The clone also
had the basis commit `5a21dd3` and the Track 2 baseline `107d8b4` available, so the comparisons against both ran;
none was skipped.

| Check | Result |
|---|---|
| `scripts/build_evidence_memory_v1_sessions.py --check` | 31 derived files match |
| Real-tokenizer cross-check, rerun in the clone (`scripts/audit_evidence_memory_v1_tokens.py`, transformers 4.57.6 / tokenizers 0.22.2) | Passed. It rewrote both token audits and the report byte-identically (no diff in the clone) |
| Review check, session A (r1, lock `5539e126…`) | Refused at the live gate. Exit 1; `LiveRefused` with 4 reasons; no `nvidia-smi` call; no temporary files |
| Review check, session B (r1, lock `fb94736b…`) | The same |
| `launch-build`, A and B | Refused (exit 1) with the same reasons |
| Successor group (`--group successor`, system Python with pip; 1,024 s) | 150 tests: 150 passed, 0 failed, 0 skipped. That is 54 successor tests (packaging and derivation, service, freeze, connected rehearsals) and the 96 vendored verified-runtime tests. Both review snapshots reproduce byte for byte (`cpu_checks_successor.json`) |
| Track 2 group (`--group track2`, dev-env Python; 1,797 s) | 157 tests: 157 passed, 0 failed, 0 skipped. This is the ten earlier Track 2 suites, including the WS3-derived connected rehearsals and the pooled-analysis end-to-end test, plus the transition-evidence v1/v2 suites, all unchanged. Both review snapshots reproduce under this interpreter too (`cpu_checks_track2.json`) |

**Retained records** (SHA-256):

| Record | SHA-256 |
|---|---|
| `fresh_clone_run.sh` (the commands that ran) | `0137b3fb…` |
| `fresh_clone_run.log` | `522ab5a2…` |
| `cpu_checks_successor.json` | `32f7055a…` |
| `cpu_checks_successor.log` | `befe64a6…` |
| `cpu_checks_track2.json` | `4ba4f4ef…` |
| `cpu_checks_track2.log` | `abda4deb…` |

The script writes its log to a scratch path outside the repository; the copy kept here is the same log.

## Real-tokenizer cross-check (`token_cross_check.json`)

| | Session A | Session B |
|---|---|---|
| Scheduled requests counted with transformers | 2,896 (1,979 distinct) | 2,832 (1,976 distinct) |
| Pure-Python vs transformers mismatches | 0 | 0 |
| Max / mean prompt tokens | 1,247 / 596.8 | 1,249 / 595.5 |
| Common budget (recent_raw block), tokens | 123–264 | 119–262 |
| Budgeted blocks over budget (transformers) | 0 of 336 | 0 of 336 |
| Evidence-block count mismatches | 0 of 672 | 0 of 672 |
| Selection rebuilt with transformers as the measure | identical, 168 of 168 trajectories | identical, 168 of 168 |
| Within 60,000 / 65,536 and the 4,096 exclusion bound | yes | yes |

`max_tokens` (64) covers every answer measured: the longest schema-valid recall answer is 23 tokens compact and 37
pretty-printed; the longest candidate-shaped decision answer is 22 and 42.

**Automated pre-run checks on both stand-ins** (`successor/freeze.py stand-in`; withheld sets get the same checks):
- 168 of 168 trajectories per session pass `verify_history`, gold equals construction, and the faithful memory is
  faithful under the independent checker;
- 0 budget violations;
- maximum prompt 1,247 (A) and 1,249 (B).

## What the connected rehearsals establish (`tests/test_evidence_memory_v1_successor_connected.py`)

Each rehearsal runs the complete verified lifecycle with fixture wheels in a real venv and the scripted stub as an
owned process group.

**Both sessions.**
- Each completes every scheduled call: A issues 2,896 completions and 2,897 metrics reads, B 2,832 and 2,833.
- Cleanup and the final lifecycle deadline are verified. No ledger refusal occurs.
- The evaluator finds each session technically complete and `session_technically_valid`.

**Technical reporting only.** `result.json`, `study/summary.json` and the per-session evaluation contain no
outcome-bearing field: no accuracy, contrast, correctness, unsupported, abstention, stability or conclusion.

**Pooled analysis.** With an exact package reader as the scripted answers, the pooled analysis of the two rehearsed
sessions reproduces protocol v2 section 8's availability ceilings end to end:
- old-evidence accuracy: recent_raw 0.00, state_keyed_raw 0.90, memory 0.90, full_history 1.00;
- verdict `memory_preserves_access_not_shown_over_retrieval`.

It equals `run/final.pooled_analysis` on the same sessions.

**Refusals.** The pooled analysis refuses:
- one session;
- duplicated or swapped sessions;
- the development stand-in in default (live) mode;
- a session whose retained call log changed by one byte (its re-evaluation fails);
- that session's earlier successful evaluation once its inputs changed (the evaluation is bound to its inputs).

Evaluating a rehearsal output as `live` fails on the evidence class.

**Faults.** Each fault is caught as follows:

| Fault | Result |
|---|---|
| Scripted invalid and truncated answers | Retained and counted; `session_technically_invalid_outputs` |
| Invalid answers only in the repeat pass | Pass 1 meets the 2% rule; pass 2 fails it; the session is invalid |
| A hung call | Cancelled at its deadline; the server was observed idle through counted reads, with the abort counted; the session is incomplete |
| A server that ignores the cancellation | `ServerNotIdle`; the study stops at call 7; the stub's process group is still removed |
| Prefix caching visible in the counters at start | Refused before any study call |
| Prefix caching visible in the counters mid-run | The study stops at that call |
| Token parity mismatch | `TokenParityViolation`; the study stops at that call |
| HTTP error | Transport failure; the study stops |
| Admission cutoff inside pass 1 | Stops at `admission_cutoff`; incomplete; the call checks are clean; the cleanup reserve is kept |

## Not established

- GPU or runtime compatibility of these packages. In particular, these were not run on the new runtime:
  - strict `json_schema` decoding;
  - the per-call prefix-cache counters;
  - server prompt-token parity.
- Throughput, or whether a session fits its reservation on the GPU.
- Anything about withheld cases, which do not exist yet.
- Approvals, attachment, permission or mounted-byte evidence.
