# V12 action-output contract review

V11 R3 retained 208 identical rejected responses selecting ACTION6 with empty action data. V12 introduces an explicit policy/prompt/decoding revision, `arc_action_v12`, derived from E1S-R. Historical frozen sources and results are preserved; the change is not represented as request-invariant or as a retrospective pass for v11.

## Contract

Each workload request contains a JSON-schema `response_format` built from its current observation's legal actions. Separate action branches allow ACTION6 only with required integer x/y coordinates between 0 and 63, and allow legal actions 1–5 and 7 only with empty action data. Extra object fields are forbidden. The new prompt shows both shapes and explains that example coordinates are illustrative, not a default action.

The existing parser/action validator remains in place. A new local response guard checks exact JSON field sets, legal action IDs, and exact Python integer types before any action can be dispatched. This is necessary because inspection/testing found that the historical `DisplayPoint` range checks permit fractional numeric values. The guard rejects floats (including 1.0), booleans, strings, missing coordinates, out-of-range coordinates and additional fields without coercion or repair. JSON Schema's mathematical integer semantics alone are not treated as sufficient local type validation.

The model service independently checks that the supplied schema matches the legal actions in the request. It does not silently fall back to unconstrained output or retry a rejected schema. The original policy/fallback flow and zero-policy-failure acceptance gate remain; the stronger response guard can still cause a failed pilot if generation violates the contract. Bounded policy diagnostics remain enabled and client/worker records identify the new contract explicitly.

The startup canary now performs one schema-constrained ACTION6 completion and validates its coordinates before starting the workload. Its completion ceiling changes from eight tokens for `OK` to 128 tokens for the action object. Workload completion limits, temperature, seed, model, tokenizer, context limit, client count and resource/deadline gates are unchanged. This additional canary shape must be reviewed as part of the protocol change.

## Serving compatibility and limits

The pinned [vLLM 0.19.0 structured-output documentation](https://docs.vllm.ai/en/v0.19.0/features/structured_outputs/) documents JSON-schema response constraints. Its [tagged chat-completion implementation](https://github.com/vllm-project/vllm/blob/v0.19.0/vllm/entrypoints/openai/chat_completion/protocol.py) maps the response format into structured-output sampling parameters. Local tests verify that our HTTP transport forwards the schema unchanged and does not retry HTTP/schema errors.

The actual pinned vLLM/grammar backend is not installed in the local development interpreter. GPU model generation, schema compilation under the target backend, and target latency remain unverified. The reviewed single startup canary will fail closed if that path is unsupported; documentation and JSON-schema validation are not substitutes for target evidence. Valid action syntax also does not guarantee a useful or winning click.

## Validation and packaging

39 Linux tests passed, covering all 127 nonempty legal-action subsets, valid coordinate boundaries, invalid response fixtures, stricter integer typing, unchanged generation settings, schema transport, model-side schema enforcement, diagnostics, bridge, staging, lifecycle deadlines and cleanup. The original malformed ACTION6 response remains rejected; no coordinates are synthesized.

The final full CPU-only integration, including the integer guard and contract metadata, passed 110 clients and 7,722 scripted requests in 126.776 seconds, with unchanged scripted actions and intentionally changed request hashes. It passed the 300-second local smoke gate; the historical 60-second resource comparison failed and is preserved as such. This is scripted-model evidence, not GPU or model-performance certification. The full evidence is archived in `evidence/phase4-v12-local-review.zip` (SHA-256 `a2f3add3e76eb9e4fb13b4c0c97a3ca7be2c1a12dbe826272e6a0dbb5b41c746`); the portable summary is `reports/phase4_v12_review_receipt.json`.

The v12 builder emits compact LZMA/base85 packaging directly and rejects a notebook at or above 900,000 bytes. The new review notebook remains GPU-disabled and its execution authority is closed. No source approval, GPU reservation or GPU launch is implied by this review.

Frozen review: `notebooks/phase4-lifecycle-v12-review-r1`, notebook size 493,893 bytes. Source-lock SHA-256: `c9123cab5b4409f4333bb01a4cda091a4f920e79fa70a30810375814e9b35542`. All bound source files and notebook artifacts were verified against this lock; historical v7-v11 bound sources and artifacts were also verified unchanged. This is a reviewed implementation snapshot pending user source approval, not a compute authorization.
