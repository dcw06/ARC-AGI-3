# M0 frozen candidate audit

Date: 2026-09-09

The three-candidate M0 set was frozen before target-hardware measurement. All
three model cards declare Apache-2.0, immutable upstream revisions are recorded,
and public Kaggle inputs were measured offline rather than inferred from catalog
metadata.

## Frozen candidates and outcomes

1. `M0-Q38-27B-FP8`
   - Upstream: `Qwen/Qwen3.8-27B-FP8` at
     `017b9c7af6b5689d5dd426a76e0bc077eb5ca20a`
   - Kaggle input: `foysalemonshanto/qwen3-8-27b-fp8-repacked-v1/PyTorch/hf-fp8/1`
   - Measured bytes: 30,890,069,847
   - Tree SHA-256: `4854e2723eb8f25eb8590080c5295519fb6a03bf4f1370c1e1b6bff0b6b4408a`
   - Disposition: measured, not selected

2. `M0-Q3VL-30B-A3B-FP8`
   - Upstream: `Qwen/Qwen3-VL-30B-A3B-Instruct-FP8` at
     `d9748a51ae66354c4dad665aab2c71f26cf2c8cd`
   - Kaggle input: `qwen-lm/qwen-3-vl/Transformers/30b-a3b-instruct-fp8/1`
   - Measured bytes: 64,526,033,084
   - Tree SHA-256: `052ab27f06c28261e143b8c1638382d107b034692bc0cd1792ec4e02ddab8627`
   - Disposition: provisional primary

3. `M0-Q3VL-8B-FP8`
   - Upstream: `Qwen/Qwen3-VL-8B-Instruct-FP8` at
     `9cdc6310a8cb770ce18efaf4e9935334512aee45`
   - Kaggle input: `qwen-lm/qwen-3-vl/Transformers/8b-instruct-fp8/1`
   - Measured bytes: 21,200,194,392
   - Tree SHA-256: `67242ee8a868b0369fc39acd3bc0e1c66d1432d6a7b3b2a3c1ef0a76bb0801f1`
   - Disposition: provisional fallback

Official model collection: <https://www.kaggle.com/models/qwen-lm/qwen-3-vl>

## Engine and packaging disposition

The frozen launch stack is vLLM 0.19.0, Torch 2.10.0+cu128, Transformers
4.57.6, and CUDA 12.8-family wheels. The wheelhouse checksum manifest and index
manifest are pinned, the Kaggle-consumed metadata exception is named, and each
mounted payload is verified before installation. Each model then launched and
served streamed requests with internet disabled on the target accelerator.

The Kaggle dataset is labeled `other`. A metadata screen of its 174 wheel
distributions found five packages without useful declared license metadata and
NVIDIA CUDA runtime distributions with proprietary/LicenseRef declarations;
`pycountry` declares LGPL-2.1-only. M0 therefore clears only the observed use of
the unchanged public Kaggle input. The repository does not vendor or republish
those wheels. Redistribution and final release remain blocked on an exact
dependency-closure review or a replacement bundle. This is a project risk
classification, not legal advice.

Wheelhouse: <https://www.kaggle.com/datasets/driessmit1/arc3-vllm-h100-wheelhouse-v3>

## Target constraints

The competition overview identifies the upgraded RTX pool, nine-hour notebook
limit, internet-off submission environment, and public-model requirements used
by this audit.

Source: <https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/overview>

The selection is provisional because M0 establishes execution viability only.
No public score or unmeasured output-quality claim was used to choose between
the candidates.
