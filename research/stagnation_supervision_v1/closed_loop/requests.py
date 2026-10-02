"""Request enumeration for token audits (hand-written; CPU only; no model).

`enumerate_requests` runs the GPU-disabled closed loop over the frozen protocol on the offline development engine
with the scripted fake server, and returns every policy and reflection request the service received, tagged with
its game group, arm and episode. `maximal_reflection_request` adds a constructed upper-bound reflection request (12
evidence entries with the largest field values the protocol allows, both enabled signals citing full evidence and
the full available-action vocabulary), since a scripted rehearsal need not reach the largest request. A token audit
with the pinned tokenizer (scripts/audit_stagnation_supervision_v1_tokens.py) counts all of them.
"""
import copy
import hashlib
import json
from pathlib import Path
import tempfile

from research.stagnation_supervision_v1 import intervention as I, thresholds as S
from research.stagnation_supervision_v1.closed_loop import bridge as B, fake_server as F, runner as R, service as SVC


def _sha(request):
    return hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()


def enumerate_requests(*, groups=None, actions_per_episode=None, faults=()):
    """[{'kind', 'pair_id', 'game_id', 'arm', 'episode_id', 'request', 'request_sha256'}] for the protocol's game
    groups (all by default), as the CPU rehearsal sends them. `actions_per_episode` may be lowered for tests only."""
    from research.grounded_action_v1.engine import restore_game_mount
    from research.stagnation_supervision_v1.closed_loop.engine import DevelopmentAdapter
    spec = R.protocol()
    if groups is not None:
        spec = {**spec, 'schedule': [s for s in spec['schedule'] if s['pair_id'] in set(groups)]}
    if actions_per_episode is not None:
        spec = {**spec, 'limits': {**spec['limits'], 'actions_per_episode': actions_per_episode}}
    current, out = {}, []
    service = SVC.LocalService(F.FakeModelServer(faults))
    inner = service.complete

    def complete(request):
        out.append({'kind': SVC.kind(request), **current, 'request': copy.deepcopy(request),
                    'request_sha256': _sha(request)})
        return inner(request)
    service.complete = complete
    pairs = {s['pair_id']: s for s in spec['schedule']}
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        games = restore_game_mount(folder / 'games')

        def adapter(game_id, arm, episode_id):
            pair_id = episode_id[:-(len(arm) + 1)]
            current.update(pair_id=pair_id, game_id=game_id, arm=arm, episode_id=episode_id)
            assert pairs[pair_id]['game_id'] == game_id
            return DevelopmentAdapter(game_id, arm, episode_id, games, folder / 'rec')
        report = R.run(folder / 'run', service, adapter, spec=spec, deadline_seconds=10 ** 6,
                       supervision_factory=B.supervision_factory(spec, S.load(),
                                                                 token_counter=B.fixture_token_counter()))
    if report['status'] != 'complete':
        raise RuntimeError('enumeration rehearsal did not complete: ' + str(report['status']))
    return out


def maximal_reflection_request():
    """A constructed reflection request at least as large as any the protocol can produce (see module docstring)."""
    from research.transition_evidence_v2 import transition as T2
    frame = [[(x * 7 + y * 3) % 16 for x in range(64)] for y in range(64)]
    raws = []
    for i in range(40):
        after = copy.deepcopy(frame)
        after[i % 64][(i * 5) % 64] = (after[i % 64][(i * 5) % 64] + 1) % 16
        raws.append({'identity': {'episode_id': 'b2-ls20-continuation', 'action_index': i},
                     'before': {'frames': [frame], 'levels_completed': 0, 'state': 'NOT_FINISHED', 'full_reset': False,
                                'available_actions': list(range(8))},
                     'proposal': None, 'dispatched': {'action_id': 6, 'action_data': {'x': 63, 'y': 63}},
                     'environment_source': B.SOURCE,
                     'outcome': {'status': 'acknowledged', 'after': {
                         'frames': [after], 'levels_completed': 0, 'state': 'NOT_FINISHED', 'full_reset': False,
                         'available_actions': list(range(8))}}})
        frame = after
    records = T2.history(raws)
    signals = [{'signal': 'state_action_recurrence', 'value': 40, 'threshold': 2, 'evidence': [38, 39]},
               {'signal': 'tiny_effect_repeat', 'value': 40, 'threshold': 10, 'evidence': list(range(30, 40))}]
    request = I.build_request(records, 39, 'triggered', signals)
    return B.reflection_request(request['text'])
