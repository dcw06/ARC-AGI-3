"""Bounded received-response evidence, usable on either side of the bridge."""
import hashlib,json,math

MAX_EVIDENCE_BYTES=262144

class ResponseValidationError(ValueError):
    def __init__(self,message,evidence):
        super().__init__(message)
        self.response_evidence=checked(evidence)

def observed(value):
    if value is None or type(value) in (bool,str,int,float):
        if isinstance(value,str):return value[:256]
        if type(value) is float and not math.isfinite(value):return {'type':'float','repr':repr(value)}
        if type(value) is int and value.bit_length()>128:return {'type':'int','repr':'exceeds 128 bits'}
        return value
    return {'type':type(value).__name__,'repr':repr(value)[:256]}

def capture(content,audit):
    raw=content.encode('utf-8')
    return checked({'response_content':raw[:32768].decode('utf-8',errors='ignore'),
        'response_sha256':hashlib.sha256(raw).hexdigest(),'response_bytes':len(raw),
        'response_truncated':len(raw)>32768,
        'audit':{k:observed(v) for k,v in audit.items()}})

def checked(evidence):
    if not isinstance(evidence,dict) or len(json.dumps(evidence,allow_nan=False).encode())>MAX_EVIDENCE_BYTES:
        raise ValueError('response evidence frame limit')
    return evidence

def emit(evidence):
    # The outer supervisor owns and bounds this process's stdout log.
    print(json.dumps({'diagnostic_received_response':checked(evidence)},allow_nan=False),flush=True)
