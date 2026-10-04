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
        self.status, self._body = status, body
        self.headers = {'Content-Length': str(len(body)), **(headers or {})}

    def read(self, n=-1):
        return self._body if n < 0 else self._body[:n]

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
    name, version = filename.split('-')[:2]
    body = filename.encode()
    inv_row = {'filename': filename, 'size': len(body), 'sha256': sha(body), **W.wheel_identity(filename)}
    acq_row = {'filename': filename, 'status': status or ('verified' if meta else 'unknown'),
               'located': True, 'upstream_url': f'https://files.pythonhosted.org/x/{filename}'}
    if meta:
        acq_row['metadata'] = meta
    return inv_row, acq_row


def build(rows, pins):
    inv = {'archive': 'fixture', 'archive_sha256': '0' * 64, 'manifest_hashes': {}, 'non_wheel_files': [],
           'wheels': [r[0] for r in rows]}
    acq = {'acquired_at': 'fixture', 'requests_made': 0, 'wheel_urls_requested': [], 'bounds': {},
           'wheels': [r[1] for r in rows]}
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


if __name__ == '__main__':
    unittest.main()
