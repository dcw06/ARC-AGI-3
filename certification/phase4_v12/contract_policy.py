"""Explicit v12 policy revision; retains the original strict action validator."""
from certification.phase4_v12.policy_evidence import ObservedPolicy
from certification.phase4_v12.action_contract import response_format, request_legal_actions, validate_action


class ValidatingCompletion:
    def __init__(self,client):self.client=client

    def complete(self,request):
        result=self.client.complete(request)
        validate_action(result.content,request_legal_actions(request['messages']))
        return result


class ContractPolicy(ObservedPolicy):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        if self.manifest.treatment_id!='E1S-R' or self.manifest.workspace!='none':
            raise ValueError('v12 action contract supports E1S-R only')
        self.client=ValidatingCompletion(self.client)

    def _system_prompt(self):
        return (
            'You control one ARC-AGI-3 game from a stateless observation. '
            'history_compaction explicitly reports any older transitions omitted from this prompt. '
            'Return only one compact JSON object matching the supplied action schema. '
            'Omit intent, rationale, Markdown and reset/action 0. '
            'Choose exactly one currently legal action_id. '
            'For ACTION6, choose a display-grid location and include integer x and y in [0,63]. '
            'Valid ACTION6 shape: {"action":{"action_id":6,"action_data":{"x":12,"y":34}}}. '
            'These coordinates illustrate the format; choose coordinates from the observation. '
            'For actions 1,2,3,4,5,7 use empty action_data, for example '
            '{"action":{"action_id":1,"action_data":{}}}. '
            'Never return ACTION6 with empty action_data. Keep the response under 64 tokens.'
        )

    def _request(self,messages):
        request=super()._request(messages)
        request['response_format']=response_format(request_legal_actions(messages))
        return request
