# InternVL driver-library environment repair and successor

October 16, 2026. Attempt 1 remains consumed and ERROR; it was not retried.
This repair prepares a successor for review only. No new GPU/CPU provider job,
reservation, launch claim, upload or model request was created.

| Change | Behavior |
|---|---|
| Driver-library search path | Keep only absolute, deduplicated entries from the platform's LD_LIBRARY_PATH in the otherwise isolated child environment |
| Isolation | Keep host PYTHONPATH, LD_PRELOAD, credentials and unrelated host variables out; retain offline install and Agg settings |
| Invalid environment | Refuse malformed/oversized library path values; omit empty and relative entries |
| Diagnostic evidence | Before the first GPU query, write bounded driver-loader.json with selected paths, nvidia-smi resolution and file-presence checks; it loads no driver and certifies no allocated GPU |
| GPU gates and cleanup | Exact single RTX PRO 6000 check, deadlines, tracked process ownership, GPU cleanup and completion-witness requirements stay intact; driver failure cannot become a passing attempt |
| Successor binding | Separate private notebook target, same account, exact image, model revision, input/wheel inventories and six-generation scope |
| Prior attempts | Bind the consumed GPU claim and terminal failure evidence into the successor's review history; both consumed CPU attempts and earlier snapshots remain untouched |

The changed private review lock is:

`03248a0d5566b9aad4831ee82e05997c288c5acab0ed86e9efc49283198189a3`

It has no source/compute approval, reservation or claim. Its declared authority cell
is still None and refuses before installation or GPU queries. Prior approval of the
consumed package does not authorize this successor. The scope proposed for a fresh
attempt remains one RTX PRO 6000, requested session timeout 3,600 s, worker 3,300 s,
six generations of at most 4,096 tokens each, zero game actions/scorecards, owner-only
access, internet/TPU off and no automatic retries. Provider overhead may exceed one hour.

## Validation

- All 108 Linux tests passed with no failures or skips, including the 20 external
  operator regressions and four new driver-environment cases.
- A CPU-only test traversed both the consumed and corrected supervisors' real query
  paths while replacing the GPU executable with a tiny synthetic shared-library
  probe. The old child failed (exit 1; path missing), and the corrected child loaded
  it (exit 0). The corrected path retained diagnostics; both simulated failures
  stayed incomplete with GPU cleanup unverified. No real GPU query or model ran.
- The isolated environment regression verifies that unrelated Python paths,
  preload hooks and a synthetic credential never reach the child.
- The private snapshot's source/artifact/builder hashes and runtime payload match;
  its independent rebuild is byte-identical. The exact notebook, supervisor and
  seal all reject missing approval. All 216 inventory entries match the prior CPU
  verification basis; model/data content and scientific requests are unchanged.
- The successor builder accepts explicit validation receipts and notebook bindings,
  and reads the consumed-attempt registry instead of hard-coding zero prior GPU
  attempts. It refuses missing or mismatched prior terminal evidence.

This confirms the environment-stripping mechanism and its repair, not that Kaggle's
actual NVIDIA library exists or can load in a new allocation. Attempt 1 did not
retain its parent loader paths. Platform driver absence is still possible; the
new diagnostic record is designed to resolve that uncertainty if it recurs.
No full real-checkpoint load, pretrained identification response or GPU compatibility
result is claimed. CPU fixture compilation is local, not a new Kaggle CPU job.
