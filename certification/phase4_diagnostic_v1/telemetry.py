"""Lossless chunked telemetry within the existing shared evidence allocation."""
import base64
import gzip
import hashlib
import json
import zlib
import time

CHUNK_SAMPLES = 1024
MAX_SAMPLES = 13220
MAX_CHUNK_BYTES = 1024**2


class TelemetryWriter:
    def __init__(self, store):
        self.store = store
        self.sealed = []

    def save(self, state):
        begin=time.monotonic()
        self.last_timings={'encoding_seconds':0,'chunk_write_seconds':0}
        samples = state['samples']
        if not 0 < len(samples) <= MAX_SAMPLES:
            raise ValueError('telemetry sample count exhausted/invalid')
        chunks = list(self.sealed)
        for start in range(len(self.sealed)*CHUNK_SAMPLES, len(samples), CHUNK_SAMPLES):
            part = samples[start:start+CHUNK_SAMPLES]
            encoding_started=time.monotonic()
            raw = json.dumps(part, sort_keys=True, allow_nan=False).encode()
            if len(raw) > MAX_CHUNK_BYTES:
                raise ValueError('telemetry chunk too large')
            payload = gzip.compress(raw, mtime=0)
            name = f'samples-{start//CHUNK_SAMPLES:04d}.json'
            info = {'name': name, 'count': len(part),
                    'sha256': hashlib.sha256(raw).hexdigest()}
            self.last_timings['encoding_seconds']+=time.monotonic()-encoding_started
            write_started=time.monotonic()
            self.store.save(name, {'codec': 'gzip-base64-json-v1',
                                  'payload': base64.b64encode(payload).decode()})
            self.last_timings['chunk_write_seconds']+=time.monotonic()-write_started
            self.last_timings['last_store_write']=getattr(self.store,'last_write_timings',{})
            chunks.append(info)
            if len(part) == CHUNK_SAMPLES:
                self.sealed.append(info)
        manifest = {key: value for key, value in state.items() if key != 'samples'}
        manifest.update(telemetry_schema='lossless-chunks-v1', sample_count=len(samples),
                        sample_chunks=chunks)
        manifest_started=time.monotonic()
        self.store.save('telemetry.json', manifest)
        self.last_timings['manifest_write_seconds']=time.monotonic()-manifest_started
        self.last_timings['checkpoint_seconds']=time.monotonic()-begin


def read_telemetry(folder):
    def read(path):
        if path.is_symlink() or path.stat().st_size > 2*MAX_CHUNK_BYTES:
            raise ValueError('invalid telemetry file')
        return json.loads(path.read_text())
    state = read(folder/'telemetry.json')
    if state.get('telemetry_schema') != 'lossless-chunks-v1':
        # Historical monolithic evidence remains readable, never rewritten.
        return state
    count = state.get('sample_count')
    if type(count) is not int or not 0 < count <= MAX_SAMPLES:
        raise ValueError('invalid telemetry sample count')
    chunks = state['sample_chunks']
    if len(chunks) != (count+CHUNK_SAMPLES-1)//CHUNK_SAMPLES:
        raise ValueError('telemetry chunk inventory mismatch')
    samples = []
    for index, info in enumerate(chunks):
        if info['name'] != f'samples-{index:04d}.json':
            raise ValueError('telemetry chunk order/path mismatch')
        chunk = read(folder/info['name'])
        if chunk.get('codec') != 'gzip-base64-json-v1':
            raise ValueError('unknown telemetry encoding')
        decoder = zlib.decompressobj(16+zlib.MAX_WBITS)
        raw = decoder.decompress(base64.b64decode(chunk['payload'], validate=True), MAX_CHUNK_BYTES+1)
        if (len(raw) > MAX_CHUNK_BYTES or not decoder.eof or decoder.unused_data
                or hashlib.sha256(raw).hexdigest() != info['sha256']):
            raise ValueError('telemetry chunk integrity/size mismatch')
        part = json.loads(raw)
        expected = min(CHUNK_SAMPLES, count-index*CHUNK_SAMPLES)
        if not isinstance(part, list) or len(part) != expected or info['count'] != expected:
            raise ValueError('telemetry chunk sample count mismatch')
        samples.extend(part)
    state['samples'] = samples
    return state
