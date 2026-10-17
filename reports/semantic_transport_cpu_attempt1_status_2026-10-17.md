# Semantic transport CPU check: first submitted attempt

**Completed:** provider status COMPLETE; mounted hashes, reconstruction, cleanup
and finalization pass collection and independent offline audit. The worker took
144.189 seconds. See the [verified results](semantic_transport_cpu_attempt1_results_2026-10-17.md).
The submission-stage observations below are preserved chronologically.

After the owner approved CPU review r2, fresh read-only preflight passed and
exactly one private CPU notebook version was submitted. It was accepted without
provider error or rejected sources. The last retained status is **RUNNING**;
no completion or mounted-byte result is claimed yet.

| Check | Status |
|---|---|
| Account and source preflight | Target absent; source remains private version 1, zero collaborators; 21 filenames and sizes match |
| Source approval | Owner approval retained verbatim against exact private r2 lock and CPU scope |
| Provider saves | Exactly one; single-use claim consumed before send; no automatic retry |
| Saved notebook | Source matches the hash-bound request exactly; only the declared authority slot differs from review |
| Saved configuration | Private, GPU/TPU/internet off; immutable image matches; intended dataset attached |
| Time limits | Requested session timeout 1,200 seconds; worker 1,100 seconds, with a 120-second cleanup reserve |
| Installs / model work / game actions / scorecards | All zero by authorized scope |
| Completion and mounted byte verification | Pending collection and independent checks |
| Provider attachment version label | Requested version 1; API returns an unversioned attachment ref, so saved-run version evidence remains qualified |
| Semantic-SAM GPU inference | Not authorized or launched by this CPU approval |

Before the sole send, the local guard refused SDK serialization because the SDK
omits three empty attachment arrays. No SaveKernel call occurred at that point.
The operator materialized those same declared empty arrays on the wire and
revalidated the unchanged reviewed notebook and request. Fresh preflight then
passed. The original zero-save receipt and the same reservation are preserved;
there was no provider submission retry or new compute attempt.

An initial local post-save source comparison also refused because the authority
dictionary had a different key insertion order before its JSON round-trip.
The subsequent offline audit rebuilt the exact outgoing request, matched its
retained claim hash, and verified that the saved notebook matches that exact
request and the approved authority literal. Source outside that slot is identical
to review. Both diagnostic records remain preserved; no provider write followed.

The consumed attempt, approval, preflight, request claim, submitted/saved source
and diagnostics remain private and git-ignored. Terminal collection must require
provider COMPLETE, under-limit lifecycle evidence, successful temporary-original
removal, all pinned mounted hashes and the matching result/witness/final marker.
No test or saved receipt alone establishes a successful mounted check.
