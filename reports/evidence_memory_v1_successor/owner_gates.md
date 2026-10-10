# Track 2 Stage 1 successor: owner gates

**What this is.** The steps that only the owner, or a human they authorize, may take before either session can run.
Each step states its exact procedure. Only gate 0 has been taken (the protocol freeze of October 9, 2026). No seed
has been drawn, no withheld set built, no private binding resolved, and no approval, authorization, reservation, claim
or upload made.

**Protocol of record.** `reports/evidence_memory_v1_protocol_v2_frozen.md` (frozen October 9, 2026). Its section
numbers are the draft's; "protocol v2 section N" below refers to the frozen text.

**What the public checkout refuses.** Each session's live gate refuses independently because of:
- `LIVE_ENABLED = False`;
- the unresolved `REPLACE_WITH_` placeholders (seed commitment, kernel owner, model dataset, model mount);
- the development stand-in frozen set and the uncommitted seed;
- the missing approval records.

## Gate 0. Fix the design (protocol v2 section 5: the seed is drawn last). Done October 9, 2026

The owner decided the open choices on October 9, 2026 (`freeze_decisions.md`), and the protocol is frozen
(`reports/evidence_memory_v1_protocol_v2_frozen.md`, §16). Every later step binds to it; review snapshots r2 bind its
SHA-256.
- The recall decoding schema no longer carries `uniqueItems` (the defect). Since October 10 it allows exactly the
  eight valid answers; scoring is unchanged.
- The unsupported-claim margins are read three ways; only `met` permits advancement.
- A failing withheld draw is refused and redrawn (gates 1 and 2).
- Session B launches only after session A is technically complete, enforced by B's launch tooling (gate 6).

**One item was not decided and moves to gate 1:** who holds the two copies of the withheld nonce.

## Gate 1. Draw and retain the withheld seed (protocol v2 section 5, steps 1 to 3)

**Done on October 10, 2026.**
- The owner drew the nonce and checked both copies personally.
- Commitment: `7f11432aed195bbd18732abd6cb513024b48e401de17c5fd27e11b17dadfb04b`. It is recorded in
  `seed-commitment.json`, in each session's `protocol.json` and in the frozen protocol §5 (review snapshots r4).
- Copy checks: `nonce_custody.json`. Both copies are on one computer, on separate filesystems.
- The procedure below is kept for a redraw.

**The holder rule (decided by the owner on October 9, 2026; `nonce_custody.json`).**
- **One human holder.** The owner draws the nonce and keeps **two separately stored copies outside every
  repository**.
- **Checks.** The owner checks each copy personally, by recomputing the commitment. The check prints only the hash.
- **Limitation.** There is no independent second holder, so the owner is a single point of failure. Two copies on
  one computer would not survive losing that computer.
- **Frozen text.** The frozen protocol's §5 still reads "open". The rule is copied in at the next review revision,
  which the commitment requires anyway.

Run this on the owner's own machine, with no model or assistant session watching the terminal. Replace
`<copy B folder>` with a second location outside every repository, ideally on another device or removable drive.

```sh
umask 077
mkdir -p ~/private/track2
python3 -c "import secrets; print(secrets.token_hex(16))" > ~/private/track2/withheld-nonce.txt
mkdir -p "<copy B folder>" && cp ~/private/track2/withheld-nonce.txt "<copy B folder>/withheld-nonce.txt"
date -u
for f in ~/private/track2/withheld-nonce.txt "<copy B folder>/withheld-nonce.txt"; do python3 -c "import hashlib, pathlib, sys; n = pathlib.Path(sys.argv[1]).read_text().strip(); print(hashlib.sha256(('evidence-memory-v1-stage1-withheld/' + n).encode()).hexdigest())" "$f"; done
```

- **Where the nonce goes.** It goes only into the two files. Nothing in these commands prints it.
- **What is printed.** The loop prints `sha256(seed)`, the commitment, once per copy. The two lines must be identical.
- **What to report.** For each copy, report:
  - "copy A" or "copy B";
  - the `date -u` time;
  - the printed hash;
  - confirmation that you ran it yourself, that the copy is outside every repository, and that it is stored
    separately from the other copy;
  - a generic storage description.

  Never report the nonce. The reports are recorded in `nonce_custody.json` (`copy_checks`).
