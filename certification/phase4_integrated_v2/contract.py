"""Preserve exact historical control request builder."""
from certification.phase4_transient_v2.contract import pack,unpack,request_for
from certification.phase4_integrated_v2.request_contract import protocol,digest,make_request
def baseline_request(state):return request_for(state,'control',seed=0,previous_transition=None)
