"""Decision worksheet revision 2: r1 rows adjusted by the licence evidence packs (proposals, never decisions).

  python scripts/wheelhouse_worksheet_r2.py generate
      start from the issued r1 worksheet (checked against its own lock, which stays unchanged), apply the evidence
      packs in reports/wheelhouse_evidence/, and write ..._worksheet_r2.{csv,lock.json,md} plus the r1->r2
      comparison ..._worksheet_r1_to_r2.{json,md}; refuses to overwrite anything.
  python scripts/wheelhouse_worksheet_r2.py carry-forward RETURNED_R1.csv OUT.csv
      copy a returned r1 worksheet's reviewer entries onto a fresh copy of r2 (carried_from = r1). Rows whose
      evidence changed must then be reconfirmed by the reviewer (reviewer_reconfirmed_for_r2 = yes) before
      validation accepts them; unchanged rows keep their entries as made.

Validation and import of either revision: scripts/wheelhouse_decision_worksheet.py (each against its own lock).
"""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import wheelhouse_decision_worksheet as W  # noqa: E402

EVIDENCE = ROOT / 'reports/wheelhouse_evidence'
PACKS = {'cutlass': 'cutlass_binaries.json', 'nvidia': 'nvidia_deployment_assessment.json',
         'notice': 'apache_notice_check.json', 'native': 'native_libraries.json',
         'metadata': 'metadata_discrepancies.json'}
NVIDIA_GENERIC = 'NVIDIA terms: decide whether a private team-only dataset is permitted distribution'
APACHE_GENERIC = 'Apache-2.0 without a NOTICE in the wheel'


def load_packs():
    missing = [name for name in PACKS.values() if not (EVIDENCE / name).exists()]
    if missing:
        raise SystemExit(f'evidence packs missing: {missing}')
    return {key: json.loads((EVIDENCE / name).read_text(encoding='utf-8')) for key, name in PACKS.items()}


def r1_rows():
    lock = json.loads(W.LOCK.read_text(encoding='utf-8'))
    if W.sha256(W.WORKSHEET) != lock['worksheet_sha256']:
        raise SystemExit('the r1 worksheet differs from its lock; r1 must stay exactly as issued')
    return W.read_csv(W.WORKSHEET), lock


def split(text):
    return [x for x in (text or '').split(' | ') if x]


# --- evidence adapters: each returns {artifact: {'obligations_add': [...], 'obligations_drop': [prefix, ...],
#     'evidence': [...]}} -------------------------------------------------------------------------------------------

def merge(target, source):
    for artifact, item in source.items():
        slot = target.setdefault(artifact, {'obligations_add': [], 'obligations_drop': [], 'evidence': []})
        for key in slot:
            slot[key] += item.get(key, [])


def from_nvidia(pack):
    out = {}
    for product in pack['products']:
        out[product['artifact']] = {
            'obligations_drop': [NVIDIA_GENERIC],
            'obligations_add': ['shared NVIDIA deployment assessment applies; owner deployment inputs are outstanding '
                                '(account, recipients, access controls, publication intent)']
                               + [f'product question: {q}' for q in product['questions']],
            'evidence': ['nvidia_deployment_assessment.md: product-specific findings']}
    return out


def from_cutlass(pack):
    finding = pack['finding']['conclusion']
    return {w['artifact']: {'obligations_drop': [NVIDIA_GENERIC],
                            'obligations_add': [f'CUTLASS question: {q}' for q in pack['finding']['questions_for_reviewer']],
                            'evidence': [f'cutlass_binaries.md: {finding} (scoped; see pack)']}
            for w in pack['wheels']}


def own_nvidia_licence(rows):
    out = {}
    for r in rows:
        if r['distribution'] in ('cuda_python', 'cuda_bindings'):
            out[r['artifact']] = {
                'obligations_drop': [NVIDIA_GENERIC],
                'obligations_add': ['own NVIDIA Software License (not the CUDA Toolkit EULA): distribution terms '
                                    'consistent with it; notify NVIDIA of known non-compliance'],
                'evidence': ['worksheet r2: the CUDA Toolkit stand-alone/application question does not apply to this '
                             'licence (r1 flagged it in error)']}
    return out


