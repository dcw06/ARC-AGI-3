# Stage B R9 compact-feedback review (CPU only)

**Disposition:** R9 is a GPU-disabled source review. It has no source
approval, compute authorization, reservation, package upload, or GPU run.
Prior R3 capacity is consumed. R7 and R8 notebooks remain immutable.

R7's six-frame feedback stress was 59,569 prompt tokens against a 60,000
limit; seven/eight repeated grids exceeded it. R9 supplies the pre-action
grid and every returned grid (up to eight) as lossless `hex_rows_v1`: 64
row strings of 64 hexadecimal color digits, in `grid[y][x]` order. The
full numeric frames remain in the durable action trajectory. Only the
sealed feedback audit request changes; policy requests and action choices
do not receive this encoding. Feedback accuracy under this format is a
new measurement, not directly comparable to a prior audit format.

For a dense eight-frame 0–15 pattern, the complete request is **41,137
bytes**, below the 196,608-byte transport ceiling. CPU tests verify
lossless round-trip, frame count, palette/shape rejection, and independent
replay of the exact compact request. The ninth frame, invalid grid, or a
live tokenizer/context violation fails before a feedback call; the
already returned transition stays in evidence. This is a bounded
representation, not a proof that the model can interpret every grid.

R8 exposed a replay incompatibility: its evaluator rebuilt the frozen
v1 CPU archive's feedback calls using the new request format. R9 fixes
that with an explicit record-version binding. Historical v1 records
reconstruct the original decimal-grid request and instruction; new v2
records reconstruct `hex_rows_v1`. The historical archive and the new
connected supervisor both pass focused replay tests. A record cannot
choose its format by editing a single request label; the evaluator
reconstructs every call from its declared record version.

The exact pinned tokenizer files were fetched from the fixed public model
revision and verified against the existing six-file SHA-256/byte manifest.
An isolated Python 3.12 CPU environment used Transformers 4.57.6,
tokenizers 0.22.2, and Jinja2 3.1.6. The complete audit is in
`reports/perception_stage_b_r9_token_audit.json`: all 12 exact scripted
requests fit, with a maximum of **25,799 prompt tokens**. Both repeated
and dense eight-frame stress requests fit. Their respective maxima are
**36,207** and **26,379 prompt tokens**, against the 60,000 per-call
ceiling. All realistic maximum-sized serialized response examples fit the
128-token completion cap. These stress patterns do not cover every
possible grid; the live service still re-tokenizes each exact request and
rejects a request above 60,000 prompt tokens or 65,536 total context
tokens before transport. No model calls were made in this audit.
The token-audit report SHA-256 is
`970a2bce11fcc0c9ffa4f0541e29ea4237f51bed63a7daf8b2323ad3c7e79191`.

The unpacked private R9 notebook verified **1,043** source bindings, has
GPU/internet disabled, and rejects execution without authority. Its
review-lock SHA-256 is
`fed295e46233285fa3c92ce190a1b9080fe19d791503d2e2da1ef63253028571`.
The new `live-r6` authority scope uses separate R6 approval and one-use
reservation files; previous approvals cannot launch it. The earlier
`MPLBACKEND=Agg` game-bootstrap fix passed local CPU testing but is still
unverified on Kaggle. Exact provider billing and Phase 4 production
certification remain open.

The full Stage B CPU suite passed **57 tests** after the historical replay
correction. The focused v1 archive, v2 connected-supervisor, and compact
feedback tests passed **19 tests**. `git diff --check` passed. R9 is
reviewable for a separate source-approval decision; this report does not
grant that approval or authorize GPU use.
