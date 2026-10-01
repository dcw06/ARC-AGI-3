"""Local, scripted study tables for reports/evidence_memory_v1_design.md (no model, no network, CPU only).

    python -m research.evidence_memory_v1.study

Prints markdown tables: (1) writer fidelity per scripted writer, ungated and gated; (2) reader evaluation with a
known-correct memory; (3) context pressure (oracle information availability by delay). Every number is from
scripted outputs on development-partition synthetic trajectories: it validates the instruments, not a model.
"""
import collections
import json

from research.evidence_memory_v1 import fidelity as F, readers as RD, trajectories as TR, writers as W

DELAYS = (0, 3, 8)
PRESSURE_DELAYS = (0, 2, 4, 6, 8, 12, 16)


def writer_table(trajectories):
    rows = []
    for name, cls in W.WRITERS.items():
        for gate in (False, True):
            c = collections.Counter()
            for t in trajectories:
                run = W.run_writer(cls(), t, gate=gate)
                rep = F.evaluate(t['records'], run['memory'], t['evaluator_only']['expected'])
                c['trajectories'] += 1
                c['faithful'] += rep['faithful']
                c['facts_required'] += rep['facts']['required']
                c['facts_retained'] += rep['facts']['retained']
                c['counterexamples_required'] += rep['counterexamples']['required']
                c['counterexamples_missing'] += len(rep['counterexamples']['missing'])
                c['contradicted_still_live'] += len(rep['revision']['still_live'])
                c['mechanisms_lost'] += len(rep['required_live']['lost'])
                for key in ('unsupported', 'scope_violations', 'overclaims', 'ignored_counterexamples',
                            'stale_state_dependent'):
                    c[key] += len(rep[key])
                c['entries'] += rep['size']['entries']
                c['chars'] += rep['size']['chars']
                c['operations'] += rep['update_cost']['operations']
                c['writer_calls'] += run['charge']['writer_calls']
                c['writer_input_chars'] += run['charge']['input_chars']
                c['invalid_outputs'] += sum(r['kind'] == 'invalid_output' for r in run['log'])
                c['rejected_operations'] += sum(r['kind'] == 'rejected_operation' for r in run['log'])
            rows.append({'writer': name, 'gate': gate, **c})
    return rows


def reader_table(trajectories):
    rows = []
    for budgeted in (False, True):
        for name, make in RD.READERS.items():
            c = collections.Counter()
            for t in trajectories:
                memory = W.run_writer(W.Faithful(), t)['memory']
                entries = RD.packages(t, memory)['memory']['entries'] if budgeted else [
                    e for e in memory['entries'] if e['status'] != 'retired']
                for a in RD.ask(t, make(entries)):
                    c['questions'] += 1
                    c['correct'] += a['correct']
                    c['invalid'] += not a['valid']
                    c[a['kind'] + '_questions'] += 1
                    c[a['kind'] + '_correct'] += a['correct']
            rows.append({'reader': name, 'memory': 'budgeted' if budgeted else 'unbounded', **c})
    return rows


def composite_table(trajectories):
    """Writer -> oracle reader on the unbounded memory: how writer faults reach answers."""
    rows = []
    for name, cls in W.WRITERS.items():
        c = collections.Counter()
        for t in trajectories:
            memory = W.run_writer(cls(), t)['memory']
            for a in RD.ask(t, RD.oracle_memory([e for e in memory['entries'] if e['status'] != 'retired'])):
                c['questions'] += 1
                c['correct'] += a['correct']
        rows.append({'writer': name, **c})
    return rows


def pressure_table(rows):
    by = collections.defaultdict(list)
    for r in rows:
        by[r['delay']].append(r)
    out = []
    for delay, rs in sorted(by.items()):
        mean = lambda k: round(sum(r[k] for r in rs) / len(rs), 3)
        out.append({'delay': delay, 'trajectories': len(rs), 'all_relevant_in_window': mean('relevant_in_window'),
                    **{k: mean(k) for k in ('full_history', 'recent_raw', 'state_keyed_raw', 'memory',
                                            'memory_unbounded', 'budget_chars', 'memory_unbounded_chars')}})
    return out


def markdown(rows):
    keys = list(rows[0])
    lines = ['| ' + ' | '.join(keys) + ' |', '|' + '---|' * len(keys)]
    lines += ['| ' + ' | '.join(str(r.get(k, 0)) for k in keys) + ' |' for r in rows]
    return '\n'.join(lines)


def main():
    trajectories = TR.generate(delays=DELAYS, count=2)
    pressure_rows = RD.pressure(delays=PRESSURE_DELAYS, count=2)
    early = [r for r in pressure_rows if r['family'] == 'early_crucial']
    print('trajectory digest:', TR.digest(trajectories), f'({len(trajectories)} trajectories)')
    for title, rows in (('Writers', writer_table(trajectories)), ('Readers (known-correct memory)', reader_table(trajectories)),
                        ('Writer to oracle reader', composite_table(trajectories)),
                        ('Context pressure, all families', pressure_table(pressure_rows)),
                        ('Context pressure, early_crucial', pressure_table(early))):
        print(f'\n### {title}\n')
        print(markdown(rows))
    return pressure_rows


if __name__ == '__main__':
    json.dumps(main())
