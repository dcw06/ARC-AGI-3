"""Runtime v2 input mounts (hand-written). No recursive search, download or fallback source.

* Wheel dataset: the verified runtime's `publisher_host.dataset_mount` for the version-pinned reference (exactly one
  of /kaggle/input/datasets/<owner>/<slug> or /kaggle/input/<slug>). R4/R6 took the first existing candidate.
* Competition: the same two layouts for arc-prize-2026-arc-agi-3 (competitions/<slug> or <slug>). R4/R6 hard-coded
  /kaggle/input/competitions/arc-prize-2026-arc-agi-3. A root alias is accepted only if it resolves to the other
  layout of the same competition; two distinct real directories are refused. The mount must contain real
  arc_agi_3_wheels and environment_files directories; their bytes are verified later against the frozen manifest.
`inputs` replaces /kaggle/input only in staged CPU rehearsals (the launch refuses it in live mode).
"""
import json
from pathlib import Path

INPUT_ROOT = Path('/kaggle/input')
PROTOCOL = 'research/stagnation_supervision_runtime_v2/protocol.json'


class MountRefused(RuntimeError):
    pass


def _protocol(root):
    return json.loads((Path(root) / PROTOCOL).read_bytes())


def wheelhouse_mount(root, *, inputs=None):
    from research.stagnation_supervision_runtime_v2.publisher_host import dataset_mount
    dataset = _protocol(root)['dataset']
    return dataset_mount(dataset['ref'], dataset['version'], base=Path(inputs) if inputs is not None else INPUT_ROOT)


def competition_mount(root, *, inputs=None):
    competition = _protocol(root)['competition']
    slug = competition['ref']
    base = Path(inputs) if inputs is not None else INPUT_ROOT
    candidates = [base / 'competitions' / slug, base / slug]
    real = [c for c in candidates if c.is_dir() and not c.is_symlink()]
    for alias in (c for c in candidates if c.is_symlink()):
        if not alias.exists() or not real or alias.resolve() != real[0].resolve():
            raise MountRefused(f'competition mount alias does not resolve to the bound competition: {alias}')
    if len(real) != 1:
        raise MountRefused(f'competition {slug}: expected one unambiguous mount; found {len(real)} real directories')
    mount = real[0]
    for name in (competition['game_wheels_dir'], competition['environment_files_dir']):
        folder = mount / name
        if folder.is_symlink() or not folder.is_dir():
            raise MountRefused(f'competition mount lacks a real {name} directory')
    return mount
