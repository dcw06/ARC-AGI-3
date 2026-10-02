"""Evidence-linked memory v1 (Track 2): the transition_evidence_v2 format migration changes no byte.

PRE_MIGRATION_SHA256 was computed by `snapshot()` at commit a77d0d3 (records from transition_evidence_v1,
before the migration). It covers, for the study's 42 trajectories: every writer prompt of every scripted writer
(gate on and off), the final memory text, memory JSON, log and charges; the per-record level; the rendered
recent_raw / state_keyed_raw / memory / full-history packages of the 98 context-pressure trajectories; and the full
study output (writer, agreement incl. 886 mutations, reader, composite and pressure tables, trajectory digest).
Slow (about a minute): it reruns the study.
"""
import contextlib
import hashlib
import io
import json
import unittest

from research.evidence_memory_v1 import readers as RD, render as R, schema as S, study, trajectories as TR, \
    writers as W

PRE_MIGRATION_SHA256 = '35c8a848462b6c15e4dd2bc68fa7e83969082ff2a24c9a18220e4b3b4720607b'


def _prompts(cls, t, gate):
    idx = S.index(t['records'])
    inner, seen_prompts = cls(), []

    def writer(seen, view):
        seen_prompts.append(R.record_line(seen[-1], idx[S.record_key(seen[-1])]) + '\n' + R.memory_text(view['entries']))
        return inner(seen, view)
    writer.name = inner.name
    return seen_prompts, W.run_writer(writer, t, gate=gate)


def snapshot():
    out = {'writer_prompts': [], 'memory_text': [], 'packages': [], 'levels': []}
    for t in TR.generate(delays=study.DELAYS, count=2):
        idx = S.index(t['records'])
        out['levels'].append([[S.record_key(r), idx[S.record_key(r)]['level']] for r in t['records']])
        for name, cls in W.WRITERS.items():
            for gate in (False, True):
                prompts, run = _prompts(cls, t, gate)
                out['writer_prompts'].append([t['id'], name, gate, prompts])
                out['memory_text'].append([t['id'], name, gate, R.memory_text(run['memory']['entries']),
                                           json.dumps(run['memory'], sort_keys=True),
                                           json.dumps(run['log'], sort_keys=True), run['charge']])
    for delay in study.PRESSURE_DELAYS:
        for family in TR.FAMILIES:
            for i in range(2):
                t = TR.build(family, i, delay)
                idx = S.index(t['records'])
                p = RD.packages(t, W.run_writer(W.Faithful(), t)['memory'])
                out['packages'].append([t['id'], R.records_text(p['recent_raw']['records'], idx),
                                        R.records_text(p['state_keyed_raw']['records'], idx),
                                        R.memory_text(p['memory']['entries']), R.records_text(t['records'], idx)])
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        study.main()
    out['study'] = buffer.getvalue()
    return hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest()


class FormatMigration(unittest.TestCase):
    def test_prompts_memory_packages_and_tables_are_byte_identical(self):
        self.assertEqual(snapshot(), PRE_MIGRATION_SHA256)


if __name__ == '__main__':
    unittest.main()
