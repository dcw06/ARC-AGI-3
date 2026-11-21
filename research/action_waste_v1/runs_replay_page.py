"""Build a page that replays a set of local runs, the unchanged agent beside the agent with memory layers.

For each game: two players side by side, each with its two runs. Every frame the local game returned is on
the page, the action is drawn on the board before it plays, actions that changed nothing are marked on the
strip, and for the runs with memory the page shows when a case was open, when the agent chose to explain,
the lessons it wrote and its check of each action.

    three_games   vc33, s5i5, su15: unchanged | no-effect lessons and check   (level_runs.py)
    ls20_level3   ls20 level 3:     unchanged | every memory layer            (ls20_level3.py)
    ledger_test   ls20, tr87, cd82, g50t: unchanged | memory layers and object ledger
                                                                      (object_ledger_v1/held_out_runs.py)
    brief_step1   ls20, tr87, cd82: the two 16 November runs with memory layers and object ledger | one run with
                  the level brief as well (level_brief_v1/runs.py); the stamp given is the brief batch's
    astra_compare tr87, cd82, g50t: GPT-6 Astra's public recording | unchanged | memory layers and object ledger,
                  the same runs as ledger_test, each from the level our runs started on

Usage (project environment): runs_replay_page.py <out.html> <set> <batch stamp>
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
from research.action_waste_v1 import level_runs  # noqa: E402
from research.memory_fix_v1.replay_page import rle  # noqa: E402

TEST_WORDS = re.compile(r'\btest(s|ed|ing)?\b|will show|shows? (whether|which)|see whether|to see if', re.I)
SETS = {
    'three_games': {
        'games': (('vc33-5430563c', 'from the start of the game'), ('s5i5-18d95033', 'from the start of level 3'),
                  ('su15-1944f8ab', 'from the start of level 3')),
        'arms': ('control', 'lessons'), 'title': 'No-Effect Lesson Runs',
        'h1': 'Three games, with and without the no-effect lessons',
        'second': ['With the no-effect lessons', 'The agent explains actions that changed nothing, keeps the lessons, '
                                                 'and checks each action against them.'],
        'sub': 'With the layer, an action that leaves the board as it was opens a case. The agent explains it when it '
               'judges it has seen enough, after one to four further actions, and the lesson then stays in every later '
               'request. Each action is drawn on the board first, then the game\'s frames play.',
        'directional': False},
    'ls20_level3': {
        'games': (('ls20-9607627b', 'from the start of level 3, until it is solved or 65 actions are used'),),
        'arms': ('control', 'memory'), 'title': 'ls20 Level 3 Runs',
        'h1': 'ls20 level 3, with and without the memory layers',
        'second': ['With every memory layer', 'Lessons after a game over, lessons after an action that changed nothing, '
                                              'and a check of each action against them.'],
        'sub': 'ls20 has four moves and no clicks. The arrow in the corner of the board shows the move being made '
               '(ACTION1 up, 2 down, 3 left, 4 right, as the agent worked out on level 1), then the game\'s frames play. '
               'A run stops when level 3 is solved.',
        'directional': True},
    'ledger_test': {
        'games': (('ls20-9607627b', 'from the start of level 3 (the game the layer was built on)'),
                  ('tr87-cd924810', 'from the start of level 2 (held out)'),
                  ('cd82-fb555c5d', 'from the start of level 3 (held out)'),
                  ('g50t-5849a774', 'from the start of level 2 (held out)')),
        'arms': ('control', 'ledger'), 'prefix': 'ledger', 'title': 'Object Ledger Runs',
        'h1': 'Four games, with and without the object ledger',
        'second': ['With the memory layers and the object ledger',
                   'Every request lists the things on the board by look and what has happened at each. The agent '
                   'notes what a look does and says each turn which thing it is going for.'],
        'sub': 'The controller finds the things on the board from the cells alone and marks the ones nothing has '
               'happened at yet. Under each board is what the agent said it was aiming at. For the four move actions '
               'the arrow in the corner shows the direction by convention (ACTION1 up, 2 down, 3 left, 4 right); '
               'clicks are drawn where they landed.',
        'directional': True},
    'brief_step1': {
        'games': (('ls20-9607627b', 'from the start of level 3'), ('tr87-cd924810', 'from the start of level 2'),
                  ('cd82-fb555c5d', 'from the start of level 3')),
        # column -> (folder prefix, arm, run numbers, batch stamp or None for the stamp given)
        'columns': {'plain': ('ledger', 'ledger', (1, 2), '20261116T062655Z'), 'layer': ('brief', 'brief', (1,), None)},
        'title': 'Level Brief Runs', 'h1': 'Three games, with and without the level brief',
        'first': ['Memory layers and object ledger (16 November)',
                  'The two earlier runs with every memory layer and the object ledger, from the same start.'],
        'first_short': 'earlier runs',
        'second': ['With the level brief as well',
                   'The same layers, plus rules the agent records as confirmed and a brief it must write on its '
                   'first turn on a level: what is different here, why, and what it will do first.'],
        'lede': 'One run with the level brief on each of the three games the layer was designed on, beside the two '
                'earlier runs that had the other layers only. The earlier runs were played five days before, not '
                'alongside, and these three games decide nothing about whether the layer helps on other games.',
        'sub': 'Every run starts from the same board, after the saved 6 November actions, and plays 100 new actions or '
               'until the game is won. Under each board is what the agent said it was aiming at; on the turns where it '
               'wrote its brief or recorded a rule, that is shown too. For the four move actions the arrow in the corner '
               'shows the direction by convention (ACTION1 up, 2 down, 3 left, 4 right); clicks are drawn where they landed.',
        'directional': True},
    'astra_compare': {
        'games': (('tr87-cd924810', 'from the start of level 2'), ('cd82-fb555c5d', 'from the start of level 3'),
                  ('g50t-5849a774', 'from the start of level 2')),
        'arms': ('control', 'ledger'), 'prefix': 'ledger', 'title': 'Astra Beside Opus',
        'astra': {'tr87-cd924810': 2, 'cd82-fb555c5d': 3, 'g50t-5849a774': 2}, 'astra_levels': 3,
        'h1': 'GPT-6 Astra beside Opus 5.5 on three games',
        'second': ['Opus 5.5 with the memory layers and the object ledger',
                   'Every request lists the things on the board by look and what has happened at each. The agent '
                   'notes what a look does and says each turn which thing it is going for.'],
        'sub': 'The first column is GPT-6 Astra\'s public recording with the provider harness, shown from the same level '
               'our runs start on and for three levels. It has one board per action and no notes. The other two columns '
               'are our Opus 5.5 runs, 100 actions each. For the four move actions the arrow in the corner shows the '
               'direction by convention (ACTION1 up, 2 down, 3 left, 4 right); clicks are drawn where they landed.',
        'directional': True},
}


def one_run(folder, frames, index):
    def keep(frame):
        code = rle(np.asarray(frame, dtype=np.uint8))
        if code not in index:
            index[code] = len(frames)
            frames.append(code)
        return index[code]

    folder = Path(folder)
    events = [json.loads(line) for line in (folder / 'events.jsonl').read_text().splitlines()]
    config = next(e['config'] for e in events if e['kind'] == 'configuration')
    start = config.get('resume_actions') or 0
    trace = next(iter(traces.load_events(folder / 'events.jsonl', source=folder.name).values()))
    keys = measures.keys(trace, measures.counter_mask(trace))
    transitions = [e for e in events if e['kind'] == 'transition']
    replies, bodies, at = {}, {}, None
    for event in events:
        if event['kind'] == 'model_entered':
            at = event['action_index']
            bodies[at] = json.loads(event['request']['messages'][1]['content'])
        elif event['kind'] == 'model_returned':
            replies[at] = json.loads(event['content'])

    steps, lessons, slots, deaths, notes, briefs, rules = [], [], [], [], [], [], []
    board = np.asarray(transitions[start]['before']['frames'][-1], dtype=np.uint8)
    first = keep(board)
    for i in range(start, len(transitions)):
        t, reply, body = transitions[i], replies.get(i, {}), bodies.get(i, {})
        action = t['action']
        chosen = t['before']['state'] != 'GAME_OVER' and action['action_id'] != 0
        click = action['action_id'] == 6
        x, y = (action['action_data']['x'], action['action_data']['y']) if click else (None, None)
        contract, evidence = body.get('output_contract', {}), body.get('evidence', {})
        case = evidence.get('no_effect_case')
        plans = [h['statement'] for h in reply.get('hypotheses', ()) if h['status'] == 'tentative']
        tests = [s for s in plans if TEST_WORDS.search(s)]
        nothing = chosen and t['after']['state'] == 'NOT_FINISHED' and keys[i + 1] == keys[i]
        row = {'a': action['action_id'], 'x': x, 'y': y, 'n': i + 1,
               'c': int(board[y, x]) if click and board.ndim == 2 else None,
               'f': [keep(f) for f in t['after']['frames']], 'reset': not chosen, 'none': bool(nothing),
               's': ('dead' if t['after']['state'] == 'GAME_OVER'
                     else 'level' if t['after']['levels_completed'] > t['before']['levels_completed'] else ''),
               'lvl': t['after']['levels_completed'],
               'case': case['transition_id'] if case else None, 'may': 'no_effect_lesson' in contract,
               'since': len(case['actions_since']) if case else 0,
               'check': reply.get('lesson_check') if 'lesson_check' in contract else None,
               'plan': (tests or plans)[-1] if nothing and (tests or plans) else None, 'lesson': None}
        if reply.get('game_over_lesson') and 'game_over_lesson' in contract:
            row['death'] = len(deaths)
            deaths.append({'at': i - start + 1, **reply['game_over_lesson']})
        if reply.get('thing_check') and 'thing_check' in contract:
            row['aim'] = reply['thing_check']
        if reply.get('thing_note') and 'thing_note' in contract:
            row['note'] = reply['thing_note']
            notes.append({'at': i - start + 1, **reply['thing_note']})
        due = 'level_brief' in contract
        if reply.get('level_brief') and (due or 'level_brief' in evidence):
            row['brief'] = {'asked': due, 'level': t['before']['levels_completed'] + 1, **reply['level_brief']}
            briefs.append({'at': i - start + 1, **row['brief']})
        if reply.get('rule_notes') and 'rule_notes' in contract:
            row['rules'] = reply['rule_notes']
            rules.extend({'at': i - start + 1, **note} for note in reply['rule_notes'])
        if reply.get('no_effect_lesson') and row['may']:
            written = reply['no_effect_lesson']
            number = len(lessons)
            lessons.append({'at': i - start + 1, 'explains': int(case['transition_id'][1:]),
                            'also': [int(tid[1:]) for tid in case['of_those_also_changed_nothing']],
                            'combined': len(case['actions_since']), 'replaces': written['replaces'],
                            'rule': written['rule'], 'applies_when': written['applies_when'], 'replaced_at': None})
            if written['replaces']:
                lessons[slots[written['replaces'] - 1]]['replaced_at'] = i - start + 1
                slots[written['replaces'] - 1] = number
            else:
                slots.append(number)
            row['lesson'] = number
        steps.append(row)
        board = np.asarray(t['after']['frames'][-1], dtype=np.uint8)
    summary = level_runs.summary(folder)
    return {'layer': bool(config.get('no_effect_lessons')), 'has_layers': bool(config.get('no_effect_lessons')),
            'start': start, 'first': first, 'steps': steps, 'briefs': briefs, 'rules': rules,
            'lessons': lessons, 'deaths': deaths, 'notes': notes, 'level_at_start': summary['level_at_start'],
            'stats': {k: summary[k] for k in ('changed_nothing', 'levels_completed_in_new_actions', 'game_overs',
                                              'lessons_kept', 'actions_per_completed_level')}}


def astra_run(game, start_level, levels, frames, index):
    """GPT-6 Astra's public recording of one game, from the start of a level, in the shape the page plays."""
    def keep(frame):
        code = rle(np.asarray(frame, dtype=np.uint8))
        if code not in index:
            index[code] = len(frames)
            frames.append(code)
        return index[code]

    trace = traces.load_recordings()[('astra-adapter-high', game)]
    keys = measures.keys(trace, measures.counter_mask(trace))
    steps = trace['steps']
    begin = next((i + 1 for i, s in enumerate(steps) if s['lc'] == start_level - 1), 0) if start_level > 1 else 0
    board = steps[begin - 1]['frame'] if begin else trace['initial']
    first, rows, per_level, count, level = keep(board), [], [], 0, start_level - 1
    for i in range(begin, len(steps)):
        step = steps[i]
        click = step['a'] == 'ACTION6' and step['x'] is not None
        chosen = step['a'] != 'RESET'
        nothing = chosen and step['state'] == 'NOT_FINISHED' and keys[i + 1] == keys[i]
        rows.append({'a': 0 if step['a'] == 'RESET' else int(step['a'][6:]), 'x': step['x'] if click else None,
                     'y': step['y'] if click else None, 'n': i + 1,
                     'c': int(board[step['y'], step['x']]) if click and board.ndim == 2 else None,
                     'f': [keep(step['frame'])], 'reset': not chosen, 'none': bool(nothing),
                     's': 'dead' if step['state'] == 'GAME_OVER' else 'level' if step['lc'] > level else '',
                     'lvl': step['lc'], 'case': None, 'may': False, 'since': 0, 'check': None, 'plan': None, 'lesson': None})
        count += 1
        board = step['frame']
        if step['lc'] > level:
            per_level.append(count)
            count, level = 0, step['lc']
            if level >= start_level - 1 + levels:
                break
    return {'layer': False, 'astra': True, 'n': 1, 'start': begin, 'first': first, 'steps': rows, 'lessons': [],
            'deaths': [], 'notes': [], 'level_at_start': start_level,
            'stats': {'changed_nothing': sum(r['none'] for r in rows), 'levels_completed_in_new_actions': len(per_level),
                      'game_overs': sum(r['s'] == 'dead' for r in rows), 'lessons_kept': 0,
                      'actions_per_completed_level': per_level}}


