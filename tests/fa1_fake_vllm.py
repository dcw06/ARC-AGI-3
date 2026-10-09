"""CPU stand-in for the vLLM OpenAI server, for the live host factory's HTTP path (test support only; no model).

Started by the live factory exactly like vLLM (own process group, TCP readiness, log file). It prints the startup
configuration line the prefix-caching check reads, then serves POST /v1/chat/completions:
- the request's response_format is compiled with xgrammar as vLLM 0.19 does by default (json_schema,
  any_whitespace=True); a schema xgrammar cannot compile is a 400, as in vLLM;
- the completion is the CPU fake server's scripted content for that request, and must be accepted by the grammar;
- usage is counted with the pinned tokenizer: prompt tokens via the chat template with the request's
  chat_template_kwargs, completion tokens as the encoded content plus the end-of-turn token.
"""
import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--root', required=True)
    args = parser.parse_args()
    sys.path.insert(0, args.root)
    import xgrammar
    from xgrammar.testing import _is_grammar_accept_string as accepts
    from transformers import AutoTokenizer
    from research.feedback_action_v1.live.fake_server import scripted_content
    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True, trust_remote_code=False)
    print("non-default args: {'model': '%s', 'enable_prefix_caching': False, 'max_model_len': 65536}" % args.model,
          flush=True)
    state = {'calls': -1}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, status, value):
            data = json.dumps(value).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            if self.path != '/v1/chat/completions':
                return self.reply(404, {'error': 'not found'})
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            state['calls'] += 1
            try:
                schema = json.dumps(body['response_format']['json_schema']['schema'])  # order as received
                grammar = xgrammar.Grammar.from_json_schema(schema, any_whitespace=True)
            except Exception as exc:
                return self.reply(400, {'error': f'grammar: {exc}'})
            content, finish = scripted_content(body, state['calls'], 'normal')
            if finish == 'stop' and not accepts(grammar, content):
                return self.reply(500, {'error': 'scripted completion outside the grammar'})
            prompt = len(tokenizer.apply_chat_template(body['messages'], tokenize=True, add_generation_prompt=True,
                                                       **body.get('chat_template_kwargs', {})))
            completion = len(tokenizer.encode(content, add_special_tokens=False)) + 1
            self.reply(200, {'model': body['model'], 'choices': [{'index': 0, 'finish_reason': finish,
                                                                   'message': {'role': 'assistant', 'content': content}}],
                             'usage': {'prompt_tokens': prompt, 'completion_tokens': completion,
                                       'total_tokens': prompt + completion}})

    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()


if __name__ == '__main__':
    main()
