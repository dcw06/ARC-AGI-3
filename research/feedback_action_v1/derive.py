"""Derive the feedback-action v1 live runner from the reviewed action-effect-history v1 closed-loop stack.

The action-effect-history v1 files ran live as attempt aeh1-4c75150a (review r3) and are reused, not edited. Each
derived file is its source with the global renames below and that file's own substitutions, each required to match an
exact number of times; a block substitution replaces the text between two anchors that must each occur exactly once.
Any remaining action-effect-history name fails the derivation. `--check` reports drift (a derived file that differs
from what the derivation produces now).

Derived: research/feedback_action_v1/live/{runner,engine,evidence,service}.py.
Hand-written (not derived): research/feedback_action_v1/live/{policy,fake_server}.py and protocol.json; the
observation pipeline is reused unchanged via action-effect-history v1's `contract.observation_payload`.
Not yet derived (the launch harness, needed before a package lock): worker, host, supervisor, monitor, resources,
authority and the launch/package/review scripts.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = 'research/action_effect_history_v1/'
TARGET_DIR = 'research/feedback_action_v1/live/'
BANNER = '# Derived from {source} by research/feedback_action_v1/derive.py; edit the derivation, not this file.\n'
GLOBAL = (('research.action_effect_history_v1', 'research.feedback_action_v1.live'),
          ('action_effect_history_run_v1', 'feedback_action_run_v1'),
          ('action_effect_history_evidence_v1', 'feedback_action_evidence_v1'),
          ('action-effect-history-v1', 'feedback-action-v1'),
          ('action_effect_history_v1', 'feedback_action_v1_live'))

RUNNER = (
    ('Two-block action-effect-history comparison runner (CPU-rehearsable; no launch authority here).',
     'Feedback-action v1 comparison runner, one block per session (CPU-rehearsable; no launch authority here).', 1),
    ('twelve isolated episodes,', 'six isolated episodes per session (one block),', 1),
    ('from research.action_effect_v1.records import effect_record, EffectHistory\n'
     'from research.feedback_action_v1.live.contract import policy_request\n',
     'from research.feedback_action_v1.live.policy import EpisodePolicy, raw_transition\n', 1),
    ("TERMINAL_EPISODE = ('action_cap', 'win', 'game_over', 'invalid_output', 'dispatch_failure')",
     "TERMINAL_EPISODE = ('action_cap', 'decision_cap', 'win', 'game_over', 'dispatch_failure')"
     "  # an invalid output never ends an episode", 1),
    ('def parse_action(raw, legal):\n'
     '    from certification.phase4_transient_v2.action_contract import validate_action\n'
     "    return validate_action(raw, legal)['action']\n",
     'def parse_action(raw, legal, request):\n'
     '    """The adapter\'s parse for the request\'s arm; both arms share the frozen action validator."""\n'
     '    from research.feedback_action_v1.live.policy import parse_action as arm_parse\n'
     '    return arm_parse(raw, legal, request)\n', 1),
    ('            action = parse_action(raw, obs.available_actions)\n',
     '            action = parse_action(raw, obs.available_actions, request)\n', 1),
    ("            history = EffectHistory(limit=16)  # isolated per episode and arm\n"
     "            for step_index in range(limits['actions_per_episode']):\n"
     "                check()\n",
     "            policy = EpisodePolicy(arm, episode_id, seed=limits['request_seed'])  # isolated per episode and arm\n"
     "            episode['model_statements'] = policy.statements\n"
     "            step_index = 0\n"
     "            while True:\n"
     "                check()\n", 1),
    ("                request = policy_request(runtime, arm, history if arm == 'history' else None, seed=limits['request_seed'])\n"
     "                action = call(episode, request, obs)\n"
     "                if action is None:\n"
     "                    episode['stop_reason'] = 'invalid_output'\n"
     "                    break\n",
     "                if step_index >= limits['actions_per_episode']:\n"
     "                    episode['stop_reason'] = 'action_cap'\n"
     "                    break\n"
     "                if len(episode['calls']) >= limits['decision_calls_per_episode']:\n"
     "                    episode['stop_reason'] = 'decision_cap'  # everything retained; the schedule continues\n"
     "                    break\n"
     "                request = policy.request(runtime, obs)\n"
     "                action = call(episode, request, obs)\n"
     "                policy.decided(episode['calls'][-1], obs)\n"
     "                if action is None:\n"
     "                    persist(episode)\n"
     "                    continue  # an invalid output consumes a call, never an action\n", 1),
    ("                record = effect_record(step['before'], action, outcome)\n"
     "                entry = history.append(record)\n"
     "                step.update(status=outcome['status'], effect_record=record, history_entry=entry, returned_at=now(),\n"
     "                            after=outcome.get('post'))\n",
     "                raw = raw_transition(episode_id, step_index, step['before'], action, outcome)\n"
     "                record = policy.dispatched(raw)\n"
     "                step.update(status=outcome['status'], raw_transition=raw, record_id=record['identity']['record_id'],\n"
     "                            returned_at=now(), after=outcome.get('post'))\n", 1),
    ("                obs = post\n"
     "            else:\n"
     "                # The cap was reached; a terminal state produced by the last action takes precedence.\n"
     "                episode['stop_reason'] = {'WIN': 'win', 'GAME_OVER': 'game_over'}.get(obs.state.value, 'action_cap')\n",
     "                obs = post\n"
     "                step_index += 1  # terminal states are checked before the caps at the top of the loop\n", 1),
)

