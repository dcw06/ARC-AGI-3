"""Append-only evidence with deterministic reconstruction and explicit uncertainty."""
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile

from research.action_effect_v1.records import check_grid, effect_record
from .scene import extract_scene, identity_candidates

VERSION = 'ls20_discovery_mac_m1_v1'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def normalize_observation(observation):
    """Accept OfflineEngine snapshots or action_effect_v1 multi-frame observations."""
    if type(observation) is not dict:
        raise ValueError('observation must be a dict')
    allowed = {'grid', 'frames', 'state', 'levels_completed', 'legal_actions', 'full_reset'}
    if set(observation) - allowed or ('grid' in observation) == ('frames' in observation):
        raise ValueError('use exactly grid or frames; only public observation fields allowed')
    frames = observation.get('frames', [observation.get('grid')])
    if type(frames) is not list or not frames:
        raise ValueError('nonempty frame sequence required')
    for frame in frames:
        check_grid(frame)
    if type(observation.get('state')) is not str or not observation['state']:
        raise ValueError('state required')
    if type(observation.get('levels_completed')) is not int or observation['levels_completed'] < 0:
        raise ValueError('nonnegative completion counter required')
    legal = observation.get('legal_actions')
    if (type(legal) is not list or any(type(a) is not int or not 1 <= a <= 7 for a in legal)
            or len(set(legal)) != len(legal)):
        raise ValueError('legal action IDs required')
    if 'full_reset' in observation and type(observation['full_reset']) is not bool:
        raise ValueError('full_reset must be boolean')
    return copy.deepcopy(dict(frames=frames, state=observation['state'],
                              levels_completed=observation['levels_completed'],
                              legal_actions=sorted(legal), full_reset=observation.get('full_reset', False)))


