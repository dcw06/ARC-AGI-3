# Development entry points

Start with the credential-free CPU suite in the [README](../README.md). `requirements-ci.txt` is a small test environment; it does not install models or the target GPU stack.

For a complete local development environment, inspect `make setup` before running it. It installs the pinned toolkit and clones the official upstream framework. `make play-local` performs environment interactions and can fetch public game source; it is not part of offline CI. `make test` discovers the broader research test inventory and can need additional packages or frozen artifacts.

The authoritative design is [Plan 8](ARC-AGI-3_Project_Plan_8.md). Current configuration and report files determine eligibility and run status. Historical notebooks, reservations, and execution locks must not be treated as fresh compute authorization.

No maintenance change authorizes model inference, paid GPU execution, retrying consumed attempts, Kaggle upload/submission, or hidden-environment/holdout interaction. Review the relevant experiment protocol, resource accounting, and existing approval records before any such work.

The previous onboarding walkthrough is retained in [the historical README](HISTORICAL_README_2026-10-21.md); its v3 status and fallback-only wording are superseded by the root overview and committed results.
