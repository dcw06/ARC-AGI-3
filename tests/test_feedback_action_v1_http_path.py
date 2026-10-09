"""The live model-host factory's HTTP path on CPU (no model, no GPU): `host.pinned_model_factory`, unchanged, with a
CPU stand-in for vLLM (tests/fa1_fake_vllm.py) on a fixture model tree.

Exercised exactly as live: the model-tree digest check, the server started in its own process group, TCP
readiness, the server-log prefix-caching confirmation, the HTTP transport, the canary, every request form of both
arms (the candidate's extended schema included) through the service contract, tokenizer admission and the
cross-process token audit, then the owned group's cleanup and the retained evidence. The stand-in compiles each
request's response_format with xgrammar as vLLM 0.19 does and answers with the CPU fake server's scripted content.

Runs in the model interpreter (transformers, requests, xgrammar) with FA1_REHEARSAL_TOKENIZER (the pinned tokenizer)
and FA1_FORMS (the token audit's forms file: real requests of both arms from the offline engine); skipped otherwise.
"""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOKENIZER_FILES = ('tokenizer.json', 'tokenizer_config.json', 'chat_template.json', 'config.json', 'vocab.json',
                   'merges.txt')


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


class LiveFactoryHttpPath(unittest.TestCase):
    def setUp(self):
        self.tokenizer = os.environ.get('FA1_REHEARSAL_TOKENIZER')
        self.forms = os.environ.get('FA1_FORMS')
        if not self.tokenizer or not self.forms or importlib.util.find_spec('xgrammar') is None:
            self.skipTest('needs the model interpreter, FA1_REHEARSAL_TOKENIZER and FA1_FORMS')

    def test_factory_canary_every_form_and_cleanup_over_http(self):
        from certification.direct_publisher_smoke_v1.host import tree_sha256
        from research.feedback_action_v1.live import host as H, runtime as RT
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            model = tmp / 'model'
            model.mkdir()
            for name in TOKENIZER_FILES:
                shutil.copyfile(Path(self.tokenizer) / name, model / name)
            (model / 'model.safetensors.index.json').write_text('{}')
            for i in range(1, 5):
                (model / f'model-0000{i}-of-00004.safetensors').write_bytes(b'fixture shard, not model weights')
            runtime = copy.deepcopy(RT.load(ROOT))
            runtime['model'].update(source_kind='model', mounted_path=str(model),
                                    tree_sha256=tree_sha256(model)['tree_sha256'])
            port = free_port()
            runtime['server'].update(port=port, request_timeout_seconds=120, terminate_grace_seconds=5,
                                     kill_grace_seconds=3, argv=['{python}', str(ROOT / 'tests/fa1_fake_vllm.py'),
                                                                 '--model', '{model_path}', '--port', '{port}',
                                                                 '--root', str(ROOT)])
            original = RT.load
            RT.load = lambda root=RT.ROOT: copy.deepcopy(runtime)
            out = tmp / 'out'
            retained = []
            try:
                service, owner = H.pinned_model_factory(retained.append, time.monotonic() + 600, evidence_root=out,
                                                        server_log=tmp / 'model-server.log')
                try:
                    canary = service.startup_canary()
                    rows = json.loads(Path(self.forms).read_bytes())[1:]
                    results = []
                    for row in rows:
                        result, audit = service.complete(row['request'])
                        results.append((row['label'], row['arm'], audit, result))
                finally:
                    receipt = owner.close()
            finally:
                RT.load = original
            self.assertEqual(canary['status'], 'passed')
            self.assertEqual(retained[-1]['status'], 'passed')
            self.assertEqual(len(results), 24)  # 25 forms: the canary was sent first
            for label, arm, audit, result in results:
                self.assertEqual(audit['tokenizer_prompt_tokens'], audit['server_prompt_tokens'], label)
                self.assertEqual(result.finish_reason, 'stop', label)
                self.assertLessEqual(result.completion_tokens, 640 if arm == 'candidate' else 128)
                if arm == 'candidate':
                    self.assertIn('hypothesis_test', json.loads(result.content))
            self.assertTrue(receipt['groups_absent'])
            evidence = {p.name: json.loads(p.read_bytes()) for p in (out / 'worker').glob('*.json')}
            self.assertEqual(evidence['model-artifact.json']['tree_sha256'], runtime['model']['tree_sha256'])
            self.assertTrue(evidence['model-server-config.json']['prefix_caching']['disabled'])
            self.assertEqual(evidence['model-server.json']['pgid'], evidence['model-server.json']['pid'])
            self.assertTrue(evidence['model-server-cleanup.json']['receipt']['groups_absent'])
            self.assertTrue((out / 'logs/model-server.json').is_file())
            print(json.dumps({'forms': len(results), 'max_prompt_tokens': max(a['server_prompt_tokens']
                                                                               for _, _, a, _ in results),
                              'max_candidate_completion_tokens': max(r.completion_tokens for _, arm, _, r in results
                                                                     if arm == 'candidate')}))


if __name__ == '__main__':
    unittest.main()
