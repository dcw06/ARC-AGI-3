# CPU intake validation

The focused command `python -m unittest discover -s tests -p test_direct_publisher_smoke_preflight.py -v` passed all 10 tests in the existing Linux Python environment. This includes the symlink refusal; Windows passed the other nine tests and skipped symlinks because creating them was unavailable.

Coverage: nominal fixture integrity without permission/launch claims; same-size wheel tampering; missing and extra files; publisher metadata tampering; package-version mismatches even when the metadata is rebound in the fixture; trusted-lock and trusted-manifest tampering; symlinks; a deadline crossed on the final check; and consistency of the retained 174 production inputs. Fixture payloads are small inert bytes, not installable wheels.

`python scripts/direct_publisher_smoke_preflight.py review-check` passed locally in Linux. It verified the review artifact/source bindings and disabled GPU/TPU/internet metadata, then executed the embedded notebook in an isolated process with decoy pip/GPU-query executables. The missing dataset mount was refused; no decoy was invoked and no temporary source files remained. The receipt is `review_check.json`.

These checks establish local integrity-control behavior only. The real mounted wheel payloads, consuming account's attachment/version, applicable use permissions and GPU compatibility remain unverified. No pip installation, provider submission, reservation, model request or GPU run took place. The authoritative redistribution decision file retains SHA-256 `4a07339315f220b099c1489a0d15e7fe9f2d2eace1fd15123c593d5ae8ccd3ce`.
