"""Write or verify the frozen action-effect fixtures (no model calls)."""
import argparse
import hashlib

from research.action_effect_v1.fixtures import OUTPUT, render

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='regenerate and compare with the committed file')
    args = parser.parse_args()
    text = render()
    if args.check:
        if OUTPUT.read_text(encoding='utf-8') != text:
            raise SystemExit('fixtures differ from deterministic regeneration')
        print('fixtures match', hashlib.sha256(text.encode()).hexdigest())
    else:
        OUTPUT.write_text(text, encoding='utf-8', newline='\n')
        print('wrote', OUTPUT.name, hashlib.sha256(text.encode()).hexdigest())
