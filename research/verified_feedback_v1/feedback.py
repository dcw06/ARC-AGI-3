"""Bind an immutable pre-action forecast to its already observed transition.

Pins must come from separately retained pre-dispatch/event journal entries.
Self-consistent hashes alone do not prove acquisition or truthful execution.
There is no counterfactual branch, model, engine or provider in this module.
"""
from copy import deepcopy
import json
import re

from research.action_effect_choice_v2.interface import checked_pair, parse_choice
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.policy import check_observation

NOTE = ('Computed only from the immediately preceding executed study action and its immutable '
        'original forecast. Counts include every changed visible cell, including interface cells. '
        'A change is not evidence of progress, control meaning or usefulness. No unexecuted outcome is supplied.')


def _identity(trajectory_id, index, step):
    if type(trajectory_id) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,120}', trajectory_id):
        raise ValueError('invalid trajectory identity')
    if type(index) is not int or index != 0 or type(step) is not int or not 2 <= step <= 20:
        raise ValueError('first study event and restored game index required')


def _pin(value, expected, label):
    if type(expected) is not str or not re.fullmatch(r'[0-9a-f]{64}', expected) or digest(value) != expected:
        raise ValueError(label+' journal pin differs')


def extent(count):
    if type(count) is not int or not 0 <= count <= 4096:
        raise ValueError('invalid changed-cell count')
    return 'none' if count == 0 else '1_to_4' if count <= 4 else '5_to_64' if count <= 64 else '65_plus'


def freeze_forecast(answer, pair, *, trajectory_id, study_decision_index, game_action_index, before):
    """Create this envelope and journal its hash BEFORE dispatching the action."""
    _identity(trajectory_id, study_decision_index, game_action_index)
    check_observation(before)
    checked_pair(pair, before['legal_actions'])
    parsed = parse_choice(json.dumps(answer, allow_nan=False), first=True)
    return {'schema': 'verified_feedback_forecast_v1', 'trajectory_id': trajectory_id,
            'study_decision_index': study_decision_index, 'game_action_index': game_action_index,
            'before_observation_sha256': digest(before), 'candidates': deepcopy(pair), 'answer': parsed}


def build_feedback(frozen, forecast_pin, transition, transition_pin, *, trajectory_id,
                   study_decision_index, restored_prefix_length, current):
    """Refuse missing/inconsistent evidence; never invent an unknown observation."""
    if (type(study_decision_index) is not int or study_decision_index != 1 or
            type(restored_prefix_length) is not int or not 2 <= restored_prefix_length <= 20):
        raise ValueError('second study phase and exact restored prefix required')
    if type(frozen) is not dict or type(transition) is not dict:
        raise ValueError('executed feedback unavailable: prior forecast or transition missing')
    _pin(frozen, forecast_pin, 'pre-dispatch forecast')
    _pin(transition, transition_pin, 'executed transition')
    if set(transition) != {'step', 'before', 'after', 'action', 'predicted_visible_change'}:
        raise ValueError('executed transition fields differ')
    if type(transition['step']) is not int or transition['step'] != restored_prefix_length:
        raise ValueError('previous study event index differs')
    check_observation(transition['before']); check_observation(transition['after']); check_observation(current)
    if digest(transition['after']) != digest(current):
        raise ValueError('current observation differs from preceding executed after state')
    try:
        rebuilt = freeze_forecast(frozen['answer'], frozen['candidates'], trajectory_id=trajectory_id,
            study_decision_index=0, game_action_index=restored_prefix_length, before=transition['before'])
    except KeyError as exc:
        raise ValueError('pre-dispatch forecast fields missing') from exc
    if digest(rebuilt) != digest(frozen):
        raise ValueError('forecast identity, before observation or event index differs')
    answer = rebuilt['answer']; selected = answer['selected_candidate']
    forecast = answer['candidate_predictions'][selected]
    if digest(transition['action']) != digest(rebuilt['candidates'][selected]):
        raise ValueError('full dispatched action differs from committed selection')
    predicted_binary = 'unknown' if forecast == 'unknown' else 'no' if forecast == 'none' else 'yes'
    if transition['predicted_visible_change'] != predicted_binary:
        raise ValueError('transition prediction differs from immutable original forecast')
    count = sum(a != b for row_a, row_b in zip(transition['before']['grid'], current['grid'])
                for a, b in zip(row_a, row_b))
    actual = extent(count)
    return {'schema': 'verified_executed_feedback_v1', 'trajectory_id': trajectory_id,
            'previous_study_decision_index': 0, 'game_action_index': restored_prefix_length,
            'action': deepcopy(transition['action']), 'original_selected_forecast': forecast,
            'observed_changed_cell_count': count, 'observed_changed_cell_category': actual,
            'observed_visible_change': 'yes' if count else 'no',
            'original_forecast_check': 'unknown' if forecast == 'unknown' else 'matched' if forecast == actual else 'mismatched',
            'forecast_comparison_available': forecast != 'unknown', 'qualification': NOTE,
            'provenance': {'forecast_sha256': forecast_pin, 'transition_sha256': transition_pin,
                'before_observation_sha256': digest(transition['before']), 'after_observation_sha256': digest(current)}}


def display(receipt):
    """Project only observed facts, without trajectory labels or opaque hashes."""
    fields = ('previous_study_decision_index', 'game_action_index', 'action', 'original_selected_forecast',
              'observed_changed_cell_count', 'observed_changed_cell_category', 'observed_visible_change',
              'original_forecast_check', 'forecast_comparison_available', 'qualification')
    return {'schema': 'last_executed_study_action_feedback_v1',
            **{field: deepcopy(receipt[field]) for field in fields}}
