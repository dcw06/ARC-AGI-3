"""Adversarial request/forecast/terminal checks; synthetic data only."""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from research.action_effect_choice_live_v1.audit import audit_case, audit_study
from research.action_effect_choice_live_v1.live_evaluation import lines
from research.initial_geometry_assistance_v1.geometry import digest
from tests.action_effect_live_fixture import create, checkpoints, protocol_patches
from tests.test_feedback_probe_audit_v1 import ScriptEngine


class ReviewChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.folder.cleanup)
        cls.inputs, cls.out, _ = create(cls.folder.name)
        cls.cp = checkpoints()[0]
        cls.pair = json.loads((cls.inputs/'candidate-pairs.json').read_bytes())[0]['candidates']
        cls.variant = cls.cp['order'][0]
        cls.events = lines(cls.out/(cls.cp['checkpoint_id']+'-'+cls.variant+'.jsonl'))

    def test_entire_request_is_checked_after_attacker_rehashes_it(self):
        for mode in ('model', 'system', 'role', 'image', 'tokens', 'seed', 'candidates', 'previous_forecast', 'summary'):
            with self.subTest(mode=mode):
                events = deepcopy(self.events)
                event = [e for e in events if e['kind'] == 'request'][1]
                body = event['body']
                if mode == 'model': body['model'] = 'wrong'
                elif mode == 'system': body['messages'][0]['content'] += ' extra'
                elif mode == 'role': body['messages'][1]['role'] = 'assistant'
                elif mode == 'image':
                    next(part for part in body['messages'][1]['content'] if part['type'] == 'image_url')['image_url']['url'] = 'wrong'
                elif mode == 'tokens': body['max_tokens'] = 257
                elif mode == 'seed': body['seed'] = 1
                else:
                    index = -2 if mode == 'summary' else -1
                    part = body['messages'][1]['content'][index]
                    value = json.loads(part['text'])
                    if mode == 'summary': value['transitions'][-1]['changed_cell_count'] += 1
                    elif mode == 'previous_forecast': value['previous_selected_forecast']['prediction'] = '65_plus'
                    else: value['candidate_choice_v1']['A']['action_id'] = 99
                    part['text'] = json.dumps(value, sort_keys=True, separators=(',', ':'))
                event['request_sha256'] = digest(body)
                engine = ScriptEngine(self.cp)
                with self.assertRaises(ValueError): audit_case(self.cp, self.pair, self.variant, events, engine)
                self.assertTrue(engine.closed)

    def test_terminal_labels_and_final_observation_derived_from_replay(self):
        for mode in ('stop', 'final', 'dispatch_count', 'previous_answer'):
            with self.subTest(mode=mode):
                events = deepcopy(self.events)
                if mode == 'stop': events[-1]['reason'] = 'first_level_complete'
                elif mode == 'final': events[-1]['final_observation']['levels_completed'] = 1
                elif mode == 'dispatch_count': events[-1]['new_dispatches'] = 0
                else: [e for e in events if e['kind'] == 'transition'][0]['answer']['selected_candidate'] = 'A'
                with self.assertRaises(ValueError):
                    audit_case(self.cp, self.pair, self.variant, events, ScriptEngine(self.cp))

    def test_invalid_first_answers_leave_64_scheduled_forecasts(self):
        with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
            inputs, out, _ = create(folder, invalid=True)
            protocol_patches(stack)
            result = audit_study(out, inputs, token_audit=lambda _: 100,
                                 replay_factory=lambda cp, name: ScriptEngine(cp))
            self.assertEqual(result['generations'], 17)
            self.assertEqual(result['scheduled_candidate_forecasts'], 64)
            self.assertEqual(result['correct_candidate_forecasts'], 0)
            self.assertEqual(sum(r['observed'] for r in result['decisions']), 16)
            self.assertEqual(result['continuation_dispatches'], 0)
