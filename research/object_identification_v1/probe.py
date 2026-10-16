"""Image-only inventory probe; no model execution, network access or game actions.

References are partial, hierarchical, owner-reviewed annotations. Matches measure
reference coverage, not exhaustive detection precision or physical collision rules.
"""
from fractions import Fraction
import hashlib
import html
import io
import json
from pathlib import Path
import zipfile

from certification.phase4_multimodal_preflight_v3.images import png, grid_from_png
from scripts.serve_manual_strategy_worksheet import (
    GAMES, canonical, digest, private_directory, validate_regions,
)

MODEL = 'OpenGVLab/InternVL3_5-8B'
MODEL_REVISION = '9bb6a56ad9cc69db95e2d4eeb15a52bbcac4ef79'
ROLES = ('player', 'goal', 'control', 'obstacle_candidate', 'other', 'unknown')
IOU_THRESHOLD = Fraction(1, 2)
MAX_OBJECTS = 96
MAX_OUTPUT_TOKENS = 4096
PROMPT = '''Identify distinct visible objects and terrain regions in this image of a
64-by-64 game board. Include visible wall/barrier candidates, but do not assert
that appearance proves an obstacle blocks movement. No interaction history is
supplied. Do not invent game rules, a solution, or hidden objects.

Use integer board coordinates: x is column, y is row, origin at the top-left;
both range from 0 through 63. Bounding boxes are [left, top, right, bottom],
inclusive, in board cells, not rendered image pixels. The full image represents
the entire 64-by-64 board; report board-cell coordinates regardless of image
resizing. No crop or coordinate overlay is applied. Give separate entries for distinct objects, and optionally their
visually meaningful components; do not duplicate the same region.

Return only one JSON object with the key "objects" containing at most 96 entries.
Each entry must contain exactly: "id" (a unique short string), "description"
(visible appearance), "bbox_xyxy" (four integers), and "role_guess" (one of
"player", "goal", "control", "obstacle_candidate", "other", "unknown").
Use "unknown" when a role is not justified by appearance. Role guesses will be
reported as guesses, not verified mechanics. An empty objects list is allowed.
Do not include markdown, reasoning text, or action commands.'''


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_load(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result

    def nonfinite(_):
        raise ValueError('non-finite JSON number')

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)


def box(value):
    if (type(value) is not list or len(value) != 4
            or any(type(v) is not int or not 0 <= v < 64 for v in value)
            or value[0] > value[2] or value[1] > value[3]):
        raise ValueError('invalid inclusive board-cell bbox')
    return value


def iou(a, b):
    width = max(0, min(a[2], b[2]) - max(a[0], b[0]) + 1)
    height = max(0, min(a[3], b[3]) - max(a[1], b[1]) + 1)
    intersection = width * height
    area_a = (a[2] - a[0] + 1) * (a[3] - a[1] + 1)
    area_b = (b[2] - b[0] + 1) * (b[3] - b[1] + 1)
    return Fraction(intersection, area_a + area_b - intersection)


def parse_prediction(content, finish_reason):
    if finish_reason != 'stop':
        raise ValueError('unfinished or refused model output')
    if type(content) is not str or len(content.encode('utf-8')) > 65536:
        raise ValueError('missing or oversized content')
    value = strict_load(content)
    if type(value) is not dict or set(value) != {'objects'}:
        raise ValueError('expected exactly the objects field')
    objects = value['objects']
    if type(objects) is not list or len(objects) > MAX_OBJECTS:
        raise ValueError('invalid objects list')
    ids = set()
    for obj in objects:
        if type(obj) is not dict or set(obj) != {'id', 'description', 'bbox_xyxy', 'role_guess'}:
            raise ValueError('invalid object fields')
        if (type(obj['id']) is not str or not 1 <= len(obj['id']) <= 80
                or obj['id'] in ids):
            raise ValueError('invalid or duplicate object id')
        ids.add(obj['id'])
        if type(obj['description']) is not str or not 1 <= len(obj['description']) <= 240:
            raise ValueError('invalid description')
        if obj['role_guess'] not in ROLES:
            raise ValueError('invalid role guess')
        box(obj['bbox_xyxy'])
    return objects


