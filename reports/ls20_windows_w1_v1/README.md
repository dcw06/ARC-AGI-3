# Windows W1 CPU checkpoint and Mac interface handoff

Date: 2026-10-25, America/Los_Angeles. Branch: `teammate/windows-rule-discovery`.
Base: the team's frozen `1ad910bcd3a541279c4a6f224cce15368bec74aa`.

## Delivered

The new [Windows module](../../research/ls20_discovery_windows/README.md) consumes
Mac M1 raw snapshots and generates generic, revisable appearance-effect candidates.
It records predictions before dispatch, preserves counterexamples, creates new
candidate scopes/outcomes after failures, explicitly retains an unknown explanation,
and exports a schema-validated W2/M2 handoff. A fixed-action immediate-commitment
comparison uses the same candidate generator. Mac code and shared production
contracts are unchanged.

This is an interface and W1 implementation checkpoint. Full movement/contact rule
discovery, object-conditioned inference, W2 probes/objectives, M2 execution models,
and real-game integration remain unfinished. The small candidate language only
predicts appearance categories; it does not identify the cause of a change.

## Validation

| Check | Result |
|---|---|
| New W1, schema, and retained replay tests | 36 passed, no skips |
| Team's frozen portable regression suite | 102 passed, no skips |
| Original Mac M1 suite, `c920f5d` | 26 passed, no skips |
| Fixed Mac M1 suite, `f4bf522` | 31 passed, no skips |
| Actual Mac M1 integration | Both pinned versions; 20 scripted attempts each |
| Retained raw observations, forecast/handoff schemas, and Mac disk restoration | Verified for both versions |

Python: native Windows 3.12.10. JSON Schema validation uses jsonschema 4.26.0.
Tests use synthetic observations, scripted callbacks, and local files. No model,
GPU, real game interaction, scored submission, or holdout access occurred.
The 40 archived attempts are constructed diagnostics, not independent samples.
Development reruns are separately counted in [validation.json](validation.json).

## Matched diagnostic result

Each arm makes the same ten scripted attempts in three evaluator-owned cases:
misleading initial evidence followed by a transient effect, action/context
confounding, and failed/unknown dispatch. Eight attempts per arm have an observed,
within-segment appearance outcome that can be scored; failures/unknowns are excluded
from accuracy and retained in the attempt count.

| Per pinned M1 version | Immediate commitment | Competing hypotheses |
|---|---:|---:|
| Attempts / scored observations | 10 / 8 | 10 / 8 |
| Single-label forecasts | 4 | 3 |
| Correct single-label forecasts | 2 | 2 |
| Incorrect single-label forecasts | 2 | 1 |
| Explicit disagreements | 0 | 1 |

The competition arm avoids one incorrect commitment by declining to select a
single outcome. It does not produce another correct forecast. Both arms are poor
predictors in these tiny constructed cases. The result verifies the intended
uncertainty behavior and exposes limited coverage; it does not establish better
rule learning, causal identification, held-out accuracy, or gameplay performance.

In `misleading_then_transient`, the initial no-change observation generates only
no-change candidates. The next forecast is wrong. Its retained counterexample
retires those candidates, and the observed intermediate change generates the
previously absent `transient_change` candidates. The third forecast correctly
predicts that category. This demonstrates revision within the declared primitive
language, not discovery of an executable game mechanic.

## Replayable evidence

- [Fixed M1 trace](trace_fixed.json) and [summary](summary_fixed.json).
- [Original M1 trace](trace_original.json) and [summary](summary_original.json).
- [Implemented output schema](../../research/ls20_discovery_windows/schema.json).
- [Source byte bindings](../../research/ls20_discovery_windows/m1_sources.json).

Each trace retains complete before/after M1 payloads, the sealed prospective
forecast, the dispatch result, scores, and final hypotheses for each condition.
Replay checks individual bindings, exact transition prefixes, cross-step snapshot
continuity, action identity, producer provenance, and reconstruction of forecasts
from before-only evidence. Summaries bind the exact archived trace bytes.

```sh
python scripts/demo_ls20_discovery_windows_w1.py --verify reports/ls20_windows_w1_v1/trace_fixed.json
python scripts/demo_ls20_discovery_windows_w1.py --verify reports/ls20_windows_w1_v1/trace_original.json
```

## 给 Mac 队友的对齐要点

1. Windows 现在有可运行的 W1 最小模块和 v1 schema，可以直接消费你现有的 M1 snapshot；无需先合并代码。
2. 请同时传完整 producer commit。原版与修复版使用同一个 M1 version 字符串，不能仅凭 version 选择重建算法。
3. 区域仍是观察局部候选；身份链接和角色提示不会被 Windows 提升为确定对象或规则。
4. 预测绑定 episode、segment、完整观察哈希、独立帧哈希和具体动作。结果未知时 handoff 明确标记 suspended，禁止继续预测。
5. 当前只返回外观变化候选与支持/反例。W2 的目标假设、目标格和 M2 可执行规则还没有实现，相关数组保持为空。
6. 下一步应先扩展对象关联条件下的位移/交互预测，再做 W2 的成本与分歧探测；不要把这次合成用例当作真实 ls20 解题证据。

The exact ls20 asset bundle, seed-0 initial observation and hash inventory still
need to be supplied before a real offline baseline can be certified. Native
Windows portable checks do not establish WSL/Linux runner readiness.