def from_notice(pack):
    import re
    out = {}
    for r in pack['rows']:
        add = []
        if r['outcome'] == 'found':
            add.append('Apache NOTICE found upstream for this release: ' + r['remains'].split('; also ship')[0])
        elif r['outcome'] == 'inconclusive':
            add.append(f"Apache NOTICE status inconclusive: {r['reason']}")
        vendored = re.search(r'third-party directories carried in the sdist \(([^)]*)\)', r['remains'])
        if vendored:
            add.append(f'vendored components ({vendored.group(1)}) carry their own licence terms, not yet checked; '
                       'their licence texts may need to ship')
        out[r['artifact']] = {'obligations_drop': [APACHE_GENERIC], 'obligations_add': add,
                              'evidence': [f"apache_notice_check.md: {r['outcome']}"
                                           + (' (the "confirm no upstream NOTICE" question is dropped; shipping the '
                                              'licence texts and keeping attribution notices still apply)'
                                              if r['outcome'] == 'verified_absent' else '')]}
    return out


def from_native(pack):
    out = {}
    for w in pack['wheels']:
        add = []
        for c in w['components']:
            name = c['component'].split(' (')[0]
            missing = '; '.join(c['missing_links']) or 'none listed'
            if c['copyleft_as_built']:
                add.append(f"copyleft as built: {name} {c['claimed_upstream_version']} ({c['copyleft_as_built']}): "
                           f"corresponding source and instructions required; provenance chain {c['chain_status']} "
                           f"(missing: {missing})")
            if c['dual_licence_with_gpl_option']:
                add.append(f"dual licence with a GPL option: {name} ({c['dual_licence_with_gpl_option']}): record the "
                           'option relied on')
            if not c['named_in_wheel_notice']:
                add.append(f"notice gap: {name} has no section in the wheel's third-party notice")
        counts = Counter(c['chain_status'] for c in w['components'])
        out[w['artifact']] = {
            'obligations_add': add,
            'evidence': [f"native_libraries.md: {len(w['components'])} bundled components traced "
                         f"({', '.join(f'{v} {k}' for k, v in sorted(counts.items()))}); no source checksum pinned "
                         'by the build, so no chain is complete']}
    return out


def from_metadata(pack):
    out = {}
    for w in pack['wheels']:
        component = w['component'].get('name') or w['component'].get('licence', '')
        out[w['wheel']['artifact']] = {
            'obligations_add': [f"declared-licence discrepancy {w['classification']}: {w['extra_declared_licence']} "
                                f"traced to a shipped component; proposed: {w['proposed_obligation']}"],
            'evidence': [f"metadata_discrepancies.md: {w['classification']} ({component})"]}
    return out


def r2_rows():
    rows, lock = r1_rows()
    packs = load_packs()
    adjustments = {}
    for source in (from_nvidia(packs['nvidia']), from_cutlass(packs['cutlass']), own_nvidia_licence(rows),
                   from_notice(packs['notice']), from_native(packs['native']), from_metadata(packs['metadata'])):
        merge(adjustments, source)
    out = []
    for r in rows:
        row = {k: r[k] for k in W.CONTEXT}
        adj = adjustments.get(r['artifact'], {'obligations_add': [], 'obligations_drop': [], 'evidence': []})
        kept = [o for o in split(r['additional_obligations'])
                if not any(o.startswith(prefix) for prefix in adj['obligations_drop'])]
        obligations = kept + [o for o in adj['obligations_add'] if o not in kept]
        row['additional_obligations'] = ' | '.join(obligations)
        rank, label = retier(row, obligations)
        row.update(tier=str(rank), priority=label, worksheet_revision='r2',
                   evidence_checks=' | '.join(dict.fromkeys(adj['evidence'])))
        row.update({k: '' for k in list(W.REVIEWER) + W.CARRY})
        out.append(row)
    order = {d: i for i, d in enumerate(W.PRIORITY)}
    out.sort(key=lambda x: (int(x['tier']), order.get(x['distribution'], 99), x['artifact']))
    return out, rows, lock, packs


