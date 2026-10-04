"""Deterministic regressions for scripts/check_wheelhouse_metadata.py (no network: a mocked opener stands in)."""
import gzip
import hashlib
import json
import re
import socket
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from scripts import check_wheelhouse_metadata as W

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def metadata(name, version, requires=(), requires_python=None, extras=(), license=None):
    lines = ['Metadata-Version: 2.1', f'Name: {name}', f'Version: {version}']
    if requires_python:
        lines.append(f'Requires-Python: {requires_python}')
    if license:
        lines.append(f'License: {license}')
    lines += [f'Provides-Extra: {e}' for e in extras]
    lines += [f'Requires-Dist: {r}' for r in requires]
    return '\n'.join(lines) + '\n\nlong description\n'


class FakeResponse:
    def __init__(self, status, body, headers=None):
        self.status, self._body, self._pos = status, body, 0
        self.headers = {'Content-Length': str(len(body)), **(headers or {})}

    def read(self, n=-1):
        end = len(self._body) if n < 0 else self._pos + n
        chunk, self._pos = self._body[self._pos:end], min(end, len(self._body))
        return chunk

    read1 = read

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeOpener:
    """Maps URL -> response factory; records every request."""

    def __init__(self, routes):
        self.routes, self.seen = routes, []

    def open(self, request, timeout=None):
        url = request.full_url
        self.seen.append(url)
        route = self.routes.get(url)
        if route is None:
            raise urllib.error.HTTPError(url, 404, 'not found', {}, None)
        return route() if callable(route) else route


def wheel(name, version, tag='py3-none-any', build=None):
    middle = f'{version}-{build}' if build else version
    return f'{name}-{middle}-{tag}.whl'


def index(name, files):
    return json.dumps({'name': name, 'files': files}).encode()


