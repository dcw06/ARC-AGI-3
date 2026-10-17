"""Visible first-frame coordinates for the nine originally requested games.

No game source inspection, action execution, player journals, or semantic oracle.
Named groups are visual descriptions; same-colour components are not object IDs.
python -m human_play.level1_inventory [--check]
"""
from __future__ import annotations

import argparse
from collections import deque
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

from .server import ROOT, DEFAULT_GAMES, GAMES, PALETTE, engine, observation

OUT = ROOT / 'human_play/static/level1-inventory'
COLOR_NAMES = ('白', '浅灰', '中灰', '灰', '深灰', '黑', '品红', '浅粉', '红', '蓝', '浅蓝', '黄', '橙', '暗红', '绿', '紫')
RAW_TEAMMATE_EXAMPLE = '''Coordinates (preserved as written; coordinate-pair notation not normalized):
White cross: (21, 31), (20, 32), (21, 32), (22, 32), (21,33).
Target object: (33,39) to (9,15).
Pattern: (3,8) to (55,60).
Pattern in the target object: (35, 37) (11, 13).'''


def dump(value):
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)+'\n').encode()


def digest(value):
    return hashlib.sha256(json.dumps(value, separators=(',', ':')).encode()).hexdigest()


def cells_of(frame, points):
    width = len(frame[0])
    return [{'x': x, 'y': y, 'row': y, 'column': x, 'index': y*width+x, 'color_index': frame[y][x]}
            for x, y in sorted(points, key=lambda p: (p[1], p[0]))]


def bounds_of(cells):
    return {'x_min': min(c['x'] for c in cells), 'x_max': max(c['x'] for c in cells),
            'y_min': min(c['y'] for c in cells), 'y_max': max(c['y'] for c in cells)}


def components(frame):
    """Exhaustive 4-neighbour partition. Connectivity is not semantic identity."""
    height, width = len(frame), len(frame[0])
    seen, out = set(), []
    for y in range(height):
        for x in range(width):
            if (x, y) in seen:
                continue
            color, queue, points = frame[y][x], deque([(x, y)]), []
            seen.add((x, y))
            while queue:
                a, b = queue.popleft()
                points.append((a, b))
                for c, d in ((a+1, b), (a-1, b), (a, b+1), (a, b-1)):
                    if 0 <= c < width and 0 <= d < height and (c, d) not in seen and frame[d][c] == color:
                        seen.add((c, d))
                        queue.append((c, d))
            cells = cells_of(frame, points)
            out.append({'component_id': f'cc{len(out)+1:03}', 'color_index': color,
                        'bounds_inclusive': bounds_of(cells), 'cell_count': len(cells), 'cells': cells,
                        'meaning': 'same-colour 4-connected region, not a verified game object'})
    return out


