# Derived by scripts/build_evidence_memory_v1_sessions.py from research/control_interface_action_selection_v2/evidence.py at 5a21dd3 (origin/wheelhouse-replacement-audit); edit the derivation.
"""Retained evidence: atomic JSON/text writes and a final SHA-256 manifest. The evidence class is fixed by the run
mode: a scripted CPU rehearsal can never report GPU compatibility evidence."""
import hashlib
import json
import os
from pathlib import Path

REHEARSAL = 'scripted_cpu_rehearsal'
LIVE = 'gpu_evidence_memory_v1_session_a_stage1_run'
REHEARSAL_LIMITS = [
    'no GPU, CUDA, vLLM engine or model weights were used: the model server is a scripted stub',
    'installation was exercised on fixture wheels, not the publisher wheels',
    'establishes only that the control code (gate, clock, request ledger, timeouts, cancellation handling, process '
    'cleanup, evidence retention) behaves as specified against scripted behaviour',
]


def evidence_class(mode):
    if mode == 'rehearsal':
        return REHEARSAL
    if mode == 'live':
        return LIVE
    raise ValueError(f'unknown mode {mode!r}')


class Evidence:
    def __init__(self, folder, mode):
        self.folder, self.mode = Path(folder), mode
        self.folder.mkdir(parents=True, exist_ok=False)

    def _write(self, name, data):
        path = (self.folder / name).resolve()
        if not path.is_relative_to(self.folder.resolve()):
            raise ValueError('evidence path escapes the folder')
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + '.partial')
        with temporary.open('wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        return path

    def json(self, name, value):
        return self._write(name, (json.dumps(value, indent=1, sort_keys=True, default=str) + '\n').encode())

    def text_tail(self, name, source, limit):
        """The last `limit` bytes of a log (marked when truncated)."""
        source = Path(source)
        if not source.exists():
            return None
        size = source.stat().st_size
        with source.open('rb') as stream:
            stream.seek(max(0, size - limit))
            data = stream.read()
        if size > limit:
            data = f'[truncated: first {size - limit} of {size} bytes omitted]\n'.encode() + data
        return self._write(name, data)

    def finalize(self, result):
        """Write result.json (with the mode's evidence class, which callers cannot override) and the manifest."""
        result = dict(result, mode=self.mode, evidence_class=evidence_class(self.mode))
        if self.mode == 'rehearsal':
            result['gpu_compatibility_evidence'] = False
            result['rehearsal_limits'] = REHEARSAL_LIMITS
        else:
            result['gpu_compatibility_evidence'] = False
            result['study_lifecycle_passed'] = bool(result.get('passed'))
            result['evidence_scope'] = ('Track 2 Stage 1 session A: technical evidence only; outcomes only from the pooled '
                                        'two-session analysis')
        self.json('result.json', result)
        files = {p.relative_to(self.folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted(self.folder.rglob('*')) if p.is_file() and p.name != 'evidence-manifest.json'}
        self.json('evidence-manifest.json', {'files': files})
        return result
