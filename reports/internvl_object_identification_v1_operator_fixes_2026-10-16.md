# InternVL external operator: preflight fixes

October 16, 2026. The five reviewed guard gaps are fixed in the supported external
operator. The approved notebook, runtime capsule, image, datasets and scientific
scope are unchanged; their review hash remains
`b272f08526b662e75fad68c1983fc4f78c8f86d629cd1f002489e5dc2376c134`.
The owner's approval and existing unconsumed reservation are preserved. No upload,
new compute job, model inference or game action is performed by this repair work.

| Finding | Repair |
|---|---|
| Numeric target ID can override the approved slug | Closed outgoing-field contract rejects IDs and unknown selectors, plus snake/camel alias duplication |
| SDK omits empty source arrays | Normalize omission/null only for source arrays whose reviewed value is empty; keep rejecting nonempty alternative sources and missing required attachments |
| Preflight can change after admission | Bind exact immutable receipt bytes to the claim; recheck hash, status, review lock, reservation, target, operator version and freshness at the actual send boundary |
| Consumption depends on the output folder | One stable reservation-ID registry with atomic claim creation and an exclusive send marker, shared across all revision folders; check retained legacy consumption records too |
| No independent verification after save | Read back and verify exact saved version/source, private/offline/GPU settings, image and attachments; stop and retain uncertainty/mismatches without another save |
| Failed preflight cannot be refreshed safely | Separate immutable preflight revisions from the one-use reservation; preserve all prior failures, provider listings and diagnostics |
| Optimized Python removes assertion gates | New operator checks use explicit exceptions, and are tested under `python -O` |
| Provider lists duplicate notebook rows | Deduplicate identities across fully enumerated pages; require the known private notebook and target absence; refuse incomplete pagination |

Use `scripts/object_identification_operations.py`, with explicit `preflight`,
`dry-check` and `launch` modes. The installed SDK adapter blocks writes in preflight
and prohibits all writes except one validated SaveKernel in launch mode. HTTP and
client retries are disabled. Validate the real serialized SDK body before spending
anything; consume the shared claim and send marker before forwarding the one write.
Errors/interruption during preparation, sending or readback retain a failure receipt.
The old private v1 operation and failed receipts remain preserved and superseded.

The stricter operator wraps the unchanged helper in the reviewed capsule. These
repairs do not edit the notebook or its runtime, and do not move its authority slot
or transfer approval to a changed package. External operator sources and validation
receipts have their own private hash lock, checked in preflight and before sending.

Validation: the original combined Linux group passed 103 tests; after the catalog
repair, all 20 operator tests pass (zero failures/skips), and the same 20 pass with
optimized Python. The unchanged runtime/lifecycle group accounts for the other 84
distinct cases. Two SDK regressions fail against the old comparison and pass with
the fixed wrapper. Other cases cover competing claims, uncertain partial records,
legacy consumption, changed/stale/failed preflights, transport refusal, mismatched
readbacks, ambiguous sends and retained failed preflight revisions. All test claims
and notebooks are temporary synthetic fixtures; socket calls are blocked in the
before/after SDK reproduction.

The private SDK exposes no saved `session_timeout_seconds` or image-pinning-type
field in GetKernel metadata. Verify the outgoing 3,600-second timeout and immutable
image request, compare the echoed image digest, and explicitly record missing echoes.
Do not turn absent dataset-version labels into verified version echoes. Source
identities still must match, and all 216 mounted files are hashed before installation.
Generic quota does not establish per-shape capacity or actual RTX allocation; runtime
census still requires exactly one RTX PRO 6000 before installation/model loading.

No actual post-save readback is possible until a future authorized submission; that
path is covered by offline successful and mismatched provider fixtures. Full target
checkpoint loading and GPU inference remain untested. Technical completion still
requires provider COMPLETE, output hashes, completion witness, cleanup and replay.

The final corrected operator passed a real read-only provider preflight: account,
quota, complete target catalogue, dataset identity/version/privacy and all specified
inventory sizes. The actual approved notebook then passed the real SDK serialization
and authority-binding dry check, with 16 serialized fields and zero provider calls
in that dry check. No claim, send marker or execution notebook was persisted.
The passing preflight is time-limited evidence and must be fresh at any future launch.
