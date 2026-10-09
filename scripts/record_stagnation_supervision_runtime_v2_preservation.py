"""Record (once) the SHA-256 of every Track 3 file at the base commit, so tests can prove the successor left the
historical protocol, review snapshots, authorization/launch packages, R6 submission/cancellation/claim records,
frozen sources and historical scripts/tests byte-identical. Reads git objects only; writes one report."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = 'bc19919dace8dd919bf5617174534526783c159d'
OUT = ROOT / 'reports/stagnation_supervision_runtime_v2_historical_preservation.json'
PATTERN = re.compile(
    r'^(notebooks/stagnation-supervision-v1-|reports/stagnation_|research/stagnation_supervision_v1/|'
    r'research/transition_evidence_v1/|research/transition_evidence_v2/|'
    r'scripts/(stagnation|kaggle_stagnation|submit_stagnation|launch_stagnation|prepare_stagnation|record_stagnation|'
    r'review_stagnation|build_stagnation|build_review_stagnation|check_stagnation|derive_stagnation_supervision_v1|'
    r'evaluate_stagnation|rehearse_stagnation_supervision_v1|audit_stagnation|verify_stagnation)|'
    r'tests/test_(stagnation|ssv_))')


def main():
    if OUT.exists():
        raise SystemExit('write-once record exists: ' + str(OUT))
    names = subprocess.run(['git', 'ls-tree', '-r', '--name-only', BASE], cwd=ROOT, capture_output=True, text=True,
                           check=True).stdout.splitlines()
    files = {}
    for name in names:
        if PATTERN.match(name):
            data = subprocess.run(['git', 'show', f'{BASE}:{name}'], cwd=ROOT, capture_output=True, check=True).stdout
            files[name] = hashlib.sha256(data).hexdigest()
    record = {'schema': 'stagnation_supervision_runtime_v2_historical_preservation_v1', 'base_commit': BASE,
              'scope': ('every Track 3 file at the base commit: protocol and reports, review snapshots r1-r4, '
                        'authorization r5/r6, the R5/R6 session-1 reserved and launch packages, the R7 preparation '
                        'package, the R6 submission, invalid-attachment, cancellation, consumed-claim and quota records, '
                        'frozen sources, transition evidence v1/v2, and historical scripts and tests'),
              'method': 'sha256 of git blob contents at base_commit; every file must stay byte-identical',
              'files': files}
    OUT.write_text(json.dumps(record, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    changed = [n for n, d in files.items() if hashlib.sha256((ROOT / n).read_bytes()).hexdigest() != d]
    print(json.dumps({'files': len(files), 'changed_in_worktree': changed}))
    return 1 if changed else 0


if __name__ == '__main__':
    sys.exit(main())
