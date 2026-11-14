"""Rerender the 20 frozen development cases with B version 2 (M-ref-v2) and measure them.

Same cases file as the first check. Same rule for every case; no case-specific repair; failures kept.
Budgets: 2,048 working, 1,024 secondary. 512 is no longer an active budget for this representation; its
result is still recorded. Scorer limits: 4,096 description / 8,192 pair (provisional), with the original
description rule (Q-key-v1) and the shift-capable one (Q-key-v2) side by side.
No Opus generation request is made; Opus token counts are estimates from the free counting endpoint.

Usage: dev_format_check_v2.py <events.jsonl> <cases_frozen.json> <first_results.json> <out_dir>
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research'))
from complete_evidence_v1 import formats_v2 as F, records  # noqa: E402
from complete_evidence_v1.m0_example import REVISION, SCORER  # noqa: E402
from complete_evidence_v1.opus_count import MODEL, OpusCounter  # noqa: E402

ACTIVE, RETIRED = (2048, 1024), (512,)
Q_LIMIT, PAIR_LIMIT, PAIR_SPECIAL = 4096, 8192, 4


def same_frames(decoded, real):
    return len(decoded) == len(real) and all(a.shape == b.shape and np.array_equal(a, b) for a, b in zip(decoded, real))


def main(events_path, cases_path, first_path, out_dir):
    out_dir = Path(out_dir)
    (out_dir / 'packs').mkdir(parents=True, exist_ok=True)
    frozen = json.loads(Path(cases_path).read_text())
    first = {c['case']: c for c in json.loads(Path(first_path).read_text())['cases']}
    games = {k.split('-')[0]: v for k, v in records.load_run(events_path).items()}
    counter = OpusCounter()
    tok = Tokenizer.from_file(hf_hub_download(SCORER, 'tokenizer.json', revision=REVISION))
    tok.no_truncation()

    def scorer_tokens(text):
        return len(tok.encode(text, add_special_tokens=False).ids)

    results = []
    for case in frozen['cases']:
        game, decision = case['game'], case['decision_after_actions']
        data = games[game]
        recs = data['records']
        done = recs[:decision]
        current = done[-1]['response_frames'][-1]
        assert hashlib.sha256(current.tobytes()).hexdigest() == case['current_board_cells_sha256']
        initial = np.asarray(data['initial']['frames'][-1], dtype=np.uint8)
        q1 = scorer_tokens(F.q_key(initial, done[-1]['legal_after'], done, 2))
        q2_text = F.q_key2(initial, done[-1]['legal_after'], done, 2)
        q2 = scorer_tokens(q2_text)
        q2_lossless = True
        for recent in done[-2:]:
            before, _, frames = F.decode(F.recent_q2(recent, current), current=current)
            q2_lossless &= bool(np.array_equal(before, recent['before_frame']) and same_frames(frames, recent['response_frames']))
        chosen = [recs[e['event'] - 1] for e in case['earlier_records']]
        texts = [F.m_ref2(r, current) for r in chosen]
        row = {k: case[k] for k in ('case', 'type', 'game', 'decision_after_actions')}
        row.update(reference_board={'observation': case['current_board_observation'],
                                    'cells_sha256': case['current_board_cells_sha256']}, records=[])
        for r, text, src in zip(chosen, texts, case['earlier_records']):
            before, _, frames = F.decode(text, current=current)
            ok = bool(np.array_equal(before, r['before_frame']) and same_frames(frames, r['response_frames']))
            record_scorer = scorer_tokens(text)
            row['records'].append({
                'event': r['event_seq'], 'frames': len(r['response_frames']), 'start_board': F.start_mode(text),
                'share_of_board_differing_from_current': src['share_of_board_differing'],
                'reconstructs_all_frames': ok,
                'opus_tokens': counter.count(text, 'format check v2 %s B2 e%d' % (case['case'], r['event_seq'])),
                'scorer_record_tokens': record_scorer,
                'pair_tokens': {'Q-key-v1': q1 + record_scorer + PAIR_SPECIAL, 'Q-key-v2': q2 + record_scorer + PAIR_SPECIAL}})
        pack = F.pack_b2(game, chosen[0]['trajectory_id'], decision, chosen, texts)
        (out_dir / 'packs' / ('%s_B2.txt' % case['case'])).write_text(pack + '\n')
        tokens = counter.count(pack, 'format check v2 %s pack B2' % case['case'])
        modes = sorted({e['start_board'] for e in row['records']})
        row.update(
            pack={'opus_tokens': tokens, 'modes': modes, 'mixed_modes': len(modes) > 1,
                  'records_opus_tokens': sum(e['opus_tokens'] for e in row['records']),
                  'fits_active': {str(b): tokens <= b for b in ACTIVE},
                  'fits_retired_512': tokens <= 512,
                  'all_records_reconstruct': all(e['reconstructs_all_frames'] for e in row['records']),
                  'sha256': hashlib.sha256(pack.encode()).hexdigest()},
            first_check={'A_pack': first[case['case']]['formats']['A']['pack_opus_tokens'],
                         'B1_pack': first[case['case']]['formats']['B']['pack_opus_tokens']},
            description={'Q-key-v1': q1, 'Q-key-v2': q2, 'Q-key-v2_lossless': q2_lossless,
                         'Q-key-v2_uses_shift': 'shifted' in q2_text,
                         'fits_4096': {'Q-key-v1': q1 <= Q_LIMIT, 'Q-key-v2': q2 <= Q_LIMIT}},
            pairs_fit_8192={v: all(q <= Q_LIMIT and e['pair_tokens'][v] <= PAIR_LIMIT for e in row['records'])
                            for v, q in (('Q-key-v1', q1), ('Q-key-v2', q2))})
        results.append(row)
    summary = {'opus_model': MODEL, 'scorer': SCORER, 'scorer_revision': REVISION,
               'representation': 'M-ref-v2 with reading instructions version 3 (pack_b2)',
               'budgets_active': ACTIVE, 'budgets_retired_recorded_only': RETIRED,
               'scorer_limits_provisional': {'description': Q_LIMIT, 'pair': PAIR_LIMIT},
               'cases_file_sha256': hashlib.sha256(Path(cases_path).read_bytes()).hexdigest(),
               'counts_are_estimates': True, 'opus_generation_requests_sent': 0, 'cases': results}
    (out_dir / 'results.json').write_text(json.dumps(summary, indent=1))
    print('case type game | frames | modes | B2 rec/pack (B1 pack, A pack) | 2048 1024 512 | recon | Q1 Q2 lossless shift | pairs Q1/Q2')
    for r in results:
        p = r['pack']
        print(r['case'], r['type'][:5], r['game'], '|', [e['frames'] for e in r['records']], '|', p['modes'], '|',
              p['records_opus_tokens'], p['opus_tokens'], (r['first_check']['B1_pack'], r['first_check']['A_pack']), '|',
              p['fits_active']['2048'], p['fits_active']['1024'], p['fits_retired_512'], '|', p['all_records_reconstruct'], '|',
              r['description']['Q-key-v1'], r['description']['Q-key-v2'], r['description']['Q-key-v2_lossless'],
              r['description']['Q-key-v2_uses_shift'], '|', r['pairs_fit_8192'])


if __name__ == '__main__':
    main(*sys.argv[1:5])