class Network(unittest.TestCase):
    def setUp(self):
        self.filename = wheel('demo', '1.0')
        self.body = b'wheel bytes never fetched'
        self.meta = metadata('demo', '1.0').encode()
        self.wheel_url = f'https://files.pythonhosted.org/packages/aa/{self.filename}'
        self.entry = {'filename': self.filename, 'url': self.wheel_url, 'hashes': {'sha256': sha(self.body)},
                      'core-metadata': {'sha256': sha(self.meta)}}
        self.item = {'filename': self.filename, 'distribution': 'demo', 'sha256': sha(self.body)}

    def run_one(self, routes, item=None):
        opener = FakeOpener(routes)
        client = W.Client(budget=20, opener=opener, sleep=lambda s: None)
        return W.acquire_one(item or self.item, client, {}), opener

    def routes(self, entry=None, meta=None):
        return {W.index_url('demo'): FakeResponse(200, index('demo', [entry or self.entry])),
                self.wheel_url + '.metadata': FakeResponse(200, self.meta if meta is None else meta)}

    def test_exact_filename_and_hash_match_is_verified_and_no_wheel_is_requested(self):
        result, opener = self.run_one(self.routes())
        self.assertEqual(result['status'], 'verified')
        self.assertTrue(result['located'])
        self.assertEqual(result['metadata'], self.meta.decode())
        self.assertFalse(any(W.is_wheel_url(u) for u in opener.seen))
        self.assertEqual(opener.seen, [W.index_url('demo'), self.wheel_url + '.metadata'])

    def test_same_version_with_another_build_or_hash(self):
        other = {**self.entry, 'filename': wheel('demo', '1.0', build='2')}
        result, _ = self.run_one(self.routes(entry=other))
        self.assertEqual(result['status'], 'missing')
        result, _ = self.run_one(self.routes(entry={**self.entry, 'hashes': {'sha256': '0' * 64}}))
        self.assertEqual(result['status'], 'conflicting')

    def test_missing_core_metadata_is_unknown_with_no_wheel_fallback(self):
        for value in (None, False, True):
            entry = {k: v for k, v in self.entry.items() if k != 'core-metadata'}
            if value is not None:
                entry['core-metadata'] = value
            result, opener = self.run_one(self.routes(entry=entry))
            self.assertEqual(result['status'], 'unknown', value)
            self.assertEqual(opener.seen, [W.index_url('demo')])

    def test_metadata_hash_mismatch_is_unknown(self):
        result, _ = self.run_one(self.routes(meta=b'Name: demo\nVersion: 1.0\n\ntampered'))
        self.assertEqual(result['status'], 'unknown')
        self.assertIn('hash mismatch', result['reason'])

    def test_oversized_truncated_and_malformed_responses(self):
        big = b'x' * (W.METADATA_CAP + 1)
        routes = self.routes(meta=big)
        result, _ = self.run_one(routes)
        self.assertEqual(result['status'], 'unknown')
        self.assertIn('cap', result['reason'])
        undeclared = self.routes()
        undeclared[self.wheel_url + '.metadata'] = FakeResponse(200, big, headers={'Content-Length': 'unknown'})
        self.assertEqual(self.run_one(undeclared)[0]['status'], 'unknown')
        truncated = self.routes()
        truncated[self.wheel_url + '.metadata'] = FakeResponse(200, self.meta[:10],
                                                               headers={'Content-Length': str(len(self.meta))})
        self.assertIn('truncated', self.run_one(truncated)[0]['reason'])
        broken = {W.index_url('demo'): FakeResponse(200, b'{not json')}
        self.assertEqual(self.run_one(broken)[0]['status'], 'unknown')

    def test_timeouts_are_bounded_and_recorded_unknown(self):
        def timeout():
            raise socket.timeout('read timed out')
        routes = {W.index_url('demo'): timeout}
        result, opener = self.run_one(routes)
        self.assertEqual(result['status'], 'unknown')
        self.assertEqual(len(opener.seen), W.ATTEMPTS_PER_REQUEST)
        client = W.Client(budget=1, opener=FakeOpener(routes), sleep=lambda s: None)
        with self.assertRaises(W.FetchError):
            client.get(W.index_url('demo'), 100)

    def test_redirects_are_validated(self):
        def redirect_to(location):
            def fail():
                raise urllib.error.HTTPError(W.index_url('demo'), 301, 'moved', {'Location': location}, None)
            return fail
        evil = {W.index_url('demo'): redirect_to('https://evil.example/simple/demo/')}
        result, opener = self.run_one(evil)
        self.assertEqual(result['status'], 'unknown')
        self.assertIn('unexpected destination', result['reason'])
        self.assertNotIn('https://evil.example/simple/demo/', opener.seen)
        to_wheel = {W.index_url('demo'): redirect_to(self.wheel_url)}
        result, opener = self.run_one(to_wheel)
        self.assertIn('names a wheel', result['reason'])
        self.assertFalse(any(W.is_wheel_url(u) for u in opener.seen))
        moved = 'https://pypi.org/simple/demo-moved/'
        ok = {W.index_url('demo'): redirect_to(moved), moved: FakeResponse(200, index('demo', [self.entry])),
              self.wheel_url + '.metadata': FakeResponse(200, self.meta)}
        self.assertEqual(self.run_one(ok)[0]['status'], 'verified')

    def test_the_client_refuses_wheel_urls_and_foreign_hosts(self):
        client = W.Client(budget=5, opener=FakeOpener({}), sleep=lambda s: None)
        for url in (self.wheel_url, self.wheel_url.upper().replace('HTTPS', 'https'),
                    'http://pypi.org/simple/demo/', 'https://pypi.org.evil.example/simple/demo/',
                    'https://user:pw@pypi.org/simple/demo/'):
            with self.assertRaises(W.FetchError, msg=url):
                client.get(url, 100)
        self.assertEqual(client.requests, [])


def item(filename, meta=None, status=None):
    """A self-consistent (inventory row, acquisition row) pair, as a real verified acquisition would record it."""
    body = filename.encode()
    inv_row = {'filename': filename, 'size': len(body), 'sha256': sha(body), **W.wheel_identity(filename)}
    url = f'https://files.pythonhosted.org/packages/xx/{filename}'
    acq_row = {'filename': filename, 'status': status or ('verified' if meta else 'unknown'),
               'index_url': W.index_url(inv_row['distribution']),
               'located': True, 'upstream_url': url, 'upstream_sha256': sha(body)}
    if meta:
        acq_row.update(metadata=meta, metadata_sha256=sha(meta.encode()), metadata_url=url + '.metadata',
                       metadata_final_url=url + '.metadata')
    return inv_row, acq_row