def visual_groups(code, frame):
    out = []

    def add(name, bounds, colors=None, kind='visual_pattern', parent=None):
        x0, y0, x1, y1 = bounds
        points = [(x, y) for y in range(y0, y1+1) for x in range(x0, x1+1)
                  if colors is None or frame[y][x] in colors]
        if not points:
            raise ValueError(f'{code}: empty selection: {name}')
        cells = cells_of(frame, points)
        box = bounds_of(cells)
        oid = f'{code}-o{len(out)+1:03}'
        out.append({'object_id': oid, 'name': name, 'kind': kind, 'parent_id': parent,
                    'role_status': 'visual_description_only; functional role not tested in this inventory',
                    'bounds_inclusive': box, 'color_indices': sorted({c['color_index'] for c in cells}),
                    'cell_count': len(cells), 'cells': cells,
                    'coordinate_text': f"x=({box['x_min']},{box['x_max']}), y=({box['y_min']},{box['y_max']})",
                    'selector': {'bounds_inclusive': list(bounds), 'colors': colors}})
        return oid

    if code == 'ar25':
        a=add('左上黑色 L 形整体（含白点）',(18,15,26,23),[5,0])
        add('左上 L 形内五个白点',(18,15,26,23),[0],parent=a)
        add('右上深灰 L 形',(36,15,44,23),[4])
        add('右下黄色 L 形',(51,45,59,53),[11])
        add('中间浅蓝竖带',(30,0,32,62),[10],'interface_or_divider')
        add('右缘黄色竖条',(63,0,63,63),[11],'interface_or_border')
        add('底部黑色横条',(0,63,62,63),[5],'interface_or_border')
    elif code == 'g50t':
        a=add('上方蓝色方块（含黑色中心）',(14,8,18,12))
        add('上方蓝色方块的黑色中心点',(16,10,16,10),[5],parent=a)
        a=add('右下蓝黑图案框',(43,49,49,55))
        add('右下框内蓝色图案及孤立点',(43,49,49,55),[9],parent=a)
        add('红色折线与两端图形整体',(14,9,41,42),[8],'connected_visual_group')
        add('主区黑色像素结构（含图案中的黑色）',(13,7,50,56),[5],'board_structure')
        add('左上蓝色界面图标',(1,1,3,5),[9],'interface_candidate')
        add('左上浅灰小块',(5,1,7,3),[1],'interface_candidate')
        add('底部蓝色横条',(0,63,63,63),[9],'interface_or_border')
    elif code == 'lf52':
        add('L 形棋盘白色底面',(10,11,51,52),[0],'board_background')
        add('L 形棋盘黑色边框',(9,10,52,53),[5],'board_border')
        add('棋盘外侧蓝色边缘',(10,11,53,54),[9],'border_or_shadow')
        for row, y in enumerate((12,18,24,30,36,42,48),1):
            xs=(11,17,23,29,35,41,47) if row <= 3 else (35,41,47)
            for x in xs:
                col=(x-11)//6+1
                green=any(frame[yy][xx]==14 for yy in range(y,y+4) for xx in range(x,x+4))
                a=add(f'棋盘 R{row}C{col} '+('绿色十字格' if green else '浅灰格'),(x,y,x+3,y+3),[1,14],'board_cell')
                if green:
                    add(f'R{row}C{col} 内绿色十字（不含四角）',(x,y,x+3,y+3),[14],parent=a)
        add('顶部白色横条',(0,0,63,0),[0],'interface_or_border')
    elif code == 'sk48':
        add('主区品红空心方块',(11,36,16,41),[0,6])
        add('左侧灰色分段竖条',(13,14,14,35),[2,3],'segmented_visual_group')
        add('主区右向灰色连接带',(16,38,22,39),[1,2],'connector')
        for name,color,y in (('红色方块',8,19),('蓝色方块',9,25),('绿色方块',14,31)):
            add('主区'+name,(42,y,45,y+3),[color])
        add('主区深灰底板',(17,12,46,41),[4],'board_background')
        add('底部品红空心图标',(20,56,25,61),[0,6],'interface_candidate')
        for name,color,x in (('红色',8,27),('绿色',14,33),('蓝色',9,39)):
            add('底部'+name+'小方块',(x,57,x+3,60),[color],'interface_candidate')
        add('底部灰色连接带',(25,58,43,59),[1,2],'connector')
        add('底部浅灰分隔线',(0,53,63,53),[2],'interface_or_divider')
    elif code == 'sp80':
        add('上方深灰小块',(36,1,39,3),[4])
        add('深灰块下方品红小块',(36,4,39,7),[6])
        add('蓝色长方形',(12,16,31,19),[9])
        add('左下黄色 U 形',(16,52,27,59),[11])
        add('右下黄色 U 形',(40,52,51,59),[11])
        add('顶部绿色横条',(0,0,63,0),[14],'interface_or_border')
        add('底部浅灰横带',(0,60,63,63),[1],'interface_or_border')
    elif code == 'su15':
        a=add('右上蓝色近圆形（含灰色内部像素）',(44,11,52,19),[9,3])
        add('近圆形内部灰色 3×3 小块',(47,14,49,16),[3],parent=a)
        add('斜向灰色点列（不含圆形内 3×3 块）',(6,17,46,57),[3],'dotted_visual_group')
        add('白色十字',(9,52,11,54),[0])
        add('左下紫色小块',(3,58,5,60),[15])
        add('顶部紫色小块',(30,4,32,6),[15],'interface_candidate')
        add('顶部深灰带',(0,0,63,9),[4],'interface_background')
        add('底部白色横条',(0,63,63,63),[0],'interface_or_border')
    elif code == 'tr87':
        for row,y in enumerate((4,13,22),1):
            for pair,bx,px in ((1,12,22),(2,35,45)):
                for label,x,color in (('浅蓝',bx,10),('粉色',px,7)):
                    a=add(f'上部 R{row} 配对{pair} {label}图案框',(x,y,x+6,y+6),[color,5],'pattern_tile')
                    add(f'上部 R{row} 配对{pair} {label}框内黑色图案',(x+1,y+1,x+5,y+5),[5],parent=a)
                add(f'上部 R{row} 配对{pair} 灰色连接线',(bx+7,y+3,px-1,y+3),[3],'connector')
        for label,y,color in (('浅蓝',40,10),('粉色',51,7)):
            a=add(f'下部{label}整行图案带',(14,y,48,y+6),[color,5],'sequence_group')
            for k,x in enumerate((14,21,28,35,42),1):
                b=add(f'下部{label}第{k}个图案格',(x,y,x+6,y+6),[color,5],'pattern_tile',a)
                add(f'下部{label}第{k}个格内黑色图案',(x+1,y+1,x+5,y+5),[5],parent=b)
        add('浅蓝图案带下白色指示形',(15,48,19,49),[0],'interface_candidate')
        add('粉色图案带下白色指示形',(15,59,19,60),[0],'interface_candidate')
        add('底部浅灰横条',(0,63,63,63),[1],'interface_or_border')
    elif code == 'vc33':
        add('右上蓝色方块（画面内可见区域）',(60,24,63,27),[9])
        add('右侧下方蓝色方块（画面内可见区域）',(60,32,63,35),[9])
        add('中间左段黑色横条',(20,28,37,31),[5])
        add('中间黄色竖条',(38,28,39,31),[11])
        add('中间右段黑色横条',(40,28,63,31),[5])
        add('下方深灰缺口形',(46,44,49,49),[4])
        add('下方黄色竖条',(50,44,51,49),[11])
        add('右上白色区域（扣除蓝块）',(32,1,63,27),[0],'board_region')
        add('右下白色区域（扣除蓝块）',(52,32,63,63),[0],'board_region')
        add('顶部粉色横条',(0,0,63,0),[7],'interface_or_border')
    elif code == 'wa30':
        for label,b in (('右上',(44,24,47,27)),('左侧',(16,28,19,31)),('下方',(32,36,35,39))):
            a=add(label+'蓝心深灰小方块',b,[4,9])
            add(label+'小方块内蓝色 2×2 图案',b,[9],parent=a)
        a=add('中间蓝边灰心长方形',(28,28,39,31),[9,2])
        add('中间长方形蓝色边框',(28,28,39,31),[9],parent=a)
        add('中间长方形灰色内部',(29,29,38,30),[2],parent=a)
        a=add('下方白绿方块',(32,48,35,51),[0,14])
        add('白绿方块的白色顶边',(32,48,35,48),[0],parent=a)
        add('白绿方块的绿色部分',(32,49,35,51),[14],parent=a)
        add('底部粉色横条',(0,63,63,63),[7],'interface_or_border')
    else:
        raise ValueError(code)
    return out


