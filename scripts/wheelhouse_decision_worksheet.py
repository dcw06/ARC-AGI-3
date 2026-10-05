"""Redistribution decision worksheet for the designated reviewer (separate from the authoritative decisions file).

  python scripts/wheelhouse_decision_worksheet.py generate
      write reports/wheelhouse_redistribution_decision_worksheet.csv (+ .lock.json, + guide .md) from the current
      inventory, proposals and NVIDIA reconciliation; refuses to overwrite an existing worksheet. Reviewer columns
      are blank: nothing is prefilled.
  python scripts/wheelhouse_decision_worksheet.py validate RETURNED.csv
      accepts any revision (r1, or later ones from scripts/wheelhouse_worksheet_revision.py), each against its own
      lock and context; refuses entries on rows whose evidence changed in a later revision, requires reconfirmation
      of carried entries on rows that changed since their source revision, and flags recorded decisions on changed
      rows. Then: check the returned worksheet (artifact bindings, required fields, recorded conditions, conflicts with existing
      decisions) and write the proposed changes to reports/wheelhouse_decision_import_preview.{json,md}. Never
      writes the decisions file.
  python scripts/wheelhouse_decision_worksheet.py import RETURNED.csv --preview-sha256 SHA
      only after the owner has seen and confirmed that exact preview: re-validates, requires the same preview hash
      and no errors, and writes the decisions file. Never replaces a recorded (non-unresolved) decision.
"""
import argparse
import csv
import hashlib
import io
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.plan_wheelhouse_r2_bundle import (ALLOWED_DECISIONS, DECISION_FIELDS, DECISIONS_CSV,  # noqa: E402
                                               INVENTORY_CSV, bundle_eligibility, check_decisions, current_evidence,
                                               evidence_digest, read_decisions, split_conditions, valid_date)

PROPOSALS_CSV = ROOT / 'reports/wheelhouse_redistribution_proposed_dispositions.csv'
RECONCILIATION = ROOT / 'reports/wheelhouse_nvidia_licence_reconciliation.json'
WORKSHEET = ROOT / 'reports/wheelhouse_redistribution_decision_worksheet.csv'
LOCK = ROOT / 'reports/wheelhouse_redistribution_decision_worksheet.lock.json'
GUIDE = ROOT / 'reports/wheelhouse_redistribution_decision_worksheet.md'
PREVIEW_JSON = ROOT / 'reports/wheelhouse_decision_import_preview.json'
PREVIEW_MD = ROOT / 'reports/wheelhouse_decision_import_preview.md'
PRIORITY = ('nvidia_cufile_cu12', 'nvidia_nvjitlink_cu12', 'nvidia_nvshmem_cu12', 'nvidia_cutlass_dsl_libs_base')
# reviewer column -> decisions-file column
REVIEWER = {'reviewer_decision': 'redistribution_decision', 'reviewer_rationale': 'rationale',
            'reviewer_required_notices': 'required_notices', 'reviewer_conditions': 'conditions',
            'reviewer_conditions_satisfied': 'conditions_satisfied',
            'reviewer_resolved_questions': 'resolved_questions', 'reviewer_name': 'resolver',
            'reviewer_date': 'decided_on'}
CONTEXT = ['priority', 'tier', 'artifact', 'sha256', 'distribution', 'version', 'flags', 'proposed_disposition',
           'proposed_conditions', 'additional_obligations', 'evidence', 'proposal_rationale', 'unresolved_questions',
           'alternative_if_not_cleared']
COLUMNS = CONTEXT + list(REVIEWER)
# Revisions >= 2 share r2's context (two more context columns) plus carry-forward bookkeeping. Every revision keeps its
# own files and lock; a returned worksheet is validated against the lock and context of its own revision.
CONTEXT_R2 = CONTEXT + ['worksheet_revision', 'evidence_checks']


def reconfirm_column(n):
    return f'reviewer_reconfirmed_for_r{n}'


def revision_files(n):
    if n == 1:
        return {'csv': WORKSHEET, 'lock': LOCK, 'guide': GUIDE}
    stem = f'reports/wheelhouse_redistribution_decision_worksheet_r{n}'
    return {'csv': ROOT / f'{stem}.csv', 'lock': ROOT / f'{stem}.lock.json', 'guide': ROOT / f'{stem}.md'}


