"""Level-local encounter identities and cross-level appearance knowledge.

Only record_encounter creates an encounter. Merely seeing an object, failing to
route to it, or seeing the same appearance on another level does not visit it.
The caller verifies actual contact from retained before/after observations; this
module preserves that receipt and never infers a game function from contact.
"""
from copy import deepcopy
import json
import math
import re

from .objects import KINDS, instance_id

_HASH = re.compile(r'[0-9a-f]{64}\Z')
_OBJECT_FIELDS = {'id', 'appearance_sha256', 'kind', 'bbox', 'cells', 'center', 'targetability'}
_RECORD_FIELDS = _OBJECT_FIELDS | {'last_seen_sha256', 'visible', 'encounter_count'}


def _sha(value):
    if type(value) is not str or _HASH.fullmatch(value) is None:
        raise ValueError('lowercase SHA256 required')
    return value


def _level(value):
    if type(value) is not str or not value.strip() or len(value) > 256:
        raise ValueError('nonempty bounded level identity required')
    return value


def _json(value):
    # Round-trip protects memory from mutable caller values and non-JSON objects.
    try:
        return json.loads(json.dumps(value, sort_keys=True, allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise ValueError('finite JSON receipt required') from exc


def _checked_object(obj, *, record=False):
    fields = _RECORD_FIELDS if record else _OBJECT_FIELDS
    if type(obj) is not dict or set(obj) != fields:
        raise ValueError('unexpected object fields')
    if obj['kind'] not in KINDS:
        raise ValueError('unknown object kind')
    bbox, cells, center = obj['bbox'], obj['cells'], obj['center']
    last_row = 63 if obj['kind'] == 'reference' else 59
    if (type(bbox) is not list or len(bbox) != 4 or
            any(type(v) is not int for v in bbox) or
            not (0 <= bbox[0] <= bbox[2] < 64 and 0 <= bbox[1] <= bbox[3] <= last_row)):
        raise ValueError('native object bounds required')
    if obj['id'] != instance_id(obj['kind'], bbox):
        raise ValueError('object identity does not match kind and bounds')
    _sha(obj['appearance_sha256'])
    if type(cells) is not list or not cells:
        raise ValueError('visible occupied cells required')
    if any(type(p) is not list or len(p) != 2 or
           any(type(v) is not int for v in p) or
           not (bbox[0] <= p[0] <= bbox[2] and bbox[1] <= p[1] <= bbox[3])
           for p in cells):
        raise ValueError('native occupied object cells required')
    canonical = sorted(set(map(tuple, cells)), key=lambda p: (p[1], p[0]))
    if cells != [list(p) for p in canonical]:
        raise ValueError('object cells must be unique and row ordered')
    xs, ys = zip(*canonical)
    if bbox != [min(xs), min(ys), max(xs), max(ys)]:
        raise ValueError('object bounds do not enclose exactly its cells')
    if (type(center) is not list or len(center) != 2 or
            any(type(v) not in (int, float) or not math.isfinite(v) for v in center) or
            not (bbox[0] <= center[0] <= bbox[2] and bbox[1] <= center[1] <= bbox[3])):
        raise ValueError('finite object center within bounds required')
    if type(obj['targetability']) is not bool:
        raise ValueError('targetability must be a boolean')
    if obj['kind'] == 'reference' and obj['targetability']:
        raise ValueError('reference display cannot be a navigation target')
    if record:
        _sha(obj['last_seen_sha256'])
        if type(obj['visible']) is not bool or type(obj['encounter_count']) is not int or obj['encounter_count'] < 0:
            raise ValueError('invalid encounter record')
    return deepcopy(obj)


def _contained(inner, outer):
    return (outer[0] <= inner[0] <= inner[2] <= outer[2] and
            outer[1] <= inner[1] <= inner[3] <= outer[3])


class EncounterMemory:
    def __init__(self):
        self._levels = {}
        self._events = []
        self._knowledge = {}

    def observe(self, level_key, objects, observation_sha256):
        """Update visible inventory; retain absent instances without marking visits.

        A visible unknown fragment contained in an already known object is not
        a separately discovered object. More ambiguous changed bounds remain
        separate proposals rather than silently claiming identity.
        """
        _level(level_key)
        _sha(observation_sha256)
        if type(objects) is not list:
            raise ValueError('object list required')
        incoming = [_checked_object(obj) for obj in objects]
        if len({obj['id'] for obj in incoming}) != len(incoming):
            raise ValueError('duplicate object identity')
        state = self._levels.setdefault(level_key, dict(objects={}, contacts=[]))
        for old in state['objects'].values():
            old['visible'] = False
        # Specific recognized objects take precedence over component fragments.
        bounds = [obj['bbox'] for obj in incoming if obj['kind'] != 'unknown']
        bounds += [obj['bbox'] for obj in state['objects'].values() if obj['kind'] != 'unknown']
        known_unknowns = [obj for obj in state['objects'].values() if obj['kind'] == 'unknown']
        for obj in incoming:
            if obj['kind'] == 'unknown' and any(_contained(obj['bbox'], b) for b in bounds):
                continue
            if obj['kind'] == 'unknown' and any(
                    obj['id'] != old['id'] and
                    set(map(tuple, obj['cells'])) < set(map(tuple, old['cells']))
                    for old in known_unknowns):
                # A partial visible subset preserves the original instance. A
                # new mark inside a ring's empty hole is not such a subset.
                continue
            previous = state['objects'].get(obj['id'])
            state['objects'][obj['id']] = dict(obj,
                last_seen_sha256=observation_sha256, visible=True,
                encounter_count=previous['encounter_count'] if previous else 0)
        return self.objects(level_key)

    def objects(self, level_key):
        _level(level_key)
        state = self._levels.get(level_key, {'objects': {}})
        return [deepcopy(state['objects'][key]) for key in sorted(state['objects'])]

    def priorities(self, level_key, candidates=None):
        """Never-contacted targetable instances first; routing is caller-owned."""
        rows = self.objects(level_key)
        if candidates is not None:
            if type(candidates) is not list:
                raise ValueError('candidate IDs or object records required')
            ids = {obj if type(obj) is str else obj['id'] for obj in candidates}
            if not ids <= {obj['id'] for obj in rows}:
                raise ValueError('candidate absent from observed memory')
            rows = [obj for obj in rows if obj['id'] in ids]
        return sorted((obj for obj in rows if obj['targetability']),
                      key=lambda obj: (obj['encounter_count'] > 0,
                                       obj['encounter_count'], obj['id']))

    def record_encounter(self, level_key, object_id, before_sha256, after_sha256,
                         *, overlaps=True, pattern_changes=None, floor_changes=None):
        """Record caller-verified actual contact, once until release.

        The hashes identify the raw observations. Supplied effect descriptions
        are preserved as observations, not learned causal/game-rule labels.
        overlaps=False releases contact and records nothing.
        """
        _level(level_key)
        _sha(before_sha256)
        _sha(after_sha256)
        if type(overlaps) is not bool:
            raise ValueError('actual contact flag must be boolean')
        if type(object_id) is not str:
            raise ValueError('observed object identity required')
        state = self._levels.get(level_key)
        if state is None or object_id not in state['objects']:
            raise ValueError('cannot encounter an unobserved instance')
        if not overlaps:
            self.release(level_key, object_id)
            return None
        changes = _json(dict(pattern_changes=pattern_changes, floor_changes=floor_changes))
        if object_id in state['contacts']:
            return None
        obj = state['objects'][object_id]
        event = dict(index=len(self._events), level_key=level_key, object_id=object_id,
                     appearance_sha256=obj['appearance_sha256'],
                     before_sha256=before_sha256, after_sha256=after_sha256, **changes)
        self._events.append(event)
        obj['encounter_count'] += 1
        state['contacts'] = sorted(state['contacts']+[object_id])
        knowledge = self._knowledge.setdefault(obj['appearance_sha256'], dict(encounters=0, kinds=[]))
        knowledge['encounters'] += 1
        knowledge['kinds'] = sorted(set(knowledge['kinds']+[obj['kind']]))
        return deepcopy(event)

    def release(self, level_key, object_id=None):
        _level(level_key)
        state = self._levels.get(level_key)
        if state is not None:
            state['contacts'] = [] if object_id is None else [key for key in state['contacts'] if key != object_id]

    @property
    def events(self):
        return deepcopy(self._events)

    @property
    def knowledge(self):
        return deepcopy(self._knowledge)

    def snapshot(self):
        return deepcopy(dict(version=1, levels=self._levels, events=self._events, knowledge=self._knowledge))

    @classmethod
    def from_snapshot(cls, value):
        """Restore only canonical, internally consistent encounter snapshots."""
        value = _json(value)
        if (type(value) is not dict or set(value) != {'version', 'levels', 'events', 'knowledge'} or
                type(value['version']) is not int or value['version'] != 1 or
                type(value['levels']) is not dict or type(value['events']) is not list or
                type(value['knowledge']) is not dict):
            raise ValueError('invalid encounter snapshot')
        memory = cls()
        for level_key, state in value['levels'].items():
            _level(level_key)
            if (type(state) is not dict or set(state) != {'objects', 'contacts'} or
                    type(state['objects']) is not dict or type(state['contacts']) is not list):
                raise ValueError('invalid level memory')
            for key, obj in state['objects'].items():
                _checked_object(obj, record=True)
                if key != obj['id']:
                    raise ValueError('object key mismatch')
            if (any(type(key) is not str or key not in state['objects'] for key in state['contacts']) or
                    state['contacts'] != sorted(set(state['contacts']))):
                raise ValueError('invalid contact latch')
            memory._levels[level_key] = deepcopy(state)
        counts, knowledge = {}, {}
        event_fields = {'index', 'level_key', 'object_id', 'appearance_sha256',
                        'before_sha256', 'after_sha256', 'pattern_changes', 'floor_changes'}
        for index, event in enumerate(value['events']):
            if (type(event) is not dict or set(event) != event_fields or
                    type(event['index']) is not int or event['index'] != index):
                raise ValueError('invalid encounter event')
            _level(event['level_key'])
            for field in ('appearance_sha256', 'before_sha256', 'after_sha256'):
                _sha(event[field])
            if type(event['object_id']) is not str:
                raise ValueError('event object identity required')
            state = memory._levels.get(event['level_key'])
            if state is None or event['object_id'] not in state['objects']:
                raise ValueError('event refers to absent instance')
            identity = (event['level_key'], event['object_id'])
            counts[identity] = counts.get(identity, 0)+1
            entry = knowledge.setdefault(event['appearance_sha256'], dict(encounters=0, kinds=[]))
            entry['encounters'] += 1
            kind = state['objects'][event['object_id']]['kind']
            entry['kinds'] = sorted(set(entry['kinds']+[kind]))
        for level_key, state in memory._levels.items():
            for key, obj in state['objects'].items():
                if obj['encounter_count'] != counts.get((level_key, key), 0):
                    raise ValueError('encounter count does not match event receipts')
            if any(counts.get((level_key, key), 0) == 0 for key in state['contacts']):
                raise ValueError('contact latch has no encounter receipt')
        if knowledge != value['knowledge']:
            raise ValueError('appearance knowledge does not match encounter receipts')
        memory._events = value['events']
        memory._knowledge = knowledge
        return memory
