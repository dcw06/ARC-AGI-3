"""M0: one complete worked example, from stored records to the evidence Opus would be shown.

Usage: m0_example.py <events.jsonl> <game> <decision> <out_dir> [needed_event ...]
`decision` is the number of completed actions when the choice is made. `needed_event` values are the
reviewer's guess at which older records hold the needed evidence; they are used only to report ranks and
never enter scoring or selection. No Opus request is made: the example is saved-input-only.
"""
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research'))
from complete_evidence_v1 import formats, records  # noqa: E402
from complete_evidence_v1.measure_opus_sizes import MODEL as OPUS, api_key  # noqa: E402

SCORER, REVISION = 'BAAI/bge-reranker-v2-m3', '953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e'
WINDOW, LAMBDA, OPUS_LIMITS = 2, 0.75, (512, 1024, 2048)
VARIANTS = {  # name: (description builder, memory builder, description limit, pair limit)
    'A starting spec (Q-exec-rle-v1 F-all + M-rle-v1 F-all, 768/2048)': (
        lambda init, legal, done: formats.q_exec(init, legal, done, 'F-all', WINDOW),
        lambda r: formats.m_rle(r, 'F-all'), 768, 2048),
    'B merged rows, last frame only (F-end), 4096/8192': (
        lambda init, legal, done: formats.q_exec(init, legal, done, 'F-end', WINDOW, True),
        lambda r: formats.m_rle(r, 'F-end', True), 4096, 8192),
    'C merged-row description + M-diff-v1 F-all, 4096/8192': (
        lambda init, legal, done: formats.q_exec(init, legal, done, 'F-end', WINDOW, True),
        lambda r: formats.m_diff(r, 'F-all'), 4096, 8192),
    'D merged-row description + M-diff-v1 F-end, 4096/8192': (
        lambda init, legal, done: formats.q_exec(init, legal, done, 'F-end', WINDOW, True),
        lambda r: formats.m_diff(r, 'F-end'), 4096, 8192),
}


def relative_rank(scores):
    s = np.asarray(scores, dtype=float)
    if s.size == 1:
        return np.ones(1)
    lower = (s[None, :] < s[:, None]).sum(1)
    equal = (s[None, :] == s[:, None]).sum(1) - 1
    return (lower + 0.5 * equal) / (s.size - 1)


def changed(record):
    before, final = record['before_frame'], record['response_frames'][-1]
    if before.shape != final.shape:
        return frozenset()
    ys, xs = np.nonzero(before != final)
    return frozenset(zip(ys.tolist(), xs.tolist(), final[ys, xs].tolist()))


def similarity(a, b):
    """Provisional sim-v0 (the protocol leaves the formula open): half same action and cell, half overlap
    of the cells changed and their new colours."""
    same_action = float(a['action'] == b['action'])
    ca, cb = changed(a), changed(b)
    overlap = len(ca & cb) / len(ca | cb) if ca | cb else 1.0
    return 0.5 * same_action + 0.5 * overlap


def select(cands, rank, cost, limit):
    """Shared rule: highest lambda*rank - (1-lambda)*max similarity to chosen, complete records only."""
    chosen, used, skipped = [], 0, []
    left = list(range(len(cands)))
    while left:
        def priority(i):
            penalty = max((similarity(cands[i], cands[j]) for j in chosen), default=0.0)
            return LAMBDA * rank[i] - (1 - LAMBDA) * penalty
        fitting = [i for i in left if used + cost[i] <= limit]
        skipped += [cands[i]['event_seq'] for i in left if i not in fitting and cost[i] > limit and not chosen]
        if not fitting:
            break
        best = max(fitting, key=lambda i: (priority(i), -cands[i]['event_seq']))
        if priority(best) <= 0:
            break
        chosen.append(best)
        used += cost[best]
        left.remove(best)
    return [cands[i]['event_seq'] for i in chosen], used, sorted(set(skipped))


