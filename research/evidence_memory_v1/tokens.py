"""Offline prompt-token counts with the repository's pinned tokenizer, in pure Python (Track 2, evidence_memory_v1).

The pinned tokenizer is Qwen/Qwen3-VL-30B-A3B-Instruct-FP8 at revision d9748a51 (`.cache/phase4-tokenizer`, the
files `scripts/audit_ws3_questionnaire_tokens.py` loads with `transformers`). This environment has no `transformers`
or `tokenizers`, so this module reimplements the parts of that tokenizer that the Stage 1 prompts use:
- NFC normalisation (the identity on ASCII);
- the Split pre-tokenizer regex, specialised to ASCII (\\p{L} = [A-Za-z], \\p{N} = [0-9]);
- byte-level BPE with the pinned vocabulary and merge ranks;
- the added special tokens, extracted before pre-tokenization;
- the chat template for string-only system and user messages with add_generation_prompt.

Scope is enforced, never assumed: text outside printable ASCII plus tab, newline and carriage return, or containing
'<|' inside message content, is refused (ValueError), and so are the tokenizer files unless their SHA-256 equals the
pinned download record. `verify_against_ws3_audit()` checks the whole reimplementation against the committed exact
audit made with `transformers` (reports/ws3_questionnaire_token_audit.json): every prompt and key-completion count.
"""
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
PINNED = {'tokenizer.json': 'ba85e4e5222d9f53d4bd00b303ef7e9743c8ac3d07e3c23f8498dbe17baa9a2d',
          'vocab.json': '7a0cfa95c65792d7510205839f80cfd8a3c8f6b1fdad5132d95cee481800374d',
          'merges.txt': '8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5',
          'chat_template.json': '2c1437f11fc16ab501b984c000f6e291c599f0d28d2c9c6bf2c4533e65429b42'}
PRETOKENIZE = re.compile(r"(?i:'s|'t|'re|'ve|'m|'ll|'d)|[^\r\nA-Za-z0-9]?[A-Za-z]+|[0-9]| ?[^\sA-Za-z0-9]+[\r\n]*"
                         r"|\s*[\r\n]+|\s+(?!\S)|\s+")
ALLOWED = set(range(0x20, 0x7f)) | {0x09, 0x0a, 0x0d}


def candidates():
    """Where the pinned tokenizer may live: $EVIDENCE_MEMORY_TOKENIZER, this checkout, or the main checkout that
    holds this worktree."""
    env = os.environ.get('EVIDENCE_MEMORY_TOKENIZER')
    found = [Path(env)] if env else []
    found += [ROOT / '.cache/phase4-tokenizer']
    if ROOT.parent.name == 'worktrees' and ROOT.parent.parent.name == '.claude':
        found.append(ROOT.parents[2] / '.cache/phase4-tokenizer')
    return found


def locate():
    for path in candidates():
        if all((path / name).is_file() for name in PINNED):
            return path
    return None


def _bytes_to_unicode():
    keep = list(range(ord('!'), ord('~') + 1)) + list(range(ord('\xa1'), ord('\xac') + 1)) + \
        list(range(ord('\xae'), ord('\xff') + 1))
    codes, n = keep[:], 0
    for b in range(256):
        if b not in keep:
            keep.append(b)
            codes.append(256 + n)
            n += 1
    return {b: chr(c) for b, c in zip(keep, codes)}


class Tokenizer:
    def __init__(self, path=None):
        path = Path(path) if path else locate()
        if path is None:
            raise FileNotFoundError('the pinned tokenizer files were not found: ' + ', '.join(map(str, candidates())))
        for name, digest in PINNED.items():
            if hashlib.sha256((path / name).read_bytes()).hexdigest() != digest:
                raise ValueError(f'{name} does not match the pinned tokenizer')
        self.path = path
        self.vocab = json.loads((path / 'vocab.json').read_text(encoding='utf-8'))
        merges = [line for line in (path / 'merges.txt').read_text(encoding='utf-8').split('\n')
                  if line and not line.startswith('#version')]
        self.ranks = {tuple(line.split(' ')): rank for rank, line in enumerate(merges)}
        added = json.loads((path / 'tokenizer.json').read_text(encoding='utf-8'))['added_tokens']
        self.special = {a['content']: a['id'] for a in added}
        self.split_special = re.compile('(' + '|'.join(re.escape(s) for s in sorted(self.special, key=len, reverse=True)) + ')')
        self.byte_char = _bytes_to_unicode()
        self.cache = {}

    def _bpe(self, piece):
        if piece in self.cache:
            return self.cache[piece]
        word = [self.byte_char[b] for b in piece.encode('utf-8')]
        while len(word) > 1:
            pairs = [(self.ranks.get((a, b)), i) for i, (a, b) in enumerate(zip(word, word[1:]))]
            pairs = [p for p in pairs if p[0] is not None]
            if not pairs:
                break
            rank = min(p[0] for p in pairs)
            out, i = [], 0
            while i < len(word):
                if i < len(word) - 1 and self.ranks.get((word[i], word[i + 1])) == rank:
                    out.append(word[i] + word[i + 1])
                    i += 2
                else:
                    out.append(word[i])
                    i += 1
            word = out
        ids = [self.vocab[token] for token in word]
        self.cache[piece] = ids
        return ids

    def encode(self, text):
        """Token ids of `text` (special tokens recognised), as tokenizer.encode(text, add_special_tokens=False)."""
        if not isinstance(text, str) or any(ord(c) not in ALLOWED for c in text):
            raise ValueError('only printable ASCII, tab, newline and carriage return are supported exactly')
        ids = []
        for part in self.split_special.split(text):
            if part in self.special:
                ids.append(self.special[part])
            elif part:
                for piece in PRETOKENIZE.findall(part):
                    ids += self._bpe(piece)
        return ids

    def chat_prompt_tokens(self, messages):
        """Prompt tokens of apply_chat_template(messages, add_generation_prompt=True) for string-only system and
        user messages (the system message, if any, first)."""
        text = []
        for n, message in enumerate(messages):
            if message['role'] not in ('system', 'user') or (message['role'] == 'system' and n) or \
                    not isinstance(message['content'], str) or '<|' in message['content']:
                raise ValueError('only string system (first) and user messages without special-token text')
            text.append(f"<|im_start|>{message['role']}\n{message['content']}<|im_end|>\n")
        return len(self.encode(''.join(text) + '<|im_start|>assistant\n'))


def verify_against_ws3_audit(tokenizer):
    """(checked, mismatches) against the exact transformers audit of the WS3 questionnaire prompts."""
    from research.transition_evidence_v1 import questionnaire as Q
    audit = {r['probe_id']: r for r in json.loads((ROOT / 'reports/ws3_questionnaire_token_audit.json')
                                                  .read_text(encoding='utf-8'))['requests']}
    built = Q.build()
    checked, mismatches = 0, []
    for probe in built['probes']:
        row = audit[probe['probe_id']]
        request = Q.build_request(built['contexts'][probe['context_id']], probe)
        prompt = tokenizer.chat_prompt_tokens(request['messages'])
        key = len(tokenizer.encode(json.dumps({'answer': probe['key']}, separators=(',', ':')))) + 1
        checked += 1
        if (prompt, key) != (row['prompt_tokens'], row['key_completion_tokens']):
            mismatches.append({'probe_id': probe['probe_id'], 'prompt': [prompt, row['prompt_tokens']],
                               'key': [key, row['key_completion_tokens']]})
    return checked, mismatches
