import json,tempfile,time,threading,unittest
from pathlib import Path
from types import SimpleNamespace
from certification.phase4_integrated_v1.service import audited_completion
from certification.phase4_integrated_v1.response_evidence import ResponseValidationError
from certification.phase4_integrated_v1.bridge import BridgeServer,ModelProxy
class Tokenizer:
 def apply_chat_template(self,*a,**kw):return [1,2,3]
class ServiceTests(unittest.TestCase):
 def test_startup_and_structured_mismatch_retained(self):
  for cap in (128,2048):
   request={'messages':[{'role':'user','content':'test'}],'max_tokens':cap}
   retained=[]
   with self.assertRaises(ResponseValidationError) as ctx:
    audited_completion(Tokenizer(),request,lambda r:SimpleNamespace(content='{"test":1}',prompt_tokens=4,completion_tokens=3),retain=retained.append)
   self.assertEqual(ctx.exception.response_evidence,retained[0]);self.assertEqual(retained[0]['audit']['server_prompt_tokens'],4)
 def test_bridge_preserves_mismatch(self):
  class Service:
   def complete(self,request):return audited_completion(Tokenizer(),request,lambda r:SimpleNamespace(content='received',prompt_tokens=4,completion_tokens=3))
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);server=BridgeServer(str(root/'model.sock'),Service(),time.monotonic()+10,root/'cancel')
   thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    proxy=ModelProxy(root,'unused',time.monotonic()+10,root/'cancel');proxy.started=True
    with self.assertRaises(ResponseValidationError) as c:proxy.complete({'messages':[{'role':'user','content':'test'}],'max_tokens':1024})
    self.assertEqual(c.exception.response_evidence['response_content'],'received')
   finally:server.shutdown();server.server_close();thread.join()
 def test_context_rejects_before_inference(self):
  class Large:
   def apply_chat_template(self,*a,**kw):return [1]*60001
  with self.assertRaises(ValueError):audited_completion(Large(),{'messages':[],'max_tokens':2048},lambda r:self.fail('inference entered'))
if __name__=='__main__':unittest.main()
