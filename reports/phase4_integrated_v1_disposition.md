# Integrated ar25 v1: technical pass, structured study censored at inventory

Kaggle version 1 completed. Independent frozen replay passed with no errors,
including initial-state bindings, requests, token parity, dispatch journals,
stop reasons, finalization, monitoring and independent process/GPU cleanup.
Technical acceptance permits an invalid model output as a retained diagnostic
outcome; it does not mean the integrated research question was answered.

| Arm | Study calls | Actions | Level increase | Stop |
|---|---:|---:|---:|---|
| Unassisted control | 8 | 8 | 0 | Eight-action cap |
| Structured | 1 | 0 | 0 | Invalid inventory JSON |

The structured arm never reached decision, prediction, dispatch or feedback stages.
Those capabilities are **unobserved**, not failed scores. This is not a matched
eight-action scaffold-versus-baseline efficacy result, and does not demonstrate
solving improvement or prove that scaffolding cannot help.

## Exact stopping evidence

`worker/ic1-structured-call-00.json` retains the complete received body (2,612 bytes),
SHA-256 `3a645553851309de0f53729517f920c069a7f89a8bbf484c6b34c7f07dfcb7ba`.
Its tokenizer/server prompt counts agree at 8,676. Server completion count is
**2,048**, exactly the frozen inventory cap. The response ends inside a row-span
array (`[29, `), and JSON parsing fails at character 2612. Evidence truncation is
false: the local 32,768-byte retention bound did not truncate this body.

This is consistent with generation stopping at the completion-token limit.
The transport did not retain provider `finish_reason`, so that explanation is an
inference from token count and body termination, not a directly retained finish
reason. Do not repair/complete the JSON retrospectively or weaken the original
acceptance rules. The prescribed invalid-output stop worked; no action, fallback,
retry or additional question followed. The target accepted the inventory schema
request, but the decision and feedback schemas were never exercised on target.

The retained partial text enumerates narrow, overlapping vertical regions around
x=30..35, with repeated row spans, and does not reach a complete relationship or
control inventory. These fragments are qualitative evidence only. The frozen
evaluator correctly leaves initial geometry metrics null for this invalid response;
do not turn a salvaged fragment into a scored full inventory or evidence of the
model's unspoken intentions.

## Baseline observations

All eight actions were ACTION6: `(16,16)` six times and `(17,16)` twice, with three
adjacent repeats. Both coordinates lie outside the three frozen initial object
masks (A starts at x=18, B at x=36, C at x=51). This establishes initial-mask
non-overlap, not knowledge of the intended target or the game's click hitboxes.
No intention or effect predictions were elicited from baseline.

The first retained observation record differs from bootstrap; the following seven
transitions retain identical observation records. Record inequality alone does not
establish a pixel change or progress (bootstrap/reset metadata can differ).
Replay confirms zero completed-level increase. No game-source interpretation or
winning move was used to interpret these outcomes.

## Disposition and next development boundary

The earliest observed obstruction is an unusable structured inventory response,
before the intended perception-to-action sequence. The output design asks for
potentially long row-span enumerations alongside prose, controls and hypotheses;
the short scripted fixtures did not establish that a real model would finish that
inventory within 2,048 tokens. Both output-contract burden and grounding difficulty
remain plausible contributors. No isolated causal attribution is justified.

Next work should inspect this retained response offline and design a compact,
bounded inventory contract or otherwise demonstrate output-budget feasibility.
Retain the same observation-only boundary and no example winning moves. Add a
regression for completion-cap partial JSON and retain `finish_reason` in a new
transport revision. Any revised contract must receive a new source lock, local
tests and review before a separately authorized attempt. Do not repeat this run
unchanged, promote a policy, or add planning/memory mechanisms based on this result.

## Archive and reproducibility

All **43 downloaded files**, 3,078,247 bytes, were checked against the download
manifest's sizes and SHA-256 hashes. The archive includes those outputs, console
log, provider observations and seven authorization/launch/reservation receipts.
Archive: `evidence/phase4-integrated-v1-r1-completed.zip`.
SHA-256: `0c328ada42671943941a2a9e9bc8746e354775b7c2a3a4f0220e5551022a9eed`.
Member hashes: `reports/phase4_integrated_v1_completed_archive.json`.
Result: `reports/phase4_integrated_v1_pilot_evaluation.json`.

Read-only replay from a checkout with the project's CPU dependency environment:

```bash
python scripts/replay_phase4_integrated_v1_completed.py
```

The command verifies the frozen source/notebook lock and archive member hashes,
extracts to a temporary directory, and invokes the unchanged live evaluator.
No ignored downloads, model weights, credentials or GPU are needed.

## Usage reconciliation and remaining limits

Attempt `ic1-b2b8f5dbc51747ffa4f15af59ff85ed8` remains consumed. One upload;
3,600-second provider ceiling, 3,300-second internal ceiling. Notebook elapsed
**557.833114757 seconds**, model startup 403.617936526 seconds. Nine study calls
plus one startup canary; eight actions; both local offline scorecards finalized.
Study tokens: 197,702 prompt + 2,314 completion; canary: 46 prompt + 29 completion.
Total observed tokens: 197,748 prompt + 2,343 completion. The unused call/action
allowance is not new spending authority.

Independent cleanup verified absent process groups and zero remaining owned GPU
processes. Scratch, dependency trees and extracted source were removed. Account
SDK usage changed from 6,139.137 to 6,707.186 seconds: delta **568.049 seconds**.
This is account-wide usage, not exact per-attempt billing. Raw provider duration
formatting and SDK/raw allowance disagreement remain unresolved; exact billing is
null. Terminal provider reserved time was zero. No new run is authorized here.

Production one-scorecard/110-distinct-game certification, workload-specific
admission limits and exact accounting remain open.
