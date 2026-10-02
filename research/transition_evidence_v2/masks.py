"""Frozen declared masks (declared_masks_v1). Only s5i5 has a declared region; every other game is unmasked.

`declared_mask(game_id)` returns the mask for a game, or None. A game is matched on its full id, so a different
build of a game never inherits another build's region. Using a mask in a prompt, a memory or a detector changes an
experiment: it must be named in that experiment's protocol and versioned there.
"""
import copy
import hashlib
import json
from pathlib import Path

from research.transition_evidence_v2 import transition as T

PATH = Path(__file__).with_name('declared_masks.json')
FROZEN_SHA256 = '670dab4ce86daf4b74ad1a4c8fe38bf754fe38cd18d91c608e23eb4aac0a5b35'


def load(check=True):
    data = PATH.read_bytes()
    if check and hashlib.sha256(data).hexdigest() != FROZEN_SHA256:
        raise ValueError('declared_masks.json differs from its frozen hash')
    table = json.loads(data)
    for name, entry in table['masks'].items():
        problems = T.mask_problems(entry['mask'])
        if problems:
            raise ValueError(f'declared mask {name}: ' + '; '.join(problems))
    return table


def declared_mask(game_id):
    for entry in load()['masks'].values():
        if entry['game_id'] == game_id:
            return copy.deepcopy(entry['mask'])
    return None
