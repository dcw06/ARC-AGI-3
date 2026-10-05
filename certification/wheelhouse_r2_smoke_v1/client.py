"""Counted HTTP requests to the model server and the frozen request cases. Every request passes the ledger first and
has a hard deadline: min(its own timeout, the admission cutoff)."""
import base64
import http.client
import json
import re
import struct
import time
import zlib

RESPONSE_CAP = 1024 * 1024


class RequestFailed(RuntimeError):
    pass


def png(width=64, height=64, square=(255, 0, 0), background=(255, 255, 255)):
    """A deterministic PNG: a centred coloured square on a plain background (stdlib only)."""
    rows = b''
    for y in range(height):
        row = b''.join(bytes(square if width // 4 <= x < 3 * width // 4 and height // 4 <= y < 3 * height // 4
                             else background) for x in range(width))
        rows += b'\x00' + row

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b''))


LONG_TEXT = '\n'.join(f'Line {i:03d}: the archive lists item {i} as present and unchanged.' for i in range(1, 121))
CASES = {
    'canary': {'messages': [{'role': 'user', 'content': 'Reply with the single word: ok'}], 'max_tokens': 16},
    'exact_word': {'messages': [{'role': 'user', 'content': 'Reply with exactly the word READY and nothing else.'}],
                   'max_tokens': 8},
    'long_context': {'messages': [{'role': 'user', 'content': LONG_TEXT + '\n\nHow many numbered lines are above? '
                                   'Answer with a number only.'}], 'max_tokens': 16},
    'image': {'messages': [{'role': 'user', 'content': [
        {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(png()).decode()}},
        {'type': 'text', 'text': 'What colour is the square in the middle? Answer with one word.'}]}],
        'max_tokens': 8},
    'stream_then_cancel': {'messages': [{'role': 'user', 'content': 'Count from 1 to 1000, separated by spaces.'}],
                           'max_tokens': 1024, 'stream': True},
}


def body_for(case, served, sampling):
    body = {'model': served, **json.loads(json.dumps(CASES[case])), **sampling}
    return body


