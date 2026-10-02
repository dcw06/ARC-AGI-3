"""Replay the offline request inventory behind the pinned Track 3 token audit.

The default mode runs the scripted development episodes without model or GPU calls,
compares every request in order with the write-once tokenizer audit, and creates a
write-once provenance report. ``--check`` verifies that report, its audit, and its
request-building source bindings in a clean checkout without replaying episodes.
``--replay`` performs the full comparison again without writing a report.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
AUDIT = ROOT / 'reports/stagnation_supervision_v1_token_audit.json'
REPORT = ROOT / 'reports/stagnation_supervision_v1_token_audit_input_replay_r2.json'
VERSION = 'stagnation_supervision_v1_token_audit_input_replay_r2'
FIELDS = ('kind', 'pair_id', 'arm', 'episode_id', 'request_sha256')
SOURCE_FILES = (
    'research/stagnation_supervision_v1/closed_loop/protocol.json',
    'research/stagnation_supervision_v1/closed_loop/requests.py',
    'research/stagnation_supervision_v1/closed_loop/runner.py',
    'research/stagnation_supervision_v1/closed_loop/contract.py',
    'research/stagnation_supervision_v1/closed_loop/bridge.py',
    'research/stagnation_supervision_v1/closed_loop/engine.py',
    'research/stagnation_supervision_v1/closed_loop/service.py',
    'research/stagnation_supervision_v1/closed_loop/fake_server.py',
    'research/stagnation_supervision_v1/intervention.py',
    'research/stagnation_supervision_v1/supervision.py',
    'research/stagnation_supervision_v1/thresholds.py',
    'research/stagnation_supervision_v1/trigger_spec.json',
    'scripts/derive_stagnation_supervision_v1.py',
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def bindings():
    return {name: sha((ROOT / name).read_bytes()) for name in SOURCE_FILES}


def ordered_digest(rows):
    return sha(json.dumps(rows, separators=(',', ':'), ensure_ascii=True).encode())


def audit_rows():
    audit = json.loads(AUDIT.read_bytes())
    if audit.get('all_checks_pass') is not True or not isinstance(audit.get('requests'), list):
        raise ValueError('passing token audit with ordered request rows required')
    rows = [{name: row[name] for name in FIELDS} for row in audit['requests']]
    counts = {kind: sum(row['kind'] == kind for row in rows) for kind in ('policy', 'reflection')}
    if counts != {kind: audit['by_kind'][kind]['requests'] for kind in counts}:
        raise ValueError('token audit request counts disagree with ordered rows')
    return rows, counts


def replay():
    from research.stagnation_supervision_v1.closed_loop.requests import enumerate_requests, maximal_reflection_request

    source_before = bindings()
    expected, counts = audit_rows()
    actual = []
    for index, item in enumerate(enumerate_requests()):
        request = item['request']
        digest = sha(json.dumps(request, sort_keys=True).encode())
        if digest != item['request_sha256']:
            raise ValueError(f'enumerated request {index} hash differs from its bytes')
        row = {name: item[name] for name in FIELDS}
        if index >= len(expected) or row != expected[index]:
            raise ValueError(f'enumerated request {index} differs from pinned token audit')
        actual.append(row)
    if len(actual) != len(expected):
        raise ValueError(f'enumerated {len(actual)} requests, audit has {len(expected)}')
    maximal = maximal_reflection_request()
    if bindings() != source_before:
        raise ValueError('request-building source changed during replay')
    return {'version': VERSION, 'status': 'exact_ordered_requests_replayed',
            'audit_sha256': sha(AUDIT.read_bytes()), 'source_bindings': source_before,
            'request_count': len(actual), 'by_kind': counts,
            'ordered_request_rows_sha256': ordered_digest(actual),
            'maximal_reflection_request_sha256': sha(json.dumps(maximal, sort_keys=True).encode()),
            'maximal_reflection_limit': ('The historical token audit records this constructed request count but not '
                                         'its hash; the hash here binds the present constructed request only.'),
            'gpu_runs': 0, 'model_calls': 0}


def check(report=REPORT):
    from research.stagnation_supervision_v1.closed_loop.requests import maximal_reflection_request

    value = json.loads(Path(report).read_bytes())
    expected, counts = audit_rows()
    maximal_digest = sha(json.dumps(maximal_reflection_request(), sort_keys=True).encode())
    if (value.get('version') != VERSION or value.get('status') != 'exact_ordered_requests_replayed'
            or value.get('audit_sha256') != sha(AUDIT.read_bytes())
            or value.get('source_bindings') != bindings()
            or value.get('request_count') != len(expected)
            or value.get('by_kind') != counts
            or value.get('ordered_request_rows_sha256') != ordered_digest(expected)
            or value.get('maximal_reflection_request_sha256') != maximal_digest):
        raise ValueError('token audit replay report or source bindings differ')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--check', action='store_true', help='read-only report and source binding check')
    group.add_argument('--replay', action='store_true', help='full offline replay without writing a report')
    args = parser.parse_args()
    if args.check:
        value = check()
    elif args.replay:
        value = replay()
        if REPORT.exists() and value != check():
            raise ValueError('full replay differs from retained report')
    else:
        if REPORT.exists():
            raise FileExistsError('replay report is write-once; use --check or --replay')
        value = replay()
        with REPORT.open('x', encoding='utf-8') as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write('\n')
    print(json.dumps({k: value[k] for k in ('status', 'request_count', 'by_kind', 'audit_sha256')}))


if __name__ == '__main__':
    main()
