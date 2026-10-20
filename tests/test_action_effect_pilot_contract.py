"""Pilot-specific budgets, external input pins and phase-coverage regressions."""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from certification.direct_publisher_smoke_v1.accounting import Clock, RequestRefused
from research.initial_geometry_assistance_v1.geometry import canonical, digest
from research.initial_geometry_assistance_v1.live_io import sha, write_new
from research.action_effect_choice_live_v2 import live_contract as contract
from research.action_effect_choice_live_v2.live_worker import DurableLedger, request_plan
from research.action_effect_choice_live_v2.audit import audit_study, audit_case
from research.action_effect_choice_live_v2.live_runtime import SCOPE, check_authority
from research.action_effect_choice_live_v2.live_evaluation import lines
from research.action_effect_choice_live_v2.live_package import reviewed_scope_files
from tests.action_effect_pilot_fixture import checkpoints, create, protocol_patches
from tests import test_action_effect_pilot_operator as operator_fixture
from tests.test_feedback_probe_audit_v1 import ScriptEngine


class PilotContract(unittest.TestCase):
    def test_scope_model_inventory_is_required_before_package_sealing(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);write_new(root/'draft.json',{'approved':False})
            with self.assertRaisesRegex(ValueError,'root model inventory'):reviewed_scope_files(root)
            rows=[dict(path='file-'+str(i),bytes=i+1)for i in range(20)]
            path=root/'model-dataset-inventory.json';write_new(path,dict(files=rows))
            self.assertIn(path.name,reviewed_scope_files(root))
            for mode in ('duplicate','boolean_size','missing'):
                changed=deepcopy(rows)
                if mode=='duplicate':changed[1]['path']=changed[0]['path']
                elif mode=='boolean_size':changed[0]['bytes']=True
                else:changed.pop()
                path.write_bytes(canonical(dict(files=changed)))
                with self.subTest(mode=mode),self.assertRaisesRegex(ValueError,'20-file'):reviewed_scope_files(root)

    def test_ninth_request_is_last_even_with_an_oversized_external_plan(self):
        plan=[dict(id=str(i),kind='policy',method='POST',path='/v1/chat/completions',timeout_seconds=30,max_issues=1)for i in range(10)]
        clock=Clock(dict(internal_seconds=3300,admission_cutoff_seconds=3000),0,now=lambda:0)
        with self.assertRaisesRegex(ValueError,'above the cap'):DurableLedger(plan,clock,lambda _:None)
        ledger=DurableLedger(plan[:9],clock,lambda _:None)
        for i in range(9):ledger.admit(str(i))
        ledger.plan['9']=plan[9]
        with self.assertRaisesRegex(RequestRefused,'cap of 9'):ledger.admit('9')
        self.assertEqual(ledger.summary()['issued'],9)

    def test_new_scope_cannot_accept_old_scope_or_expanded_limits(self):
        pin,authority,_,_=operator_fixture.ProbeOperatorChecks.fixture()
        check_authority(authority,pin)
        for field,value in [('generations',33),('counted_HTTP_requests',33),('offline_engine_actions',84),('local_scorecards',16)]:
            changed=deepcopy(authority);changed['scope'][field]=value
            with self.subTest(field=field),self.assertRaises(PermissionError):check_authority(changed,pin)
        self.assertEqual((SCOPE['generations'],SCOPE['offline_engine_actions'],SCOPE['local_scorecards']),(9,20,4))

    def test_externally_pinned_subset_and_every_first_request_are_reconstructed(self):
        values=checkpoints()
        # Synthetic values have no original 'order' field in the real pinned file.
        for cp in values:cp.pop('order',None)
        original={'checkpoints':values}
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);write_new(root/'checkpoints.json',original)
            frozen=deepcopy(contract.protocol())
            frozen.update(checkpoint_inventory_sha256=digest(values),checkpoint_file_sha256=sha(root/'checkpoints.json'))
            with patch.object(contract,'protocol',return_value=frozen):
                payload=contract.expected_inputs(values)
                for name,value in payload.items():
                    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);write_new(p,value)
                manifest=dict(schema='action_effect_choice_live_inputs_v2',protocol_sha256=sha(Path(contract.__file__).with_name('live_protocol.json')),
                    source_CPU_manifest_sha256=frozen['source_CPU_manifest_sha256'],prospective_maxima=contract.MAXIMA,
                    files={name:sha(root/name)for name in ['checkpoints.json',*payload]})
                write_new(root/'manifest.json',manifest);contract.verify_inputs(root,sha(root/'manifest.json'))
                name=next(n for n in payload if n.startswith('model-inputs/'))
                body=json.loads((root/name).read_bytes());body['response_format']={'type':'json_object'}
                (root/name).write_bytes(canonical(body));manifest['files'][name]=sha(root/name)
                (root/'manifest.json').write_bytes(canonical(manifest))
                with self.assertRaisesRegex(ValueError,'frozen pilot request'):contract.verify_inputs(root,sha(root/'manifest.json'))
                changed=deepcopy(values);changed.reverse()
                with self.assertRaisesRegex(ValueError,'ordinal-selected'):contract.check_checkpoints(changed)

    def test_valid_run_has_all_eight_phases_and_invalid_run_keeps_missing_phases(self):
        for invalid in (False,True):
            with self.subTest(invalid=invalid),tempfile.TemporaryDirectory()as folder,ExitStack()as stack:
                inputs,output,_=create(folder,invalid=invalid);protocol_patches(stack)
                result=audit_study(output,inputs,token_audit=lambda _:100,replay_factory=lambda cp,_:ScriptEngine(cp))
                self.assertEqual(result['phase_coverage'],dict(scheduled=8,reached=4 if invalid else 8,valid=0 if invalid else 8))
                self.assertEqual(result['format_coverage_complete'],not invalid)
                self.assertTrue(result['format_only']);self.assertFalse(result['outcome_claim_permitted'])

    def test_phase_and_schema_mutations_refused_even_after_rehash(self):
        with tempfile.TemporaryDirectory()as folder:
            _,out,_=create(folder);cp=checkpoints()[0];variant=cp['order'][0]
            events=lines(out/(cp['checkpoint_id']+'-'+variant+'.jsonl'))
            from research.action_effect_choice_v2.interface import candidates
            pair=candidates(cp,0)
            for mode in ('phase','schema','previous_first_answer'):
                changed=deepcopy(events);event=[e for e in changed if e['kind']=='request'][1]
                if mode=='schema':event['body']['response_format']={'type':'json_object'}
                else:
                    part=event['body']['messages'][1]['content'][-1];value=json.loads(part['text'])
                    if mode=='phase':value['study_phase']['study_decision_index']=0
                    else:value['previous_selected_forecast']['study_decision_index']=1
                    part['text']=json.dumps(value)
                event['request_sha256']=digest(event['body'])
                with self.subTest(mode=mode),self.assertRaises(ValueError):audit_case(cp,pair,variant,changed,ScriptEngine(cp))

    def test_terminal_after_first_action_retains_valid_but_incomplete_phase_coverage(self):
        original_dispatch=ScriptEngine.dispatch
        def terminal_dispatch(engine,action):
            result=original_dispatch(engine,action)
            if len(engine.actions)>len(engine.value['prefix']):
                engine.current['state']=result['state']='GAME_OVER'
            return result
        with tempfile.TemporaryDirectory()as folder,ExitStack()as stack:
            stack.enter_context(patch.object(ScriptEngine,'dispatch',new=terminal_dispatch))
            inputs,out,_=create(folder);protocol_patches(stack)
            result=audit_study(out,inputs,token_audit=lambda _:100,replay_factory=lambda cp,_:ScriptEngine(cp))
            self.assertEqual(result['phase_coverage'],dict(scheduled=8,reached=4,valid=4))
            self.assertEqual(result['continuation_dispatches'],4)
            self.assertFalse(result['format_coverage_complete'])
            self.assertTrue(all(row['reason']=='game_over'for row in result['conditions']))


if __name__=='__main__':unittest.main()
