# Track 2 Stage 1 successor: owner gates

**What this is.** The steps that only the owner, or a human they authorize, may take before either session can run.
Each step states its exact procedure. None of these steps has been taken: no seed has been drawn, no withheld set
built, no private binding resolved, and no approval, authorization, reservation, claim or upload made.

**What the public checkout refuses.** Each session's live gate refuses independently because of:
- `LIVE_ENABLED = False`;
- the unresolved `REPLACE_WITH_` placeholders (seed commitment, kernel owner, model dataset, model mount);
- the development stand-in frozen set and the uncommitted seed;
- the missing approval records.

## Gate 0. Fix the design (protocol v2 section 5: the seed is drawn last)

Decide the open choices in `open_protocol_choices.md`, at least:
- the margins;
- the exclusion behaviour;
- whether B waits for A's technical report.

Then freeze a protocol revision. Every later step binds to it.

## Gate 1. Draw and retain the withheld seed (protocol v2 section 5, steps 1 to 3)

Run this on the owner's own machine, in a private directory outside every repository checkout, with no model or
assistant session watching the terminal.

```sh
umask 077
mkdir -p ~/private/track2
python3 -c "import secrets; print(secrets.token_hex(16))" > ~/private/track2/withheld-nonce.txt
python3 -c "import hashlib, pathlib; n = pathlib.Path.home().joinpath('private/track2/withheld-nonce.txt').read_text().strip(); print(hashlib.sha256(('evidence-memory-v1-stage1-withheld/' + n).encode()).hexdigest())"
```

- **Where the nonce goes.** The nonce goes only into the file; nothing in these commands prints it.
- **Where the hash goes.** The second command prints only `sha256(seed)`, the commitment.
- **Retention.** Keep two copies outside the repository: a private note held by the person who drew it, and a secret
  held by the run operator. Never commit it, never paste it into a conversation with a model, and never put it in a
  notebook output.
- **Commitment.** Write only the printed hash into `research/evidence_memory_v1/successor/seed-commitment.json`
  (`withheld_seed_sha256`; `status: committed`) and into the frozen protocol revision. Commit and publish that hash.
- **If the nonce is lost before the run:** draw a new one, commit it afresh and record the loss.
- **If it is lost after the run:** the results stand but are recorded as not independently reproducible.

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
   failure refuses to write; see choice 8.
4. It requires every prompt within 4,096 tokens and every budgeted arm within its common budget.
5. It prints counts and hashes only.

**Then.** The audit recomputes every prompt count with transformers, with pure-Python parity, and writes each
session's `token-audit.json`. The builder rebinds each protocol to the new frozen set, audit and seed commitment.
`live_frozen_set_reasons` then returns no reason for that package.

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
  - `maximum_model_requests` at the plan's worst case (194,044 for A and 189,756 for B, which counts metrics reads)
    beside the 2,896 / 2,832 study-completion ceiling;
- the execution lock and an unconsumed reservation.

The launch tooling then:
1. creates the exclusive claim (`launch.claim`);
2. writes the package (`launch.write_package`);
3. records the receipt before the push (`launch.submit`).

Any receipt spends the attempt; an uncertain submission is never relaunched.

**Session B.** Launch B only after A's technical report (`successor/evaluate.py`: technical status only) is retained.
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
