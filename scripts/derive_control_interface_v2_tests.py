"""Keep the v1 CPU controls in v2's isolated scope; no runtime/provider work."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build():
    text = (ROOT / 'tests/test_control_interface_action_selection_v1.py').read_text(encoding='utf-8')
    text = text.replace('control_interface_action_selection_v1', 'control_interface_action_selection_v2')
    text = text.replace('control-interface-action-selection-v1', 'control-interface-action-selection-v2')
    text = text.replace('result = check(notebook)',
                        "result = check(notebook, package='research.control_interface_action_selection_v2')")
    return ('# Derived by scripts/derive_control_interface_v2_tests.py; additional scientific tests are separate.\n' + text).encode()


if __name__ == '__main__':
    (ROOT / 'tests/test_control_interface_action_selection_v2.py').write_bytes(build())
