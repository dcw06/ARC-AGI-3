"""Build the staged review packet for the 12 full-history development decisions (protocol G3 subset).

Subset: three cases from each of the four contrasting types (level/reset, delayed, conflicting, spatial),
from three different games within each type, chosen by a fixed seed from the 20 frozen cases.

Each case folder is split so a reviewer meets the material in the protocol's order:
  stage1/  the common decision-time input only (text as the model would get it, plus a picture view)
  stage2/  every past action record up to the decision, as pictures; nothing marks which were selected
  stage3/  the rendered older-memory pack (B version 2) and which records it holds
  stage4/  the effect type assigned by rule
Nothing from after the decision appears anywhere, and no format result, score or answer is included.

Usage: review_packet.py <events.jsonl> <cases_frozen.json> <format_check_v2_dir> <out_dir>
"""
import hashlib
import json
import random
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research'))
from complete_evidence_v1 import records  # noqa: E402

SEED, PER_TYPE = 20261121, 3
TYPES = ('level/reset', 'delayed', 'conflicting', 'spatial')
HEX = '0123456789abcdef'
PALETTE = ['#FFFFFF', '#CCCCCC', '#999999', '#666666', '#333333', '#000000', '#E53AA3', '#FF7BCC',
           '#F93C31', '#1E93FF', '#88D8F1', '#FFDC00', '#FF851B', '#921231', '#4FCC30', '#A356D6']
CONTEXT_NOTE = (
    'The game board has 64 columns and 64 rows. Each cell holds one colour, written as a hexadecimal digit '
    '(0-9, a-f). x is the column counted from the left starting at 0; y is the row counted from the top '
    'starting at 0. In the current board below, each line reads "yy|" then that row\'s 64 cells in groups of 8 '
    'separated by spaces. In the recent history, changed_cells lists runs '
    '[x_first, x_last, y, colour_before, colour_after] of cells that differ between the board before that '
    'action and the last frame it returned.')


def hex_rows(frame):
    rows = []
    for y, row in enumerate(frame):
        text = ''.join(HEX[int(v)] for v in row)
        rows.append('%02d|' % y + ' '.join(text[i:i + 8] for i in range(0, len(text), 8)))
    return rows


def changed_runs(old, new):
    if old.shape != new.shape:
        return 'board size changed'
    runs = []
    ys, xs = np.nonzero(old != new)
    for y, x in zip(ys.tolist(), xs.tolist()):
        pair = (HEX[int(old[y, x])], HEX[int(new[y, x])])
        if runs and runs[-1][2] == y and runs[-1][1] == x - 1 and (runs[-1][3], runs[-1][4]) == pair:
            runs[-1][1] = x
        else:
            runs.append([x, x, y, pair[0], pair[1]])
    return runs if len(runs) <= 64 else {'cells': int(len(xs)), 'runs': len(runs), 'listed': False}


def action_text(action):
    return '%s x=%d y=%d' % (action['id'], action['x'], action['y']) if action['x'] is not None else action['id']


def decision_input(done, decision):
    current = done[-1]['response_frames'][-1]
    history = [{'transition_id': 't%d' % r['event_seq'], 'action': action_text(r['action']),
                'frames_returned': len(r['response_frames']),
                'changed_cells': changed_runs(r['before_frame'], r['response_frames'][-1]),
                'state': r['state_after'], 'levels_completed': r['level_after']} for r in done[-2:]]
    return '\n'.join(
        ['== DECISION-TIME INPUT ==', CONTEXT_NOTE, '',
         'Current board: observation o%d (the board after %d actions). levels_completed=%d, state=%s.' % (
             decision, decision, done[-1]['level_after'], done[-1]['state_after'])]
        + hex_rows(current)
        + ['Legal actions now: %s (ACTION6 clicks one cell x,y).' % ','.join(map(str, done[-1]['legal_after'])), '',
           'Recent history, the two most recent actions:'] + [json.dumps(h, separators=(',', ':')) for h in history])