def fixture(rows):
    inv = {'archive': 'fixture', 'archive_sha256': 'a' * 64, 'manifest_hashes': {}, 'non_wheel_files': [],
           'wheels': [r[0] for r in rows]}
    acq = {'acquired_at': 'fixture', 'requests_made': 2 * len(rows), 'wheel_urls_requested': [], 'bounds': {},
           'inventory_archive_sha256': 'a' * 64, 'wheels': [r[1] for r in rows]}
    return inv, acq


def build(rows, pins):
    inv, acq = fixture(rows)
    with mock.patch.object(W, 'ROOT_PINS', tuple(pins)):
        return W.analyze(inv, acq)


class Closure(unittest.TestCase):
    def test_complete_closure_passes(self):
        report = build([item(wheel('app', '1.0'), metadata('app', '1.0', ['lib>=2'])),
                        item(wheel('lib', '2.1'), metadata('lib', '2.1'))], ['app==1.0'])
        self.assertTrue(report['summary']['closure_complete'])
        self.assertEqual(report['summary']['verdict'], 'metadata_closure_complete')

    def test_dependency_absent_from_inventory(self):
        report = build([item(wheel('app', '1.0'), metadata('app', '1.0', ['ghost']))], ['app==1.0'])
        self.assertFalse(report['summary']['closure_complete'])
        self.assertEqual(report['missing'][0]['requirement'], 'ghost')

    def test_conflicting_constraints(self):
        report = build([item(wheel('app', '1.0'), metadata('app', '1.0', ['lib<2'])),
                        item(wheel('lib', '2.1'), metadata('lib', '2.1'))], ['app==1.0'])
        self.assertEqual(report['conflicts'][0]['available'], '2.1')
        self.assertFalse(report['summary']['closure_complete'])

    def test_incompatible_requires_python(self):
        report = build([item(wheel('app', '1.0'), metadata('app', '1.0', requires_python='>=3.13'))], ['app==1.0'])
        self.assertTrue(any(p['kind'] == 'requires_python' for p in report['problems']))
        self.assertFalse(report['summary']['closure_complete'])

    def test_compatible_older_manylinux_tags_are_accepted(self):
        for tag in ('cp312-cp312-manylinux_2_17_x86_64', 'cp312-cp312-manylinux2014_x86_64',
                    'cp38-abi3-manylinux_2_31_x86_64', 'cp312-cp312-manylinux_2_28_x86_64.manylinux_2_34_x86_64',
                    'py3-none-any'):
            report = build([item(wheel('app', '1.0', tag), metadata('app', '1.0'))], ['app==1.0'])
            self.assertTrue(report['wheels'][0]['tag_compatible'], tag)

    def test_wrong_architecture_abi_or_newer_glibc_is_rejected(self):
        for tag in ('cp312-cp312-manylinux_2_17_aarch64', 'cp311-cp311-manylinux_2_17_x86_64',
                    'cp312-cp312-win_amd64', 'cp312-cp312-macosx_11_0_arm64', 'cp312-cp312-manylinux_2_35_x86_64'):
            report = build([item(wheel('app', '1.0', tag), metadata('app', '1.0'))], ['app==1.0'])
            self.assertFalse(report['wheels'][0]['tag_compatible'], tag)
            self.assertFalse(report['summary']['closure_complete'], tag)

    def test_dependencies_activated_through_extras(self):
        rows = [item(wheel('app', '1.0'), metadata('app', '1.0', ['lib[img]'])),
                item(wheel('lib', '2.0'), metadata('lib', '2.0', ['pillow; extra == "img"', 'audio; extra == "snd"'],
                                                   extras=['img', 'snd'])),
                item(wheel('pillow', '11.0'), metadata('pillow', '11.0'))]
        report = build(rows, ['app==1.0'])
        self.assertTrue(report['summary']['closure_complete'])
        required = {r['distribution'] for r in report['wheels'] if r['required']}
        self.assertEqual(required, {'app', 'lib', 'pillow'})
        without = build(rows[:2], ['app==1.0'])
        self.assertEqual(without['missing'][0]['requirement'], 'pillow; extra == "img"')

    def test_markers_use_the_declared_target_not_the_host(self):
        rows = [item(wheel('app', '1.0'), metadata('app', '1.0', [
            'winonly; sys_platform == "win32"', 'maconly; sys_platform == "darwin"',
            'linuxonly; sys_platform == "linux" and platform_machine == "x86_64"',
            'old; python_version < "3.10"'])),
            item(wheel('linuxonly', '1.0'), metadata('linuxonly', '1.0'))]
        fake_host = {'sys_platform': 'win32', 'platform_machine': 'AMD64', 'python_version': '3.9',
                     'python_full_version': '3.9.1', 'platform_system': 'Windows', 'os_name': 'nt'}
        with mock.patch('packaging.markers.default_environment', return_value=fake_host):
            report = build(rows, ['app==1.0'])
        self.assertTrue(report['summary']['closure_complete'], report['missing'])
        from packaging.markers import default_environment
        self.assertLessEqual(set(default_environment()), set(W.TARGET_ENVIRONMENT))

    def test_duplicate_distributions_are_diagnosed(self):
        report = build([item(wheel('app', '1.0'), metadata('app', '1.0')),
                        item(wheel('app', '1.1'), metadata('app', '1.1'))], ['app==1.0'])
        self.assertTrue(any(p['kind'] == 'duplicate_distribution' for p in report['problems']))
        self.assertFalse(report['summary']['closure_complete'])

    def test_unknown_metadata_never_passes_and_unrequired_is_only_reported(self):
        report = build([item(wheel('app', '1.0'), metadata('app', '1.0', ['lib'])),
                        item(wheel('lib', '1.0')), item(wheel('extra', '1.0'), metadata('extra', '1.0'))], ['app==1.0'])
        self.assertFalse(report['summary']['closure_complete'])
        self.assertEqual(report['unknown'][0]['distribution'], 'lib')
        self.assertEqual(report['unrequired'], [wheel('extra', '1.0')])
        self.assertEqual(len(report['wheels']), 3)  # nothing removed

    def test_report_generation_is_stable(self):
        rows = [item(wheel('app', '1.0'), metadata('app', '1.0', ['lib'])), item(wheel('lib', '1.0'),
                                                                                metadata('lib', '1.0'))]
        first, second = build(rows, ['app==1.0']), build(list(reversed(rows)), ['app==1.0'])
        self.assertEqual(W.dumps(first), W.dumps(second))
        self.assertEqual(W.render_markdown(first), W.render_markdown(second))


