from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import json
from pathlib import Path
import socket
import struct
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from certification.phase4_v7.bridge import BridgeServer, ModelProxy, receive, request_hash

@dataclass
class Reply:
    content:str='ok'
    prompt_tokens:int=3
    completion_tokens:int=1
    elapsed_seconds:float=.01

class Service:
    def complete(self,request):
        return Reply(),{'request_sha256':request_hash(request),'tokenizer_prompt_tokens':3,
                        'server_prompt_tokens':3,'server_completion_tokens':1,'service_seconds':.01}

class BridgeTests(unittest.TestCase):
    def test_concurrent_requests_preserve_per_request_audits(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with BridgeServer(root/'model.sock',Service(),time.monotonic()+10,root/'cancel') as server:
                thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
                try:
                    proxy=ModelProxy(root,'unused',time.monotonic()+10,root/'cancel')
                    proxy.started=True
                    with ThreadPoolExecutor(max_workers=8) as pool:
                        results=list(pool.map(proxy.complete,[{'n':n} for n in range(32)]))
                    self.assertEqual(len(results),32)
                    self.assertEqual({r['request_sha256'] for r in proxy.audit_records},
                                     {request_hash({'n':n}) for n in range(32)})
                finally: server.shutdown(); thread.join()

    def test_cancel_and_deadline_reject_before_connect(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            proxy=ModelProxy(root,'unused',time.monotonic()-1,root/'cancel')
            with self.assertRaises(TimeoutError): proxy.call({'op':'ready'})
            proxy.deadline=time.monotonic()+10; (root/'cancel').touch()
            with self.assertRaises(TimeoutError): proxy.call({'op':'ready'})

    def test_forged_audit_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            proxy=ModelProxy(directory,'unused',time.monotonic()+10,Path(directory)/'cancel')
            proxy.started=True
            with patch.object(proxy,'call',return_value={'result':Reply().__dict__,
                'audit':{'request_sha256':'wrong'}}), self.assertRaises(ValueError):
                proxy.complete({'n':1})
            self.assertEqual(proxy.audit_records,[])

    def test_oversized_frame_rejected_before_payload(self):
        left,right=socket.socketpair()
        try:
            left.sendall(struct.pack('!I',2*1024*1024))
            with self.assertRaises(ValueError): receive(right)
        finally: left.close(); right.close()

    def test_model_imports_do_not_require_game_packages(self):
        import subprocess,sys
        code='''import sys
class Deny:
    def find_spec(self,fullname,*args):
        if fullname.split('.')[0] in ('arcengine','arc_agi'):
            raise RuntimeError('forbidden game import: '+fullname)
sys.meta_path.insert(0,Deny())
from certification.phase4_v7 import service,model_process,model_transport,model_artifact
'''
        result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
