from pathlib import Path
import tempfile
import unittest
import zipfile

from certification.phase4_v6.torch_wheel_contract import inspect, validate


class TorchContractTests(unittest.TestCase):
    def make_wheel(self, path, version='2.10.0+cu128', cuda='12.8', extra=''):
        with zipfile.ZipFile(path, 'w') as bundle:
            bundle.writestr('torch-2.10.0.dist-info/METADATA',
                            'Name: torch\nVersion: 2.10.0\nRequires-Dist: example==1\n')
            bundle.writestr('torch/version.py',
                            f'__version__: str = {version!r}\ncuda: str = {cuda!r}\n'+extra)

    def test_distribution_and_build_versions_are_distinct_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            wheel = Path(directory)/'torch.whl'
            self.make_wheel(wheel, extra="raise RuntimeError('must never execute')\n")
            result = inspect(wheel)
            self.assertEqual(result['distribution_version'], '2.10.0')
            self.assertEqual(result['runtime_build']['__version__'], '2.10.0+cu128')
            self.assertEqual(result['runtime_build']['cuda'], '12.8')
            validate(result, result)

    def test_cuda_and_metadata_drift_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            wheel = Path(directory)/'torch.whl'
            self.make_wheel(wheel)
            expected = inspect(wheel)
            for change in ({'runtime_build': {'__version__': '2.10.0+cpu', 'cuda': None}},
                           {'distribution_version': '2.10.1'}, {'metadata_sha256': 'wrong'}):
                with self.assertRaises(ValueError):
                    validate({**expected, **change}, expected)

    def test_dynamic_version_assignment_is_not_executed(self):
        with tempfile.TemporaryDirectory() as directory:
            wheel = Path(directory)/'torch.whl'
            self.make_wheel(wheel, extra='cuda = str(12.8)\n')
            with self.assertRaises(ValueError):
                inspect(wheel)