- **Retention.** Never commit the nonce, never paste it into a conversation with a model, and never put it in a
  notebook output.
- **Commitment.** Write only the printed hash into `research/evidence_memory_v1/successor/seed-commitment.json`
  (`withheld_seed_sha256`; `status: committed`) and into the frozen protocol revision. Commit and publish that hash.
- **If the nonce is lost before the run:** draw a new one, commit it afresh and record the loss.
- **If it is lost after the run:** the results stand but are recorded as not independently reproducible.
- **If a draw fails the automated checks (gate 2): refuse and redraw** (frozen protocol §4). Publish the failed
  commitment and its counts, discard that nonce (delete both copies; it is never used again), then repeat this gate
  from the first command with a new nonce, and commit the new hash.

## Gate 2. Build the withheld frozen sets (protocol v2 section 5, step 4); private checkout only

The withheld frozen sets contain the questions and their truths. They are generated only in a private checkout and
are not committed to the public repository before the run.

**Who may read them.** Only automated checks inspect them: exclusions, faithful memory, budget fit and the token
cross-check. No person opens `probes.json` or `token-audit.json`.

```sh
# in the private checkout of the approved successor revision
python -m research.evidence_memory_v1.successor.freeze withheld --session A --nonce-file ~/private/track2/withheld-nonce.txt
python -m research.evidence_memory_v1.successor.freeze withheld --session B --nonce-file ~/private/track2/withheld-nonce.txt
EVIDENCE_MEMORY_TOKENIZER=<pinned tokenizer dir> <isolated transformers 4.57.6 env>/bin/python \
    scripts/audit_evidence_memory_v1_tokens.py --no-report
python scripts/build_evidence_memory_v1_sessions.py
```

**What `freeze withheld` does.**
1. It refuses unless `sha256(seed)` equals the committed hash.
2. It builds `stage1.build(session, seed, partition='withheld', case_source='withheld')`.
3. It rebuilds every trajectory and requires zero exclusion conditions. stage1.build has no exclusion step, so any
   failure refuses to write (the owner's refuse-and-redraw decision, frozen protocol §4).
4. It requires every prompt within 4,096 tokens and every budgeted arm within its common budget.
5. It prints counts and hashes only.

**Then.** The audit recomputes every prompt count with transformers, with pure-Python parity, and writes each
session's `token-audit.json`. The builder rebinds each protocol to the new frozen set, audit and seed commitment.
`live_frozen_set_reasons` then returns no reason for that package.

**If `freeze withheld` refuses (refuse and redraw, frozen protocol §4).** It writes nothing, and its error message
carries only the commitment (`seed_sha256`), the frozen-set hash it would have had and the failure counts per
condition. Then:
1. publish that commitment and the counts in a committed redraw record
   (`reports/evidence_memory_v1_successor/withheld_redraws.md`, one entry per failed draw: date, commitment, counts);
2. discard the nonce: delete both copies; it is never used again;
3. never inspect the failed set beyond the automated checks (no one builds, opens or prints it);
4. return to gate 1: draw a new nonce, commit its hash in `seed-commitment.json` (replacing the failed one, which
   stays in the redraw record), and run this gate again.

**Tests on this path.** It was exercised only with non-withheld test seeds; see
`tests/test_evidence_memory_v1_successor_freeze.py`.

## Gate 3. Resolve the private bindings (private checkout)

The reference package resolves its private bindings the same way. In each session's `protocol.json`, replace only:
- `kernel_id`: the consuming account's owner/slug;
- `model.kaggle_source`: the private model snapshot dataset as `owner/slug/version`;
- `model.mounted_path`: `/kaggle/input/datasets/<owner>/<slug>` or `/kaggle/input/<slug>`.

**Effect on the build check.** `scripts/build_evidence_memory_v1_sessions.py --check` then reports exactly those two
protocol files as differing in the private checkout. No other drift is acceptable.

**Not to be published.** Do not publish these values as a routine fix.

## Gate 4. Account, permission and mounted-byte evidence (per session scope)

Follow `reports/direct_publisher_smoke_v1/runner.md` (on the reference branch). Write these records for each scope:
- `reports/evidence_memory_v1_session_{a,b}_account_attachment.json`;
- `reports/evidence_memory_v1_session_{a,b}_use_permission.json`;
- `reports/evidence_memory_v1_session_{a,b}_byte_verification.json`;
- the private provider evidence and use assessment those records reference.

`binding.check_evidence` checks their structure and hashes. A reviewer establishes that they are authentic.

## Gate 5. Enable the live path in a reviewed revision

`LIVE_ENABLED` is written by the builder as a substitution, `LIVE_ENABLED = False`. Enabling it is a deliberate,
reviewed one-line change to the builder in the approved private revision. It produces new source hashes, and
therefore a new review snapshot.

Then, for each session:

```sh
python scripts/evidence_memory_v1_session_a_package.py review-build --revision <N>
python scripts/evidence_memory_v1_session_a_package.py review-check --revision <N>
python scripts/check_evidence_memory_v1_session_a_embedded_inputs.py --revision <N> --out <receipt>
```

Do the same for session B. The review check must still refuse, for want of approvals.

## Gate 6. Approvals, authorization, reservation and launch (human-made, per session)

These records are made by the owner and the reviewer, never by tooling:
- the source approval, bound to the review lock and the evidence;
- the Record C compute authorization, bound to the protocol, the source approval, the dataset and every limit:
  - `authorized_seconds` 3,600, `internal_seconds` 3,300, `admission_cutoff_seconds` 3,000, cleanup reserve 300;
  - one attempt, zero retries;
  - `maximum_model_requests` at the plan's worst case for the withheld sets (186,540 for A and 198,332 for B, which
    counts metrics reads), beside the 2,784 / 2,960 study-completion ceilings, both stated (frozen protocol §12);
  - **session B only:** `session_a_technical_evaluation_sha256`, the SHA-256 of session A's retained technical
    evaluation (below);
