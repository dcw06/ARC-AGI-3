"""The frozen Stage 1 question set, in the shape the reviewed supervised runner expects (hand-written adapter).

Runtime code reads the frozen file (research/evidence_memory_v1/stage1.py writes it) and builds each request with
stage1.build_request: the protocol's prompt frame, strict JSON schema and fixed decoding settings.

Rehearsal only: `EM1S_REHEARSAL_FROZEN` may name another frozen set (for example session B's development stand-in)
so a CPU rehearsal can run a second session through the same stack. It is honoured only under the rehearsal gate's
own conditions (`EM1S_REHEARSAL=1` and no visible GPU); otherwise its presence is refused. A live run reads only
the package's own probes.json, which the authority binds.
"""
import hashlib
import json
import os
from pathlib import Path

from research.evidence_memory_v1 import stage1 as _stage1
from research.evidence_memory_v1.trajectories import FAMILIES

FROZEN_PATH = Path(__file__).with_name('probes.json')
REHEARSAL_FROZEN_ENV = 'EM1S_REHEARSAL_FROZEN'
GATE_PARTITION = 'withheld'
PASSES = {'withheld': 2}  # pass 2 is the preselected repeat (whole groups), not a full second pass
MAX_TOKENS = {family: _stage1.P.MAX_TOKENS for family in FAMILIES}


def frozen_path():
    override = os.environ.get(REHEARSAL_FROZEN_ENV)
    if not override:
        return FROZEN_PATH
    if os.environ.get('EM1S_REHEARSAL') != '1' or os.environ.get('CUDA_VISIBLE_DEVICES', '') != '':
        raise PermissionError(f'{REHEARSAL_FROZEN_ENV} is honoured only in CPU rehearsal')
    return Path(override)


def load_frozen(path=None):
    raw = Path(path or frozen_path()).read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def build_request(context, probe):
    return _stage1.build_request(context, probe)
