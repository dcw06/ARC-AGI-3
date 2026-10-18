# MolmoPoint: original short-prompt control completed

October 17, 2026. **Restoring the original short prompt restored native pointing:**
22 points across 5 valid boards. The separate
SAM 2.1 CPU stage produced **12/37 whole-object matches at IoU ≥ 0.5** and
**6/37 exact masks**. These are new outputs from the authorized control,
not the earlier seeds or masks reused as predictions.

| Board | Reviewed objects | New native seeds | SAM matches | SAM exact masks | Pointing response |
|---|---:|---:|---:|---:|---|
| ls20 | 3 | 0 | 0 | 0 | Invalid: token cap |
| s5i5 | 7 | 6 | 4 | 2 | Valid, nonempty |
| cd82 | 5 | 5 | 3 | 1 | Valid, nonempty |
| ft09 | 6 | 2 | 0 | 0 | Valid, nonempty |
| ka59 | 10 | 6 | 3 | 1 | Valid, nonempty |
| sc25 | 6 | 3 | 2 | 2 | Valid, nonempty |
| **Total** | **37** | **22** | **12** | **6** | **5/6 valid** |

| Condition | Native seeds | SAM matches | SAM exact masks |
|---|---:|---:|---:|
| Original short-prompt run | 22 | 12/37 | 6/37 |
| Detailed eight-rule prompt, two completed runs | 0 in each | No seeds; skipped | No seeds; skipped |
| Restored short-prompt control | 22 | 12/37 | 6/37 |

All six generated-token sequences and all valid decoded point coordinates are identical to the original discovery run. The independently reconstructed SAM cell masks are also identical to the original CPU comparison.
The control's same-color baseline has 7/37 IoU matches and 3/37 exact
masks. SAM's precision over the 22 unchanged proposals is
54.5%; whole-object recall is 32.4%.
The auxiliary seed-containment diagnostic covers 18/37 objects. It does
not replace the frozen whole-mask criterion.

ls20 again reaches 4,096 output tokens. The whole response remains invalid;
no partial points are salvaged and no SAM inference is performed for that board.
Its three reviewed objects remain in the 37-object denominator. The other five
responses are parser-valid and contain native points. This differs from the
detailed prompt's parser-valid empty/prose results; parser validity alone is
never presented as successful pointing.

## Interpretation

This control strongly links the zero-point regression on these boards to the
**revised instruction**. The same current wrapper, model bytes, dependency
locks, image bytes, decoder, coordinate mapping and generation settings recover
the earlier output when the 226-character prompt is restored. It does not
identify which individual rule, wording or length effect caused the change.
There was no prompt truncation or context overflow in the detailed runs.

The pinned native logit processor enforces the order of point tokens after
a point starts; it still permits ordinary text or EOS before a point starts.
The local CPU diagnostic confirmed those allowed paths without pretrained
inference. Therefore a natural-language request for native-only output did
not itself guarantee a pointing response. No forced-prefix or token-mask
change was introduced in this control.

Keep the short prompt as the tested baseline. The result still leaves many
objects missed or incorrectly bounded, including zero valid ls20 discovery
and zero ft09 SAM matches. It does not establish reliable full-image inventory,
semantic roles, obstacle mechanics, action execution or gameplay ability.
The 37 whole objects and separate parts come from one owner's reviewed inventory
on exposed development boards; no held-out generalization claim follows.

## Runtime and verification

| Check | Verified result |
|---|---|
| Provider / hardware | COMPLETE; one NVIDIA RTX PRO 6000 Blackwell Server Edition |
| GPU worker lifecycle through witness | 344.464 seconds, below 3,300; not total provider-job time |
| Model calls / output | Six generations, 4,377 output tokens, max 4,096 each; no retry |
| Integrity | All 220 mounted files plus seven executable inputs hash-match |
| Deployment / cleanup | Saved source/authority/settings match; process groups absent, GPU cleanup verified, temporary environment removed |
| Independent model replay | Checkpoint bytes, exact prompts/processor metadata, admissions, raw/generated IDs, native points and component masks verified offline on CPU |
| SAM checkpoint / runtime | Original pinned Hiera-Large weights rehashed; FP32, CPU, four threads; no missing or unexpected image-model keys |
| SAM inference | 5 image forwards, 22 seed segmentations, 108.449 seconds through witness, below 1,200 |
| SAM replay | Saved candidate logits/quality, point scaling, quality selection, cell projection, manifest and return marker independently verified |
| Reference / selection | Same externally bound owner reference checked before scoring; no reference masks available to the inference worker |
| Extra activity | Zero additional GPU jobs or MolmoPoint generations during collection/SAM/replay; zero game actions or scorecards |
| Viewer | Six boards, reference/component/SAM masks, seed/proposal selection and original-cell hover coordinates; eight CPU browser checks pass |

The original SAM policy is unchanged: independent positive seeds, three candidates,
highest predicted quality with first-index tie break, logits strictly above zero
and at least 25 of 49 foreground pixels per cell. No correction, borrowed seeds,
reference-based selection, snapping, hole filling or duplicate suppression.
The CPU policy and seed manifest were frozen before segmentation.

Kaggle does not independently echo the requested timeout or dataset-version
labels in this API readback. The pinned request and mounted-byte checks remain
the supporting evidence, with the accepted provider-overhead qualification.

Review-lock SHA256:
`6f5f2611163b10ee91f583d9a68edb244f5d2fc04dec646a8b470a48ebacc3c2`

Independent control replay SHA256:
`32eae91f0e49ad7da71e87e2b82b24f16d1dba440fe115522b47d1d5d53600ff`

Independent SAM comparison SHA256:
`baaf83f11b36343580a80e996c166e23bd2ece31a561173dbf02ace9d8290408`

All consumed attempts and earlier results are preserved. No further GPU attempt
or prompt variant is authorized. Raw evidence, coordinates, masks and the
interactive viewer remain private and git-ignored. Only sanitized summaries
are published here.

Related: [submission](molmopoint_short_prompt_control_submission_2026-10-17.md),
[detailed-prompt repeat](molmopoint_sam21_detailed_repeat_results_2026-10-17.md),
[original SAM comparison](sam21_retained_seed_boundaries_v1_results_2026-10-16.md).
