# Phase 0 transport and Phase 0F validator revalidation

Date: 2026-09-13

## Differential client fixture

`tests/test_phase0_transport_equivalence.py` executes the unmodified remote
wrapper from the public PyPI arc-agi 0.9.8 distribution. Its checked-in source
hash is `ebe8fd0a5ab2d5f65600f072fb22cf1de21c347a55b8c5ef569d6d7305c520e5`,
exactly the existing Kaggle mounted-profile hash. The common base wrapper hash
is `deaf07a628fb2e0f743366de4967110d4c06bafa21c5b61561d9ca02f31055ee`;
the downloaded 0.9.8 and installed 0.9.9 base wrapper bytes are identical.
The vendored fixture retains the wheel metadata's MIT copyright and license.

This is a local replay of the pinned mounted-client source using local pinned
dependencies, not a newly executed Kaggle runtime certification. No live key,
private game, scored submission, or network transport is used by the fixture.

Only Requests' HTTP adapter `send` is substituted. Both clients use real session
request preparation, JSON/body encoding, headers and cookie extraction. The
fixture compares initial constructor RESET, two isolated clients, interleaved
ACTION6 coordinates/reasoning, ordinary actions, affinity propagation,
converted temporal frames, identity binding and last-response state. Wire bodies
and relevant headers must agree byte-for-byte. Synthetic response facts are
deliberately named as fixtures, not captured game observations.

Post-entry connection/read failures, HTTP errors, redirects, malformed JSON,
conversion failures and wrong GUIDs preserve the last acknowledged observation,
record outcome_unknown, and prohibit further actions. Ambiguous open/bootstrap/
close cannot be retried. Bootstrap game-identity mismatch prohibits repair make.
These are intentional safety differences from the upstream wrapper, which
returns None on failures without providing our terminal quarantine contract.

Pre-entry action serialization failures do not call the session or quarantine.
The conservative ambiguity boundary is entry to Session.post, not the first
socket byte: even a later Session.prepare_request exception is quarantined.
The fixture explicitly tests this distinction rather than claiming knowledge
of whether a server executed an action. The independent real local REST gateway
remains the scorecard, authentication/affinity and scorer-semantics complement.

`scripts/validate_phase0.py` now requires this differential/fault suite, so the
gate can no longer pass on the old URL/payload and gateway coverage alone.

## Durable M0 completion

`scripts/validate_phase0f.py` now checks the registered M0 selection, completed
model manifest and frozen candidate set independently of current_phase. Existing
profile/hash/resource checks are unchanged. Regression tests confirm later
phases remain valid, while missing selection, pending model status or an
unfrozen candidate set still fail.

No production adapter, diagnostic source lock, E1 policy, or running notebook
was changed. This closes the two identified local validation/coverage gaps;
it does not close the remaining Phase 2 evidence and accounting findings.
