# Feedback-action v1: owner gates (analysis and prepared implementation; no decision recorded)

Prepared October 8, 2026 on `track1-successor-runtime-v1`. Two decisions belong to the study owner:

- **Gate A:** the permitted free-text format, including the proposed ASCII-only restriction.
- **Gate B:** F5 early abort.

This document prepares both decisions. For each gate it gives the exact token audit and the consequences of every
option, and it implements the recommended option behind the gate in `research/feedback_action_v1/live/owner_gates.json`.

Both decisions are `null`, so the committed protocol v2 behaviour applies unchanged. Tests show that requests, the
schedule and the abort rule are then identical to the committed ones.

Recording a decision is a protocol amendment. It needs three things:
- the owner's explicit response;
- a new review snapshot;
- a compute authorization bound to the record's new hash. The gate checks `owner_gates_sha256`.

Nothing on this branch records a decision.

## Gate A: the permitted free-text format

`hypothesis` and `if_different` are free text in the candidate's `hypothesis_test` block. Their schema is
`{"type": "string", "maxLength": 240}`. The candidate's completion cap is 640 tokens; the baseline's is 128.

### What the decoder admits today

These are measured, not assumed. They come from xgrammar 0.1.34, the version in the trusted lock, compiled the way
vLLM 0.19 compiles `json_schema` by default (`any_whitespace=True`). The source is
`research/feedback_action_v1/token_audit.json` `grammar`.

