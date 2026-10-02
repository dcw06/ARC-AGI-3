"""CPU-only archive diagnostic: the FROZEN detector as an observer over archived real development play (Track 3).

Source: the 144 transitions of action-effect-history v1 (12 episodes x 12 steps; development games ar25, s5i5,
wa30), opened only after the archive's SHA-256 matches its lock (reports/action_effect_history_v1_archive.json),
and each episode member only after its own locked hash matches. Raw transitions are rebuilt with the replay
script's own `verified_zip`/`raw_step` (scripts/replay_transition_evidence_v1.py), imported, not copied.

The detector runs unchanged: trigger_spec.json parameters and cooldown, detector.py, full-frame (unmasked)
fingerprints. No threshold is chosen or changed here, and these traces have no independent stagnation labels:
everything below is descriptive, never a validation.

Candidate categories, defined mechanically before the detector was run on these traces. "Segment" is the
transition_evidence segment (a reset, level change or terminal state starts a new one); only acknowledged steps
count; a failed dispatch is skipped and an unknown outcome or missing observation is never counted as no change.

Repeated-action patterns (each is checked per segment):
  M1 exact_repeat_no_change      the same (pre-frame fingerprint, exact dispatched action) acknowledged at least twice
                                 with visual effect no_observed_change;
  M2 same_action_no_change       the same exact dispatched action (id and coordinates) acknowledged at least twice
                                 with no_observed_change, whatever the pre-frame;
  M3 action_id_no_change_streak  at least 3 consecutive acknowledged steps with the same action id (coordinates may
                                 differ), each no_observed_change;
  M4 repeated_tiny_effect        at least 3 consecutive acknowledged steps with the identical action, each changing
                                 1..4 cells of the final frame (a small, ongoing visible change).
  A pattern "qualifies" at the step where its count first reaches the stated minimum. A candidate missed
  repeated-action episode is an episode in which some pattern qualifies and the detector fires (trigger or
  cooldown-suppressed firing) at no step from that qualifying step to the end of its segment.

Potential false interruption: a trigger at step t such that at least one of the last 3 acknowledged steps of the
segment up to and including t reached a final frame not seen earlier in the segment (ongoing observed change into new
states). This is a proxy: a new frame is not progress, and an unchanged frame is not stagnation.

The result file is written once; a second run refuses to overwrite it. Run:
  python -m research.stagnation_supervision_v1.archive_diagnostic
"""
import hashlib
import importlib.util
import json
from pathlib import Path

from research.stagnation_supervision_v1 import detector as D, thresholds as S
from research.transition_evidence_v1 import transition as T, vocabulary as V

VERSION = 'stagnation_supervision_v1_archive_diagnostic'
ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / 'reports/stagnation_supervision_v1_archive_diagnostic.json'
REPLAY = ROOT / 'scripts/replay_transition_evidence_v1.py'
SOURCE = 'offline_development_engine'
FROZEN_FILES = ('trigger_spec.json', 'detector.py', 'thresholds.py')
TINY_MAX = 4
RECENT = 3