- the execution lock and an unconsumed reservation.

The launch tooling then:
1. creates the exclusive claim (`launch.claim`);
2. writes the package (`launch.write_package`);
3. records the receipt before the push (`launch.submit`).

Any receipt spends the attempt; an uncertain submission is never relaunched.

**Session B: only after session A is technically complete (enforced; frozen protocol §12).**
1. After session A's run, evaluate its retained output and retain the record at the fixed path, in the repository:

   ```sh
   python -m research.evidence_memory_v1.successor.evaluate <output_a> --session A \
       > reports/evidence_memory_v1_session_a_technical_evaluation.json
   sha256sum reports/evidence_memory_v1_session_a_technical_evaluation.json
   ```

   The record is technical only: it carries no outcome.
2. If session A is not technically complete, or not valid in every pass, the experiment stops: no pooled analysis is
   possible, and session B is never launched.
3. Otherwise session B's compute authorization names the printed hash as `session_a_technical_evaluation_sha256`.
4. Session B's launch tooling refuses the claim and the launch package (`launch-build`, `launch.write_package`,
   `launch.submit`) unless the record exists in B's checkout, matches that hash, and shows session A live, on A's
   registered withheld frozen set, technically complete and valid in every pass
   (`research/evidence_memory_v1/successor/session_order.py`). The reviewed per-scope live gate is unchanged, and
   session A's tooling never reads the record.

Only technical rules may stop the experiment after A.

## Gate 7. The one scientific analysis, after both sessions qualify

```sh
python -m research.evidence_memory_v1.successor.final --session A <output_a> --session B <output_b>
```

It refuses unless both sessions:
- are the registered withheld sets;
- were evaluated by it, bound to their exact retained inputs;
- are technically complete and valid in every pass;
- ran in live mode.

Only then does it pool both sessions once. After the run, publish the nonce in the results report so anyone can
rebuild the cases and verify the commitment (protocol v2 section 5, step 5).
