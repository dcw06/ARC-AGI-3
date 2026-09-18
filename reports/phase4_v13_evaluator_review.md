# V13 evaluator correction and v12 evidence replay

The new evaluator revision passes the retained v12 target lifecycle evidence. Replaying the same evidence through the original evaluator reproduces exactly `single audited canary evidence missing`. The original provider status and failed notebook result are preserved.

`certification/phase4_v13/base_evaluate.py` is a copy of the frozen v4 base evaluator with only its canary acceptance block replaced. `certification/phase4_v13/evaluate.py` retains the v12 monitor, lifecycle and capacity checks and calls that corrected base. Historical source files and the v12 notebook remain unchanged. This is an evaluator-only revision, not a new launch-ready notebook.

The canary gate requires status `passed`, contract `arc_action_v12`, positive exact integer prompt and completion counts, exact tokenizer/server prompt parity, a 1–128 completion-token range, context allowance, finite nonnegative service duration, and a lowercase 64-character request hash. It does not fabricate canary output, clamp token counts, remove errors after evaluation, or relax action validation. The retained body is unavailable; content validation remains evidenced by the frozen service's successful canary audit.

Validation:

- Four unit tests passed, including real-receipt and boundary cases, malformed/missing/type-invalid cases, and AST comparisons proving every other base check and all monitor/capacity functions remain unchanged.
- Full replay ran in the configured Linux development environment against hash-verified downloaded files and hash-verified v12 source bindings. The original gate failed for the expected reason; the corrected gate passed all 110 clients and 7,582 requests.
- Seven full-evaluator negative replays rejected missing/wrong-contract/token-mismatch/over-limit canaries and process/GPU cleanup failures. Every rejected replay withheld capacity. The independent-cleanup case includes the supervisor error that the live supervisor produces for that failure.

`reports/phase4_v13_v12_replay.json` records both evaluator results, negative-case errors, evidence archive identity and hashes of the new evaluator, test and replay sources. Its capacity candidate is diagnostic replay output only; it does not authorize admission or certify production operation. The historical notebook's finalization did not succeed under its original evaluator, and an offline replay does not establish a new end-to-end notebook execution.

No GPU reservation or run was created. Before any future target rerun, integrate this evaluator into a new immutable pilot snapshot and review its notebook bindings; do not edit or relaunch the consumed v12 package.
