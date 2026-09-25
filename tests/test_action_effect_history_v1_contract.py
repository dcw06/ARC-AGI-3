"""Common baseline and history-arm request construction (no model calls)."""
import json,re,unittest
from research.action_effect_history_v1 import contract as c
from research.action_effect_v1.records import effect_record,EffectHistory
from research.action_effect_v1 import fixtures

def runtime():
    from certification.phase4_integrated_v2.contract import unpack
    from agent.state import GameRuntimeState
    value=json.loads((fixtures.ROOT/'reports/integrated_case_v1/initial_observation.json').read_bytes())
    return GameRuntimeState(unpack(value),action_budget_limit=12)

def history(steps):
    h=EffectHistory(limit=16);g=fixtures.base()
    for action,post in steps:h.append(effect_record(fixtures.observation([g]),action,post))
    return h

ACK=lambda frames,**kw:{'status':'acknowledged','post':fixtures.observation(frames,**kw)}

class ContractTests(unittest.TestCase):
    def test_arms_differ_only_by_history_field(self):
        rt=runtime();h=history([(fixtures.click(16,16),ACK([fixtures.base()]))])
        base=c.policy_request(rt,'baseline',h);hist=c.policy_request(rt,'history',h)
        self.assertEqual(c.strip_history(hist),base)
        self.assertNotIn(c.HISTORY_FIELD,json.loads(base['messages'][1]['content'])['observation'])
        self.assertEqual(base['messages'][0],hist['messages'][0]);self.assertEqual(base['response_format'],hist['response_format'])
    def test_prompt_matches_actual_interface_and_states_no_effects(self):
        from arcengine import GameAction
        simple={a.value for a in GameAction if a.is_simple() and a.value!=0};complex_={a.value for a in GameAction if a.is_complex()}
        self.assertEqual((simple,complex_),({1,2,3,4,5,7},{6}))
        p=c.SYSTEM_PROMPT
        self.assertIn('ACTION6 is the only action that takes arguments',p)
        self.assertIn('Every other action (1, 2, 3, 4, 5, 7) takes empty action_data',p)
        self.assertIn('x is the column counted left to right',p);self.assertIn('y is the row counted top to bottom',p)
        self.assertIn('integers 0 to 63',p);self.assertIn('current_grid[y][x]',p)
        self.assertIn('does not mean its effect is known',p)
        for word in ('move','moves','up','down','arrow','direction','click on','objects','game object','ar25','level'):
            self.assertIsNone(re.search(r'\b'+re.escape(word)+r'\b',p.lower()),word)
    def test_new_baseline_departs_from_r8_control_only_in_system_prompt(self):
        from certification.phase4_integrated_v2.contract import baseline_request
        rt=runtime();old=baseline_request(rt);new=c.policy_request(rt,'baseline')
        self.assertNotEqual(old['messages'][0],new['messages'][0])
        self.assertEqual(old['messages'][1],new['messages'][1])
        self.assertEqual({k:v for k,v in old.items() if k!='messages'},{k:v for k,v in new.items() if k!='messages'})
    def test_history_field_segment_limit_and_content(self):
        g=fixtures.base();moved=fixtures.moved(g,'A',1,0)
        steps=[(fixtures.plain(7),ACK([moved])),(fixtures.click(1,1),ACK([g])),(fixtures.click(2,2),{'status':'dispatch_failed','error':'x'}),
               (fixtures.plain(5),ACK([g])),(fixtures.plain(2),ACK([g]))]
        f=c.history_field(history(steps))
        self.assertEqual([e['step'] for e in f['entries']],[1,2,3,4]);self.assertEqual(f['omitted_entries'],1)
        self.assertIsNone(f['entries'][1]['changed_cells_by_frame']);self.assertEqual(f['entries'][1]['status'],'dispatch_failed')
        self.assertEqual(f['entries'][0]['action_data'],{'x':1,'y':1})
        text=json.dumps(f).lower()
        for word in ('sha256','hash','recommend','probe','current_grid','arrow'):self.assertNotIn(word,text)
        self.assertEqual(f['computed_by'],'deterministic frame-comparison tool, not the model')
        # After a level change the next decision starts an empty segment.
        f=c.history_field(history(steps+[(fixtures.plain(1),ACK([g],levels=1))]))
        self.assertEqual((f['entries'],f['omitted_entries']),([],0))
        self.assertEqual(c.history_field(None)['entries'],[])
    def test_prompt_budget_shape(self):
        rt=runtime();r=c.policy_request(rt,'history',EffectHistory())
        self.assertEqual((r['max_tokens'],r['temperature'],r['seed']),(128,0,0))
        with self.assertRaises(ValueError):c.policy_request(rt,'target')

if __name__=='__main__':unittest.main()
