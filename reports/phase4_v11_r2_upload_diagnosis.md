# V11 R2 upload rejection and packaging repair

The local launch receipt contains Kaggle's exact response:

```json
{"error":{"code":400,"message":"The kernel source must be less than 1 megabytes in size.","status":"INVALID_ARGUMENT"}}
```

Submission failed with HTTP 400 at 2026-09-18 00:39:06 UTC. The later monitoring 404 is a consequence of no notebook being created. This recorded rejection is a source-size validation failure, not evidence of a VPN, authentication, model or GPU-runtime failure. The original V11 attempt did not retain its response body; its matching oversized package suggests the same cause, but only R2 has the explicit provider diagnosis.

The R2 notebook is 1,127,654 bytes; its code cell is 1,127,050 bytes. Even the GPU-disabled original review notebook is 1,064,238 bytes. Source snapshots accumulated across revisions and exceeded the upload limit; a pre-submit size guard was missing.

`scripts/compact_phase4_notebook.py` losslessly replaces the embedded file payload's zlib/base64 encoding with LZMA/base85. It verifies the decompressed payload bytes are identical and leaves the remainder of the execution wrapper unchanged. No source file, hash binding, policy, dependency or authority check is removed. It enforces a conservative 900,000-byte whole-notebook ceiling and emits a GPU-disabled packaging review, not a launch-ready replacement.

Created `notebooks/phase4-v11-compact-review-r1`: 480,284 bytes, down from 1,064,238. The equivalent encoding measured against the rejected R2 code would reduce it to about 543 KB; a future fresh launch package must still pass the exact whole-file size guard after adding new authority sidecars.

Three local tests passed: exact decoded payload and untouched wrapper comparison, execution stopping at the closed authority gate, and rejection above the size ceiling. No GPU request was made during validation. Historical source/notebook artifacts and consumed claims remain unchanged.

Before another submission, integrate this encoding and the size guard into a newly reviewed launch package with fresh authority. The previous R2 command still targets its consumed oversized package and should not be rerun. The failed submission's eight-hour reservation remains retained; it is not evidence of eight hours billed.
