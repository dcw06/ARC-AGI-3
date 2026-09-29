"""Offline replay of approved archived trajectories through transition_evidence_v1 (Workstream 3, step 6).

Sources, each opened only after its archive hash matches its lock:
- action-effect-history v1 (reports/action_effect_history_v1_archive.json): 12 episodes of development-engine play;
- Stage B R8 (reports/perception_stage_b_r8_archive.json): 2 episodes with model predictions and self-assessments.

For every dispatched step the replay rebuilds the transition from raw retained evidence (before/after observations,
dispatched action, dispatch status) and compares:
- previously recorded effects (action_effect_record_v1) with the recomputed measurements;
- model statements (R8 predictions, self-assessments and their frame-change claims) with computed facts;
- available environment progress signals.
Every statement is classified as directly observed, mechanically computed, human annotation or model hypothesis.
Archives are never rewritten; the report is written once (append-only: a second run refuses to overwrite).
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.transition_evidence_v1 import transition as T, vocabulary as V  # noqa: E402

REPORT = ROOT / 'reports/ws3_transition_replay_v1.json'
GALLERY = ROOT / 'reports/ws3_transition_replay_v1'
AEH_LOCK = ROOT / 'reports/action_effect_history_v1_archive.json'
R8_LOCK = ROOT / 'reports/perception_stage_b_r8_archive.json'
R8_TRAJECTORY = 'reports/runs/phase4-grounded-action-v1-r8/download/phase4-grounded-action-v1/worker/trajectory.json'


def verified_zip(lock_path):
    lock = json.loads(lock_path.read_bytes())
    path = ROOT / lock['archive']
    if hashlib.sha256(path.read_bytes()).hexdigest() != lock['archive_sha256']:
        raise ValueError('archive hash mismatch: ' + lock['archive'])
    return lock, zipfile.ZipFile(path)


def parse_action(response):
    try:
        value = json.loads(response)
        action = value.get('action', value)
        return {'action_id': action['action_id'], 'action_data': action.get('action_data', {})}
    except Exception:
        return {'unparsed': (response or '')[:200]}


def raw_step(episode_id, step, proposal, source):
    outcome = ({'status': 'acknowledged', 'after': step['after']} if step['status'] == 'acknowledged' else
               {'status': 'failed' if step['status'] == 'dispatch_failed' else 'outcome_unknown',
                'reason': step.get('error') or step['status']})
    return {'identity': {'episode_id': episode_id, 'action_index': step['index']}, 'before': step['before'],
            'proposal': proposal, 'dispatched': step['action'], 'outcome': outcome, 'environment_source': source}


def recorded_vs_recomputed(recorded, record):
    """Field-by-field agreement with action_effect_record_v1 (reference: the last pre-action frame, as v1)."""
    m = record['measurements']
    counts = [f['vs_pre']['changed_cells']['value'] if f['valid'] and f['vs_pre']['changed_cells']['status'] == 'measured'
              else None for f in m['frames']]
    any_changed = m['any_returned_frame_differs'].get('value')
    final_changed = None if m['final_frame_equals_pre']['status'] != 'measured' else not m['final_frame_equals_pre']['value']
    reported = record['environment']['reported'] or {}
    mine = {'changed_cells_by_frame': counts, 'any_frame_changed': any_changed, 'final_frame_changed': final_changed,
            'returned_to_pre_frame': m['visual_effect']['status'] == V.CHANGED_THEN_RETURNED,
            'level_delta': (reported.get('levels_completed_after', 0) - reported.get('levels_completed_before', 0)),
            'reset': reported.get('full_reset_after') is True}
    return {k: {'recorded': recorded.get(k), 'recomputed': v} for k, v in mine.items() if recorded.get(k) != v}


def replay():
    rows, statements, disagreements = [], [], []
    lock, bundle = verified_zip(AEH_LOCK)
    episodes = sorted(n for n in lock['members'] if '/episodes/' in n and n.endswith('.json'))
    for name in episodes:
        raw_bytes = bundle.read(name)
        if hashlib.sha256(raw_bytes).hexdigest() != lock['members'][name]['sha256']:
            raise ValueError('member hash mismatch: ' + name)
        episode = json.loads(raw_bytes)
        raws = [raw_step(episode['episode_id'], s, parse_action(episode['calls'][s['call_index']]['response']),
                         'offline_development_engine') for s in episode['steps']]
        for s, raw, record in zip(episode['steps'], raws, T.history(raws)):
            diff = recorded_vs_recomputed(s['effect_record'], record)
            if diff:
                disagreements.append({'source': 'action_effect_history_v1', 'episode': episode['episode_id'],
                                      'index': s['index'], 'fields': diff})
            rows.append(summary('action_effect_history_v1', episode['episode_id'], s['index'], record, raw))
    lock, bundle = verified_zip(R8_LOCK)
    raw_bytes = bundle.read(R8_TRAJECTORY)
    if hashlib.sha256(raw_bytes).hexdigest() != lock['members'][R8_TRAJECTORY]['sha256']:
        raise ValueError('R8 trajectory hash mismatch')
    trajectory = json.loads(raw_bytes)
    for n, episode in enumerate(trajectory['episodes']):
        episode_id = f"r8-{episode['arm']}-{n}"
        raws = [raw_step(episode_id, s, parse_action(episode['calls'][s['decision_call']]['response']),
                         trajectory['kind']) for s in episode['steps']]
        for s, raw, record in zip(episode['steps'], raws, T.history(raws)):
            rows.append(summary('perception_stage_b_r8', episode_id, s['index'], record, raw))
            statements += model_checks(episode_id, s, record, episode['calls'])
    return rows, statements, disagreements


def summary(source, episode, index, record, raw):
    m = record['measurements']
    return {'source': source, 'episode': episode, 'index': index,
            'observed': {'dispatch': record['dispatch']['status'], 'dispatched': record['action']['dispatched'],
                         'returned_frames': m['returned_frame_count'].get('value'),
                         'environment': record['environment']['reported']},
            'computed': {'availability': record['observations']['availability']['status'],
                         'visual_effect': m['visual_effect']['status'],
                         'changed_cells_vs_pre': [f['vs_pre']['changed_cells'].get('value') for f in m['frames'] if f['valid']],
                         'environment_events': record['environment']['events'], 'progress': record['progress']['status'],
                         'segment': record['segment'], 'continuity': record['continuity']['status'],
                         'proposal_equals_dispatched': record['action']['proposal_equals_dispatched']},
            'human_annotation': None}


def model_checks(episode_id, step, record, calls):
    """R8 model statements, kept as hypotheses and checked against computed facts."""
    m = record['measurements']
    differs = m['any_returned_frame_differs']
    fact = differs['value'] if differs['status'] == 'measured' else None
    out = []
    prediction = step.get('prediction') or {}
    if prediction.get('prediction') in ('change', 'no_change'):
        claim = prediction['prediction'] == 'change'
        out.append({'episode': episode_id, 'index': step['index'], 'kind': 'prediction', 'statement': prediction,
                    'status': 'hypothesis', 'computed_any_returned_frame_differs': fact,
                    'agrees_with_computed': None if fact is None else claim == fact})
    feedback_call = step.get('feedback_call')
    if feedback_call is not None:
        try:
            said = json.loads(calls[feedback_call]['response'])
        except Exception:
            said = {'unparsed': calls[feedback_call]['response'][:200]}
        frame0 = m['frames'][0]['vs_pre']['differs'].get('value') if m['frames'] and m['frames'][0]['valid'] else None
        out.append({'episode': episode_id, 'index': step['index'], 'kind': 'self_assessment_frame_claim',
                    'statement': said, 'status': 'hypothesis', 'computed_frame_0_differs': frame0,
                    'agrees_with_computed': (None if frame0 is None or 'frame_0_changed' not in said
                                             else said['frame_0_changed'] == frame0)})
        if said.get('assessment') in ('supported', 'contradicted') and prediction.get('prediction') in ('change', 'no_change') \
                and fact is not None:
            correct = ('supported' if (prediction['prediction'] == 'change') == fact else 'contradicted')
            out.append({'episode': episode_id, 'index': step['index'], 'kind': 'self_assessment_verdict',
                        'statement': {'assessment': said['assessment']}, 'status': 'hypothesis',
                        'computed_verdict': correct, 'agrees_with_computed': said['assessment'] == correct})
    return out


def gallery(rows, statements):
    """A few annotated renders: before frame, final returned frame, changed cells outlined."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    palette = ListedColormap(['#000000', '#0074D9', '#FF4136', '#2ECC40', '#FFDC00', '#AAAAAA', '#F012BE', '#FF851B',
                              '#7FDBFF', '#870C25', '#FFFFFF', '#39CCCC', '#01FF70', '#85144b', '#B10DC9', '#3D9970'])
    lock, bundle = verified_zip(R8_LOCK)
    trajectory = json.loads(bundle.read(R8_TRAJECTORY))
    lock_a, bundle_a = verified_zip(AEH_LOCK)
    chosen = []
    for n, episode in enumerate(trajectory['episodes']):
        for s in episode['steps']:
            chosen.append((f"r8-{episode['arm']}-{n}", s))
    changed = [r for r in rows if r['source'] == 'action_effect_history_v1' and r['computed']['visual_effect'] != 'no_observed_change']
    unchanged = [r for r in rows if r['source'] == 'action_effect_history_v1' and r['computed']['visual_effect'] == 'no_observed_change']
    for r in ([max(changed, key=lambda r: sum(c or 0 for c in r['computed']['changed_cells_vs_pre']))] if changed else []) + unchanged[:1]:
        name = next(n for n in lock_a['members'] if n.endswith(f"/episodes/{r['episode']}.json"))
        episode = json.loads(bundle_a.read(name))
        chosen.append((r['episode'], next(s for s in episode['steps'] if s['index'] == r['index'])))
    GALLERY.mkdir(parents=True, exist_ok=True)
    written = []
    for episode_id, step in chosen:
        before = step['before']['frames'][-1]
        after = step['after']['frames'][-1]
        _, cells = T.compare(before, after)
        fig, axes = plt.subplots(1, 2, figsize=(6, 3.2))
        for ax, grid, title in ((axes[0], before, 'before'), (axes[1], after, 'final returned')):
            ax.imshow(grid, cmap=palette, vmin=0, vmax=15, interpolation='nearest')
            ax.set_title(title, fontsize=8)
            ax.set_xticks([]), ax.set_yticks([])
        for x, y in cells or []:
            axes[1].add_patch(plt.Rectangle((x - .5, y - .5), 1, 1, fill=False, edgecolor='magenta', linewidth=.8))
        action = step['action']
        fig.suptitle(f"{episode_id} step {step['index']}: ACTION{action['action_id']} {action['action_data'] or ''}; "
                     f"changed cells {len(cells) if cells is not None else 'n/a'}", fontsize=7)
        path = GALLERY / f"{episode_id}-step{step['index']:02d}.png"
        fig.savefig(path, dpi=110, bbox_inches='tight')
        plt.close(fig)
        written.append(path.relative_to(ROOT).as_posix())
    return written


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-gallery', action='store_true')
    args = parser.parse_args()
    rows, statements, disagreements = replay()
    images = [] if args.no_gallery else gallery(rows, statements)
    counts = {}
    for r in rows:
        key = f"{r['source']}/{r['computed']['visual_effect']}/{r['computed']['progress']}"
        counts[key] = counts.get(key, 0) + 1
    report = {'version': 'ws3_transition_replay_v1', 'sources': {
                  'action_effect_history_v1': json.loads(AEH_LOCK.read_bytes())['archive_sha256'],
                  'perception_stage_b_r8': json.loads(R8_LOCK.read_bytes())['archive_sha256']},
              'transitions': len(rows), 'counts': dict(sorted(counts.items())),
              'recorded_vs_recomputed_disagreements': disagreements,
              'model_statements': statements,
              'model_statement_agreement': {
                  kind: {'n': sum(1 for s in statements if s['kind'] == kind),
                         'agree': sum(1 for s in statements if s['kind'] == kind and s['agrees_with_computed'] is True),
                         'disagree': sum(1 for s in statements if s['kind'] == kind and s['agrees_with_computed'] is False)}
                  for kind in sorted({s['kind'] for s in statements})},
              'statement_classes': {'observed': 'dispatch status, dispatched action, returned frames, environment fields',
                                    'computed': 'availability, visual effect, changed cells, events, progress, continuity',
                                    'human_annotation': 'none in this replay',
                                    'model_hypothesis': 'R8 predictions and self-assessments'},
              'gallery': images, 'rows': rows}
    with REPORT.open('x', encoding='utf-8') as stream:  # append-only: never overwrite an earlier replay
        json.dump(report, stream, indent=1, sort_keys=True)
        stream.write('\n')
    print(json.dumps({k: report[k] for k in ('transitions', 'counts', 'model_statement_agreement')}, indent=1))
    print('disagreements with recorded effects:', len(disagreements))