def main(events_path, game, decision, out_dir, needed):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = next(v for k, v in records.load_run(events_path).items() if k.startswith(game))
    recs = data['records']
    done = recs[:decision]
    initial = np.asarray(data['initial']['frames'][-1], dtype=np.uint8)
    legal = done[-1]['legal_after']
    older = done[:-WINDOW]  # the last WINDOW responses are already in the shared input
    timing, report = {}, {'game': game, 'decision': decision, 'next_event': decision + 1,
                          'action_actually_taken': recs[decision]['action'] if decision < len(recs) else None,
                          'older_candidates': len(older), 'recent_window': WINDOW,
                          'reviewer_guess_needed_events': needed, 'opus_response': 'saved-input-only (no request made)',
                          'scorer': SCORER, 'scorer_revision': REVISION, 'variants': {}}

    start = time.time()
    tok = AutoTokenizer.from_pretrained(SCORER, revision=REVISION)
    device = 'mps' if torch.backends.mps.is_available() else 'cpu'
    model = AutoModelForSequenceClassification.from_pretrained(SCORER, revision=REVISION).to(device).eval()
    timing['load_model_s'] = round(time.time() - start, 1)
    report['hardware'] = {'machine': platform.machine(), 'device': device, 'torch': torch.__version__,
                          'max_position_embeddings': model.config.max_position_embeddings}

    import anthropic
    client = anthropic.Anthropic(api_key=api_key(), max_retries=6)

    def opus_tokens(text):
        return client.messages.count_tokens(model=OPUS, messages=[{'role': 'user', 'content': text}]).input_tokens

    for name, (q_build, m_build, q_limit, pair_limit) in VARIANTS.items():
        tag = name[0]
        start = time.time()
        query = q_build(initial, legal, done)
        memories = [m_build(r) for r in older]
        timing[tag + '_format_s'] = round(time.time() - start, 2)
        q_len = len(tok(query, add_special_tokens=False)['input_ids'])
        rows, ids_out = [], {}
        start = time.time()
        for r, text in zip(older, memories):
            enc = tok(query, text, truncation=False, return_tensors='pt')
            n = int(enc['input_ids'].shape[1])
            ok = q_len <= q_limit and n <= pair_limit
            row = {'event': r['event_seq'], 'action': formats._action_text(r['action']),
                   'frames': len(r['response_frames']), 'pair_tokens': n, 'accepted': ok, 'score': None}
            if ok:
                with torch.no_grad():
                    logit = model(**{k: v.to(device) for k, v in enc.items()}).logits.float().view(-1)[0].item()
                row['score'] = logit
                ids_out['e%04d' % r['event_seq']] = enc['input_ids'][0].numpy().astype(np.int32)
            rows.append(row)
        timing[tag + '_score_s'] = round(time.time() - start, 1)
        (out_dir / ('%s_description.txt' % tag)).write_text(query)
        entry = {'description_tokens': q_len, 'description_limit': q_limit, 'pair_limit': pair_limit,
                 'description_fits': q_len <= q_limit, 'pairs': len(rows),
                 'pairs_accepted': sum(r['accepted'] for r in rows),
                 'pair_tokens_min_median_max': [int(np.min([r['pair_tokens'] for r in rows])),
                                                float(np.median([r['pair_tokens'] for r in rows])),
                                                int(np.max([r['pair_tokens'] for r in rows]))]}
        scored = [i for i, r in enumerate(rows) if r['accepted']]
        if scored:
            np.savez_compressed(out_dir / ('%s_input_ids.npz' % tag), **ids_out)
            scores = [rows[i]['score'] for i in scored]
            rank = relative_rank(scores)
            order = sorted(range(len(scored)), key=lambda j: -scores[j])
            for position, j in enumerate(order, 1):
                rows[scored[j]]['rank'] = position
            entry['score_min_median_max'] = [round(min(scores), 3), round(float(np.median(scores)), 3),
                                             round(max(scores), 3)]
            entry['top10_events'] = [rows[scored[j]]['event'] for j in order[:10]]
            entry['needed_event_ranks'] = {str(e): next((r.get('rank') for r in rows if r['event'] == e), None)
                                           for e in needed}
            start = time.time()
            cands = [older[i] for i in scored]
            cost = [opus_tokens(memories[i]) for i in scored]
            timing[tag + '_opus_count_s'] = round(time.time() - start, 1)
            for i, c in zip(scored, cost):
                rows[i]['opus_tokens'] = c
            entry['opus_tokens_per_record_min_median_max'] = [min(cost), float(np.median(cost)), max(cost)]
            entry['selection'] = {}
            for limit in OPUS_LIMITS:
                chosen, used, skipped = select(cands, rank, cost, limit)
                entry['selection'][str(limit)] = {
                    'selected_events': chosen, 'opus_tokens_used': used,
                    'needed_events_included': [e for e in needed if e in chosen],
                    'records_too_big_for_limit': sum(c > limit for c in cost)}
                by_event = {r['event_seq']: m for r, m in zip(older, memories)}
                (out_dir / ('%s_actor_pack_%d.txt' % (tag, limit))).write_text(
                    formats.READING_NOTE + '\n\n' + '\n\n'.join(by_event[e] for e in sorted(chosen)))
        entry['rows'] = rows
        report['variants'][name] = entry
    report['timing'] = timing
    (out_dir / 'm0.json').write_text(json.dumps(report, indent=1))
    for name, entry in report['variants'].items():
        print('\n' + name)
        print({k: v for k, v in entry.items() if k != 'rows'})
    print(timing, report['hardware'])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], [int(a) for a in sys.argv[5:]])
