# Conditional transfer applicability protocol

Frozen CPU development specification dated October 13, 2026. The exact prompts, enums, schemas and settings are in `review_package/protocol.json`; source and artifact hashes bind this revision. A specification freeze grants no execution authority. An amendment before model evaluation must be recorded, rebuilt and reviewed before a new evaluation seed is registered.

## Research question and scope

Can qualified knowledge be reused without deleting its uncertainty, coordinates, boundaries or later corrections? This is a supplied-evidence applicability task, not factual recall, prediction of hidden future outcomes, model-written memory, or game solving. `supported_local` means a matching acknowledged observation exists in the current context. It never means the rule is universal or its mechanic necessarily transfers elsewhere.

The earlier [frozen Track 2 protocol](https://github.com/dcw06/ARC-AGI-3/blob/e5b0830e7c7dddfad366fc52aabed35079a9f1a6/reports/evidence_memory_v1_protocol_v2_frozen.md) and the existing memory-stress report were read. Their source files, approvals and runtime are unchanged. Their authority does not apply to this study.

## Evidence and conditional knowledge

Record IDs use the shared `transition_evidence_v2` convention `episode_id#action_index`. Exact action IDs and integer arguments, including x and y, are retained. Failed and unknown dispatches remain distinct receipts with no observed visual effect. Intermediate returned frames establish `changed_then_returned` even when the final frame equals the original frame. The before-frame, before-level and segment define each trial's context; a boundary transition belongs to its old segment and subsequent trials to the new segment.

Frames are 4 by 4 integer grids. Three common observable annotations are explicitly supplied to every arm: mode, layout and appearance are the first three cells of row zero. They are observations, not hidden mechanics. A candidate's named preconditions may use a subset of them. No persistent-object identity or causal cell identity is asserted.

Each written rule contains rule ID, structured statement, support IDs, exact action, observable preconditions, scope, epistemic status, counterevidence IDs, revision history, applicability status and a complete observation ledger. The deterministic writer groups only identical action, full observable conditions, level and segment. Individual observations also retain exact state hashes. Every aggregated rule remains a hypothesis; repetition never promotes it into an observation. Support and contradiction remain in one atomic group. A later support does not erase a previous counterexample.

The existing faithful writer and independent fidelity evaluator run unchanged as an additional source-contract audit. The new audit checks every original observation and every qualified claim/revision. Independent answer keys rederive visual effects and boundaries from raw frames and receipts without importing the writer, reader or selection code.

## Six separate tasks and update policy

| Task | Answers | Decision rule |
| --- | --- | --- |
| Conditions | match, mismatch, unknown | Exact target action and all named preconditions match; missing observable values mean unknown |
| Target support | supported, contradicted, unobserved | Only qualified observations in the exact current state, level and segment decide; a counter takes priority |
| Contradiction | present, not_observed | Differing acknowledged effects in original scope or qualified current context count |
| Transfer | supported_local, unestablished, not_applicable, contradicted | Mismatch takes priority; missing conditions remain unestablished; otherwise a relevant counter wins, then current-context confirmation, otherwise unestablished |
| Evidence | records, no_evidence | Enumerate all qualified original-scope or current-context records, including unresolved receipts |
| Update | retain, narrow, retire | Counter inside original scope retires that proposal; only a counter outside its scope in the matching target narrows reuse; otherwise retain |

Retain preserves a hypothesis and its limits; it does not approve use in an unconfirmed target. Narrow preserves the original scoped evidence while refusing the proposed wider reuse. Retire retires the stated proposal, not every possible alternative hypothesis. These are declared benchmark policies, not claims that a single counter universally disproves a real stochastic mechanic.

Other tasks cite sufficient deciding evidence, not every redundant trial. Conditions and transfer cite the target observation. Support/counter tasks cite one appropriate deciding trial; unresolved target outcomes cite a failed/unknown receipt when one exists. Retain cites original support if available. Reference alternatives allow either of two redundant supports. Evidence enumeration requires each relevant record. Precision penalises irrelevant references; coverage measures required reference groups separately.

Responses must have exactly `answer` and `evidence_ids`. References must be distinct, visible, and at most eight. Duplicate JSON keys, extra fields, unresolved references, invalid enums, malformed or truncated JSON remain invalid. No repair, truncation, retries or output rewriting is allowed. The decoding schema omits `uniqueItems` following the older runtime's documented incompatibility; the scorer rejects duplicates. The six new schemas still require independent Linux target validation before a connected run.

## Source target pairs and split

Eight families cover layout, appearance, coordinates, state dependence, level/reset boundaries, contradiction, unknown dispatch and distracting history. Each has six development scenarios and delays of 0, 8 and 24 unrelated actions: 48 underlying clusters, 144 variants. Target support and counterexamples, when supplied, are already visible history, not withheld future effects.

Groups 0–5 use the public development seed. Evaluation groups 100–105 require a fresh private seed registered after design review. Categories use the within-partition ordinal so both partitions retain the same category/reset/dispatch/large-record coverage. No final evaluation set has been generated. Unit tests construct only disposable evaluation-shaped examples with a public test seed. They cannot become held-out evaluation cases. All delays and questions from one scenario stay in its split and analysis cluster.

## Fair arms and selection

All three arms receive the same proposed rule, target observation, task, answer schema, model and decoding. Primary final prompt ceiling: 1,536 tokens. The 1,024-token construction stress comparison is secondary. Completion cap: 256 tokens. Equal-token means a shared maximum, with no padding. Token counts include both messages and the assistant generation prefix, using four SHA-256-verified pinned tokenizer assets.

Recent history ranks the last six raw records by recency. Retrieved evidence ranks current state/level first, then recency. Conditional memory ranks groups containing a current-state observation first, then current segment, then other groups, with recency as tie-breaker. Selection uses current context and source evidence only; it cannot read the task, answers, family or construction metadata. A common maximum over all six task prompts is used to select one evidence package per arm/scenario/ceiling. This measurement is task-independent budgeting, not task-aware ranking.

The existing `readers._fit` priority-prefix selector is reused, including stopping at the first oversized item. Changes are explicit: the ceiling covers the complete request rather than being defined by the recent evidence block, and memory groups are atomic qualified records. Full history and unbounded memory are diagnostics only. Question-aware retrieval is absent.

## Attribution and endpoints

Each probe retains full-source, full-store, selected-package and response verdicts. The existing memory-stress `diagnostics.attribution` is reused through a one-to-one task-category adapter, with new strict provenance scoring layered on it. Category loss and reference loss are separate flags. Writer integrity is independent of answer-changing writer loss. Writer, selection and reader faults may coexist. A package-correct reader can still be source-incorrect when its package omitted evidence.

Primary endpoints are transfer category accuracy, unsupported `supported_local` claims, and contradiction/update accuracy on counterexamples. Report supported reuse coverage, per-family accuracy, condition/coordinate fidelity, source-relative reference precision and coverage, validity, stage losses and cost separately. Invalid responses are incorrect, remain in denominators and count as risk in the unsupported safety endpoint. The older recall protocol used a different invalid-output convention; this study declares its own conservative safety convention.

Average delays within each scenario, then weight scenarios equally. Arm contrasts are paired. Evaluation intervals use 10,000 scenario bootstrap samples with seed 20261013. Repeated questions, delays, aliases and arms are not independent cases. The equal six scenarios per family give equal family weight. Descriptive development tables carry no inferential significance claim.

Frozen review thresholds: validity at least 98%; transfer accuracy at least 85% overall and 70% in each family; unsupported rate at most 5% with cluster interval upper bound at most 10%; contradiction/update accuracy at least 90%; supported reuse coverage at least 80%; reference precision at least 95% and coverage at least 90%. Thresholds are review criteria, not automatic authorization. Development results do not satisfy all reference criteria.

Eight declared shortcuts are scored on full source evidence. Report the strongest shortcut's wrong subset without excluding other cases. The strongest shortcut's high aggregate score cannot substitute for family coverage or safe transfer. One pass is planned, with no repeat/stability claim. Unlike older Track 2, exact duplicate requests share one call, retain all aliases and are never counted as independent replicates. Request order is SHA-256 of registered seed plus request digest.

## Workload and stop rules

Development has 5,184 dependent probes across two ceilings, deduplicated to 3,354 inert requests. Final evaluation planning uses 48 clusters, three delays, three arms and six tasks at the primary ceiling: 2,592 probes before deduplication. Its exact schedule must be measured after the new seed is registered; development request counts are not a final-call authorization.

The package also prepares six separately counted schema probes. Writer model calls are zero; construction performs 2,160 deterministic record updates. Token totals and caps are in `token_audit.json`. Linux installation, startup, GPU time and cleanup have not been measured or authorized; they must be added to a separately reviewed runtime and compute budget. No old connected runtime was copied.

Stop on any source/request/schema/tokenizer mismatch or cap violation. After 50 attempted calls per arm, stop if invalid responses exceed 2%. Preserve every request, attempted call, failure, partial response and negative result. Do not retry or exclude selectively. Any request for a model-written memory study or a behavioural pilot requires its own protocol, review and compute authorization.
