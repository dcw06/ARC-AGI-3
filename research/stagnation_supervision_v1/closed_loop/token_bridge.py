"""Exact reflection-token admission over the existing bounded model socket.

The game interpreter never imports a tokenizer. Count requests use the same chat
template and context admission as a completion, but never call the model and never
consume the inference-call allowance. The frozen integrated bridge is untouched.
"""
from dataclasses import asdict
import time

from certification.phase4_integrated_v2.bridge import BridgeServer, Handler, receive, request_hash, send
from certification.phase4_integrated_v2.response_evidence import ResponseValidationError, capture, checked


COUNT_OP = 'count_reflection'
MAX_COUNT_CALLS = 2160  # at most two counts per action in the frozen 1080-action schedule


def count_reflection(service, request, digest):
    """Model-side exact count after canary readiness; no transport or inference charge."""
    from research.stagnation_supervision_v1.closed_loop.service import validate_reflection_request
    if service.canary_audit is None or service.canary_audit.get('status') != 'passed':
        raise RuntimeError('model bridge not ready for token counting')
    if type(digest) is not str or digest != request_hash(request):
        raise ValueError('reflection count request hash')
    validate_reflection_request(request)
    calls = getattr(service, 'token_count_calls', 0)
    if calls >= MAX_COUNT_CALLS:
        raise ValueError('reflection count ceiling')
    service.token_count_calls = calls + 1  # a failed admission still consumes one count slot
    return {'request_sha256': digest, 'prompt_tokens': service._admit(request)}


def worker_count(proxy, request):
    """Worker-side count of one exact reflection request through an admitted proxy."""
    if proxy.started is not True:
        raise RuntimeError('model bridge not ready for token counting')
    from research.stagnation_supervision_v1.closed_loop.service import validate_reflection_request
    validate_reflection_request(request)
    digest = request_hash(request)
    result = proxy.call({'op': COUNT_OP, 'request': request, 'request_sha256': digest})
    if (type(result) is not dict or set(result) != {'request_sha256', 'prompt_tokens'}
            or result['request_sha256'] != digest or type(result['prompt_tokens']) is not int
            or not 0 < result['prompt_tokens'] <= 60000):
        raise ValueError('reflection count bridge reply')
    return result['prompt_tokens']


class TokenHandler(Handler):
    """The historical ready/complete protocol with one narrowly scoped count operation."""

    def handle(self):
        server = self.server
        try:
            remaining = server.deadline - time.monotonic()
            if remaining <= 0 or server.cancel.exists():
                raise TimeoutError('bridge admission closed')
            self.request.settimeout(min(remaining, 180))
            message = receive(self.request, server.deadline)
            if message == {'op': 'ready'}:
                service = server.service
                reply = {'artifact': service.artifact, 'canary_audit': service.canary_audit,
                         'startup_seconds': service.startup_seconds}
            elif type(message) is dict and set(message) == {'op', 'request', 'request_sha256'} and message['op'] == COUNT_OP:
                if server.cancel.exists() or time.monotonic() >= server.deadline:
                    raise TimeoutError('bridge admission closed')
                reply = count_reflection(server.service, message['request'], message['request_sha256'])
                if server.cancel.exists() or time.monotonic() >= server.deadline:
                    raise TimeoutError('bridge count after cancellation/deadline')
            elif type(message) is dict and set(message) == {'op', 'request'} and message['op'] == 'complete':
                if server.cancel.exists() or time.monotonic() >= server.deadline:
                    raise TimeoutError('bridge admission closed')
                result, audit = server.service.complete(message['request'])
                if time.monotonic() >= server.deadline or server.cancel.exists():
                    raise ResponseValidationError('bridge completion after cancellation/deadline',
                                                  capture(result.content, audit))
                reply = {'result': asdict(result), 'audit': audit}
            else:
                raise ValueError('invalid bridge operation')
            send(self.request, {'ok': True, 'value': reply})
        except Exception as exc:
            reply = {'ok': False, 'error': type(exc).__name__ + ': ' + str(exc)[:512]}
            if hasattr(exc, 'response_evidence'):
                reply['response_evidence'] = checked(exc.response_evidence)
            try:
                send(self.request, reply)
            except OSError:
                pass


class TokenBridgeServer(BridgeServer):
    """Retain the frozen bridge's queue, semaphore, socket permissions and deadlines."""

    def __init__(self, path, service, deadline, cancel):
        super().__init__(path, service, deadline, cancel)
        self.RequestHandlerClass = TokenHandler
