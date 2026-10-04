"""Prepare (do not build) the R2 wheelhouse bundle: the artifact-by-artifact redistribution review table and the
proposed bundle contents. No download, installation, upload or GPU use; nothing is copied.

Inputs (all committed): the approved download manifest, the licence evidence index, the metadata closure report and
the retained CPU installation evidence. Outputs:
  reports/wheelhouse_redistribution_inventory.csv  GENERATED, regenerated freely: one row per artifact (identity,
                                                   licence documents, flags, proposed notices, open questions)
  reports/wheelhouse_redistribution_decisions.csv  HUMAN-OWNED: created once (all 'unresolved') if absent and never
                                                   written again by any tool; keyed by artifact and SHA-256
  reports/wheelhouse_r2_bundle_plan.json           every proposed bundle file with its source and (where known) hash
  reports/wheelhouse_r2_bundle_plan.md             the same for review, with the README draft and open decisions
The generator validates the decisions file against the inventory and exits non-zero (without touching it) if any
entry is missing, stale (different SHA-256), unexpected or not an allowed decision value.
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.download_wheelhouse import APPROVED_MANIFEST_SHA256, load_manifest  # noqa: E402

MANIFEST = ROOT / 'reports/wheelhouse_download_manifest.json'
EVIDENCE = ROOT / 'reports/wheelhouse_license_evidence.json'
INSTALL = ROOT / 'reports/wheelhouse_r2_offline_install_check.json'
INVENTORY_CSV = ROOT / 'reports/wheelhouse_redistribution_inventory.csv'
DECISIONS_CSV = ROOT / 'reports/wheelhouse_redistribution_decisions.csv'
EVIDENCE_DIR = ROOT / 'reports/wheelhouse_r2_offline_install_evidence'
DECISION_FIELDS = ['artifact', 'sha256', 'redistribution_decision', 'rationale', 'required_notices',
                   'resolved_questions', 'resolver', 'decided_on']
ALLOWED_DECISIONS = {'unresolved', 'approved', 'approved_with_conditions', 'restricted', 'excluded'}
PLAN_JSON = ROOT / 'reports/wheelhouse_r2_bundle_plan.json'
PLAN_MD = ROOT / 'reports/wheelhouse_r2_bundle_plan.md'
RESOLVER = 'dcw06'
PROPOSED_NAME = 'arc3-vllm-0.19.0-cu128-wheelhouse-r2'
ORIGINAL_NON_WHEEL = ['README.md', 'dataset-metadata.json', 'pip-resolve-report.json', 'requirements.in',
                      'requirements.lock']

QUESTIONS = {
    'proprietary_terms_present': 'Do the proprietary terms (e.g. NVIDIA software licence) permit redistributing this '
                                 'exact wheel in a team-owned Kaggle dataset, and under which conditions and notices?',
    'declared_copyleft': 'The package declares a copyleft licence: confirm the notice and source-availability '
                         'obligations for redistributing the unmodified wheel.',
    'copyleft_terms_present': 'Copyleft text appears in bundled notices: confirm whether it applies to shipped '
                              'components and what notices must accompany the wheel.',
    'no_licence_file_in_wheel': 'The wheel ships no licence file: obtain the upstream licence text to accompany it.',
    'unrecognised_licence_text': 'The licence text was not recognised automatically: read and classify it.',
}


def lock_lines(manifest):
    lines = []
    for a in sorted(manifest['artifacts'], key=lambda a: a['filename']):
        name, version = a['filename'][:-4].split('-')[:2]
        lines.append(f"{name}=={version} --hash=sha256:{a['sha256']}")
    return lines


def review_rows(manifest, evidence):
    by_artifact = {r['artifact']: r for r in evidence['wheels']}
    rows = []
    for a in sorted(manifest['artifacts'], key=lambda a: a['filename']):
        e = by_artifact[a['filename']]
        name, version = a['filename'][:-4].split('-')[:2]
        build = a['filename'][:-4].split('-')[2] if a['filename'].count('-') == 5 else ''
        docs = e['licence_files']
        questions = [QUESTIONS[f] for f in e['flags'] if f in QUESTIONS] or [
            'Confirm the detected permissive licence and include its text and notices with the wheel.']
        rows.append({
            'artifact': a['filename'], 'distribution': name, 'version': version, 'build': build,
            'sha256': a['sha256'], 'size': a['size'], 'upstream_url': a['url'],
            'licence_documents': '; '.join(d['path'] for d in docs) or 'none in wheel',
            'licence_document_sha256': '; '.join(d['sha256'] for d in docs),
            'licence_source': 'bundled in the wheel' if docs else 'upstream (not bundled)',
            'metadata_declared': '; '.join(e['metadata_declared']),
            'detected_families': ', '.join(e['detected_families']),
            'flags': ', '.join(e['flags']),
            'required_notices_proposed': (f"ship LICENSES/{a['filename']}/ with the {len(docs)} bundled document(s)"
                                          if docs else 'obtain and ship the upstream licence text'),
            'open_questions': ' | '.join(questions),
        })
    return rows


README = '''# ARC-AGI-3 offline vLLM runtime wheelhouse — R2

A team-owned, versioned offline wheelhouse for the ARC-AGI-3 model host: vLLM 0.19.0, torch 2.10.0 (runtime build
2.10.0+cu128, CUDA 12.8), transformers 4.57.6, numpy 2.2.6 and their complete dependency closure (174 wheels).

Identity: this is a NEW bundle (R2). Every wheel is byte-identical to an official PyPI artifact (verified by
SHA-256) and to the retained inventory of the earlier bundle, but the earlier bundle's non-wheel files could not be
reproduced, so the bundle as a whole is not byte-identical to any earlier dataset.

Target: CPython 3.12, Linux x86-64, glibc >= 2.34, NVIDIA driver supporting CUDA 12.8 (supplied by the image).

Install (offline, hash-pinned):
    python -m pip install --no-index --no-cache-dir --require-hashes --only-binary=:all: \\
        --find-links <bundle>/wheels -r <bundle>/requirements.lock

Verify first: `sha256sum -c SHA256SUMS` from the bundle root; bundle-manifest.json lists every file.

Evidence: metadata closure complete; wheel bytes verified after download; CPU-only offline installation passed in a
network-isolated environment. GPU startup, inference and cleanup are NOT yet verified by this bundle.

Licences: LICENSES/ holds the licence documents bundled in each wheel; see LICENSES/REVIEW.csv for the
redistribution review of every artifact.
'''


def initial_decisions(rows):
    return [{'artifact': r['artifact'], 'sha256': r['sha256'], 'redistribution_decision': 'unresolved',
             'rationale': '', 'required_notices': '', 'resolved_questions': '', 'resolver': RESOLVER,
             'decided_on': ''} for r in rows]


def read_decisions(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


def check_decisions(rows, decisions):
    """Problems with the human decisions file relative to the generated inventory (empty list if consistent)."""
    expected = {r['artifact']: r['sha256'] for r in rows}
    problems, seen = [], set()
    for d in decisions:
        name = d.get('artifact')
        if name in seen:
            problems.append(f'duplicate decision for {name}')
        seen.add(name)
        if name not in expected:
            problems.append(f'decision for an artifact not in the inventory: {name}')
        elif d.get('sha256') != expected[name]:
            problems.append(f'stale decision for {name}: recorded SHA-256 differs from the inventory')
        if d.get('redistribution_decision') not in ALLOWED_DECISIONS:
            problems.append(f"{name}: decision {d.get('redistribution_decision')!r} is not one of "
                            f"{sorted(ALLOWED_DECISIONS)}")
        if d.get('redistribution_decision') not in (None, 'unresolved') and not (d.get('rationale') or '').strip():
            problems.append(f'{name}: a decision without a rationale')
    problems += [f'no decision row for {name}' for name in sorted(set(expected) - seen)]
    return problems


def file_entry(path, bundle_path, kind, source):
    data = path.read_bytes()
    return {'path': bundle_path, 'kind': kind, 'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'source': source}


def plan(manifest, evidence, install):
    lock = '\n'.join(lock_lines(manifest)) + '\n'
    lock_sha = hashlib.sha256(lock.encode()).hexdigest()
    install_lock_sha = (install.get('evidence') or {}).get('files_sha256', {}).get('requirements.lock')
    files = [{'path': f"wheels/{a['filename']}", 'kind': 'wheel', 'size': a['size'], 'sha256': a['sha256'],
              'source': a['url']} for a in sorted(manifest['artifacts'], key=lambda a: a['filename'])]
    for row in sorted(evidence['wheels'], key=lambda r: r['artifact']):
        for doc in row['licence_files']:
            files.append({'path': f"LICENSES/{row['artifact']}/{doc['path']}", 'kind': 'licence_document',
                          'size': doc['size'], 'sha256': doc['sha256'], 'source': f"extracted from {row['artifact']}"})
    readme = README.encode()
    files += [
        {'path': 'requirements.lock', 'kind': 'generated', 'size': len(lock.encode()), 'sha256': lock_sha,
         'source': 'generated: name==version --hash=sha256 for all 174 artifacts'},
        {'path': 'README.md', 'kind': 'generated', 'size': len(readme), 'sha256': hashlib.sha256(readme).hexdigest(),
         'source': 'generated (draft in this plan)'},
        {'path': 'LICENSES/REVIEW.csv', 'kind': 'generated', 'size': None, 'sha256': None,
         'source': 'inventory joined with the owner decisions file, at build, once every row is decided'},
        file_entry(INSTALL, 'EVIDENCE/offline_install_check.json', 'evidence',
                   'reports/wheelhouse_r2_offline_install_check.json (retained CPU-only installation receipt)'),
    ]
    evidence_folder = ROOT / (install.get('evidence') or {}).get('folder', '')
    for name, digest in sorted(((install.get('evidence') or {}).get('files_sha256') or {}).items()):
        entry = file_entry(evidence_folder / name, f'EVIDENCE/{name}', 'evidence',
                           f'{evidence_folder.relative_to(ROOT)}/{name} (referenced by the receipt)')
        if entry['sha256'] != digest:
            raise SystemExit(f'retained evidence {name} does not match the hash in the installation receipt')
        files.append(entry)
    files += [
        {'path': 'bundle-manifest.json', 'kind': 'checksum', 'size': None, 'sha256': None,
         'source': 'generated at build: size and SHA-256 of every payload file (excludes itself and SHA256SUMS)'},
        {'path': 'SHA256SUMS', 'kind': 'checksum', 'size': None, 'sha256': None,
         'source': 'generated at build: sha256sum lines for every payload file and bundle-manifest.json '
                   '(excludes itself)'},
    ]
    proprietary = sum(1 for r in evidence['wheels'] if 'proprietary_terms_present' in r['flags'])
    return {
        'schema': 'wheelhouse_r2_bundle_plan_v1',
        'status': 'proposal only: nothing built, copied or uploaded',
        'proposed_dataset_name': PROPOSED_NAME, 'proposed_name_needs_owner_decision': True,
        'identity': 'new bundle (R2); wheels byte-identical to official PyPI artifacts; not byte-identical to any '
                    'earlier dataset because the earlier non-wheel files are not reproduced',
        'source_manifest_sha256': manifest['manifest_sha256'],
        'wheel_count': manifest['artifact_count'], 'wheel_bytes': manifest['total_bytes'],
        'licence_documents': sum(len(r['licence_files']) for r in evidence['wheels']),
        'requirements_lock': {'sha256': lock_sha, 'matches_installed_lock': lock_sha == install_lock_sha,
                              'installed_lock_sha256': install_lock_sha},
        'non_wheel_files_of_earlier_bundle': {
            'missing_not_reproduced': ORIGINAL_NON_WHEEL,
            'replaced_by': {'README.md': 'new README.md', 'requirements.lock': 'new hash-pinned requirements.lock',
                            'requirements.in': 'not reproduced; the install pins are documented in README.md',
                            'pip-resolve-report.json': 'not reproduced; replaced by the metadata closure report',
                            'dataset-metadata.json': 'generated by Kaggle at upload'},
        },
        'cpu_installation_evidence': {'report': 'reports/wheelhouse_r2_offline_install_check.json',
                                      'passed': install.get('passed'),
                                      'limitations': install.get('not_established')},
        'checksum_construction': {
            'payload': 'every file except bundle-manifest.json and SHA256SUMS',
            'bundle-manifest.json': 'covers the payload only (never SHA256SUMS, never itself)',
            'SHA256SUMS': 'covers the payload plus the completed bundle-manifest.json (never itself)',
            'approval_binds': 'the SHA-256 of the final SHA256SUMS file',
            'order': ['write payload', 'write bundle-manifest.json over the payload',
                      'write SHA256SUMS over the payload and bundle-manifest.json', 'record sha256(SHA256SUMS)'],
        },
        'upload_blocked_until': [f'every one of the {manifest["artifact_count"]} artifacts has a recorded '
                                 f'redistribution decision ({proprietary} carry proprietary terms)',
                                 'required notices are prepared', 'the dataset name and access are chosen',
                                 'the owner approves this exact bundle for upload'],
        'files': files,
    }


def render(p, rows, decisions_status):
    from collections import Counter
    flags = Counter(f for r in rows for f in r['flags'].split(', ') if f)
    lines = ['# Wheelhouse R2 bundle plan (proposal; nothing built or uploaded)', '',
             f"Proposed team-owned dataset: `{p['proposed_dataset_name']}` (name and access need the owner's decision).",
             f"Identity: {p['identity']}.", '',
             '## Proposed contents', '', '| Part | Files | Notes |', '|---|---|---|',
             f"| `wheels/` | {p['wheel_count']} | {p['wheel_bytes']:,} bytes, SHA-256 and PyPI URL per file |",
             f"| `LICENSES/<artifact>/` | {p['licence_documents']} | licence documents extracted from the wheels, hashed |",
             f"| `requirements.lock` | 1 | hash-pinned, 174 lines; SHA-256 `{p['requirements_lock']['sha256'][:12]}…`, "
             f"{'identical to' if p['requirements_lock']['matches_installed_lock'] else 'DIFFERENT from'} the lock "
             'used by the passing CPU installation |',
             '| `README.md` | 1 | draft below |',
             '| `LICENSES/REVIEW.csv` | 1 | the redistribution review, once every decision is recorded |',
             '| `EVIDENCE/offline_install_check.json` | 1 | retained CPU-only installation evidence and its limits |',
             '| `EVIDENCE/` | 3 | the installation receipt plus the log and lock it references, hash-checked |',
             '| `bundle-manifest.json`, `SHA256SUMS` | 2 | checksum files, built in the order below |', '',
             '## Checksum construction (non-circular)', '',
             '1. `bundle-manifest.json` lists the size and SHA-256 of every payload file; it never covers itself or '
             '`SHA256SUMS`.',
             '2. `SHA256SUMS` covers every payload file plus the completed `bundle-manifest.json`; it never covers '
             'itself.',
             '3. The upload approval binds the SHA-256 of the final `SHA256SUMS`.', '',
             '## Earlier bundle files not reproduced', '']
    for name, replacement in p['non_wheel_files_of_earlier_bundle']['replaced_by'].items():
        lines.append(f'- `{name}`: {replacement}')
    lines += ['', '## Redistribution review status', '',
              f"Decisions file `reports/wheelhouse_redistribution_decisions.csv` (owner-maintained, never overwritten "
              f"by tools): {decisions_status}. Generated prompts are in "
              '`reports/wheelhouse_redistribution_inventory.csv`; they are review prompts, not legal clearance. '
              'Flags to decide:', '']
    lines += [f'- `{f}`: {n}' for f, n in sorted(flags.items())]
    lines += ['', '## Upload is blocked until', '']
    lines += [f'- {item}' for item in p['upload_blocked_until']]
    lines += ['', '## README draft', '', '```', README.rstrip(), '```', '']
    return '\n'.join(lines)


def main():
    manifest = load_manifest(MANIFEST, APPROVED_MANIFEST_SHA256)
    evidence = json.loads(EVIDENCE.read_text(encoding='utf-8'))
    if evidence.get('manifest_sha256') != manifest['manifest_sha256']:
        raise SystemExit('licence evidence is not bound to the approved manifest')
    install = json.loads(INSTALL.read_text(encoding='utf-8'))
    rows = review_rows(manifest, evidence)
    with INVENTORY_CSV.open('w', encoding='utf-8', newline='') as stream:  # generated: safe to regenerate
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    created = False
    if not DECISIONS_CSV.exists():  # created once; never written again by any tool
        with DECISIONS_CSV.open('x', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=DECISION_FIELDS, lineterminator='\n')
            writer.writeheader()
            writer.writerows(initial_decisions(rows))
        created = True
    decisions = read_decisions(DECISIONS_CSV)
    problems = check_decisions(rows, decisions)
    counts = {}
    for d in decisions:
        counts[d.get('redistribution_decision')] = counts.get(d.get('redistribution_decision'), 0) + 1
    status = ('INCONSISTENT: ' + '; '.join(problems[:5])) if problems else ', '.join(
        f'{n} {k}' for k, n in sorted(counts.items()))
    p = plan(manifest, evidence, install)
    p['decisions'] = {'file': str(DECISIONS_CSV.relative_to(ROOT)) if DECISIONS_CSV.is_relative_to(ROOT)
                      else str(DECISIONS_CSV), 'created_now': created, 'counts': counts, 'problems': problems}
    PLAN_JSON.write_text(json.dumps(p, indent=1) + '\n', encoding='utf-8')
    PLAN_MD.write_text(render(p, rows, status), encoding='utf-8')
    print(json.dumps({'inventory_rows': len(rows), 'plan_files': len(p['files']), 'decisions': counts,
                      'decision_problems': len(problems),
                      'lock_matches_installed': p['requirements_lock']['matches_installed_lock']}))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