def comparison_files(n):
    """The comparison from revision n-1 to revision n."""
    stem = f'reports/wheelhouse_redistribution_worksheet_r{n - 1}_to_r{n}'
    return {'json': ROOT / f'{stem}.json', 'md': ROOT / f'{stem}.md'}


def columns(n):
    return COLUMNS if n == 1 else CONTEXT_R2 + list(REVIEWER) + ['carried_from', reconfirm_column(n)]


def revisions():
    """{n: files, context and columns} for every revision whose lock exists (r1, r2, ... without gaps)."""
    out, n = {}, 1
    while revision_files(n)['lock'].exists():
        out[n] = dict(revision_files(n), context=CONTEXT if n == 1 else CONTEXT_R2, columns=columns(n))
        n += 1
    return out


def latest_revision():
    return max(revisions(), default=1)


# r2 names, kept for callers that refer to the second revision directly
WORKSHEET_R2, LOCK_R2, GUIDE_R2 = (revision_files(2)[k] for k in ('csv', 'lock', 'guide'))
COMPARISON_JSON, COMPARISON_MD = comparison_files(2)['json'], comparison_files(2)['md']
CARRY = ['carried_from', reconfirm_column(2)]
COLUMNS_R2 = columns(2)


def revision_of(row):
    """r1 worksheets have no worksheet_revision column; later revisions name themselves."""
    if 'worksheet_revision' not in row:
        return 1
    value = row['worksheet_revision'].strip().lower()
    if not value.startswith('r') or not value[1:].isdigit() or int(value[1:]) not in revisions():
        raise ValueError(f'unknown worksheet revision {value!r}')
    return int(value[1:])


def evidence_changes(since=1, until=None):
    """artifact -> fields (labelled by revision) changed in any revision after `since`, up to `until` (default: the
    latest). Fails closed: every consecutive comparison in that range must exist and be bound to the locked hashes of
    both of its worksheets."""
    revs = revisions()
    until = max(revs, default=1) if until is None else until
    changed = {}
    for n in range(since + 1, until + 1):
        path = comparison_files(n)['json']
        if not path.exists():
            raise ValueError(f'worksheet r{n} exists but the r{n - 1}->r{n} comparison is missing; entries made on '
                             'earlier revisions cannot be assessed')
        comparison = json.loads(path.read_text(encoding='utf-8'))
        before = json.loads(revs[n - 1]['lock'].read_text(encoding='utf-8'))['worksheet_sha256']
        after = json.loads(revs[n]['lock'].read_text(encoding='utf-8'))['worksheet_sha256']
        if (comparison.get(f'r{n - 1}_worksheet_sha256') != before
                or comparison.get(f'r{n}_worksheet_sha256') != after):
            raise ValueError(f'the r{n - 1}->r{n} comparison is not bound to the current r{n - 1} and r{n} worksheets')
        for c in comparison['rows']:
            if c['changed_fields']:
                changed.setdefault(c['artifact'], []).extend(f'{f} (r{n})' for f in c['changed_fields'])
    return changed


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def obligations(row, proposal, recon_row):
    """Obligations beyond shipping the wheel's own licence files that the decision must address."""
    found = []
    conditions = proposal['proposed_conditions']
    if proposal['proposed_disposition'] in ('needs_qualified_review', 'likely_not_distributable'):
        found.append('QUALIFIED REVIEW REQUIRED before any decision')
    if row['distribution'] in PRIORITY:
        found.append('PRIORITY: NVIDIA applicability/grant question (see the reconciliation report)')
    if proposal['group'].startswith(('NVIDIA', 'NVSHMEM')) or row['distribution'] in ('cuda_python', 'cuda_bindings'):
        found.append('NVIDIA terms: decide whether a private team-only dataset is permitted distribution (not '
                     'stand-alone); private access is not clearance')
    if recon_row:
        unnamed = [Path(f['member']).name for f in recon_row['library_files'] if not f['in_official_attachment_a']]
        if unnamed and recon_row['primary_source'] == 'cuda-12.8.1-eula':
            found.append('library files not named in the official Attachment A: ' + ', '.join(unnamed))
    lowered = conditions.lower()
    if 'source code form' in lowered or 'corresponding source' in lowered or 'point to the pypi sdist' in lowered \
            or 'source of etc/roots.pem' in lowered:
        found.append('source availability: README/NOTICES must state where the source is available (or ship it)')
    if 'notice' in lowered and 'apache' in lowered:
        found.append('Apache-2.0 4(d): ship the NOTICE file')
    if 'upstream' in lowered:
        found.append('ship the upstream licence text(s) from LICENSES/<wheel>/UPSTREAM/ with their recorded source')
    if 'dataset description' in lowered:
        found.append('dataset description must state the governing NVIDIA licence')
    if 'dual-licensed' in lowered or 'option of each' in lowered:
        found.append('record which licence option of each dual-licensed bundled library is relied on')
    if 'apache-2.0 with no notice file' in proposal['questions_for_reviewer'].lower():
        found.append('Apache-2.0 without a NOTICE in the wheel: confirm no upstream NOTICE must accompany it')
    return found


