"""Exact token audit of every feedback-action v1 request form and of the longest allowed candidate response, under
both free-text options (no model calls; no GPU).

Two steps, in the two interpreters the live session uses:

    python -m research.feedback_action_v1.token_audit forms --out <forms.json>              (game side: real engine)
    <model python> -m research.feedback_action_v1.token_audit tokenize --forms <forms.json> \\
        --tokenizer <pinned tokenizer folder>                                              (model side: pinned stack)

`forms` builds every request form exactly as the live runner sends it, from the real offline development engine
(s5i5, ls20, sk48; seed 0) through the derived runner and the CPU fake server, for both sessions: the canary; per
game and arm the first and the largest steady-state request; for the candidate, the largest steady-state request
with the carried statement at its text caps, for each free-text option's worst text. `tokenize` refuses unless the
pinned stack (transformers 4.57.6, tokenizers 0.22.2, jinja2 3.1.6) and the pinned tokenizer files (verified
against certification/phase4_integrated_v2/tokenizer_manifest.json) are present, counts every form the way the
service admits it (`apply_chat_template(..., tokenize=True, add_generation_prompt=True, enable_thinking=False)`), and
counts the longest allowed candidate response against its 640-token cap. Where the pinned guided-decoding library
(xgrammar 0.1.34, the trusted model lock) is importable it also records what the decoder admits.

Free-text options (an owner decision; see research/feedback_action_v1/live/owner_gates.json):
- current: hypothesis and if_different are JSON strings with maxLength 240. Under vLLM 0.19's default xgrammar
  backend (json_schema, any_whitespace=True) the decoder admits any code point except quote, backslash, CR and LF,
  never an escape, at most 240 code points.
- ascii_only: printable ASCII without quote and backslash, at most 240 characters ({0,240} inside the pattern).
"""
import argparse
import copy
import hashlib
import itertools
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).with_name('token_audit.json')
PINNED = {'transformers': '4.57.6', 'tokenizers': '0.22.2', 'jinja2': '3.1.6'}
PROMPT_CEILING, CONTEXT = 60000, 65536
CAPS = {'baseline': 128, 'candidate': 640}
# Worst free text per option, found by the search in `worst_text` (the byte-fallback bound for 'current': a
# supplementary-plane code point is 4 byte-level tokens; for 'ascii_only' a digit is one token).
WORST_TEXT = {'current': '\U0010FAA4' * 240, 'ascii_only': '9' * 240}
# The previous audit's carried-statement probes, kept for continuity of the forms.
PROBE_TEXT = {'ascii_letters': 'W' * 240, 'mixed_non_ascii': 'é中\U0001f600' * 80}
FORMATS = {'compact': {'separators': (',', ':')}, 'json_default': {}, 'indent2': {'indent': 2},
           'indent4': {'indent': 4}}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def worst_statement(text):
    from research.feedback_action_v1 import adapter as AD
    block = {'hypothesis': text[:AD.TEXT_LIMIT], 'status': 'revised', 'supporting': [], 'conflicting': [],
             'prediction': {'visual_effect': 'changed_then_returned', 'level_completed': False,
                            'changed_region_xyxy': [63, 63, 63, 63]},
             'if_different': text[:AD.TEXT_LIMIT]}
    return AD.carried_statement({'procedure': block}, ['none_reported'], 'T23')


