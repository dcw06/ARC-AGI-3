"""Repeat the opening of a saved run, so several conditions can start from one position with one set of notes.

The saved run's first N actions per game are sent again without any model call. Every returned
observation must hash to the saved one; the controller stops the game at the first difference. The
model's saved replies are fed back to the policy, so its history and notes are rebuilt exactly.
"""
import hashlib
import json

from .config import strict_json


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


# Settings that shape the prompt and the notes. A saved run made under different ones cannot be continued.
MUST_MATCH = ('model', 'stage', 'effort', 'thinking', 'grid_encoding', 'history_limit', 'history_board_limit',
              'observation_evidence_ids', 'clear_hypotheses_on_level', 'max_output_tokens', 'resets_per_game')
# A saved run that itself used these cannot be told apart action by action, so it is refused.
MUST_BE_OFF = ('model_may_reset', 'stall_window', 'stall_level_ratio', 'recovery_pricing', 'replay_after_reset',
               'resume_actions', 'pin_game_overs', 'game_over_lessons', 'state_objective')
KINDS = ('configuration', 'initial_observation', 'model_returned', 'transition')


class Diverged(ValueError):
    """The live game did not return what the saved run recorded. Ends that game only."""


def load(path, games, count, config=None):
    """{game: {'initial_sha256', 'actions': [{'action', 'after_sha256', 'answer'}]}} for the first `count` actions.

    answer is the model's accepted reply for that action, or None when the controller sent the action
    itself (a reset after GAME_OVER). Raises before anything is sent if a game has fewer actions, if the
    saved run was not a plain control run, or if its prompt settings differ from `config`.
    """
    wanted = {game: {'initial_sha256': None, 'actions': []} for game in games}
    pending = {}
    with open(path, encoding='utf-8') as handle:
        for line in handle:
            if not any('"kind":"%s"' % kind in line for kind in KINDS):
                continue
            event = json.loads(line)
            if event['kind'] == 'configuration':
                saved = event['config']
                used = [name for name in MUST_BE_OFF if saved.get(name)]
                if used:
                    raise ValueError('saved run used recovery or resume settings: ' + ', '.join(used))
                differ = [name for name in MUST_MATCH if config is not None and saved.get(name) != getattr(config, name)]
                if differ:
                    raise ValueError('saved run was made with different settings: ' + ', '.join(differ))
                continue
            game = event.get('game_id')
            if game not in wanted or len(wanted[game]['actions']) >= count:
                continue
            if event['kind'] == 'initial_observation':
                wanted[game]['initial_sha256'] = event['observation']['observation_sha256']
            elif event['kind'] == 'model_returned':
                pending[game] = event['content']          # the last reply before the action is the accepted one
            else:
                content = pending.pop(game, None)
                answer = None if content is None else strict_json(content)
                if answer is not None and answer.get('action') != event['action']:
                    raise ValueError('saved reply and saved action disagree for ' + game)
                if answer is None and event['action']['action_id'] != 0:
                    raise ValueError('saved run has an action without a model reply for ' + game)
                wanted[game]['actions'].append({'action': event['action'],
                                                'after_sha256': event['after']['observation_sha256'],
                                                'answer': answer})
    short = sorted(game for game, saved in wanted.items() if len(saved['actions']) < count)
    if short:
        raise ValueError('saved run has fewer than %d actions for: %s' % (count, ', '.join(short)))
    return wanted