def build(check=False):
    arc = engine(DEFAULT_GAMES, ROOT/'.cache/human-play/inventory-sdk')
    files, games = {}, []
    for code in GAMES[:9]:
        env = arc.make(code, seed=0, save_recording=False)
        if env is None:
            raise ValueError(f'missing offline environment: {code}')
        obs = observation(env.observation_space)
        frame = obs['frames'][-1]
        groups = visual_groups(code, frame)
        info = env.environment_info
        source = Path(info.local_dir)/(info.class_name.lower()+'.py')
        entry = {'game_id': info.game_id, 'short_id': code, 'seed': 0, 'level_display': 1,
                 'levels_completed': obs['levels_completed'], 'observation_scope': 'last frame returned by initial reset, before any play action',
                 'coordinate_convention': 'zero based; x=column; y=row; frame[y][x]; flat index=y*width+x; inclusive bounds',
                 'coordinate_text_origin': 'newly derived from visible matrix; not quoted teammate notation',
                 'width': len(frame[0]), 'height': len(frame), 'frame_sha256': digest(frame),
                 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'initial_observation': obs,
                 'objects': groups, 'components': components(frame),
                 'limitations': ['visual labels do not establish mechanics or persistent identities',
                                 'parent groups and child patterns can overlap; not a count of unique physical objects',
                                 'a bounding box is not an occupied-cell mask; use cells for exact coordinates']}
        validate(entry)
        games.append(entry)
        files[f'{code}.json'] = dump(entry)
    index = {'title': '九个游戏第一关初始画面坐标', 'method': 'visible matrices only, no actions or hidden-rule source inspection',
             'coordinate_convention': games[0]['coordinate_convention'],
             'teammate_ls20_example_preserved_verbatim': RAW_TEAMMATE_EXAMPLE,
             'teammate_example_scope': 'ls20 only, a notation example; not evidence for these nine games',
             'games': [{'game_id': g['game_id'], 'file': g['short_id']+'.json', 'objects': len(g['objects']),
                        'components': len(g['components']), 'frame_sha256': g['frame_sha256']} for g in games]}
    files['index.json'] = dump(index)
    csv_file = io.StringIO(newline='')
    writer = csv.writer(csv_file, lineterminator='\n')
    writer.writerow(['game_id','object_id','object_name','parent_id','x','y','row','column','index','color_index'])
    for g in games:
        for o in g['objects']:
            for c in o['cells']:
                writer.writerow([g['game_id'],o['object_id'],o['name'],o['parent_id'] or '',
                                 c['x'],c['y'],c['row'],c['column'],c['index'],c['color_index']])
    files['all-object-cells.csv'] = ('\ufeff'+csv_file.getvalue()).encode('utf-8')
    md = ['# 九个游戏第一关物体坐标', '',
          '本地官方环境、seed=0、首次 RESET 返回的最后一帧；此时完成关卡数为 0，即第一关。', '',
          '坐标从 0 起算：x 是列，y 是行，矩阵写作 frame[y][x]。范围包含两端。以下文字是新整理的明确坐标，不冒充队友原文。', '',
          '这些是画面中的视觉对象、图案、界面元素及其子图案。功能角色没有在本次清单中通过动作验证。父子对象可能重叠；同色连通域不等于真实游戏物体。', '',
          '每个 JSON 的 objects[].cells 保存精确 x/y、row/column、index 和颜色值。components 是覆盖整个 64×64 画面的同色四邻接划分，保证未命名像素也可检索。CSV 汇总所有命名对象的逐格坐标。', '',
          '范围只是包围盒；精确图案应读 cells。例如一个十字的包围盒是 3×3，但实际只有 5 格。移动后的坐标不在此初始清单范围内。', '']
    for g in games:
        md += [f"## {g['short_id']}", '', f"版本：`{g['game_id']}`。完整格子坐标：[JSON]({g['short_id']}.json)。", '',
               '| ID | 物体或图案 | x 范围 | y 范围 | 实际格数 | 颜色 index | 上级对象 |',
               '| --- | --- | --- | --- | --- | --- | --- |']
        for o in g['objects']:
            b=o['bounds_inclusive']
            md.append(f"| {o['object_id']} | {o['name']} | ({b['x_min']},{b['x_max']}) | ({b['y_min']},{b['y_max']}) | {o['cell_count']} | {', '.join(map(str,o['color_indices']))} | {o['parent_id'] or '—'} |")
        md += ['', '小图案的全部坐标：', '']
        small = [o for o in g['objects'] if o['cell_count'] <= 8]
        md += [f"- {o['name']}："+', '.join(f"({c['x']}, {c['y']})" for c in o['cells']) for o in small] if small else ['本游戏命名图案均超过 8 格，逐格列表见 JSON 或 CSV。']
        md += ['']
    md += ['## 队友提供的 ls20 原文', '', '以下只作为记法参考，原样保留，不用于替代九个游戏的矩阵证据。', '', '```text', RAW_TEAMMATE_EXAMPLE, '```', '']
    files['coordinates.md'] = ('\n'.join(md)).encode()
    files['manifest.json'] = dump({'sha256': {k:hashlib.sha256(v).hexdigest() for k,v in files.items()}})
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as z:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980,1,1,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    files['nine-games-level1-coordinates.zip'] = archive.getvalue()
    if check:
        mismatch=[name for name,data in files.items() if not (OUT/name).is_file() or (OUT/name).read_bytes()!=data]
        if mismatch:
            raise ValueError('inventory differs: '+str(mismatch))
    else:
        OUT.mkdir(parents=True, exist_ok=True)
        for name,data in files.items():
            (OUT/name).write_bytes(data)
    return {'games':len(games), 'named_entries':sum(len(g['objects']) for g in games),
            'component_cells':sum(sum(c['cell_count'] for c in g['components']) for g in games),
            'checked':check, 'output':str(OUT)}