def forms():
    """[(label, game_id, arm, request)] for every request form, from the real offline engine, both sessions."""
    from research.grounded_action_v1.engine import restore_game_mount
    from research.feedback_action_v1 import adapter as AD
    from research.feedback_action_v1.live import runner as R
    from research.feedback_action_v1.live.engine import DevelopmentAdapter
    from research.feedback_action_v1.live.fake_server import FakeServer
    from research.feedback_action_v1.live.policy import session_spec, validate_policy_request
    from research.feedback_action_v1.live.service import canary_request
    rows = [('canary', None, None, canary_request())]
    seen = {}
    with tempfile.TemporaryDirectory() as tmp:
        games = restore_game_mount(Path(tmp) / 'games')
        for session in (1, 2):
            report = R.run(Path(tmp) / f'run{session}', FakeServer(), lambda g, a, e: DevelopmentAdapter(
                g, a, e, games, Path(tmp) / f'rec{session}'), spec=session_spec(session))
            if report['status'] != 'complete':
                raise RuntimeError('form generation run did not complete: ' + str(report['status']))
            for episode in report['episodes']:
                requests = [c['request'] for c in episode['calls']]
                for request in requests:
                    validate_policy_request(request)
                key = (episode['game_id'], episode['arm'])
                first, largest = seen.get(key, (None, None))
                steady = max(requests[1:], key=lambda r: len(canonical(r)))
                if first is None:
                    first = requests[0]
                elif canonical(first) != canonical(requests[0]):
                    raise RuntimeError('first requests differ between sessions: ' + str(key))
                if largest is None or len(canonical(steady)) > len(canonical(largest)):
                    largest = steady
                seen[key] = (first, largest)
    for (game, arm), (first, largest) in sorted(seen.items()):
        rows.append(('first', game, arm, first))
        rows.append(('steady_largest', game, arm, largest))
        if arm == 'candidate':
            user = json.loads(largest['messages'][1]['content'])
            for name, text in list(WORST_TEXT.items()) + list(PROBE_TEXT.items()):
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


def write_forms(path):
    rows = forms()
    Path(path).write_text(json.dumps([{'label': l, 'game_id': g, 'arm': a, 'request': r} for l, g, a, r in rows]),
                          encoding='utf-8')
    return describe(rows)


