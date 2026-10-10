# Track 2 successor: CPU verification record

**Environment.** WSL Ubuntu 24.04, CPython 3.12.3, no GPU.

**Scope.** These are CPU-only checks with scripted (stub) answers and fixture wheels. They are not GPU, model,
throughput or outcome evidence. No provider was contacted.

## r2: the protocol freeze (fresh clone of `239c418`)

**What changed since r1.** The owner's freeze decisions of October 9, 2026 (`freeze_change_list_r2.md`): the recall
decoding schema has no `uniqueItems`; the unsupported-claim margins are read three ways; session B's launch tooling
waits for session A's technical completion; the frozen protocol is bound by review snapshots r2.

**Clone.** A fresh `--no-local` clone of `track2-successor-runtime-v1` at `239c418`, with the basis commit `5a21dd3`,
the Track 2 baseline `107d8b4` and the r1 audits' commit `fb8cf77` available, so every comparison ran and none was
skipped. Every check ran network-isolated (`unshare --net`, loopback only), with a logging `nvidia-smi` stub on
`PATH` in addition to each review check's own decoy. `239c418` is the freeze commit `b58e5f1` plus a fix to one test
file (the first fresh-clone run, of `b58e5f1`, found the connected rehearsal module unimportable; its other checks
had passed). The commit that adds these records changes only reports.

| Check | Result |
|---|---|
| `scripts/build_evidence_memory_v1_sessions.py --check` | 31 derived files match |
| Structured-output check r2 (dump with the dev env; check with the vLLM 0.19.0 interpreter, CPU) | Passed, and it rewrote `structured_outputs_check_r2.json` byte-identically. Both Track 2 schemas accepted (xgrammar). The decoder admits exactly two answers the protocol counts invalid (recall duplicate; "no_evidence" with another value), and the scorer rejects both. Every valid answer passes decoder and scorer. Every structural error tested is rejected by the decoder |
| Real-tokenizer cross-check (`scripts/audit_evidence_memory_v1_tokens.py`, transformers 4.57.6 / tokenizers 0.22.2) | Passed. It rewrote both token audits and `token_cross_check_r2.json` byte-identically |
| Prompt token counts against the r1 audits (`scripts/compare_evidence_memory_v1_token_audits.py --before fb8cf77`) | Identical on every row of both sessions: A 2,896 rows, 1,728,220 prompt tokens; B 2,832 rows, 1,686,442. Every recall request digest changed (A 2,144; B 2,096); every decision digest is unchanged (A 752; B 736). Distinct requests unchanged (1,979; 1,976). The receipt `token_counts_r1_vs_r2.json` was rewritten byte-identically |
| Review check, session A (r2, lock `750ea373…`) | Refused at the live gate. Exit 1; `LiveRefused` with 4 reasons; no `nvidia-smi` call (decoy or stub); no temporary files |
| Review check, session B (r2, lock `37296378…`) | The same |
| Embedded inputs, r2 (each payload extracted alone) | Passed for A and B: 174 trusted wheel records loaded; the live entry points import from the payload alone; nothing outside the payload (`extracted_inputs_session_{a,b}_r2.json`) |
| `launch-build`, A and B | Refused (exit 1) with the live-gate reasons. Session B also names the missing session-A technical evaluation (`reports/evidence_memory_v1_session_a_technical_evaluation.json`); session A does not |
| Successor group (`--group successor`, system Python with pip; 791 s) | 163 tests: 163 passed, 0 failed, 0 skipped. That is 67 successor tests and the 96 vendored verified-runtime tests. New since r1: 12 session-order tests (fabricated fixtures only), the bound-document test, and session-order assertions on real evaluator output in the connected rehearsals. Both r2 snapshots reproduce byte for byte (`cpu_checks_successor_r2.json`) |
| Track 2 group (`--group track2`, dev-env Python; 1,680 s) | 162 tests: 162 passed, 0 failed, 0 skipped. The earlier suites, with the new tests of the decoding schema (2) and of the three-way margin reading (3, boundaries included). Both r2 snapshots reproduce under this interpreter too (`cpu_checks_track2_r2.json`) |
| Working tree after every reproduction and at the end | Empty (`git status`), after restoring the review-check receipts the checks rewrite with their temporary paths |

