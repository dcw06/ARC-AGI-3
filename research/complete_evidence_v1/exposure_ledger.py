"""Exposure ledger: what has already been done with each of the 25 games in this study.

Built from the study's own data files, so the lists of sampled records and decisions are exact.
Usage: exposure_ledger.py <reports_dir> <out_dir>
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

DEVELOPMENT = ('bp35', 'lf52', 'ls20', 'tn36', 'cd82', 'ka59', 'vc33')
ALL_GAMES_AUTOMATED = [
    'Saved stateless run of 100 actions exists; every request and frame is on disk (this is the source data).',
    'Phase 1 size measurement formatted and token-counted every record and every decision (records.csv, '
    'decisions.csv, published). records.csv holds, per record, the action ID, frame count, level and the number '
    'of cells changed: outcome-derived values, used only in aggregate.',
    'Repeat audits compared every board with every earlier board (per-game counts published).',
    'Per-game outcome totals were printed and published: levels completed, last level-up action, actions that did nothing.',
    'Loss audit of 2026-11-09 used public recordings of other agents on this game (action counts per level).']
SPECIFIC = {
    'tn36': ['Frames and the agent\'s notes inspected in detail (tn36_case.py: all 26 "run" presses).',
             'First and revised worked examples: decisions 54 and 97 with records 19, 39, 60.',
             'Readability rehearsal: decision 46 with record 12; correct answers published; four Opus responses.'],
    'bp35': ['Agent notes read at actions 60 and 98.', 'A local solver derived from the game source exists (earlier project work).',
             'Earlier Tycho and arc-skill experiments on this game.'],
    'lf52': ['Agent notes read at actions 30 and 99.', 'Earlier Tycho comparison on this game.'],
    'ls20': ['Earlier project branches built ls20-specific agents (per project notes).'],
}
PACKET = {'bp35': (17, 24), 'lf52': (19, 53), 'ls20': (67, 92), 'cd82': (40, 97), 'ka59': (36, 53), 'vc33': (88, 99)}


def main(reports_dir, out_dir):
    reports, out = Path(reports_dir), Path(out_dir)
    p1 = reports / 'complete_evidence_phase1_v1/data'
    sample = defaultdict(list)
    for row in csv.DictReader(open(p1 / 'opus_sample_v2.csv')):
        sample[row['game']].append({'record': int(row['event']), 'paired_decision': int(row['decision'])})
    pair_decisions, pair_records = defaultdict(set), defaultdict(set)
    for row in csv.DictReader(open(p1 / 'scorer_pairs_v2.csv')):
        pair_decisions[row['game']].add(int(row['decision']))
        pair_records[row['game']].add(int(row['event']))
    over = defaultdict(list)
    for row in json.loads((out / 'q_key2_cross_game.json').read_text())['summary']['q2_over_limit']:
        over[row['game']].append(row['decision'])
    frozen = json.loads((reports / 'complete_evidence_format_check_v1/cases_frozen.json').read_text())
    subset = set(json.loads((out / 'review_packet/subset_frozen.json').read_text())['subset'])
    dev_cases = defaultdict(list)
    for c in frozen['cases']:
        dev_cases[c['game']].append({'case': c['case'], 'type': c['type'], 'decision': c['decision_after_actions'],
                                     'records': [e['event'] for e in c['earlier_records']],
                                     'in_full_review_subset': c['case'] in subset})
    games = sorted(sample)
    ledger = {'date': '2026-11-14', 'source_run': 'opus55-competition-20261106T054112Z',
              'applies_to_every_game': ALL_GAMES_AUTOMATED,
              'statement': ('No game is wholly untouched. The 18 games outside the development set have format-development '
                            'exposure: automated measurement of every record, exact token counts on 8 sampled records each, '
                            'and description sizes on 20 sampled decisions each. No person and no reviewer has inspected what '
                            'specific actions did in those games, and no prediction target has been chosen or opened there. '
                            'They may still supply reserved prediction cases if target answers stay concealed and unused, '
                            'and the cases avoid the sampled records and decisions listed here.'),
              'games': {}}
    for game in games:
        entry = {'tier': 'development' if game in DEVELOPMENT else 'format-exposed',
                 'opus_token_sample_records': sorted(sample[game], key=lambda r: r['record']),
                 'scorer_sample_decisions': sorted(pair_decisions[game]),
                 'scorer_sample_records': sorted(pair_records[game]),
                 'description_rule_check_decisions_over_limit_seen_individually': sorted(over.get(game, [])),
                 'development_cases': dev_cases.get(game, []),
                 'reading_packet_record_and_decision': list(PACKET[game]) if game in PACKET else None,
                 'specific_inspection': SPECIFIC.get(game, [])}
        ledger['games'][game] = entry
    (out / 'exposure_ledger.json').write_text(json.dumps(ledger, indent=1))
    lines = ['| Game | Tier | Token-count sample (records) | Scorer sample (decisions / records) | Development cases | Other specific exposure |',
             '|---|---|---|---|---|---|']
    for game in games:
        e = ledger['games'][game]
        other = len(e['specific_inspection']) + (1 if e['reading_packet_record_and_decision'] else 0) + (
            1 if e['description_rule_check_decisions_over_limit_seen_individually'] else 0)
        lines.append('| %s | %s | %d | %d / %d | %s | %s |' % (
            game, e['tier'], len(e['opus_token_sample_records']), len(e['scorer_sample_decisions']),
            len(e['scorer_sample_records']), ', '.join(c['case'] for c in e['development_cases']) or 'none',
            '%d item%s' % (other, '' if other == 1 else 's') if other else 'none'))
    (out / 'exposure_ledger_table.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    print({t: sum(1 for g in games if ledger['games'][g]['tier'] == t) for t in ('development', 'format-exposed')})


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