def pinned_versions():
    import importlib.metadata
    found = {}
    for name in PINNED:
        try:
            found[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            found[name] = None
    return found


def candidate_response(text, vis, claim, stat, lvl, ref='T23'):
    cite = {'ref': ref, 'claim': claim}
    return {'hypothesis_test': {'hypothesis': text, 'status': stat, 'supporting': [cite] * 4,
                                'conflicting': [cite] * 4,
                                'prediction': {'visual_effect': vis, 'level_completed': lvl,
                                               'changed_region_xyxy': [63, 63, 63, 63]},
                                'if_different': text},
            'action': {'action_id': 6, 'action_data': {'x': 63, 'y': 63}}}


def longest_responses(count, text):
    """Per format: the enum choices maximizing the token count of the full candidate response with `text` in both
    free-text fields, eight citations of the latest possible ref (T23), the widest region and ACTION6 (63, 63)."""
    from research.feedback_action_v1 import adapter as AD
    out = {}
    for name, options in FORMATS.items():
        best = None
        for vis, claim, stat, lvl in itertools.product(AD.VISUAL_PREDICTIONS, AD.CLAIMS, AD.STATUSES, (True, False)):
            value = candidate_response(text, vis, claim, stat, lvl)
            serialized = json.dumps(value, ensure_ascii=False, **options)
            n = count(serialized)
            if best is None or n > best['content_tokens']:
                best = {'content_tokens': n, 'with_end_of_turn': n + 1, 'bytes': len(serialized.encode()),
                        'choices': {'visual_effect': vis, 'claim': claim, 'status': stat, 'level_completed': lvl}}
        best['fits_640'] = best['with_end_of_turn'] <= CAPS['candidate']
        best['byte_bound_fits_640'] = best['bytes'] + 1 <= CAPS['candidate']
        out[name] = best
    return out


def worst_text(count):
    """The adversarial free text per option, found by search (single code points and printable-ASCII pairs)."""
    ascii_chars = [chr(i) for i in range(32, 127) if chr(i) not in '"\\']
    pairs = max(((count((a + b) * 120), a + b) for a in ascii_chars for b in ascii_chars))
    singles = max((count(c * 240), c) for c in ascii_chars)
    points = [cp for cp in list(range(0x80, 0x3000, 7)) + list(range(0x3000, 0x10000, 97))
              + list(range(0x10000, 0x110000, 1531)) if not 0xD800 <= cp <= 0xDFFF]
    unicode_worst = max((count(chr(cp) * 240), cp) for cp in points)
    return {'ascii_only': {'single_char_240_tokens': singles[0], 'single_char': singles[1],
                           'pair_240_tokens': pairs[0], 'pair': pairs[1], 'bound': 240,
                           'note': 'every permitted character is one byte, so 240 tokens is an exact upper bound'},
            'current': {'code_points_searched': len(points), 'worst_240_tokens': unicode_worst[0],
                        'worst_code_point': f'U+{unicode_worst[1]:06X}', 'bound': 960,
                        'note': 'at most 4 UTF-8 bytes per code point, so 960 tokens is an exact upper bound'}}


def grammar_facts():
    """What the pinned decoder admits for the candidate schema (None when xgrammar is not importable here)."""
    try:
        import xgrammar
        from xgrammar.testing import _is_grammar_accept_string as accepts
    except ImportError:
        return None
    from research.feedback_action_v1 import adapter as AD
    from research.feedback_action_v1.live import owner_gates as G
    import importlib.metadata
    committed = AD.candidate_response_format([1, 2, 3, 4, 6, 7])['json_schema']['schema']
    gated = copy.deepcopy(committed)
    for name in G.FREE_TEXT:
        gated['properties']['hypothesis_test']['properties'][name]['pattern'] = G.ASCII_PATTERN
    unbounded = copy.deepcopy(gated)
    for name in G.FREE_TEXT:
        unbounded['properties']['hypothesis_test']['properties'][name]['pattern'] = '^[ !#-\\[\\]-~]*$'
    grammars = {k: xgrammar.Grammar.from_json_schema(json.dumps(v), any_whitespace=True)
                for k, v in (('current', committed), ('ascii_only', gated), ('pattern_without_bound', unbounded))}

    def response(h, ref='T3', n=1):
        v = candidate_response(h, 'no_observed_change', 'same_state_as_now', 'new', False, ref)
        v['hypothesis_test']['supporting'] = [{'ref': ref, 'claim': 'same_state_as_now'}] * n
        v['hypothesis_test']['conflicting'] = []
        return v
    compact = lambda v, ascii_=False: json.dumps(v, separators=(',', ':'), ensure_ascii=ascii_)
    checks = {
        'ascii_240': compact(response('a' * 240)), 'ascii_241': compact(response('a' * 241)),
        'astral_240': compact(response('\U0010FAA4' * 240)), 'astral_241': compact(response('\U0010FAA4' * 241)),
        'escaped_e_acute_1': compact(response('é'), True), 'escaped_quote_1': compact(response('"')),
        'escaped_backslash_1': compact(response('\\')), 'escaped_newline_1': compact(response('\n')),
        'raw_tab_in_text': compact(response('a\tb')).replace('\\t', '\t'),
        'ref_500_digits': compact(response('a', ref='T' + '0' * 500)),
        'whitespace_2000_after_brace': '{' + ' ' * 2000 + compact(response('a'))[1:],
        'five_supporting_citations': compact(response('a', n=5)),
    }
    return {'xgrammar_version': importlib.metadata.version('xgrammar'),
            'compile': 'Grammar.from_json_schema(schema, any_whitespace=True), as vLLM 0.19 compiles json_schema by '
                       'default (structured_outputs_config.disable_any_whitespace = False)',
            'accepts': {option: {label: accepts(g, s) for label, s in checks.items()}
                        for option, g in grammars.items()}}


def tokenize(forms_path, tokenizer_path, out=OUTPUT):
    versions = pinned_versions()
    if versions != PINNED:
        raise SystemExit(f'TODO(pinned tokenizer): exact counts need {PINNED}; this environment has {versions}. '
                         'No counts were produced.')
    from certification.phase4_integrated_v2.tokenizer_binding import verify
    from transformers import AutoTokenizer
    manifest = verify(tokenizer_path)  # the pinned files, by hash, before any count
    tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_path), local_files_only=True, trust_remote_code=False)
    count = lambda text: len(tokenizer.encode(text, add_special_tokens=False))
    rows = json.loads(Path(forms_path).read_bytes())
    described = describe([(r['label'], r['game_id'], r['arm'], r['request']) for r in rows])
    for row, item in zip(described, rows):
        request = item['request']
        ids = tokenizer.apply_chat_template(request['messages'], tokenize=True, add_generation_prompt=True,
                                            truncation=False, **request['chat_template_kwargs'])
        row['prompt_tokens'] = len(ids)
        row['context_with_cap'] = len(ids) + request['max_tokens']
        row['within_limits'] = len(ids) <= PROMPT_CEILING and len(ids) + request['max_tokens'] <= CONTEXT
    baseline = {'action': {'action_id': 6, 'action_data': {'x': 63, 'y': 63}}}
    completions = {
        'baseline': {name: {'content_tokens': count(json.dumps(baseline, **o)),
                            'with_end_of_turn': count(json.dumps(baseline, **o)) + 1,
                            'fits_128': count(json.dumps(baseline, **o)) + 1 <= CAPS['baseline']}
                     for name, o in FORMATS.items()},
        'candidate_structure_only': {k: {kk: v[kk] for kk in ('content_tokens', 'with_end_of_turn', 'bytes')}
                                     for k, v in longest_responses(count, '').items()},
        'candidate_by_free_text_option': {option: longest_responses(count, text) for option, text in WORST_TEXT.items()},
        'candidate_natural_ascii_reference': longest_responses(count, 'W' * 240)}
    prompts = {}
    for option, text in WORST_TEXT.items():
        rows_option = [r for r in described if r['label'] == f'steady_worst_carried_{option}']
        prompts[option] = {'largest_prompt_tokens': max(r['prompt_tokens'] for r in rows_option),
                           'all_within_limits': all(r['within_limits'] for r in rows_option)}
    audit = {
        'schema': 'feedback_action_v1_token_audit_v2', 'tokenizer_files': manifest['files'], 'versions': versions,
        'tokenizer_revision': manifest['revision'], 'forms': described,
        'max_prompt_tokens': max(r['prompt_tokens'] for r in described),
        'all_forms_within_limits': all(r['within_limits'] for r in described),
        'prompt_with_worst_carried_statement_by_option': prompts,
        'completion_caps': CAPS, 'completions': completions, 'worst_text_search': worst_text(count),
        'grammar': grammar_facts(),
        'findings': [
            'Prompt: every form, including the carried statement at its caps under either option, is far below the '
            '60,000-token ceiling and the 65,536 context.',
            'Under vLLM 0.19 defaults the decoder admits unbounded whitespace between JSON tokens and unbounded '
            'digits in a citation ref (pattern ^T[0-9]+$), in both arms and both options: no finite cap covers every '
            'response the grammar admits. A truncated response is an invalid output (protocol v2 section 5).',
            'xgrammar 0.1.34 drops maxLength when a pattern is present: the ascii_only option must carry its bound '
            'inside the pattern ({0,240}), as owner_gates.ASCII_PATTERN does.',
            'The counts above are canonical tokenizations. Guided decoding may also emit non-canonical token '
            'sequences; their only bound is the response byte length (bytes field).'],
        'counts_are': 'exact for the pinned tokenizer; the completion maxima are over the enumerated enum choices and '
                      'the searched worst text (exact per-character bounds stated in worst_text_search)'}
    Path(out).write_text(json.dumps(audit, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    return audit


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    f = sub.add_parser('forms')
    f.add_argument('--out', type=Path, required=True)
    t = sub.add_parser('tokenize')
    t.add_argument('--forms', type=Path, required=True)
    t.add_argument('--tokenizer', type=Path, default=ROOT / '.cache/phase4-tokenizer')
    t.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    if args.command == 'forms':
        print(json.dumps(write_forms(args.out), indent=1))
    else:
        audit = tokenize(args.forms, args.tokenizer, args.output)
        print(json.dumps({k: audit[k] for k in ('max_prompt_tokens', 'all_forms_within_limits',
                                                'prompt_with_worst_carried_statement_by_option')}, indent=1))
        print(json.dumps(audit['completions']['candidate_by_free_text_option'], indent=1))
