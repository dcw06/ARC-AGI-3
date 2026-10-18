"""Durable evidence and absolute-deadline pipes; standard library only."""
import hashlib
import json
import os
from pathlib import Path
import selectors
import time

from .geometry import canonical


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            value.update(part)
    return value.hexdigest()


def write_new(path, value):
    with Path(path).open('xb') as stream:
        stream.write(canonical(value))
        stream.flush()
        os.fsync(stream.fileno())


class Journal:
    def __init__(self, path):
        self.stream = Path(path).open('xb', buffering=0)

    def __call__(self, event):
        raw = canonical(event).rstrip(b'\n') + b'\n'
        # FileIO.write can be short; a partial record must never admit an effect.
        view = memoryview(raw)
        while view:
            used = self.stream.write(view)
            if not used:
                raise OSError('short journal write')
            view = view[used:]
        os.fsync(self.stream.fileno())

    def close(self):
        self.stream.close()


class DeadlinePipe:
    """One request / one reply, no retry and no timeout reset on trickled bytes."""
    def __init__(self, reader, writer, limit=1024 * 1024):
        self.reader, self.writer, self.limit = reader, writer, limit
        self.buffer = b''
        os.set_blocking(reader.fileno(), False)
        os.set_blocking(writer.fileno(), False)

    @staticmethod
    def wait(file, event, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('engine RPC deadline')
        with selectors.DefaultSelector() as selector:
            selector.register(file, event)
            if not selector.select(remaining) or time.monotonic() >= deadline:
                raise TimeoutError('engine RPC deadline')

    def exchange(self, value, deadline):
        raw = canonical(value).rstrip(b'\n') + b'\n'
        if len(raw) > self.limit:
            raise ValueError('engine request too large')
        while raw:
            self.wait(self.writer, selectors.EVENT_WRITE, deadline)
            try:
                used = os.write(self.writer.fileno(), raw)
            except BlockingIOError:
                continue
            if not used:
                raise EOFError('engine pipe closed during write')
            raw = raw[used:]
        while b'\n' not in self.buffer:
            self.wait(self.reader, selectors.EVENT_READ, deadline)
            try:
                part = os.read(self.reader.fileno(), 65536)
            except BlockingIOError:
                continue
            if not part:
                raise EOFError('engine pipe closed during read')
            self.buffer += part
            if len(self.buffer) > self.limit:
                raise ValueError('engine reply too large')
        raw, self.buffer = self.buffer.split(b'\n', 1)
        if self.buffer or time.monotonic() >= deadline:
            raise ValueError('unsolicited or late engine reply')
        return json.loads(raw)
