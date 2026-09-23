import json,tempfile,time,threading,unittest
from pathlib import Path
from types import SimpleNamespace
from certification.phase4_integrated_v2.service import audited_completion
from certification.phase4_integrated_v2.response_evidence import ResponseValidationError
from certification.phase4_integrated_v2.bridge import BridgeServer,ModelProxy
class Tokenizer:
 def apply_chat_template(self,*a,**kw):return [1,2,3]
class ServiceTests(unittest.TestCase):
 def test_transport_finish_reason(self):
  from certification.phase4_integrated_v2.model_transport import OpenAICompatibleCompletionClient
  from unittest.mock import Mock
  for reason in ('stop','length',None):
   session=Mock();session.post.return_value.json.return_value={'choices':[{'message':{'content':'{"objects":['},'finish_reason':reason}],
    'usage':{'prompt_tokens':3,'completion_tokens':10}}
   result=OpenAICompatibleCompletionClient(session=session).complete({})
   self.assertEqual(result.finish_reason,reason);self.assertEqual(result.content,'{"objects":[')
 def test_bridge_success_retains_partial_reason(self):
  from certification.phase4_integrated_v2.model_transport import CompletionResult
  class Service:
   def complete(self,request):return audited_completion(Tokenizer(),request,lambda r:CompletionResult('{"objects":[',3,10,0,'length'))
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);server=BridgeServer(str(root/'model.sock'),Service(),time.monotonic()+10,root/'cancel')
   thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    proxy=ModelProxy(root,'unused',time.monotonic()+10,root/'cancel');proxy.started=True
    result=proxy.complete({'messages':[{'role':'user','content':'test'}],'max_tokens':2048})
    self.assertEqual(result.finish_reason,'length');self.assertEqual(proxy.audit_records[-1]['finish_reason'],'length')
    self.assertEqual(result.content,'{"objects":[')
   finally:server.shutdown();server.server_close();thread.join()
 def test_startup_and_structured_mismatch_retained(self):
  for cap in (128,2048):
   request={'messages':[{'role':'user','content':'test'}],'max_tokens':cap}
   retained=[]
   with self.assertRaises(ResponseValidationError) as ctx:
    audited_completion(Tokenizer(),request,lambda r:SimpleNamespace(content='{"test":1}',prompt_tokens=4,completion_tokens=3,finish_reason='length'),retain=retained.append)
   self.assertEqual(ctx.exception.response_evidence,retained[0]);self.assertEqual(retained[0]['audit']['server_prompt_tokens'],4)
 def test_bridge_preserves_mismatch(self):
  class Service:
   def complete(self,request):return audited_completion(Tokenizer(),request,lambda r:SimpleNamespace(content='received',prompt_tokens=4,completion_tokens=3,finish_reason='length'))
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);server=BridgeServer(str(root/'model.sock'),Service(),time.monotonic()+10,root/'cancel')
   thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    proxy=ModelProxy(root,'unused',time.monotonic()+10,root/'cancel');proxy.started=True
    with self.assertRaises(ResponseValidationError) as c:proxy.complete({'messages':[{'role':'user','content':'test'}],'max_tokens':1024})
    self.assertEqual(c.exception.response_evidence['response_content'],'received')
    self.assertEqual(c.exception.response_evidence['audit']['finish_reason'],'length')
   finally:server.shutdown();server.server_close();thread.join()
 def test_context_rejects_before_inference(self):
  class Large:
   def apply_chat_template(self,*a,**kw):return [1]*60001
  with self.assertRaises(ValueError):audited_completion(Large(),{'messages':[],'max_tokens':2048},lambda r:self.fail('inference entered'))
if __name__=='__main__':unittest.main()
