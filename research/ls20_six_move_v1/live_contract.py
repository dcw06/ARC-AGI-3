"""Frozen initial board and explicit six-move instruction; future frames excluded."""
import json
from pathlib import Path
from research.initial_geometry_assistance_v1.geometry import canonical, digest, check_grid
from research.initial_geometry_assistance_v1.live_io import sha
from research.feedback_probe_v1.source_closure import safe_member

MODEL='Qwen/Qwen3-VL-30B-A3B-Instruct-FP8'
MAX_PROMPT_TOKENS=8192
ACTION_CAP=6

def protocol():
    return json.loads(Path(__file__).with_name('live_protocol.json').read_bytes())

def verify_inputs(root,pin):
    root=Path(root)
    manifest=json.loads(safe_member(root,'manifest.json').read_bytes())
    if sha(root/'manifest.json')!=pin or set(manifest)!= {'schema','protocol_sha256','files'}:
        raise ValueError('external inference-input pin differs')
    frozen=protocol()
    if (manifest['schema']!='ls20_six_move_inputs_v1' or
        manifest['protocol_sha256']!=sha(Path(__file__).with_name('live_protocol.json')) or
        set(manifest['files'])!={'instructions.txt','initial.json'} or
        {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()} != {'manifest.json','instructions.txt','initial.json'}):
        raise ValueError('input inventory differs; only the frozen initial board and route instruction are allowed')
    for name,pin in manifest['files'].items():
        if sha(safe_member(root,name))!=pin: raise ValueError('frozen input changed: '+name)
    instructions=(root/'instructions.txt').read_text(encoding='utf-8')
    initial=json.loads((root/'initial.json').read_bytes())
    check_grid(initial['grid'])
    if (set(initial)!={'grid','legal_actions','state','levels_completed'} or initial['legal_actions']!=[1,2,3,4] or
        initial['state']!='NOT_FINISHED' or initial['levels_completed']!=0 or
        digest(initial)!=frozen['initial_observation_sha256'] or
        sha(root/'instructions.txt')!=frozen['instructions_sha256'] or not instructions.strip()):
        raise ValueError('fixed level-1 board or instruction identity differs')
    return manifest
