"""Build a page that shows the bp35 repeat-death test: the three deaths of the saved run frame by frame, and
for each tested turn the board, every reply's chosen action drawn on it, and what the local game did next.

Everything on the page is read from the saved run, the saved replies and the local copy of the game.

Usage (project environment): actions_page.py <death_test_dir>   writes actions.html there
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from research.memory_fix_v1 import bp35_local  # noqa: E402

HEX = '0123456789abcdef'
DEATHS = (23, 48, 78)
LABELS = {'none': 'As sent on 6 November', 'irrelevant': 'Plus irrelevant earlier boards',
          'evidence': 'Plus the earlier deaths’ boards', 'lesson': 'Plus the lessons',
          'lesson_check': 'Plus the lessons and the check'}
ABOUT = re.compile(r'spike|hazard|f tile|f object|f/b0|game_over|game over|fatal|lesson', re.I)


def cells(frame):
    return ''.join(HEX[int(v)] for v in np.asarray(frame).flatten())


def words(action):
    if action['action_id'] == 6:
        return 'click at x=%d, y=%d' % (action['action_data']['x'], action['action_data']['y'])
    return {3: 'move left', 4: 'move right', 7: 'ACTION7 (undo)'}.get(action['action_id'], 'ACTION%d' % action['action_id'])


def piece_box(frame):
    """The player's piece: a 5 by 5 sprite whose blue cells (colour 9) sit one cell in from its left edge."""
    ys, xs = np.nonzero(np.asarray(frame) == 9)
    if not len(xs):
        return None
    return [int(xs.min()) - 1, int(ys.min()), int(xs.max()) + 2, int(ys.max()) + 1]


def said(row):
    """What the reply said about the danger: its check if it had to give one, else its note on the subject."""
    if row.get('lesson_check'):
        return row['lesson_check']
    notes = [h['statement'] for h in json.loads(row['content'])['hypotheses'] if ABOUT.search(h['statement'])]
    return notes[0] if notes else json.loads(row['content'])['hypotheses'][-1]['statement']


def build(folder):
    folder = Path(folder)
    first, steps = bp35_local.saved_run()
    saved_actions = [a for a, _ in steps]
    rows = [json.loads(line) for line in (folder / 'replies_scored.jsonl').read_text().splitlines()]
    lessons = json.loads((folder / 'lessons.json').read_text())
    deaths = []
    for number in DEATHS:
        action, after = steps[number - 1]
        before = steps[number - 2][1]['frames'][-1]
        deaths.append({'id': 't%d' % number, 'number': number, 'did': words(action), 'action': action,
                       'piece': piece_box(before),
                       'frames': [cells(before)] + [cells(f) for f in after['frames']]})
    turns = []
    for turn in sorted({int(r['id'].split('-')[0][4:]) for r in rows}):
        board = steps[turn - 1][1]['frames'][-1]
        after_boards, inputs = {}, []
        for arm, label in LABELS.items():
            replies = []
            for r in sorted((r for r in rows if r['id'] == 'turn%d-%s' % (turn, arm)), key=lambda r: r['repeat']):
                key = json.dumps(r['action'], sort_keys=True)
                if key not in after_boards:
                    _, result, _ = bp35_local.replay(saved_actions[:turn] + [r['action']])
                    assert result.state.name == r['state_on_local_game']
                    after_boards[key] = cells(result.frame[-1])
                replies.append({'action': r['action'], 'did': words(r['action']), 'key': key,
                                'dead': r['state_on_local_game'] == 'GAME_OVER', 'said': said(r),
                                'is_check': bool(r.get('lesson_check'))})
            inputs.append({'arm': arm, 'label': label, 'replies': replies,
                           'dead': sum(x['dead'] for x in replies)})
        turns.append({'turn': turn, 'next': turn + 1, 'board': cells(board), 'piece': piece_box(board),
                      'earlier': [d for d in DEATHS if d <= turn], 'saved': words(steps[turn][0]),
                      'inputs': inputs, 'after': after_boards})
    data = {'deaths': deaths, 'turns': turns, 'lessons': lessons}
    (folder / 'actions.html').write_text(PAGE.replace('__DATA__', json.dumps(data, separators=(',', ':'))))
    return data


