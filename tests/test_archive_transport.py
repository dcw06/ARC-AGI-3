import copy
import json
from pathlib import Path
import tempfile
import unittest
from research.object_discovery_boundaries_v1 import archive_transport as A
from tests.archive_transport_fixture import build, replace


class Transport(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.manifest, self.pin, self.original_pin, self.originals = build(self.source)

    def restore(self):
        return A.restore(self.source, self.root / 'restored', self.pin, self.original_pin)

    def test_multipart_roundtrip_verifies_original_inventory_without_extraction(self):
        result = self.restore()
        self.assertTrue(result['all_sha256_matched'])
        self.assertFalse(result['contents_extracted_or_executed'])
        self.assertEqual(result['original_files_restored'], 3)
        for name, raw in self.originals.items():
            self.assertEqual((self.root / 'restored' / name).read_bytes(), raw)

    def test_changed_manifest_cannot_approve_itself(self):
        self.manifest['originals'][0]['sha256'] = '0' * 64
        replace(self.source, self.manifest)
        with self.assertRaisesRegex(ValueError, 'reviewed digest'):
            self.restore()
        self.assertFalse((self.root / 'restored').exists())

    def test_repinned_transport_cannot_change_original_authority(self):
        self.manifest['original_payload_manifest_sha256'] = '0' * 64
        self.pin = replace(self.source, self.manifest)
        with self.assertRaisesRegex(ValueError, 'protocol differs'):
            self.restore()

    def test_chunk_header_and_payload_corruption_refuse(self):
        path = self.source / self.manifest['originals'][0]['chunks'][0]['name']
        raw = path.read_bytes()
        for offset in (0, len(raw) - 1):
            with self.subTest(offset=offset), tempfile.TemporaryDirectory() as output:
                changed = bytearray(raw)
                changed[offset] ^= 1
                path.write_bytes(changed)
                with self.assertRaises(ValueError):
                    A.restore(self.source, Path(output) / 'new', self.pin, self.original_pin)
        path.write_bytes(raw)

    def test_missing_extra_truncated_and_symlinked_files_refuse(self):
        path = self.source / 'checkpoint.pt'
        original = path.read_bytes()
        path.unlink()
        with self.assertRaisesRegex(ValueError, 'inventory'):
            self.restore()
        path.write_bytes(original[:-1])
        with self.assertRaisesRegex(ValueError, 'size'):
            self.restore()
        path.write_bytes(original)
        (self.source / 'extra').write_bytes(b'')
        with self.assertRaisesRegex(ValueError, 'inventory'):
            self.restore()

    def test_chunk_order_duplicate_and_unsafe_names_refuse_before_writes(self):
        for mode in ('order', 'duplicate', 'path', 'boolean'):
            with self.subTest(mode=mode):
                item = copy.deepcopy(self.manifest)
                chunks = item['originals'][0]['chunks']
                if mode == 'order': chunks.reverse()
                if mode == 'duplicate': chunks[1]['name'] = chunks[0]['name']
                if mode == 'path': item['originals'][0]['name'] = '../outside'
                if mode == 'boolean': chunks[0]['payload_bytes'] = True
                raw = A.canonical(item)
                with self.assertRaises(ValueError):
                    A.manifest(raw, A.digest(raw), self.original_pin)

    def test_duplicate_json_keys_refuse_even_with_matching_bytes_pin(self):
        raw = (self.source / 'transport-manifest.json').read_bytes()
        raw = raw.replace(b'{', b'{"schema":"duplicate",', 1)
        with self.assertRaisesRegex(ValueError, 'duplicate JSON'):
            A.manifest(raw, A.digest(raw), self.original_pin)

    def test_existing_output_is_preserved(self):
        output = self.root / 'restored'
        output.mkdir()
        (output / 'keep').write_bytes(b'keep')
        with self.assertRaises(FileExistsError): self.restore()
        self.assertEqual((output / 'keep').read_bytes(), b'keep')

    def test_deadline_callback_interrupts_restoration(self):
        def stop(): raise TimeoutError('budget')
        with self.assertRaises(TimeoutError):
            A.restore(self.source, self.root / 'restored', self.pin, self.original_pin, stop)
        self.assertFalse((self.root / 'restored').exists())

    @unittest.skipIf(__import__('os').name == 'nt', 'Linux filesystem symlink check')
    def test_symlink_in_mount_is_not_followed(self):
        path = self.source / 'checkpoint.pt'
        outside = self.root / 'outside'
        path.rename(outside)
        path.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'type or size'):
            self.restore()


if __name__ == '__main__': unittest.main()
