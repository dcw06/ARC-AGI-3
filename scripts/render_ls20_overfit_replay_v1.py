"""Render a pinned fresh-engine fitted-agent journal; never execute game actions."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from certification.phase4_multimodal_preflight_v3.images import PALETTE, png
from research.initial_geometry_assistance_v1.geometry import digest
from research.initial_geometry_assistance_v1.policy import check_observation

NAMES = {1: 'UP', 2: 'DOWN', 3: 'LEFT', 4: 'RIGHT'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify(events):
    """Derive frame order and actual level completions before exporting anything."""
    position = 0

    def take(kind):
        nonlocal position
        if position >= len(events) or type(events[position]) is not dict or events[position].get('kind') != kind:
            raise ValueError('unexpected replay event order: expected ' + kind)
        event = events[position]
        position += 1
        return event

    seed = take('bootstrap_intent').get('seed')
    if type(seed) is not int or seed != 0:
        raise ValueError('replay seed differs')
    current = check_observation(take('initial')['observation'])
    if current['levels_completed'] != 0 or current['state'] != 'NOT_FINISHED':
        raise ValueError('replay does not start at level one')
    states, frames, boundaries = [current], [{'move': 0, 'action': 'START', 'levels_completed': 0}], []
    while position < len(events) and events[position].get('kind') == 'dispatch_intent':
        index = len(states) - 1
        if index >= 256:
            raise ValueError('replay exceeds move cap')
        intent, transition = take('dispatch_intent'), take('transition')
        for event in (intent, transition):
            if type(event.get('index')) is not int or event['index'] != index:
                raise ValueError('replay move index differs')
        action = transition.get('action')
        if (type(action) is not dict or set(action) != {'action_id', 'action_data'} or
                type(action['action_id']) is not int or action['action_id'] not in NAMES or
                type(action['action_data']) is not dict or action['action_data'] or
                action['action_id'] not in current['legal_actions'] or
                digest(intent.get('action')) != digest(action) or intent.get('before_sha256') != digest(current)):
            raise ValueError('replay action or dispatch intent differs')
        before, after = check_observation(transition['before']), check_observation(transition['after'])
        if digest(before) != digest(current) or before['state'] != 'NOT_FINISHED':
            raise ValueError('replay observation chain differs')
        old_level, new_level = before['levels_completed'], after['levels_completed']
        if not old_level <= new_level <= min(old_level + 1, 3) or after['state'] != 'NOT_FINISHED':
            raise ValueError('replay level progression or state differs')
        if new_level > old_level:
            boundary = {'level': new_level, 'after_moves': index + 1,
                        'moves': index + 1 - (boundaries[-1]['after_moves'] if boundaries else 0)}
            event = take('level_completed')
            if digest({k: v for k, v in event.items() if k != 'kind'}) != digest(boundary):
                raise ValueError('replay completion event differs')
            boundaries.append(boundary)
        current = after
        states.append(current)
        frames.append({'move': index + 1, 'action': NAMES[action['action_id']], 'levels_completed': new_level})
        if new_level == 3:
            break
    receipt = take('closed').get('receipt')
    if digest(receipt) != digest({'closed': True, 'local_scorecard_opened': True,
                                  'local_scorecard_closed': True, 'online_calls': 0}):
        raise ValueError('replay cleanup receipt differs')
    result = take('summary')
    if (position != len(events) or result.get('success') is not True or result.get('error') is not None or
            type(result.get('moves')) is not int or result['moves'] != len(states) - 1 or
            type(result.get('levels_completed')) is not int or result['levels_completed'] != 3 or
            current['levels_completed'] != 3 or digest(result.get('final_observation')) != digest(current) or
            digest(result.get('level_boundaries')) != digest(boundaries) or
            type(result.get('model_generations')) is not int or result['model_generations'] != 0 or
            result.get('reason') != 'three_levels_completed'):
        raise ValueError('replay summary is not a verified three-level completion')
    return states, frames, boundaries


HTML = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>ls20: three completed levels</title>
<style>body{font:17px system-ui;margin:2em auto;max-width:1000px;background:#10151d;color:#eee;padding:0 1em}
img{image-rendering:pixelated;max-width:100%;background:#000}button,input{font:inherit}input{width:65%}
.status{color:#86efac}code{color:#b9dfff}a{color:#a9cfff}#coordinate{font-family:monospace}</style>
<h1>ls20 fitted agent: first three levels completed</h1>
<p class="status">Fresh local engine execution: __MOVES__ moves, three observed level increments.</p>
<p>This controller memorized the owner's demonstration on the same game and seed. This is a fresh
agent execution, not the original human log. It demonstrates deliberate overfitting; it does not
show generalization, independent rule discovery or VLM training. No GPU or model inference was used.</p>
<p>Each original 64 × 64 observation is displayed as 448 × 448 pixels using exact 7 × 7 blocks.
The completion frame displays the next level's board. The run stops immediately after level 3 passes.</p>
<p id="label"></p><img id="board" width="448" height="448" alt="Actual game observation">
<p id="coordinate">Hover over the board for native coordinates.</p>
<p><button id="play">Play</button> <button id="back">Previous</button> <button id="next">Next</button></p>
<input id="slider" aria-label="Replay frame" type="range" min="0" max="__MAX__" value="0">
<span id="count"></span><h2>Observed level completions</h2><ul id="boundaries"></ul>
<script>const frames=__FRAMES__,boundaries=__BOUNDARIES__;let index=0,timer=null;
const board=document.getElementById('board'),slider=document.getElementById('slider');
function draw(){const f=frames[index];board.src=f.image;slider.value=index;
document.getElementById('label').textContent=`Move ${f.move}: ${f.action} | Completed levels: ${f.levels_completed}`;
document.getElementById('count').textContent=`${index+1} / ${frames.length}`;}
function stop(){clearInterval(timer);timer=null;document.getElementById('play').textContent='Play';}
slider.oninput=()=>{stop();index=Number(slider.value);draw()};
document.getElementById('back').onclick=()=>{stop();index=Math.max(0,index-1);draw()};
document.getElementById('next').onclick=()=>{stop();index=Math.min(frames.length-1,index+1);draw()};
document.getElementById('play').onclick=()=>{if(timer){stop();return}if(index===frames.length-1)index=0;
document.getElementById('play').textContent='Pause';draw();timer=setInterval(()=>{if(index===frames.length-1){stop();return}index++;draw()},400)};
board.onmousemove=e=>{const r=board.getBoundingClientRect(),x=Math.floor((e.clientX-r.left)*64/r.width),
y=Math.floor((e.clientY-r.top)*64/r.height);document.getElementById('coordinate').textContent=`Cell (${x}, ${y})`;};
for(const b of boundaries){const li=document.createElement('li');li.textContent=`Level ${b.level}: ${b.moves} moves, completed after move ${b.after_moves}`;document.getElementById('boundaries').appendChild(li)}draw();
</script></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--events', type=Path, required=True)
    parser.add_argument('--events-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = args.events.read_bytes()
    if re.fullmatch('[0-9a-f]{64}', args.events_sha256) is None or sha(raw) != args.events_sha256:
        raise ValueError('pinned replay journal differs')
    if args.output.exists():
        raise FileExistsError('preserve previous replays; use a new directory')
    states, frames, boundaries = verify([json.loads(line) for line in raw.splitlines()])
    images = [png(state['grid'], cell=7) for state in states]
    for frame, image in zip(frames, images):
        frame['image'] = 'data:image/png;base64,' + base64.b64encode(image).decode('ascii')
    html = HTML.replace('__MOVES__', str(len(states) - 1)).replace('__MAX__', str(len(states) - 1))
    html = html.replace('__FRAMES__', json.dumps(frames, separators=(',', ':')))
    html = html.replace('__BOUNDARIES__', json.dumps(boundaries, separators=(',', ':')))
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'frames').mkdir()
    (args.output / 'index.html').write_text(html, encoding='utf-8', newline='\n')
    for index, image in enumerate(images):
        (args.output / 'frames' / f'{index:03d}.png').write_bytes(image)
    gif_verification = None
    try:
        import PIL
        from PIL import Image
    except ImportError:
        pass
    else:
        start = 0
        for boundary in boundaries:
            end = boundary['after_moves']
            clip = []
            for state in states[start:end + 1]:
                image = Image.frombytes('P', (64, 64), bytes(v for row in state['grid'] for v in row))
                image.putpalette([v for color in PALETTE for v in color] + [0] * (768 - 48))
                clip.append(image.resize((448, 448), Image.Resampling.NEAREST))
            destination = args.output / f"level-{boundary['level']}.gif"
            clip[0].save(destination, save_all=True, append_images=clip[1:],
                         duration=[1000] + [400] * (len(clip) - 2) + [1200],
                         loop=0, disposal=1, optimize=True)
            with Image.open(destination) as decoded:
                if decoded.n_frames != len(clip):
                    raise ValueError('GIF omitted replay frames')
                for index in range(len(clip)):
                    decoded.seek(index)
                    with Image.open(io.BytesIO(images[start + index])) as original:
                        if decoded.convert('RGB').tobytes() != original.convert('RGB').tobytes():
                            raise ValueError('GIF pixel verification differs')
            start = end
        gif_verification = {'Pillow_version': PIL.__version__, 'every_frame_matches_original_PNG': True}
    files = {path.relative_to(args.output).as_posix(): {'sha256': sha(path.read_bytes()), 'bytes': path.stat().st_size}
             for path in sorted(args.output.rglob('*')) if path.is_file()}
    manifest = {'schema': 'ls20_overfit_v1_replay', 'events_sha256': args.events_sha256,
                'renderer_sha256': sha(Path(__file__).read_bytes()), 'frames': len(states),
                'moves': len(states) - 1, 'levels_completed': 3, 'level_boundaries': boundaries,
                'rendering': '64x64 original cells enlarged to 448x448; exact 7x7 color blocks',
                'GIF_verification': gif_verification, 'files': files}
    manifest_raw = (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode()
    (args.output / 'manifest.json').write_bytes(manifest_raw)
    print(json.dumps({'frames': len(states), 'moves': len(states) - 1, 'levels_completed': 3,
                      'manifest_sha256': sha(manifest_raw), 'GIFs_created': gif_verification is not None}))


if __name__ == '__main__':
    main()