PAGE = r'''<title>bp35 Repeat Deaths</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
/* Layout: a column. Deaths as a row of three players; each tested turn as board | inputs, with the chosen reply shown below. */
:root {
  --bg: #f3f5f7; --surface: #ffffff; --fg: #18222b; --muted: #5a6875; --line: #d5dce2; --matte: #7d8891;
  --dead: #b3261e; --alive: #0b6e6e; --pick: #18222b; --soft: #e9edf1;
  --display: "Space Grotesk", "Inter", system-ui, sans-serif;
  --body: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #12171c; --surface: #1b2229; --fg: #e6ebef; --muted: #9aa7b3; --line: #2f3a44; --matte: #4b5660;
  --dead: #ff8a80; --alive: #5fd0cc; --pick: #e6ebef; --soft: #242d36; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #12171c; --surface: #1b2229; --fg: #e6ebef; --muted: #9aa7b3; --line: #2f3a44; --matte: #4b5660;
  --dead: #ff8a80; --alive: #5fd0cc; --pick: #e6ebef; --soft: #242d36; color-scheme: dark }
body { background: var(--bg); color: var(--fg); font-family: var(--body); font-size: 15px; line-height: 1.55; }
.wrap { max-width: 1080px; margin: 0 auto; padding-block: 32px 56px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: flex; flex-direction: column; gap: 34px; }
h1 { font-family: var(--display); font-weight: 600; font-size: 30px; line-height: 1.15; margin: 0; text-wrap: balance; }
h2 { font-family: var(--display); font-weight: 600; font-size: 21px; margin: 0; text-wrap: balance; }
h3 { font-family: var(--display); font-weight: 600; font-size: 17px; margin: 0; }
p { margin: 0; }
section { display: flex; flex-direction: column; gap: 14px; }
.lede, .sub { max-width: 68ch; } .sub { color: var(--muted); }
canvas { display: block; width: 100%; height: auto; background: var(--matte); border: 6px solid var(--matte);
  border-radius: 3px; image-rendering: pixelated; }
.deaths { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; }
.player { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 14px;
  display: flex; flex-direction: column; gap: 10px; min-width: 0; }
.bar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; }
button { font: inherit; color: var(--fg); background: var(--soft); border: 1px solid var(--line); border-radius: 4px;
  padding: 5px 12px; cursor: pointer; }
button:focus-visible { outline: 2px solid var(--alive); outline-offset: 2px; }
.count { font-family: var(--mono); font-size: 12.5px; color: var(--muted); font-variant-numeric: tabular-nums; }
.turn { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 18px;
  display: flex; flex-direction: column; gap: 18px; }
.top { display: grid; grid-template-columns: minmax(0, 396px) minmax(0, 1fr); gap: 24px; }
.boardbox { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.cap { font-size: 12.5px; color: var(--muted); }
.inputs { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.input { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 4px 14px; align-items: center; }
.input .name { font-weight: 500; }
.input .tally { font-size: 13px; color: var(--muted); font-variant-numeric: tabular-nums; grid-column: 1 / -1; }
.dots { display: flex; gap: 5px; }
.dot { width: 26px; height: 26px; padding: 0; border-radius: 50%; border: 2px solid var(--alive); background: transparent;
  color: var(--alive); font-family: var(--mono); font-size: 13px; line-height: 1; display: grid; place-items: center; }
.dot.dead { border-radius: 4px; border-color: var(--dead); color: var(--dead); }
.dot[aria-pressed="true"] { background: var(--pick); color: var(--surface); border-color: var(--pick); }
.chosen { border-top: 1px solid var(--line); padding-top: 16px; display: grid;
  grid-template-columns: minmax(0, 250px) minmax(0, 1fr); gap: 22px; }
.chosen .what { display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.verdict { font-weight: 600; } .verdict.dead { color: var(--dead); } .verdict.alive { color: var(--alive); }
blockquote { margin: 0; padding-left: 12px; border-left: 2px solid var(--line); font-size: 14px; }
.key { display: flex; flex-wrap: wrap; gap: 6px 20px; font-size: 13.5px; color: var(--muted); align-items: center; }
.key span { display: inline-flex; align-items: center; gap: 7px; }
.key .dot { width: 18px; height: 18px; font-size: 10px; pointer-events: none; }
.lessons { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.lesson { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 14px;
  display: flex; flex-direction: column; gap: 8px; min-width: 0; font-size: 14px; }
.lesson b { font-weight: 600; }
@media (max-width: 820px) { .deaths, .lessons, .top, .chosen { grid-template-columns: minmax(0, 1fr); } h1 { font-size: 25px; } }
@media (prefers-reduced-motion: reduce) { .player button.play { display: none; } }
</style>
<div class="wrap">
  <section>
    <h1>Dying to the same spike, and what remembering changed</h1>
    <p class="lede">bp35, level 2, from the saved 6 November run. The piece (blue and yellow) rises through light-blue space whenever nothing is above it. Purple tiles with a yellow and white underside are spikes. Green tiles can be clicked away. The agent rose into a spike three times.</p>
  </section>
  <section>
    <h2>The three deaths</h2>
    <p class="sub">Each player shows the board before the fatal action, then every frame the game returned. Press Play, or step through.</p>
    <div class="deaths" id="deaths"></div>
  </section>
  <section>
    <h2>The two turns that were tested</h2>
    <p class="sub">The same turn was sent to the model 8 times under each of five inputs. Each mark is one reply. Choose a mark to see the action it picked drawn on the board, what the game did with it, and what the reply said about the danger.</p>
    <div class="key"><span><span class="dot dead">&times;</span>the action ended in game over</span><span><span class="dot">&bull;</span>it did not</span></div>
    <div id="turns" style="display:flex;flex-direction:column;gap:22px"></div>
  </section>
  <section>
    <h2>The lessons the model wrote</h2>
    <p class="sub">Written on the turn after each earlier death, when asked for a general rule and how to recognise the danger elsewhere. These are what the two lesson inputs carried.</p>
    <div class="lessons" id="lessons"></div>
  </section>
</div>
<script>
const DATA = __DATA__;
const PALETTE = ['#FFFFFF','#CCCCCC','#999999','#666666','#333333','#000000','#E53AA3','#FF7BCC','#F93C31','#1E93FF','#88D8F1','#FFDC00','#FF851B','#921231','#4FCC30','#A356D6'];
const S = 6;
function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
function paint(canvas, cells) {
  canvas.width = 64 * S; canvas.height = 64 * S;
  const g = canvas.getContext('2d');
  for (let i = 0; i < 4096; i++) { g.fillStyle = PALETTE[parseInt(cells[i], 16)]; g.fillRect((i % 64) * S, Math.floor(i / 64) * S, S, S); }
  return g;
}
function halo(g, draw, colour) {
  for (const [w, c] of [[7, 'rgba(255,255,255,0.95)'], [3, colour]]) { g.lineWidth = w; g.strokeStyle = c; g.fillStyle = c; g.lineJoin = 'round'; g.lineCap = 'round'; draw(w); }
}
function mark(g, action, piece, colour) {
  if (action.action_id === 6) {
    const cx = (action.action_data.x + 0.5) * S, cy = (action.action_data.y + 0.5) * S;
    halo(g, () => { g.beginPath(); g.arc(cx, cy, S * 2.6, 0, Math.PI * 2); g.stroke(); g.beginPath(); g.moveTo(cx - S, cy); g.lineTo(cx + S, cy); g.moveTo(cx, cy - S); g.lineTo(cx, cy + S); g.stroke(); }, colour);
  } else if (piece && (action.action_id === 3 || action.action_id === 4)) {
    const dir = action.action_id === 3 ? -1 : 1, y = (piece[1] + piece[3] + 1) / 2 * S;
    const x0 = (dir < 0 ? piece[0] : piece[2] + 1) * S, x1 = x0 + dir * S * 6;
    halo(g, () => { g.beginPath(); g.moveTo(x0, y); g.lineTo(x1, y); g.stroke(); g.beginPath(); g.moveTo(x1, y); g.lineTo(x1 - dir * S * 2, y - S * 1.6); g.lineTo(x1 - dir * S * 2, y + S * 1.6); g.closePath(); g.fill(); g.stroke(); }, colour);
  } else if (piece) {
    const x = piece[0] * S - S, y = piece[1] * S - S, w = (piece[2] - piece[0] + 3) * S, h = (piece[3] - piece[1] + 3) * S;
    halo(g, () => { g.setLineDash([6, 5]); g.strokeRect(x, y, w, h); g.setLineDash([]); }, colour);
  }
}
const repaints = [];
// The three deaths
for (const d of DATA.deaths) {
  const box = el('div', 'player');
  box.appendChild(el('h3', null, 'Death at action ' + d.number + ': ' + d.did));
  const canvas = el('canvas'); canvas.setAttribute('role', 'img');
  canvas.setAttribute('aria-label', 'bp35 level 2, the frames of the fatal action ' + d.number);
  const bar = el('div', 'bar'), play = el('button', 'play', 'Play'), back = el('button', null, '‹ Frame'), fwd = el('button', null, 'Frame ›'), count = el('span', 'count');
  let at = 0, timer = null;
  const show = () => {
    const g = paint(canvas, d.frames[at]);
    if (at === 0) mark(g, d.action, d.piece, css('--dead'));
    count.textContent = at === 0 ? 'before the action' : 'frame ' + at + ' of ' + (d.frames.length - 1);
  };
  const stop = () => { clearInterval(timer); timer = null; play.textContent = 'Play'; };
  play.addEventListener('click', () => {
    if (timer) { stop(); return; }
    if (at >= d.frames.length - 1) at = 0;
    play.textContent = 'Pause';
    timer = setInterval(() => { at++; show(); if (at >= d.frames.length - 1) stop(); }, 110);
  });
  back.addEventListener('click', () => { stop(); at = Math.max(0, at - 1); show(); });
  fwd.addEventListener('click', () => { stop(); at = Math.min(d.frames.length - 1, at + 1); show(); });
  bar.appendChild(play); bar.appendChild(back); bar.appendChild(fwd); bar.appendChild(count);
  box.appendChild(canvas); box.appendChild(bar);
  box.appendChild(el('p', 'cap', 'The red mark is the action. The last frame is the game over.'));
  document.getElementById('deaths').appendChild(box);
  show(); repaints.push(show);
}
// The tested turns
for (const t of DATA.turns) {
  const card = el('article', 'turn');
  const head = el('div');
  head.appendChild(el('h3', null, 'Before action ' + t.next + ', after ' + (t.earlier.length === 1 ? 'one earlier death' : t.earlier.length + ' earlier deaths')));
  head.appendChild(el('p', 'cap', 'In the saved run the agent chose: ' + t.saved + ', and died.'));
  card.appendChild(head);
  const top = el('div', 'top'), boardbox = el('div', 'boardbox'), board = el('canvas');
  board.setAttribute('role', 'img'); board.setAttribute('aria-label', 'The board the model saw before action ' + t.next);
  const boardcap = el('div', 'cap', 'The board the model saw');
  boardbox.appendChild(boardcap); boardbox.appendChild(board); top.appendChild(boardbox);
  const inputs = el('div', 'inputs'); top.appendChild(inputs); card.appendChild(top);
  const chosen = el('div', 'chosen'), afterbox = el('div', 'boardbox'), after = el('canvas');
  after.setAttribute('role', 'img'); after.setAttribute('aria-label', 'The board after the chosen action');
  afterbox.appendChild(el('div', 'cap', 'What the game returned')); afterbox.appendChild(after);
  const what = el('div', 'what'), verdict = el('div', 'verdict'), source = el('div', 'cap'), quote = el('blockquote');
  what.appendChild(verdict); what.appendChild(source); what.appendChild(quote);
  chosen.appendChild(afterbox); chosen.appendChild(what); card.appendChild(chosen);
  let current = null; const dots = [];
  const choose = (input, reply, n, dot) => {
    current = {input, reply, n};
    dots.forEach(x => x.setAttribute('aria-pressed', x === dot ? 'true' : 'false'));
    draw();
  };
  const draw = () => {
    const g = paint(board, t.board);
    if (!current) return;
    const r = current.reply;
    mark(g, r.action, t.piece, css(r.dead ? '--dead' : '--alive'));
    paint(after, t.after[r.key]);
    verdict.className = 'verdict ' + (r.dead ? 'dead' : 'alive');
    verdict.textContent = 'It chose: ' + r.did + '. ' + (r.dead ? 'Game over.' : 'No game over.');
    source.textContent = current.input.label + ', reply ' + (current.n + 1) + ' of ' + current.input.replies.length + (r.is_check ? '. Its check against the lessons:' : '. Its note on the danger:');
    quote.textContent = r.said;
  };
  let firstDot = null, firstArgs = null;
  for (const input of t.inputs) {
    const row = el('div', 'input');
    row.appendChild(el('div', 'name', input.label));
    const group = el('div', 'dots');
    input.replies.forEach((reply, n) => {
      const dot = el('button', 'dot' + (reply.dead ? ' dead' : ''), reply.dead ? '×' : '•');
      dot.setAttribute('aria-pressed', 'false');
      dot.setAttribute('aria-label', input.label + ', reply ' + (n + 1) + ': ' + reply.did + (reply.dead ? ', game over' : ', no game over'));
      dot.addEventListener('click', () => choose(input, reply, n, dot));
      group.appendChild(dot); dots.push(dot);
      if (!firstDot) { firstDot = dot; firstArgs = [input, reply, n, dot]; }
    });
    row.appendChild(group);
    row.appendChild(el('div', 'tally', input.dead + ' of ' + input.replies.length + ' ended in game over'));
    inputs.appendChild(row);
  }
  document.getElementById('turns').appendChild(card);
  choose(...firstArgs); repaints.push(draw);
}
for (const l of DATA.lessons) {
  const box = el('div', 'lesson');
  box.appendChild(el('h3', null, 'After the death at action ' + l.after.slice(1)));
  const a = el('p'); a.appendChild(el('b', null, 'Rule. ')); a.appendChild(document.createTextNode(l.rule)); box.appendChild(a);
  const b = el('p'); b.appendChild(el('b', null, 'Applies when. ')); b.appendChild(document.createTextNode(l.applies_when)); box.appendChild(b);
  document.getElementById('lessons').appendChild(box);
}
const repaint = () => repaints.forEach(f => f());
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', repaint);
new MutationObserver(repaint).observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme']});
</script>
'''


if __name__ == '__main__':
    data = build(sys.argv[1])
    for d in data['deaths']:
        print('death', d['id'], d['did'], 'frames', len(d['frames']) - 1, 'piece', d['piece'])
    for t in data['turns']:
        print('turn', t['turn'], 'piece', t['piece'], 'distinct actions', len(t['after']),
              [(i['arm'], i['dead']) for i in t['inputs']])
