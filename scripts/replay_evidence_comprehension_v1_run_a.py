"""Replay a retained connected-suite run through the unmodified connected tests (no new rehearsals).

Extracts the chosen run from the hash-locked intermittent-runs archive, then substitutes `run_fault`
so each test receives that run's own evidence for its fault, in execution order, and runs every test
method as written. For run A this reproduces its single failure; for runs B and C it reproduces
their passes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
LOCK = ROOT / 'reports/evidence_comprehension_v1_intermittent_runs_archive.json'


def extract(run, target):
    lock = json.loads(LOCK.read_bytes())
    archive = ROOT / lock['archive']
    if hashlib.sha256(archive.read_bytes()).hexdigest() != lock['archive_sha256']:
        raise ValueError('archive hash mismatch')
    with tarfile.open(archive, 'r:xz') as bundle:
        for info in bundle.getmembers():
            member = info.name
            if member.startswith(run + '/') and info.isfile():
                if Path(member).is_absolute() or '..' in Path(member).parts:
                    raise ValueError('unsafe archive member')
                raw = bundle.extractfile(info).read()
                if hashlib.sha256(raw).hexdigest() != lock['members'][member]:
                    raise ValueError('member hash mismatch: ' + member)
                path = Path(target) / member
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
    return [(row['fault'], Path(target) / run / row['directory'] / 'working/evidence-comprehension-v1')
            for row in lock['runs'][run]]


def replay(run):
    import tests.test_evidence_comprehension_v1_connected as connected
    from scripts.evaluate_evidence_comprehension_v1 import evaluate_output
    with tempfile.TemporaryDirectory() as folder:
        queue = extract(run, folder)

        def retained(fault, seconds=connected.REHEARSAL_SECONDS):
            expected, output = queue.pop(0)
            if expected != fault:
                raise AssertionError(f'replay order: expected {expected}, test asked for {fault}')
            receipt = json.loads((output / 'control/notebook-cost.json').read_bytes())
            outer = json.loads((output / 'control/outer.json').read_bytes())
            return receipt, output, outer, evaluate_output(output, mode='rehearsal', rehearsal_seconds=seconds)
        connected.run_fault = retained
        result = unittest.TextTestRunner(verbosity=2).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(connected.Rehearsals))
        problems = [{'test': str(t), 'detail': d[-2000:]} for t, d in result.failures + result.errors]
        return {'run': run, 'tests_run': result.testsRun, 'failures': len(result.failures),
                'errors': len(result.errors), 'unconsumed_rehearsals': len(queue), 'problems': problems}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', choices=('run_a', 'run_b', 'run_c'), default='run_a')
    print(json.dumps(replay(parser.parse_args().run), indent=1))
