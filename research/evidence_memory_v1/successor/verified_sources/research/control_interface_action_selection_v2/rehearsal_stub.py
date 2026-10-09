# Derived by scripts/build_control_interface_action_selection_v2.py; edit the derivation.
"""Local HTTP fixture, not a model. Exercises the complete bounded controller on CPU."""
import argparse
import json
import time
from http.server import ThreadingHTTPServer
from certification.direct_publisher_smoke_v1 import rehearsal_stub as base


class Handler(base.Handler):
    research_fault = 'none'

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
        if self.path != '/v1/chat/completions':
            return self._send(404, {'error': 'not found'})
        if body.get('stream'):
            return self._stream(body)
        research = body.get('response_format') == {'type': 'json_object'}
        content = base.answer(body)
        finish = 'stop'
        if research:
            observation = json.loads(body['messages'][1]['content'])['observation']
            action_id = observation['legal_actions'][0]
            data = {'x': 32, 'y': 32} if action_id == 6 else {}
            if self.research_fault == 'semantic_invalid':
                action_id, data = 0, {}
            if self.research_fault == 'truncated':
                finish = 'length'
            if self.research_fault == 'timeout':
                time.sleep(30)
            content = json.dumps({'action': {'action_id': action_id, 'action_data': data}})
        self._send(200, {'model': self.served, 'choices': [{'index': 0,
            'message': {'role': 'assistant', 'content': content}, 'finish_reason': finish}],
            'usage': {'prompt_tokens': 100, 'completion_tokens': 24 if research else 1}})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--served', required=True)
    parser.add_argument('--research-fault', choices=('none', 'semantic_invalid', 'truncated', 'timeout'), default='none')
    args = parser.parse_args()
    print('SCRIPTED CPU STUB: no model, no GPU; enable_prefix_caching=False', flush=True)
    Handler.served, Handler.research_fault = args.served, args.research_fault
    ThreadingHTTPServer.daemon_threads = True
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
