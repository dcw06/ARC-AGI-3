"""Source freeze regressions use inert temporary files, never an engine/model."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from research.feedback_probe_v1.preparation import verify_prepared
from research.feedback_probe_v1.source_closure import (
    safe_member, source_inventory, source_payload, verify_source_inventory,
    write_source_payload,
)


def put(root, name, text):
    path = root/name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def hashed(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def draft(root, sources):
    manifest = {'files': {}}
    put(root, 'manifest.json', json.dumps(manifest))
    put(root, 'draft-lock.json', json.dumps({
        'live_launch_package': False,
        'manifest_sha256': hashed(root/'manifest.json'), 'sources': sources,
    }))
    return hashed(root/'draft-lock.json')


class SourceClosure(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)/'checkout'
        self.root.mkdir()

    def test_transitive_relative_imports_and_initializers_without_execution(self):
        put(self.root, 'app/__init__.py', 'raise RuntimeError("must not execute")\n')
        put(self.root, 'app/main.py', 'from . import policy\n')
        put(self.root, 'app/policy.py', 'from support.images import png\n')
        put(self.root, 'support/__init__.py', 'from . import colors\n')
        put(self.root, 'support/colors.py', 'PALETTE = []\n')
        put(self.root, 'support/images.py', 'def png(): pass\n')
        actual = source_inventory(self.root, ['app/main.py'])
        self.assertEqual(set(actual), {'app/__init__.py', 'app/main.py', 'app/policy.py',
                                      'support/__init__.py', 'support/colors.py', 'support/images.py'})

    def test_omitted_initializer_in_old_external_pin_is_refused(self):
        put(self.root, 'support/__init__.py', 'SENTINEL = "changed probe instruction"\n')
        put(self.root, 'support/images.py', 'def png(): pass\n')
        put(self.root, 'policy.py', 'from support.images import png\n')
        # e1e2349 only hashed listed files, so this incomplete lock was accepted
        # even though Python executes an unlisted, mutable package initializer.
        incomplete = {name: hashed(self.root/name) for name in ('policy.py', 'support/images.py')}
        prepared = Path(self.temporary.name)/'old-draft'
        prepared.mkdir()
        pin = draft(prepared, incomplete)
        with self.assertRaisesRegex(ValueError, 'source closure changed'):
            verify_prepared(prepared, pin, self.root)

    def test_mutated_initializer_rejected_under_unchanged_external_pin(self):
        put(self.root, 'support/__init__.py', 'SENTINEL = "original"\n')
        put(self.root, 'support/images.py', 'def png(): pass\n')
        put(self.root, 'policy.py', 'from support.images import png\n')
        sources = source_inventory(self.root, ['policy.py'])
        prepared = Path(self.temporary.name)/'draft'
        prepared.mkdir()
        pin = draft(prepared, sources)
        verify_prepared(prepared, pin, self.root)
        put(self.root, 'support/__init__.py', 'SENTINEL = "mutated"\n')
        with self.assertRaisesRegex(ValueError, 'support/__init__.py'):
            verify_prepared(prepared, pin, self.root)
        self.assertEqual(hashed(prepared/'draft-lock.json'), pin)

    def test_added_namespace_initializer_refused_unrelated_checkout_files_allowed(self):
        put(self.root, 'app/main.py', 'from app import policy\n')
        put(self.root, 'app/policy.py', 'VALUE = 1\n')
        approved = source_inventory(self.root, ['app/main.py'])
        put(self.root, 'app/unrelated.py', 'raise RuntimeError("unrelated")\n')
        put(self.root, 'other/__init__.py', 'raise RuntimeError("unrelated")\n')
        self.assertEqual(verify_source_inventory(self.root, approved), approved)
        put(self.root, 'app/__init__.py', 'raise RuntimeError("import shadow")\n')
        with self.assertRaisesRegex(ValueError, 'app/__init__.py'):
            verify_source_inventory(self.root, approved)

    def test_new_external_import_shadow_refused(self):
        put(self.root, 'main.py', 'import json\n')
        approved = source_inventory(self.root, ['main.py'])
        put(self.root, 'json.py', 'raise RuntimeError("shadow stdlib")\n')
        with self.assertRaisesRegex(ValueError, 'json.py'):
            verify_source_inventory(self.root, approved)

    def test_new_module_cannot_shadow_namespace_package(self):
        put(self.root, 'main.py', 'from app import policy\n')
        put(self.root, 'app/policy.py', 'VALUE = 1\n')
        approved = source_inventory(self.root, ['main.py'])
        put(self.root, 'app.py', 'VALUE = "shadow"\n')
        with self.assertRaisesRegex(ValueError, 'source closure changed'):
            verify_source_inventory(self.root, approved)

    def test_sourceless_import_shadow_refused(self):
        put(self.root, 'main.py', 'import json\n')
        approved = source_inventory(self.root, ['main.py'])
        put(self.root, 'json.pyc', 'opaque bytecode\n')
        with self.assertRaisesRegex(ValueError, 'non-source local import candidate'):
            verify_source_inventory(self.root, approved)

    def test_literal_dynamic_import_and_explicit_data_are_closed(self):
        put(self.root, 'main.py', 'import importlib\nimportlib.import_module("app.worker")\n')
        put(self.root, 'app/worker.py', 'VALUE = 1\n')
        put(self.root, 'settings.json', '{"bounded":true}\n')
        self.assertEqual(set(source_inventory(self.root, ['main.py', 'settings.json'])),
                         {'main.py', 'app/worker.py', 'settings.json'})

    def test_payload_contains_only_pins_and_refuses_overlays(self):
        put(self.root, 'app/main.py', 'from . import policy\n')
        put(self.root, 'app/policy.py', 'VALUE = 1\n')
        approved = source_inventory(self.root, ['app/main.py'])
        put(self.root, 'private-reference-keys/key.json', '{"answer":"private"}\n')
        self.assertEqual(set(source_payload(self.root, approved)), set(approved))
        target = Path(self.temporary.name)/'payload'
        write_source_payload(self.root, approved, target)
        verify_source_inventory(target, approved, closed=True)
        self.assertFalse((target/'private-reference-keys').exists())
        with self.assertRaises(FileExistsError):
            write_source_payload(self.root, approved, target)
        put(target, 'unapproved.py', 'VALUE = 2\n')
        with self.assertRaisesRegex(ValueError, 'unexpected files'):
            verify_source_inventory(target, approved, closed=True)

    def test_native_unsafe_member_names_are_rejected(self):
        put(self.root, 'okay.py', 'VALUE = 1\n')
        for name in ('../okay.py', '..\\okay.py', 'C:/okay.py', '/okay.py', './okay.py', 'a//okay.py'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_member(self.root, name)


if __name__ == '__main__':
    unittest.main()
