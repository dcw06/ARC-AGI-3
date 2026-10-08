# Milestone E: explicit output contract, paired observation protocol v2 r1

Status: development proposal, GPU-disabled review. This package creates no
approval, reservation, notebook upload or GPU run. Earlier source packages,
scientific results and consumed attempts remain historical and unchanged.

The question is whether computed control metadata helps full action validity
under a shared, explicit output contract. This is a new development condition;
it does not estimate the causal effect of the template by comparing different
GPU runs. It does not establish action usefulness or game progress.

## Frozen observations and comparison

Reuse all 30 exact v1 observations, steps 0 and 10 from each of 15 development
games. `research/control_interface_action_selection_v1/cases.json` and its lock
are embedded and hash-bound directly, without rewriting their contents.
Case SHA256: `57231b44a693953fd633cd43cb31a5a31c945482b8e1cf6b59f04f784aab0439`.
These are exposed development trajectories. Two contexts from one game and
repeated passes are correlated; no held-out performance is claimed.

Both arms receive the same updated system instruction and `output_contract`
after the observation in the user-message JSON. The static contract specifies:

```text
{"action":{"action_id":INTEGER_ID,"action_data":ACTION_DATA}}
```

The model must replace INTEGER_ID with a currently legal, unquoted JSON integer,
and ACTION_DATA with `{}` for actions 1..5 or 7, or integer x/y in 0..63 for 6.
Placeholders, string IDs, ACTION labels and extra keys are invalid. The contract
supplies no concrete action or coordinate answer. It contains no game-dependent
legal list; both arms retain the same legal list in the observation.

The reference receives the unchanged observation. The candidate adds only
`computed_control_metadata`, the exact v3 deterministic mapping from legal
actions to argument rules. The template, prompt, decoder and runtime are
identical between arms. Observations and history are never repaired or altered.

The decoder remains `response_format={"type":"json_object"}`. It enforces no
action schema, legal IDs or argument rules. Strict scoring can therefore detect
malformed or illegal choices. No normalization, repair, fallback or retry occurs.

Same model/revision, temperature 0, seed 0, non-thinking, max_tokens 128 and
explicitly disabled prefix caching as v1. Same counterbalanced E000..E119
schedule: 30 contexts x two arms x two passes = 120 research completions.
The second pass reverses the full first-pass schedule. No subset is selected
after inspecting outputs; all contexts remain in the comparison.

## Scoring and decision

Full validity in both passes remains primary. It requires the exact nested
shape, an integer currently legal action ID and correct action-specific data.
Report improved, regressed, both-valid and neither-valid context counts, with
15 game clusters, repeatability and descriptive action switches.

Report formatting separately: exact nesting/keys, integer ID and object-valued
action_data. This structural metric does not enforce legality or the specific
contents of action_data. A well-formed illegal action counts as formatted and
invalid. A formatted legal action with wrong arguments also remains invalid.

For each arm, report legal responses / formatted responses, and correct
arguments / formatted legal responses, with explicit numerators and
denominators. A zero denominator yields null, never a rate. Include separate
step0 and step10 context summaries. Conditional metrics cannot replace the
primary full-validity result. The scorer reconstructs requests and recomputes
all labels from raw responses, ignoring runner labels.

Invalid semantic responses are outcomes, not technical failures. Missing,
duplicate, reordered, tampered, truncated, timed-out or transport-invalid
responses prevent a complete comparison. No post-hoc repair of v1 or v2 scores.

The outcome is always a development diagnostic with no policy promotion.
Improvement without regressions may motivate a separately reviewed closed-loop
pilot; mixed or worse validity requires diagnosis first. No numeric adoption
threshold, significance claim, useful-action claim or solving claim is added.

## Proposed runtime and lifecycle

Reuse the exact trusted 174-wheel publisher inputs, hash-pinned installation,
private version1 model binary tree and immutable Kaggle image. Public account
and model-location placeholders are intentional. There is no game-engine import,
action dispatch or scorecard. The new scope cannot consume v1 authority.

Proposal: one RTX PRO 6000, <=3,600 seconds, <=131 counted HTTP requests,
one attempt, no automatic retries, private account-only access and outputs.
The cap includes 120 research, three startup, four compatibility and at most
four cancellation requests. It is not authorized by preparing this document.

Internal deadline 3,420s; admission cutoff 3,120s; cleanup reserve 300s;
research ceiling 1,500s. Preserve protected process ownership, installation
descendant cleanup, watchdogs, cancellation, GPU cleanup, environment/source
removal, evidence finalization and the explicit final deadline before passing.
Emergency termination after an overrun cannot restore a passing verdict.

The exact offline tokenizer audit uses Transformers 4.57.6/tokenizers 0.22.2,
verifies all six tokenizer files and counts 2,147,900 scheduled prompt tokens,
maximum 36,284 per request. All fit the frozen 60,000 prompt/65,536 context
ceilings. CPU auditing does not predict model compliance or throughput.

## CPU review

```text
python scripts/build_control_interface_action_selection_v2.py --check
python scripts/control_interface_action_selection_v2_package.py review-check --revision 1
python scripts/check_control_interface_embedded_inputs.py --version 2 --revision 1 --out reports/control_interface_action_selection_v2/extracted_inputs.json
python scripts/run_control_interface_action_selection_v2_checks.py
```

Checks use scripted CPU fixtures and no real model. The extracted notebook must
include the shared verifier's default proposal, manifest and requirements.
The review notebook must refuse at the live gate before installation or GPU
queries. Both old v1 r2 and smoke r10 snapshots must still reproduce exactly.
Final private source/use review and a fresh compute reservation remain separate.