**Retained records** (SHA-256):

| Record | SHA-256 |
|---|---|
| `fresh_clone_run_r2.sh` | `53878fa9…` |
| `fresh_clone_run_r2.log` | `88c53fad…` |
| `cpu_checks_successor_r2.json` | `a1d0d9c1…` |
| `cpu_checks_successor_r2.log` | `497eedc1…` |
| `cpu_checks_track2_r2.json` | `6e0aa261…` |
| `cpu_checks_track2_r2.log` | `37e880d9…` |
| `extracted_inputs_session_a_r2.json` | `8a1daf3c…` |
| `extracted_inputs_session_b_r2.json` | `9bd29cba…` |
| `structured_outputs_check_r2.json` | `fb45fe16…` |
| `token_cross_check_r2.json` | `c0a18e21…` |
| `token_counts_r1_vs_r2.json` | `338a5e0a…` |
| `../evidence_memory_v1_session_a_review_check_r2.json` | `841b54ea…` |
| `../evidence_memory_v1_session_b_review_check_r2.json` | `40a0a5c4…` |

The script writes its log to a scratch path outside the repository; the copy kept here is the same log. The
review-check receipts committed for r2 (`../evidence_memory_v1_session_{a,b}_review_check_r2.json`) were written by
the same command on the worktree before the commit; the fresh-clone reruns gave the same verdicts.

### What the r2 checks add

- **The decoding schema.** `uniqueItems` is gone from every request schema, and the answers the decoder now admits
  are still scored invalid by `readers`, `protocol.score` and `run/score.score` (`tests/test_evidence_memory_v1_stage1.py`).
  The baseline tests apply the exact recorded amendment to the `107d8b4` file and require the committed file
  (`tests/test_evidence_memory_v1_successor.py`).
- **The margin reading.** `met`, `exceeded` and `not_shown` at and just beyond both inclusive bounds; the verdict for
  each; only `met` advances; an end-to-end `not_shown` (`tests/test_evidence_memory_v1_protocol.py`).
- **Session B after session A** (`tests/test_evidence_memory_v1_successor_session_order.py`, fabricated fixtures in
  temporary directories). The check refuses when the record is absent, when the hash is unnamed or mismatched, when
  A is not technically complete, when A is invalid in any pass, when A was not live or not withheld, and when the
  record is of another session or frozen set. It passes on a complete record. B's launch package, `write_package`,
  `submit` and `claim` all refuse and spend nothing; the per-scope live gate ignores the record; A's tooling never
  reads it. In the connected rehearsals, the check applied to real evaluator output refuses a complete rehearsal of A
  only as "not live" and "not withheld", the invalid-repeat rehearsal as invalid in a pass, and the timeout rehearsal
  as not technically complete.

### Not established (unchanged from r1)

- GPU or runtime compatibility of these packages, beyond the CPU structured-output check. In particular, these were
  not run on the new runtime: strict `json_schema` decoding on a GPU, the per-call prefix-cache counters, and server
  prompt-token parity.
- Throughput, or whether a session fits its reservation on the GPU.
- Anything about withheld cases, which do not exist yet.
- Approvals, attachment, permission or mounted-byte evidence.

## r1: the successor build (fresh clone of `9655dbf`)

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

### Real-tokenizer cross-check (`token_cross_check.json`)

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

### What the connected rehearsals establish (`tests/test_evidence_memory_v1_successor_connected.py`)

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

### Not established

- GPU or runtime compatibility of these packages. In particular, these were not run on the new runtime:
  - strict `json_schema` decoding;
  - the per-call prefix-cache counters;
  - server prompt-token parity.
- Throughput, or whether a session fits its reservation on the GPU.
- Anything about withheld cases, which do not exist yet.
- Approvals, attachment, permission or mounted-byte evidence.

## Review snapshots r3 (October 9, 2026): fresh-clone verification of `7f16825`

r3 adds one fix: review documents are verified by the launch tooling and the live evaluation, not only by the review
check (`runtime_diff.md`, addendum r3). The procedure was that of r2, in a fresh, network-isolated clone (loopback
only); script `fresh_clone_run_r3.sh`, log `fresh_clone_run_r3.log`.