PAGE = '''<!doctype html><meta charset="utf-8"><title>__TITLE__</title>
<style>
body{font:14px/1.4 system-ui,sans-serif;margin:16px;background:#f4f5f7;color:#17202b}
h1{font-size:18px} .rec{background:#fff;border:1px solid #d4dae2;border-radius:6px;padding:8px 10px;margin:10px 0}
.rec h2{font-size:14px;margin:0 0 6px} .frames{display:flex;flex-wrap:wrap;gap:8px}
figure{margin:0} figcaption{font-size:11px;color:#5a6676} canvas{border:1px solid #8a94a3;image-rendering:pixelated}
.mark{background:#fff3cd} #tip{position:fixed;background:#17202b;color:#fff;padding:2px 6px;font-size:12px;border-radius:3px;display:none;pointer-events:none}
.legend span{display:inline-block;width:22px;height:18px;line-height:18px;text-align:center;font-size:11px;border:1px solid #8a94a3;margin-right:2px}
</style>
<h1>__TITLE__</h1>
<p>__INTRO__</p>
<p class="legend">Colour digits: <span id="lg"></span> Hover a cell to see its column x, row y and digit. Display colours are only for viewing; the model sees digits.</p>
<div id="out"></div><div id="tip"></div>
<script>
const D=__DATA__, P=__PALETTE__, S=3, HX='0123456789abcdef';
const lg=document.getElementById('lg');P.forEach((c,i)=>{const s=document.createElement('span');s.style.background=c;s.style.color=(i<3||i==7||i==10||i==11)?'#000':'#fff';s.textContent=HX[i];lg.appendChild(s)});
const tip=document.getElementById('tip');
function draw(idx,cap){const f=D.frames[idx],h=f.length/D.w|0,fig=document.createElement('figure'),c=document.createElement('canvas');
 c.width=D.w*S;c.height=h*S;const g=c.getContext('2d');
 for(let y=0;y<h;y++)for(let x=0;x<D.w;x++){g.fillStyle=P[parseInt(f[y*D.w+x],16)];g.fillRect(x*S,y*S,S,S)}
 c.onmousemove=e=>{const r=c.getBoundingClientRect(),x=Math.floor((e.clientX-r.left)/S),y=Math.floor((e.clientY-r.top)/S);
  if(x>=0&&y>=0&&x<D.w&&y<h){tip.style.display='block';tip.style.left=(e.clientX+12)+'px';tip.style.top=(e.clientY+12)+'px';tip.textContent='x='+x+' y='+y+' colour '+f[y*D.w+x]}};
 c.onmouseleave=()=>tip.style.display='none';
 const fc=document.createElement('figcaption');fc.textContent=cap;fig.appendChild(c);fig.appendChild(fc);return fig}
const out=document.getElementById('out');
D.records.forEach(r=>{const d=document.createElement('div');d.className='rec'+(r.mark?' mark':'');
 const h=document.createElement('h2');h.textContent=r.title;d.appendChild(h);
 const fr=document.createElement('div');fr.className='frames';
 r.frames.forEach((i,k)=>fr.appendChild(draw(i,r.captions[k])));d.appendChild(fr);out.appendChild(d)});
</script>
'''


def page(title, intro, entries, width):
    table, frames = {}, []

    def ref(frame):
        key = frame.tobytes()
        if key not in table:
            table[key] = len(frames)
            frames.append(''.join(HEX[int(v)] for v in frame.ravel()))
        return table[key]
    recs = [{'title': e['title'], 'mark': e.get('mark', False), 'frames': [ref(f) for f in e['frames']],
             'captions': e['captions']} for e in entries]
    data = json.dumps({'w': width, 'frames': frames, 'records': recs}, separators=(',', ':'))
    return (PAGE.replace('__TITLE__', title).replace('__INTRO__', intro)
            .replace('__DATA__', data).replace('__PALETTE__', json.dumps(PALETTE)))


def record_entry(r, mark=False, note=''):
    total = len(r['response_frames'])
    return {'title': 'Action %d (t%d): %s | level %d, attempt %d | returned %d frame%s | after: %s, levels completed %d%s' % (
                r['event_seq'], r['event_seq'], action_text(r['action']), r['level_observed'], r['reset_id'] + 1, total,
                '' if total == 1 else 's', r['state_after'], r['level_after'], note),
            'mark': mark, 'frames': [r['before_frame']] + list(r['response_frames']),
            'captions': ['before'] + ['frame %d/%d' % (i + 1, total) for i in range(total)]}


