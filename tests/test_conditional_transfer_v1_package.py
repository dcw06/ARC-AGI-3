import copy
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from research.conditional_transfer_v1 import build as B, replay as RP, schema as S, score as SC, render as R


class Package(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files, cls.summary, cls.audit = B.artifacts()

    def test_duplicates_preserve_all_dependent_aliases(self):
        requests = [json.loads(line) for line in gzip.decompress(self.files['requests.jsonl.gz']).splitlines()]
        aliases = [json.loads(line) for line in gzip.decompress(self.files['request_aliases.jsonl.gz']).splitlines()]
        self.assertEqual(len(aliases), 5184)
        self.assertEqual(len(requests), self.audit['unique_requests'])
        self.assertEqual(len({r['request_id'] for r in requests}), len(requests))
        self.assertEqual({a['request_id'] for a in aliases}, {r['request_id'] for r in requests})
        self.assertEqual(len(aliases)-len(requests), self.audit['duplicate_aliases'])
        for r in requests:
            self.assertEqual(RP.digest(r['request']), r['request_id'])

    def test_hidden_fields_never_reach_request(self):
        for line in gzip.decompress(self.files['requests.jsonl.gz']).splitlines():
            request = json.loads(line)['request']
            p, _ = SC.parse_request(request)
            self.assertEqual(set(p), {'rule', 'target', 'task', 'answer_categories', 'evidence'})
            self.assertNotIn('family', p)
            self.assertNotIn('evaluator_only', p)
            self.assertEqual(request['max_tokens'], S.OUTPUT_CAP)

    def test_cpu_package_has_no_execution_authority(self):
        protocol = json.loads(self.files['protocol.json'])
        manifest = json.loads(self.files['manifest.json'])
        self.assertFalse(protocol['execution_authorized'])
        self.assertFalse(protocol['gpu_enabled'])
        self.assertFalse(manifest['execution_authorized'])
        self.assertFalse(manifest['gpu_enabled'])
        self.assertEqual(protocol['workload']['writer_model_calls'], 0)
        self.assertEqual(protocol['evaluation']['status'], 'reserved_not_generated')

    def test_manifest_does_not_legitimise_forged_request(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name, data in self.files.items():
                (root/name).write_bytes(data)
            lines = [json.loads(x) for x in gzip.decompress(self.files['requests.jsonl.gz']).splitlines()]
            p, _ = SC.parse_request(lines[0]['request'])
            p['rule']['action']['action_data']['x'] = 99
            lines[0]['request']['messages'][1]['content'] = S.compact(p)
            lines[0]['request_id'] = RP.digest(lines[0]['request'])
            altered = gzip.compress((''.join(S.compact(x)+'\n' for x in lines)).encode(), mtime=0)
            (root/'requests.jsonl.gz').write_bytes(altered)
            manifest = json.loads(self.files['manifest.json'])
            manifest['sha256']['requests.jsonl.gz'] = hashlib.sha256(altered).hexdigest()
            (root/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'semantic package reconstruction differs'):
                RP.verify_directory(root)


if __name__ == '__main__':
    unittest.main()
