# Stage B launch R2 import-boundary review

Status: **GPU disabled and unapproved. No reservation, upload, or GPU run.**
The R1 target notebook and R1-R5 source snapshots remain unchanged.

The model host imports `bridge_service`, which imports the Stage B contract for
the canary and protocol. The contract previously imported the historical
policy request builder at module load; that path reaches game-only packages.
R2 moves that import into `policy_request`, which is called in the game worker.
The model-side canary and token guard still use the same frozen protocol and
request formats. The game/model interpreter split is unchanged.

A fresh isolated Python subprocess blocked imports of both `arcengine` and
`arc_agi`, imported the **actual** model host, bridge service, and token guard,
constructed the canary request, and verified neither game package entered
`sys.modules`. The complete local Stage B suite passed: **50 tests**.

The new GPU-disabled target notebook was independently unpacked and checked
against **1,042 source bindings**. Its unapproved execution stopped at the
Stage B authority gate before installation or GPU access. R2 review lock
SHA-256: `2452a94693d37e051bc1b70092e537b316614c56d4dbcdcdc82f33d46d1ba57a`.
The notebook is 692,915 bytes and retains the same private, Internet-disabled
attachments and 3,600-second proposed provider envelope. The active authority
gate now references R2; R1 remains historical and cannot authorize this source.

The reviewed notebook is not a launch package. Explicit source approval,
separate compute authorization, a fresh one-use reservation, sidecar-bound
package verification, and provider quota check must precede submission. Any
such package should be independently reviewed against this exact R2 lock
before one launch. Exact billing and Phase 4 certification remain open.
