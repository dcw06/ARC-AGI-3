"""Owner gates (hand-written; import is inert): the two decisions that belong to the study owner.

`owner_gates.json` records them. While a decision is null the committed protocol v2 behaviour applies exactly: the
candidate's response schema is the adapter's, unchanged, and F5 is the running rate from the first dispatch. The
recommended option of each gate is implemented here so that, if the owner records it (an amendment with a new review
snapshot and a new compute authorization), no further code change is needed. This module never records a decision.

- free_text_format = 'ascii_only': the decoder may emit only printable ASCII without quote and backslash in
  `hypothesis` and `if_different`, at most 240 characters. xgrammar 0.1.34 drops `maxLength` when a `pattern` is
  present, so the bound is written inside the pattern ({0,240}) and `maxLength` is kept for other validators. The
  parsed block is checked again (a disallowed character makes the procedure block invalid, never the action).
- f5_early_abort = 'denominator_floor_10': F5 compares failures x 10 with max(dispatches so far, 10).
"""
import copy
import json
from pathlib import Path
import re

GATES = Path(__file__).with_name('owner_gates.json')
ASCII_PATTERN = '^[ !#-\\[\\]-~]{0,240}$'
ASCII_TEXT = re.compile(r'[ !#-\[\]-~]{0,240}')
FREE_TEXT = ('hypothesis', 'if_different')
DECISIONS = {'free_text_format': (None, 'current', 'ascii_only'),
             'f5_early_abort': (None, 'running_rate_from_first_dispatch', 'denominator_floor_10')}


def load(path=GATES):
    gates = json.loads(Path(path).read_bytes())
    if gates.get('schema') != 'feedback_action_v1_owner_gates_v1':
        raise ValueError('owner-gate record schema')
    for name, allowed in DECISIONS.items():
        entry = gates.get(name)
        if not isinstance(entry, dict) or entry.get('decision') not in allowed:
            raise ValueError('owner gate ' + name)
    return gates


def decision(name, gates=None):
    """The effective option: the recorded decision, or the committed behaviour while none is recorded."""
    gates = gates or load()
    entry = gates[name]
    return entry['decision'] if entry['decision'] is not None else entry['committed']


def ascii_only(gates=None):
    return decision('free_text_format', gates) == 'ascii_only'


def candidate_response_format(legal, gates=None):
    """The candidate's guided-decoding schema under the effective free-text option."""
    from research.feedback_action_v1 import adapter as AD
    value = AD.candidate_response_format(legal)
    if ascii_only(gates):
        properties = value['json_schema']['schema']['properties']['hypothesis_test']['properties']
        for name in FREE_TEXT:
            properties[name]['pattern'] = ASCII_PATTERN
    return value


def gate_request(request, gates=None):
    """A candidate request with the effective schema (the committed request is returned unchanged)."""
    from research.feedback_action_v1 import adapter as AD
    if not ascii_only(gates) or request['messages'][0]['content'] != AD.SYSTEM_PROMPT + '\n' + AD.PROCEDURE:
        return request
    value = copy.deepcopy(request)
    legal = json.loads(value['messages'][1]['content'])['observation']['legal_actions']
    value['response_format'] = candidate_response_format(legal, gates)
    return value


def free_text_problem(block, gates=None):
    """Why a parsed procedure block's free text is outside the effective option (None if it is inside)."""
    if not ascii_only(gates) or not isinstance(block, dict):
        return None
    for name in FREE_TEXT:
        if isinstance(block.get(name), str) and not ASCII_TEXT.fullmatch(block[name]):
            return f'{name}: outside the permitted printable-ASCII set'
    return None


def dispatch_denominator_floor(gates=None):
    return 10 if decision('f5_early_abort', gates) == 'denominator_floor_10' else 0


def apply(spec, gates=None):
    """The session spec with the effective F5 rule (unchanged while no decision is recorded)."""
    floor = dispatch_denominator_floor(gates)
    if floor:
        spec = copy.deepcopy(spec)
        spec['limits']['session_abort']['dispatch_denominator_floor'] = floor
    return spec
