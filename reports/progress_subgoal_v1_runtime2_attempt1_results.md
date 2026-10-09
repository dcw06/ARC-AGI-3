# progress_subgoal_v1 runtime2: attempt 1 results (sanitized summary)

The attempt ran on October 9, 2026 under the frozen protocol (`reports/progress_subgoal_v1_protocol_v2_frozen.md`).
The source package was the private review snapshot r8, the public r7 package plus three private bindings. The owner
gave a source approval and a compute authorization for one attempt.

This page carries aggregate results only. The raw replies, the account and notebook identifiers, the private model
dataset reference and all private paths stay in the account-only workspace. The model is the dataset snapshot
described in `reports/progress_subgoal_v1_model_identity.json`.

## 1. Technical verdict: technically complete

| Item | Result |
|---|---|
| Submissions | 1 (attempt `psv1r2-170e3ce7b29548f6a912a9b4e0db4bf0`); no retry |
| Accelerator | one NVIDIA RTX PRO 6000 Blackwell Server Edition, as authorized |
| Lifecycle | passed in 1,091 s; final deadline met; process and GPU cleanup verified |
| Installation path | all 174 mounted wheels verified before installation (31 s), then the hash-pinned install (85 s); model tree verified (146 s); server ready (113 s) |
| Prefix caching | shown disabled in the retained server configuration |
| Questionnaire | 5,852 of 5,852 calls answered in 686 s, ending at about 1,087 s (admission cutoff 3,000 s), so the frozen deadline edge case did not arise |
| Counted HTTP requests | 5,863 (≤ 6,613): 5,852 questionnaire, 3 startup, 4 inference, 4 cancellation; 0 idle-check reads; 0 refusals |
| Generation requests | 5,859 (≤ 5,859) |
| Game actions, scorecards | 0 |
| Retained evidence | 5,856 files; every evidence-manifest hash matches |
| Independent evaluation | `technically_complete`; every mandatory runtime probe reconciled; prompt tokens equal the frozen audit on every call; review sources and review documents verified against the review lock |

## 2. Readiness: neither arm is eligible

Under the frozen §9, neither arm's outputs may feed memory or supervision. A is `raw_plus_computed_record`; B is
the same plus the constant safeguard. Both arms have perfect validity: 0 invalid responses of 2,790, and 0 of 1,510
gate-member responses.

| Condition | A | B |
|---|---|---|
| Validity (≤ 1% overall; ≤ 0.5% gate members) | passes | passes |
| Primary families at criterion (all 8 required) | 2 of 8 | 2 of 8 |
| Over-claim gates passing (all 5 required) | 1 of 5 | 1 of 5 |
| Uncertainty recall ≥ 0.90 | 0.736: fails | 0.708: fails |
| Over-hedging ≤ 10% | 7.4%: passes | 10.03%: fails |
| **Readiness** | **not eligible** | **not eligible** |

## 3. Over-claim gates (contexts; rate; context-bootstrap 95% upper bound)

These gates are benchmark criteria, not bounds on the model's underlying error probability (frozen §8).

| Gate | A | B |
|---|---|---|
| False progress | 0/125; 0.0%: passes | 3/125; 2.4% (5.6%): fails |
| Unsupported causal claim | 16/169; 9.5% (14.2%): fails | 10/169; 5.9% (9.5%): fails |
| Unsupported usefulness claim | 5/115; 4.3% (8.7%): fails | 0/115; 0.0%: passes |
| False subgoal success | 4/120; 3.3% (6.7%): fails | 5/120; 4.2% (8.3%): fails |
| False "no progress" | 38/180; 21.1% (26.7%): fails | 76/180; 42.2% (49.4%): fails |

## 4. Accuracy by family (correct in both passes)

The criterion is ≥ 0.90 overall and where the best shortcut is wrong.

| Level | Family | A | B |
|---|---|---|---|
| Observed change | `visual_effect` | 1.000: met | 1.000: met |
| | `region_changed` | 0.658: below floor | 0.683: below floor |
| Confirmed progress | `progress_status` | 1.000: met | 0.983: met |
| | `claim_progress` | 0.870: inconclusive | 0.752: inconclusive |
| Hypothesized usefulness | `claim_usefulness` (gate only) | 0.958 | 1.000 |
| Causal restraint | `claim_causal` | 0.508: below floor | 0.525: below floor |
| | `effect_hypothesis` | 0.350: below floor | 0.350: below floor |
| Subgoal verification | `subgoal_status` | 0.333: below floor | 0.344: below floor |
| | `subgoal_decision` | 0.317: below floor | 0.233: below floor |

Subgoal success detection: 0.333 (A) and 0.344 (B). Abandonment after disconfirmation is a reported secondary
measure (30 questions): 0.500 (A) and 0.567 (B).

## 5. Safeguard effect, B vs A (paired, descriptive)

Differences are in both-pass accuracy, with context-bootstrap 95% intervals:
- `claim_progress`: −0.117 [−0.162, −0.076]; 8 contexts improved, 45 regressed.
- `subgoal_decision`: −0.083 [−0.150, −0.025]; 3 improved, 13 regressed.
- `claim_usefulness`: +0.042 [+0.008, +0.081]; 5 improved, 0 regressed.
- `claim_causal`: +0.017 [0.000, +0.043].
- Every other family's interval includes 0.

## 6. Reading

- **The hypothesis is not supported as a whole.** The safeguard removed unsupported usefulness claims (5 to 0) and
  reduced unsupported causal claims (16 to 10). It also:
  - doubled false "no progress" assertions (38 to 76 of 180 contexts);
  - introduced false progress claims (0 to 3);
  - pushed over-hedging just past its cap;
  - lowered accuracy on `claim_progress` and `subgoal_decision`.
  Its net effect is a shift toward conservative answers, not a selective correction.
- **Shared weaknesses** in both arms:
  - subgoal verification, about one third correct;
  - causal restraint (`effect_hypothesis` 0.35, `claim_causal` about 0.5);
  - recall on uncertain-keyed questions (about 0.72);
  - `region_changed`.
- **Shared strengths:**
  - perfectly valid structured output;
  - reading observed change (`visual_effect` 1.0);
  - confirmed progress status (≥ 0.98);
  - in A, no false progress claims.
- **Scope:**
  - the results speak only to newly withheld instances from the synthetic generator (frozen §1);
  - this is one attempt on one model artifact, whose weights were not shown identical to the earlier Kaggle Model
    attachment;
  - the seed was retained under the owner's amended single-holder rule, with two copies on one computer.

## 7. Records

- Private, account-only:
  - the retained evidence (evidence-manifest SHA-256 `2e751b73…`);
  - the independent evaluation output (SHA-256 `64eface2…`);
  - the approvals and the launch, collection and watch records.
- The attempt is consumed and preserved. Any further run needs a new compute authorization.
