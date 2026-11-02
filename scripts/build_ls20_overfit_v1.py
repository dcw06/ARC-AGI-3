"""Compile a pinned human demonstration into a new, exact-observation policy file."""
import argparse
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research.initial_geometry_assistance_v1.geometry import canonical
from research.ls20_overfit_v1.policy import compile_demo


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', required=True)
    parser.add_argument('--demo-sha256', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise FileExistsError('preserve the existing compiled demonstration')
    program = compile_demo(args.demo, args.demo_sha256)
    raw = canonical(program)
    with output.open('xb') as stream:
        stream.write(raw)
    print(hashlib.sha256(raw).hexdigest())


if __name__ == '__main__':
    main()