| Fact | Current schema | ASCII-only schema |
|---|---|---|
| 240 characters accepted, 241 rejected | yes (per code point; 240 astral characters accepted) | yes |
| JSON escapes (`\uXXXX`, `\"`, `\\`, `\n`) | **never admitted**: the string body is any code point except `"`, `\`, CR, LF | never |
| Raw control characters (e.g. TAB) in text | **admitted**. `json.loads` then rejects the response, so it is an invalid output | rejected |
| Non-ASCII characters | admitted | rejected |
| Whitespace between JSON tokens | unbounded (2,000 spaces accepted), both arms | unbounded |
| Digits in a citation `ref` (`^T[0-9]+$`) | unbounded (500 digits accepted) | unbounded |
| Citations per list | at most 4 (a 5th rejected) | at most 4 |
| Property order | fixed (as sent) | fixed |
| `pattern` without a length bound in it | n/a | **drops `maxLength`**: a 241-character text is accepted. The bound must sit inside the pattern, as `^[ !#-\[\]-~]{0,240}$` |

### Exact token audit (pinned tokenizer, transformers 4.57.6, tokenizers 0.22.2, jinja2 3.1.6)

**Setup.** Each row is the longest allowed candidate response, end-of-turn token included. It has:
- both free-text fields at 240 characters of the option's worst text;
- 8 citations of the latest possible ref `T23`;
- region `[63,63,63,63]` and ACTION6 at (63, 63);
- the enum choices that maximize the count.

**Counts are canonical tokenizations.** Guided decoding can also emit non-canonical token sequences. Their only
bound is the byte length, shown in brackets.

| Free text | compact | `json.dumps` default spacing | indent 2/4 | Fits 640? |
|---|---|---|---|---|
| current, worst (U+10FAA4: 4 byte-level tokens per character) | **2,106** [2,536 B] | 2,162 [2,594 B] | 2,250 | no, under any format |
| current, CJK (1 token per character) | 666 | 722 | 810 | no |
| ascii_only, worst (digits: 1 token per character, which is also the exact bound) | **666** [1,096 B] | 722 [1,154 B] | 810 | no (26 to 170 over) |
| English-like ASCII at the caps | 287 | 343 | 401 (3 spaces after each separator, as seen live in AEH v1); 446 with tabs | **yes** |
| structure only (empty text) | 185 | 241 | 328 | yes |
| baseline (cap 128) | 22 | 29 | 42 (36 with the AEH-style spacing) | yes |

**Exact per-field bounds:**
- current: 960 tokens per field (at most 4 UTF-8 bytes per code point).
- ascii_only: 240 tokens per field.

**Prompt side.** All 25 request forms (both sessions) are within the 60,000-token ceiling and the 65,536 context.
The maximum is 30,351 tokens: a candidate request whose carried statement holds the current option's worst text,
escaped by the request's JSON encoding. Under ascii_only the same form is 26,991 tokens. Ordinary steady-state
requests are 25,994–26,516 tokens.

**No cap covers every grammar-admitted response, under either option.** Whitespace and ref digits are unbounded,
and this holds in both arms. The committed protocol already treats a truncated response as an invalid output
(§5): an unfavourable outcome that also counts toward F2a.

### Options

1. **current (committed).** Natural English text at the caps fits easily. However, text in a non-Latin script, or
   adversarial Unicode, can need up to 2,106 tokens with no added whitespace. A response truncated by the cap is
   an invalid output. That makes it a cap artefact counted against the candidate.
2. **ascii_only (recommended).**
   - **Specification:** printable ASCII without quote and backslash, at most 240 characters. The decoder enforces it
     through `"pattern": "^[ !#-\[\]-~]{0,240}$"`; `maxLength` stays for other validators.
   - **Check at parse time:** a disallowed character makes the procedure block invalid, never the action.
   - **Effect on the token bound:** it removes the multi-token-per-character blow-up, so natural text cannot reach
     the cap.
   - **Remaining overflow:** degenerate content only, such as runs of digits or punctuation at full length in
     default spacing (up to 722 tokens), plus runaway whitespace.
   - **Scientific consequence:** the candidate's `response_format` bytes change. That is a change to the treatment's
     request, made before session 1. The baseline is unchanged.
3. **Not prepared here; owner alternatives:**
   - **raise the 640-token cap.** It is part of the bundled treatment's disclosed allowance.
   - **lower the 240-character limit.** Even at 226, ascii_only fits 640 only in compact formatting.
   - **bound ref digits** (`maxLength` on `ref`).
   - **disable inter-token whitespace.** This is a server flag that changes both arms; it is a runtime change outside
     the verified argv.

**Recommendation: ascii_only.** It is the smallest change that makes the cap a property of the model's choices
rather than of the tokenizer's treatment of characters. It leaves the cap, the text limit and the baseline
unchanged.

**What it does not remove:**
- the whitespace risk, which is common to both arms;
- the degenerate-content risk.

Both stay as invalid outputs under the committed rules.

**Implementation, inactive:**
- `owner_gates.candidate_response_format` / `gate_request` / `free_text_problem`;
- `policy.validate_policy_request` expects the gated schema only when the decision is recorded;
- the independent evaluator flags any out-of-option text as an integrity failure (F4).

Tests: `tests/test_feedback_action_v1_successor.py` `OwnerGateOptions`; `tests/test_feedback_action_v1_token_audit.py`.

## Gate B: F5 early abort

### Committed rule

**Rule.** Protocol v2 §10 aborts when (failed + unknown dispatches) × 10 > dispatches so far. It is checked after
every dispatch, over the whole session.

**Exact consequences:**
- a failure at any dispatch among the first 9 aborts the session;
- 1 failure in 10 does not;
- a second failure aborts if it comes before the 20th dispatch;
- in general, the k-th failure aborts iff 10k > n, where n is the dispatch at which it occurs.

Every failure already ends its own episode. So under this rule a single failure among the first 9 dispatches costs
the whole session. Those dispatches belong to the first pair's first episode or the start of its second.

### Options

| Option | Rule | First failure | Second failure | From the 10th dispatch on |
|---|---|---|---|---|
| running_rate_from_first_dispatch (committed) | 10k > n | aborts if n ≤ 9 | aborts if n ≤ 19 | 10k > n |
| **denominator_floor_10 (recommended)** | 10k > max(n, 10) | **never aborts** | aborts if n ≤ 19 | identical to committed |

**Rationale for the floor.** It keeps the 10% threshold and the online check. It changes only the small-sample
region, where one event already exceeds 10%:
- one early failure loses its own episode, which is retained;
- the schedule continues;
- a second failure within the first 19 dispatches still aborts.

The dispatches are local, to the offline engine. A failure there points to the harness or the engine rather than to
the model, so a second failure is the trip wire.

**Implementation, inactive.** When the decision is recorded:
- `owner_gates.apply` adds `dispatch_denominator_floor: 10` to the session spec;
- the derived runner's F5 check uses `max(dispatches, floor)`, recording the floor in the abort record;
- the independent evaluator recomputes F5 with the effective spec.

With no decision recorded the floor is 0, which is the committed rule. Tests:
- `tests/test_feedback_action_v1_dispatch.py` `F5DispatchFailureAbort`: the committed boundaries;
- `tests/test_feedback_action_v1_live_evaluation.py`: both rules recomputed online;
- the connected rehearsal: `dispatch_failed` and `dispatch_unknown` abort under the committed rule.

## Teammate material, not part of this study

Rainnnee's competing-explanations challenge set is at `origin/teammate/windows-track1` `df29206`. It is synthetic,
CPU-only development material and is not merged here. It could enter the study only as a separately reviewed
amendment.
