# Initial-geometry submission SSL diagnosis — October 18, 2026

The leading diagnosis is an oversized notebook/API request rejected during
upload, surfacing as SSL EOF in the client. A size-dependent failure was
reproduced against a read-only Kaggle endpoint after a successful, verified TLS
handshake. This is strong evidence for a packaging/transport problem; it is
not a GPU runtime result. The exact SaveKernel rejection status, service limit
and infrastructure layer remain unconfirmed.

No notebook save, GPU job or new attempt was made during diagnosis. Approved
private r4 remains unchanged, with review-lock SHA256
`e0452a412ecc0fe2be93c954547fbf88ad824272cc3f4ee36dadb75f04af6476`.
Both earlier uncertain attempts and their single-use claims remain consumed.

## Original failures

| Observation | Attempt 1 | Attempt 2 |
|---|---|---|
| Operator | Windows Python HTTPS | WSL Python HTTPS |
| Successful authenticated reads before submission | 11 HTTP 200 responses | 11 HTTP 200 responses |
| SaveKernel sends | Exactly one | Exactly one |
| Result | SSLError / abrupt SSL EOF; no returned HTTP status or version | SSLError; no returned HTTP status or version |
| Notebook bytes | 57,967,648 | 57,967,905 |
| Reconstructed SDK JSON request-body bytes | 57,968,542 | 57,968,799 |

The JSON bodies were reconstructed offline from the retained launch notebooks
using the installed SDK serialization and Requests JSON preparation, without
authentication or a network call. Reconciliation at 15:32:21 UTC still found
no target notebook among 73 owner notebooks. This does not justify recycling
either uncertain reservation. Windows and WSL share the same machine/network;
their failures are not independent physical-network tests.

## Controlled read-only reproduction

Only the authenticated `GetAcceleratorQuotaStatistics` metadata RPC was used.
The ordinary JSON body was padded with ASCII whitespace; parsing was checked
to produce exactly the same JSON value. No notebook source or experiment data
was transmitted. Each size was tried once, with retries disabled, stopping at
the first failure.

| Request body | Result | Elapsed |
|---|---|---|
| 2 bytes | HTTP 200 | 0.198 s |
| 8,388,608 bytes (8 MiB) | HTTP 200 | 1.031 s |
| 60,817,408 bytes (58 MiB) | SSLError while writing the body | 0.430 s |

All three connections completed TLS 1.3 handshakes with certificate validation
and hostname checking enabled. The certificate issuer was Google Trust
Services / WR3. There was no effective Requests proxy or custom CA environment
override. The large request failed during its body write, after the handshake;
it was not a certificate-verification failure. Instrumentation counts only
successful socket-write returns, so it cannot prove that no part of that
failed body reached the server.

A second control sent **headers only**, using `Expect: 100-continue` and no
body, to the same read-only endpoint:

| Declared Content-Length | Server response | Elapsed |
|---|---|---|
| 57,968,799 bytes — exact attempt-2 body size | HTTP 400 Bad Request; empty body; connection close | 0.119 s |
| 2 bytes | HTTP 100 Continue | 0.111 s |

Both headers-only connections also completed verified TLS handshakes. Only
the declared length changed between these two probes. The large length was
rejected before sending a body. This corroborates a size-dependent rejection,
but **400 is not 413**: no explicit size-error message was returned. The
quota RPC and SaveKernel may have different service limits, and no exact
threshold was measured. The original SaveKernel failures must remain recorded
as SSLError with no observed HTTP status.

Diagnostic environment: Linux Python 3.12.3, OpenSSL 3.0.13, Requests 2.34.2,
urllib3 2.8.0, Kaggle 2.2.4 and kagglesdk 0.1.37.

## Why this notebook is large

| Embedded payload component | Files | Compressed bytes |
|---|---:|---:|
| Game-environment wheels | 31 | 43,212,532 |
| Other ZIP entries, including the payload manifest | 86 | 237,951 |
| Complete ZIP, including archive overhead | 117 | 43,469,549 |

The 31 game wheels account for about **99.4% of the ZIP's total size**.
Base64 embedding expands the ZIP into roughly 58 MB of notebook source, which
the SDK then sends inside a JSON request. An in-memory ZIP excluding wheel
bytes was only **251,017 bytes**. This is a size estimate, not a runnable or
approved successor: manifests, bootstrap checks and dependency acquisition
would all need to be rebuilt and reviewed.

## Interpretation and next fix

Python defines SSL EOF as abrupt connection termination, which alone does not
identify its cause. [Python SSL documentation](https://docs.python.org/3.12/library/ssl.html#ssl.SSLEOFError).
An upstream urllib3 report documents large uploads whose server-side HTTP
rejection appears as SSLEOFError instead of the expected HTTP response. That
is consistent with this reproduction; it does not establish Kaggle's exact
limit. [urllib3 issue 2733](https://github.com/urllib3/urllib3/issues/2733).

The practical fix is to remove binary wheels from notebook source. A successor
should resolve the same 31 exact, hash-pinned wheels from a verified mounted
source, using the already attached competition inputs if their bytes match.
If those inputs do not supply the exact wheels, separately staging a reviewed
private dependency artifact is another option. Keep the experiment, prompts,
game versions, offline installation and hash verification unchanged.

Before another launch, rebuild and review the smaller notebook, verify exact
mounted wheel availability/bytes and the serialized request size, and obtain
authority for its new lock and one fresh attempt. Changing Python or disabling
TLS verification would not make an oversized request acceptable. Further
retries of unchanged r4 are not supported by this diagnosis.

## Retained evidence

Private diagnostic scripts and receipts remain git-ignored under
`.cache/github-review/initial-geometry-ssl-diagnosis-2026-10-18/` in the main
workspace. These receipts contain metadata only, not credentials or source
notebook bodies. All diagnostic provider operations were reads; no SaveKernel
was called. The headers-only interception uses an intentional `Captured`
exception to stop normal SDK response parsing; those ledger entries are not
additional failed submission attempts.

| Receipt | SHA256 |
|---|---|
| `offline-r1.json` | `f28c335bea17d52be503e0d9f96c065dd2463069d810dfa63c7e640b6163b774` |
| `readonly-wsl-r1.json` | `3393369cd9a98b6b7bb42fa5a21a31d034d3cff50cef6162b42172e6e2a2d001` |
| `headers-only-wsl-r1.json` | `292c2b822076aa05e8ef37393d20c35565d68ececb58d6db93a8fa0f267a3823` |
