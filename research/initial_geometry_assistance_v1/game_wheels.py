"""Resolve read-only competition wheels; never download, copy or repair them."""
import json
from pathlib import Path

from .engine import verify_game_environment

GAME_WHEEL_SOURCE = {'kind': 'competition_mount', 'competition': 'arc-prize-2026-arc-agi-3',
                     'directory': 'arc_agi_3_wheels'}


def mounted_game_wheels(source, *, base=Path('/kaggle/input')):
    if source != GAME_WHEEL_SOURCE:
        raise ValueError('game wheel source differs from frozen competition binding')
    base = Path(base)
    candidates = [base/'competitions'/source['competition'], base/source['competition']]
    found = [p for p in candidates if p.is_dir()]
    if len(found) != 1:
        raise ValueError('competition mount missing or ambiguous')
    wheels = found[0]/source['directory']
    if any(p.is_symlink() for p in (wheels, *wheels.parents)) or not wheels.is_dir():
        raise ValueError('unsafe or missing competition wheel directory')
    return wheels


def verify_mounted_game(root, receipt_sha256, source, *, base=Path('/kaggle/input'), check=lambda: None):
    wheels = mounted_game_wheels(source, base=base)
    receipt = verify_game_environment(root, receipt_sha256, wheels=wheels, check=check)
    members = json.loads((Path(root)/'receipt.json').read_bytes())['verified_members']
    names = {name.split('/', 1)[1] for name in members if name.startswith('wheels/')}
    if len(names) != 31:
        raise ValueError('expected exactly 31 frozen game wheels')
    return wheels, dict(receipt, source=source, mounted_path=str(wheels), wheel_count=len(names))
