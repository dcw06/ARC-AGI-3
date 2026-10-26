import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, ValidationError
from research.ls20_discovery_windows import HypothesisManager, M1View
from tests.ls20_windows_fixture import PRODUCER, RawMemory, action, obs, observe


class SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schema=json.loads((Path(__file__).parents[1]/'research/ls20_discovery_windows/schema.json').read_text())
        Draft202012Validator.check_schema(schema)
        cls.validator=Draft202012Validator(schema)

    def test_generated_prediction_and_handoff_validate(self):
        memory=RawMemory()
        for _ in range(3):
            manager=HypothesisManager(M1View(memory.snapshot(),PRODUCER))
            self.validator.validate(manager.export())
            for mode in ('immediate','competing'):
                self.validator.validate(manager.predict(action(),mode))
            observe(memory,obs())

    def test_extra_fields_wrong_action_and_fabricated_objectives_rejected(self):
        prediction=HypothesisManager(M1View(RawMemory().snapshot(),PRODUCER)).predict(action())
        for mutation in ('extra','action_data','goal','unknown'):
            value=copy.deepcopy(prediction)
            if mutation=='extra': value['injected_rule']='player is color 12'
            elif mutation=='action_data': value['action']['action_data']={'x':0,'y':0}
            elif mutation=='goal': value['objective_hypotheses']=[{'confirmed':True}]
            else: value['unknown_alternative']=False
            with self.subTest(mutation=mutation),self.assertRaises(ValidationError):
                self.validator.validate(value)


if __name__=='__main__': unittest.main()
