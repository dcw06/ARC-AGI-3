"""Independent keys for evidence comprehension v3, from raw frames and dispatch outcomes.

Imports only research/evidence_comprehension_v2/independent.py, which itself imports nothing. The v3 families
are v2 families, so v2's independent answers apply unchanged. v3 adds an independent recomputation of the B1
tool fields from raw rows (frames compared here, not the record code), and of the A1 computed control metadata
from the legal set, so the presented tool output can be checked against separate logic.
"""
from research.evidence_comprehension_v2 import independent as I2

answer = I2.answer
resolve = I2.resolve
synthetic_rows = I2.synthetic_rows
archived_rows = I2.archived_rows
window = I2.window


def tool_eligibility(shown):
    """[(step, rule, reason)] from raw rows; the precedence mirrors the documented rule."""
    result = []
    for i, r in enumerate(shown):
        if r['status'] == 'dispatch_failed':
            result.append((r['step'], 'not eligible', 'not delivered: the dispatch failed'))
            continue
        if r['status'] == 'outcome_unknown':
            result.append((r['step'], 'not eligible', 'its own outcome is unknown'))
            continue
        if r['moved'][-1]:
            result.append((r['step'], 'not eligible', 'its own final returned frame differed from the frame before it'))
            continue
        blocker = None
        for later in shown[i + 1:]:
            if later['status'] == 'outcome_unknown':
                blocker = (later['step'], 'had an unknown outcome')
                break
            if later['status'] == 'acknowledged' and later['moved'][-1]:
                blocker = (later['step'], 'changed the final frame')
                break
        if blocker is None:
            result.append((r['step'], 'eligible', 'acknowledged; final returned frame same as the frame before it; '
                                                  'no later shown entry changed the final frame or had an unknown outcome'))
        else:
            result.append((r['step'], 'not eligible', f'later step {blocker[0]} {blocker[1]}'))
    return result


def control_metadata(legal):
    return [(k, 'x and y, integers 0 to 63' if k == 6 else 'empty {}') for k in sorted(set(legal))]
