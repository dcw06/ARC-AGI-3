"""Restore declared transport parts without executing or extracting their contents.

Both manifest digests must come from the independently reviewed protocol.
The mounted inventory and every original byte are checked before use.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct

MAGIC = b'ARC3DATA-TRANSPORT-V1\n'
HEADER_BYTES = len(MAGIC) + 8
MAX_CHUNK = 1024 ** 3
MAX_TOTAL = 32 * 1024 ** 3


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _object(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError('duplicate JSON field')
        result[name] = value
    return result


def _pin(value):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('independently retained SHA256 required')


def _name(value):
    if type(value) is not str or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]{0,179}', value):
        raise ValueError('unsafe transport filename')
    return value


def _integer(value, low=0, high=MAX_TOTAL):
    if type(value) is not int or not low <= value <= high:
        raise ValueError('invalid transport length or offset')


def manifest(raw, transport_sha256, original_sha256):
    _pin(transport_sha256)
    _pin(original_sha256)
    if len(raw) > 1024 ** 2 or digest(raw) != transport_sha256:
        raise ValueError('transport manifest differs from reviewed digest')
    data = json.loads(raw, object_pairs_hook=_object)
    if (data.get('schema') != 'arc3_archive_transport_v2' or
            data.get('original_payload_manifest_sha256') != original_sha256 or
            type(data.get('maximum_chunk_payload_bytes')) is not int or
            data['maximum_chunk_payload_bytes'] != MAX_CHUNK):
        raise ValueError('transport protocol differs')
    originals = data.get('originals')
    if type(originals) is not list or not 1 <= len(originals) <= 48:
        raise ValueError('bounded original inventory required')
    sources, storage = set(), set()
    total = 0
    for row in originals:
        name = _name(row['name'])
        if name.casefold() in sources or name == 'transport-manifest.json':
            raise ValueError('duplicate or reserved original filename')
        sources.add(name.casefold())
        _integer(row['bytes'], 1)
        _pin(row['sha256'])
        total += row['bytes']
        if total > MAX_TOTAL or row['mode'] not in ('unchanged', 'framed_chunks'):
            raise ValueError('transport mode or total size differs')
        chunks = row['chunks']
        if type(chunks) is not list or not 1 <= len(chunks) <= 48:
            raise ValueError('bounded chunk inventory required')
        if row['mode'] == 'unchanged' and len(chunks) != 1:
            raise ValueError('unchanged files must be single parts')
        offset = 0
        for chunk in chunks:
            part = _name(chunk['name'])
            if part.casefold() in storage or part == 'transport-manifest.json':
                raise ValueError('duplicate or reserved transport filename')
            storage.add(part.casefold())
            _integer(chunk['offset'])
            _integer(chunk['payload_bytes'], 1, MAX_CHUNK if row['mode'] == 'framed_chunks' else MAX_TOTAL)
            _integer(chunk['stored_bytes'], 1)
            _pin(chunk['sha256'])
            overhead = HEADER_BYTES if row['mode'] == 'framed_chunks' else 0
            if chunk['offset'] != offset or chunk['stored_bytes'] != chunk['payload_bytes'] + overhead:
                raise ValueError('chunk order or declared size differs')
            if row['mode'] == 'unchanged' and (part != name or chunk['sha256'] != row['sha256']):
                raise ValueError('unchanged file identity differs')
            offset += chunk['payload_bytes']
        if offset != row['bytes']:
            raise ValueError('original file length differs')
    if len(storage) > 48:
        raise ValueError('too many top-level transport files')
    original = next((row for row in originals if row['name'] == 'upload-manifest.json'), None)
    if original is None or original['sha256'] != original_sha256:
        raise ValueError('original payload manifest not independently bound')
    return data


def inventory(data, manifest_bytes):
    return {'transport-manifest.json': manifest_bytes,
            **{chunk['name']: chunk['stored_bytes'] for row in data['originals'] for chunk in row['chunks']}}


def restore(source, output, transport_sha256, original_sha256, check=lambda: None):
    source, output = Path(source), Path(output)
    check()
    if source.is_symlink() or not source.is_dir():
        raise ValueError('regular transport mount required')
    manifest_path = source / 'transport-manifest.json'
    if manifest_path.is_symlink() or manifest_path.stat().st_size > 1024 ** 2:
        raise ValueError('invalid mounted transport manifest')
    raw = manifest_path.read_bytes()
    data = manifest(raw, transport_sha256, original_sha256)
    expected = inventory(data, len(raw))
    actual = list(source.iterdir())
    if {path.name for path in actual} != set(expected):
        raise ValueError('transport mount inventory differs')
    for path in actual:
        check()
        if path.is_symlink() or not path.is_file() or path.stat().st_size != expected[path.name]:
            raise ValueError('transport file type or size differs')
    if shutil.disk_usage(output.parent).free < sum(row['bytes'] for row in data['originals']) + 256 * 1024 ** 2:
        raise ValueError('insufficient space for restored originals and cleanup reserve')
    check()
    output.mkdir(exist_ok=False)
    rows = []
    for row in data['originals']:
        check()
        original_digest = hashlib.sha256()
        with (output / row['name']).open('xb') as target:
            for part in row['chunks']:
                check()
                part_digest = hashlib.sha256()
                with (source / part['name']).open('rb') as stream:
                    if row['mode'] == 'framed_chunks':
                        header = stream.read(HEADER_BYTES)
                        check()
                        if (len(header) != HEADER_BYTES or not header.startswith(MAGIC) or
                                struct.unpack('>Q', header[len(MAGIC):])[0] != part['payload_bytes']):
                            raise ValueError('transport frame header differs')
                        part_digest.update(header)
                    count = 0
                    while True:
                        check()
                        block = stream.read(8 * 1024 * 1024)
                        check()
                        if not block:
                            break
                        count += len(block)
                        if count > part['payload_bytes']:
                            raise ValueError('oversized transport part')
                        target.write(block)
                        check()
                        part_digest.update(block)
                        original_digest.update(block)
                if count != part['payload_bytes'] or part_digest.hexdigest() != part['sha256']:
                    raise ValueError('transport part bytes differ')
        check()
        if (output / row['name']).stat().st_size != row['bytes'] or original_digest.hexdigest() != row['sha256']:
            raise ValueError('reconstructed original bytes differ')
        rows.append({'name': row['name'], 'bytes': row['bytes'], 'sha256': row['sha256']})
    original_raw = (output / 'upload-manifest.json').read_bytes()
    if digest(original_raw) != original_sha256:
        raise ValueError('reconstructed original manifest differs')
    original_inventory = json.loads(original_raw, object_pairs_hook=_object)
    checked = {row['name']: {'bytes': row['bytes'], 'sha256': row['sha256']}
               for row in rows if row['name'] != 'upload-manifest.json'}
    if original_inventory != checked:
        raise ValueError('original manifest does not bind reconstructed payload')
    check()
    return {'transport_manifest_sha256': transport_sha256, 'original_manifest_sha256': original_sha256,
            'transport_files_checked': len(expected), 'original_files_restored': len(rows),
            'transport_bytes_checked': sum(expected.values()), 'originals': rows,
            'all_sha256_matched': True, 'contents_extracted_or_executed': False}
