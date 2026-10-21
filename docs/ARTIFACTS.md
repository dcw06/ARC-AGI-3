# Evidence and transfer artifacts

This checkout contains frozen run archives, generated notebooks, and a Git transfer bundle. Several contracts record exact digests or archive inventories; Windows transfer tooling references `repository.bundle`, `TRANSFER.json`, and `SHA256-INVENTORY.json`.

These files are deliberately retained by this maintenance change. Deleting them merely to reduce the displayed repository size would break existing retrieval and provenance paths.

A future storage migration must first identify every referencing manifest and replay command, publish immutable assets at a verified destination, preserve digests and access permissions, and test retrieval/replay before removing tracked duplicates. Update current pointers additively; never edit historical evidence to conceal a change. Do not republish third-party bundles whose redistribution has not been established.