def tier(row, proposal, extra):
    if row['distribution'] in PRIORITY:
        return 1, 'priority NVIDIA'
    if proposal['proposed_disposition'] != 'approved_with_conditions':
        return 2, 'qualified review'
    if any(not x.startswith('ship the upstream') for x in extra):
        return 3, 'conditional, with additional obligations'
    return 4, 'conditional'


def worksheet_rows():
    inventory = read_csv(INVENTORY_CSV)
    proposals = {p['artifact']: p for p in read_csv(PROPOSALS_CSV)}
    recon = {w['artifact']: w for w in json.loads(RECONCILIATION.read_text(encoding='utf-8'))['wheels']}
    if set(proposals) != {r['artifact'] for r in inventory}:
        raise SystemExit('proposals do not cover exactly the inventory')
    rows = []
    for r in inventory:
        p = proposals[r['artifact']]
        if p['sha256'] != r['sha256']:
            raise SystemExit(f"stale proposal for {r['artifact']}")
        extra = obligations(r, p, recon.get(r['artifact']))
        rank, label = tier(r, p, extra)
        rows.append({'tier': rank, 'priority': label, 'artifact': r['artifact'], 'sha256': r['sha256'],
                     'distribution': r['distribution'], 'version': r['version'], 'flags': r['flags'],
                     'proposed_disposition': p['proposed_disposition'], 'proposed_conditions': p['proposed_conditions'],
                     'additional_obligations': ' | '.join(extra), 'evidence': p['evidence'],
                     'proposal_rationale': p['rationale'], 'unresolved_questions': p['questions_for_reviewer'],
                     'alternative_if_not_cleared': p['alternative_if_not_cleared'],
                     **{k: '' for k in REVIEWER}})
    order = {d: i for i, d in enumerate(PRIORITY)}
    rows.sort(key=lambda x: (x['tier'], order.get(x['distribution'], 99), x['artifact']))
    return rows


def generate():
    for path in (WORKSHEET, LOCK, GUIDE):
        if path.exists():
            raise SystemExit(f'{path.relative_to(ROOT)} exists; a worksheet is never overwritten')
    rows = worksheet_rows()
    with WORKSHEET.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    lock = {'schema': 'wheelhouse_decision_worksheet_v1', 'worksheet_sha256': sha256(WORKSHEET),
            'inventory_sha256': sha256(INVENTORY_CSV), 'proposals_sha256': sha256(PROPOSALS_CSV),
            'reconciliation_sha256': sha256(RECONCILIATION), 'decisions_sha256_at_generation': sha256(DECISIONS_CSV),
            'rows': len(rows), 'tiers': dict(Counter(r['priority'] for r in rows)),
            'context_sha256': {r['artifact']: row_digest(r) for r in rows}}
    with LOCK.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(lock, indent=1) + '\n')
    with GUIDE.open('x', encoding='utf-8') as stream:
        stream.write(guide(rows, lock))
    return lock


def row_digest(row, context=None):
    context = CONTEXT if context is None else context
    return hashlib.sha256(json.dumps([str(row.get(k, '')) for k in context], ensure_ascii=False).encode()).hexdigest()


