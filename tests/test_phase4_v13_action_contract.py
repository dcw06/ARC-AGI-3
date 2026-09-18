import itertools
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from jsonschema import Draft202012Validator
from agent.e1_policy import E1Policy, E1ModelBinding, _strict_object
from agent.feature_manifest import load_e1_feature_manifests, validate_e1_proposal
from certification.phase4_v13.action_contract import response_format, validate_canary, validate_action
from certification.phase4_v13.contract_policy import ContractPolicy, ValidatingCompletion
from certification.phase4_v13.policy_evidence import PolicyEvidence
from certification.phase4_v13.model_transport import OpenAICompatibleCompletionClient
from certification.phase4_v13.service import SharedModelService

ROOT=Path(__file__).resolve().parents[1]


class ActionContractTests(unittest.TestCase):
    def schema(self,legal):return Draft202012Validator(response_format(legal)['json_schema']['schema'])

    def policy(self):
        return ContractPolicy(evidence=PolicyEvidence('test'),
            manifest=load_e1_feature_manifests(ROOT/'config/e1_feature_manifests.yaml')['E1S-R'],
            binding=E1ModelBinding.from_mapping(json.loads((ROOT/'config/operational_primary.yaml').read_text())['primary']['model_binding']),
            client=None,inference=None)

    def test_all_legal_subsets_and_coordinate_boundaries(self):
        for size in range(1,8):
            for legal in itertools.combinations(range(1,8),size):
                validator=self.schema(legal);validator.check_schema(validator.schema)
                for action in range(1,8):
                    payload={'action':{'action_id':action,'action_data':{'x':0,'y':63} if action==6 else {}}}
                    self.assertEqual(validator.is_valid(payload),action in legal)
        for x,y in itertools.product((0,63),repeat=2):
            self.assertTrue(self.schema([6]).is_valid({'action':{'action_id':6,'action_data':{'x':x,'y':y}}}))

    def test_observed_failure_and_bad_coordinates_rejected(self):
        policy=self.policy();validator=self.schema([6])
        for data in ({},{'x':1},{'x':-1,'y':0},{'x':64,'y':0},
                     {'x':True,'y':0},{'x':'1','y':0},{'x':1.5,'y':0},{'x':0,'y':0,'z':1}):
            with self.subTest(data=data):
                value={'action':{'action_id':6,'action_data':data}}
                self.assertFalse(validator.is_valid(value))
                with self.assertRaises(ValueError):validate_action(json.dumps(value),[6])
                with self.assertRaises(ValueError):validate_canary(json.dumps(value))
        with self.assertRaises(ValueError):_strict_object('```json\n{}\n```')

    def test_completion_gate_rejects_numeric_coercion_without_repair(self):
        request={'messages':[{'role':'system','content':'test'},
            {'role':'user','content':json.dumps({'observation':{'legal_actions':[6]}})}]}
        client=Mock()
        for x in (1.0,1.5,True,'1'):
            client.complete.return_value=SimpleNamespace(content=json.dumps({'action':{
                'action_id':6,'action_data':{'x':x,'y':0}}}))
            with self.assertRaises(ValueError):ValidatingCompletion(client).complete(request)
        result=SimpleNamespace(content='{"action":{"action_id":6,"action_data":{"x":0,"y":63}}}')
        client.complete.return_value=result
        self.assertIs(ValidatingCompletion(client).complete(request),result)
        self.assertEqual(client.complete.call_count,5)

    def test_valid_actions_still_use_existing_validator(self):
        policy=self.policy()
        for action in range(1,8):
            value={'action':{'action_id':action,'action_data':{'x':12,'y':34} if action==6 else {}}}
            decision=validate_e1_proposal(value,manifest=policy.manifest,legal_actions=[action])
            self.assertEqual(decision.action_id,action)
        self.assertFalse(self.schema([1]).is_valid({'action':{'action_id':1,'action_data':{'x':1,'y':2}}}))
        self.assertFalse(self.schema([6]).is_valid({'action':{'action_id':6,'action_data':{'x':1,'y':2}},'rationale':'extra'}))

    def test_request_adds_schema_preserving_generation_settings(self):
        policy=self.policy()
        messages=[{'role':'system','content':policy._system_prompt()},
                  {'role':'user','content':json.dumps({'observation':{'legal_actions':[6]}})}]
        original=E1Policy._request(policy,messages);revised=policy._request(messages)
        self.assertEqual({k:v for k,v in revised.items() if k!='response_format'},original)
        self.assertEqual(revised['response_format'],response_format([6]))
        self.assertIn('"x":12,"y":34',messages[0]['content'])
        self.assertEqual(revised['max_tokens'],128)
        with self.assertRaises(ValueError):response_format([0])
        with self.assertRaises(ValueError):response_format([])

    def test_transport_preserves_schema_and_does_not_retry_errors(self):
        session=Mock();reply=Mock();reply.json.return_value={'choices':[{'message':{'content':'{}'}}],'usage':{}}
        session.post.return_value=reply
        client=OpenAICompatibleCompletionClient(session=session)
        request={'response_format':response_format([6])};client.complete(request)
        self.assertEqual(session.post.call_args.kwargs['json'],request)
        reply.raise_for_status.side_effect=RuntimeError('unsupported schema')
        with self.assertRaisesRegex(RuntimeError,'unsupported schema'):client.complete(request)
        self.assertEqual(session.post.call_count,2)

    def test_service_rejects_missing_or_weakened_schema_before_http(self):
        service=SharedModelService(Path('.'));service.started=True
        service.primary=SimpleNamespace(binding=SimpleNamespace(model_id='test'))
        request={'model':'test','seed':0,'temperature':0,'max_tokens':128,
            'chat_template_kwargs':{'enable_thinking':False},'messages':[
                {'role':'system','content':'test'},
                {'role':'user','content':json.dumps({'observation':{'legal_actions':[6]}})}]}
        with patch('requests.Session') as http:
            for fmt in (None,response_format([1,6])):
                request['response_format']=fmt
                with self.assertRaisesRegex(ValueError,'schema'):service.complete(request)
            http.assert_not_called()