def match(references, predictions):
    """Maximum-cardinality bipartite matching at the frozen IoU threshold.

    Edges are visited by decreasing IoU with stable index ties. This optimizes
    number of covered references, not the summed IoU of all possible matchings.
    """
    edges = {
        r: sorted((p for p, pred in enumerate(predictions)
                   if iou(ref['bbox_xyxy'], pred['bbox_xyxy']) >= IOU_THRESHOLD),
                  key=lambda p: (-iou(ref['bbox_xyxy'], predictions[p]['bbox_xyxy']), p))
        for r, ref in enumerate(references)
    }
    owners = {}

    def augment(r, seen):
        for p in edges[r]:
            if p in seen:
                continue
            seen.add(p)
            if p not in owners or augment(owners[p], seen):
                owners[p] = r
                return True
        return False

    for r in range(len(references)):
        augment(r, set())
    return sorted((r, p) for p, r in owners.items())


def score_case(reference, content=None, finish_reason=None):
    error = None
    try:
        predictions = parse_prediction(content, finish_reason)
    except (ValueError, TypeError, KeyError) as exc:
        error = str(exc)
        predictions = []
    results = {}
    # Match whole regions and parts independently; never sum these overlapping
    # strata into an object count or an exhaustive detection score.
    for name, refs in (
        ('whole_regions', [r for r in reference['regions'] if r['parent_id'] is None]),
        ('parts', [r for r in reference['regions'] if r['parent_id'] is not None]),
    ):
        pairs = match(refs, predictions)
        results[name] = {
            'matched': len(pairs), 'reference_count': len(refs),
            'reference_coverage': len(pairs) / len(refs) if refs else None,
            'matches': [{'reference_id': refs[r]['id'], 'prediction_id': predictions[p]['id'],
                         'bbox_iou': float(iou(refs[r]['bbox_xyxy'], predictions[p]['bbox_xyxy'])),
                         'reference_kind': refs[r]['kind']} for r, p in pairs],
            'unmatched_reference_ids': [ref['id'] for r, ref in enumerate(refs)
                                        if r not in {r for r, _ in pairs}],
            'unmatched_prediction_ids_for_review': [pred['id'] for p, pred in enumerate(predictions)
                                                    if p not in {p for _, p in pairs}],
        }
    obstacle_refs = [r for r in reference['regions'] if r['kind'] == 'obstacle']
    obstacle_guesses = [p for p in predictions if p['role_guess'] == 'obstacle_candidate']
    return {
        'case_id': reference['case_id'], 'response_valid': error is None,
        'response_error': error, 'predicted_regions': len(predictions),
        'localization': results,
        'obstacles': {
            'owner_labelled_candidates': len(obstacle_refs),
            'model_candidate_ids': [p['id'] for p in obstacle_guesses],
            'candidate_label_spatial_matches': len(match(obstacle_refs, obstacle_guesses)),
            'movement_blocking_accuracy': None,
            'status': 'not_tested_no_verified_collision_labels_or_action_history',
        },
        'mask_identification': 'not_tested_bounding_boxes_do_not_establish_occupied_cells',
    }


def review_page(prepared, references):
    sections = []
    for item, ref in zip(prepared, references):
        rectangles = ''.join(
            '<rect class="annotation" x="{0}" y="{1}" width="{2}" height="{3}">'
            '<title>{4}</title></rect>'.format(
                r['bbox_xyxy'][0], r['bbox_xyxy'][1],
                r['bbox_xyxy'][2] - r['bbox_xyxy'][0] + 1,
                r['bbox_xyxy'][3] - r['bbox_xyxy'][1] + 1, html.escape(r['label']))
            for r in ref['regions'])
        sections.append(
            '<section><h2>{}</h2><svg viewBox="0 0 64 64"><image width="64" height="64" '
            'href="{}"/>{}</svg><p>{} owner-reviewed regions, including overlapping parts. '
            'Hover a reference box for its label.</p></section>'.format(
                html.escape(ref['source_case_id']), item['image'], rectangles, len(ref['regions'])))
    return ('''<!doctype html><meta charset="utf-8"><title>Private InternVL probe review</title>
<style>body{font:16px system-ui;max-width:1100px;margin:24px auto;background:#171b23;color:#eee}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:24px}
svg{width:100%;image-rendering:pixelated;background:black}
.annotation{fill:none;stroke:#ff7100;stroke-width:.18;display:none;pointer-events:all}
body:has(#show:checked) .annotation{display:block}pre{white-space:pre-wrap}</style>
<h1>Private six-board identification probe</h1>
<p><strong>Prepared only. No InternVL responses, GPU runs or game actions.</strong></p>
<p>The model receives the plain images and inventory prompt, never these reference overlays or labels.
Boxes test coarse localization, not exact masks. Obstacle roles remain unverified.</p>
<label><input type="checkbox" id="show"> Show owner-reviewed reference boxes (not model predictions)</label>
<main>''' + ''.join(sections) + '</main>').encode('utf-8')