def build(out_path, which, stamp):
    spec = SETS[which]
    frames, index, games = [], {}, []
    for game, where in spec['games']:
        runs = []
        if game in spec.get('astra', {}):
            runs.append(astra_run(game, spec['astra'][game], spec['astra_levels'], frames, index))
        for arm in spec.get('arms', ()):
            for n in range(1, level_runs.REPEATS + 1):
                folder = level_runs.RUNS / ('%s-%s-%s-%d-%s' % (spec.get('prefix', 'waste'), game.split('-')[0], arm, n, stamp))
                runs.append({'n': n, **one_run(folder, frames, index)})
        for column, (prefix, arm, numbers, fixed) in spec.get('columns', {}).items():
            for n in numbers:       # the column is chosen here, not by which layers the run had
                folder = level_runs.RUNS / ('%s-%s-%s-%d-%s' % (prefix, game.split('-')[0], arm, n, fixed or stamp))
                runs.append({'n': n, **one_run(folder, frames, index), 'layer': column == 'layer'})
        games.append({'g': game.split('-')[0], 'where': where, 'runs': runs})
    data = {'frames': frames, 'games': games,
            'meta': {**{k: spec[k] for k in ('h1', 'second', 'sub', 'directional')}, 'astra': bool(spec.get('astra')),
                     **{k: spec[k] for k in ('first', 'first_short', 'lede') if k in spec}}}
    page = PAGE.replace('__TITLE__', spec['title']).replace('__DATA__', json.dumps(data, separators=(',', ':')))
    Path(out_path).write_text(page)
    return data


