"""Build a page that replays the bp35 level-2 runs action by action, one player per scenario side by side.

Every frame the local game returned is on the page, with the action drawn on the board before it plays,
and what the agent wrote when it chose that action. Read from the run logs and, where present, from the
results files (which turns had a game over one action away).

Scenarios, read from each run's own configuration: memory unchanged, lessons and the check
(game_over_lessons), the scoring rule in the prompt (state_objective).

Usage (project environment): replay_page.py <level2_run dir> <run folder>...   writes replay.html there
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'research'))
from research.memory_fix_v1.actions_page import piece_box  # noqa: E402
from research.memory_fix_v1.continue_bp35 import LEVEL_ONE  # noqa: E402
from recovery_v1 import measures, traces  # noqa: E402

RESULTS = ('reports/memory_fix_v1/level2_run/results.json', 'reports/action_waste_v1/level2_run/results.json')
TEST_WORDS = re.compile(r'\btest(s|ed|ing)?\b|will show|shows? (whether|which)|see whether|to see if', re.I)

DANGER = ('spike', 'hazard', 'game_over', 'game over', 'ended the game', 'ends the game', 'dies', 'died', 'fatal',
          'destroy', 'deadly', 'lethal', 'kill')
STATUS = {'supported_locally': 'supported'}


def rle(frame):
    """One board as runs of equal cells: a letter A to P for the colour, then the run length if above 1."""
    flat = np.asarray(frame, dtype=np.uint8).flatten()
    out, start = [], 0
    edges = list(np.nonzero(np.diff(flat))[0] + 1) + [len(flat)]
    for end in edges:
        out.append(chr(65 + int(flat[start])) + (str(end - start) if end - start > 1 else ''))
        start = end
    return ''.join(out)


def words(action):
    if action['action_id'] == 6:
        return 'click at x=%d, y=%d' % (action['action_data']['x'], action['action_data']['y'])
    return {0: 'level reset', 3: 'move left', 4: 'move right', 7: 'undo'}.get(action['action_id'],
                                                                             'ACTION%d' % action['action_id'])


def unchanged_steps(folder):
    """Indices of the actions that changed nothing: board after equals board before, step counter ignored."""
    trace = next(iter(traces.load_events(Path(folder) / 'events.jsonl', source=Path(folder).name).values()))
    keys = measures.keys(trace, measures.counter_mask(trace))
    return {i for i, step in enumerate(trace['steps'])
            if step['a'] != 'RESET' and step['state'] == 'NOT_FINISHED' and keys[i + 1] == keys[i]}


def one_run(folder, near, frames, index):
    events = [json.loads(line) for line in (Path(folder) / 'events.jsonl').read_text().splitlines()]
    nothing = unchanged_steps(folder)
    config = next(e['config'] for e in events if e['kind'] == 'configuration')
    steps = [e for e in events if e['kind'] == 'transition']
    replies, at = {}, None
    for event in events:
        if event['kind'] == 'model_entered':
            at = event['action_index']
        elif event['kind'] == 'model_returned':
            replies[at] = json.loads(event['content'])

    def keep(frame):
        code = rle(frame)
        if code not in index:
            index[code] = len(frames)
            frames.append(code)
        return index[code]

    out, lesson = [], None
    board = steps[LEVEL_ONE]['before']['frames'][-1]
    start = keep(board)
    for n in range(LEVEL_ONE, len(steps)):
        step, number = steps[n], n - LEVEL_ONE + 1
        chosen = step['before']['state'] != 'GAME_OVER'
        reply = replies.get(n, {}) if chosen else {}
        notes = [[STATUS.get(h['status'], h['status'].replace('_', ' ')), h['statement']]
                 for h in reply.get('hypotheses', ()) if any(w in h['statement'].lower() for w in DANGER)]
        plans = [h['statement'] for h in reply.get('hypotheses', ()) if h['status'] == 'tentative']
        tests = [s for s in plans if TEST_WORDS.search(s)]
        row = {'a': step['action'], 'w': words(step['action']), 'f': [keep(f) for f in step['after']['frames']],
               'p': piece_box(board), 'reset': not chosen, 'near': bool(near.get(number)), 'notes': notes[:3],
               'check': reply.get('lesson_check'), 'none': chosen and n in nothing,
               'plan': (tests or plans)[-1] if chosen and (tests or plans) else None, 'test': bool(tests),
               's': ('dead' if step['after']['state'] == 'GAME_OVER'
                     else 'solved' if step['after']['levels_completed'] >= 2 else '')}
        if reply.get('game_over_lesson'):
            lesson = {'at': number, **reply['game_over_lesson']}
            row['lesson'] = True
        out.append(row)
        board = step['after']['frames'][-1]
    scenario = ('objective' if config.get('state_objective') else
                'lessons' if config.get('game_over_lessons') else 'unchanged')
    return {'scenario': scenario, 'start': start, 'steps': out, 'lesson': lesson,
            'deaths': [i + 1 for i, s in enumerate(out) if s['s'] == 'dead'], 'solved': out[-1]['s'] == 'solved',
            'nothing': sum(s['none'] for s in out)}


def build(folder, run_folders):
    folder = Path(folder)
    results = {}
    for path in RESULTS:
        if (ROOT / path).exists():
            results.update({r['run']: r for r in json.loads((ROOT / path).read_text())['runs']})
    frames, index, runs = [], {}, []
    for path in run_folders:
        name = Path(path).name
        near = {t['level_2_action']: t['a_game_over_was_one_action_away'] for t in results.get(name, {}).get('turns', ())}
        runs.append({'name': name, 'near_known': name in results, **one_run(path, near, frames, index)})
    data = {'frames': frames, 'runs': runs}
    (folder / 'replay.html').write_text(PAGE.replace('__DATA__', json.dumps(data, separators=(',', ':'))))
    return data


PAGE = r'''<title>bp35 Level 2 Replays</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
/* Layout: one player per scenario, side by side. Each: run tabs, board, a strip with one cell per action, transport, then what the agent wrote. */
:root {
  --bg: #f3f5f7; --surface: #ffffff; --fg: #18222b; --muted: #5a6875; --line: #d5dce2; --matte: #7d8891;
  --dead: #b3261e; --alive: #0b6e6e; --pick: #18222b; --soft: #e9edf1; --cell: #cfd7de; --done: #7f8c98; --idle: #c77700;
  --display: "Space Grotesk", "Inter", system-ui, sans-serif;
  --body: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #12171c; --surface: #1b2229; --fg: #e6ebef; --muted: #9aa7b3; --line: #2f3a44; --matte: #4b5660;
  --dead: #ff8a80; --alive: #5fd0cc; --pick: #e6ebef; --soft: #242d36; --cell: #34404b; --done: #8794a0; --idle: #f0b24a; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #12171c; --surface: #1b2229; --fg: #e6ebef; --muted: #9aa7b3; --line: #2f3a44; --matte: #4b5660;
  --dead: #ff8a80; --alive: #5fd0cc; --pick: #e6ebef; --soft: #242d36; --cell: #34404b; --done: #8794a0; --idle: #f0b24a; color-scheme: dark }
body { background: var(--bg); color: var(--fg); font-family: var(--body); font-size: 15px; line-height: 1.55; }
.wrap { max-width: 1480px; margin: 0 auto; padding-block: 32px 56px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: flex; flex-direction: column; gap: 26px; }
h1 { font-family: var(--display); font-weight: 600; font-size: 30px; line-height: 1.15; margin: 0; text-wrap: balance; }
h2 { font-family: var(--display); font-weight: 600; font-size: 20px; margin: 0; text-wrap: balance; }
p { margin: 0; }
header { display: flex; flex-direction: column; gap: 12px; }
.lede { max-width: 70ch; } .sub { max-width: 70ch; color: var(--muted); }
.players { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 330px), 1fr)); gap: 22px; align-items: start; }
.player { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 16px;
  display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.player .about { font-size: 13.5px; color: var(--muted); }
.tabs, .bar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
button, select { font: inherit; color: var(--fg); background: var(--soft); border: 1px solid var(--line); border-radius: 4px;
  padding: 5px 12px; cursor: pointer; }
select { padding: 5px 6px; }
button:focus-visible, select:focus-visible, .strip:focus-visible { outline: 2px solid var(--alive); outline-offset: 2px; }
button[aria-pressed="true"] { background: var(--pick); color: var(--surface); border-color: var(--pick); }
button.play { min-width: 74px; font-weight: 600; }
button:disabled { opacity: .45; cursor: default; }
.tabs button { font-size: 13.5px; font-variant-numeric: tabular-nums; }
canvas { display: block; width: 100%; height: auto; aspect-ratio: 1; background: var(--matte); border: 6px solid var(--matte);
  border-radius: 3px; }
.strip { display: flex; gap: 1px; height: 26px; align-items: stretch; cursor: pointer; border-radius: 3px; }
.strip span { flex: 1 1 0; min-width: 0; background: var(--cell); border-radius: 1px; position: relative; }
.strip span.done { background: var(--done); }
.strip span.reset { background: repeating-linear-gradient(135deg, var(--cell) 0 2px, var(--surface) 2px 4px); }
.strip span.none { background: var(--idle); }
.strip span.dead { background: var(--dead); }
.strip span.solved { background: var(--alive); }
.strip span.near::after { content: ""; position: absolute; left: 0; right: 0; top: -5px; height: 3px; background: var(--dead); opacity: .55; border-radius: 1px; }
.strip span.lesson::before { content: ""; position: absolute; left: 0; right: 0; bottom: -5px; height: 3px; background: var(--alive); border-radius: 1px; }
.strip span.cur { box-shadow: 0 0 0 2px var(--pick); z-index: 1; }
.stripbox { padding-block: 6px; }
.count { font-family: var(--mono); font-size: 12.5px; color: var(--muted); font-variant-numeric: tabular-nums; margin-left: auto; }
.now { border-top: 1px solid var(--line); padding-top: 12px; display: flex; flex-direction: column; gap: 10px; min-height: 250px; }
.headline { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 10px; }
.headline .num { font-family: var(--display); font-weight: 600; font-size: 17px; font-variant-numeric: tabular-nums; }
.headline .did { font-family: var(--mono); font-size: 13.5px; }
.badge { font-size: 12.5px; font-weight: 600; padding: 1px 8px; border-radius: 999px; border: 1.5px solid currentColor; }
.badge.dead { color: var(--dead); } .badge.solved { color: var(--alive); } .badge.reset { color: var(--muted); }
.flag { font-size: 13.5px; color: var(--dead); } .flag.ok { color: var(--muted); } .flag.idle { color: var(--idle); }
.stats { font-size: 13px; color: var(--muted); font-variant-numeric: tabular-nums; }
.cap { font-size: 12.5px; color: var(--muted); }
blockquote { margin: 0; padding-left: 12px; border-left: 2px solid var(--line); font-size: 14px; overflow-wrap: anywhere; }
blockquote.check { border-left-color: var(--alive); }
.said { display: flex; flex-direction: column; gap: 6px; }
.status { font-family: var(--mono); font-size: 11.5px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; margin-right: 6px; }
.lessoncard { border: 1px solid var(--line); border-radius: 6px; padding: 12px; font-size: 14px; display: flex; flex-direction: column; gap: 6px; }
.lessoncard b { font-weight: 600; }
.key { display: flex; flex-wrap: wrap; gap: 6px 20px; font-size: 13.5px; color: var(--muted); align-items: center; }
.key span { display: inline-flex; align-items: center; gap: 7px; }
.key i { display: inline-block; width: 12px; height: 16px; border-radius: 1px; background: var(--cell); position: relative; }
.key i.dead { background: var(--dead); } .key i.solved { background: var(--alive); } .key i.none { background: var(--idle); }
.key i.reset { background: repeating-linear-gradient(135deg, var(--cell) 0 2px, var(--surface) 2px 4px); border: 1px solid var(--line); }
.key i.near { height: 3px; background: var(--dead); opacity: .55; } .key i.lesson { height: 3px; background: var(--alive); }
@media (max-width: 860px) { h1 { font-size: 25px; } .now { min-height: 0; } }
</style>
<div class="wrap">
  <header>
    <h1>bp35 level 2, replayed</h1>
    <p class="lede" id="lede"></p>
    <p class="sub">The piece (blue and yellow) rises through light-blue space whenever nothing is above it. Purple tiles with a yellow and white underside are spikes. Green tiles can be clicked away. Each action is drawn on the board first, then the game's frames play.</p>
    <div class="key">
      <span><i class="none"></i>action changed nothing</span>
      <span><i class="dead"></i>action ended in game over</span>
      <span><i class="reset"></i>level reset by the controller</span>
      <span><i class="solved"></i>level solved</span>
      <span><i class="near"></i>a game over was one action away</span>
      <span><i class="lesson"></i>lesson written</span>
    </div>
  </header>
  <div class="players" id="players"></div>
</div>
<script>
const DATA = __DATA__;
const PALETTE = ['#FFFFFF','#CCCCCC','#999999','#666666','#333333','#000000','#E53AA3','#FF7BCC','#F93C31','#1E93FF','#88D8F1','#FFDC00','#FF851B','#921231','#4FCC30','#A356D6'];
const RGB = PALETTE.map(h => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]);
const S = 6;
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
  } else if (piece && action.action_id === 7) {
    const x = piece[0] * S - S, y = piece[1] * S - S, w = (piece[2] - piece[0] + 3) * S, h = (piece[3] - piece[1] + 3) * S;
    halo(g, () => { g.setLineDash([6, 5]); g.strokeRect(x, y, w, h); g.setLineDash([]); }, colour);
  }
}
const repaints = [];
function player(title, about, runs, id) {
  const box = el('section', 'player');
  box.appendChild(el('h2', null, title));
  box.appendChild(el('p', 'about', about));
  const tabs = el('div', 'tabs'); box.appendChild(tabs);
  const stats = el('div', 'stats'); box.appendChild(stats);
  const canvas = el('canvas'); canvas.width = canvas.height = 64 * S; canvas.setAttribute('role', 'img'); box.appendChild(canvas);
  const stripbox = el('div', 'stripbox'), strip = el('div', 'strip'); stripbox.appendChild(strip); box.appendChild(stripbox);
  strip.tabIndex = 0; strip.setAttribute('role', 'slider'); strip.setAttribute('aria-label', title + ': action');
  const bar = el('div', 'bar');
  const first = el('button', null, 'Start'), back = el('button', null, '‹ Back'), play = el('button', 'play', 'Play'), next = el('button', null, 'Next ›');
  const speed = el('select'); speed.id = 'speed-' + id; speed.setAttribute('aria-label', 'Playback speed');
  for (const [v, t] of [[1, '1×'], [2, '2×'], [4, '4×']]) { const o = el('option', null, t); o.value = v; speed.appendChild(o); }
  const count = el('span', 'count');
  for (const b of [first, back, play, next, speed, count]) bar.appendChild(b);
  box.appendChild(bar);
  const now = el('div', 'now'); box.appendChild(now);
  const lessonbox = el('div'); box.appendChild(lessonbox);

  let run = runs[0], pos = 0, playing = false, token = 0, cells = [], shown = 0;
  const rate = () => +speed.value;
  const boardAt = p => frame(p === 0 ? run.start : run.steps[p - 1].f[run.steps[p - 1].f.length - 1]);

  function describe(p) {
    now.textContent = '';
    const head = el('div', 'headline');
    if (p === 0) {
      head.appendChild(el('span', 'num', 'Start of level 2'));
      now.appendChild(head);
      now.appendChild(el('p', 'cap', 'The first board of level 2, the same in all four runs. Press Play, or step with Next. Click the strip to jump to an action.'));
      return;
    }
    const s = run.steps[p - 1];
    head.appendChild(el('span', 'num', 'Action ' + p + ' of ' + run.steps.length));
    head.appendChild(el('span', 'did', s.w));
    if (s.s === 'dead') head.appendChild(el('span', 'badge dead', 'Game over'));
    if (s.s === 'solved') head.appendChild(el('span', 'badge solved', 'Level 2 solved'));
    if (s.reset) head.appendChild(el('span', 'badge reset', 'No choice by the agent'));
    now.appendChild(head);
    if (s.reset) { now.appendChild(el('p', 'cap', 'After a game over the controller resets the level. No model call is made.')); return; }
    if (s.none) now.appendChild(el('p', 'flag idle', 'This action changed nothing on the board.'));
    if (s.near) now.appendChild(el('p', 'flag' + (s.s === 'dead' ? '' : ' ok'), s.s === 'dead'
      ? 'One action on this board ended the game, and the agent took it.'
      : 'One action on this board would have ended the game. The agent did not take it.'));
    if (s.lesson) now.appendChild(el('p', 'cap', 'On this turn, the first after its game over, the agent wrote the lesson shown below.'));
    if (s.check) {
      const said = el('div', 'said'); said.appendChild(el('div', 'cap', 'Its check of this action against the lesson'));
      said.appendChild(el('blockquote', 'check', s.check)); now.appendChild(said);
    }
    const said = el('div', 'said');
    said.appendChild(el('div', 'cap', s.notes.length ? 'Its notes about the danger when it chose this' : 'None of its notes mentioned the danger when it chose this.'));
    for (const [status, text] of s.notes) { const q = el('blockquote'); q.appendChild(el('span', 'status', status)); q.appendChild(document.createTextNode(text)); said.appendChild(q); }
    if (s.plan && (s.none || s.test)) {
      const why = el('div', 'said'); why.appendChild(el('div', 'cap', s.test ? 'Its note announcing a test' : 'What it expected'));
      why.appendChild(el('blockquote', null, s.plan)); now.appendChild(why);
    }
    now.appendChild(said);
  }
  function chrome(p) {
    shown = p;
    cells.forEach((c, i) => { c.classList.toggle('done', i < p - 1); c.classList.toggle('cur', i === p - 1); });
    strip.setAttribute('aria-valuenow', p);
    strip.setAttribute('aria-valuetext', p === 0 ? 'Start of level 2' : 'Action ' + p + ': ' + run.steps[p - 1].w);
    count.textContent = p + ' / ' + run.steps.length;
    back.disabled = first.disabled = p === 0; next.disabled = p >= run.steps.length;
    play.textContent = playing ? 'Pause' : (pos >= run.steps.length ? 'Replay' : 'Play');
    describe(p);
  }
  function rest() { paint(canvas, boardAt(pos)); chrome(pos); canvas.setAttribute('aria-label', title + ', board ' + (pos === 0 ? 'at the start of level 2' : 'after action ' + pos)); }
  function jump(p) { token++; playing = false; pos = Math.max(0, Math.min(run.steps.length, p)); rest(); }
  async function advance() {
    const mine = ++token, s = run.steps[pos];
    chrome(pos + 1);
    const g = paint(canvas, boardAt(pos));
    if (!s.reset) mark(g, s.a, s.p, css(s.s === 'dead' ? '--dead' : '--alive'));
    await sleep((s.reset ? 250 : 560) / rate()); if (mine !== token) return false;
    if (!reduced) for (const f of s.f.slice(0, -1)) { paint(canvas, frame(f)); await sleep(70 / rate()); if (mine !== token) return false; }
    pos++; rest(); return true;
  }
  async function run_play() {
    if (pos >= run.steps.length) { pos = 0; rest(); }
    playing = true; play.textContent = 'Pause';
    while (playing && pos < run.steps.length) {
      if (!(await advance())) return;
      const mine = token;
      await sleep((run.steps[pos - 1].s === 'dead' ? 1300 : 300) / rate());
      if (mine !== token) return;
    }
    playing = false; chrome(pos);
  }
  function choose(r, button) {
    token++; playing = false; run = r; pos = 0;
    [...tabs.children].forEach(b => b.setAttribute('aria-pressed', b === button ? 'true' : 'false'));
    strip.textContent = ''; cells = [];
    strip.setAttribute('aria-valuemin', 0); strip.setAttribute('aria-valuemax', r.steps.length);
    r.steps.forEach((s, i) => {
      const c = el('span', [s.s, s.reset ? 'reset' : '', s.none ? 'none' : '', s.near ? 'near' : '', s.lesson ? 'lesson' : ''].filter(Boolean).join(' '));
      c.dataset.at = i + 1; c.title = 'Action ' + (i + 1) + ': ' + s.w + (s.s === 'dead' ? ', game over' : s.s === 'solved' ? ', level solved' : s.none ? ', changed nothing' : '');
      strip.appendChild(c); cells.push(c);
    });
    stats.textContent = (r.solved ? 'Solved in ' + r.steps.length + ' actions' : 'Not solved in ' + r.steps.length + ' actions')
      + ' · ' + r.nothing + (r.nothing === 1 ? ' action' : ' actions') + ' changed nothing · ' + r.deaths.length + (r.deaths.length === 1 ? ' game over' : ' game overs')
      + (r.near_known ? '' : ' · one-action-from-game-over marks not computed for this run');
    lessonbox.textContent = '';
    if (r.lesson) {
      const card = el('div', 'lessoncard');
      card.appendChild(el('div', 'cap', 'The lesson it wrote on action ' + r.lesson.at + ', kept in every later request'));
      const a = el('p'); a.appendChild(el('b', null, 'Rule. ')); a.appendChild(document.createTextNode(r.lesson.rule)); card.appendChild(a);
      const b = el('p'); b.appendChild(el('b', null, 'Applies when. ')); b.appendChild(document.createTextNode(r.lesson.applies_when)); card.appendChild(b);
      lessonbox.appendChild(card);
    }
    rest();
  }
  runs.forEach((r, i) => {
    const d = r.deaths.length;
    const b = el('button', null, 'Run ' + (i + 1) + ' · ' + r.steps.length + ' actions');
    b.addEventListener('click', () => choose(r, b)); tabs.appendChild(b);
  });
  first.addEventListener('click', () => jump(0));
  back.addEventListener('click', () => jump(shown - 1));
  next.addEventListener('click', () => { if (pos !== shown) { jump(shown); return; } playing = false; if (pos < run.steps.length) advance(); });
  play.addEventListener('click', () => { if (playing) { jump(shown); } else run_play(); });
  strip.addEventListener('click', e => { const c = e.target.closest('span'); if (c) jump(+c.dataset.at); });
  strip.addEventListener('keydown', e => {
    const to = {ArrowLeft: shown - 1, ArrowDown: shown - 1, ArrowRight: shown + 1, ArrowUp: shown + 1, Home: 0, End: run.steps.length}[e.key];
    if (to != null) { e.preventDefault(); jump(to); }
  });
  document.getElementById('players').appendChild(box);
  choose(runs[0], tabs.children[0]);
  repaints.push(() => { if (!playing) rest(); });
}
const SCENARIOS = [
  ['unchanged', 'Memory unchanged', 'The harness as it ran on 6 November. The agent keeps eight notes and rewrites them every turn. Its prompt says nothing about what actions cost.'],
  ['lessons', 'With lessons and the check', 'After a game over the agent writes a rule and how to recognise the danger. Both stay, and every action is checked against them.'],
  ['objective', 'With the scoring rule', 'The harness of 6 November, plus the benchmark’s scoring rule in the prompt: a level scores higher the fewer actions it took, and every action counts.']];
const shown = SCENARIOS.filter(([id]) => DATA.runs.some(r => r.scenario === id));
for (const [id, title, about] of shown) player(title, about, DATA.runs.filter(r => r.scenario === id), id);
const solved = DATA.runs.filter(r => r.solved).length;
document.getElementById('lede').textContent = DATA.runs.length + ' runs from the same first board and the same notes, on a local copy of the game, in '
  + shown.length + ' set-ups. ' + (solved === DATA.runs.length ? 'All of them solved the level.' : solved + ' of them solved the level.')
  + ' Amber cells on each strip are actions that changed nothing.';
const repaint = () => repaints.forEach(f => f());
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', repaint);
new MutationObserver(repaint).observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme']});
</script>
'''


if __name__ == '__main__':
    built = build(sys.argv[1], sys.argv[2:])
    size = (Path(sys.argv[1]) / 'replay.html').stat().st_size
    print('frames kept', len(built['frames']), 'page bytes', size)
    for run in built['runs']:
        print(run['name'], run['scenario'], 'changed nothing', run['nothing'], 'actions', len(run['steps']), 'deaths', run['deaths'],
              'solved', run['solved'], 'lesson at', run['lesson'] and run['lesson']['at'],
              'frames', sum(len(s['f']) for s in run['steps']), 'near turns', sum(s['near'] for s in run['steps']))
