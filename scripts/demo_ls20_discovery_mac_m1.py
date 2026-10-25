"""CPU-only synthetic diagnostic. No game assets, model, credentials, or network."""
import argparse
import html
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from research.ls20_discovery_mac import EvidenceMemory


def observation(grid):
    return dict(grid=grid, state='NOT_FINISHED', levels_completed=0, legal_actions=[1, 2])


def color(value):
    # Diagnostic colors only; the extractor never receives these RGB values.
    import colorsys
    return tuple(round(v * 255) for v in colorsys.hsv_to_rgb((value * 0.618034) % 1, .48, .9))


def build(output):
    from PIL import Image, ImageDraw
    output.mkdir(parents=True, exist_ok=True)
    scenarios = {
        'relocation': [[[2, 0, 0, 0]], [[0, 0, 0, 2]]],
        'merge_split_ambiguous': [[[2, 0, 2]], [[2, 2, 2]], [[2, 0, 2]]],
        'occlusion_or_disappearance': [[[2, 0, 0]], [[0, 0, 0]], [[0, 0, 2]]],
        'recoloring_unresolved_failure': [[[2, 0, 0]], [[7, 0, 0]]],
        'hidden_mode_a': [[[4]], [[0]], [[0]], [[0]], [[0]]],
        'hidden_mode_b': [[[7]], [[0]], [[0]], [[0]], [[0]]],
    }
    canvas = Image.new('RGB', (1100, 170 * len(scenarios)), '#f5f7fb')
    draw = ImageDraw.Draw(canvas)
    sections, results = [], {}
    for row, (name, grids) in enumerate(scenarios.items()):
        memory = EvidenceMemory(name, observation(grids[0]))
        for grid in grids[1:]:
            memory.append(dict(action_id=1, action_data={}),
                          dict(status='acknowledged', post=observation(grid)))
        memory.save(output / f'{name}.json')
        payload = memory.snapshot()
        restored = EvidenceMemory.load(output / f'{name}.json')
        assert restored.snapshot() == payload
        results[name] = dict(observations=len(payload['observations']),
                            transitions=len(payload['transitions']),
                            identity_alternatives=len(payload['identity_candidates']),
                            snapshot_bytes=(output / f'{name}.json').stat().st_size,
                            restored_exactly=True)
        draw.text((18, row*170+10), name.replace('_', ' '), fill='#14263d')
        panels = []
        for i, (grid, scene) in enumerate(zip(grids, payload['scenes'])):
            x0, y0, size = 18+i*210, row*170+42, 34
            svg = []
            for y, values in enumerate(grid):
                for x, value in enumerate(values):
                    rgb = color(value)
                    draw.rectangle((x0+x*size,y0+y*size,x0+(x+1)*size-1,y0+(y+1)*size-1), fill=rgb, outline='#ffffff')
                    draw.text((x0+x*size+12,y0+y*size+10), str(value), fill='#102030')
                    svg.append(f'<rect x="{x*34}" y="{y*34}" width="34" height="34" fill="rgb{rgb}" stroke="white"/>')
                    svg.append(f'<text x="{x*34+17}" y="{y*34+23}" text-anchor="middle">{value}</text>')
            draw.text((x0,y0+42), f'o{i}: {len(scene["regions"])} region proposals', fill='#14263d')
            panels.append(f'<div><p>o{i} / {len(scene["regions"])} proposals</p><svg width="{34*len(grid[0])}" height="{34*len(grid)}">{"".join(svg)}</svg></div>')
        draw.text((18,row*170+118), f'{len(payload["identity_candidates"])} unresolved links; no confirmed object roles', fill='#14263d')
        sections.append(f'<section><h2>{html.escape(name)}</h2><div class="frames">{"".join(panels)}</div>'
                        f'<details><summary>Inspect masks, identity alternatives and evidence</summary><pre>{html.escape(json.dumps(payload,indent=2))}</pre></details></section>')
    canvas.save(output / 'diagnostics.png')
    (output / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Mac M1 synthetic evidence</title>'
        '<style>body{font:16px system-ui;max-width:1150px;margin:32px auto;color:#14263d;background:#f5f7fb}section{background:white;padding:20px;margin:20px 0}.frames{display:flex;gap:28px;flex-wrap:wrap}pre{overflow:auto;font-size:12px}svg text{font:14px monospace}</style>'
        '<h1>M1: observations, proposals, and retained uncertainty</h1><p>Synthetic CPU fixtures only. '
        'Numbers are observed palette IDs; colors are for display. A region is not a confirmed object. '
        'Merge/split and occlusion keep alternatives. Recoloring exposes a known association failure.</p>'
        + ''.join(sections), encoding='utf-8')
    (output / 'summary.json').write_text(json.dumps(results, indent=2)+'\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('reports/runs/ls20-discovery-mac-m1'))
    build(parser.parse_args().output)
