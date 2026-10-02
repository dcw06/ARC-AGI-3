"""The progress_subgoal_v1 question set in the shape the reviewed supervised runner expects (hand-written adapter).

Shape (WS3 questionnaire v1 / evidence comprehension v2): `contexts` [{context_id, evidence}], `probes`, and
`schedule` blocks [{partition, pass, probe_ids}] in call order. The reviewed schedule names the decision partition
`withheld`, so the decision partition (the evaluation build at the freeze; the coverage dry run before it) is labelled
`withheld` here; probe and context ids keep their original partition prefix.

Nothing is frozen. Live mode reads only FROZEN_PATH (`probes.json`, written from the evaluation build at the freeze,
and bound by the review lock). Before the freeze, CPU rehearsals read a stand-in that `write_rehearsal_set` writes
from the dry run, named by PSV1_REHEARSAL_PROBE_SET; the override is honoured only with PSV1_REHEARSAL=1 and no
visible GPU, so it can never reach a live run.

`scheduled_requests` yields every scheduled request (messages and generation settings) for the exact token audit.
"""
import hashlib
import json
import os
from pathlib import Path

from research.progress_subgoal_v1 import questions as Q

FROZEN_PATH = Path(__file__).with_name('probes.json')
REHEARSAL_ENV = 'PSV1_REHEARSAL_PROBE_SET'
GATE_PARTITION = 'withheld'
PASSES = {'withheld': 2, 'development': 1}
MAX_TOKENS = {family: Q.MAX_TOKENS for family in Q.FAMILIES}
DECISION_STAND_IN = 'coverage_dryrun'


def runner_shape(decision, development):
    """One runner-shaped set from a decision-partition build and a development build (same arms)."""
    if decision['conditions'] != development['conditions']:
        raise ValueError('the decision and development builds must use the same arms')
    contexts, probes, schedule = [], [], []
    for value, label in ((decision, GATE_PARTITION), (development, 'development')):
        contexts += [{'context_id': cid, 'evidence': evidence} for cid, evidence in sorted(value['contexts'].items())]
        probes += [{**p, 'partition': label} for p in value['probes']]
        schedule += [{**block, 'partition': label} for block in value['schedule']]
    return {'version': Q.VERSION, 'conditions': decision['conditions'], 'system_prompts': decision['system_prompts'],
            'decision_source_partition': decision['partition'], 'contexts': contexts, 'probes': probes,
            'schedule': schedule}


def encode(frozen):
    return (json.dumps(frozen, sort_keys=True, separators=(',', ':')) + '\n').encode()


def rehearsal_set(conditions=Q.PRIMARY_CONDITIONS):
    """The pre-freeze stand-in: the decision-shaped dry run plus development. Never evaluation evidence."""
    return runner_shape(Q.build(DECISION_STAND_IN, conditions=conditions),
                        Q.build('development', conditions=conditions))


def write_rehearsal_set(path, conditions=Q.PRIMARY_CONDITIONS):
    raw = encode(rehearsal_set(conditions))
    Path(path).write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _path():
    override = os.environ.get(REHEARSAL_ENV)
    if override:
        if os.environ.get('PSV1_REHEARSAL') != '1' or os.environ.get('CUDA_VISIBLE_DEVICES', '') != '':
            raise PermissionError('a rehearsal probe set requires PSV1_REHEARSAL=1 and no visible GPU')
        return Path(override)
    return FROZEN_PATH


def load_frozen(path=None):
    raw = Path(path or _path()).read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def build_request(context, probe):
    return Q.make_request(context['evidence'], probe)


def scheduled_requests(frozen=None):
    """Every scheduled request, in call order, for the exact token audit.

    `frozen` is a runner-shaped set (default: the frozen file if it exists, otherwise the pre-freeze stand-in, i.e.
    `rehearsal_set()`). Yields one dict per scheduled call: index, phase, pass_id, probe_id, partition, condition,
    family, request_sha256, messages, chat_template_kwargs, max_tokens and the full request."""
    from research.action_effect_history_v1.service import request_hash
    if frozen is None:
        frozen = load_frozen()[0] if FROZEN_PATH.is_file() else rehearsal_set()
    contexts = {c['context_id']: c for c in frozen['contexts']}
    probes = {p['probe_id']: p for p in frozen['probes']}
    index = 0
    for block in frozen['schedule']:
        for probe_id in block['probe_ids']:
            probe = probes[probe_id]
            request = build_request(contexts[probe['context_id']], probe)
            yield {'index': index, 'phase': f"{block['partition']}_{block['pass']}", 'pass_id': block['pass'],
                   'probe_id': probe_id, 'partition': probe['partition'], 'condition': probe['condition'],
                   'family': probe['family'], 'request_sha256': request_hash(request),
                   'messages': request['messages'], 'chat_template_kwargs': request['chat_template_kwargs'],
                   'max_tokens': request['max_tokens'], 'request': request}
            index += 1