def validate(entry):
    f = entry['initial_observation']['frames'][-1]
    width, height = entry['width'], entry['height']
    if digest(f) != entry['frame_sha256'] or entry['levels_completed'] != 0:
        raise ValueError('not the declared first frame')
    ids={o['object_id'] for o in entry['objects']}
    by_id={o['object_id']:o for o in entry['objects']}
    coverage=[]
    for obj in entry['objects']+entry['components']:
        cells=obj['cells']
        if len(cells)!=obj['cell_count'] or len({(c['x'],c['y']) for c in cells})!=len(cells):
            raise ValueError('missing or duplicate cell')
        if bounds_of(cells)!=obj['bounds_inclusive']:
            raise ValueError('bounds differ from occupied cells')
        if obj.get('parent_id') and obj['parent_id'] not in ids:
            raise ValueError('parent does not resolve')
        if obj.get('parent_id'):
            parent={(c['x'],c['y']) for c in by_id[obj['parent_id']]['cells']}
            if not {(c['x'],c['y']) for c in cells} <= parent:
                raise ValueError('child pattern lies outside parent mask')
        for c in cells:
            if not (0<=c['x']<width and 0<=c['y']<height and c['row']==c['y'] and c['column']==c['x']
                    and c['index']==c['y']*width+c['x'] and c['color_index']==f[c['y']][c['x']]):
                raise ValueError('coordinate/index/value differs from matrix')
    for c in entry['components']:
        coverage.extend((p['x'],p['y']) for p in c['cells'])
    if len(coverage)!=width*height or len(set(coverage))!=width*height:
        raise ValueError('component partition does not cover every pixel exactly once')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    print(json.dumps(build(parser.parse_args().check),ensure_ascii=False))