class EvidenceMemory:
    """One episode. Accessors return copies; callers cannot rewrite retained evidence.

    A missing outcome suspends this episode (no guessed current state). Restart with
    a new episode after external recovery. No retention cap in this CPU milestone.
    """
    def __init__(self, episode_id, initial):
        if type(episode_id) is not str or not episode_id:
            raise ValueError('episode ID required')
        self._episode = episode_id
        self._initial = normalize_observation(initial)
        self._current = self._initial
        self._transitions, self._observations, self._scenes = [], [], []
        self._events, self._links, self._hypotheses = [], [], []
        self._segment = 0
        self._suspended = False
        self._ingest(self._initial, None, boundary=True)

    def _ingest(self, observation, transition_id, boundary=False):
        if boundary and self._observations:
            self._segment += 1
        for frame in observation['frames']:
            ident = f'o{len(self._observations)}'
            previous = self._observations[-1] if self._observations else None
            record = dict(id=ident, kind='raw_observation', segment=self._segment,
                          transition_id=transition_id, grid=copy.deepcopy(frame), sha256=digest(frame))
            scene = extract_scene(frame, ident)
            prior_scenes = [s for s, o in zip(self._scenes, self._observations)
                            if o['segment'] == self._segment and
                            (len(o['grid']), len(o['grid'][0])) == (len(frame), len(frame[0]))]
            links = identity_candidates(prior_scenes, scene)
            self._links.extend(links)
            if previous and previous['segment'] == self._segment:
                before = previous['grid']
                comparable = (len(before), len(before[0])) == (len(frame), len(frame[0]))
                changes = ([[r, c, before[r][c], frame[r][c]]
                            for r in range(len(frame)) for c in range(len(frame[0]))
                            if before[r][c] != frame[r][c]] if comparable else None)
                event = dict(id=f'e{len(self._events)}', kind='computed_change',
                             transition_id=transition_id, before=previous['id'], after=ident,
                             changes=changes, dimensions_changed=not comparable)
                self._events.append(event)
                # Association is not control, causation, or proof of persistent identity.
                for link in links:
                    if (transition_id is not None and link['before'].startswith(previous['id']+':')
                            and link['translation'] is not None and any(link['translation'])):
                        self._hypotheses.append(dict(id=f'h{len(self._hypotheses)}',
                            kind='role_hypothesis', role='possible_controlled_entity',
                            proposal_id=link['after'], evidence_ids=[event['id']],
                            status='tentative', alternatives=['autonomous_change', 'identity_mismatch'],
                            confidence_kind='uncalibrated_heuristic'))
            self._observations.append(record)
            self._scenes.append(scene)

    def append(self, action, outcome, *, elapsed_seconds=0.0):
        if self._suspended:
            raise ValueError('unknown outcome: recover outside this episode before continuing')
        if (type(elapsed_seconds) not in (float, int) or not math.isfinite(elapsed_seconds)
                or elapsed_seconds < 0):
            raise ValueError('finite nonnegative timing required')
        # Validate everything before touching retained state.
        if type(action) is not dict or set(action) != {'action_id', 'action_data'}:
            raise ValueError('use existing action_id/action_data contract')
        if type(action['action_id']) is not int or action['action_id'] not in self._current['legal_actions']:
            raise ValueError('action not legal in latest observation')
        if type(action['action_data']) is not dict:
            raise ValueError('action_data must be a dict')
        if any(type(k) is not str for k in action['action_data']):
            raise ValueError('action data keys must be strings')
        # Coordinates use the existing native x/y interface; no direction semantics supplied.
        data = action['action_data']
        if data and (set(data) != {'x', 'y'} or any(type(v) is not int or not 0 <= v <= 63 for v in data.values())):
            raise ValueError('action data must be empty or native x/y coordinates')
        if type(outcome) is not dict:
            raise ValueError('outcome must be a dict')
        outcome = copy.deepcopy(outcome)
        status = outcome.get('status')
        expected = {'acknowledged': {'status', 'post'}, 'dispatch_failed': {'status', 'error'},
                    'outcome_unknown': {'status', 'reason'}}
        if status not in expected or set(outcome) != expected[status]:
            raise ValueError('invalid outcome fields')
        if status == 'acknowledged':
            outcome['post'] = normalize_observation(outcome['post'])
        effect = effect_record(self._current, action, outcome)
        ident = f't{len(self._transitions)}'
        entry = dict(id=ident, episode_id=self._episode, segment=self._segment,
                     action=copy.deepcopy(action), outcome=outcome, elapsed_seconds=float(elapsed_seconds),
                     before_observation_id=self._observations[-1]['id'],
                     before_sha256=digest(self._current), after_sha256=None, effect=effect)
        if status == 'acknowledged':
            post = outcome['post']
            entry['after_sha256'] = digest(post)
            boundary = post['full_reset'] or post['levels_completed'] != self._current['levels_completed']
            # Same visible state/action can have different outcomes: retain both, not overwrite.
            conflicts = [t['id'] for t in self._transitions if t['segment'] == self._segment
                         and t['before_sha256'] == entry['before_sha256'] and t['action'] == action
                         and t['after_sha256'] is not None and t['after_sha256'] != entry['after_sha256']]
            if conflicts:
                self._events.append(dict(id=f'e{len(self._events)}', kind='context_dependent_outcome',
                                         transition_id=ident, conflicting_transition_ids=conflicts))
            self._ingest(post, ident, boundary=boundary)
            entry['after_observation_id'] = self._observations[-1]['id']
            self._current = post
        else:
            entry['after_observation_id'] = None
            self._suspended = status == 'outcome_unknown'
        self._transitions.append(entry)
        return copy.deepcopy(entry)

    def cell_history(self, row, column, *, segment=None):
        """Observed pixel values, NOT inferred floor beneath an occluder."""
        if any(type(v) is not int or v < 0 for v in (row, column)):
            raise ValueError('nonnegative integer coordinates required')
        return [dict(observation_id=o['id'], segment=o['segment'], color=o['grid'][row][column])
                for o in self._observations if (segment is None or o['segment'] == segment)
                and row < len(o['grid']) and column < len(o['grid'][0])]

    def snapshot(self):
        return copy.deepcopy(dict(version=VERSION, episode_id=self._episode, initial=self._initial,
            transitions=self._transitions, observations=self._observations, scenes=self._scenes,
            identity_candidates=self._links, events=self._events, hypotheses=self._hypotheses,
            suspended=self._suspended))

    def save(self, path):
        """Atomic snapshot; fsync before replacement. No partial file masquerades as evidence."""
        path = Path(path)
        payload = self.snapshot()
        raw = json.dumps(dict(payload=payload, sha256=digest(payload)), sort_keys=True, allow_nan=False)
        temp = None
        try:
            with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False, encoding='utf-8') as stream:
                temp = stream.name
                stream.write(raw + '\n')
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, path)
        finally:
            if temp is not None and os.path.exists(temp):
                os.unlink(temp)

    @classmethod
    def load(cls, path):
        envelope = json.loads(Path(path).read_text(encoding='utf-8'))
        if set(envelope) != {'payload', 'sha256'} or digest(envelope['payload']) != envelope['sha256']:
            raise ValueError('snapshot checksum mismatch')
        payload = envelope['payload']
        if payload.get('version') != VERSION:
            raise ValueError('unsupported memory version')
        memory = cls(payload['episode_id'], payload['initial'])
        for t in payload['transitions']:
            memory.append(t['action'], t['outcome'], elapsed_seconds=t['elapsed_seconds'])
        if memory.snapshot() != payload:
            raise ValueError('snapshot does not reconstruct from raw evidence')
        return memory
