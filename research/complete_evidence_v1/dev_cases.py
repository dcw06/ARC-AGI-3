"""Freeze the 20 development decisions (protocol Appendix D) from source records only.

Nothing here formats a record or counts a token. A case is a decision (the number of completed actions)
plus the earlier record or records whose content a reader would need. Types are assigned by fixed rules
from the saved frames, in this order of precedence, and are not yet reviewed by a person:

  level/reset   the earlier record is from an earlier level (2 cases) or an earlier attempt (2 cases)
  delayed       3 or more returned frames, and an intermediate frame differs from the last one
  conflicting   two records with the same action in the same level and attempt: one changed the board,
                the later one did nothing
  spatial       one returned frame whose change is mostly one shape moved to a new place
  ordinary      one returned frame, same level and attempt, none of the above

"Changed" and "did nothing" ignore the step counter, estimated as in audit_repeats_masked.py.
Games: only the seven already used for development (bp35, lf52, ls20 named in the protocol; tn36, cd82,
ka59, vc33 used in Phase 1), so that the other 18 games stay untouched for the reserved sample.
Every earlier record is at least 9 actions before its decision, outside what the saved agent could see.
Choices among eligible candidates are random with a fixed seed, spread across games.

Usage: dev_cases.py <events.jsonl> <out.json>
"""
import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from complete_evidence_v1 import records  # noqa: E402

GAMES = ('bp35', 'lf52', 'ls20', 'tn36', 'cd82', 'ka59', 'vc33')
TYPES = ('level/reset', 'delayed', 'conflicting', 'spatial', 'ordinary')
SEED, GAP, PER_TYPE = 20261114, 9, 4
ALREADY_USED = {('tn36', 12)}  # the frozen readability example


def counter_mask(recs, tick=2):
    shape = recs[0]['before_frame'].shape
    mask = np.zeros(shape, dtype=bool)
    for r in recs:
        final = r['response_frames'][-1]
        if final.shape == shape == r['before_frame'].shape:
            diff = final != r['before_frame']
            if 0 < diff.sum() <= tick:
                mask |= diff
    base = mask.copy()
    for line, wide in ((base, mask), (base.T, mask.T)):
        for i, cells in enumerate(line):
            hit = np.flatnonzero(cells)
            if hit.size >= 3:
                wide[i, hit[0]:hit[-1] + 1] = True
    return mask


def moved_share(before, after, mask):
    """Share of the changed cells explained by one shape shifted by up to 12 cells."""
    if before.shape != after.shape or before.shape != mask.shape:
        return 0.0
    changed = (before != after) & ~mask
    n = int(changed.sum())
    if n < 4 or n > 600:
        return 0.0
    ys, xs = np.nonzero(changed)
    best = 0
    for dy in range(-12, 13):
        for dx in range(-12, 13):
            if dy == 0 and dx == 0:
                continue
            yy, xx = ys + dy, xs + dx
            ok = (yy >= 0) & (yy < before.shape[0]) & (xx >= 0) & (xx < before.shape[1])
            hit = changed[yy[ok], xx[ok]] & (after[yy[ok], xx[ok]] == before[ys[ok], xs[ok]])
            best = max(best, int(hit.sum()))
    return best / n


def describe(recs, mask):
    out = []
    for r in recs:
        before, frames = r['before_frame'], r['response_frames']
        same_shape = all(f.shape == before.shape == mask.shape for f in frames)
        changed = (not same_shape) or bool(((frames[-1] != before) & ~mask).any())
        transient = same_shape and len(frames) >= 3 and any(((f != frames[-1]) & ~mask).any() for f in frames[:-1])
        out.append({'event': r['event_seq'], 'scope': (r['level_observed'], r['reset_id']), 'action': r['action'],
                    'frames': len(frames), 'changed': changed, 'transient': bool(transient),
                    'level_up': r['level_after'] > r['level_observed'], 'reset': r['action']['id'] == 'RESET',
                    'moved': moved_share(before, frames[-1], mask) if len(frames) == 1 and same_shape else 0.0})
    return out


