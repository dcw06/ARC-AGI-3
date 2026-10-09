"""Distribution metadata and CUDA build are independent exact checks; no GPU use."""
import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from certification.direct_publisher_smoke_v1 import install as I
from certification.direct_publisher_smoke_v1.preflight import PACKAGE, load_inputs, normalize


class RuntimeVersionTests(unittest.TestCase):
    def setUp(self):
        self.runtime = json.loads((PACKAGE / 'protocol.json').read_bytes())['runtime']

    def checked_install(self, *, version='2.10.0', cuda='12.8'):
        report = {'versions': dict(self.runtime['packages']), 'imports': {}, 'torch_cuda_build': cuda}
        report['versions']['torch'] = version
        completed = subprocess.CompletedProcess([], 0, stdout=json.dumps(report), stderr='')
        with tempfile.TemporaryDirectory() as folder, patch.object(I, '_run', return_value=completed):
            return I.install(Path(folder) / 'bundle', Path(folder) / 'venv', self.runtime,
                             time.monotonic() + 10, Path(folder) / 'install.log')

    def test_protocol_distribution_versions_match_trusted_installation_pins(self):
        _, _, pins = load_inputs()
        for name, version in self.runtime['packages'].items():
            self.assertEqual(version, pins[normalize(name)][0], name)

    def test_trusted_torch_metadata_and_cuda_build_pass_independent_checks(self):
        try:
            report = self.checked_install()
        except I.InstallFailed as exc:
            self.fail(f'trusted distribution metadata and CUDA build were rejected: {exc}')
        self.assertTrue(report['passed'])
        self.assertEqual(report['versions']['torch'], '2.10.0')
        self.assertEqual(report['torch_cuda_build'], '12.8')

    def test_wrong_distribution_version_is_rejected(self):
        with self.assertRaisesRegex(I.InstallFailed, 'version mismatch'):
            self.checked_install(version='2.9.0')

    def test_local_version_suffix_is_not_silently_normalized(self):
        with self.assertRaisesRegex(I.InstallFailed, 'version mismatch'):
            self.checked_install(version='2.10.0+unexpected')

    def test_wrong_cuda_build_is_rejected(self):
        # Use the protocol's version so this verifies the separate CUDA guard on
        # both the baseline and repaired protocol.
        with self.assertRaisesRegex(I.InstallFailed, 'torch CUDA build'):
            self.checked_install(version=self.runtime['packages']['torch'], cuda='12.6')


if __name__ == '__main__':
    unittest.main()
