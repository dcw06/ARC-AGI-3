# Phase 1 control freeze and availability decision

Decision date: 2026-09-11 UTC
Provenance cutoff: 2026-09-10 23:59 UTC
Registry: `config/control_registry.yaml`, schema 2

Machine-readable audit evidence:
`reports/phase1_control_audit_2026-09-11.json`, SHA-256
`356d6bec08522dd2e80f4214d1919b50d845261bbb39f2849788be5281e6c114`.

## Outcome

The public inventory was rerun after the cutoff. The immutable September 9
snapshots remain the inputs to this historical decision; revisions first seen
after the cutoff are prospective and cannot change Phase 1.

| Role | Frozen record | Decision |
|---|---|---|
| Published workspace control | `duck-qwen3.8-flash-next-nvfp4-anim` | Snapshot frozen; faithful runner unavailable; production-ineligible |
| Published structured reference | `reki-milestone1` | Snapshot frozen; runner unavailable because the attached wheelhouse license is unknown |
| Eligible structured fallback | `e1s-r-project-structured-fallback` | Production-eligible project control; not a published reproduction |
| Workspace substitute | `e1c-f-safe-operations-duck-substitute` | Production-eligible adapted control; not faithful and not normalized Duck |

This closes the decision. “Unavailable” is a final fail-closed classification
for these captured bundles, not a pending presumption of permission.

## Published Duck evidence

The selected notebook is the pre-cutoff snapshot of
`wuliao0/duck-qwen3-8-anim-base`:

- notebook SHA-256: `72d6f35147b5d1c422a2959cc378727df6b688c4f478c2aa9ad3580b4a247122`;
- source manifest SHA-256: `330ddcbde7ae0663012050ab0fcf34bc035d5e698a169af6876fb9e5606b3408`;
- policy tree SHA-256: `ce01153b091d6ab5098751bacc072273058032a9453dcc18aa0c9d491a8bfdc2`;
- prompt surface SHA-256: `39113db786cfa220e569b85ff2f01fd5e977ca8ddf309aea58456cc79bb9e768`;
- Python runner SHA-256: `765e90cf8d141f912f6cfbba498426c9b0de9453e6e44c97d3bc8df45cf9aa91`;
- model manifest SHA-256: `a09bdad3fe3240c73332c0f99f4388a547205cb488c127f9b9059c9267dd9a5b`;
- runtime manifest SHA-256: `e9453f8d0e9c5eb2e14712e0f8563aaa96752ddc1705f245cac327537502baad`.

The downloaded source dataset and runtime dataset each report `unknown` in
their current Kaggle license metadata. The source tree has an MIT classifier
but no root license file; that classifier is not treated as a grant. The
RadixArk model revision delegates to the Qwen Community License 1.0 and labels
the derivative `other`. These facts make the captured distribution
production-ineligible independently of the Python boundary.

### Python isolation decision

The runner does launch `python -I -S` in a new process/session with a temporary
working directory, a small environment, an import/builtin allowlist, timeouts,
and selected POSIX resource limits. It still runs arbitrary model-authored code
with `exec`, without an enforceable filesystem jail, credential boundary,
native-code boundary, syscall/process policy, or a target-Kaggle adversarial
escape result. Section 8.12 explicitly rejects an AST/import filter or child
process alone as sufficient proof.

Therefore:

- full Duck Python is disabled in production;
- no faithful Duck reproduction will be launched with the captured runner;
- replacing Python with safe operations changes a policy capability and is
  classified as an adapted control;
- `E1C-F` is the implemented adapted substitute and may never inherit a
  published-reproduction label or published score.

## Published structured evidence

`reki-milestone1` is retained as the strongest frozen published structured
reference. The captured notebook used Gemma 4 31B, image observations,
structured JSON, reflection memory, and plans of up to four actions:

- notebook SHA-256: `3cb34c4a04140535081afa611159fc303ccd29481bd34a62e3bc6aa44bff0618`;
- code-cell surface SHA-256: `d2556ae3a75d2bb0e8f8f799191800861085725b951e703b640c37ff214eb25c`;
- prompt surface SHA-256: `052ad788d3704fa06c0e1786ad30a3d8f9a4e639309e60159394f6ae09dec8d3`;
- exact Gemma revision: `4797d2888d4e7a1450a92a7d426967eeca6f3d7e`;
- wheelhouse metadata SHA-256: `b43599a33be150cc2a26f32167d14f944877dd2a8622919a2829b22b1764e764`.

The public notebook and exact model are Apache-2.0. The required
`ruichardliu/vllm-0230-offline` dataset is public, but its Kaggle metadata says
`unknown`; the captured runner installs its full transitive vLLM wheel set from
that distribution. This fails the declared license-closure rule. Forge cannot
replace it because its required wheelhouse metadata endpoint returned HTTP 403,
so public availability itself was not established.

A future runner may become eligible by building a hash-pinned offline
wheelhouse from authoritative, license-closed upstream distributions. That
would be a recorded compatibility patch and would require a fresh packaging
and runtime validation. It does not retroactively make the captured bundle
eligible.

## Comparison consequences

Published scores remain inventory metadata and cannot be substituted for
project results. With both published runners unavailable, the completed v5
four-cell evidence supports only the project-owned `E1S-R` provisional
structured fallback and the explicitly adapted `E1C-F` safety substitute.
Neither result is a published reproduction. The frozen fallback-only decision
now selects E1S-R as the `Provisional primary`; this does not convert unavailable
published controls into reproductions or establish a superiority claim. A
rebuilt eligible runner would require a prospective control-registry version.
