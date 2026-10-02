"""Text renderings of the packages a writer or reader would see (Track 2, evidence_memory_v1).

Character counts of these renderings are the context-budget unit in v1 (a stated proxy for tokens). Retired
entries are never shown to a reader; they stay in the audit trail.
"""
from research.evidence_memory_v1 import schema as S


def action_text(action):
    data = action['action_data']
    if data == S.ANY:
        return f"ACTION{action['action_id']}(any)"
    return f"ACTION{action['action_id']}(" + ','.join(f'{k}={data[k]}' for k in sorted(data)) + ')'


def record_line(record, info):
    return (f"step {info['step']} | level {info['level']} | segment {info['segment']} | state {info['state'][:10]} | "
            f"{action_text(info['action'])} | dispatch {info['dispatch']} | "
            f"visual {record['measurements']['visual_effect']['status']} | events {','.join(record['environment']['events'])}")


def records_text(records, idx):
    return '\n'.join(record_line(r, idx[S.record_key(r)]) for r in records)


def entry_line(entry):
    steps = lambda refs: ','.join(str(r['action_index']) for r in refs) or '-'
    return (f"[{entry['id']}] {entry['kind']}/{entry['status']} {S.claim_text(entry)} | evidence steps {steps(entry['evidence'])}"
            f" | counterevidence steps {steps(entry['counterevidence'])} | reviewed at step {entry['last_reviewed_step']}")


def memory_text(entries):
    return '\n'.join(entry_line(e) for e in entries if e['status'] != S.RETIRED)
