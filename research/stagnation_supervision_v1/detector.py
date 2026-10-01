"""Mechanical stagnation detector (Track 3, stagnation_supervision_v1). No model, no learned weights.

Input: transition_evidence_v1 records in order (transition.history output, consumed read-only), plus an optional
agent-side prediction stream. Uses only observable evidence: pre-action frame fingerprints, the exact dispatched
action, measured visual effects, environment-reported progress and segment boundaries, and prediction outcomes.

Signals (each optional; thresholds are chosen on development fixtures and frozen in trigger_spec.json):
- repeat_no_effect:        the same (pre-frame, action) acknowledged k times with no lasting observed change;
- state_action_recurrence: the same (pre-frame, action) acknowledged k times, whatever its effect (cycles);
- tiny_effect_repeat:      the identical action k times in a row, each changing at most TINY_CELLS cells;
- novelty_stall:           among the last w observed transitions, at most n reached a frame new to the segment;
- prediction_failures:     k consecutive scored predictions failed;
- no_progress_horizon:     k observed transitions in the segment without a confirmed progress signal (segments
                           end at level completion, so this counts from the last level change or reset).

Evidence rules, from the transition contract:
- a failed dispatch is never a no-effect observation: it neither extends nor breaks a pattern;
- an unknown outcome or missing observation breaks streaks (the state may have changed unseen) and adds nothing;
- `indeterminate` effects are never counted as no change;
- a segment boundary (reset, level change, terminal state) clears all statistics: revisiting a level start after
  a reset is not a loop.
The detector is causal: its output at step t depends only on records 0..t. "No progress detected" never means
"progress is impossible": every firing is a prompt to reconsider, not a verdict.
"""
import json

from research.transition_evidence_v1 import vocabulary as V

VERSION = 'stagnation_supervision_v1_detector'
TINY_CELLS = 4  # fixed before any selection; small effects such as counters, single-cell fills or 1x1 moves
SIGNALS = ('repeat_no_effect', 'state_action_recurrence', 'tiny_effect_repeat', 'novelty_stall', 'prediction_failures',
           'no_progress_horizon')
COUNT_SIGNALS = ('repeat_no_effect', 'state_action_recurrence', 'tiny_effect_repeat', 'prediction_failures',
                 'no_progress_horizon')
NO_LASTING_CHANGE = (V.NO_OBSERVED_CHANGE, V.CHANGED_THEN_RETURNED)
NOVELTY_HISTORY = 16


def action_key(dispatched):
    return json.dumps(dispatched, sort_keys=True, separators=(',', ':'))


def final_frame(record):
    """(sha256, changed cells vs pre or None) of the last returned frame when it is valid, else None."""
    frames = record['measurements']['frames']
    if not frames or not frames[-1]['valid']:
        return None
    changed = frames[-1]['vs_pre']['changed_cells']
    return frames[-1]['sha256'], changed['value'] if changed['status'] == 'measured' else None


def prediction_outcome(record, prediction):
    """'matched', 'failed' or None (unscored). A prediction is scored only against a measured lasting effect."""
    if prediction is None or 'expects_change' not in prediction:
        return None
    visual = record['measurements']['visual_effect']['status']
    if visual == V.FINAL_FRAME_DIFFERS:
        changed = True
    elif visual in NO_LASTING_CHANGE:
        changed = False
    else:
        return None
    return 'matched' if prediction['expects_change'] == changed else 'failed'


