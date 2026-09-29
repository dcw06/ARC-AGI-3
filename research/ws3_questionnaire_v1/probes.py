"""The frozen WS3 transition questionnaire, in the shape the reviewed supervised runner expects.

Runtime code reads the frozen file (scripts/build_ws3_questionnaire_v1.py writes it) and builds each request from
the frozen context's evidence and the frozen question, with the questionnaire's system prompt, schema and fixed
decoding settings.
"""
import hashlib
import json
from pathlib import Path

from research.transition_evidence_v1 import questionnaire as Q

FROZEN_PATH = Path(__file__).with_name('probes.json')
GATE_PARTITION = 'withheld'
PASSES = {'withheld': 2, 'development': 1, 'transfer': 1}
MAX_TOKENS = {family: 32 for family in Q.FAMILIES}


def load_frozen(path=FROZEN_PATH):
    raw = Path(path).read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def build_request(context, probe):
    return Q.build_request(context['evidence'], probe)