class Retained(unittest.TestCase):
    def test_root_pins_match_the_current_install_path(self):
        source = (ROOT / 'certification/phase4_v6/target_install_probe_r5.py').read_text(encoding='utf-8')
        pins = re.search(r'MODEL_PINS = \[(.*?)\]', source).group(1)
        self.assertEqual(tuple(p.strip(" '\"") for p in pins.split(',')), W.ROOT_PINS)

    def test_inventory_is_verified_against_the_pinned_manifest_hashes(self):
        inv = W.inventory()
        self.assertTrue(inv['manifests_verified'])
        self.assertEqual(len(inv['wheels']), 174)
        self.assertEqual(len(inv['non_wheel_files']), 5)
        torch = next(w for w in inv['wheels'] if w['distribution'] == 'torch')
        self.assertEqual((torch['version'], torch['build']), ('2.10.0', '3'))
        with mock.patch.object(W, 'pinned_manifest_hashes', return_value={'SHA256SUMS': '0' * 64,
                                                                          'wheelhouse-manifest.json': '0' * 64}):
            with self.assertRaises(SystemExit):
                W.inventory()

    def test_acquisition_record_is_byte_stable(self):
        record = {'b': [1, 2], 'a': 'x'}
        path = ROOT / 'reports' / '.wheelhouse_metadata_test.json.gz'
        try:
            W.write_acquisition(record, path)
            first = path.read_bytes()
            W.write_acquisition(record, path)
            self.assertEqual(first, path.read_bytes())
            self.assertEqual(W.read_acquisition(path), record)
        finally:
            path.unlink(missing_ok=True)

    def test_committed_reports_reproduce_offline_without_network(self):
        if not W.ACQUISITION.exists():
            self.skipTest('no retained acquisition record')
        with mock.patch.object(W.Client, 'get', side_effect=AssertionError('network used')):
            report = W.analyze(W.inventory(), W.read_acquisition())
        self.assertEqual(W.dumps(report), W.REPORT_JSON.read_text(encoding='utf-8'))
        self.assertEqual(W.render_markdown(report), W.REPORT_MD.read_text(encoding='utf-8'))
        record = W.read_acquisition()
        self.assertEqual(record['wheel_urls_requested'], [])