def candidates(game, recs, info):
    """Per type: [(decision candidates, [earlier events], note)]. A decision d means d completed actions."""
    n = len(recs)
    scope_at = {d: (recs[d - 1]['level_after'], recs[d - 1]['reset_id']) for d in range(1, n + 1)}
    plain = [i for i in info if not i['reset'] and not i['level_up'] and (game, i['event']) not in ALREADY_USED]
    out = {t: [] for t in TYPES}

    def later(event, same_scope=None, level_after=None, attempt_after=None):
        ds = []
        for d in range(event + GAP, n + 1):
            level, reset = scope_at[d]
            if same_scope is not None and (level, reset) == same_scope:
                ds.append(d)
            if level_after is not None and level > level_after:
                ds.append(d)
            if attempt_after is not None and level == attempt_after[0] and reset > attempt_after[1]:
                ds.append(d)
        return ds
    for i in plain:
        level, reset = i['scope']
        for kind, ds in (('earlier level', later(i['event'], level_after=level)),
                         ('earlier attempt', later(i['event'], attempt_after=(level, reset)))):
            if ds and i['changed'] and i['frames'] == 1:
                out['level/reset'].append((ds, [i['event']], kind))
        same = later(i['event'], same_scope=i['scope'])
        if not same:
            continue
        if i['transient']:
            out['delayed'].append((same, [i['event']], '%d frames with a transient state' % i['frames']))
        elif i['frames'] == 1 and i['changed'] and i['moved'] >= 0.3:
            out['spatial'].append((same, [i['event']], 'moved share %.2f' % i['moved']))
        elif i['frames'] == 1:
            out['ordinary'].append((same, [i['event']], 'changed' if i['changed'] else 'did nothing'))
        if not i['changed'] and i['frames'] == 1:
            key = (i['action']['id'], i['action']['x'], i['action']['y']) if i['action']['x'] is not None else (i['action']['id'],)
            earlier = [j for j in plain if j['event'] < i['event'] and j['scope'] == i['scope'] and j['changed'] and j['frames'] == 1
                       and ((j['action']['id'], j['action']['x'], j['action']['y']) if j['action']['x'] is not None else (j['action']['id'],)) == key]
            if earlier:
                out['conflicting'].append((same, [earlier[-1]['event'], i['event']], 'same action: changed, then did nothing'))
    return out


def main(events_path, out_path):
    games = {k.split('-')[0]: v for k, v in records.load_run(events_path).items()}
    rng = random.Random(SEED)
    pool, facts = {}, {}
    for game in GAMES:
        recs = games[game]['records']
        mask = counter_mask(recs)
        info = describe(recs, mask)
        pool[game] = candidates(game, recs, info)
        facts[game] = {'records': len(recs), 'counter_cells_estimated': int(mask.sum()),
                       'candidates': {t: len(pool[game][t]) for t in TYPES}}
    used, cases, count = set(), [], {g: 0 for g in GAMES}
    for kind in TYPES:
        wanted = ['earlier level', 'earlier level', 'earlier attempt', 'earlier attempt'] if kind == 'level/reset' else [None] * PER_TYPE
        games_used = []
        for want in wanted:
            options = {g: [c for c in pool[g][kind] if (want is None or c[2] == want) and not any((g, e) in used for e in c[1])]
                       for g in GAMES}
            eligible = [g for g in GAMES if options[g]]
            if not eligible:
                cases.append({'type': kind, 'unfilled': True, 'wanted': want, 'reason': 'no eligible candidate in the seven games'})
                continue
            # spread: games not yet used for this type first, then games with fewest cases overall, then random
            order = sorted(eligible, key=lambda g: (games_used.count(g), count[g], rng.random()))
            game = order[0]
            decisions, events, note = rng.choice(options[game])
            decision = rng.choice(decisions)
            recs = games[game]['records']
            current = recs[decision - 1]['response_frames'][-1]
            used.update((game, e) for e in events)
            games_used.append(game)
            count[game] += 1
            earlier = []
            for e in events:
                r = recs[e - 1]
                same_shape = r['before_frame'].shape == current.shape
                earlier.append({'event': e, 'action': r['action'], 'frames_returned': len(r['response_frames']),
                                'level': r['level_observed'], 'reset': r['reset_id'],
                                'cells_differing_from_current_board': int((r['before_frame'] != current).sum()) if same_shape else None,
                                'share_of_board_differing': round(float((r['before_frame'] != current).mean()), 3) if same_shape else None})
            cases.append({'type': kind, 'game': game, 'decision_after_actions': decision,
                          'current_level': recs[decision - 1]['level_after'], 'current_reset': recs[decision - 1]['reset_id'],
                          'current_board_observation': 'o%d' % decision,
                          'current_board_cells_sha256': hashlib.sha256(current.tobytes()).hexdigest(),
                          'earlier_records': earlier, 'rule_note': note})
    for number, case in enumerate(cases, 1):
        case['case'] = 'D%02d' % number
    frozen = {'protocol': 'revision 11, Appendix D', 'frozen_before_any_format_output': True, 'seed': SEED,
              'source_run': str(events_path).split('/')[-2], 'games': GAMES, 'minimum_gap_actions': GAP,
              'types_assigned_by_rule_not_yet_reviewed': True, 'candidate_counts': facts, 'cases': cases}
    Path(out_path).write_text(json.dumps(frozen, indent=1))
    print(json.dumps(facts, indent=0))
    for c in cases:
        if c.get('unfilled'):
            print(c['case'], c['type'], 'UNFILLED', c['wanted'])
            continue
        print(c['case'], c['type'], c['game'], 'decision', c['decision_after_actions'], 'earlier',
              [(e['event'], e['frames_returned'], e['share_of_board_differing']) for e in c['earlier_records']], '|', c['rule_note'])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