def guide(rows, lock):
    tiers = Counter(r['priority'] for r in rows)
    lines = ['# Redistribution decision worksheet: instructions for the designated reviewer', '',
             f"`{WORKSHEET.relative_to(ROOT).as_posix()}` has {len(rows)} rows, one per artifact in the approved R2 "
             'manifest (sha256 `' + lock['worksheet_sha256'][:12] + '…`).', '',
             '**This worksheet is not the decisions file, and nothing in it is a decision yet.**',
             '- The `proposed_*` columns are proposals prepared for you. They are not approvals.',
             '- Every reviewer column is blank.',
             '- Do not edit the context columns; validation reports any change to them.', '',
             '## Order', '',
             '| Tier | Rows | Meaning |', '|---|---|---|',
             f"| 1 | {tiers.get('priority NVIDIA', 0)} | Priority NVIDIA artifacts (cuFile, nvJitLink, NVSHMEM, CUTLASS DSL binaries). Applicability or grant is unresolved; qualified review or NVIDIA clarification is needed. |",
             f"| 2 | {tiers.get('qualified review', 0)} | Other rows that need qualified review |",
             f"| 3 | {tiers.get('conditional, with additional obligations', 0)} | Conditional candidates with obligations beyond shipping the licence files (see `additional_obligations`) |",
             f"| 4 | {tiers.get('conditional', 0)} | Conditional candidates |", '',
             '## Filling in a row', '',
             'Fill in a row only when you have decided it. A row left with a blank `reviewer_decision` stays '
             '`unresolved`.', '',
             '| Column | Content |', '|---|---|',
             '| `reviewer_decision` | One of `approved`, `approved_with_conditions`, `restricted`, `excluded`, `unresolved` |',
             '| `reviewer_rationale` | Required for any decision other than `unresolved` |',
             '| `reviewer_required_notices` | The notices that must ship with the artifact |',
             '| `reviewer_conditions` | Required for `approved_with_conditions`: each condition, separated by ` \\| ` |',
             '| `reviewer_conditions_satisfied` | One entry per condition, in the same order, separated by ` \\| `: how and where each was satisfied. The build stays blocked until every condition has an entry. |',
             '| `reviewer_resolved_questions` | Which unresolved questions you resolved, and how |',
             '| `reviewer_name` | The reviewer |',
             '| `reviewer_date` | ISO date (YYYY-MM-DD) |', '',
             '## How decisions affect the build', '',
             '`restricted` and `excluded` block the bundle. Every artifact is a required dependency, so nothing is '
             'silently omitted. An artifact that cannot be cleared needs an explicit alternative, which is the '
             "owner's decision.", '',
             '## Return', '',
             'Return the CSV as it is. Before anything is imported, it is validated for artifact bindings, required '
             'fields, recorded conditions and conflicts with existing decisions. The owner is then shown the proposed '
             'changes, and the import happens only after the owner confirms that exact preview.', '']
    return '\n'.join(lines)