class EvidenceValidation(unittest.TestCase):
    """Review finding 1: retained evidence is validated against the inventory before analysis."""

    @classmethod
    def setUpClass(cls):
        cls.inv = W.inventory()
        cls.acq = W.read_acquisition()

    def verdict(self, acq):
        return W.analyze(self.inv, acq)['summary']['verdict']

    def mutated(self, change, filename=None):
        import copy
        acq = copy.deepcopy(self.acq)
        row = next(r for r in acq['wheels'] if filename is None or r['filename'] == filename)
        change(acq, row)
        return acq

    def test_the_retained_acquisition_passes_validation(self):
        result = W.validate_evidence(self.inv, self.acq)
        self.assertTrue(result['bound'])
        self.assertEqual(result['problems'], [])
        self.assertEqual(result['verified_entries'], 174)
        self.assertEqual(self.verdict(self.acq), 'metadata_closure_complete')

    def test_review_mutations_each_prevent_a_complete_result(self):
        torch = next(w['filename'] for w in self.inv['wheels'] if w['distribution'] == 'torch')
        mutations = {
            'wrong archive binding': lambda acq, row: acq.__setitem__('inventory_archive_sha256', '0' * 64),
            'wrong upstream hash': lambda acq, row: row.__setitem__('upstream_sha256', '0' * 64),
            'wrong metadata hash': lambda acq, row: row.__setitem__('metadata_sha256', '0' * 64),
            'modified metadata': lambda acq, row: row.__setitem__('metadata', row['metadata'].replace(
                'Requires-Dist:', 'Requires-Dist: ghost\nRequires-Dist:', 1)),
        }
        for name, change in mutations.items():
            self.assertEqual(self.verdict(self.mutated(change, torch)), 'unresolved', name)

    def test_stored_flags_are_not_trusted(self):
        first = self.acq['wheels'][0]['filename']
        cases = {
            'located but foreign host': lambda acq, row: row.__setitem__(
                'upstream_url', row['upstream_url'].replace('files.pythonhosted.org', 'evil.example')),
            'located but another artifact': lambda acq, row: row.__setitem__(
                'upstream_url', row['upstream_url'].rsplit('/', 1)[0] + '/other-1.0-py3-none-any.whl'),
            'verified without metadata': lambda acq, row: row.pop('metadata'),
            'metadata URL elsewhere': lambda acq, row: row.__setitem__(
                'metadata_url', 'https://pypi.org/simple/x.metadata'),
            'final URL on another host': lambda acq, row: row.__setitem__(
                'metadata_final_url', 'https://evil.example/m.metadata'),
            'metadata of another package': lambda acq, row: (
                row.__setitem__('metadata', 'Metadata-Version: 2.1\nName: other\nVersion: 9\n'),
                row.__setitem__('metadata_sha256', sha(b'Metadata-Version: 2.1\nName: other\nVersion: 9\n'))),
            'unknown status': lambda acq, row: row.__setitem__('status', 'trusted'),
            'duplicate entry': lambda acq, row: acq['wheels'].append(dict(row)),
            'unexpected entry': lambda acq, row: acq['wheels'].append({**row, 'filename': 'extra-1.0-py3-none-any.whl'}),
            'missing entry': lambda acq, row: acq['wheels'].remove(row),
            'wheel URL in accounting': lambda acq, row: acq.__setitem__('wheel_urls_requested', [row['upstream_url']]),
            'impossible request count': lambda acq, row: acq.__setitem__('requests_made', 3),
        }
        for name, change in cases.items():
            acq = self.mutated(change, first)
            self.assertNotEqual(W.validate_evidence(self.inv, acq)['problems'], [], name)
            self.assertEqual(self.verdict(acq), 'unresolved', name)

    def test_fixture_mutations_downgrade_to_invalid(self):
        rows = [item(wheel('app', '1.0'), metadata('app', '1.0'))]
        inv, acq = fixture(rows)
        acq['wheels'][0]['located'] = True
        acq['wheels'][0]['upstream_sha256'] = '0' * 64
        entry = W.validate_evidence(inv, acq)['entries'][wheel('app', '1.0')]
        self.assertEqual((entry['status'], entry['located'], entry['metadata']), ('invalid', False, None))


