# ARC3 vLLM H100 wheelhouse v3

Offline wheels for `vllm==0.19.0 torch==2.10.0 flashinfer==0.6.6` on Kaggle's
Python 3.12 image (CUDA 12.8 libraries from the `nvidia-*-cu12` wheels):

    pip install --no-index --find-links . --requirement requirements.lock --only-binary :all:

`requirements.lock` pins all 174 wheels; `SHA256SUMS` lists their digests.

This dataset was re-created on 2026-10-05 after the original was deleted. Every
wheel is the PyPI file of the same name the original held (the names come from
an install log of the original; sizes and sha256 are PyPI's), and the lock was
rebuilt from that log in the original's line order.
