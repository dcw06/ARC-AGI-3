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
point or region; subsequent hovering updates the readout without changing that selection. Object regions store
every coordinate in `target_points`, their inclusive `bbox_xyxy`, a board hash, a role and an optional `parent_id`.
Use **Rectangle: two corners** for all enclosed cells, or **Mask: click cells to toggle** for irregular shapes
and holes. Name and save the object, or check existing objects and choose **Group checked objects** to create a
parent from their union. Selecting an object displays its full region and coordinate count; child objects remain
separately editable. Older single-point markers remain in their own collapsed section.

For ft09 level 1, each of the four tile arrangements has **nine 6x6 child objects, each with 36 target points**.
The central diagram is a child object too. Each parent has **324 unique points**, excluding the gaps between
cells. Full initial-board regions were also added for the other games; original owner notes and point markers
were retained. ls20's owner-supplied interval pairs are interpreted as x ranges and y ranges for rectangles;
its five-pixel white cross and separate blue foreground masks are preserved explicitly.

These coordinate sets define localization/reference targets. They do **not** establish that clicking is legal,
that a click changes selection, or that a proposed role is correct. References and semantic labels still need
independent review. A rectangle can include background; a shape mask retains only its annotated pixels.

Answers and regions autosave locally, with explicit Save now, per-entry optimistic revision checks, atomic current-file
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

Verification: 12 automated persistence/scope/provenance/HTTP/geometry checks passed. They include 36-point cells,
324-point groups, exact mask holes, duplicate/out-of-board/type rejection, parent containment, cycle rejection,
frame/hash binding, restart/export and preservation when an older browser omits regions. Thirteen browser
checks passed for rectangle selection, full-coordinate saving, grouping, mask editing, hover, navigation,
older-draft restoration and JSON/ZIP downloads. Test answers are isolated from the owner's folder.

All imported real ft09 groups were additionally checked for nine 36-point children and a 324-point parent.
Existing text and single-point markers were compared before and after import; levels 2–3 were unchanged.
