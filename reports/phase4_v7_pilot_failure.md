# V7 pilot version 1 failure

The offline split installation succeeded on Kaggle in 127.801 seconds. The worker then failed at `verify_environment_mount` with `ValueError: environment mount inventory differs from package`, before constructing or starting `ModelProxy`. This is an integrated game-artifact path failure, not a new dependency-resolution failure.

The v7 entry point passes the competition's entire `environment_files` directory to the worker. The strict verifier expects exactly the 30 manifest files for the frozen 15 development games. By comparison, the v6 notebook builder copied only manifest-selected game files into its temporary source tree, verified their sizes and hashes, and passed that staged directory to the pilot. The v7 integration omitted that step.

Target logs do not retain a directory listing, so they do not distinguish additional files from missing files. The transferred local assets contain exactly the 30 expected files and pass verification; they cannot establish the current competition mount's inventory. Do not weaken the worker's inventory check or update frozen game hashes to accommodate the target.

The next source revision should restore explicit manifest-only staging before expensive installation: read only expected game paths, reject symlinks and path escapes, check sizes and hashes, copy into a temporary directory, verify its exact inventory, and pass it to the worker. Missing or changed expected files must fail with a specific path before installation. Staged games must remain covered by lifecycle cleanup. A regression check should cover a mount containing unrelated extra games, missing expected files, modified expected files, and symlinks. The repair then needs a new reviewed source/notebook snapshot; the approved v7 files and historical notebook remain intact.

The logs also contain `sitecustomize` warnings about missing `wrapt`. They were nonfatal in this attempt: both child roles executed, and the worker traceback identifies the game inventory check as the fatal error. Review interpreter startup isolation separately before another pilot. The independent evaluation reports missing monitor evidence even though final monitor files exist; it conservatively failed, and its collection/finalization ordering should also be reviewed.

Final result: failed, no model workload or capacity evidence. The final notebook receipt records 132.544 seconds and source removal. Other receipts verify dependency-tree removal, scratch removal, process cleanup, and GPU cleanup. These establish cleanup for this early abort only.

Account GPU usage changed from 26,675.767 to 26,818.521 seconds, a 142.754-second aggregate delta. Exact provider billing is unavailable. The attempt is consumed, all 28,800 reserved seconds remain retained in the local ledger, and no retry is authorized or submitted.

Preserved output: `evidence/phase4-v7-pilot-failed-v1.zip`, SHA-256 `560e93ca94b90a8ecb187287b9524bb6be91296cd4b05db2dade678c8b5dbc7c`. Per-file hashes and accounting are in `reports/phase4_v7_pilot_evaluation.json`.
