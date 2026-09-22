# Coordinate diagnostic v2: tokenizer binding repair

The user requested repair and one replacement GPU launch under the existing
2,100-second proposal. A new source lock, approval records, and reservation are
required; the failed v1 reservation remains consumed and its files stay unchanged.

Repair scope: restore tokenizer_manifest.json byte-for-byte from successful
grounding v1; make the CPU audit use this exact v2 runtime verifier; retain actual
and expected artifact hashes on future mismatch; regress immutable tokenizer/model
bindings and exact case bytes. All 56 requests, paired wording, cases, schemas,
decoding, scoring and decision rules are unchanged. Namespace identity and
authority records are new. No blanket numeric replacement is used.

The pinned CPU audit now verifies the corrected runtime manifest and all 57
requests, producing the same token counts as before. Target artifact verification
remains strict. No unexplained sitecustomize warning is patched: the retained
fatal error was the corrupted expected vocab digest, not the wrapt warning.

Experiment contract and predeclared decisions: [v1 protocol](phase4_coordinates_v1_review.md).
The budget is frozen separately in `phase4_coordinates_v2_budget.json`.
New notebook: `notebooks/phase4-coordinates-v2-review-r1/profile.ipynb`.
Local evidence, token audit, and package checks use the v2 prefix.
No gameplay or production-certification claim is made.
