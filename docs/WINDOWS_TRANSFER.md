# Windows transfer

The accompanying ZIP contains the committed project working tree, ignored local
run/evidence records, game environments and environment dependency wheels,
reference/vendor files, a Git history bundle and an installed-package inventory.
It is not a complete offline model runtime: model weights and the large frozen
vLLM wheelhouse remain external Kaggle attachments.

## Open and continue

1. Extract the ZIP to a new directory. Open its `AGI` folder in your editor.
2. Read `reports/AGI_MEMORY_HANDOFF_2026-09-16.md` and the latest section of
   `certification/phase4_v6/README.md`. The handoff's uncommitted-work warning was
   written before this migration commit; `TRANSFER.json` identifies the committed
   checkpoint exported in this ZIP. This export changes no compute authorization.
3. Use Linux/WSL for execution. POSIX process groups, `fcntl`, `ps`, signals and
   `/dev/stdout` prevent running the pilot directly with native Windows Python.
   Recreate Python 3.12 dependencies; do not reuse a macOS virtual environment.
4. `.env.example` is included. Copy it to `.env` and enter your credentials
   separately if needed. Real `.env`, `.kaggle`, keys, caches and the Mac `.venv`
   were deliberately excluded. No authentication is required for reading the code.
5. `installed-packages-macos-reference.txt` records observed package versions;
   it is NOT a validated Linux installation lock. Check the Makefile, dependency
   manifest and frozen target installer before installing. Do not run submission,
   notebook-push or GPU targets as part of setup.

## Restore Git history (optional)

The extracted `AGI` has no `.git` directory, avoiding transfer of machine-specific
configuration and remote credentials. `repository.bundle` contains the commit and
reachable Git history. To reconnect the extracted working tree in Linux/WSL:

```sh
cd AGI
git init
git fetch ../repository.bundle HEAD
git reset --mixed FETCH_HEAD
git status
```

The mixed reset attaches the index/HEAD to the bundled commit without replacing
working files. Use these commands only in the NEW extracted directory, not an
existing project. Ignored evidence/assets remain present. No remote is configured
and nothing is pushed. Alternatively clone the bundle into a separate directory,
then copy the ignored asset/evidence folders from the extracted AGI.

`SHA256-INVENTORY.json` supplies a hash and size for every payload, including the
Git bundle. Preserve original archive/evidence bytes: historical locks depend on
exact hashes. Do not bulk-normalize line endings in locked source snapshots.

## Still blocked

Clean target-compatible Linux/CUDA offline installation and independent target
review remain unfinished. Review-r2 is GPU-disabled and unapproved. No fresh GPU
reservation, holdout access or scored submission is authorized. The completed
fixture prescreen's eight hours remain retained; no budget credit was released.
