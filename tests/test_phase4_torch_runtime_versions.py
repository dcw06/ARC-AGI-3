"""Exercise the actual probe runtime assertions with independent version values."""
import contextlib
import io
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from certification.phase4_v6.target_install_probe_r3 import RUNTIME_CHECK


class TorchRuntimeVersionTests(unittest.TestCase):
    def execute(self, distribution='2.10.0', runtime='2.10.0+cu128', cuda='12.8'):
        torch = ModuleType('torch')
        torch.__version__ = runtime
        torch.version = SimpleNamespace(cuda=cuda)
        torch.cuda = SimpleNamespace(is_available=lambda:True, device_count=lambda:1,
            get_device_name=lambda _: 'NVIDIA RTX PRO 6000', synchronize=lambda:None)
        tensor = MagicMock()
        tensor.__matmul__.return_value.__getitem__.return_value.item.return_value = 16
        torch.ones = MagicMock(return_value=tensor)
        vllm = ModuleType('vllm')
        vllm._C = ModuleType('vllm._C')
        modules = {'torch':torch, 'vllm':vllm, 'vllm._C':vllm._C,
                   **{name:ModuleType(name) for name in ('arc_agi', 'arcengine', 'transformers')}}
        versions = {'torch':distribution, 'vllm':'0.19.0', 'transformers':'4.57.6',
                    'arc-agi':'0.9.8', 'arcengine':'0.9.3', 'numpy':'2.4.4'}
        with patch.dict('sys.modules', modules), \
             patch('importlib.metadata.version', side_effect=versions.__getitem__), \
             patch('platform.system', return_value='Linux'), \
             patch('platform.machine', return_value='x86_64'), \
             patch('sys.version_info', (3,12)), \
             patch('subprocess.check_output', return_value='fake test driver'), \
             contextlib.redirect_stdout(io.StringIO()):
            exec(compile(RUNTIME_CHECK, 'probe-runtime-check', 'exec'), {})

    def test_distinct_distribution_and_runtime_versions_pass(self):
        self.execute()

    def test_each_incorrect_version_is_rejected(self):
        for change in ({'distribution':'2.10.0+cu128'}, {'runtime':'2.10.0+cpu'}, {'cuda':'13.0'}):
            with self.subTest(change=change), self.assertRaises(AssertionError):
                self.execute(**change)