class TargetTags(unittest.TestCase):
    """Review finding 2: the target ABI is explicit and independent of the host build."""

    def test_host_debug_or_free_threaded_settings_do_not_change_the_target(self):
        baseline = W.target_tags()
        import sysconfig
        fake = {'Py_DEBUG': 1, 'Py_GIL_DISABLED': 1, 'abiflags': 'dt', 'SOABI': 'cpython-312d-x86_64-linux-gnu'}
        with mock.patch.object(sysconfig, 'get_config_var', side_effect=lambda k: fake.get(k)), \
                mock.patch('sys.abiflags', 'dt', create=True):
            self.assertEqual(W.target_tags(), baseline)

    def accepted(self, tag):
        return bool(W.parse_wheel_filename(wheel('app', '1.0', tag))[3] & W.target_tags())

    def test_debug_and_free_threaded_wheels_are_rejected(self):
        for tag in ('cp312-cp312d-manylinux_2_17_x86_64', 'cp312-cp312t-manylinux_2_17_x86_64'):
            self.assertFalse(self.accepted(tag), tag)

    def test_standard_abi3_and_pure_python_wheels_remain_accepted(self):
        for tag in ('cp312-cp312-manylinux_2_28_x86_64', 'cp38-abi3-manylinux_2_31_x86_64',
                    'cp36-abi3-manylinux2014_x86_64', 'py3-none-any', 'py2.py3-none-any',
                    'py3-none-manylinux_2_17_x86_64'):
            self.assertTrue(self.accepted(tag), tag)

    def test_wrong_architecture_and_newer_glibc_remain_rejected(self):
        for tag in ('cp312-cp312-manylinux_2_17_aarch64', 'cp312-cp312-manylinux_2_35_x86_64',
                    'cp313-cp313-manylinux_2_17_x86_64', 'cp312-abi3-win_amd64'):
            self.assertFalse(self.accepted(tag), tag)

    def test_report_records_the_declared_abi(self):
        report = build([item(wheel('app', '1.0'), metadata('app', '1.0'))], ['app==1.0'])
        self.assertEqual(report['target']['abi'], 'cp312')


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class TimedResponse(FakeResponse):
    """read1 delivers `step` bytes per call and advances the clock by `delay` seconds per call."""

    def __init__(self, clock, body, step, delay, headers=None):
        super().__init__(200, body, headers)
        self.clock, self.step, self.delay, self.pos = clock, step, delay, 0

    def read1(self, n=-1):
        self.clock.now += self.delay
        chunk = self._body[self.pos:self.pos + min(self.step, n)]
        self.pos += len(chunk)
        return chunk


