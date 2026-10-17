"""Synthetic multipart fixtures; no real boards, weights or provider data."""
import hashlib
import json
from pathlib import Path
import struct
from research.object_discovery_boundaries_v1.archive_transport import MAGIC, canonical, digest, MAX_CHUNK


def build(root):
    root = Path(root)
    root.mkdir()
    originals = {'runtime.tar': b'synthetic archive bytes only' * 7, 'checkpoint.pt': b'not real weights'}
    original_raw = canonical({name: {'bytes': len(raw), 'sha256': digest(raw)} for name, raw in originals.items()})
    original_pin = digest(original_raw)
    originals['upload-manifest.json'] = original_raw
    manifest = {'schema': 'arc3_archive_transport_v2', 'maximum_chunk_payload_bytes': MAX_CHUNK,
                'original_payload_manifest_sha256': original_pin, 'originals': []}
    for name, raw in originals.items():
        framed = name == 'runtime.tar'
        row = {'name': name, 'bytes': len(raw), 'sha256': digest(raw),
               'mode': 'framed_chunks' if framed else 'unchanged', 'chunks': []}
        size = 73 if framed else len(raw)
        for number, offset in enumerate(range(0, len(raw), size), 1):
            block = raw[offset:offset + size]
            filename = name + '.part-' + str(number) + '.bin' if framed else name
            encoded = MAGIC + struct.pack('>Q', len(block)) + block if framed else block
            (root / filename).write_bytes(encoded)
            row['chunks'].append({'name': filename, 'offset': offset, 'payload_bytes': len(block),
                                  'stored_bytes': len(encoded), 'sha256': digest(encoded)})
        manifest['originals'].append(row)
    raw = canonical(manifest)
    (root / 'transport-manifest.json').write_bytes(raw)
    return manifest, digest(raw), original_pin, originals


def replace(root, manifest):
    raw = canonical(manifest)
    (Path(root) / 'transport-manifest.json').write_bytes(raw)
    return digest(raw)
