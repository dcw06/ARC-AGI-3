# ls20 k=4 pilot: floor estimate matched, cross not reached

**The color estimate matched the floor exposed by the first move, but the VLM
did not navigate to the white cross within 24 moves.** Independent replay
verified the actions, outcome and lifecycle. The run itself completed normally.

| Question | Observed result |
| --- | --- |
| What did kNN predict? | Dark gray, color 3: three of four neighbors; one voted for color 4 |
| Did exposed floor support the prediction? | Yes. After the first move, all 25 cells vacated by the original player showed color 3 |
| What path color did the VLM choose? | Color 3, matching the initial estimate |
| Did uncertainty exploration activate? | No. The initial color answer was not null |
| Did the player reach the white cross? | No |
| Did level 1 complete? | No; completed-level counter stayed at zero |

The revealed-floor check is post-run analysis of observed pixels. Those future
pixels were not supplied in the initial request. It supports the starting-floor
estimate; it does not establish that every region of that color is traversable.

## What the agent actually did

The player started at native coordinate **(36, 47)**. The target cross center was
**(21, 32)**. The model first moved up, attempted a blocked left move, and then
made a series of moves toward the right side of the board. It ended at
**(51, 27)**.

| Movement measure | Result |
| --- | --- |
| Actual model-chosen actions | 24 |
| Actions that moved the player | 13 |
| Actions leaving the player stationary | 11 |
| Distinct observed player centers, including the start | 10 |
| Final consecutive stationary actions | 10 |
| Stop reason | Action cap |

The final ten actions repeatedly tried up and right from the same position,
without moving the player. No generation hit its token cap: the largest
completion was 26 tokens against a 256-token policy cap. This was not a
truncated-answer or runtime-error result.

The actual sequence was:

`UP, LEFT, RIGHT, UP, RIGHT, UP, LEFT, RIGHT, UP, DOWN, RIGHT, UP, LEFT, RIGHT, UP, UP, RIGHT, UP, UP, RIGHT, UP, UP, RIGHT, UP`.

The uncertainty fallback was conditional on an unknown initial **color** answer.
It was not a detector for later navigation stalls. Because the model answered
color 3, it received no exploration phase or second color assessment. This run
therefore provides no GPU evidence about the fallback's effectiveness.

## What this means

Knowing the starting-floor color was insufficient for successful navigation in
this trial. The visible action trace shows ineffective routing and failure to
recover from repeated blocked moves. It does not isolate the model's internal
reason for those choices.

The VLM received player/cross coordinates, control meanings, initial/current
images, kNN estimates and observed action history. It received no solved route,
and the runner dispatched its actual choices without correction. This is an
assisted exposed-board pilot, not a test of independent object discovery.
There is no control arm establishing a benefit or harm caused by kNN.

## Technical completion

| Measure | Observed |
| --- | --- |
| Provider | COMPLETE, version 1; one submission, no automatic retry |
| Actual GPU | One NVIDIA RTX PRO 6000 Blackwell Server Edition |
| Runtime | 1,508.26 seconds, approximately 25 minutes 8 seconds |
| Model requests / generations | 26 of at most 27: one canary, one color assessment, 24 action replies |
| Offline actions | 25: one reset and 24 moves |
| Local scorecards | One, closed |
| Online game calls / competition submissions | Zero / zero |
| Prompt / completion tokens | 99,830 / 520 |
| Maximum native prompt | 5,183 tokens, below 8,192 |
| Generation endings | All 26 stopped normally |
| Cleanup | Verified; zero GPU processes, owned groups absent, temporary environment and extracted source removed |
| Independent audit | Exact reviewed source, native token counts and fresh offline replay of all 24 actions verified |

All 13 original downloads and 11 runtime-manifest members verified. The
preservation check confirmed that all 805 retained files from previous work
were unchanged. Collection and independent evaluation made no provider writes,
launched no GPU jobs and generated no new model answers. The independent CPU
replay's 24 dispatches are separate from the original attempt's action count.

| Binding | Commit or SHA256 |
| --- | --- |
| Executed source | `0176ffc851b4f54fd986031efa49a1d3ca9642cb` |
| Approved review lock | `e603c754197474550ecbb47e40dc7f59c2b5d0907a1a49fcbdd912e02fd48328` |
| Input manifest | `2dee9f065ab4b1a9193b7308e4c13f4e2f676ee60f779487b90817fe12e83ae5` |
| Independent evaluation | `8f419361cd4ba22c585ead45f9e2453bdfb8b73b85fe9238e7352c5a59e68be3` |
| Evaluated run evidence inventory | `2cb56263fd6da499e86961800d4c3c5dc14ede7ba738fe7cd37abbef95617db1` |

The attempt is consumed and preserved. Raw evidence and the visual replay remain
private and account-only; this report contains sanitized results. No new
attempt was launched. [Preparation](ls20_knn_path_v1_preparation_2026-10-21.md).
