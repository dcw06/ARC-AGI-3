"""Bounded Unix-domain transport. No model imports in the game process."""
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import socket
import socketserver
import struct
import subprocess
import sys
import threading
import time
from certification.phase4_transient_v1.response_evidence import ResponseValidationError,capture,checked

MAX_BYTES=1024*1024


def receive(sock,deadline=None):
    def exact(size):
        result=bytearray()
        while len(result)<size:
            if deadline is not None:
                remaining=deadline-time.monotonic()
                if remaining<=0: raise TimeoutError('bridge frame deadline')
                sock.settimeout(min(remaining,180))
            block=sock.recv(size-len(result))
            if not block: raise EOFError('incomplete bridge frame')
            result.extend(block)
        return bytes(result)
    size=struct.unpack('!I',exact(4))[0]
    if not 0<size<=MAX_BYTES: raise ValueError('bridge frame limit')
    return json.loads(exact(size))


def send(sock,value):
    data=json.dumps(value,allow_nan=False).encode()
    if len(data)>MAX_BYTES: raise ValueError('bridge frame limit')
    sock.sendall(struct.pack('!I',len(data))+data)


def request_hash(request):
    return hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest()


class BridgeServer(socketserver.ThreadingMixIn,socketserver.UnixStreamServer):
    daemon_threads=True
    request_queue_size=1
    block_on_close=False
    def __init__(self,path,service,deadline,cancel):
        self.service,self.deadline,self.cancel=service,deadline,Path(cancel)
        self.slots=threading.BoundedSemaphore(1)
        super().__init__(str(path),Handler)
        os.chmod(path,0o600)
        self.timeout=.2

    def process_request(self,request,address):
        if not self.slots.acquire(timeout=max(0,min(.25,self.deadline-time.monotonic()))):
            request.close()
            return
        try: super().process_request(request,address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self,request,address):
        try: super().process_request_thread(request,address)
        finally: self.slots.release()


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        server=self.server
        try:
            remaining=server.deadline-time.monotonic()
            if remaining<=0 or server.cancel.exists(): raise TimeoutError('bridge admission closed')
            self.request.settimeout(min(remaining,180))
            message=receive(self.request,server.deadline)
            if message=={'op':'ready'}:
                service=server.service
                reply={'artifact':service.artifact,'canary_audit':service.canary_audit,
                       'startup_seconds':service.startup_seconds}
            elif set(message)=={'op','request'} and message['op']=='complete':
                if server.cancel.exists() or time.monotonic()>=server.deadline:
                    raise TimeoutError('bridge admission closed')
                result,audit=server.service.complete(message['request'])
                if time.monotonic()>=server.deadline or server.cancel.exists():
                    raise ResponseValidationError('bridge completion after cancellation/deadline',capture(result.content,audit))
                reply={'result':asdict(result),'audit':audit}
            else: raise ValueError('invalid bridge operation')
            send(self.request,{'ok':True,'value':reply})
        except Exception as exc:
            reply={'ok':False,'error':type(exc).__name__+': '+str(exc)[:512]}
            if hasattr(exc,'response_evidence'):reply['response_evidence']=checked(exc.response_evidence)
            try: send(self.request,reply)
            except OSError: pass


class ModelProxy:
    def __init__(self,scratch,python,deadline,cancel):
        self.scratch=Path(scratch)
        self.path=self.scratch/'model.sock'
        self.python,self.deadline,self.cancel=str(python),deadline,Path(cancel)
        self.started=False
        self.audit_records=[]
        self.lock=threading.Lock()

    def call(self,message):
        remaining=self.deadline-time.monotonic()
        if remaining<=0 or self.cancel.exists(): raise TimeoutError('bridge admission closed')
        with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as sock:
            sock.settimeout(min(remaining,180))
            sock.connect(str(self.path))
            send(sock,message)
            reply=receive(sock,self.deadline)
        if not reply['ok']:
            if 'response_evidence' in reply:
                raise ResponseValidationError(reply['error'],reply['response_evidence'])
            raise RuntimeError(reply['error'])
        if time.monotonic()>=self.deadline or self.cancel.exists():
            value=reply.get('value',{})
            if 'result' in value and 'audit' in value:
                raise ResponseValidationError('bridge reply expired',capture(value['result']['content'],value['audit']))
            raise TimeoutError('bridge reply expired')
        return reply['value']

    def start(self):
        from certification.phase4_transient_v1.live_probes import require_live_authority
        require_live_authority()
        if self.path.exists() or hasattr(self,'process'): raise RuntimeError('bridge already claimed')
        env=dict(os.environ)
        # Restore GPU visibility only in the owned model-side process.
        original=env.pop('P4_MODEL_CUDA_VISIBLE_DEVICES',None)
        if original is None: env.pop('CUDA_VISIBLE_DEVICES',None)
        else: env['CUDA_VISIBLE_DEVICES']=original
        self.process=subprocess.Popen([self.python,'-m','certification.phase4_transient_v1.model_host',
            '--socket',str(self.path),'--scratch',str(self.scratch),'--deadline',str(self.deadline),
            '--cancel',str(self.cancel)],env=env)  # Inherit the supervised worker group and log pipe.
        until=min(self.deadline,time.monotonic()+900)
        while time.monotonic()<until:
            if self.cancel.exists() or self.process.poll() is not None: raise RuntimeError('model bridge startup failed')
            if self.path.exists():
                ready=self.call({'op':'ready'})
                self.artifact=ready['artifact']; self.canary_audit=ready['canary_audit']
                self.startup_seconds=ready['startup_seconds']; self.started=True
                return
            time.sleep(.05)
        raise TimeoutError('model bridge startup deadline')

    def complete(self,request):
        if not self.started: raise RuntimeError('model bridge not ready')
        from agent.e1_policy import CompletionResult
        value=self.call({'op':'complete','request':request})
        result=CompletionResult(**value['result']); audit=value['audit']
        if (audit['request_sha256']!=request_hash(request)
                or audit['tokenizer_prompt_tokens']!=result.prompt_tokens
                or audit['server_prompt_tokens']!=result.prompt_tokens
                or audit['server_completion_tokens']!=result.completion_tokens):
            raise ResponseValidationError('cross-process token audit mismatch',capture(result.content,
                {**audit,'bridge_result_prompt_tokens':result.prompt_tokens,
                 'bridge_result_completion_tokens':result.completion_tokens}))
        with self.lock: self.audit_records.append(audit)
        return result
