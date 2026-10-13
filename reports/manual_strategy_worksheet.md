# Private human-strategy annotation worksheet

October 13, 2026. The owner supplies the answers; the assistant does not populate inferred strategies as labels.
The local worksheet covers **ls20, s5i5, cd82, ft09, ka59 and sc25, levels 1–3 only**: 18 entries.

| Input | Purpose |
| --- | --- |
| Objects and roles | Distinct objects, targets, obstacles and interface elements |
| Controls and execution | Available actions, intended targets, effects and unsuccessful/unchanged actions |
| Goal and confirmation | Completion criterion and its observed confirmation |
| Rules and evidence | Probe, effect, prediction, correction and uncertainty |
| Solving strategy | Successful sequence, ordering, corrections and resets |
| Similar objects | Shape/color/structure matches and whether visual matches share a function |
| Transfer | Expectations in level 1; reused rules and new constraints in levels 2–3 |

The replay uses the owner's retained manual logs, verifying paired inputs and before/after continuity up to the
third completion. It renders the **final returned frame per input**, omitting animation frames and every
following-level board at a completion boundary. It lists the completion input separately. No engine, model,
Kaggle, GPU or live-game call is made.

Hovering over the board shows live zero-based `(x, y)` coordinates and the cell color, using the rendered content
area rather than the CSS border. Hover does not select a point or save an answer. Clicking selects a reference
point; subsequent hovering updates the readout without changing that selection. A named point can identify the intended object/control on that exact
frame; its coordinates and board hash are retained. Such a point is **not a complete object mask or a proven
clickable region**. References for segmentation, similarity and functional claims still need independent review.

Answers autosave locally, with explicit Save now, per-entry optimistic revision checks, atomic current-file
writes and immutable revision snapshots. A browser-local draft is retained until a save succeeds. Navigation
saves first; network/conflict errors retain the draft. Empty entries remain drafts. All seven fields require
text (including “unknown”/“not applicable”) before an entry can be marked ready for review. Ready is not approved.

Download JSON for answers or ZIP for answers, replay boards and provenance. Both exports remain private. No human
logs, answers, boards, account details or completed annotations are included in GitHub commits. Source hashes
and the context hash bind annotations to their retained evidence; restarting against changed logs is refused.

```sh
python scripts/serve_manual_strategy_worksheet.py --data <private-folder> --port 8791 \
  --log <ls20-log> --log <s5i5-log> --log <cd82-log> \
  --log <ft09-log> --log <ka59-log> --log <sc25-log>
```

The data directory must be git-ignored or outside a repository. The service binds to `127.0.0.1`, checks Host and
Origin, requires a page token for saves, and serves no arbitrary filesystem paths. It is a private development
annotation aid. Human first-level success does not certify agent success; the later agent baseline must actually
complete each first level within its separately agreed budget. No frozen protocol or compute approval changes.

Verification: nine automated persistence/scope/provenance/HTTP checks passed, plus 15 browser checks using
the six real logs in an isolated test-answer folder. Browser checks covered all 18 entries, initially empty
fields, autosave, live hover coordinates without selection/saving, separate hover/selected coordinates,
named point coordinates, entry separation, ready status, reload, explicit draft recovery and
JSON/ZIP downloads. Automated test text is excluded from the owner's answer folder.
