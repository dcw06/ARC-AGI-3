# MolmoPoint detailed generic instruction: complete run, zero native points

The corrected attempt completed on one RTX PRO 6000 Blackwell. Saved deployment,
runtime lifecycle, cleanup and independent CPU request/token/point/mask replay
pass. The **detailed instruction did not produce usable native pointing output
on any of the six boards**. There are no points to feed into SAM.

| Initial level-1 board | Reviewed whole objects | Native decoded points | Point hits | Component-mask matches | Output tokens | Ended normally |
|---|---:|---:|---:|---:|---:|---|
| ls20 | 3 | 0 | 0 | 0 | 31 | Yes |
| s5i5 | 7 | 0 | 0 | 0 | 1 | Yes |
| cd82 | 5 | 0 | 0 | 0 | 1 | Yes |
| ft09 | 6 | 0 | 0 | 0 | 1 | Yes |
| ka59 | 10 | 0 | 0 | 0 | 60 | Yes |
| sc25 | 6 | 0 | 0 | 0 | 1 | Yes |
| **Total** | **37** | **0** | **0** | **0** | **95** | **6/6** |

Four responses contain only the normal end-of-response token. The other two
contain non-point text: a pseudo-pointer list and a prose inventory. Neither
contains a native point sequence. Raw generated IDs, text and native decoding
were replayed independently; no coordinates were discarded, clipped or repaired.
No response approached the 4,096-token cap. All 37 references remain in the
denominator. Point coverage and mask recall are zero; precision is undefined
because there are no proposals. Exact masks are also 0/37.

**The frozen decoder's validity label needs care.** It accepts empty native
decodings, including when unrelated text accompanies them. It therefore reports
six parser-valid empty responses. This is not six successful pointing answers,
nor proof that the instruction to return only native pointing output was
followed. The two text responses visibly fail that instruction. The frozen
scoring and validity rules were not changed after seeing the outputs; the
distinction is reported explicitly instead of awarding success for empty output.

## Verified runtime and evidence

| Check | Result |
|---|---|
| Provider | COMPLETE; exact saved version 1 of the separate corrected notebook |
| Submission | One authorized save; no automatic retry; fresh claim consumed |
| Actual GPU | One NVIDIA RTX PRO 6000 Blackwell Server Edition |
| Worker lifecycle | 294.849115 seconds through the post-write witness, below 3,300 seconds |
| Mounted identity | All 220 mounted-file hashes match: 177 publisher files, 34 model files, nine input-dataset files |
| New agent inputs | All seven embedded generic-input artifacts hash-checked before use |
| Installation/loading | Isolated hashed installation, dependency check and pinned model BF16 CUDA load succeeded |
| Model calls | Exactly six greedy generations, maximum 4,096 new tokens each; 95 completion tokens total |
| Input instruction | Exact unchanged 3,290-character owner instruction, with the corrected explicit 4,096-character input bound |
| Processor | 1,358 input tokens per board, including image/template tokens |
| Cleanup | Owned process groups absent, no cleanup error/interruption, GPU cleanup verified, temporary environment removed |
| Finalization | Result/output hashes, completion witness, return marker and terminal provider status verified together |
| Independent evaluation | Complete local checkpoint rehashed; frozen requests, prompts, metadata, token IDs, native decoding and masks independently replayed on CPU |
| Deployment | Saved identity, source, authority, image, private access and available settings verified |
| Actions/scorecards | Zero |

Worker duration excludes provider allocation, mounting before the first cell
and GPU release. The API does not independently echo the requested timeout or
saved dataset version labels; the validated request and actual mounted hashes
remain the evidence for these settings and consumed content.

Review-lock SHA256:
`c7c3d890d0c00383bba1aa0ae5d9a42b261fa6b0d408bd79a5e1455c8bb4b7ed`

Runtime-lock SHA256:
`890a5d0de61b49a17117ac36bb0b12636c1b8931a0d2dd25c6279c7519041511`

Independent evaluation SHA256:
`fb3d86ec6185d39722c3c7b88914cc185ed1cc2117f490b251a143041a047540`

## Interpretation

The input-length correction worked, and the run ended normally. This prompt
condition failed to elicit native points on these exposed development frames.
The outcome does not establish that MolmoPoint cannot recognize visual objects:
one response contains an inventory in words, and the earlier separate assisted
test located six described targets successfully. Pointing, independent inventory
selection and object boundaries remain different tasks.

For context, the earlier shorter uncued instruction produced 22 accepted points
on five boards, with the ls20 output length-limited and rejected. Its initial
same-color masks matched 7/37 references. The current condition produces zero
points or masks. This is a descriptive development comparison, not a randomized
prompt-effect estimate, independent replication or generalization result. The
earlier notebook-identity warning remains preserved with that earlier study.

The same frozen single-owner reference inventory was used without relabelling.
No SAM extraction was run on the empty new seed set, no coordinates were
invented from prose, and no further model inference or GPU attempt was started.
The failed predecessor remains consumed and preserved; the completed attempt is
also consumed. Raw outputs, reference masks, exact notebook, approval/launch
records, CPU replay and an interactive six-board viewer stay private and
git-ignored. Only aggregates are published here.
