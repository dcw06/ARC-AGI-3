"""Build a page that shows the ten one-decision test positions: the board the model saw, the board a reset
would have restored, what the model chose with and without the recovery check, and the reasons it gave.

Everything on the page is read from the saved run, the frozen manifest and the saved replies.

Usage: positions_page.py <decision_test_dir>   writes positions.html there
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research'))
from recovery_v1 import traces  # noqa: E402

HEX = '0123456789abcdef'
RIGHT = {'lp85', 'ka59', 'sc25', 'tr87', 'vc33', 'bp35'}


def cells(frame):
    return ''.join(HEX[int(v)] for v in frame.flatten())


def what_followed(trace, index, level):
    """What the saved run did after this turn, in words."""
    steps = trace['steps']
    for k, step in enumerate(steps[index:], 1):
        if step['lc'] > level:
            return 'It completed the level %d action%s later.' % (k, '' if k == 1 else 's')
        if step['state'] == 'GAME_OVER':
            return 'It hit a game over %d actions later and never completed the level.' % k
    return 'It played %d more actions, to the 100-action cap, without completing the level.' % (len(steps) - index)


def build(folder):
    folder = Path(folder)
    manifest = [m for m in json.loads((folder / 'manifest.json').read_text()) if m['arm'] == 'asked']
    replies = [json.loads(line) for line in (folder / 'replies.jsonl').read_text().splitlines()]
    saved = traces.load_events()
    positions = []
    for m in manifest:
        trace, index, level = saved[m['game']], m['actions_before'], m['level'] - 1
        short = m['game'].split('-')[0]
        board = trace['steps'][index - 1]['frame']
        start = trace['initial'] if level == 0 else next(s['frame'] for s in trace['steps'] if s['lc'] == level)
        # Count actions taken while the level was the current one (the action that completed the level
        # before it belongs to that earlier level). Resets on the level are counted.
        on_level = since_start = before = 0
        for s in trace['steps'][:index]:
            if before == level:
                on_level += 1
                since_start = 0 if s['a'] == 'RESET' else since_start + 1
            before = s['lc']
        choices, reasons = {}, []
        for arm in ('not_asked', 'asked'):
            picked = Counter()
            for r in replies:
                if r['id'] != '%s-L%d-%s' % (short, m['level'], arm):
                    continue
                action = json.loads(r['content'])['action']
                picked[(action['action_id'], action['action_data'].get('x'), action['action_data'].get('y'))] += 1
                if arm == 'asked':
                    reasons.append(r['recovery']['reason'])
            choices[arm] = [{'action': a, 'x': x, 'y': y, 'times': n} for (a, x, y), n in picked.most_common()]
        note = what_followed(trace, index, level)
        if short == 'bp35':
            note += ' By the simulator, this position was 24 actions from a win, on a shortest path.'
        positions.append({'game': short, 'level': m['level'], 'turn': index, 'on_level': on_level,
                          'baseline': m['human_baseline'], 'attempt': since_start, 'followed': note,
                          'right': short in RIGHT, 'board': cells(board), 'start': cells(start),
                          'choices': choices, 'reasons': reasons})
    positions.sort(key=lambda p: (not p['right'], p['game']))
    page = PAGE.replace('__DATA__', json.dumps(positions, separators=(',', ':')))
    (folder / 'positions.html').write_text(page)
    return positions


PAGE = r'''<title>Decision Test Positions</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
/* Layout: one column of position cards; each card is board | facts, stacking on narrow screens. */
:root {
  --bg: #f3f5f7; --surface: #ffffff; --fg: #18222b; --muted: #5a6875; --line: #d5dce2;
  --matte: #7d8891; --asked: #0b6e6e; --plain: #9a4a00; --good: #1f6f3d; --unknown: #6a5a1a;
  --display: "Space Grotesk", "Inter", system-ui, sans-serif;
  --body: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #12171c; --surface: #1b2229; --fg: #e6ebef; --muted: #9aa7b3; --line: #2f3a44;
  --matte: #4b5660; --asked: #5fd0cc; --plain: #f0a860; --good: #6fcf8e; --unknown: #d8c26a; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #12171c; --surface: #1b2229; --fg: #e6ebef; --muted: #9aa7b3; --line: #2f3a44;
  --matte: #4b5660; --asked: #5fd0cc; --plain: #f0a860; --good: #6fcf8e; --unknown: #d8c26a; color-scheme: dark }
body { background: var(--bg); color: var(--fg); font-family: var(--body); font-size: 15px; line-height: 1.55; }
.wrap { max-width: 1040px; margin: 0 auto; padding-block: 32px 56px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: flex; flex-direction: column; gap: 28px; }
h1 { font-family: var(--display); font-weight: 600; font-size: 30px; line-height: 1.15; margin: 0; text-wrap: balance; }
h2 { font-family: var(--display); font-weight: 600; font-size: 20px; margin: 0; text-wrap: balance; }
h3 { font-family: var(--display); font-weight: 600; font-size: 18px; margin: 0; }
p { margin: 0; }
.lede { max-width: 66ch; color: var(--fg); }
.intro { display: flex; flex-direction: column; gap: 12px; }
.key { display: flex; flex-wrap: wrap; gap: 8px 22px; color: var(--muted); font-size: 13.5px; align-items: center; }
.key span { display: inline-flex; align-items: center; gap: 7px; }
.mark { width: 16px; height: 16px; flex: none; }
.group { display: flex; flex-direction: column; gap: 14px; }
.group > p { color: var(--muted); max-width: 70ch; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 18px;
  display: grid; grid-template-columns: minmax(0, 396px) minmax(0, 1fr); gap: 22px; }
.boards { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
figure { margin: 0; display: flex; flex-direction: column; gap: 6px; }
figcaption { font-size: 12.5px; color: var(--muted); letter-spacing: 0.02em; }
canvas { display: block; width: 100%; height: auto; max-width: 384px; background: var(--matte);
  border: 6px solid var(--matte); border-radius: 3px; image-rendering: pixelated; }
canvas.small { max-width: 168px; border-width: 4px; }
.readout { font-family: var(--mono); font-size: 12px; color: var(--muted); min-height: 1.4em; }
.facts { display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.head { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 12px; }
.tag { font-size: 12px; font-weight: 600; letter-spacing: 0.04em; text-transform: uppercase; }
.tag.good { color: var(--good); } .tag.unknown { color: var(--unknown); }
dl { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 4px 14px; margin: 0; font-size: 14px; }
dt { color: var(--muted); } dd { margin: 0; font-variant-numeric: tabular-nums; }
.chose { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.arm { border-top: 3px solid var(--line); padding-top: 8px; display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.arm.asked { border-top-color: var(--asked); } .arm.plain { border-top-color: var(--plain); }
.arm b { font-weight: 600; font-size: 13.5px; }
.arm ul { margin: 0; padding: 0; list-style: none; font-family: var(--mono); font-size: 12.5px; display: flex; flex-direction: column; gap: 2px; }
.arm .none { color: var(--muted); font-size: 13px; }
.why { display: flex; flex-direction: column; gap: 6px; }
.why b { font-size: 13.5px; font-weight: 600; }
blockquote { margin: 0; padding-left: 12px; border-left: 2px solid var(--line); color: var(--fg); font-size: 14px; }
details summary { cursor: pointer; color: var(--muted); font-size: 13px; }
details summary:focus-visible { outline: 2px solid var(--asked); outline-offset: 2px; }
details[open] { display: flex; flex-direction: column; gap: 6px; }
.note { color: var(--muted); font-size: 13.5px; max-width: 70ch; }
@media (max-width: 760px) { .card { grid-template-columns: minmax(0, 1fr); } .chose { grid-template-columns: minmax(0, 1fr); } h1 { font-size: 25px; } }
</style>
<div class="wrap">
  <div class="intro">
    <h1>Where the model was offered a reset and kept playing</h1>
    <p class="lede">Ten positions from the saved 6 November run, each at the turn where the actions spent on a level first reached the human baseline. Each was sent to Claude Opus 5.5 ten times: five with resetting merely allowed, five with a recovery check that asked it to choose "continue" or "reset". It never chose a reset. No game was played; the replies were only recorded.</p>
    <div class="key" aria-label="Key">
      <span><svg class="mark" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="5.5" fill="none" stroke="var(--asked)" stroke-width="2.5"/></svg>click chosen when asked</span>
      <span><svg class="mark" viewBox="0 0 16 16" aria-hidden="true"><rect x="3" y="3" width="10" height="10" fill="none" stroke="var(--plain)" stroke-width="2.5" transform="rotate(45 8 8)"/></svg>click chosen when not asked</span>
      <span>Boards are 64 by 64 cells. Point at a board to read a cell.</span>
    </div>
  </div>
  <div class="group" id="right">
    <h2>Continuing was the right call</h2>
    <p>In five of these the saved run completed the level within seven more actions. In the sixth, bp35, a simulator of the game shows the position was still on a shortest path to a win.</p>
  </div>
  <div class="group" id="unknown">
    <h2>The level was never finished, and nobody knows whether it still could be</h2>
    <p>In the saved run these four levels were never completed. Whether a reset would have helped at this turn is unknown: there is no ground truth for these games.</p>
  </div>
  <p class="note">The marks show only the clicks (ACTION6). Other actions have no place on the board and are listed beside it. The small board is the level's first board, which is exactly what a reset returns.</p>
</div>
<script>
const DATA = __DATA__;
const PALETTE = ['#FFFFFF','#CCCCCC','#999999','#666666','#333333','#000000','#E53AA3','#FF7BCC','#F93C31','#1E93FF','#88D8F1','#FFDC00','#FF851B','#921231','#4FCC30','#A356D6'];
const HEX = '0123456789abcdef';
function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
function draw(canvas, cells, scale, marks) {
  canvas.width = 64 * scale; canvas.height = 64 * scale;
  const g = canvas.getContext('2d');
  for (let i = 0; i < 4096; i++) {
    g.fillStyle = PALETTE[parseInt(cells[i], 16)];
    g.fillRect((i % 64) * scale, Math.floor(i / 64) * scale, scale, scale);
  }
  for (const m of marks || []) {
    const cx = (m.x + 0.5) * scale, cy = (m.y + 0.5) * scale, r = scale * 2.6;
    for (const [width, colour] of [[6, 'rgba(255,255,255,0.95)'], [2.6, m.asked ? css('--asked') : css('--plain')]]) {
      g.lineWidth = width; g.strokeStyle = colour; g.beginPath();
      if (m.asked) { g.arc(cx, cy, r, 0, Math.PI * 2); }
      else { const d = r * 1.25; g.moveTo(cx, cy - d); g.lineTo(cx + d, cy); g.lineTo(cx, cy + d); g.lineTo(cx - d, cy); g.closePath(); }
      g.stroke();
    }
  }
}
function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
function actionText(c) {
  const what = c.action === 6 ? 'click x=' + c.x + ' y=' + c.y : 'ACTION' + c.action;
  return what + '  × ' + c.times;
}
function arm(title, cls, list) {
  const box = el('div', 'arm ' + cls); box.appendChild(el('b', null, title));
  const ul = el('ul'); for (const c of list) ul.appendChild(el('li', null, actionText(c))); box.appendChild(ul);
  box.appendChild(el('span', 'none', 'Resets: 0 of 5'));
  return box;
}
const redraw = [];
for (const p of DATA) {
  const card = el('article', 'card');
  const boards = el('div', 'boards');
  const big = el('figure'), canvas = el('canvas'), readout = el('div', 'readout', ' ');
  canvas.setAttribute('role', 'img');
  canvas.setAttribute('aria-label', p.game + ' level ' + p.level + ', the board after ' + p.turn + ' actions');
  const marks = [];
  for (const [name, asked] of [['not_asked', false], ['asked', true]])
    for (const c of p.choices[name]) if (c.action === 6) marks.push({x: c.x, y: c.y, asked});
  const paint = () => draw(canvas, p.board, 6, marks); paint(); redraw.push(paint);
  canvas.addEventListener('mousemove', e => {
    const r = canvas.getBoundingClientRect(), inner = r.width - 12;
    const x = Math.floor((e.clientX - r.left - 6) / inner * 64), y = Math.floor((e.clientY - r.top - 6) / inner * 64);
    readout.textContent = (x >= 0 && y >= 0 && x < 64 && y < 64) ? 'x=' + x + ' y=' + y + ' colour ' + p.board[y * 64 + x] : ' ';
  });
  canvas.addEventListener('mouseleave', () => { readout.textContent = ' '; });
  big.appendChild(el('figcaption', null, 'The board the model saw, after ' + p.turn + ' actions'));
  big.appendChild(canvas); big.appendChild(readout); boards.appendChild(big);
  const small = el('figure'), first = el('canvas', 'small');
  first.setAttribute('role', 'img'); first.setAttribute('aria-label', p.game + ' level ' + p.level + ', first board');
  draw(first, p.start, 3);
  small.appendChild(el('figcaption', null, 'What a reset would have restored: the level’s first board'));
  small.appendChild(first); boards.appendChild(small);
  card.appendChild(boards);
  const facts = el('div', 'facts'), head = el('div', 'head');
  head.appendChild(el('h3', null, p.game + ', level ' + p.level));
  head.appendChild(el('span', 'tag ' + (p.right ? 'good' : 'unknown'), p.right ? 'continuing was right' : 'outcome unknown'));
  facts.appendChild(head);
  const dl = el('dl');
  for (const [k, v] of [['Actions into the game', p.turn], ['Actions on this level', p.on_level + ' (human baseline ' + p.baseline + ')'],
                         ['Actions since the level last started', p.attempt], ['What the saved run did next', p.followed]]) {
    dl.appendChild(el('dt', null, k)); dl.appendChild(el('dd', null, String(v)));
  }
  facts.appendChild(dl);
  const chose = el('div', 'chose');
  chose.appendChild(arm('Not asked: what it did', 'plain', p.choices.not_asked));
  chose.appendChild(arm('Asked: what it did', 'asked', p.choices.asked));
  facts.appendChild(chose);
  const why = el('div', 'why'); why.appendChild(el('b', null, 'Its reason for continuing, when asked (5 of 5 said continue)'));
  why.appendChild(el('blockquote', null, p.reasons[0]));
  const more = el('details'); more.appendChild(el('summary', null, 'The other four replies'));
  for (const r of p.reasons.slice(1)) more.appendChild(el('blockquote', null, r));
  why.appendChild(more); facts.appendChild(why);
  card.appendChild(facts);
  document.getElementById(p.right ? 'right' : 'unknown').appendChild(card);
}
// Marker colours come from the theme: repaint when it changes.
const repaint = () => redraw.forEach(f => f());
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', repaint);
new MutationObserver(repaint).observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme']});
</script>
'''


if __name__ == '__main__':
    for p in build(sys.argv[1]):
        print(p['game'], p['level'], 'turn', p['turn'], 'on level', p['on_level'], 'since start', p['attempt'], '|', p['followed'])
