# Phase 2 cd82 retained-evidence review

The two fresh E1S-R runs on cd82-fb555c5d, seed 104759, reproduce the same
unproductive trajectory. Both source locks and run artifacts validate. This
review uses retained frames and proposals only, with no inspection of game
implementation, hidden mechanics, or holdouts.

## Verified observations

Each run has 80 valid model proposals, 80 acknowledged actions, zero queue or
inference transport failures, zero policy failures, zero quarantine, zero
completed levels and official RHAE score 0. Both stop at the 80-action cap.

The model clicks (x=15,y=15) 79 times. Action 5 clicks (20,20) once; actions
6–80 return to (15,15), giving a 75-action identical-click streak. Both runs
retain exactly the same action and observation trajectory.

There are 51 one-cell changes and 29 transitions with no final-grid changes.
All changed coordinates are in row 63, columns 13–63, using zero-based
row/column coordinates. Each cell changes from palette value 4 to 5, progressing
from the right edge toward the left. Every pixel in rows 0–62 remains unchanged.
This is consistent with a bottom-edge time/action indicator, but its meaning
is an inference, not verified game mechanics. The existing grid-change metric
therefore cannot be interpreted as evidence of task progress in these runs.

Each run charges 2,005,762 prompt tokens and 1,760 completion tokens. These are
reported workload costs, not evidence that context length caused the repetition.

## Treatment decision for this evidence

No E2–E4 treatment is admitted. Classification remains unsupported_other.
The observations establish repeated ineffective action selection, but cannot
identify exactly one missing capability:

- E2a/E2b/E2c: intermediate sequence bytes were not retained. Neither a missing
  event nor summary aliasing nor a need for selective rich evidence is proven.
- E2d: the visible final-frame scene does not change outside the bottom row;
  no movement/identity failure is isolated.
- E3: no successful mechanic is demonstrated and then forgotten. Repetition
  alone does not establish memory failure.
- E4: no older exact observation is shown to resolve a current decision.

The pattern is a lead for action selection, orientation or exploration review.
It does not itself admit E5/E6 or justify a multi-action queue. The 75-action
streak and row-specific analysis are post-hoc descriptions, not new prospective
success thresholds. No fallback, prompt or controller is changed by this review.

The appropriate present decision is to retain E1S-R and record no justified
Phase 2 treatment from these runs. A V2 GPU rerun is not automatically warranted.
Administrative closure is recorded in config/phase2_closure.json after the owner
confirmed the provider runtime and the single-attempt inventory.

## Artifact provenance and reproduction

- R1: cd82-a53509512e87466c8ae53b19f45f0924-R1,
  run.json SHA-256 97c75b84abbb069ab0de022c41febb640ac9aff1e23cec9382695d1b382a17f7.
- R2: cd82-17b05b0c3e6344ebbd6c45399d941155-R2,
  run.json SHA-256 bebcefe0b336170f24f13f9d8ed1e52e6537400bb88e079994e99f33e794f993.
- Shared normalized trajectory SHA-256:
  88c74f82cb9d1b4b376c7314bb6894bf5683132a0305274aa3a81c3a24b1b13f.

```bash
make validate-phase2-reproduction
.venv/bin/python scripts/review_phase2_trajectory.py reports/runs/phase2-cd82/phase2-cd82
```

The downloaded notebook records 1155.962916959 seconds (19m 16s). This is
notebook elapsed time, not complete provider-accounted accelerator usage.
The owner subsequently reported Kaggle runtime 19m 25s and confirmed no other
Phase 2 attempts. The ledger charges 1165 seconds on that explicit attestation,
leaving 27635 seconds unused; it is not an independently fetched billing record.
The raw run files remain in the ignored reports/runs directory;
preserve the Kaggle output download alongside this report.
