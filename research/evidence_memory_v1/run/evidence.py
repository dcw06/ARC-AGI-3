"""Run evidence for the Stage 1 run: WS3's module (v2's append-only call log plus committed-state recovery), unchanged.

A recovered (interrupted) run is always incomplete and never carries a promotable verdict; see
research/ws3_questionnaire_v1/evidence.py for the recovery rules.
"""
from research.ws3_questionnaire_v1.evidence import (  # noqa: F401  (re-exported, unchanged)
    CALLS, INTERRUPTED_TEMPORARY, MANIFEST, VERSION, EvidenceError, RunEvidence, StorageExhausted, atomic_write,
    encode, forge, load_committed, load_unverified_calls, load_verified, truncate)
