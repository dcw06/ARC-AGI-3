# Stage B target launch R1 review

Status: **GPU disabled and unapproved. No reservation or GPU attempt was made.**
The earlier R1-R5 source snapshots remain unchanged.

The real monitor's RSS probe now accepts the worker PID supplied by the
monitor collector and rejects any other PID. The host and worker use one
artifact contract with tree SHA-256, file count, and byte count. The host
checks the full measured artifact against the frozen profile before model
startup, and the game worker requires exact equality at bridge readiness.
The frozen expected byte count is 64,526,033,084.

The connected CPU supervisor rehearsal covered a successful archived
trajectory replay and five fail-closed variants: model-startup failure,
cancellation, admission deadline, evidence exhaustion, and independent GPU
cleanup failure. It checked worker release where appropriate, process-group
exit, scratch removal, and retained outer/cleanup receipts. These tests use
scripted processes and injected GPU telemetry; they do not prove target GPU
startup or provider cleanup.

The new **target launch review notebook** contains the runnable first-cell
entrypoint and its source closure. It is private, Internet-disabled, and
GPU-disabled. Independent unpacking verified 1,042 source bindings and its
artifacts. Executing the review notebook without sidecars stopped at the
Stage B authority gate before installation or GPU access. Review lock
SHA-256: `061c8ea376b40e0e235c95537d8641ba28f1872a4241dc583447a5399dfda260`.
The notebook is 692,960 bytes. The historical development archive is not
embedded; the case protocol checks the frozen archive hash through the
packaged manifest when the archive is absent, and the runtime separately
verifies the mounted development game files against that manifest.

**Local verification:** 49 Stage B tests passed in WSL, including the real
`LiveProbes.rss(pid)` signature, byte-count mismatch rejection, notebook
unpacking, unapproved execution rejection, and the connected supervisor
matrix. The existing pinned-tokenizer audit covers the unchanged policy and
sealed-audit request construction; this revision changes startup plumbing and
the archive-mount binding, not those request formats. Live requests still
have a pre-transport tokenizer/context check.

The review lock alone is not launch authority. Separate explicit source
approval and compute authorization, a fresh one-attempt 3,600-second
reservation, sidecar-bound package verification, and provider quota check
remain required before any submission. The R1 notebook is the review
executable; no GPU-enabled copy has been produced or uploaded. Phase 4
certification and exact billing remain open.