def validate(path):
    """(preview, errors) for a returned worksheet of any revision, against that revision's own lock and context;
    writes nothing."""
    inventory = {r['artifact']: r['sha256'] for r in read_csv(INVENTORY_CSV)}
    current = {d['artifact']: d for d in read_decisions(DECISIONS_CSV)}
    errors, warnings, changes = [], [], []
    try:
        returned = read_csv(path)
        revision = revision_of(returned[0]) if returned else 1
    except (OSError, csv.Error, UnicodeDecodeError, ValueError) as exc:
        return None, [f'unreadable worksheet: {exc}']
    spec = revisions()[revision]
    if not spec['lock'].exists():
        return None, [f'no lock for worksheet revision r{revision}']
    lock = json.loads(spec['lock'].read_text(encoding='utf-8'))
    if not returned or set(spec['columns']) - set(returned[0]):
        return None, [f"missing columns for r{revision}: "
                      f"{sorted(set(spec['columns']) - set(returned[0] if returned else {}))}"]
    try:
        if any(revision_of(r) != revision for r in returned):
            return None, ['rows from different worksheet revisions are mixed']
    except ValueError as exc:
        return None, [str(exc)]
    if sha256(INVENTORY_CSV) != lock['inventory_sha256']:
        errors.append('the inventory changed since the worksheet was generated; regenerate it')
    latest = latest_revision()
    try:
        changed_evidence = evidence_changes(revision)  # changes after this worksheet's revision
        carried_changes = {}
        latest_seen, evidence_now = current_evidence()
        if sha256(spec['csv']) != lock['worksheet_sha256']:
            raise ValueError(f'the issued r{revision} worksheet differs from its lock')
        issued = {r['artifact']: r for r in read_csv(spec['csv'])}
    except (OSError, ValueError, KeyError) as exc:
        return None, [f'cannot assess revision changes: {exc}']
    stale = []
    for name, old in current.items():
        if old.get('redistribution_decision') not in (None, 'unresolved') and \
                old.get('evidence_sha256') != evidence_now.get(name):
            stale.append(name)
            warnings.append(f"{name}: the recorded decision ({old['redistribution_decision']}) was not made on the "
                            f"current evidence ({old.get('worksheet_revision') or 'no recorded worksheet revision'}); "
                            f'it does not count toward eligibility until it is reconfirmed on r{latest_seen}')
    seen = Counter(r['artifact'] for r in returned)
    errors += [f'duplicate row for {a}' for a, n in seen.items() if n > 1]
    errors += [f'row for an artifact not in the inventory: {a}' for a in seen if a not in inventory]
    errors += [f'no row for {a}' for a in inventory if a not in seen]
    proposed = {a: dict(d) for a, d in current.items()}
    for r in returned:
        name = r['artifact']
        if name not in inventory:
            continue
        if r['sha256'] != inventory[name]:
            errors.append(f'{name}: SHA-256 does not match the inventory (artifact binding)')
            continue
        if row_digest(r, spec['context']) != lock['context_sha256'].get(name):
            warnings.append(f'{name}: context columns were edited (proposal text is not authoritative; ignored)')
        decision = r['reviewer_decision'].strip()
        if not decision:
            if any(r[k].strip() for k in REVIEWER):
                errors.append(f'{name}: reviewer fields filled but reviewer_decision is blank')
            continue
        if decision not in ALLOWED_DECISIONS:
            errors.append(f'{name}: decision {decision!r} is not one of {sorted(ALLOWED_DECISIONS)}')
            continue
        row = {'artifact': name, 'sha256': inventory[name],
               **{target: r[source].strip() for source, target in REVIEWER.items()},
               # provenance from the issued worksheet row, never from the returned copy
               'worksheet_revision': f'r{revision}', 'evidence_sha256': evidence_digest(issued[name])}
        affected = changed_evidence.get(name, [])
        if affected and decision != 'unresolved':
            # The decisions file keeps no revision or reconfirmation status, so an entry on a row whose evidence
            # changed in a later revision would be imported (and could count toward eligibility) without the
            # reconfirmation the later revision requires: refused.
            errors.append(f"{name}: decided on r{revision} evidence, which changed later ({', '.join(affected)}); not "
                          f'importable from r{revision}: carry it forward to r{latest} and reconfirm it there, or '
                          f'decide it on r{latest}')
            continue
        if revision >= 2:
            carried = r.get('carried_from', '').strip().lower()
            source = int(carried[1:]) if carried[1:].isdigit() and carried.startswith('r') else None
            if carried and (source is None or not 1 <= source < revision):
                errors.append(f'{name}: carried_from {carried!r} is not an earlier revision')
            elif source is not None:
                if source not in carried_changes:
                    carried_changes[source] = evidence_changes(source, revision)
                moved = carried_changes[source].get(name, [])
                if moved and r.get(reconfirm_column(revision), '').strip().lower() != 'yes':
                    errors.append(f"{name}: entry carried from r{source} but the evidence changed "
                                  f"({', '.join(moved)}); set {reconfirm_column(revision)} to yes only after "
                                  f'reconfirming against r{revision}')
        if decision != 'unresolved':
            for source in ('reviewer_rationale', 'reviewer_name'):
                if not r[source].strip():
                    errors.append(f'{name}: {source} is required for {decision}')
            if not valid_date(r['reviewer_date']):
                errors.append(f"{name}: reviewer_date {r['reviewer_date']!r} is not an ISO date")
        conditions, satisfied = split_conditions(row['conditions']), split_conditions(row['conditions_satisfied'])
        if decision == 'approved' and conditions:
            errors.append(f'{name}: approved with conditions listed; use approved_with_conditions')
        if decision == 'approved_with_conditions':
            if not conditions or not all(conditions):
                errors.append(f'{name}: approved_with_conditions needs at least one recorded condition')
            elif len(satisfied) > len(conditions):
                errors.append(f'{name}: more satisfaction entries ({len(satisfied)}) than conditions ({len(conditions)})')
            elif len(satisfied) < len(conditions) or not all(satisfied):
                warnings.append(f'{name}: {len(conditions)} condition(s), {len([s for s in satisfied if s])} documented '
                                'as satisfied: recorded, but the build stays blocked until all are')
        if decision in ('restricted', 'excluded'):
            warnings.append(f'{name}: {decision} blocks the bundle (a required dependency); an explicit alternative is '
                            "the owner's decision")
        old = current.get(name, {})
        replaces_stale = name in stale and row['evidence_sha256'] == evidence_now.get(name)
        if old.get('redistribution_decision') not in (None, 'unresolved') and not replaces_stale and \
                any(old.get(k, '') != row[k] for k in DECISION_FIELDS):
            errors.append(f"{name}: would replace a recorded decision ({old['redistribution_decision']}) made on the "
                          'current evidence; not allowed by import')
            continue
        if any(old.get(k, '') != row[k] for k in DECISION_FIELDS):
            changes.append({'artifact': name, 'from': old.get('redistribution_decision'), 'to': decision,
                            'reviewer': row['resolver'], 'date': row['decided_on'],
                            'conditions': len(conditions), 'satisfied': len([s for s in satisfied if s]),
                            # the complete decision rows, so the owner reviews exactly what would be imported
                            'before': {k: old.get(k, '') for k in DECISION_FIELDS},
                            'after': {k: row[k] for k in DECISION_FIELDS},
                            'worksheet_revision': revision,
                            'affected_by_newer_evidence': affected,
                            'carried_from': r.get('carried_from', '').strip() if revision >= 2 else '',
                            'replaces_stale_decision': replaces_stale})
            proposed[name] = row
    resulting = [proposed[a] for a in inventory]
    errors += [f'resulting decisions: {p}' for p in check_decisions(read_csv(INVENTORY_CSV), resulting)]
    blockers = bundle_eligibility(read_csv(INVENTORY_CSV), resulting, evidence_now)
    preview = {'schema': 'wheelhouse_decision_import_preview_v1', 'worksheet': str(path),
               'worksheet_revision': revision, 'worksheet_lock_sha256': sha256(spec['lock']),
               'latest_revision': latest_seen, 'stale_recorded_decisions': stale,
               'worksheet_sha256': sha256(path), 'decisions_sha256_now': sha256(DECISIONS_CSV),
               'errors': errors, 'warnings': warnings, 'changes': changes,
               'counts_after': dict(Counter(d['redistribution_decision'] for d in resulting)),
               'build_eligible_after': not blockers, 'build_blockers_after': len(blockers),
               'resulting_decisions_sha256': hashlib.sha256(decisions_bytes(resulting)).hexdigest()}
    return (preview, resulting), errors