class TimedOpener:
    def __init__(self, clock, script):
        self.clock, self.script, self.timeouts, self.seen = clock, list(script), [], []

    def open(self, request, timeout=None):
        self.timeouts.append(timeout)
        self.seen.append(request.full_url)
        latency, outcome = self.script.pop(0)
        self.clock.now += latency
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class Deadline(unittest.TestCase):
    """Review finding 3: one absolute deadline bounds each logical fetch."""

    URL = 'https://pypi.org/simple/demo/'

    def client(self, clock, script, total=10.0, op=4.0):
        opener = TimedOpener(clock, script)
        slept = []

        def sleep(seconds):
            slept.append(seconds)
            clock.now += seconds
        return W.Client(budget=50, opener=opener, sleep=sleep, clock=clock, total_deadline=total,
                        operation_timeout=op), opener, slept

    def test_trickling_body_cannot_outlast_the_deadline(self):
        clock = Clock()
        body = b'x' * 100
        client, _, _ = self.client(clock, [(0.1, TimedResponse(clock, body, step=1, delay=0.5))])
        with self.assertRaises(W.DeadlineExceeded):
            client.get(self.URL, 1000)
        self.assertLess(clock.now, 10.0 + 0.5 + 1e-9)  # stopped within one chunk of the deadline

    def test_redirects_consume_the_same_allowance(self):
        clock = Clock()
        moved = 'https://pypi.org/simple/demo2/'
        redirect = urllib.error.HTTPError(self.URL, 301, 'moved', {'Location': moved}, None)
        client, opener, _ = self.client(clock, [(9.5, redirect), (1.0, FakeResponse(200, b'ok'))])
        with self.assertRaises(W.DeadlineExceeded):
            client.get(self.URL, 1000)
        self.assertLessEqual(opener.timeouts[1], 0.5 + 1e-9)  # the second hop was bounded by what remained

    def test_retries_and_backoff_exhaust_the_deadline(self):
        clock = Clock()
        timeouts = [(3.5, socket.timeout('t')), (3.5, socket.timeout('t')), (3.5, socket.timeout('t'))]
        client, opener, slept = self.client(clock, timeouts)
        with self.assertRaises(W.DeadlineExceeded):
            client.get(self.URL, 1000)
        self.assertLessEqual(clock.now, 10.0)
        self.assertLessEqual(len(opener.seen), 3)

    def test_a_response_arriving_just_after_the_deadline_is_refused(self):
        clock = Clock()
        client, _, _ = self.client(clock, [(10.01, FakeResponse(200, b'late'))])
        with self.assertRaises(W.DeadlineExceeded):
            client.get(self.URL, 1000)

    def test_normal_bounded_completion(self):
        clock = Clock()
        body = b'y' * 300
        client, opener, _ = self.client(clock, [(0.5, TimedResponse(clock, body, step=100, delay=0.2))])
        self.assertEqual(client.get(self.URL, 1000), (body, self.URL))
        self.assertEqual(opener.timeouts, [4.0])

    def test_operation_timeout_is_capped_by_the_remaining_allowance(self):
        clock = Clock()
        clock.now = 0.0
        client, opener, _ = self.client(clock, [(8.0, urllib.error.HTTPError(self.URL, 503, 'busy', {}, None)),
                                                (0.1, FakeResponse(200, b'ok'))], total=10.0, op=4.0)
        self.assertEqual(client.get(self.URL, 100)[0], b'ok')
        self.assertEqual(opener.timeouts[0], 4.0)
        self.assertLessEqual(opener.timeouts[1], 1.0 + 1e-9)


