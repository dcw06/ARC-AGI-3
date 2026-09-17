import json
from pathlib import Path
import tempfile
import unittest

from certification.phase4_v6.evidence import EvidenceStore, LIMITS
from certification.phase4_v6.telemetry import TelemetryWriter, read_telemetry, CHUNK_SAMPLES


class TelemetryTests(unittest.TestCase):
    def test_full_envelope_fits_and_roundtrips_every_sample(self):
        # Size/codec validation only, not live GPU timing or measured capacity.
        samples = [{'uuid': 'GPU-01234567-89ab-cdef-0123-456789abcdef',
                    'elapsed_seconds': i*.25, 'monotonic_seconds': 1234567+i*.25,
                    'used_bytes': 85000000000+i, 'rss_bytes': 120000000000+i,
                    'scratch_bytes': 4000000000+i} for i in range(110161)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            writer = TelemetryWriter(EvidenceStore(root, 'monitor'))
            # Write a partial chunk, seal it, then continue across all boundaries.
            for count in (1, CHUNK_SAMPLES, CHUNK_SAMPLES+1, len(samples)):
                writer.save({'samples': samples[:count], 'scope': 'fixture'})
            writer.save({'samples': samples, 'scope': 'fixture', 'status': 'completed'})
            restored = read_telemetry(root/'monitor')
            self.assertEqual(restored['samples'], samples)
            size = sum(p.stat().st_size for p in root.rglob('*') if p.is_file())
            self.assertLess(size+2*1024**2, LIMITS['monitor'])

    def test_corruption_and_reordering_cannot_hide_samples(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            writer = TelemetryWriter(EvidenceStore(root, 'monitor'))
            writer.save({'samples': [{'elapsed_seconds': 1}]})
            path = root/'monitor/telemetry.json'
            state = json.loads(path.read_text())
            state['sample_chunks'][0]['sha256'] = '0'*64
            path.write_text(json.dumps(state))
            with self.assertRaisesRegex(ValueError, 'integrity'):
                read_telemetry(root/'monitor')
            state['sample_chunks'][0]['name'] = '../other.json'
            path.write_text(json.dumps(state))
            with self.assertRaisesRegex(ValueError, 'order/path'):
                read_telemetry(root/'monitor')