def prepare(snapshot, output, runtime_extra=None):
    snapshot, output = Path(snapshot).resolve(), Path(output).resolve()
    if output.exists():
        raise ValueError('output already exists; preserve every earlier preparation')
    manifest = strict_load((snapshot / 'snapshot-manifest.json').read_bytes())
    for name in ('answers.json', 'cases.json', 'provenance.json'):
        raw = (snapshot / name).read_bytes()
        if (sha(raw) != manifest['files'][name]['sha256']
                or len(raw) != manifest['files'][name]['bytes']):
            raise ValueError('snapshot hash/size mismatch: ' + name)
    answers = strict_load((snapshot / 'answers.json').read_bytes())
    cases = strict_load((snapshot / 'cases.json').read_bytes())
    if answers['context_sha256'] != manifest['context_sha256']:
        raise ValueError('snapshot context mismatch')
    prepared, references = [], []
    files = {}
    for index, game in enumerate(GAMES, 1):
        key = game + '.level1'
        case, answer = cases[key], answers['cases'][key]
        frame = case['frames'][0]
        if digest(frame['grid']) != frame['grid_sha256']:
            raise ValueError('frame hash mismatch')
        regions = validate_regions(answer['regions'], case)
        if any(r['frame_index'] != 0 for r in regions):
            raise ValueError('initial-board probe cannot use later-frame annotations')
        image = png(frame['grid'], cell=8)
        if grid_from_png(image, cell=8) != frame['grid']:
            raise ValueError('render round-trip mismatch')
        public_id = f'board-{index:02d}'  # no game name or answer IDs in model input
        image_path = f'inputs/{public_id}.png'
        files[image_path] = image
        prepared.append({'case_id': public_id, 'image': image_path, 'image_sha256': sha(image), 'prompt': PROMPT,
                         'model': MODEL, 'model_revision': MODEL_REVISION,
                         'max_tokens': MAX_OUTPUT_TOKENS, 'temperature': 0,
                         'stream': False})
        references.append({'case_id': public_id, 'source_case_id': key,
                           'grid_sha256': frame['grid_sha256'],
                           'entry_revision': answer['revision'],
                           'qualification': 'owner-reviewed partial hierarchical reference',
                           'regions': regions})
    files['inputs/requests.jsonl'] = b''.join(canonical(row) for row in prepared)
    files['references/answers.json'] = canonical(references)
    files['references/source_binding.json'] = canonical(manifest)
    files['review.html'] = review_page(prepared, references)
    # Only image inputs and prompts belong in a model-facing dataset.
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
        for name in sorted(n for n in files if n.startswith('inputs/')):
            entry = zipfile.ZipInfo(name, date_time=(2026, 10, 15, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            zipped.writestr(entry, files[name])
    files['model-inputs-only.zip'] = archive.getvalue()
    if runtime_extra is not None:
        extra = Path(runtime_extra).resolve()
        wheel_name = 'timm-1.0.20-py3-none-any.whl'
        wheel = (extra/wheel_name).read_bytes()
        expected = 'f6e62f780358476691996c47aa49de87b95cc507edf923c3042f74a07e45b7fe'
        if sha(wheel) != expected:
            raise ValueError('supplemental timm wheel hash mismatch')
        files['runtime-extra/'+wheel_name] = wheel
        files['runtime-extra/requirements-extra.lock'] = Path(__file__).with_name(
            'runtime_requirements_extra.lock').read_bytes()
        files['runtime-extra/acquisition-manifest.json'] = (extra/'manifest.json').read_bytes()
        # The immutable wheel itself retains its licence. Include the inspected
        # text for review without installing or executing this wheel here.
        license_text = (extra/'retained-licenses/LICENSE').read_bytes()
        if sha(license_text) != '71b111620fa32c17a80ccd6db2da759d31a591e497d8b5f382174f59d1b59d49':
            raise ValueError('supplemental timm licence hash mismatch')
        files['runtime-extra/LICENSE'] = license_text
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
            for name in sorted(n for n in files if n.startswith(('inputs/', 'runtime-extra/'))):
                entry = zipfile.ZipInfo(name, date_time=(2026, 10, 15, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                zipped.writestr(entry, files[name])
        files['kaggle-inputs.zip'] = archive.getvalue()
    model_pin = {'repository': MODEL, 'revision': MODEL_REVISION,
                 'source': 'https://huggingface.co/api/models/' + MODEL,
                 'weights_manifest_bound': False, 'runtime_validated': False}
    files['model_pin.json'] = canonical(model_pin)
    files['STATUS.json'] = canonical({
        'status': 'prepared_only_no_model_results', 'planned_model_requests': len(prepared),
        'model_calls': 0, 'game_actions': 0, 'gpu_runs': 0,
        'obstacle_mechanics_testable': False,
        'source_approval': 'not_recorded', 'compute_authorization': 'not_recorded',
    })
    notebook = {
        'nbformat': 4, 'nbformat_minor': 5,
        'metadata': {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'}},
        'cells': [
            {'cell_type': 'markdown', 'id': 'scope', 'metadata': {}, 'source': [
                '# Private InternVL3.5-8B object-localization probe\n',
                'Six independent image-only requests, zero game actions. Review only.\n',
                'The enforced 3,600-second cap must cover mounting, setup and all GPU-job time.\n',
                'No provider enforcement, model dataset or validated runtime is bound yet.\n',
                'This notebook cannot launch inference and is not a competition submission.\n']},
            {'cell_type': 'code', 'id': 'refuse', 'metadata': {}, 'execution_count': None,
             'outputs': [], 'source': [
                 'raise SystemExit("REVIEW ONLY: provider full-job cap, mounted model bytes, '
                 'runtime validation and exact launch authority are not bound. No inference started.")\n']},
            {'cell_type': 'markdown', 'id': 'inputs', 'metadata': {}, 'source': [
                'A future input attachment may contain inputs/ and the separately pinned runtime-extra/ only.\n',
                'Keep references/, review.html and evaluator results outside the model sandbox.\n',
                'A worker timer or notebook timeout field alone is not evidence of the full-job cap.\n',
                'Retain raw completions and exact input bindings; do not repair or retry invalid answers.\n']},
        ],
    }
    files['kaggle-review/profile.ipynb'] = canonical(notebook)
    files['kaggle-review/kernel-metadata.json'] = canonical({
        'id': 'daichongwei06/arc3-internvl-object-identification-v1',
        'title': 'ARC3 InternVL Object Identification V1 Private Review',
        'code_file': 'profile.ipynb', 'language': 'python', 'kernel_type': 'notebook',
        'is_private': True, 'enable_gpu': False, 'enable_tpu': False,
        'enable_internet': False, 'dataset_sources': [], 'model_sources': [],
    })
    files['kaggle-review/readiness.json'] = canonical({
        'status': 'local_review_only_do_not_upload_or_launch',
        'intended_account': 'daichongwei06', 'access': 'account_holder_only',
        'intended_accelerator': 'one NVIDIA RTX PRO 6000',
        'whole_job_cap_seconds': 3600, 'provider_cap_verified': False,
        'model_mount_bound': False, 'input_mount_bound': False, 'runtime_validated': False,
        'supplemental_runtime_wheel_bound': runtime_extra is not None,
        'planned_generation_requests': 6, 'max_output_tokens_per_request': MAX_OUTPUT_TOKENS,
        'automatic_retries': 0, 'game_actions': 0,
        'note': 'The six requests exclude any future separately budgeted runtime canaries or polls.',
    })
    lock = {
        'schema': 'object_identification_probe_v1',
        'model': model_pin, 'case_ids': [r['case_id'] for r in references],
        'reference_qualification': 'partial owner-reviewed labels; not exhaustive ground truth',
        'bbox_iou_threshold': '1/2', 'prompt_sha256': sha(PROMPT.encode()),
        'artifacts': {name: sha(raw) for name, raw in sorted(files.items())},
        'source_sha256': {path.relative_to(Path(__file__).parents[2]).as_posix(): sha(path.read_bytes())
                          for path in (Path(__file__),
                                       Path(__file__).parents[2] / 'scripts/object_identification_v1.py',
                                       Path(__file__).with_name('runtime.py'),
                                       Path(__file__).with_name('runtime_source_pin.json'),
                                       Path(__file__).with_name('runtime_requirements_extra.lock'),
                                       Path(__file__).parents[2] / 'scripts/serve_manual_strategy_worksheet.py',
                                       Path(__file__).parents[2] / 'certification/phase4_multimodal_preflight_v3/images.py')},
    }
    files['review-lock.json'] = canonical(lock)
    private_directory(output)
    for name, raw in files.items():
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return {'output': str(output), 'review_lock_sha256': sha(files['review-lock.json']),
            'cases': len(references), 'reference_regions': sum(len(r['regions']) for r in references),
            'owner_labelled_obstacle_candidates': sum(r['kind'] == 'obstacle'
                                                     for ref in references for r in ref['regions']),
            'model_calls': 0, 'game_actions': 0, 'gpu_runs': 0}


def verify(bundle):
    bundle = Path(bundle).resolve()
    lock = strict_load((bundle / 'review-lock.json').read_bytes())
    if lock['schema'] != 'object_identification_probe_v1':
        raise ValueError('unknown bundle schema')
    for name, expected in lock['artifacts'].items():
        path = (bundle / name).resolve()
        if not path.is_relative_to(bundle) or sha(path.read_bytes()) != expected:
            raise ValueError('bundle artifact mismatch: ' + name)
    root = Path(__file__).resolve().parents[2]
    for name, expected in lock['source_sha256'].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or sha(path.read_bytes()) != expected:
            raise ValueError('evaluating source mismatch: ' + name)
    return lock


def evaluate(bundle, response_path):
    bundle, response_path = Path(bundle).resolve(), Path(response_path).resolve()
    lock = verify(bundle)
    references = strict_load((bundle / 'references/answers.json').read_bytes())
    requests = [strict_load(line) for line in (bundle / 'inputs/requests.jsonl').read_bytes().splitlines()]
    request_hashes = {row['case_id']: sha(canonical(row)) for row in requests}
    raw = response_path.read_bytes()
    rows = [strict_load(line) for line in raw.splitlines() if line.strip()]
    records = {}
    for row in rows:
        if type(row) is not dict or set(row) != {
                'case_id', 'model', 'model_revision', 'request_sha256', 'content', 'finish_reason'}:
            raise ValueError('invalid response record')
        if row['case_id'] not in lock['case_ids'] or row['case_id'] in records:
            raise ValueError('unknown or duplicate case response')
        if row['model'] != MODEL:
            raise ValueError('response model mismatch')
        if row['model_revision'] != MODEL_REVISION:
            raise ValueError('response model revision mismatch')
        if row['request_sha256'] != request_hashes[row['case_id']]:
            raise ValueError('response input binding mismatch')
        records[row['case_id']] = row
    scores = []
    for ref in references:
        row = records.get(ref['case_id'])
        score = score_case(ref, row['content'] if row else None,
                           row['finish_reason'] if row else None)
        score['available'] = row is not None
        scores.append(score)
    return {
        'status': 'recorded_response_evaluation_not_runtime_or_model_provenance_certification',
        'review_lock_sha256': sha((bundle / 'review-lock.json').read_bytes()),
        'responses_sha256': sha(raw), 'planned_cases': len(references),
        'available_responses': len(records), 'valid_responses': sum(s['response_valid'] for s in scores),
        'missing_case_ids': [s['case_id'] for s in scores if not s['available']], 'cases': scores,
        'limitations': [
            'A model name in a response record does not prove which weights produced it.',
            'References are incomplete; unmatched predictions require review, not automatic false-positive labels.',
            'Bounding-box coverage does not establish exact masks, roles, obstacle mechanics or gameplay ability.',
            'Whole-region and part scores overlap and must not be summed into independent detections.',
        ],
    }
