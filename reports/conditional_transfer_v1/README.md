# Conditional knowledge and cross level transfer

This is the Mac teammate's Plan 2 CPU milestone. It tests whether a proposed rule retains its conditions, exact coordinates, uncertainty and corrections when evidence is compressed or selected. It contains synthetic fixtures, independent keys, a deterministic writer, a scripted reader, component attribution and inert model-request drafts. No model or GPU was run.

The implementation is in `research/conditional_transfer_v1/` on branch `teammate/mac-conditional-transfer-v1`. The checkout is `~/projects/ARC-AGI-3-track2`. Open that folder in VS Code to work on these files.

Read [the results](report.md), [the frozen applicability protocol](protocol.md), [the CPU verification receipt](verification.md), and [the later study proposals](later_proposals.md). Machine-readable results and the full request schedule are in [review_package](review_package/).

## Reproduce on CPU

Run from the Track 2 checkout with its existing Python environment and verified tokenizer cache:

```bash
source .venv/bin/activate
python -m unittest -v \
  tests.test_conditional_transfer_v1_fixtures \
  tests.test_conditional_transfer_v1_components \
  tests.test_conditional_transfer_v1_selection \
  tests.test_conditional_transfer_v1_package
python -m research.conditional_transfer_v1.build --check
python -m research.conditional_transfer_v1.replay
```

`--check` compares all generated package bytes without changing the checkout. The builder without `--check` writes only this new development package. Replay checks hashes **and** reconstructs the original evidence, independent keys, requests, selection and verdicts; changing a manifest cannot legitimise forged evidence.

## Package contents

| File | Purpose |
| --- | --- |
| `benchmark.json.gz` | 144 original source–target trajectories and transition records |
| `independent_keys.json` | Independently derived, evaluator-only answers and reference alternatives |
| `requests.jsonl.gz` | 3,354 unique inert development reader requests |
| `request_aliases.jsonl.gz` | All 5,184 dependent probes, including duplicate aliases |
| `schema_probes.jsonl.gz` | Six separately counted, unexecuted schema probe requests |
| `schema_probe_keys.json` | Evaluator-only expected probe answers |
| `attribution.jsonl.gz` | Four-stage verdicts, faults and provenance coverage per probe |
| `shortcuts.jsonl.gz` | Eight full-source shortcut outputs and scores |
| `summary.json` | Arm, family, delay and shortcut measurements |
| `token_audit.json` | Final prompt and completion bounds, selection IDs and schedule costs |
| `protocol.json` | Frozen prompts, response schemas, sampling, endpoints and stop rules |
| `source_hashes.json`, `manifest.json` | Source/dependency bindings and artifact integrity |

All compressed files are ordinary gzip, readable with Python's standard library. Reader requests contain no evaluator keys or fixture-family metadata. Keys and attribution remain evaluator-side files and must never be sent to a model.

There is no network client, launch command, approval, reservation, model download or runtime in this package. Mac CPU verification establishes construction behaviour; it does not establish Linux/Kaggle compatibility or model performance. Frozen Track 1–3 files and archived evidence remain unchanged.