def decisions_bytes(rows):
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=DECISION_FIELDS, lineterminator='\n')
    writer.writeheader()
    writer.writerows({k: r.get(k, '') for k in DECISION_FIELDS} for r in rows)
    return buffer.getvalue().encode('utf-8')


def cell(value):
    """A Markdown table cell showing the value exactly (pipes and newlines escaped; empty shown as an em dash)."""
    text = str(value)
    return text.replace('\\', '\\\\').replace('|', '\\|').replace('\r', '').replace('\n', '<br>') if text else '—'


def write_preview(preview):
    data = (json.dumps(preview, indent=1) + '\n').encode()
    PREVIEW_JSON.write_bytes(data)
    lines = ['# Proposed decision import: preview (not imported)', '',
             f"Worksheet `{preview['worksheet']}` (sha256 `{preview['worksheet_sha256'][:12]}…`) against decisions "
             f"file `{preview['decisions_sha256_now'][:12]}…`.", '',
             f"- Errors: {len(preview['errors'])} (any error blocks import)",
             f"- Warnings: {len(preview['warnings'])}",
             f"- Rows that would change: {len(preview['changes'])}",
             f"- Counts after import: {preview['counts_after']}",
             f"- Build eligible after import: {preview['build_eligible_after']} "
             f"({preview['build_blockers_after']} blockers)", '']
    for title, items in (('Errors', preview['errors']), ('Warnings', preview['warnings'])):
        if items:
            lines += [f'## {title}', ''] + [f'- {x}' for x in items] + ['']
    if preview['changes']:
        lines += ['## Changes', '', '| Artifact | From | To | Reviewer | Date | Conditions satisfied |',
                  '|---|---|---|---|---|---|']
        lines += [f"| `{c['artifact']}` | {c['from']} | {c['to']} | {c['reviewer']} | {c['date']} | "
                  f"{c['satisfied']}/{c['conditions']} |" for c in preview['changes']]
        lines += ['', '## Complete decision fields (every field that would be imported)', '']
        for c in preview['changes']:
            lines += [f"### `{c['artifact']}`", '', '| Field | Before | After |', '|---|---|---|']
            for field in DECISION_FIELDS:
                before, after = c['before'].get(field, ''), c['after'].get(field, '')
                mark = ' **(changed)**' if before != after else ''
                lines.append(f'| `{field}`{mark} | {cell(before)} | {cell(after)} |')
            conditions = split_conditions(c['after'].get('conditions'))
            satisfied = split_conditions(c['after'].get('conditions_satisfied'))
            if conditions:
                lines += ['', 'Conditions and how each was satisfied:', '']
                lines += [f"{i}. {condition} — satisfied: {satisfied[i - 1] if i <= len(satisfied) and satisfied[i - 1] else '**not documented**'}"
                          for i, condition in enumerate(conditions, 1)]
            lines.append('')
    lines += ['', f"Import requires `--preview-sha256 {hashlib.sha256(data).hexdigest()}` and no errors.", '']
    PREVIEW_MD.write_text('\n'.join(lines), encoding='utf-8')
    return hashlib.sha256(data).hexdigest()


