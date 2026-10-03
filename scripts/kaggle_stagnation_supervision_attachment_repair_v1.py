"""Unapproved successor adapter repair; not wired to a launch entrypoint.
Historical R6 is unchanged. Fresh reviewed authority is required before use.
"""
"""Single SaveKernel POST. No CLI, SDK transport, redirect, retry, or credential logging."""
import base64
import hashlib
import json
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from scripts.submit_stagnation_supervision_v1_r6_once import durable_new

URL = 'https://api.kaggle.com/v1/kernels.KernelsApiService/SaveKernel'
SLUG = 'daichongwei06/arc3-stagnation-supervision-v1-authorization-r6'
MAX_RESPONSE = 262144


class OneShotSession(requests.Session):
    def __init__(self):
        super().__init__()
        self.trust_env = False
        self.used = False
        for scheme in ('http://', 'https://'):
            self.mount(scheme, HTTPAdapter(max_retries=Retry(total=0, connect=0, read=0,
                redirect=0, status=0, other=0, respect_retry_after_header=False)))

    def send(self, request, **kwargs):
        if self.used:
            raise PermissionError('HTTP request already attempted; no retry')
        self.used = True
        kwargs.update(allow_redirects=False, timeout=(30, 120), stream=True)
        return super().send(request, **kwargs)


def request_body(folder):
    from kagglesdk.kernels.types.kernels_api_service import ApiSaveKernelRequest
    folder=Path(folder);meta=json.loads((folder/'kernel-metadata.json').read_bytes())
    if (meta['id'] != SLUG or meta['is_private'] is not True or meta['enable_gpu'] is not True
            or meta['enable_tpu'] is not False or meta['enable_internet'] is not False
            or meta['code_file'] != 'profile.ipynb' or meta['language'] != 'python'
            or meta['kernel_type'] != 'notebook'):
        raise ValueError('frozen private R6 GPU metadata required')
    notebook=json.loads((folder/'profile.ipynb').read_bytes())
    if any(c.get('outputs') for c in notebook['cells'] if c['cell_type']=='code'):
        raise ValueError('notebook output not empty')
    r=ApiSaveKernelRequest()
    r.slug=meta['id'];r.new_title=meta['title'];r.text=json.dumps(notebook)
    r.language='python';r.kernel_type='notebook';r.is_private=True
    r.enable_gpu=True;r.enable_tpu=False;r.enable_internet=False
    r.dataset_data_sources=meta['dataset_sources'];r.competition_data_sources=meta['competition_sources']
    r.kernel_data_sources=[];r.model_data_sources=meta['model_sources'];r.category_ids=[]
    r.session_timeout_seconds=5400;r.machine_shape='NvidiaRtxPro6000'
    return json.dumps(ApiSaveKernelRequest.to_dict(r),separators=(',',':')).encode()


def credential_session():
    from scripts.phase4_install_kaggle import environment
    env=environment()  # local files only; values never logged
    s=OneShotSession()
    s.headers.update({'Content-Type':'application/json','User-Agent':'arc3-ssv-r6-single-post'})
    if env.get('KAGGLE_API_TOKEN'):
        s.headers['Authorization']='Bearer '+env['KAGGLE_API_TOKEN']
    else:
        s.auth=(env['KAGGLE_USERNAME'],env['KAGGLE_KEY'])
    return s


class KaggleNoRetry:
    def __init__(self, session, ledger, expected_body_sha256, *, source_observations):
        self.source_observations=source_observations
        self.session=session;self.ledger=Path(ledger);self.expected_body_sha256=expected_body_sha256

    def __call__(self, folder):
        if not (self.ledger/'submission-claim.json').is_file():
            raise PermissionError('durable submission claim required before HTTP')
        from scripts.stagnation_supervision_launch_preflight_v1 import validate_preflight, validate_response
        validate_preflight(folder, self.source_observations)
        body=request_body(folder)
        if hashlib.sha256(body).hexdigest()!=self.expected_body_sha256:
            raise ValueError('reviewed request body drift')
        evidence={'endpoint':URL,'method':'POST','request_body_sha256':self.expected_body_sha256,
                  'request_bytes':len(body),'maximum_http_attempts':1,'http_retries':0,'redirects':False,
                  'response_received':False}
        durable_new(self.ledger/'provider-request.json',evidence)
        try:
            response=self.session.post(URL,data=body)
            retained=bytearray()
            with response:
                for chunk in response.iter_content(8192):
                    retained.extend(chunk[:max(0,MAX_RESPONSE+1-len(retained))])
                    if len(retained)>MAX_RESPONSE:break
            truncated=len(retained)>MAX_RESPONSE
            body_received=bytes(retained[:MAX_RESPONSE])
            receipt={**evidence,'response_received':True,'http_status':response.status_code,
                     'response_base64':base64.b64encode(body_received).decode(),
                     'retained_response_sha256':hashlib.sha256(body_received).hexdigest(),
                     'response_truncated':truncated}
            durable_new(self.ledger/'provider-response.json',receipt)
            if truncated or not 200<=response.status_code<300:
                raise RuntimeError('provider response not accepted; no retry')
            value=json.loads(body_received)
            # Retain first. Provider errors or ambiguous success never cause another POST.
            try:
                validate_response(value)
            except ValueError:
                durable_new(self.ledger/'provider-attachment-disposition.json', {
                    'status':'provider_response_rejected_no_retry', 'consumed':True,
                    'response_sha256':hashlib.sha256(body_received).hexdigest(),
                    'requires_provider_reconciliation':True})
                raise
            return value
        except BaseException as exc:
            durable_new(self.ledger/'provider-transport-outcome.json',{
                'status':'unknown_or_rejected_no_retry','exception_type':type(exc).__name__,
                'http_attempted':self.session.used,'request_body_sha256':self.expected_body_sha256})
            raise
        finally:
            self.session.close()
