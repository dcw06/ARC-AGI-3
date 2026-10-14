# Shortcut Baseline Report v1

Computed mechanically before any model execution. Unit: one scenario. Accuracy is scored only on determinable scenarios; unsupported certainty is reported separately on underdetermined scenarios.

The strongest shortcut is selected on the development split only. The evaluation split is not used for shortcut selection.

| Shortcut | Dev determinate accuracy | Eval determinate accuracy | Eval unsupported certainty | Wrong eval determinate scenarios |
| --- | ---: | ---: | ---: | ---: |
| repeat_last_observed_outcome | 0.250 | 0.125 | 1.000 | 7 |
| ignore_coordinates | 0.750 | 0.000 | 1.000 | 8 |
| assume_available_means_effective | 0.000 | 0.000 | 1.000 | 8 |
| failed_dispatch_means_no_change | 0.250 | 0.125 | 1.000 | 7 |
| final_frame_only | 0.375 | 0.000 | 1.000 | 8 |
| always_no_change | 1.000 | 0.000 | 1.000 | 8 |
| always_unknown | 0.000 | 0.000 | 0.000 | 8 |
| most_recent_rule_everywhere | 0.250 | 0.125 | 1.000 | 7 |

Development-selected strongest shortcut: `always_no_change`.
Wrong determinable evaluation scenarios: S01-04, S02-04, S03-04, S04-04, S05-04, S06-04, S07-04, S08-04.

These are small synthetic construction checks, not model results or a generalization estimate.
