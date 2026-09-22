"""Catch digest corruption and prevent audit/runtime manifest divergence."""
import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]

class BindingTests(unittest.TestCase):
    def test_original_tokenizer_bytes_and_model_bindings_preserved(self):
        base=ROOT/'certification'
        self.assertEqual((base/'phase4_coordinates_v2/tokenizer_manifest.json').read_bytes(),(base/'phase4_grounding_v1/tokenizer_manifest.json').read_bytes())
        self.assertEqual((base/'phase4_coordinates_v2/cases.json').read_bytes(),(base/'phase4_coordinates_v1/cases.json').read_bytes())
        for name in ('model_artifact.py','model_config.py','model_transport.py'):
            self.assertEqual((base/'phase4_coordinates_v2'/name).read_bytes(),(base/'phase4_coordinates_v1'/name).read_bytes().replace(b'phase4_coordinates_v1',b'phase4_coordinates_v2'))
    def test_audit_uses_runtime_verifier(self):
        from scripts.audit_phase4_coordinates_v2 import verify as audit
        from certification.phase4_coordinates_v2.tokenizer_binding import verify as runtime
        self.assertIs(audit,runtime)
    def test_failure_retains_expected_and_observed_hashes(self):
        from certification.phase4_coordinates_v2.tokenizer_binding import verify
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'vocab.json').write_bytes(b'abc')
            fake={'files':{'vocab.json':{'bytes':3,'sha256':'0'*64}}}
            with patch('certification.phase4_coordinates_v2.tokenizer_binding.json.loads',return_value=fake),patch('builtins.print') as output:
                with self.assertRaisesRegex(ValueError,hashlib.sha256(b'abc').hexdigest()):verify(root)
                self.assertIn('observed_sha256',output.call_args[0][0])

if __name__=='__main__':unittest.main()
