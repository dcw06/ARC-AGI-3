"""Reuse the pinned existing ARC adapter with bounded, no-retry HTTP sessions."""
import time
from http.cookies import SimpleCookie
from urllib.parse import urlsplit
import requests
from agent.framework_adapter import RemoteFrameworkAdapter
from .transport import request_once


class BoundedSession(requests.Session):
    def __init__(self, origin, timeout, *, transport=request_once):
        super().__init__()
        self.origin, self.limit, self.transport = origin.rstrip('/'), timeout, transport
        self.trust_env = False

    def request(self, method, url, **kwargs):
        if not url.startswith(self.origin + '/'):
            raise ValueError('ARC session refuses another origin')
        prepared = self.prepare_request(requests.Request(method, url, headers=kwargs.get('headers'),
                                                         data=kwargs.get('data')))
        remaining = min(kwargs.get('timeout', self.limit()), self.limit())
        result = self.transport(prepared.url, method.upper(), dict(prepared.headers), prepared.body, remaining)
        if result['status'] != 200:
            raise requests.HTTPError('ARC HTTP ' + str(result['status']) + '; no retry')
        response = requests.Response()
        response.status_code, response.url = result['status'], url
        response._content = result['body'].encode('utf-8')
        response.headers.update(dict(result['headers']))
        for key, value in result['headers']:
            if key.lower() == 'set-cookie':
                cookie = SimpleCookie()
                cookie.load(value)
                for name, morsel in cookie.items():
                    self.cookies.set(name, morsel.value, domain=urlsplit(self.origin).hostname, path='/')
        return response


def make_adapter(config, api_key, clock):
    def limit():
        left = clock() - (0 if getattr(adapter, '_evaluation_cleanup', False) else config.cleanup_seconds)
        return min(config.request_timeout_seconds, left)
    adapter = RemoteFrameworkAdapter(base_url=config.arc_base_url, api_key=api_key,
        competition_mode=config.mode == 'competition', timeout_seconds=config.request_timeout_seconds,
        session_factory=lambda: BoundedSession(config.arc_base_url, limit))
    return adapter
