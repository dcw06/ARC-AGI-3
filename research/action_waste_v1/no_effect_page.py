"""Build a page that replays every action of the saved 6 November run that left the board as it was.

One small player per action, grouped by game, and nothing else. It plays the earlier actions that were in
the agent's request at that turn (up to 8), frame by frame as the game returned them, and then the action
itself. What the agent's notes said is folded away under each player. Nothing is sent anywhere.

"Changed nothing" is the measure of measure.py: the last board returned equals the board before, step-counter
cells ignored, game still running.

Usage (project environment): no_effect_page.py <out.html>
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'research'))
from recovery_v1 import measures, traces  # noqa: E402
from research.action_waste_v1 import probe_test  # noqa: E402
from research.memory_fix_v1.replay_page import rle  # noqa: E402

TEST_WORDS = re.compile(r'\btest(s|ed|ing)?\b|will show|shows? (whether|which)|see whether|to see if', re.I)


def build(out_path):
    frames, index = [], {}

    def keep(frame):
        code = rle(frame)
        if code not in index:
            index[code] = len(frames)
            frames.append(code)
        return index[code]

    sent = probe_test.saved_requests()
    steps_out, step_id, rows, games = [], {}, [], []

    for game, trace in sorted(traces.load_events().items()):
        keys = measures.keys(trace, measures.counter_mask(trace))
        steps = trace['steps']

        def action(j):
            """One action of this game, stored once however many players show it."""
            if (game, j) not in step_id:
                step = steps[j]
                was = steps[j - 1]['frame'] if j else trace['initial']
                level_was = steps[j - 1]['lc'] if j else 0
                click = step['a'] == 'ACTION6'
                kind = ('over' if step['state'] == 'GAME_OVER' else 'level' if step['lc'] > level_was else
                        'reset' if step['a'] == 'RESET' else 'none' if keys[j + 1] == keys[j] else 'changed')
                step_id[(game, j)] = len(steps_out)
                steps_out.append({
                    'n': j + 1, 'a': 0 if step['a'] == 'RESET' else int(step['a'][6:]),
                    'x': step['x'] if click else None, 'y': step['y'] if click else None,
                    'c': int(was[step['y'], step['x']]) if click and was.ndim == 2 else None,
                    'b': keep(was), 'f': [keep(step['frame'])], 'k': kind,
                    'cells': int((was != step['frame']).sum()) if was.shape == step['frame'].shape else None})
            return step_id[(game, j)]

        state, level, first_seen, chosen, mine = 'NOT_FINISHED', 0, {}, 0, 0
        for i, step in enumerate(steps):
            if step['a'] != 'RESET' and state != 'GAME_OVER':
                chosen += 1
                pair = (keys[i], step['a'], step['x'], step['y'])
                unchanged = keys[i + 1] == keys[i] and step['state'] == 'NOT_FINISHED'
                if unchanged:
                    plans = [n[1] for n in (step['notes'] or ()) if n[2] == 'tentative']
                    tests = [s for s in plans if TEST_WORDS.search(s)]
                    earlier = first_seen.get(pair)
                    history = json.loads(sent[game][i]['messages'][1]['content'])['evidence']['history']
                    before = [int(entry['transition_id'][1:]) - 1 for entry in history]
                    # The newest entry's board is the current board. Older entries carry their full board only
                    # for the newest few (history_board_limit); the rest are a list of changed cells.
                    seen = [n == len(history) - 1 or isinstance(entry['after'].get('final_frame'), list)
                            for n, entry in enumerate(history)]
                    rows.append({'g': game.split('-')[0], 'lvl': level + 1,
                                 'seq': [action(j) for j in before] + [action(i)], 'seen': seen,
                                 'said': (tests or plans or [n[1] for n in (step['notes'] or ())] or [None])[-1],
                                 'test': bool(tests), 'known': earlier[1] + 1 if earlier and earlier[0] else None})
                    mine += 1
                first_seen.setdefault(pair, (unchanged, i))
            state, level = step['state'], step['lc']
        games.append({'g': game.split('-')[0], 'chosen': chosen, 'nothing': mine})

    counts = {}
    with traces.NOV6.open() as handle:       # every frame the game returned for the actions shown
        for line in handle:
            if '"kind":"transition"' not in line:
                continue
            event = json.loads(line)
            j = counts.get(event['game_id'], 0)
            counts[event['game_id']] = j + 1
            if (event['game_id'], j) in step_id:
                steps_out[step_id[(event['game_id'], j)]]['f'] = [keep(np.asarray(f, dtype=np.uint8))
                                                                  for f in event['after']['frames']]

    data = {'frames': frames, 'steps': steps_out, 'rows': rows, 'games': games,
            'total': sum(g['chosen'] for g in games)}
    Path(out_path).write_text(PAGE.replace('__DATA__', json.dumps(data, separators=(',', ':'))))
    return data


PAGE = r'''<title>Actions That Changed Nothing</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
/* Layout: a filter bar, then one section per game holding a grid of small players: board, a strip with one cell per action (the earlier ones, then this one), transport, then what the agent expected. */
:root {
  --bg: #f3f5f7; --surface: #ffffff; --fg: #18222b; --muted: #5a6875; --line: #d5dce2; --matte: #7d8891;
  --dead: #b3261e; --alive: #0b6e6e; --pick: #18222b; --soft: #e9edf1; --idle: #c77700; --other: #6b3fa0; --done: #7f8c98; --cell: #cfd7de;
  --display: "Space Grotesk", "Inter", system-ui, sans-serif;
  --body: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #12171c; --surface: #1b2229; --fg: #e6ebef; --muted: #9aa7b3; --line: #2f3a44; --matte: #4b5660;
  --dead: #ff8a80; --alive: #5fd0cc; --pick: #e6ebef; --soft: #242d36; --idle: #f0b24a; --other: #c3a2f2; --done: #8794a0; --cell: #34404b; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #12171c; --surface: #1b2229; --fg: #e6ebef; --muted: #9aa7b3; --line: #2f3a44; --matte: #4b5660;
  --dead: #ff8a80; --alive: #5fd0cc; --pick: #e6ebef; --soft: #242d36; --idle: #f0b24a; --other: #c3a2f2; --done: #8794a0; --cell: #34404b; color-scheme: dark }
body { background: var(--bg); color: var(--fg); font-family: var(--body); font-size: 15px; line-height: 1.55; }
.wrap { max-width: 1400px; margin: 0 auto; padding-block: 32px 56px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: flex; flex-direction: column; gap: 24px; }
h1 { font-family: var(--display); font-weight: 600; font-size: 30px; line-height: 1.15; margin: 0; text-wrap: balance; }
h2 { font-family: var(--display); font-weight: 600; font-size: 20px; margin: 0; display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 12px; }
h2 small { font-family: var(--body); font-weight: 400; font-size: 13.5px; color: var(--muted); font-variant-numeric: tabular-nums; }
p { margin: 0; }
header { display: flex; flex-direction: column; gap: 12px; }
.lede { max-width: 72ch; } .sub { max-width: 72ch; color: var(--muted); }
.bar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.bar .label { font-size: 13px; color: var(--muted); margin-right: 2px; }
button { font: inherit; font-size: 13.5px; color: var(--fg); background: var(--soft); border: 1px solid var(--line); border-radius: 4px;
  padding: 4px 11px; cursor: pointer; font-variant-numeric: tabular-nums; }
button:focus-visible, .strip:focus-visible { outline: 2px solid var(--alive); outline-offset: 2px; }
button[aria-pressed="true"] { background: var(--pick); color: var(--surface); border-color: var(--pick); }
button:disabled { opacity: .45; cursor: default; }
button.play { min-width: 62px; font-weight: 600; }
section { display: flex; flex-direction: column; gap: 12px; scroll-margin-top: 12px; }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 290px), 1fr)); gap: 16px; align-items: start; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 12px;
  display: flex; flex-direction: column; gap: 9px; min-width: 0; }
canvas { display: block; width: 100%; height: auto; aspect-ratio: 1; background: var(--matte); border: 4px solid var(--matte); border-radius: 3px; }
.head { display: flex; flex-wrap: wrap; align-items: baseline; gap: 2px 10px; }
.head .where { font-family: var(--display); font-weight: 600; font-size: 15px; font-variant-numeric: tabular-nums; }
.did { font-family: var(--mono); font-size: 12.5px; display: inline-flex; align-items: center; gap: 6px; }
.sw { display: inline-block; width: 12px; height: 12px; border: 1px solid var(--muted); border-radius: 2px; }
.strip { display: flex; gap: 2px; height: 22px; align-items: flex-end; cursor: pointer; padding-top: 4px; }
.strip span { flex: 1 1 0; min-width: 0; height: 14px; background: var(--done); border-radius: 2px; }
.strip span.none { background: var(--idle); } .strip span.over { background: var(--dead); } .strip span.level { background: var(--alive); }
.strip span.reset { background: repeating-linear-gradient(135deg, var(--cell) 0 2px, var(--surface) 2px 4px); }
.strip span.me { height: 22px; }
.strip span.cur { box-shadow: 0 0 0 2px var(--surface), 0 0 0 4px var(--pick); }
.now { display: flex; flex-direction: column; gap: 2px; min-height: 62px; font-size: 13px; }
.now .what { display: flex; flex-wrap: wrap; align-items: baseline; gap: 2px 8px; }
.now .num { font-weight: 600; font-variant-numeric: tabular-nums; }
.now .res { color: var(--muted); } .now .res.none { color: var(--idle); } .now .res.over { color: var(--dead); } .now .res.level { color: var(--alive); }
.cap { font-size: 12.5px; color: var(--muted); }
.flag { font-size: 13px; color: var(--idle); }
blockquote { margin: 0; padding-left: 10px; border-left: 2px solid var(--line); font-size: 13.5px; overflow-wrap: anywhere; }
.key { display: flex; flex-wrap: wrap; gap: 6px 20px; font-size: 13.5px; color: var(--muted); align-items: center; }
.key span { display: inline-flex; align-items: center; gap: 7px; }
.key i { display: inline-block; width: 12px; height: 14px; border-radius: 2px; background: var(--done); }
.key i.none { background: var(--idle); } .key i.over { background: var(--dead); } .key i.level { background: var(--alive); }
.key i.reset { background: repeating-linear-gradient(135deg, var(--cell) 0 2px, var(--surface) 2px 4px); border: 1px solid var(--line); }
.ring { display: inline-block; width: 13px; height: 13px; border-radius: 50%; border: 2.5px solid var(--idle); }
details { font-size: 13px; } summary { cursor: pointer; color: var(--muted); font-size: 12.5px; }
details blockquote { margin-top: 6px; }
@media (max-width: 700px) { h1 { font-size: 25px; } }
</style>
<div class="wrap">
  <header>
    <h1>Actions that changed nothing</h1>
    <p class="lede" id="lede"></p>
    <p class="sub">Each card is one of those actions, as a small replay. It opens on the board the agent faced, with its action drawn. Press Play to watch the eight actions that came before it, exactly the ones in the agent's request at that turn, and then the action itself. Every frame the game returned is played. The tall cell at the end of the strip is the action the card is about; click any cell to jump to it. Cards from the first eight actions of a game have fewer actions before them.</p>
    <div class="key">
      <span><i></i>changed the board</span>
      <span><i class="none"></i>changed nothing</span>
      <span><i class="over"></i>game over</span>
      <span><i class="level"></i>level completed</span>
      <span><i class="reset"></i>level restarted by the controller</span>
    </div>
    <div class="key"><span><span class="ring"></span>where the agent clicked</span></div>
    <div class="bar" id="games"><span class="label">Jump to</span></div>
  </header>
  <div id="list" style="display:flex;flex-direction:column;gap:30px"></div>
</div>
<script>
const DATA = __DATA__;
const PALETTE = ['#FFFFFF','#CCCCCC','#999999','#666666','#333333','#000000','#E53AA3','#FF7BCC','#F93C31','#1E93FF','#88D8F1','#FFDC00','#FF851B','#921231','#4FCC30','#A356D6'];
const RGB = PALETTE.map(h => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]);
const S = 5;
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
function el(tag, cls, text) { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
const sleep = ms => new Promise(r => setTimeout(r, ms));
const decoded = new Map();
function frame(i) {
  let cells = decoded.get(i);
  if (!cells) {
    cells = new Uint8Array(4096); let at = 0, m; const re = /([A-P])(\d*)/g;
    while ((m = re.exec(DATA.frames[i]))) { const n = m[2] ? +m[2] : 1; cells.fill(m[1].charCodeAt(0) - 65, at, at + n); at += n; }
    decoded.set(i, cells);
  }
  return cells;
}
const small = document.createElement('canvas'); small.width = small.height = 64;
const smallg = small.getContext('2d'), image = smallg.createImageData(64, 64);
function paint(canvas, cells) {
  for (let i = 0; i < 4096; i++) { const c = RGB[cells[i]]; image.data[i * 4] = c[0]; image.data[i * 4 + 1] = c[1]; image.data[i * 4 + 2] = c[2]; image.data[i * 4 + 3] = 255; }
  smallg.putImageData(image, 0, 0);
  const g = canvas.getContext('2d'); g.imageSmoothingEnabled = false; g.drawImage(small, 0, 0, 64 * S, 64 * S);
  return g;
}
function ring(g, x, y, colour, r) {
  const cx = (x + 0.5) * S, cy = (y + 0.5) * S;
  for (const [w, c] of [[6, 'rgba(255,255,255,0.95)'], [2.6, colour]]) {
    g.lineWidth = w; g.strokeStyle = c; g.lineCap = 'round';
    g.beginPath(); g.arc(cx, cy, S * r, 0, Math.PI * 2); g.stroke();
    g.beginPath(); g.moveTo(cx - S * 0.9, cy); g.lineTo(cx + S * 0.9, cy); g.moveTo(cx, cy - S * 0.9); g.lineTo(cx, cy + S * 0.9); g.stroke();
  }
}
const name = s => s.a === 0 ? 'level restart' : s.a === 6 ? 'click at x=' + s.x + ', y=' + s.y : 'ACTION' + s.a;
const result = s => s.k === 'none' ? 'changed nothing' : s.k === 'over' ? 'game over' : s.k === 'level' ? 'level completed'
  : s.k === 'reset' ? 'back to the level’s first board' : (s.cells == null ? 'board changed' : s.cells + (s.cells === 1 ? ' cell changed' : ' cells changed'));
const draws = [];
function card(r) {
  const seq = r.seq.map(id => DATA.steps[id]), last = seq.length - 1, me = seq[last];
  const box = el('article', 'card');
  const head = el('div', 'head');
  head.appendChild(el('span', 'where', 'Level ' + r.lvl + ' · action ' + me.n));
  const did = el('span', 'did', name(me));
  if (me.c != null) { const sw = el('span', 'sw'); sw.style.background = PALETTE[me.c]; sw.title = 'colour of the clicked cell'; did.appendChild(sw); }
  head.appendChild(did); box.appendChild(head);
  const canvas = el('canvas'); canvas.width = canvas.height = 64 * S; canvas.setAttribute('role', 'img');
  box.appendChild(canvas);
  const strip = el('div', 'strip'); strip.tabIndex = 0; strip.setAttribute('role', 'slider');
  strip.setAttribute('aria-label', r.g + ' action ' + me.n + ': step through the actions before it');
  strip.setAttribute('aria-valuemin', 0); strip.setAttribute('aria-valuemax', last);
  const cells = seq.map((s, i) => { const c = el('span', s.k + (i === last ? ' me' : '')); c.dataset.at = i; c.title = 'Action ' + s.n + ': ' + name(s) + ', ' + result(s); strip.appendChild(c); return c; });
  box.appendChild(strip);
  const bar = el('div', 'bar'), play = el('button', 'play', 'Play'), back = el('button', null, '‹'), next = el('button', null, '›');
  back.setAttribute('aria-label', 'Previous action'); next.setAttribute('aria-label', 'Play this action and go to the next');
  bar.appendChild(play); bar.appendChild(back); bar.appendChild(next); box.appendChild(bar);
  const now = el('div', 'now'); box.appendChild(now);

  let k = last, token = 0, playing = false;
  function chrome() {
    const s = seq[k];
    cells.forEach((c, i) => c.classList.toggle('cur', i === k));
    strip.setAttribute('aria-valuenow', k); strip.setAttribute('aria-valuetext', 'Action ' + s.n + ': ' + name(s));
    play.textContent = playing ? 'Stop' : 'Play'; back.disabled = k === 0;
    canvas.setAttribute('aria-label', r.g + ', board before action ' + s.n);
    now.textContent = '';
    const what = el('div', 'what');
    what.appendChild(el('span', 'num', k === last ? 'Action ' + s.n + ', this one' : 'Action ' + s.n + ', ' + (last - k) + ' before'));
    what.appendChild(el('span', 'did', name(s)));
    now.appendChild(what);
    now.appendChild(el('div', 'res ' + s.k, result(s) + (s.f.length > 1 ? ' · the game returned ' + s.f.length + ' frames' : '')));
    if (k < last && s.a !== 0) now.appendChild(el('div', 'cap', r.seen[k] ? 'At this turn the agent saw this action’s board in full.' : 'At this turn the agent saw only which cells this action changed.'));
  }
  function show(i) {
    k = i; const s = seq[i];
    const g = paint(canvas, frame(s.b));
    if (s.a === 6) ring(g, s.x, s.y, css('--idle'), 2.6);
    chrome();
  }
  async function act(i, mine) {       // the board with the action drawn, then the frames the game returned
    show(i);
    await sleep(reduced ? 700 : 520); if (mine !== token) return false;
    const list = reduced ? seq[i].f.slice(-1) : seq[i].f;
    const wait = list.length > 24 ? 45 : list.length > 1 ? 110 : 320;      // long animations play faster
    for (const f of list) { paint(canvas, frame(f)); await sleep(wait); if (mine !== token) return false; }
    await sleep(260); return mine === token;
  }
  async function run() {
    const mine = ++token; playing = true;
    for (let i = k === last ? 0 : k; i <= last; i++) if (!(await act(i, mine))) return;
    playing = false; show(last);
  }
  function stop(i) { token++; playing = false; show(Math.max(0, Math.min(last, i))); }
  play.addEventListener('click', () => { if (playing) stop(k); else run(); });
  back.addEventListener('click', () => stop(k - 1));
  next.addEventListener('click', async () => {
    const mine = ++token, i = k; playing = false;
    if (await act(i, mine)) show(Math.min(last, i + 1));
  });
  strip.addEventListener('click', e => { const c = e.target.closest('span'); if (c) stop(+c.dataset.at); });
  strip.addEventListener('keydown', e => {
    const to = {ArrowLeft: k - 1, ArrowDown: k - 1, ArrowRight: k + 1, ArrowUp: k + 1, Home: 0, End: last}[e.key];
    if (to != null) { e.preventDefault(); stop(to); }
  });
  show(last); draws.push(() => { if (!playing) show(k); });

  if (last === 0) box.appendChild(el('p', 'cap', 'This was the first action of the game. Nothing came before it.'));
  if (r.known) box.appendChild(el('p', 'flag', 'The same action from this same board had already changed nothing at action ' + r.known + '.'));
  if (r.said) {
    const more = el('details'); more.appendChild(el('summary', null, r.test ? 'Its note announces a test' : 'What its notes said'));
    more.appendChild(el('blockquote', null, r.said)); box.appendChild(more);
  }
  return box;
}
const list = document.getElementById('list'), sections = [];
for (const game of DATA.games) {
  const rows = DATA.rows.filter(r => r.g === game.g); if (!rows.length) continue;
  const sec = el('section'); sec.id = 'game-' + game.g;
  const h = el('h2', null, game.g); h.appendChild(el('small', null, rows.length + ' of its ' + game.chosen + ' actions changed nothing'));
  sec.appendChild(h);
  const cards = el('div', 'cards'); rows.forEach(r => cards.appendChild(card(r))); sec.appendChild(cards);
  list.appendChild(sec); sections.push(sec);
  const jump = el('button', null, game.g + ' ' + rows.length);
  jump.addEventListener('click', () => sec.scrollIntoView({behavior: reduced ? 'auto' : 'smooth', block: 'start'}));
  document.getElementById('games').appendChild(jump);
}
document.getElementById('lede').textContent = DATA.rows.length + ' of the ' + DATA.total.toLocaleString('en-US') + ' actions the agent chose in the 6 November run left the board exactly as it was, step counter aside. They come from '
  + sections.length + ' of the ' + DATA.games.length + ' games.';
const repaint = () => draws.forEach(f => f());
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', repaint);
new MutationObserver(repaint).observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme']});
</script>
'''


if __name__ == '__main__':
    built = build(sys.argv[1])
    print('players', len(built['rows']), 'of', built['total'], 'actions; actions stored', len(built['steps']), 'frames', len(built['frames']), 'bytes', Path(sys.argv[1]).stat().st_size)
    print({g['g']: g['nothing'] for g in built['games'] if g['nothing']})
