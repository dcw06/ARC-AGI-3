"""Commit the owner's completed self-review locally before pooled comparison; no provider or GPU calls.

Use a new private repository outside all project checkouts. Do not publish this
repository or the receipt. Incomplete annotations and reused destinations refuse.
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

def main():
    from research.stagnation_supervision_runtime_v2.selfreview import commit_annotations
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('repository', 'receipt', 'sample', 'annotations'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    record = commit_annotations(args.repository, args.receipt, args.sample, args.annotations)
    print('Private self-review committed: ' + record['commit'])
    print('Annotations SHA256: ' + record['annotations_sha256'])

if __name__ == '__main__':
    main()
