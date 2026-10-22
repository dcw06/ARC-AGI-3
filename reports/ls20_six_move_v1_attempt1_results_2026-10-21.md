# ls20: explicit left-three, up-three probe

**The VLM followed all six instructions correctly. Independent game replay
verified every resulting state against the references frozen before launch.**

The requested sequence was **LEFT, LEFT, LEFT, UP, UP, UP**. The model produced
action IDs **3, 3, 3, 1, 1, 1**. The runner dispatched those actual choices; it did
not replace, correct or force them.

| Requested moves | Model choices | Observed movement in native board cells |
| --- | --- | --- |
| Left three times | Left, left, left | Five cells left each time; 15 total |
| Up three times | Up, up, up | Five cells up each time; 15 total |
| Complete sequence | 6/6 correct | All six after-states match the frozen references |

The run stopped at its six-move cap. The level counter remained zero: this
prefix is not a complete level solution.

## What this establishes

In this one probe, the model translated the explicit route into the right game
actions, and the engine executed them correctly. All four legal directions
remained available throughout the test.

The entire route and control meanings were supplied in every prompt, alongside
the initial/current images and recent action history. A model could pass from
the text alone. This result therefore does not establish object recognition,
visual grounding, autonomous route planning or first-level solving. It also
does not isolate why the earlier instructed-but-agent-plans pilot failed; the
two probes are not a controlled comparison.

## Attempt and resource use

| Measure | Observed |
| --- | --- |
| Provider result | COMPLETE; one submission, version 1 |
| Accelerator | One NVIDIA RTX PRO 6000 Blackwell Server Edition |
| Runtime | 1,667.74 seconds, approximately 27 minutes 48 seconds |
| Requested session timeout / worker limit | 3,600 / 3,300 seconds; provider overhead may extend total time |
| Model HTTP requests / generations | 7: one startup canary and six policy replies |
| Valid policy replies | 6/6 |
| Prompt / completion tokens | 8,812 / 128 |
| Largest prompt / completion | 1,708 / 21 tokens |
| Generation endings | All seven stopped normally; none hit the token cap |
| Offline engine actions | 7: one reset and six moves |
| Local scorecards | One, closed |
| Online game calls / competition submissions | Zero / zero |
| Automatic retries | Zero |
| Cleanup | Verified; no owned process groups or GPU processes left; temporary environment and extracted source removed |

## Independent checks and retained evidence

The independent evaluator reported the attempt technically complete and its
lifecycle certified. It reconstructed the requests and token counts and
replayed all six moves in a fresh offline game environment. The replay made
zero model requests and used no GPU inference.

All 13 originally collected files retained their hashes and sizes, and all 11
runtime-manifest members verified. The preservation check also confirmed that
751 retained files from earlier work were unchanged. Collection and evaluation
made no provider writes and launched no new GPU job.

| Binding | SHA256 or commit |
| --- | --- |
| Executed source commit | `764773ab7e723a3fd256e8328224dccc0a342d68` |
| Private review lock | `3e8afbcb386f0d17e40f94d658ebcd3d52817b27af34da28b78c94678a77fdab` |
| Input manifest | `7e9410bba02c9516b41d4b3daed9e3024f49d5eca6f231f9fb3b398db9342976` |
| Source inventory | `27e4999b36d61a30097c6e82f331ae40e6420d284ad6d0e6f20a9c6272142cf7` |
| Independent evaluation | `62f1b635761d268fbc20ea3b8d823c1d47c1a17b090b3ae99b528ab75d0cf728` |
| Evaluated run evidence inventory | `3d8db9a8217da37749a3bf4662e0679cf6473204569f39d16fb269513b95b082` |

The attempt is consumed and preserved. Raw outputs, frames, private replay and
approval records remain private and account-only. This report contains only
sanitized results. No further attempt was launched.

[Preparation and frozen design](ls20_six_move_v1_preparation_2026-10-21.md).