def do_import(path, preview_sha):
    result, errors = validate(path)
    if result is None or errors:
        raise SystemExit('import refused: validation errors (see the preview)')
    preview, resulting = result
    data = (json.dumps(preview, indent=1) + '\n').encode()
    if hashlib.sha256(data).hexdigest() != preview_sha or not PREVIEW_JSON.exists() or \
            PREVIEW_JSON.read_bytes() != data:
        raise SystemExit('import refused: the confirmed preview does not match the current validation')
    temporary = DECISIONS_CSV.with_name(DECISIONS_CSV.name + '.importing')
    with temporary.open('xb') as stream:
        stream.write(decisions_bytes(resulting))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, DECISIONS_CSV)
    return preview


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['generate', 'validate', 'import'])
    parser.add_argument('worksheet', nargs='?', type=Path)
    parser.add_argument('--preview-sha256')
    args = parser.parse_args()
    if args.command == 'generate':
        lock = generate()
        print(json.dumps({k: lock[k] for k in ('rows', 'tiers', 'worksheet_sha256')}, indent=1))
        return 0
    if args.worksheet is None:
        parser.error('a returned worksheet path is required')
    if args.command == 'validate':
        result, errors = validate(args.worksheet)
        if result is None:
            print('\n'.join(errors))
            return 1
        digest = write_preview(result[0])
        print(json.dumps({'errors': len(errors), 'warnings': len(result[0]['warnings']),
                          'changes': len(result[0]['changes']), 'preview_sha256': digest}, indent=1))
        return 1 if errors else 0
    if not args.preview_sha256:
        parser.error('import requires --preview-sha256 of the preview the owner confirmed')
    preview = do_import(args.worksheet, args.preview_sha256)
    print(f"imported {len(preview['changes'])} change(s)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
