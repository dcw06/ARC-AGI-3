# MolmoPoint decoder sequence validation repair

October 16, 2026. The incomplete-point finding on `5227344` is reproduced and
fixed. Every pointing token is now validated before native decoding. An incomplete
fragment cannot become a target hit or a valid empty detection. No inference ran.

## Behavior

The validator derives the patch/subpatch ranges and no-more-points sentinel from
the retained pooling shape, and requires the pinned checkpoint's no-more-points
class and 3-by-3 location grammar. Every ordinary point must contain, in order,
a patch token, a subpatch token, a location token and an object ID. Missing tokens
or IDs, malformed markers, wrong token roles/ranges and out-of-order fragments
raise an error before calling the native decoder.

A no-more-points sentinel is valid at a point boundary, with no later point
tokens. Sentinel-only output is a valid empty detection; a complete point followed
by the sentinel is valid. The sentinel cannot replace part of a point, repeat or
hide a following fragment. Ordinary surrounding text, closing tags, raw token IDs
and decoded text remain unchanged. Complete-point counts must still match the
native decoder's output, catching dropped mappings.

## Retained reproductions

These use synthetic arrays/tokens and the two hash-verified upstream decoder
functions, not real model responses. The historical adapter is loaded from the
exact bytes of `52273442461846260868cf726988e1aeb0aadcbe`.

| Synthetic continuation | `5227344` | Fixed adapter |
|---|---|---|
| Complete point inside target | Accepted, hit | Accepted, hit |
| Same point plus unfinished second point | Accepted, hit | Rejected before native decoding |
| Only an unfinished point | Accepted as empty detection | Rejected before native decoding |
| Sentinel alone | Accepted as empty detection | Accepted as empty detection |
| Complete point plus sentinel | Accepted, hit | Accepted, hit |
| Point after sentinel | Accepted, hit | Rejected before native decoding |

Ten retained regression methods produce **18 failed assertions, including
subtests**, against the historical adapter, with no test errors. They all pass
against the fixed adapter. The explicit before/after native-decoder harness also
passes all ten expected case outcomes after the fix.

## Verification

- **26 MolmoPoint tests pass locally.**
- **63 relevant Linux tests pass**, with zero failures, errors or skips, covering
  the MolmoPoint and retained InternVL preparation/inference/deployment groups.
- All six plain 448px target inputs pass the real-processor CPU check again.
  Their actual pooling metadata gives sentinel index 725. Each check rejects
  three incomplete continuations and accepts sentinel-only and complete-plus-
  sentinel controls, using the pinned native decoder and synthetic tokens.
- The rebuilt private input draft has current source hashes. Images, prompts,
  target references and source arrays are byte-identical to its predecessor.
  Earlier drafts and receipts remain unchanged.
- The CPU environment remains PyTorch 2.10.0+cpu / Transformers 4.57.6. It does
  not certify the publisher-recommended 4.57.1 environment, real generation,
  full checkpoint loading or Kaggle/GPU operation.

[Aggregate validation and hashes](molmopoint_decoder_sequence_fix_validation_2026-10-16.json).
The native-decoder check is reproducible without loading a model:

```text
python scripts/check_molmopoint_point_sequences.py --upstream-modeling <pinned-modeling_molmo_point.py> --output <new-private-directory>
```

A normal checkout can read the baseline using local Git. For a cross-OS worktree
or shallow checkout, `--baseline-adapter <retained-git-show-file>` accepts only
the hard-pinned SHA256 of that exact historical file.

There is still no live package or launch authority. This repair preserves the
six-case, plain 448px design and zero-action scope. Full model acquisition,
runtime validation, guarded packaging and new exact-hash approval precede inference.