def main(events_path, cases_path, check_dir, out_dir):
    out, check_dir = Path(out_dir), Path(check_dir)
    frozen = json.loads(Path(cases_path).read_text())
    results = {c['case']: c for c in json.loads((check_dir / 'results.json').read_text())['cases']}
    games = {k.split('-')[0]: v for k, v in records.load_run(events_path).items()}
    rng = random.Random(SEED)
    subset = []
    for kind in TYPES:
        by_game = {}
        for c in frozen['cases']:
            if c['type'] == kind:
                by_game.setdefault(c['game'], []).append(c['case'])
        chosen_games = sorted(rng.sample(sorted(by_game), PER_TYPE))
        subset += [rng.choice(by_game[g]) for g in chosen_games]
    subset.sort()
    cases = {c['case']: c for c in frozen['cases']}
    manifest = {'protocol': 'revision 11, G3 full-review subset', 'seed': SEED, 'rule':
                'three cases per contrasting type, three different games within each type, seeded random',
                'chosen_after_format_sizes_were_known': True, 'chosen_before_any_scorer_or_reviewer_output': True,
                'cases_file_sha256': hashlib.sha256(Path(cases_path).read_bytes()).hexdigest(), 'subset': subset, 'files': {}}
    for name in subset:
        case = cases[name]
        game, decision = case['game'], case['decision_after_actions']
        recs = games[game]['records']
        done = recs[:decision]
        folder = out / 'cases' / name
        for stage in ('stage1', 'stage2', 'stage3', 'stage4'):
            (folder / stage).mkdir(parents=True, exist_ok=True)
        width = done[-1]['response_frames'][-1].shape[1]
        (folder / 'stage1' / 'decision_input.txt').write_text(decision_input(done, decision) + '\n')
        current_entry = {'title': 'Current board: observation o%d, after %d actions | level %d, attempt %d | legal actions %s' % (
            decision, decision, done[-1]['level_after'], done[-1]['reset_id'] + 1, ','.join(map(str, done[-1]['legal_after']))),
            'frames': [done[-1]['response_frames'][-1]], 'captions': ['current board']}
        (folder / 'stage1' / 'decision_view.html').write_text(page(
            'Case %s, stage 1: decision-time input (%s)' % (name, game),
            'The current board and the two most recent actions. This is all the model has before any older memory is added.',
            [current_entry] + [record_entry(r, note=' | recent') for r in done[-2:]], width))
        (folder / 'stage2' / 'history_view.html').write_text(page(
            'Case %s, stage 2: all past actions up to the decision (%s)' % (name, game),
            'Every action record from the start of the game to the decision, oldest first. The last two are the recent '
            'actions already in the decision-time input (marked "recent"). Nothing here says which records anyone selected.',
            [record_entry(r, note=' | recent, already in the decision-time input' if r['event_seq'] > decision - 2 else '')
             for r in done], width))
        pack = (check_dir / 'packs' / ('%s_B2.txt' % name)).read_text()
        (folder / 'stage3' / 'pack_B2.txt').write_text(pack)
        p = results[name]['pack']
        (folder / 'stage3' / 'pack_contents.json').write_text(json.dumps({
            'case': name, 'records_in_pack': [e['event'] for e in results[name]['records']],
            'start_board_modes': [e['start_board'] for e in results[name]['records']],
            'pack_opus_tokens': p['opus_tokens'], 'within_2048_working_allowance': p['fits_active']['2048'],
            'within_1024_secondary_allowance': p['fits_active']['1024'], 'pack_sha256': p['sha256'],
            'how_the_records_were_chosen': 'by the case-selection rule, not by a reviewer and not by a scoring model'}, indent=1))
        (folder / 'stage4' / 'assigned_type.json').write_text(json.dumps({
            'case': name, 'assigned_type': case['type'], 'rule_note': case['rule_note'],
            'rule': 'see the type table in ../../../README.md of the first format check; assigned from frames by rule'}, indent=1))
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                manifest['files'][str(path.relative_to(out))] = hashlib.sha256(path.read_bytes()).hexdigest()
    (out / 'subset_frozen.json').write_text(json.dumps(manifest, indent=1))
    print(subset)
    for name in subset:
        c = cases[name]
        size = sum(p.stat().st_size for p in (out / 'cases' / name).rglob('*') if p.is_file())
        print(name, c['type'], c['game'], 'decision', c['decision_after_actions'], 'records',
              [e['event'] for e in c['earlier_records']], 'fits 2048:', results[name]['pack']['fits_active']['2048'],
              '| folder %.1f MB' % (size / 1e6))


if __name__ == '__main__':
    main(*sys.argv[1:5])
