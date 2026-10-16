# InternVL identification successor: one submission

Follow-up: the attempt is COMPLETE. Runtime evidence verifies the RTX PRO 6000,
six generations and cleanup, but all six responses fail the coordinate contract.
See the [completed results](internvl_object_identification_v1_results_2026-10-16.md).
The initial submission observations below are preserved.

October 16, 2026, 16:52 UTC. The owner approved successor review lock
`03248a0d5566b9aad4831ee82e05997c288c5acab0ed86e9efc49283198189a3`
and one fresh RTX PRO 6000 attempt. This is separate from the consumed, failed
first attempt. All earlier attempts, claims, receipts and snapshots are preserved.

| Check | Retained result |
|---|---|
| Approval | Exact-hash source/use/compute records and a fresh unique reservation; unchanged reviewed template |
| Read-only preflight | Passed account, quota, absent target, source versions, private access and all 216 inventory entries; no provider writes |
| SDK dry check | Exact outgoing request and authority-data-only sealing passed; no provider calls or claim consumed during dry check |
| Submission | Exactly one SaveKernel at 16:51:33 UTC; accepted as saved version 1 with no rejected sources |
| Saved-package verification | Independent readback matches exact sealed source, private/GPU/offline settings, immutable image, requested shape and available source identities |
| Initial status | RUNNING at the subsequent read-only check; this is not a completion or scientific result |
| Consumption | Fresh claim and send marker consumed once; no automatic retries |

Scope: one requested RTX PRO 6000, requested session timeout 3,600 seconds,
worker limit 3,300 seconds, six generations with at most 4,096 new tokens each,
zero game actions or scorecards, internet/TPU off, account-only notebook and raw
outputs. The owner accepts provider allocation/setup/mounting/release overhead
beyond an hour. No enforced entire-job cap is claimed.

The provider API does not echo the session timeout or explicit dataset-version
labels. These were validated in the actual outgoing request; mounted bytes must
still pass the runtime hash checks. Saved configuration does not prove physical
RTX allocation or working drivers: the notebook must independently verify them
before model work. There is no pretrained response, identification score, cleanup
verdict or technical-completion claim yet. Raw evidence and notebook bindings stay
in the private, git-ignored workspace.
