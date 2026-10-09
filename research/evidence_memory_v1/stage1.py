"""Stage 1 frozen question set, requests and request enumeration (Track 2, protocol v2). No model is called.

A session's frozen set (`build`) holds:
- contexts: one rendered evidence block per (trajectory, arm), under the common token budget of the pinned
  tokenizer (full history is the unbudgeted diagnostic reference);
- probes: one per (trajectory, arm, scheduled question), carrying the question shown to the model and, for the
  independent scorer only, the full-history truth, the package-relative truth and a key answer;
- schedule: pass 1 holds every probe, ordered by group (all horizons, arms and questions of a group together,
  families interleaved), so a truncated session keeps complete, family-balanced groups; pass 2 repeats the
  preselected whole groups of this session (response stability, not independent samples).

The run stack's phase names are fixed (`withheld_pass_1`, `withheld_pass_2`), so every probe carries
partition `withheld`; `case_source` says where the cases came from. Only `withheld` cases from the committed seed may
ever reach a live run; the committed `run/probes.json` is a `development_stand_in` for CPU rehearsal.

`enumerate_requests()` yields every Stage 1 request of both sessions (all arms including full history, every
scheduled question including recent controls, and the repeat), with the pure-Python token count, for the
cross-check against the pinned `transformers` tokenizer.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random

from research.evidence_memory_v1 import fidelity as F, protocol as P, tokens as TK, trajectories as TR, writers as W

VERSION = 'evidence_memory_v1_stage1'
MODEL = 'Qwen/Qwen3-VL-30B-A3B-Instruct-FP8'
GROUPS_PER_FAMILY = 12
SESSIONS = {'A': tuple(range(0, 6)), 'B': tuple(range(6, 12))}
REPEAT_GROUPS = 9  # ceil(10% of 84 groups); one per family, then two more
ARM_ORDER = P.ARMS + (P.REFERENCE,)
CASE_SOURCES = ('development_stand_in', 'withheld')
RUN_PROBES = Path(__file__).with_name('run') / 'probes.json'
RECALL_VALUES = P.VALUES + ('no_evidence',)


def response_schema(kind):
    """The decoding schema sent with each request. The recall schema has no `uniqueItems`: vLLM 0.19's structured-output
    backends refuse it (protocol v2 frozen, section 2). Scoring is unchanged: readers.validate_response still rejects
    duplicate values and "no_evidence" with another value, so such an answer stays invalid."""
    if kind == 'recall':
        return {'type': 'object', 'additionalProperties': False, 'required': ['values'],
                'properties': {'values': {'type': 'array', 'minItems': 1,
                                          'items': {'type': 'string', 'enum': list(RECALL_VALUES)}}}}
    action = {'type': 'object', 'additionalProperties': False, 'required': ['action_id', 'action_data'],
              'properties': {'action_id': {'type': 'integer'},
                             'action_data': {'type': 'object', 'additionalProperties': {'type': 'integer'}}}}
    return {'type': 'object', 'additionalProperties': False, 'required': ['choice'], 'properties': {'choice': action}}


def build_request(context, probe):
    """The request for one probe: the protocol's prompt frame over the context's evidence block."""
    return {'model': MODEL, 'messages': P.reader_messages(context['evidence'], probe['question']),
            'temperature': 0, 'seed': 0, 'max_tokens': P.MAX_TOKENS, 'chat_template_kwargs': {'enable_thinking': False},
            'response_format': {'type': 'json_schema', 'json_schema': {
                'name': f"{VERSION}_{probe['kind']}", 'strict': True, 'schema': response_schema(probe['kind'])}}}


def repeat_groups(seed):
    """The preselected repeat: whole groups, one in every family, then two more, drawn from the seed."""
    rng = random.Random(hashlib.sha256(f'{seed}/repeat'.encode()).hexdigest())
    chosen = [(family, rng.randrange(GROUPS_PER_FAMILY)) for family in TR.FAMILIES]
    rest = [(f, g) for f in TR.FAMILIES for g in range(GROUPS_PER_FAMILY) if (f, g) not in chosen]
    chosen += rng.sample(rest, REPEAT_GROUPS - len(chosen))
    return sorted(chosen, key=lambda fg: (fg[1], list(TR.FAMILIES).index(fg[0])))


def key_answer(probe_kind, truth):
    return {'values': truth} if probe_kind == 'recall' else {'choice': truth[0]}


def build(session, seed=TR.SEED, partition=TR.PARTITION, case_source='development_stand_in', tokenizer=None):
    if session not in SESSIONS or case_source not in CASE_SOURCES:
        raise ValueError('session or case source')
    tokenizer = tokenizer or TK.Tokenizer()
    measure = lambda text: len(tokenizer.encode(text))
    repeat = [fg for fg in repeat_groups(seed) if fg[1] in SESSIONS[session]]
    contexts, probes, pass_2 = [], [], []
    for group in SESSIONS[session]:
        for family in TR.FAMILIES:  # families interleaved within a group index
            ids = []
            for delay in P.HORIZONS:
                t = TR.build(family, group, delay, seed=seed, partition=partition)
                t['group'] = group
                memory = W.run_writer(W.Faithful(), t)['memory']
                _, contents = P.arm_contents(t, memory, measure)
                questions = P.questions(t)
                for arm in ARM_ORDER:
                    text, content = contents[arm]
                    context_id = f"{t['id']}/{arm}"
                    contexts.append({'context_id': context_id, 'evidence': text})
                    for n, q in enumerate(questions):
                        truth = F.gold(t['records'], q)
                        probe = {'probe_id': f'{context_id}/q{n}', 'context_id': context_id, 'partition': 'withheld',
                                 'family': family, 'group': group, 'delay': delay, 'trajectory': t['id'],
                                 'question_index': n, 'arm': arm, 'kind': q['kind'], 'control': q['control'],
                                 'evidence': P.evidence_class(t['records'], q), 'question': q, 'truth': truth,
                                 'package': P.package_truth(arm, content, q), 'key': key_answer(q['kind'], truth)}
                        probes.append(probe)
                        ids.append(probe['probe_id'])
            if (family, group) in repeat:
                pass_2 += ids
    return {'version': VERSION, 'session': session, 'case_source': case_source,
            'seed_sha256': hashlib.sha256(seed.encode()).hexdigest(), 'groups': list(SESSIONS[session]),
            'repeat_groups': [list(fg) for fg in repeat], 'window': P.RD.WINDOW, 'horizons': list(P.HORIZONS),
            'model': MODEL, 'contexts': contexts, 'probes': probes,
            'schedule': [{'partition': 'withheld', 'pass': 'pass_1', 'probe_ids': [p['probe_id'] for p in probes]},
                         {'partition': 'withheld', 'pass': 'pass_2', 'probe_ids': pass_2}]}


def encode(frozen):
    return (json.dumps(frozen, sort_keys=True, separators=(',', ':')) + '\n').encode()


def enumerate_requests(seed=TR.SEED, partition=TR.PARTITION, case_source='development_stand_in', sessions=('A', 'B'),
                       tokenizer=None):
    """Every Stage 1 request: both sessions, both passes, all arms (full history included), every scheduled question
    (recent controls included). Yields {'session', 'pass_id', 'probe_id', 'arm', 'request', 'pure_python_prompt_tokens'}."""
    tokenizer = tokenizer or TK.Tokenizer()
    for session in sessions:
        frozen = build(session, seed, partition, case_source, tokenizer)
        contexts = {c['context_id']: c for c in frozen['contexts']}
        probes = {p['probe_id']: p for p in frozen['probes']}
        for block in frozen['schedule']:
            for probe_id in block['probe_ids']:
                probe = probes[probe_id]
                request = build_request(contexts[probe['context_id']], probe)
                yield {'session': session, 'pass_id': block['pass'], 'probe_id': probe_id, 'arm': probe['arm'],
                       'request': request, 'pure_python_prompt_tokens': tokenizer.chat_prompt_tokens(request['messages'])}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', choices=sorted(SESSIONS), default='A')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    raw = encode(build(args.session))
    if args.check:
        if RUN_PROBES.read_bytes() != raw:
            raise SystemExit('the committed development stand-in differs from a fresh build')
        print('probes match:', hashlib.sha256(raw).hexdigest())
    else:
        RUN_PROBES.parent.mkdir(exist_ok=True)
        RUN_PROBES.write_bytes(raw)
        print('wrote', RUN_PROBES, hashlib.sha256(raw).hexdigest(), len(raw))
