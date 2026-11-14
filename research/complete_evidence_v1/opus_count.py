"""Opus token counts from the token-counting endpoint, with every request and answer kept.

The endpoint is free. Anthropic describes its counts as estimates: the number billed for a real message
can differ slightly. Each call is appended to a gzip JSON-lines log with the model ID, the exact request
payload and the returned count, so every reported number can be traced.
"""
import gzip
import hashlib
import json
import threading
import time
from pathlib import Path

import anthropic

ROOT = Path(__file__).resolve().parents[2]
MODEL = 'claude-opus-5-5'
DEFAULT_LOG = ROOT / 'reports/complete_evidence_phase1_v1/data/opus_token_count_log.jsonl.gz'


def api_key():
    for line in (ROOT / '.env').read_text().splitlines():
        if line.startswith('ANTHROPIC_API_KEY='):
            return line.split('=', 1)[1].strip().strip('"\'')
    raise SystemExit('no ANTHROPIC_API_KEY in .env')


class OpusCounter:
    def __init__(self, log_path=DEFAULT_LOG, model=MODEL):
        self.model, self.log_path, self.lock, self.seen = model, Path(log_path), threading.Lock(), {}
        self.client = anthropic.Anthropic(api_key=api_key(), max_retries=6)
        if self.log_path.exists():
            with gzip.open(self.log_path, 'rt') as handle:
                for line in handle:
                    entry = json.loads(line)
                    if entry['request']['model'] == model:
                        self.seen[entry['content_sha256']] = entry['input_tokens']

    def count(self, text, label=''):
        """Tokens for one user message holding `text`. A text already in the log is not sent again."""
        digest = hashlib.sha256(text.encode()).hexdigest()
        if digest in self.seen:
            return self.seen[digest]
        request = {'model': self.model, 'messages': [{'role': 'user', 'content': text}]}
        tokens = self.client.messages.count_tokens(**request).input_tokens
        entry = {'time': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'endpoint': 'POST /v1/messages/count_tokens',
                 'label': label, 'content_sha256': digest, 'request': request, 'input_tokens': tokens}
        with self.lock:
            with gzip.open(self.log_path, 'at') as handle:
                handle.write(json.dumps(entry) + '\n')
            self.seen[digest] = tokens
        return tokens