class Statistics:
    """Threshold-free statistics, updated once per record. Each statistic keeps its evidence (action indices)."""

    def __init__(self):
        self.segment = None
        self.clear()

    def clear(self):
        self.pairs, self.no_effect_pairs = {}, {}
        self.seen = set()
        self.streak, self.streak_key = [], None
        self.novelty = []  # (action_index, reached a new frame) for observed transitions
        self.prediction_streak = []
        self.observed = []

    def update(self, record, prediction=None):
        index = record['identity']['action_index']
        if record['segment'] != self.segment:
            self.segment = record['segment']
            self.clear()
        status = record['dispatch']['status']
        availability = record['observations']['availability']['status']
        fp = record['observations']['before_frames_sha256'][-1]
        self.seen.add(fp)
        key = action_key(record['action']['dispatched'])
        out = {'action_index': index, 'segment': self.segment, 'evidence_step': False}
        if status == V.FAILED:
            return out  # not an observation; neither extends nor breaks a pattern
        if status == V.OUTCOME_UNKNOWN or availability == V.MISSING:
            self.streak, self.streak_key = [], None
            self.prediction_streak = []
            return out
        out['evidence_step'] = True
        self.observed.append(index)
        out['no_progress_horizon'] = list(self.observed)
        pair = (fp, key)
        self.pairs.setdefault(pair, []).append(index)
        out['state_action_recurrence'] = list(self.pairs[pair])
        visual = record['measurements']['visual_effect']['status']
        if visual in NO_LASTING_CHANGE:
            self.no_effect_pairs.setdefault(pair, []).append(index)
            out['repeat_no_effect'] = list(self.no_effect_pairs[pair])
        final = final_frame(record)
        lasting = 0 if visual in NO_LASTING_CHANGE else (final[1] if final else None)
        if lasting is not None and lasting <= TINY_CELLS:
            self.streak = self.streak + [index] if key == self.streak_key else [index]
            self.streak_key = key
        else:
            self.streak, self.streak_key = [], None
        out['tiny_effect_repeat'] = list(self.streak)
        if final is not None:
            self.novelty.append((index, final[0] not in self.seen))
            self.seen.add(final[0])
            out['novelty'] = list(self.novelty[-NOVELTY_HISTORY:])
        outcome = prediction_outcome(record, prediction)
        if outcome == 'failed':
            self.prediction_streak.append(index)
        elif outcome == 'matched':
            self.prediction_streak = []
        out['prediction_failures'] = list(self.prediction_streak) if outcome == 'failed' else []
        return out


def signals(stats, params):
    """The signals firing at this step under `params`, each with its value, threshold and evidence references.
    Only an evidence step (an acknowledged, observed transition that itself extends the pattern) can fire."""
    fired = []
    if not stats['evidence_step']:
        return fired
    for name in COUNT_SIGNALS:
        k = params.get(name)
        refs = stats.get(name) or []
        if k is not None and len(refs) >= k:
            fired.append({'signal': name, 'value': len(refs), 'threshold': k, 'evidence': refs[-k:]})
    novelty = params.get('novelty_stall')
    history = stats.get('novelty')
    if novelty is not None and history and history[-1][0] == stats['action_index'] and len(history) >= novelty[0]:
        window = history[-novelty[0]:]
        new = sum(flag for _, flag in window)
        if new <= novelty[1]:
            fired.append({'signal': 'novelty_stall', 'value': new, 'threshold': list(novelty),
                          'evidence': [i for i, _ in window]})
    return fired


def statistics(records, predictions=None):
    """Per-step statistics for one trajectory (records from transition.history)."""
    by_index = {p['action_index']: p for p in predictions or ()}
    stats = Statistics()
    return [stats.update(r, by_index.get(r['identity']['action_index'])) for r in records]


def triggers(step_stats, params, cooldown):
    """Trigger decisions with a cooldown in actions: a firing within `cooldown` actions of the previous trigger is
    suppressed (and kept, with its reason). Returns one entry per step."""
    out, last = [], None
    for stats in step_stats:
        fired = signals(stats, params)
        entry = {'action_index': stats['action_index'], 'signals': fired, 'trigger': False}
        if fired:
            if last is not None and stats['action_index'] - last < cooldown:
                entry['suppressed'] = 'cooldown'
            else:
                entry['trigger'] = True
                last = stats['action_index']
        out.append(entry)
    return out
