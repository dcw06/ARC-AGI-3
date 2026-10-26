"""Read Mac M1 raw records without importing its extractor or a game solver."""
import copy
import hashlib
import json
import math
import re

from research.action_effect_v1.records import check_grid, effect_record

VERSION = 'ls20_windows_w1_v1'
LABELS = ('no_visible_change', 'visible_change', 'transient_change', 'dimensions_changed')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def normalize_observation(value):
    require(type(value) is dict, 'observation must be a dict')
    allowed = {'grid', 'frames', 'state', 'levels_completed', 'legal_actions', 'full_reset'}
    require(not set(value) - allowed and ('grid' in value) != ('frames' in value),
            'use exactly grid or frames and public observation fields')
    frames = value.get('frames', [value.get('grid')])
    require(type(frames) is list and bool(frames), 'nonempty frames required')
    for frame in frames:
        check_grid(frame)
    require(type(value.get('state')) is str and bool(value['state']), 'state required')
    require(type(value.get('levels_completed')) is int and value['levels_completed'] >= 0,
            'nonnegative completion counter required')
    legal = value.get('legal_actions')
    require(type(legal) is list and all(type(a) is int and 1 <= a <= 7 for a in legal)
            and len(set(legal)) == len(legal), 'unique legal action IDs required')
    require(type(value.get('full_reset', False)) is bool, 'full_reset must be boolean')
    return copy.deepcopy(dict(frames=frames, state=value['state'],
        levels_completed=value['levels_completed'], legal_actions=sorted(legal),
        full_reset=value.get('full_reset', False)))


def validate_action(action, legal_actions):
    require(type(action) is dict and set(action) == {'action_id', 'action_data'},
            'use exactly action_id/action_data')
    ident, data = action['action_id'], action['action_data']
    require(type(ident) is int and ident in legal_actions and 1 <= ident <= 7,
            'action is not a legal non-reset control')
    require(type(data) is dict, 'action_data must be a dict')
    if ident == 6:
        require(set(data) == {'x', 'y'} and all(type(v) is int and 0 <= v <= 63
                for v in data.values()), 'ACTION6 requires integer x/y in [0,63]')
    else:
        require(not data, 'only ACTION6 takes coordinates')
    return copy.deepcopy(action)


def normalize_outcome(outcome):
    require(type(outcome) is dict, 'outcome must be a dict')
    fields = {'acknowledged': {'status', 'post'}, 'dispatch_failed': {'status', 'error'},
              'outcome_unknown': {'status', 'reason'}}
    status = outcome.get('status')
    require(status in fields and set(outcome) == fields[status], 'invalid outcome fields')
    result = copy.deepcopy(outcome)
    if status == 'acknowledged':
        result['post'] = normalize_observation(result['post'])
    else:
        text = result['error' if status == 'dispatch_failed' else 'reason']
        require(type(text) is str and bool(text), 'nonempty outcome detail required')
    return result


def effect_label(pre, post):
    """Visible appearance only. Never equates no change with a blocked movement."""
    before = pre['frames'][-1]
    frames = post['frames']
    if any((len(f), len(f[0])) != (len(before), len(before[0])) for f in frames):
        return 'dimensions_changed'
    changed = [frame != before for frame in frames]
    if any(changed) and not changed[-1]:
        return 'transient_change'
    return 'visible_change' if any(changed) else 'no_visible_change'


class M1View:
    """Replay factual records; derived regions/roles are forwarded, not endorsed.

    SHA256 is an integrity check, not proof of source authenticity. Source commit
    is required because the two reviewed M1 algorithms share a version string.
    """
    def __init__(self, snapshot, producer_commit):
        require(type(producer_commit) is str and re.fullmatch('[0-9a-f]{40}', producer_commit),
                'full M1 producer commit required')
        require(type(snapshot) is dict and snapshot.get('version') == 'ls20_discovery_mac_m1_v1',
                'unsupported M1 version')
        self.snapshot = copy.deepcopy(snapshot)
        self.producer_commit = producer_commit
        self.episode_id = snapshot.get('episode_id')
        require(type(self.episode_id) is str and bool(self.episode_id), 'episode ID required')
        require(type(snapshot.get('transitions')) is list and
                type(snapshot.get('observations')) is list, 'raw history required')
        for name in ('scenes', 'identity_candidates', 'events', 'hypotheses'):
            require(type(snapshot.get(name)) is list, 'M1 memory field missing: ' + name)
        self.current = normalize_observation(snapshot['initial'])
        self.segment, self.suspended, self.history = 0, False, []
        expected = []

        def ingest(observation, transition_id):
            for frame in observation['frames']:
                expected.append(dict(id=f'o{len(expected)}', kind='raw_observation',
                    segment=self.segment, transition_id=transition_id,
                    grid=copy.deepcopy(frame), sha256=digest(frame)))

        ingest(self.current, None)
        for index, transition in enumerate(snapshot['transitions']):
            require(not self.suspended, 'history continues after unknown outcome')
            ident = f't{index}'
            require(transition['id'] == ident and transition['episode_id'] == self.episode_id
                    and type(transition['segment']) is int and transition['segment'] == self.segment,
                    'transition identity/segment mismatch')
            require(transition['before_sha256'] == digest(self.current) and
                    transition['before_observation_id'] == expected[-1]['id'], 'before binding mismatch')
            elapsed = transition['elapsed_seconds']
            require(type(elapsed) in (float, int) and math.isfinite(elapsed) and elapsed >= 0,
                    'finite nonnegative timing required')
            action = validate_action(transition['action'], self.current['legal_actions'])
            outcome = normalize_outcome(transition['outcome'])
            require(digest(transition['effect']) == digest(effect_record(self.current, action, outcome)),
                    'effect record does not reconstruct')
            pre = self.current
            record = dict(id=ident, episode_id=self.episode_id, segment=self.segment,
                          action=action, pre=copy.deepcopy(pre), outcome=outcome, label=None)
            if outcome['status'] == 'acknowledged':
                post = outcome['post']
                require(transition['after_sha256'] == digest(post), 'after hash mismatch')
                boundary = post['full_reset'] or post['levels_completed'] != pre['levels_completed']
                if boundary:
                    self.segment += 1
                ingest(post, ident)
                require(transition['after_observation_id'] == expected[-1]['id'], 'after ID mismatch')
                # A level/reset boundary cannot support an old spatial mechanic.
                record.update(label=None if boundary else effect_label(pre, post), boundary=boundary)
                self.current = post
            else:
                require(transition['after_sha256'] is None and
                        transition['after_observation_id'] is None, 'unobserved outcome has an after state')
                self.suspended = outcome['status'] == 'outcome_unknown'
            self.history.append(record)
        require(digest(snapshot['observations']) == digest(expected),
                'raw observation history does not reconstruct')
        require(type(snapshot.get('suspended')) is bool and snapshot['suspended'] == self.suspended,
                'suspended flag mismatch')
        self.latest_observation_id = expected[-1]['id']

    def context(self):
        return dict(episode_id=self.episode_id, segment=self.segment,
            next_step=len(self.history), before_observation_id=self.latest_observation_id,
            before_sha256=digest(self.current), before_frame_sha256=digest(self.current['frames'][-1]),
            legal_actions=list(self.current['legal_actions']), suspended=self.suspended)
