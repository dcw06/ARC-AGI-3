"""Exact token audit of every feedback-action v1 request form (no model calls).

TODO(pinned tokenizer): the exact counts require the pinned stack (transformers 4.57.6, tokenizers 0.22.2,
jinja2 3.1.6) and the pinned tokenizer files (.cache/phase4-tokenizer). The development environment used for this
track has none of them, so `tokenize` refuses to run there and nothing here reports a token count. The main session
runs it in its isolated pinned environment:

    python -m research.feedback_action_v1.token_audit tokenize --tokenizer <path to .cache/phase4-tokenizer>

`forms` (any environment) builds every request form exactly as the live runner sends it, from the real offline
development engine (s5i5, ls20, sk48; seed 0) through the derived runner and the CPU fake server, and records each
form's bytes and SHA-256. `tokenize` counts the same forms with the pinned tokenizer, the way the service admits a
request (`apply_chat_template(..., tokenize=True, add_generation_prompt=True, enable_thinking=False)`), and counts
the longest schema-valid completion of each arm against its cap.

Forms per game and arm: the first request (empty evidence; candidate: no carried statement), every steady-state
request of a 24-action episode (the largest is reported), and for the candidate a worst case with the carried
statement at its text caps in ASCII and in non-ASCII text (escaped by JSON, so more tokens per character). Plus
the startup canary.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).with_name('token_audit.json')
PINNED = {'transformers': '4.57.6', 'tokenizers': '0.22.2', 'jinja2': '3.1.6'}
PROMPT_CEILING, CONTEXT = 60000, 65536


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def worst_statement(text):
    from research.feedback_action_v1 import adapter as AD
    block = {'hypothesis': text[:AD.TEXT_LIMIT], 'status': 'revised', 'supporting': [], 'conflicting': [],
             'prediction': {'visual_effect': 'changed_then_returned', 'level_completed': False,
                            'changed_region_xyxy': [63, 63, 63, 63]},
             'if_different': text[:AD.TEXT_LIMIT]}
    return AD.carried_statement({'procedure': block}, ['none_reported'], 'T23')


WORST_TEXT = {'ascii': 'W' * 240, 'non_ascii': 'é中\U0001f600' * 80}


def longest_completions():
    """The longest schema-valid completion text of each arm (compact and pretty-printed JSON)."""
    from research.feedback_action_v1 import adapter as AD
    action = {'action_id': 6, 'action_data': {'x': 63, 'y': 63}}
    cite = {'ref': 'T23', 'claim': 'different_state_from_now'}
    out = {'baseline': [json.dumps({'action': action}, separators=(',', ':')),
                        json.dumps({'action': action}, indent=4)]}
    rows = []
    for name, text in WORST_TEXT.items():
        block = {'hypothesis': text[:AD.TEXT_LIMIT], 'status': 'retained', 'supporting': [cite] * AD.CITATION_LIMIT,
                 'conflicting': [cite] * AD.CITATION_LIMIT,
                 'prediction': {'visual_effect': 'changed_then_returned', 'level_completed': False,
                                'changed_region_xyxy': [63, 63, 63, 63]},
                 'if_different': text[:AD.TEXT_LIMIT]}
        value = {'hypothesis_test': block, 'action': action}
        for ascii_only in (False, True):  # raw UTF-8 or JSON-escaped text: count whichever is longer
            rows += [json.dumps(value, separators=(',', ':'), ensure_ascii=ascii_only),
                     json.dumps(value, indent=4, ensure_ascii=ascii_only)]
    out['candidate'] = rows
    return out


def forms():
    """[(label, game_id, arm, request)] for every request form, from the real offline engine."""
    from research.grounded_action_v1.engine import restore_game_mount
    from research.feedback_action_v1 import adapter as AD
    from research.feedback_action_v1.live import runner as R
    from research.feedback_action_v1.live.engine import DevelopmentAdapter
    from research.feedback_action_v1.live.fake_server import FakeServer
    from research.feedback_action_v1.live.policy import session_spec, validate_policy_request
    from research.feedback_action_v1.live.service import canary_request
    rows = [('canary', None, None, canary_request())]
    with tempfile.TemporaryDirectory() as tmp:
        games = restore_game_mount(Path(tmp) / 'games')
        report = R.run(Path(tmp) / 'run', FakeServer(), lambda g, a, e: DevelopmentAdapter(g, a, e, games,
                                                                                          Path(tmp) / 'rec'),
                       spec=session_spec(1))
    if report['status'] != 'complete':
        raise RuntimeError('form generation run did not complete: ' + str(report['status']))
    for episode in report['episodes']:
        requests = [c['request'] for c in episode['calls']]
        for request in requests:
            validate_policy_request(request)
        game, arm = episode['game_id'], episode['arm']
        rows.append(('first', game, arm, requests[0]))
        largest = max(requests[1:], key=lambda r: len(canonical(r)))
        rows.append(('steady_largest', game, arm, largest))
        if arm == 'candidate':
            user = json.loads(largest['messages'][1]['content'])
            for name, text in WORST_TEXT.items():
                variant = copy.deepcopy(largest)
                user[AD.PREVIOUS_FIELD] = worst_statement(text)
                variant['messages'][1]['content'] = json.dumps(user, sort_keys=True, separators=(',', ':'))
                validate_policy_request(variant)
                rows.append((f'steady_worst_carried_{name}', game, arm, variant))
    return rows


def describe(rows):
    return [{'label': label, 'game_id': game, 'arm': arm, 'request_sha256': hashlib.sha256(canonical(r).encode()).hexdigest(),
             'request_bytes': len(json.dumps(r, separators=(',', ':')).encode()), 'max_tokens': r['max_tokens'],
             'system_chars': len(r['messages'][0]['content']), 'user_chars': len(r['messages'][1]['content'])}
            for label, game, arm, r in rows]


def pinned_versions():
    import importlib.metadata
    found = {}
    for name in PINNED:
        try:
            found[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            found[name] = None
    return found


def tokenize(tokenizer_path):
    versions = pinned_versions()
    if versions != PINNED:
        raise SystemExit(f'TODO(pinned tokenizer): exact counts need {PINNED}; this environment has {versions}. '
                         'No counts were produced.')
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_path), local_files_only=True, trust_remote_code=False)
    rows = forms()
    described = describe(rows)
    for row, (_, _, _, request) in zip(described, rows):
        ids = tokenizer.apply_chat_template(request['messages'], tokenize=True, add_generation_prompt=True,
                                            truncation=False, **request['chat_template_kwargs'])
        row['prompt_tokens'] = len(ids)
        row['within_limits'] = len(ids) <= PROMPT_CEILING and len(ids) + request['max_tokens'] <= CONTEXT
    caps = {}
    for arm, texts in longest_completions().items():
        cap = 640 if arm == 'candidate' else 128
        longest = max(len(tokenizer.encode(t, add_special_tokens=False)) + 1 for t in texts)
        caps[arm] = {'longest_valid_completion_tokens': longest, 'max_tokens': cap, 'covers': longest <= cap}
    OUTPUT.write_text(json.dumps({'tokenizer': str(tokenizer_path), 'versions': versions, 'forms': described,
                                  'completion_caps': caps}, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({'forms': len(described), 'max_prompt_tokens': max(r['prompt_tokens'] for r in described),
                      'all_within_limits': all(r['within_limits'] for r in described), 'caps': caps}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('forms')
    t = sub.add_parser('tokenize')
    t.add_argument('--tokenizer', type=Path, default=ROOT / '.cache/phase4-tokenizer')
    args = parser.parse_args()
    if args.command == 'forms':
        print(json.dumps(describe(forms()), indent=1))
    else:
        tokenize(args.tokenizer)
