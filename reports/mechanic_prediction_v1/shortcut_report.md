# Shortcut Baseline Report v1

Computed mechanically before any model execution. Unit: one scenario. Accuracy is scored only on determinable scenarios; unsupported certainty is reported separately on underdetermined scenarios.

The strongest shortcut is selected on the development split only. The evaluation split is not used for shortcut selection.

| Shortcut | Dev determinate accuracy | Eval determinate accuracy | Eval unsupported certainty | Wrong eval determinate scenarios |
| --- | ---: | ---: | ---: | ---: |
| repeat_last_observed_outcome | 0.250 | 0.250 | 1.000 | 6 |
| ignore_coordinates | 0.250 | 0.250 | 1.000 | 6 |
| assume_available_means_effective | 0.250 | 0.250 | 1.000 | 6 |
| failed_dispatch_means_no_change | 0.250 | 0.250 | 1.000 | 6 |
| final_frame_only | 0.375 | 0.375 | 1.000 | 5 |
| always_no_change | 0.250 | 0.250 | 1.000 | 6 |
| always_unknown | 0.000 | 0.000 | 0.000 | 8 |
| most_recent_rule_everywhere | 0.250 | 0.250 | 1.000 | 6 |
| position_only | 0.000 | 0.000 | 0.000 | 8 |

Development-selected strongest shortcut: `final_frame_only`.
Wrong determinable evaluation scenarios: S04-04, S05-04, S06-04, S07-04, S08-04.

These are small synthetic construction checks, not model results or a generalization estimate.
