"""The frozen Stage 1 question set, in the shape the reviewed supervised runner expects (hand-written adapter).

Runtime code reads the frozen file (research/evidence_memory_v1/stage1.py writes it) and builds each request with
stage1.build_request: the protocol's prompt frame, strict JSON schema and fixed decoding settings.
"""
import hashlib
import json
from pathlib import Path

from research.evidence_memory_v1 import stage1 as _stage1
from research.evidence_memory_v1.trajectories import FAMILIES

FROZEN_PATH = Path(__file__).with_name('probes.json')
GATE_PARTITION = 'withheld'
PASSES = {'withheld': 2}  # pass 2 is the preselected repeat (whole groups), not a full second pass
MAX_TOKENS = {family: _stage1.P.MAX_TOKENS for family in FAMILIES}


def load_frozen(path=FROZEN_PATH):
    raw = Path(path).read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def build_request(context, probe):
    return _stage1.build_request(context, probe)