def retier(row, obligations):
    if row['distribution'] in W.PRIORITY:
        return 1, 'priority NVIDIA'
    if row['proposed_disposition'] != 'approved_with_conditions':
        return 2, 'qualified review'
    if any(not o.startswith('ship the upstream') for o in obligations):
        return 3, 'conditional, with additional obligations'
    return 4, 'conditional'


def comparison(r1, r2):
    by_artifact = {r['artifact']: r for r in r1}
    rows = []
    for new in r2:
        old = by_artifact[new['artifact']]
        changed = [f for f in W.CONTEXT if str(old.get(f, '')) != str(new.get(f, ''))]
        if new['evidence_checks']:
            changed.append('evidence_checks')
        before, after = split(old['additional_obligations']), split(new['additional_obligations'])
        rows.append({'artifact': new['artifact'], 'changed_fields': changed,
                     'tier': [old['priority'], new['priority']],
                     'obligations_removed': [o for o in before if o not in after],
                     'obligations_added': [o for o in after if o not in before],
                     'new_evidence': split(new['evidence_checks'])})
    return rows


def write_exclusive(path, data):
    with Path(path).open('x', encoding='utf-8', newline='') as stream:
        stream.write(data)


def csv_text(rows, columns):
    import io
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def generate():
    for path in (W.WORKSHEET_R2, W.LOCK_R2, W.GUIDE_R2, W.COMPARISON_JSON, W.COMPARISON_MD):
        if path.exists():
            raise SystemExit(f'{path.relative_to(ROOT)} exists; a worksheet revision is never overwritten')
    rows, r1, r1_lock, packs = r2_rows()
    compared = comparison(r1, rows)
    write_exclusive(W.WORKSHEET_R2, csv_text(rows, W.COLUMNS_R2))
    lock = {'schema': 'wheelhouse_decision_worksheet_v2', 'revision': 2, 'worksheet_sha256': W.sha256(W.WORKSHEET_R2),
            'parent': {'revision': 1, 'worksheet_sha256': r1_lock['worksheet_sha256'],
                       'lock_sha256': W.sha256(W.LOCK)},
            'inventory_sha256': W.sha256(W.INVENTORY_CSV), 'decisions_sha256_at_generation': W.sha256(W.DECISIONS_CSV),
            'evidence_packs': {name: W.sha256(EVIDENCE / name) for name in PACKS.values()},
            'rows': len(rows), 'tiers': dict(Counter(r['priority'] for r in rows)),
            'context_sha256': {r['artifact']: W.row_digest(r, W.CONTEXT_R2) for r in rows}}
    write_exclusive(W.LOCK_R2, json.dumps(lock, indent=1) + '\n')
    summary = {'schema': 'wheelhouse_worksheet_comparison_v1', 'from': 'r1', 'to': 'r2',
               'r1_worksheet_sha256': r1_lock['worksheet_sha256'], 'r2_worksheet_sha256': lock['worksheet_sha256'],
               'rows_changed': sum(bool(c['changed_fields']) for c in compared),
               'tier_moves': dict(Counter(f'{a} -> {b}' for a, b in (c['tier'] for c in compared) if a != b)),
               'rows': compared}
    write_exclusive(W.COMPARISON_JSON, json.dumps(summary, indent=1) + '\n')
    write_exclusive(W.COMPARISON_MD, comparison_markdown(summary))
    write_exclusive(W.GUIDE_R2, guide(rows, lock, summary))
    return lock, summary


def comparison_markdown(summary):
    lines = ['# Decision worksheet r1 -> r2: changed evidence and obligations', '',
             '**Proposals, not decisions.** Any reviewer entry made on r1 keeps its r1 meaning. Where a row changed, '
             'the entry must be reconfirmed against r2 before it is relied on.', '',
             f"- Rows changed: {summary['rows_changed']} of {len(summary['rows'])}",
             f"- Tier moves: {summary['tier_moves'] or 'none'}", '',
             '| Artifact | Tier (r1 → r2) | Obligations removed | Obligations added | New evidence |',
             '|---|---|---|---|---|']
    for c in summary['rows']:
        if not c['changed_fields']:
            continue
        tier = c['tier'][0] if c['tier'][0] == c['tier'][1] else f"{c['tier'][0]} → {c['tier'][1]}"
        lines.append(f"| `{c['artifact']}` | {tier} | {W.cell('; '.join(c['obligations_removed']))} | "
                     f"{W.cell('; '.join(c['obligations_added']))} | {W.cell('; '.join(c['new_evidence']))} |")
    return '\n'.join(lines) + '\n'