def replay_module():
    spec = importlib.util.spec_from_file_location('replay_transition_evidence_v1', REPLAY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def episodes():
    """[(episode json, raws)] after the archive and every member hash match their lock."""
    replay = replay_module()
    lock, bundle = replay.verified_zip(replay.AEH_LOCK)
    out = []
    for name in sorted(n for n in lock['members'] if '/episodes/' in n and n.endswith('.json')):
        data = bundle.read(name)
        if hashlib.sha256(data).hexdigest() != lock['members'][name]['sha256']:
            raise ValueError('member hash mismatch: ' + name)
        episode = json.loads(data)
        raws = [replay.raw_step(episode['episode_id'], s,
                                replay.parse_action(episode['calls'][s['call_index']]['response']), SOURCE)
                for s in episode['steps']]
        out.append((episode, raws))
    return lock, out


def _step_facts(record):
    m = record['measurements']
    final = m['frames'][-1] if m['frames'] and m['frames'][-1]['valid'] else None
    changed = final['vs_pre']['changed_cells'] if final else None
    return {'action_index': record['identity']['action_index'], 'segment': record['segment'],
            'dispatch': record['dispatch']['status'], 'availability': record['observations']['availability']['status'],
            'action': record['action']['dispatched'], 'pre_frame': record['observations']['before_frames_sha256'][-1],
            'after_frame': final['sha256'] if final else None, 'visual_effect': m['visual_effect']['status'],
            'changed_cells': changed['value'] if changed and changed['status'] == 'measured' else None,
            'events': record['environment']['events'], 'progress': record['progress']['status'],
            'continuity': record['continuity']['status']}


def patterns(facts):
    """Every qualifying M1-M4 occurrence: (category, qualifying step, segment, steps involved)."""
    found = []
    by_segment = {}
    for f in facts:
        by_segment.setdefault(f['segment'], []).append(f)
    for segment, steps in by_segment.items():
        acked = [f for f in steps if f['dispatch'] == V.ACKNOWLEDGED and f['availability'] != V.MISSING]
        seen_m1, seen_m2 = {}, {}
        for f in acked:
            if f['visual_effect'] != V.NO_OBSERVED_CHANGE:
                continue
            key = json.dumps(f['action'], sort_keys=True)
            for table, name, k in ((seen_m1, 'M1_exact_repeat_no_change', (f['pre_frame'], key)),
                                   (seen_m2, 'M2_same_action_no_change', key)):
                table.setdefault(k, []).append(f['action_index'])
                if len(table[k]) == 2:
                    found.append({'category': name, 'qualifies_at': f['action_index'], 'segment': segment,
                                  'steps': list(table[k])})
        for name, same, ok in (
                ('M3_action_id_no_change_streak', lambda a, b: a['action']['action_id'] == b['action']['action_id'],
                 lambda f: f['visual_effect'] == V.NO_OBSERVED_CHANGE),
                ('M4_repeated_tiny_effect', lambda a, b: a['action'] == b['action'],
                 lambda f: f['changed_cells'] is not None and 1 <= f['changed_cells'] <= TINY_MAX
                 and f['visual_effect'] == V.FINAL_FRAME_DIFFERS)):
            run = []
            for f in acked:
                run = run + [f] if run and ok(f) and same(run[-1], f) else ([f] if ok(f) else [])
                if len(run) == 3:
                    found.append({'category': name, 'qualifies_at': f['action_index'], 'segment': segment,
                                  'steps': [g['action_index'] for g in run]})
    return found


def diagnose(lock, eps, spec):
    params, cooldown = spec['params'], spec['cooldown_actions']
    out_eps, totals = [], {}
    for episode, raws in eps:
        records = T.history(raws)
        stats = D.statistics(records)
        decisions = D.triggers(stats, params, cooldown)
        facts = [_step_facts(r) for r in records]
        firing_steps = [d['action_index'] for d in decisions if d['signals']]
        triggers = []
        for d in decisions:
            if not d['trigger']:
                continue
            t = d['action_index']
            f = facts[t]
            prior = [g for g in facts[:t + 1] if g['segment'] == f['segment']]
            seen, new_flags = set(), []
            for g in prior:
                seen.add(g['pre_frame'])
                new_flags.append(g['dispatch'] == V.ACKNOWLEDGED and g['after_frame'] is not None
                                 and g['after_frame'] not in seen)
                if g['after_frame']:
                    seen.add(g['after_frame'])
            acked = [flag for g, flag in zip(prior, new_flags) if g['dispatch'] == V.ACKNOWLEDGED]
            triggers.append({'episode': episode['episode_id'], 'game': episode['game_id'], 'step': t,
                             'timing': {'actions_into_episode': t + 1, 'segment': f['segment'],
                                        'steps_into_segment': len(prior)},
                             'signals': d['signals'],
                             'cited_evidence': sorted({i for s in d['signals'] for i in s['evidence']}),
                             'potential_false_interruption': any(acked[-RECENT:]),
                             'trace': [facts[i] for i in sorted({i for s in d['signals'] for i in s['evidence']})]})
        found = patterns(facts)
        missed = []
        for p in found:
            end = max(g['action_index'] for g in facts if g['segment'] == p['segment'])
            if not any(p['qualifies_at'] <= i <= end for i in firing_steps):
                missed.append({**p, 'trace': [facts[i] for i in p['steps']]})
        statuses = {}
        for f in facts:
            statuses[f['dispatch']] = statuses.get(f['dispatch'], 0) + 1
        out_eps.append({'episode': episode['episode_id'], 'game': episode['game_id'], 'arm': episode['arm'],
                        'block': episode['block'], 'steps': len(facts), 'dispatch_status': statuses,
                        'segments': len({f['segment'] for f in facts}),
                        'environment_events': sorted({e for f in facts for e in f['events']}),
                        'visual_effects': sorted({f['visual_effect'] for f in facts}),
                        'distinct_pre_frames': len({f['pre_frame'] for f in facts}),
                        'firing_steps': firing_steps, 'triggers': triggers, 'patterns': found,
                        'candidate_missed_patterns': missed, 'steps_detail': facts})
    games = {}
    for e in out_eps:
        g = games.setdefault(e['game'].split('-')[0], {'episodes': 0, 'steps': 0, 'triggers': 0,
                                                       'episodes_with_trigger': 0, 'firing_steps': 0,
                                                       'candidate_missed_repeated_action_episodes': 0,
                                                       'candidate_missed_patterns': 0,
                                                       'potential_false_interruptions': 0,
                                                       'patterns_by_category': {}, 'dispatch_status': {},
                                                       'environment_events': set(), 'distinct_pre_frames': 0})
        g['episodes'] += 1
        g['steps'] += e['steps']
        g['triggers'] += len(e['triggers'])
        g['episodes_with_trigger'] += bool(e['triggers'])
        g['firing_steps'] += len(e['firing_steps'])
        g['candidate_missed_repeated_action_episodes'] += bool(e['candidate_missed_patterns'])
        g['candidate_missed_patterns'] += len(e['candidate_missed_patterns'])
        g['potential_false_interruptions'] += sum(t['potential_false_interruption'] for t in e['triggers'])
        g['distinct_pre_frames'] += e['distinct_pre_frames']
        for p in e['patterns']:
            g['patterns_by_category'][p['category']] = g['patterns_by_category'].get(p['category'], 0) + 1
        for k, v in e['dispatch_status'].items():
            g['dispatch_status'][k] = g['dispatch_status'].get(k, 0) + v
        g['environment_events'] |= set(e['environment_events'])
    for g in games.values():
        g['environment_events'] = sorted(g['environment_events'])
    package = Path(__file__).parent
    return {'version': VERSION, 'archive': lock['archive'], 'archive_sha256': lock['archive_sha256'],
            'attempt_id': lock.get('attempt_id'),
            'frozen_files_sha256': {n: hashlib.sha256((package / n).read_bytes().replace(b'\r\n', b'\n')).hexdigest()
                                    for n in FROZEN_FILES},
            'params': spec['params'], 'cooldown_actions': spec['cooldown_actions'], 'view': 'full_frame_unmasked',
            'labels': 'none: these transitions have no independent stagnation labels; all categories are descriptive',
            'definitions': __doc__, 'transitions': sum(e['steps'] for e in out_eps), 'per_game': games,
            'episodes': out_eps}


def run():
    lock, eps = episodes()
    return diagnose(lock, eps, S.load())


def encode(result):
    return json.dumps(result, indent=1, sort_keys=True) + '\n'


if __name__ == '__main__':
    if RESULTS.exists():
        raise SystemExit('refusing to overwrite the write-once result: ' + str(RESULTS))
    result = run()
    RESULTS.write_text(encode(result), encoding='utf-8')
    for game, g in sorted(result['per_game'].items()):
        print(game, json.dumps(g))