class Client:
    def __init__(self, host, port, ledger, clock, served):
        self.host, self.port, self.ledger, self.clock, self.served = host, port, ledger, clock, served

    def _deadline(self, item):
        return min(time.monotonic() + item['timeout_seconds'],
                   self.clock.started + self.clock.limits['admission_cutoff_seconds'])

    def _connection(self, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RequestFailed('request deadline reached before sending')
        connection = http.client.HTTPConnection(self.host, self.port, timeout=remaining)
        connection.connect()
        return connection, connection.sock  # keep the socket: a streaming response takes it from the connection

    def call(self, request_id, body=None):
        """One counted request; returns (status, raw bytes). Never retried here."""
        item, entry = self.ledger.admit(request_id)
        deadline = self._deadline(item)
        begin = time.monotonic()
        try:
            connection, sock = self._connection(deadline)
            try:
                payload = None if body is None else json.dumps(body).encode()
                connection.request(item['method'], item['path'], body=payload,
                                   headers={'Content-Type': 'application/json'} if payload else {})
                response = connection.getresponse()
                data = b''
                while True:
                    if time.monotonic() >= deadline:
                        raise RequestFailed('request deadline reached while reading')
                    sock.settimeout(max(0.01, deadline - time.monotonic()))
                    part = response.read1(65536) if hasattr(response, 'read1') else response.read(65536)
                    if not part:
                        break
                    data += part
                    if len(data) > RESPONSE_CAP:
                        raise RequestFailed('response exceeds cap')
                entry.update(outcome='http_' + str(response.status), seconds=round(time.monotonic() - begin, 3))
                return response.status, data
            finally:
                connection.close()
        except (OSError, http.client.HTTPException, RequestFailed) as exc:
            entry.update(outcome='failed', error=f'{type(exc).__name__}: {str(exc)[:200]}',
                         seconds=round(time.monotonic() - begin, 3))
            raise RequestFailed(f'{request_id}: {type(exc).__name__}: {exc}') from exc

    def completion(self, request_id, case, sampling):
        body = body_for(case, self.served, sampling)
        status, data = self.call(request_id, body)
        if status != 200:
            raise RequestFailed(f'{request_id}: HTTP {status}: {data[:200]!r}')
        reply = json.loads(data)
        choice = reply['choices'][0]
        content, usage = choice['message'].get('content'), reply.get('usage') or {}
        checks = {'model_matches': reply.get('model') == self.served,
                  'content_nonempty': isinstance(content, str) and bool(content.strip()),
                  'finish_reason_valid': choice.get('finish_reason') in ('stop', 'length'),
                  'prompt_tokens_positive': type(usage.get('prompt_tokens')) is int and usage['prompt_tokens'] > 0,
                  'completion_within_limit': type(usage.get('completion_tokens')) is int
                  and 0 < usage['completion_tokens'] <= body['max_tokens']}
        record = {'case': case, 'content': (content or '')[:200], 'finish_reason': choice.get('finish_reason'),
                  'usage': usage, 'checks': checks, 'passed': all(checks.values())}
        if not record['passed']:
            raise RequestFailed(f'{request_id}: response checks failed: {[k for k, v in checks.items() if not v]}')
        return record

    def stream_then_cancel(self, request_id, case, sampling):
        """Stream a long completion, close the connection after the first content chunk (client cancellation)."""
        item, entry = self.ledger.admit(request_id)
        deadline = self._deadline(item)
        body = body_for(case, self.served, sampling)
        begin = time.monotonic()
        connection, sock = self._connection(deadline)
        try:
            connection.request('POST', item['path'], body=json.dumps(body).encode(),
                               headers={'Content-Type': 'application/json'})
            response = connection.getresponse()
            if response.status != 200:
                raise RequestFailed(f'HTTP {response.status}')
            while True:
                if time.monotonic() >= deadline:
                    raise RequestFailed('no streamed content before the deadline')
                sock.settimeout(max(0.01, deadline - time.monotonic()))
                line = response.readline(65536)
                if not line:
                    raise RequestFailed('stream ended before any content')
                line = line.strip()
                if line.startswith(b'data:') and line != b'data: [DONE]':
                    delta = json.loads(line[5:])['choices'][0].get('delta', {})
                    if delta.get('content'):
                        first = round(time.monotonic() - begin, 3)
                        break
            entry.update(outcome='cancelled_after_first_content', first_content_seconds=first,
                         seconds=round(time.monotonic() - begin, 3))
            return {'cancelled': True, 'first_content_seconds': first}
        except (OSError, http.client.HTTPException, ValueError, KeyError, RequestFailed) as exc:
            entry.update(outcome='failed', error=f'{type(exc).__name__}: {str(exc)[:200]}',
                         seconds=round(time.monotonic() - begin, 3))
            raise RequestFailed(f'{request_id}: {type(exc).__name__}: {exc}') from exc
        finally:
            connection.close()  # the cancellation: the server sees the client disconnect
            sock.close()

    def idle_after_cancel(self, request_id, sleep=time.sleep):
        """Read /metrics (at most the plan's max_issues times) until no request is running or waiting."""
        item = self.ledger.plan[request_id]
        readings = []
        for issue in range(item.get('max_issues', 1)):
            if issue:
                sleep(item.get('retry_delay_seconds', 0))
            status, data = self.call(request_id)
            if status != 200:
                raise RequestFailed(f'{request_id}: HTTP {status}')
            values = metrics(data.decode('utf-8', 'replace'))
            readings.append(values)
            if values.get('running') == 0 and values.get('waiting') == 0:
                return {'idle': True, 'readings': readings}
        raise RequestFailed(f'{request_id}: server not idle after cancellation: {readings}')


def metrics(text):
    """Sum vLLM's running/waiting request gauges from a Prometheus exposition."""
    found = {}
    for line in text.splitlines():
        match = re.match(r'^vllm:num_requests_(running|waiting)(\{[^}]*\})?\s+([0-9.eE+-]+)$', line.strip())
        if match:
            found[match.group(1)] = found.get(match.group(1), 0) + float(match.group(3))
    return {k: int(v) for k, v in found.items()}