def guide(rows, lock, summary):
    tiers = Counter(r['priority'] for r in rows)
    return '\n'.join([
        '# Redistribution decision worksheet r2: instructions for the designated reviewer', '',
        f"`{W.WORKSHEET_R2.relative_to(ROOT).as_posix()}` (sha256 `{lock['worksheet_sha256'][:12]}…`) revises r1 with "
        'the evidence packs in `reports/wheelhouse_evidence/`. r1 stays valid under its own lock.', '',
        '**Nothing in this worksheet is a decision.** The proposals and evidence are prepared for you.', '',
        '## What changed from r1', '',
        f"{summary['rows_changed']} rows changed; see `{W.COMPARISON_MD.relative_to(ROOT).as_posix()}`.", '',
        '## Order', '', '| Tier | Rows |', '|---|---|',
        *[f'| {name} | {tiers.get(name, 0)} |' for name in ('priority NVIDIA', 'qualified review',
                                                           'conditional, with additional obligations', 'conditional')],
        '', '## Filling in', '',
        'The reviewer columns are the same as in r1 (see the r1 guide). Two columns are new:', '',
        '| Column | Content |', '|---|---|',
        '| `carried_from` | Set by the carry-forward tool when an r1 entry is copied here; do not edit |',
        '| `reviewer_reconfirmed_for_r2` | `yes` only after you have reconfirmed a carried entry against the r2 evidence. Required wherever the row changed. |',
        '', '## If you already filled in r1', '',
        '- Return r1 as it is: it is validated against r1, and each entry on a changed row is flagged.',
        '- Or ask for your r1 entries to be carried onto r2, then reconfirm the changed rows.',
        '', 'Old entries never silently take on a new meaning.', ''])


def carry_forward(returned_r1, out):
    returned = W.read_csv(returned_r1)
    if not returned or W.revision_of(returned[0]) != 1:
        raise SystemExit('carry-forward takes a returned r1 worksheet')
    r1_lock = json.loads(W.LOCK.read_text(encoding='utf-8'))
    inventory = {r['artifact']: r['sha256'] for r in W.read_csv(W.INVENTORY_CSV)}
    entries = {}
    for r in returned:
        if r['sha256'] != inventory.get(r['artifact']) or r['artifact'] not in r1_lock['context_sha256']:
            raise SystemExit(f"{r['artifact']}: not bound to the r1 inventory")
        if any(r[k].strip() for k in W.REVIEWER):
            entries[r['artifact']] = {k: r[k] for k in W.REVIEWER}
    rows = W.read_csv(W.WORKSHEET_R2)
    changed = W.evidence_changes()
    for row in rows:
        if row['artifact'] in entries:
            row.update(entries[row['artifact']], carried_from='r1', reviewer_reconfirmed_for_r2='')
    write_exclusive(out, csv_text(rows, W.COLUMNS_R2))
    needs = sorted(a for a in entries if a in changed)
    return {'carried': len(entries), 'require_reconfirmation': needs}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['generate', 'carry-forward'])
    parser.add_argument('paths', nargs='*', type=Path)
    args = parser.parse_args()
    if args.command == 'generate':
        lock, summary = generate()
        print(json.dumps({'rows': lock['rows'], 'tiers': lock['tiers'], 'rows_changed': summary['rows_changed'],
                          'tier_moves': summary['tier_moves']}, indent=1))
        return 0
    if len(args.paths) != 2:
        parser.error('carry-forward RETURNED_R1.csv OUT.csv')
    print(json.dumps(carry_forward(*args.paths), indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