PAGE = r'''<title>__TITLE__</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;600&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
/* Layout: a game switch, then two players side by side (unchanged | with the layer). Each: run tabs, board, a strip with one cell per action, transport, what happened at the selected action, and the lessons of the run. */
:root {
  --bg: #f3f5f7; --surface: #ffffff; --fg: #18222b; --muted: #5a6875; --line: #d5dce2; --matte: #7d8891;
  --dead: #b3261e; --alive: #0b6e6e; --pick: #18222b; --soft: #e9edf1; --cell: #cfd7de; --done: #7f8c98; --idle: #c77700; --other: #6b3fa0;
  --display: "Space Grotesk", "Inter", system-ui, sans-serif;
  --body: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #12171c; --surface: #1b2229; --fg: #e6ebef; --muted: #9aa7b3; --line: #2f3a44; --matte: #4b5660;
  --dead: #ff8a80; --alive: #5fd0cc; --pick: #e6ebef; --soft: #242d36; --cell: #34404b; --done: #8794a0; --idle: #f0b24a; --other: #c3a2f2; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #12171c; --surface: #1b2229; --fg: #e6ebef; --muted: #9aa7b3; --line: #2f3a44; --matte: #4b5660;
  --dead: #ff8a80; --alive: #5fd0cc; --pick: #e6ebef; --soft: #242d36; --cell: #34404b; --done: #8794a0; --idle: #f0b24a; --other: #c3a2f2; color-scheme: dark }
body { background: var(--bg); color: var(--fg); font-family: var(--body); font-size: 15px; line-height: 1.55; }
.wrap { max-width: 1180px; margin: 0 auto; padding-block: 32px 56px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: flex; flex-direction: column; gap: 22px; }
h1 { font-family: var(--display); font-weight: 600; font-size: 30px; line-height: 1.15; margin: 0; text-wrap: balance; }
h2 { font-family: var(--display); font-weight: 600; font-size: 20px; margin: 0; text-wrap: balance; }
p { margin: 0; }
header { display: flex; flex-direction: column; gap: 12px; }
.lede { max-width: 72ch; } .sub { max-width: 72ch; color: var(--muted); }
table { border-collapse: collapse; font-size: 13.5px; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 4px 16px 4px 0; border-bottom: 1px solid var(--line); }
th { font-weight: 500; color: var(--muted); }
.scroll { overflow-x: auto; }
.players { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 340px), 1fr)); gap: 22px; align-items: start; }
.player { background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 16px;
  display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.tabs, .bar { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.bar .label { font-size: 13px; color: var(--muted); }
button, select { font: inherit; color: var(--fg); background: var(--soft); border: 1px solid var(--line); border-radius: 4px;
  padding: 5px 12px; cursor: pointer; font-variant-numeric: tabular-nums; }
select { padding: 5px 6px; }
button:focus-visible, select:focus-visible, .strip:focus-visible { outline: 2px solid var(--alive); outline-offset: 2px; }
button[aria-pressed="true"] { background: var(--pick); color: var(--surface); border-color: var(--pick); }
button.play { min-width: 74px; font-weight: 600; }
button:disabled { opacity: .45; cursor: default; }
.stats { font-size: 13px; color: var(--muted); font-variant-numeric: tabular-nums; }
canvas { display: block; width: 100%; height: auto; aspect-ratio: 1; background: var(--matte); border: 6px solid var(--matte); border-radius: 3px; }
.strip { display: flex; gap: 1px; height: 26px; align-items: stretch; cursor: pointer; border-radius: 3px; }
.strip span { flex: 1 1 0; min-width: 0; background: var(--cell); border-radius: 1px; position: relative; }
.strip span.done { background: var(--done); }
.strip span.reset { background: repeating-linear-gradient(135deg, var(--cell) 0 2px, var(--surface) 2px 4px); }
.strip span.none { background: var(--idle); }
.strip span.dead { background: var(--dead); }
.strip span.level { background: var(--alive); }
.strip span.lesson::before { content: ""; position: absolute; left: 0; right: 0; bottom: -5px; height: 3px; background: var(--other); border-radius: 1px; }
.strip span.cur { box-shadow: 0 0 0 2px var(--pick); z-index: 1; }
.stripbox { padding-block: 2px 6px; }
.count { font-family: var(--mono); font-size: 12.5px; color: var(--muted); margin-left: auto; }
.now { border-top: 1px solid var(--line); padding-top: 12px; display: flex; flex-direction: column; gap: 9px; min-height: 230px; }
.headline { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 10px; }
.headline .num { font-family: var(--display); font-weight: 600; font-size: 17px; font-variant-numeric: tabular-nums; }
.did { font-family: var(--mono); font-size: 13px; display: inline-flex; align-items: center; gap: 6px; }
.sw { display: inline-block; width: 12px; height: 12px; border: 1px solid var(--muted); border-radius: 2px; }
.badge { font-size: 12.5px; font-weight: 600; padding: 1px 8px; border-radius: 999px; border: 1.5px solid currentColor; }
.badge.dead { color: var(--dead); } .badge.level { color: var(--alive); } .badge.reset { color: var(--muted); }
.flag { font-size: 13.5px; color: var(--idle); }
.cap { font-size: 12.5px; color: var(--muted); }
blockquote { margin: 0; padding-left: 12px; border-left: 2px solid var(--line); font-size: 14px; overflow-wrap: anywhere; }
blockquote.check { border-left-color: var(--alive); } blockquote.lesson { border-left-color: var(--other); }
.said { display: flex; flex-direction: column; gap: 5px; }
.said b { font-weight: 600; }
.lessons { border-top: 1px solid var(--line); padding-top: 12px; display: flex; flex-direction: column; gap: 10px; }
.lessonrow { font-size: 13.5px; display: flex; flex-direction: column; gap: 3px; padding-left: 10px; border-left: 2px solid var(--other); }
.lessonrow.later { opacity: .4; } .lessonrow.gone { border-left-color: var(--line); }
.lessonrow b { font-weight: 600; }
.key { display: flex; flex-wrap: wrap; gap: 6px 20px; font-size: 13.5px; color: var(--muted); align-items: center; }
.key span { display: inline-flex; align-items: center; gap: 7px; }
.key i { display: inline-block; width: 12px; height: 16px; border-radius: 1px; background: var(--cell); }
.key i.none { background: var(--idle); } .key i.dead { background: var(--dead); } .key i.level { background: var(--alive); }
.key i.reset { background: repeating-linear-gradient(135deg, var(--cell) 0 2px, var(--surface) 2px 4px); border: 1px solid var(--line); }
.key i.lesson { height: 3px; background: var(--other); }
@media (max-width: 760px) { h1 { font-size: 25px; } .now { min-height: 0; } }
</style>
<div class="wrap">
  <header>
    <h1 id="h1"></h1>
    <p class="lede" id="lede"></p>
    <div class="scroll"><table id="table"></table></div>
    <p class="sub" id="sub"></p>
    <div class="key">
      <span><i class="none"></i>action changed nothing</span>
      <span><i class="level"></i>level completed</span>
      <span><i class="dead"></i>game over</span>
      <span><i class="reset"></i>level restarted by the controller</span>
      <span><i class="lesson"></i>lesson written</span>
    </div>
    <div class="bar" id="games"><span class="label">Game</span></div>
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
function ring(g, x, y, colour) {
  const cx = (x + 0.5) * S, cy = (y + 0.5) * S;
  for (const [w, c] of [[7, 'rgba(255,255,255,0.95)'], [3, colour]]) {
    g.lineWidth = w; g.strokeStyle = c; g.lineCap = 'round';
    g.beginPath(); g.arc(cx, cy, S * 2.6, 0, Math.PI * 2); g.stroke();
    g.beginPath(); g.moveTo(cx - S, cy); g.lineTo(cx + S, cy); g.moveTo(cx, cy - S); g.lineTo(cx, cy + S); g.stroke();
  }
}
const DIRS = {1: 'up', 2: 'down', 3: 'left', 4: 'right'};
const name = s => s.a === 0 ? 'level restart' : s.a === 6 ? 'click at x=' + s.x + ', y=' + s.y
  : 'ACTION' + s.a + (DATA.meta.directional && DIRS[s.a] ? ' (' + DIRS[s.a] + ')' : '');
function arrow(g, a, colour) {       // the move being made, in the top-left corner of the board
  const cx = 34, cy = 34, r = 24, [dx, dy] = {1: [0, -1], 2: [0, 1], 3: [-1, 0], 4: [1, 0]}[a];
  g.fillStyle = 'rgba(255,255,255,0.95)'; g.beginPath(); g.arc(cx, cy, r, 0, Math.PI * 2); g.fill();
  g.strokeStyle = colour; g.fillStyle = colour; g.lineWidth = 5; g.lineCap = 'round'; g.lineJoin = 'round';
  g.beginPath(); g.moveTo(cx - dx * 12, cy - dy * 12); g.lineTo(cx + dx * 8, cy + dy * 8); g.stroke();
  g.beginPath(); g.moveTo(cx + dx * 16, cy + dy * 16); g.lineTo(cx + dx * 4 - dy * 9, cy + dy * 4 - dx * 9); g.lineTo(cx + dx * 4 + dy * 9, cy + dy * 4 + dx * 9); g.closePath(); g.fill();
}
const plural = (n, word) => n + ' ' + word + (n === 1 ? '' : 's');
let repaints = [], stops = [];
function player(title, about, runs, id) {
  const box = el('section', 'player');
  box.appendChild(el('h2', null, title));
  box.appendChild(el('p', 'cap', about));
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
  const lessonbox = el('div', 'lessons'); box.appendChild(lessonbox);

  let run = runs[0], pos = 0, shown = 0, playing = false, token = 0, cells = [], rows = [];
  const rate = () => +speed.value;
  const boardAt = p => frame(p === 0 ? run.first : run.steps[p - 1].f[run.steps[p - 1].f.length - 1]);

  function describe(p) {
    now.textContent = '';
    const head = el('div', 'headline');
    if (p === 0) {
      head.appendChild(el('span', 'num', 'Start: level ' + run.level_at_start));
      now.appendChild(head);
      now.appendChild(el('p', 'cap', (run.astra ? 'The first board of this level in the recording. ' : run.start ? 'The board after the ' + run.start + ' saved actions that were repeated, the same in all four runs of this game. ' : 'The first board of the game. ')
        + 'Press Play, or step with Next. Click the strip to jump to an action.'));
      return;
    }
    const s = run.steps[p - 1];
    head.appendChild(el('span', 'num', 'Action ' + p + ' of ' + run.steps.length));
    const did = el('span', 'did', name(s));
    if (s.c != null) { const sw = el('span', 'sw'); sw.style.background = PALETTE[s.c]; sw.title = 'colour of the clicked cell'; did.appendChild(sw); }
    head.appendChild(did);
    if (s.s === 'dead') head.appendChild(el('span', 'badge dead', 'Game over'));
    if (s.s === 'level') head.appendChild(el('span', 'badge level', 'Level ' + s.lvl + ' completed'));
    if (s.reset) head.appendChild(el('span', 'badge reset', 'No choice by the agent'));
    now.appendChild(head);
    if (s.reset) { now.appendChild(el('p', 'cap', 'After a game over the controller restarts the level. No model call is made.')); return; }
    if (s.none) now.appendChild(el('p', 'flag', 'This action changed nothing on the board.'));
    if (s.death != null) {
      const l = run.deaths[s.death], said = el('div', 'said');
      said.appendChild(el('div', 'cap', 'On this turn, the first after its game over, it wrote what the game over teaches.'));
      const q = el('blockquote', 'lesson'); q.appendChild(el('b', null, 'Rule. ')); q.appendChild(document.createTextNode(l.rule));
      const w = el('blockquote', 'lesson'); w.appendChild(el('b', null, 'Applies when. ')); w.appendChild(document.createTextNode(l.applies_when));
      said.appendChild(q); said.appendChild(w); now.appendChild(said);
    }
    if (s.lesson != null) {
      const l = run.lessons[s.lesson], said = el('div', 'said');
      said.appendChild(el('div', 'cap', 'On this turn it explained action ' + (l.explains - run.start) + (l.also.length ? ' (and ' + l.also.map(n => n - run.start).join(', ') + ')' : '')
        + ', after ' + plural(l.combined, 'further action') + (l.replaces ? '. This replaced lesson ' + l.replaces + '.' : '. A new lesson.')));
      const q = el('blockquote', 'lesson'); q.appendChild(el('b', null, 'Rule. ')); q.appendChild(document.createTextNode(l.rule));
      const w = el('blockquote', 'lesson'); w.appendChild(el('b', null, 'Applies when. ')); w.appendChild(document.createTextNode(l.applies_when));
      said.appendChild(q); said.appendChild(w); now.appendChild(said);
    } else if (s.case) {
      now.appendChild(el('p', 'cap', 'Action ' + (+s.case.slice(1) - run.start) + ' changed nothing and is not explained yet. '
        + (s.may ? 'The agent could explain it on this turn and chose to wait.' : 'It is too early: no further action has followed it.')));
    }
    if (s.check) {
      const said = el('div', 'said'); said.appendChild(el('div', 'cap', 'Its check of this action against the lessons'));
      said.appendChild(el('blockquote', 'check', s.check)); now.appendChild(said);
    }
    if (s.aim) {
      const said = el('div', 'said'); said.appendChild(el('div', 'cap', 'What it said it was aiming at'));
      said.appendChild(el('blockquote', 'check', s.aim)); now.appendChild(said);
    }
    if (s.note) {
      const said = el('div', 'said'); said.appendChild(el('div', 'cap', 'It noted what look ' + s.note.look + ' does'));
      said.appendChild(el('blockquote', 'lesson', s.note.does)); now.appendChild(said);
    }
    if (s.brief) {
      const said = el('div', 'said');
      said.appendChild(el('div', 'cap', s.brief.asked ? 'Its brief for level ' + s.brief.level + ', written on its first turn there' : 'It replaced its brief for level ' + s.brief.level));
      [['What completed the last level. ', s.brief.won_by], ['What is different. ', s.brief.different], ['Why. ', s.brief.why], ['First. ', s.brief.first]].filter(pair => pair[1]).forEach(([label, text]) => {
        const q = el('blockquote', 'lesson'); q.appendChild(el('b', null, label)); q.appendChild(document.createTextNode(text)); said.appendChild(q);
      });
      now.appendChild(said);
    }
    if (s.rules) {
      const said = el('div', 'said'); said.appendChild(el('div', 'cap', 'It recorded ' + plural(s.rules.length, 'rule') + ' as confirmed'));
      s.rules.forEach(r => said.appendChild(el('blockquote', 'lesson', (r.replaces ? 'In place of rule ' + r.replaces + ': ' : '') + r.rule)));
      now.appendChild(said);
    }
    if (s.plan) {
      const said = el('div', 'said'); said.appendChild(el('div', 'cap', 'What its notes said when it chose this'));
      said.appendChild(el('blockquote', null, s.plan)); now.appendChild(said);
    }
  }
  function chrome(p) {
    shown = p;
    cells.forEach((c, i) => { c.classList.toggle('done', i < p - 1); c.classList.toggle('cur', i === p - 1); });
    rows.forEach(([row, l]) => { row.classList.toggle('later', l.at > p); row.classList.toggle('gone', l.replaced_at != null && l.replaced_at <= p); });
    strip.setAttribute('aria-valuenow', p);
    strip.setAttribute('aria-valuetext', p === 0 ? 'Start' : 'Action ' + p + ': ' + name(run.steps[p - 1]));
    count.textContent = p + ' / ' + run.steps.length;
    back.disabled = first.disabled = p === 0; next.disabled = p >= run.steps.length;
    play.textContent = playing ? 'Pause' : (pos >= run.steps.length ? 'Replay' : 'Play');
    describe(p);
  }
  function rest() { paint(canvas, boardAt(pos)); chrome(pos); canvas.setAttribute('aria-label', title + ', board ' + (pos === 0 ? 'at the start' : 'after action ' + pos)); }
  function jump(p) { token++; playing = false; pos = Math.max(0, Math.min(run.steps.length, p)); rest(); }
  async function advance() {
    const mine = ++token, s = run.steps[pos];
    chrome(pos + 1);
    const g = paint(canvas, boardAt(pos));
    const tone = css(s.s === 'dead' ? '--dead' : s.none ? '--idle' : '--alive');
    if (s.a === 6) ring(g, s.x, s.y, tone);
    else if (DATA.meta.directional && DIRS[s.a]) arrow(g, s.a, tone);
    await sleep((s.reset ? 250 : 560) / rate()); if (mine !== token) return false;
    const list = reduced ? [] : s.f.slice(0, -1), wait = list.length > 24 ? 40 : 80;
    for (const f of list) { paint(canvas, frame(f)); await sleep(wait / rate()); if (mine !== token) return false; }
    pos++; rest(); return true;
  }
  async function runPlay() {
    if (pos >= run.steps.length) { pos = 0; rest(); }
    playing = true; play.textContent = 'Pause';
    while (playing && pos < run.steps.length) {
      if (!(await advance())) return;
      const mine = token, s = run.steps[pos - 1];
      await sleep((s.s === 'dead' || s.lesson != null ? 1300 : s.none ? 700 : 280) / rate());
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
      const c = el('span', [s.s, s.reset ? 'reset' : '', s.none ? 'none' : '', s.lesson != null || s.death != null || s.brief ? 'lesson' : ''].filter(Boolean).join(' '));
      c.dataset.at = i + 1;
      c.title = 'Action ' + (i + 1) + ': ' + name(s) + (s.s === 'dead' ? ', game over' : s.s === 'level' ? ', level completed' : s.none ? ', changed nothing' : '');
      strip.appendChild(c); cells.push(c);
    });
    const t = r.stats;
    stats.textContent = plural(t.changed_nothing, 'action') + ' changed nothing · ' + plural(t.levels_completed_in_new_actions, 'level') + ' completed'
      + (t.actions_per_completed_level.length ? ' (in ' + t.actions_per_completed_level.join(', ') + ' actions)' : '')
      + ' · ' + plural(t.game_overs, 'game over') + ((r.has_layers ?? r.layer) ? ' · ' + plural(r.lessons.length + r.deaths.length, 'lesson') + ' written' : '')
      + (r.notes.length ? ' · ' + plural(r.notes.length, 'note') + ' on things' : '')
      + ((r.briefs || []).length ? ' · ' + plural(r.briefs.length, 'brief') + ' · ' + plural(r.rules.length, 'rule') + ' recorded' : '');
    lessonbox.textContent = ''; rows = []; lessonbox.hidden = !(r.has_layers ?? r.layer);
    if (r.has_layers ?? r.layer) {
      lessonbox.appendChild(el('div', 'cap', r.lessons.length + r.deaths.length ? 'The lessons of this run, in the order written. Faded ones come later than the action shown; grey ones have been replaced.' : 'No lesson was written in this run: no action changed nothing by the controller\u2019s check, and there was no game over.'));
      r.deaths.forEach(l => {
        const row = el('div', 'lessonrow');
        row.appendChild(el('div', 'cap', 'Written at action ' + l.at + ', after a game over'));
        const a = el('div'); a.appendChild(el('b', null, 'Rule. ')); a.appendChild(document.createTextNode(l.rule)); row.appendChild(a);
        const b = el('div'); b.appendChild(el('b', null, 'Applies when. ')); b.appendChild(document.createTextNode(l.applies_when)); row.appendChild(b);
        lessonbox.appendChild(row); rows.push([row, {at: l.at, replaced_at: null}]);
      });
      if ((r.briefs || []).length) {
        const more = el('details'), list = el('div'); list.style.cssText = 'display:flex;flex-direction:column;gap:6px;margin-top:8px';
        more.open = true;
        more.appendChild(el('summary', 'cap', 'Its ' + plural(r.briefs.length, 'brief') + ' and the ' + plural(r.rules.length, 'rule') + ' it recorded'));
        const say = (label, text) => { const line = el('div'); line.style.fontSize = '13.5px'; line.appendChild(el('b', null, label)); line.appendChild(document.createTextNode(text)); list.appendChild(line); };
        r.briefs.forEach(b => {
          if (b.won_by) say('Action ' + b.at + ', what completed the level before: ', b.won_by);
          say('Action ' + b.at + ', brief for level ' + b.level + (b.asked ? '' : ' (replaced)') + '. Different: ', b.different);
          say('Why: ', b.why); say('First: ', b.first);
        });
        r.rules.forEach(n => say('Action ' + n.at + ', rule' + (n.replaces ? ' in place of rule ' + n.replaces : '') + '. ', n.rule));
        more.appendChild(list); lessonbox.appendChild(more);
      }
      if (r.notes.length) {
        const more = el('details'), list = el('div'); list.style.cssText = 'display:flex;flex-direction:column;gap:6px;margin-top:8px';
        more.appendChild(el('summary', 'cap', 'Its ' + r.notes.length + ' notes on what kinds of thing do'));
        r.notes.forEach(note => { const line = el('div'); line.style.fontSize = '13.5px'; line.appendChild(el('b', null, 'Action ' + note.at + ', look ' + note.look + '. ')); line.appendChild(document.createTextNode(note.does)); list.appendChild(line); });
        more.appendChild(list); lessonbox.appendChild(more);
      }
      r.lessons.forEach((l, n) => {
        const row = el('div', 'lessonrow');
        row.appendChild(el('div', 'cap', 'Written at action ' + l.at + ', explaining action ' + (l.explains - r.start) + (l.replaces ? ', replacing lesson ' + l.replaces : '')
          + (l.replaced_at ? ' · replaced at action ' + l.replaced_at : '')));
        const a = el('div'); a.appendChild(el('b', null, 'Rule. ')); a.appendChild(document.createTextNode(l.rule)); row.appendChild(a);
        const b = el('div'); b.appendChild(el('b', null, 'Applies when. ')); b.appendChild(document.createTextNode(l.applies_when)); row.appendChild(b);
        const go = el('button', null, 'Go to action ' + l.at); go.style.alignSelf = 'flex-start'; go.style.fontSize = '12.5px'; go.style.padding = '2px 8px';
        go.addEventListener('click', () => jump(l.at)); row.appendChild(go);
        lessonbox.appendChild(row); rows.push([row, l]);
      });
    }
    rest();
  }
  runs.forEach((r, i) => {
    const b = el('button', null, (r.astra ? 'Recording' : 'Run ' + r.n) + ' · ' + r.stats.changed_nothing + ' changed nothing');
    b.addEventListener('click', () => choose(r, b)); tabs.appendChild(b);
  });
  first.addEventListener('click', () => jump(0));
  back.addEventListener('click', () => jump(shown - 1));
  next.addEventListener('click', () => { if (pos !== shown) { jump(shown); return; } playing = false; if (pos < run.steps.length) advance(); });
  play.addEventListener('click', () => { if (playing) jump(shown); else runPlay(); });
  strip.addEventListener('click', e => { const c = e.target.closest('span'); if (c) jump(+c.dataset.at); });
  strip.addEventListener('keydown', e => {
    const to = {ArrowLeft: shown - 1, ArrowDown: shown - 1, ArrowRight: shown + 1, ArrowUp: shown + 1, Home: 0, End: run.steps.length}[e.key];
    if (to != null) { e.preventDefault(); jump(to); }
  });
  document.getElementById('players').appendChild(box);
  choose(runs[0], tabs.children[0]);
  repaints.push(() => { if (!playing) rest(); });
  stops.push(() => { token++; playing = false; });
}
// summary table and totals
const table = document.getElementById('table');
document.getElementById('h1').textContent = DATA.meta.h1; document.getElementById('sub').textContent = DATA.meta.sub;
const second = DATA.meta.second[0].charAt(0).toLowerCase() + DATA.meta.second[0].slice(1);
if (DATA.meta.astra) document.querySelector('.wrap').style.maxWidth = '1620px';
const columns = DATA.meta.astra
  ? ['Game', 'Start', 'GPT-6 Astra, actions per level', 'Opus 5.5 unchanged, actions per completed level', 'Opus 5.5 with the layers, actions per completed level']
  : ['Game', 'Start', 'Changed nothing, ' + (DATA.meta.first_short || 'unchanged'), 'Changed nothing, ' + second, 'Levels completed, ' + (DATA.meta.first_short || 'unchanged'), 'Levels completed, ' + second];
const head = el('tr'); columns.forEach(t => head.appendChild(el('th', null, t)));
table.appendChild(head);
let wastedPlain = 0, wastedLayer = 0, levelsPlain = 0, levelsLayer = 0;
for (const game of DATA.games) {
  const plain = game.runs.filter(r => !r.layer && !r.astra), layer = game.runs.filter(r => r.layer), row = el('tr');
  const list = (runs, key) => runs.map(r => r.stats[key]).join(' and ');
  const levels = runs => runs.map(r => r.stats.actions_per_completed_level.length ? r.stats.actions_per_completed_level.join(', ') : 'none').join(' | ');
  (DATA.meta.astra
    ? [game.g, game.where, levels(game.runs.filter(r => r.astra)), levels(plain), levels(layer)]
    : [game.g, game.where, list(plain, 'changed_nothing'), list(layer, 'changed_nothing'), list(plain, 'levels_completed_in_new_actions'), list(layer, 'levels_completed_in_new_actions')])
    .forEach(t => row.appendChild(el('td', null, t)));
  table.appendChild(row);
  plain.forEach(r => { wastedPlain += r.stats.changed_nothing; levelsPlain += r.stats.levels_completed_in_new_actions; });
  layer.forEach(r => { wastedLayer += r.stats.changed_nothing; levelsLayer += r.stats.levels_completed_in_new_actions; });
}
const total = DATA.games.reduce((n, game) => n + game.runs.filter(r => !r.astra).length, 0);
document.getElementById('lede').textContent = DATA.meta.lede || ((DATA.meta.astra ? 'GPT-6 Astra\u2019s recorded play beside ours. ' : '') + total + ' runs of ours on local copies of ' + plural(DATA.games.length, 'game') + ': for each game, two with the 6 November harness unchanged and two '
  + second.replace('opus 5.5 ', '') + ', from the same start. Actions that changed nothing: ' + wastedPlain + ' in the unchanged runs, ' + wastedLayer + ' in the others. Levels completed: ' + levelsPlain + ' and ' + levelsLayer + '.');
const gameBar = document.getElementById('games');
function showGame(game, button) {
  stops.forEach(f => f()); repaints = []; stops = [];
  [...gameBar.querySelectorAll('button')].forEach(b => b.setAttribute('aria-pressed', b === button ? 'true' : 'false'));
  document.getElementById('players').textContent = '';
  const recorded = game.runs.filter(r => r.astra);
  if (recorded.length) player('GPT-6 Astra, provider harness', 'The public recording of its run, from the same level. One board per action; its reasoning is not recorded.', recorded, 'astra');
  player(DATA.meta.first ? DATA.meta.first[0] : DATA.meta.astra ? 'Opus 5.5 unchanged' : 'Unchanged', DATA.meta.first ? DATA.meta.first[1] : 'The harness as it ran on 6 November.', game.runs.filter(r => !r.layer && !r.astra), 'plain');
  player(DATA.meta.second[0], DATA.meta.second[1], game.runs.filter(r => r.layer), 'layer');
}
DATA.games.forEach((game, i) => {
  const b = el('button', null, game.g + ' · ' + game.where); b.addEventListener('click', () => showGame(game, b)); gameBar.appendChild(b);
});
showGame(DATA.games[0], gameBar.querySelector('button'));
const repaint = () => repaints.forEach(f => f());
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', repaint);
new MutationObserver(repaint).observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme']});
</script>
'''


if __name__ == '__main__':
    built = build(sys.argv[1], sys.argv[2], sys.argv[3])
    print('frames', len(built['frames']), 'bytes', Path(sys.argv[1]).stat().st_size)
    for game in built['games']:
        for r in game['runs']:
            print(game['g'], 'layer' if r['layer'] else 'unchanged', r['n'], 'actions', len(r['steps']), r['stats'],
                  'lessons', [(l['at'], l['explains'] - r['start'], l['combined'], l['replaces'], l['replaced_at']) for l in r['lessons']],
                  'after game overs', [d['at'] for d in r['deaths']])