class DownloadGate(unittest.TestCase):
    """The prepared (not executed) manifest-bound downloader."""

    def setUp(self):
        import tempfile
        from scripts import download_wheelhouse as D
        self.D = D
        self.tmp = Path(tempfile.mkdtemp())
        self.body = b'wheel-bytes-' * 10
        name = wheel('demo', '1.0')
        self.artifact = {'filename': name, 'url': f'https://files.pythonhosted.org/packages/aa/{name}',
                         'size': len(self.body), 'sha256': sha(self.body)}
        self.manifest = {'artifacts': [self.artifact], 'artifact_count': 1, 'total_bytes': len(self.body)}
        self.manifest['manifest_sha256'] = D.manifest_digest(self.manifest)
        self.path = self.tmp / 'manifest.json'
        self.path.write_text(json.dumps(self.manifest))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def downloader(self, body):
        opener = FakeOpener({self.artifact['url']: lambda: FakeResponse(200, body)})
        return self.D.Downloader(self.tmp / 'out', opener=opener, sleep=lambda s: None), opener

    def test_approval_must_name_this_manifest(self):
        with self.assertRaises(SystemExit):
            self.D.load_manifest(self.path, '0' * 64)
        self.assertEqual(self.D.load_manifest(self.path, self.manifest['manifest_sha256'])['artifact_count'], 1)
        tampered = dict(self.manifest, artifacts=[dict(self.artifact, size=1)])
        self.path.write_text(json.dumps(tampered))
        with self.assertRaises(SystemExit):
            self.D.load_manifest(self.path, self.manifest['manifest_sha256'])

    def test_foreign_or_mismatched_urls_and_in_repo_destinations_are_refused(self):
        bad = dict(self.manifest, artifacts=[dict(self.artifact, url='https://evil.example/' + self.artifact['filename'])])
        bad['manifest_sha256'] = self.D.manifest_digest(bad)
        self.path.write_text(json.dumps(bad))
        with self.assertRaises(SystemExit):
            self.D.load_manifest(self.path, bad['manifest_sha256'])
        with self.assertRaises(SystemExit):
            self.D.check_destination(ROOT / 'reports' / 'wheels')

    def test_download_verifies_and_reuses_only_verified_files(self):
        dl, opener = self.downloader(self.body)
        record = self.D.run(self.manifest, self.tmp / 'out', downloader=dl)
        self.assertTrue(record['complete'])
        self.assertEqual((self.tmp / 'out' / self.artifact['filename']).read_bytes(), self.body)
        dl2, opener2 = self.downloader(self.body)
        self.assertEqual(dl2.fetch(self.artifact)['status'], 'reused_verified')
        self.assertEqual(opener2.seen, [])
        (self.tmp / 'out' / self.artifact['filename']).write_bytes(b'corrupt')
        dl3, opener3 = self.downloader(self.body)
        self.assertEqual(dl3.fetch(self.artifact)['status'], 'downloaded_verified')
        self.assertEqual(len(opener3.seen), 1)

    def test_wrong_bytes_never_become_a_completed_artifact(self):
        for body in (b'x' * len(self.body), self.body[:-1], self.body + b'extra'):
            dl, _ = self.downloader(body)
            result = dl.fetch(self.artifact)
            self.assertEqual(result['status'], 'failed', body[:8])
            self.assertFalse((self.tmp / 'out' / self.artifact['filename']).exists())
            self.assertEqual(list((self.tmp / 'out' / '.partial').glob('*.tmp')), [])

    def test_the_downloader_never_installs_or_resolves(self):
        source = (ROOT / 'scripts/download_wheelhouse.py').read_text(encoding='utf-8')
        for word in ('pip install', 'subprocess', 'importlib', '/simple/', 'Requirement(', 'packaging'):
            self.assertNotIn(word, source)


class ManifestAndLicences(unittest.TestCase):
    def test_manifest_is_refused_unless_the_closure_is_complete(self):
        report = build([item(wheel('app', '1.0'), metadata('app', '1.0', ['ghost']))], ['app==1.0'])
        with self.assertRaises(SystemExit):
            W.download_manifest(fixture([])[0], report)

    def test_committed_manifest_and_licence_table_match_the_retained_evidence(self):
        manifest_path, table_path = W.DOWNLOAD_MANIFEST, W.LICENSE_TABLE
        if not manifest_path.exists():
            self.skipTest('no committed manifest')
        inv, acq = W.inventory(), W.read_acquisition()
        report = W.analyze(inv, acq)
        fresh = W.download_manifest(inv, report)
        committed = json.loads(manifest_path.read_text(encoding='utf-8'))
        self.assertEqual({k: v for k, v in committed.items() if k != 'checker'},
                         {k: v for k, v in fresh.items() if k != 'checker'})
        self.assertEqual(committed['artifact_count'], 174)
        from scripts import download_wheelhouse as D
        self.assertEqual(D.manifest_digest(committed), committed['manifest_sha256'])
        import csv
        rows = list(csv.DictReader(table_path.open(encoding='utf-8')))
        self.assertEqual(len(rows), 174)
        self.assertEqual({r['redistribution_status'] for r in rows}, {'unresolved'})
        self.assertTrue(all(r['owner'].startswith('dcw06') for r in rows))


if __name__ == '__main__':
    unittest.main()