SERVICE_VALIDATE = (
    'def validate_policy_request(request):\n'
    '    """Exact frozen request contract for both arms (feedback-action v1: research/feedback_action_v1/live/policy.py);\n'
    '    raises ValueError before any transport."""\n'
    '    from research.feedback_action_v1.live.policy import validate_policy_request as validate\n'
    '    return validate(request)\n')

SERVICE = (
    ('MAX_POLICY_CALLS = 144', 'MAX_POLICY_CALLS = 192  # one session: 6 episodes x 32 decision calls', 1),
    ('"""One canary, then at most 144 contract-checked policy calls; raw evidence returned for retention."""',
     '"""One canary, then at most 192 contract-checked policy calls; raw evidence returned for retention."""', 1),
    ("raise ValueError('policy call ceiling (144)')", "raise ValueError('policy call ceiling (192)')", 1),
    (('def validate_policy_request(request):\n', '\n\nclass HistoryModelService'), SERVICE_VALIDATE, 'block'),
)

DERIVED = {'runner.py': RUNNER, 'engine.py': (), 'evidence.py': (), 'service.py': SERVICE}


def derive_one(name):
    source = SOURCE_DIR + name
    text = (ROOT / source).read_text(encoding='utf-8')
    for old, new in GLOBAL:
        text = text.replace(old, new)
    for old, new, count in DERIVED[name]:
        if count == 'block':
            start, end = old
            for anchor in (start, end):
                if text.count(anchor) != 1:
                    raise ValueError(f'{name}: anchor {anchor[:50]!r} must occur once, found {text.count(anchor)}')
            i, j = text.index(start), text.index(end)
            if j <= i:
                raise ValueError(f'{name}: block anchors out of order')
            text = text[:i] + new + text[j:]
            continue
        found = text.count(old)
        if found != count:
            raise ValueError(f'{name}: expected {count} of {old[:70]!r}, found {found}')
        text = text.replace(old, new)
    if 'action_effect_history' in text or 'action-effect-history' in text or 'EffectHistory' in text:
        raise ValueError(f'{name}: unexpected remaining action-effect-history reference')
    return BANNER.format(source=source) + text


def derive():
    return {TARGET_DIR + name: derive_one(name) for name in DERIVED}


def stale():
    return [t for t, text in derive().items()
            if not (ROOT / t).is_file() or (ROOT / t).read_text(encoding='utf-8') != text]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    if parser.parse_args().check:
        drift = stale()
        if drift:
            raise SystemExit('derived files differ from the derivation: ' + ', '.join(drift))
        print(f'{len(DERIVED)} derived files match the derivation')
        sys.exit(0)
    for target, text in derive().items():
        (ROOT / target).write_text(text, encoding='utf-8', newline='\n')
    print(f'wrote {len(DERIVED)} derived files')