| Check | Result |
|---|---|
| Builder `--check` | All 31 derived files match |
| Structured-output check, token cross-check, prompt-count comparison | Reproduce the committed r2 receipts; r3 changes none of their inputs. 0 prompt-count mismatches |
| Review checks r3, A and B | Refuse at the live gate. Neither the package's own decoy nor a logging `nvidia-smi` stub on PATH was called |
| `launch-build`, A and B | Refused (exit 1). B also names the missing session-A record |
| Embedded inputs r3, A and B | Pass |
| Successor group (system Python) | 164 tests: 0 failures, 0 errors, 0 skipped (`cpu_checks_successor_r3.json`) |
| Track 2 group (dev env) | 162 tests: 0 failures, 0 errors, 0 skipped (`cpu_checks_track2_r3.json`) |
| Snapshots r3 | Rebuild byte for byte under both interpreters: A `fbad29c7…`, B `84407411…` |
| Working tree | Empty after the reproductions and at the end |

The "Not established" list above still applies, apart from strict `json_schema` decoding. Track 4 exercised flat
string-enum schemas live, and the CPU check covers Track 2's schemas on the exact runtime install.

## Review snapshots r4 (October 10, 2026): fresh-clone verification of `5d6abf1`

r4 binds the owner's withheld-seed commitment (owner gate 1; `7f11432a…`) in both session protocols and the holder
rule in the frozen protocol's §5. The procedure was that of r3: script `fresh_clone_run_r4.sh`, log
`fresh_clone_run_r4.log`.

| Check | Result |
|---|---|
| Builder `--check` | All 31 derived files match |
| Structured-output check, token cross-check, prompt-count comparison | Reproduce the committed receipts; 0 prompt-count mismatches |
| Review checks r4, A and B | Refuse at the live gate. The refusals list the private placeholders and the development stand-in, but no longer the seed commitment. No `nvidia-smi` call |
| `launch-build`, A and B | Refused (exit 1) |
| Embedded inputs r4, A and B | Pass |
| Successor group (system Python) | 164 tests: 0 failures, 0 errors, 0 skipped |
| Track 2 group (dev env) | 162 tests: 0 failures, 0 errors, 0 skipped |
| Snapshots r4 | Rebuild byte for byte: A `c6c89b3a…`, B `f9a480b8…` |
| Working tree | Empty after the reproductions and at the end |

## Review snapshots r5 (October 10, 2026): fresh-clone check of `da465b5`, one failure

r5 made the recall decoding schema the exact enum of the eight valid answers (owner decision, October 10, 2026). The
structured-output check r3 passed: both schemas were accepted, and over all 340 recall answers of one to four values the
decoder admitted exactly the canonical form of each scorer-valid answer. The token audits changed only in request
digests (`token_counts_r2_vs_r3.json`: 0 prompt-count mismatches).

The fresh clone (`fresh_clone_run_r5.log`) passed everything except one test in the Track 2 group, 162 of 163:
`test_evidence_memory_v1_harness.Boundaries.test_no_model_network_or_process_imports`. The r5 `stage1.py` imported
`itertools`, which the research modules' import boundary does not allow. Its receipts are kept
(`cpu_checks_*_r5.json`).

## Review snapshots r6 (October 10, 2026): fresh-clone verification of `8dc9b7a`

r6 computes the eight answers with a plain comprehension in the same canonical order. The recall schema is
byte-identical to the one the r3 check verified.

| Check | Result |
|---|---|
| Builder `--check` | All 31 derived files match |
| Structured-output check r3, token cross-check r3, prompt counts against the r4 audits (`2d0aa6b`) | Reproduce the committed receipts; 0 prompt-count mismatches |
| Review checks r6, A and B | Refuse at the live gate; no `nvidia-smi` call |
| `launch-build`, A and B | Refused (exit 1) |
| Embedded inputs r6, A and B | Pass |
| Successor group | 164 tests: 0 failures, 0 errors, 0 skipped |
| Track 2 group | 163 tests: 0 failures, 0 errors, 0 skipped, including the import boundary |
| Snapshots r6 | Rebuild byte for byte: A `80fbe454…`, B `26f321fc…` |
| Working tree | Empty after the reproductions and at the end |
