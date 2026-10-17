# Semantic-SAM native build compatibility

The pinned upstream deformable-attention extension fails to compile against
Torch 2.10.0 / CUDA 12.8: both `AT_DISPATCH_FLOATING_TYPES(value.type(), ...)`
calls pass `DeprecatedTypeProperties` where the current API requires `ScalarType`.
The failure was reproduced by the real compiler, before model inference.

The [two-line compatibility patch](../research/object_discovery_boundaries_v1/runtime_profiles/semantic_msda_torch210.patch)
uses `value.scalar_type()` for forward and backward dispatch. It changes the
dispatch API argument, not the attention algorithm, thresholds or mask selection.
The original pinned Semantic-SAM runtime tree remains untouched: only a separate
native extension build copy is patched, and the compiled wheel has its own hash.

| Item | Exact identity |
|---|---|
| Upstream Semantic-SAM revision | `e11f8b518539faea731e2744cc3e44c24572e30d` |
| Modified file, relative to `semantic_sam/body/encoder/ops` | `src/cuda/ms_deform_attn_cuda.cu` |
| Original file SHA256 | `9b45778524e75be7696f1fdb3c41564efae162930d5e8f9f89cff74b98167f1c` |
| Patched file SHA256 | `0b7c38657c05ca77e335cda87a06499b62b51db40393da3b57551dc7010dfcef` |
| Build Python / Torch | `3.10.22` / `2.10.0+cu128` |
| CUDA compiler / host compiler | `12.8.93` / GCC `13.4.0` |
| GPU architecture compiled | `sm_120`, using `TORCH_CUDA_ARCH_LIST=12.0` |
| Parallel compilation | `MAX_JOBS=1`; compilation performed on CPU |
| Built wheel | `multiscaledeformableattention-1.0-cp310-cp310-linux_x86_64.whl` |
| Wheel SHA256 | `83f6f39cb124268ce02c94c36a97722221a642721d2c80da9d4b3f12e6a12452` |
| Patched build result | Success, 73.128 seconds |

The conda toolkit's `targets/x86_64-linux/include` and the retained NVIDIA wheel
include directories must be supplied through `CPATH`; its library directories
must be supplied through `LIBRARY_PATH`. Earlier header-path build failures and
the original API failure are preserved, with no overwritten build logs.

Detectron2 also compiled successfully in 250.617 seconds, without a source patch.
Its pinned revision is `42121d75e10d9f858f3a91b6a39f5722c02868f0`.
The resulting `detectron2-0.6-cp310-cp310-linux_x86_64.whl` has SHA256
`cef97384625881707582c65f3636fb95c384e97b85582ba8c9ad2494a5777a63`.

Both compiled extensions, Semantic-SAM and its seeded/automatic helpers now
**pass offline native import qualification**, with socket connections disabled.
The [import receipt](../research/object_discovery_boundaries_v1/runtime_profiles/semantic_native_import_receipt.json)
also records the installed native binary hashes. `pip check` passes after native
installation. The [Python pins](../research/object_discovery_boundaries_v1/runtime_profiles/semantic_cuda_requirements.lock),
[installed versions](../research/object_discovery_boundaries_v1/runtime_profiles/semantic_cuda_versions.json)
and [explicit conda toolchain pins](../research/object_discovery_boundaries_v1/runtime_profiles/semantic_conda_toolchain.lock)
are retained publicly, with [SHA256 records for all 73 conda packages](../research/object_discovery_boundaries_v1/runtime_profiles/semantic_conda_package_manifest.json).
The worker's environment verifier matches all 99 installed distributions,
including pip and the
conda-managed build tools. Setuptools and wheel were reconciled to conda packages
at the same versions used for compilation; stale replaced records were archived
privately after verifying every replacement package file exists. Archive checks
were not disabled.

This validates compilation and imports, **not model construction or inference**.
The inspected machine reports CUDA unavailable and zero devices. The unchanged
upstream constructor allocates CUDA tensors, so a real load-and-inference check
requires suitable GPU hardware. No GPU execution, Kaggle job or upload occurred.
The six-board comparison stays blocked on the remaining one-image backend checks.
