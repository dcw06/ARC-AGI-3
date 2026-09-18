"""Bounded proposal diagnostics; policy outputs and exceptions are unchanged."""
import hashlib
import json
from agent.e1_policy import E1Policy
from agent.diagnostics import classify_proposal_rejection


class PolicyEvidence:
    def __init__(self, client_id):
        self.client_id=client_id
        self.last=None
        self.failures=[]
        self.counts={}
        self.total=0

    def begin(self):
        self.last=None

    def received(self, request, result, request_id):
        if not isinstance(getattr(result,'content',None),str):
            self.last={'request_id':request_id,'invalid_completion_type':type(result).__name__}
            return
        raw=result.content.encode('utf-8')
        self.last={'request_id':request_id,
            'request_sha256':hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest(),
            'response_sha256':hashlib.sha256(raw).hexdigest(),'response_bytes':len(raw),
            'response_prefix':raw[:1024].decode('utf-8',errors='replace'),
            'response_truncated':len(raw)>1024,'completion_tokens':result.completion_tokens}

    def rejected(self, exc):
        category=classify_proposal_rejection(exc)
        self.total+=1
        self.counts[category]=self.counts.get(category,0)+1
        if len(self.failures)<8:
            self.failures.append({'category':category,'exception_type':type(exc).__name__,
                'message':str(exc)[:384],'completion':self.last})

    def summary(self):
        return {'client_id':self.client_id,'policy_failures':self.total,
            'categories':dict(self.counts),'examples':list(self.failures),
            'examples_omitted':self.total-len(self.failures),
            'limits':{'examples_per_client':8,'response_prefix_bytes':1024,'message_chars':384}}


class ObservedPolicy(E1Policy):
    def __init__(self, *, evidence, **kwargs):
        super().__init__(**kwargs)
        self.evidence=evidence

    def propose(self,state):
        self.evidence.begin()
        try:
            return super().propose(state)
        except Exception as exc:
            self.evidence.rejected(exc)
            raise
