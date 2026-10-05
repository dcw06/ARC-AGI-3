"""Apache-2.0 NOTICE check: the three-outcome classification on synthetic inputs, the wheel-to-sdist tracing rules,
and the committed pack's coverage of the flagged worksheet rows. Offline: no network and no local wheels needed."""
import hashlib
import json
import unittest
from pathlib import Path

from scripts import evidence_notice as N

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'reports/wheelhouse_evidence'
PACK = EVIDENCE / 'apache_notice_check.json'


def h(text):
    return hashlib.sha256(text.encode()).hexdigest()


VERIFIED = {'status': 'verified', 'sdist': 'pkg-1.0.tar.gz', 'sha256': '0' * 64, 'verified_against_pypi': True}
SDIST = {'PKG-INFO': h('pkg-info'), 'LICENSE': h('licence'), 'pkg/__init__.py': h('init'), 'pkg/_ext.c': h('ext'),
         'pyproject.toml': h('pyproject')}


CLEAN_REPOSITORY = {'verified_clean': True, 'summary': 'o/r@abc (tag v1.0, version verified in pkg/__init__.py): '
                                                       'no NOTICE-named file in 40 tree entries'}


def evidence(**changes):
    """A wheel/sdist that meets every package condition, with a clean, version-verified release repository."""
    e = {'notices': [], 'sdist': VERIFIED, 'listing_complete': True, 'member_count': 5,
         'pkg_info_version_matches': True, 'notice_like': [], 'outside': [], 'repository': CLEAN_REPOSITORY}
    e.update(changes)
    return e


def repository(notices=(), verified=True, notice_like=(), truncated=False, commit='c' * 40):
    """A repository_check() record (as returned after listing the release tree)."""
    return {'performed': True, 'repository': 'https://github.com/o/r', 'tag': 'v1.0', 'commit': commit,
            'tree_entries': 40, 'tree_truncated': truncated, 'notice_like': list(notice_like),
            'version_check': {'verified': verified, 'path': 'pkg/__init__.py'},
            'notices': [{'source': 'repository o/r@cccccccccccc', 'path': n, 'counts_for_outcome': verified}
                        for n in notices], 'submodule_checks': []}


def member(path, content='', elf=False, **extra):
    return dict({'path': path, 'sha256': h(content), 'elf': elf}, **extra)


class NoticeNames(unittest.TestCase):
    def test_notice_names_at_any_path_any_case(self):
        for path in ('NOTICE', 'NOTICE.txt', 'notice.md', 'NOTICES', 'vendor/llhttp/Notice.rst', 'a/b/NOTICE.TXT'):
            self.assertTrue(N.is_notice_name(path), path)
        for path in ('LICENSE', 'pkg/notice.py', 'NOTICEBOARD', 'THIRD_PARTY_NOTICES.txt'):
            self.assertFalse(N.is_notice_name(path), path)

    def test_notice_like_documents_need_a_look_but_code_and_data_do_not(self):
        self.assertTrue(N.is_notice_like('THIRD_PARTY_NOTICES.txt'))
        self.assertTrue(N.is_notice_like('licenses/NOTICE-binary'))
        self.assertFalse(N.is_notice_like('NOTICE'))
        self.assertFalse(N.is_notice_like('x509/UserNoticeQualifierTest15EE.crt'))
        self.assertFalse(N.is_notice_like('pkg/notice.py'))

    def test_retained_names_are_safe_and_prefixed(self):
        name = N.source_name('vllm', 'sdist', 'csrc/third party/NOTICE')
        self.assertEqual(name, 'notice-vllm-sdist-csrc+third_party+NOTICE')


class Classify(unittest.TestCase):
    def test_found_when_the_sdist_has_a_notice(self):
        outcome, reason = N.classify(evidence(notices=[{'source': 'sdist pkg-1.0.tar.gz', 'path': 'vendor/x/NOTICE'}]))
        self.assertEqual(outcome, 'found')
        self.assertIn('vendor/x/NOTICE', reason)

    def test_found_takes_precedence_over_a_missing_sdist(self):
        e = evidence(notices=[{'source': 'repository o/r@abc', 'path': 'NOTICE'}],
                     sdist={'status': 'none', 'reason': 'no sdist on PyPI'})
        self.assertEqual(N.classify(e)[0], 'found')

    def test_repository_only_notice_is_found_and_says_so(self):
        outcome, reason = N.classify(evidence(notices=[{'source': 'repository o/r@abc', 'path': 'NOTICE'}]))
        self.assertEqual(outcome, 'found')
        self.assertIn('repository only', reason)

    def test_verified_absent_only_when_every_condition_holds(self):
        outcome, reason = N.classify(evidence())
        self.assertEqual(outcome, 'verified_absent')
        self.assertIn('pkg-1.0.tar.gz', reason)

    def test_package_absence_alone_is_not_verified_absent(self):
        """Review P2 on 42c2b4c: without a verified release repository, the upstream question stays open."""
        outcome, reason = N.classify(evidence(repository=None))
        self.assertEqual(outcome, 'inconclusive')
        self.assertIn('absent from the inspected wheel and sdist', reason)
        self.assertIn('upstream NOTICE question stays open', reason)

    def test_repository_is_consulted_after_a_clean_package_and_its_notice_counts(self):
        """The reviewer's synthetic case: byte-identical wheel/sdist, NOTICE only in the release repository."""
        calls = []
        outcome, reason, repo = N.decide(evidence(repository=None), [],
                                         lambda: calls.append(1) or repository(notices=['NOTICE']))
        self.assertEqual(calls, [1])
        self.assertEqual(outcome, 'found')
        self.assertIn('repository only', reason)

    def test_repository_conditions_for_verified_absent(self):
        cases = {'clean and version-verified': (repository(), 'verified_absent'),
                 'version not verified': (repository(verified=False), 'inconclusive'),
                 'notice-like file in the tree': (repository(notice_like=['THIRD_PARTY_NOTICES.txt']), 'inconclusive'),
                 'tree truncated': (repository(truncated=True), 'inconclusive'),
                 'not listed (no repository named)': ({'performed': False, 'reason': 'no repository'},
                                                     'inconclusive')}
        for label, (repo, expected) in cases.items():
            with self.subTest(case=label):
                outcome, reason, _ = N.decide(evidence(repository=None), [], lambda: repo)
                self.assertEqual(outcome, expected, reason)

    def test_a_notice_in_the_wheel_or_sdist_needs_no_repository(self):
        outcome, _, repo = N.decide(evidence(notices=[{'source': 'sdist pkg-1.0.tar.gz', 'path': 'NOTICE'}]), [],
                                    lambda: self.fail('repository consulted unnecessarily'))
        self.assertEqual((outcome, repo['performed']), ('found', False))

    def test_no_sdist_is_inconclusive(self):
        outcome, reason = N.classify(evidence(sdist={'status': 'none', 'reason': 'no sdist on PyPI'}))
        self.assertEqual(outcome, 'inconclusive')
        self.assertIn('no sdist', reason)

    def test_fetch_failure_is_inconclusive_never_absence(self):
        outcome, reason = N.classify(evidence(sdist={'status': 'error', 'reason': 'URLError: timed out'}))
        self.assertEqual(outcome, 'inconclusive')
        self.assertIn('timed out', reason)
        self.assertIn('not evidence of absence', reason)

    def test_unreadable_listing_version_mismatch_and_notice_like_are_inconclusive(self):
        for changes in ({'listing_complete': False, 'listing_error': 'EOFError'},
                        {'pkg_info_version_matches': False},
                        {'notice_like': ['sdist: THIRD_PARTY_NOTICES.txt']}):
            self.assertEqual(N.classify(evidence(**changes))[0], 'inconclusive', changes)

    def test_bundled_auditwheel_libraries_are_inconclusive(self):
        wheel = [member('pkg/__init__.py', 'init'), member('pkg/_ext.cpython-312-x86_64-linux-gnu.so', 'bin', elf=True),
                 member('pkg.libs/libssl-1a2b3c.so.3', 'ssl', elf=True)]
        outside, coverage = N.outside_components(wheel, SDIST)
        self.assertTrue(any('auditwheel' in r for r in outside))
        self.assertEqual(coverage['auditwheel_libs'], ['pkg.libs/libssl-1a2b3c.so.3'])
        outcome, reason = N.classify(evidence(outside=outside))
        self.assertEqual(outcome, 'inconclusive')
        self.assertIn('pkg.libs/libssl', reason)


class Tracing(unittest.TestCase):
    def test_pure_python_and_own_extension_are_traced(self):
        wheel = [member('pkg/__init__.py', 'init'), member('pkg-1.0.dist-info/METADATA', 'meta'),
                 member('pkg/_ext.cpython-312-x86_64-linux-gnu.so', 'bin', elf=True)]
        outside, coverage = N.outside_components(wheel, SDIST)
        self.assertEqual(outside, [])
        self.assertEqual((coverage['matched_by_content'], coverage['unmatched']), (1, 0))
        self.assertEqual(N.classify(evidence(outside=outside))[0], 'verified_absent')

    def test_binary_without_matching_source_is_not_traced(self):
        outside, _ = N.outside_components([member('pkg/_other.abi3.so', 'bin', elf=True)], SDIST)
        self.assertTrue(any('no source file named _other' in r for r in outside))

    def test_embedded_third_party_markers_are_not_traced(self):
        wheel = [member('pkg/_ext.cpython-312-x86_64-linux-gnu.so', 'bin', elf=True, markers=['OpenSSL 3.5.0'])]
        outside, _ = N.outside_components(wheel, SDIST)
        self.assertTrue(any('OpenSSL 3.5.0' in r for r in outside))

    def test_rust_crates_from_a_registry_are_outside_unless_vendored(self):
        sdist = dict(SDIST, **{'Cargo.toml': h('cargo'), 'src/lib.rs': h('rs')})
        lock = ('[[package]]\nname = "pkg"\nversion = "1.0.0"\n\n[[package]]\nname = "serde"\nversion = "1.0.200"\n'
                'source = "registry+https://github.com/rust-lang/crates.io-index"\n')
        rust = N.rust_summary(sdist, {'Cargo.lock': lock})
        self.assertEqual(rust['external_crates'], 1)
        outside, _ = N.outside_components([member('pkg/_pkg.abi3.so', 'bin', elf=True)], sdist, rust)
        self.assertTrue(any('Rust build' in r for r in outside))
        vendored = dict(sdist, **{'vendor/serde/.cargo-checksum.json': h('sum')})
        self.assertEqual(N.rust_summary(vendored, {'Cargo.lock': lock})['external_crates'], 0)
        self.assertIsNone(N.rust_summary(SDIST, {}))

    def test_wheel_file_absent_from_sdist_is_not_traced(self):
        outside, coverage = N.outside_components([member('pkg/third_party/kernel.py', 'copied')], SDIST)
        self.assertEqual(coverage['unmatched_sample'], ['pkg/third_party/kernel.py'])
        self.assertTrue(any('neither content nor path' in r for r in outside))

    def test_same_path_with_different_content_counts_as_from_the_sdist(self):
        outside, coverage = N.outside_components([member('pkg/__init__.py', 'rewritten at build')], SDIST)
        self.assertEqual((outside, coverage['matched_by_path_content_differs']), ([], 1))

    def test_generated_version_stub_needs_the_exact_version(self):
        stub = member('pkg/_version.py', 'v', text='version = "1.0"\n')
        self.assertEqual(N.outside_components([stub], SDIST, version='1.0')[0], [])
        self.assertNotEqual(N.outside_components([stub], SDIST, version='2.0')[0], [])

    def test_download_directives_count_unless_test_only(self):
        cmake = (b'include(CTest)\nif(BUILD_TESTING)\n  if(NOT GTest_FOUND)\n    FetchContent_Declare(googletest)\n'
                 b'  endif()\nendif()\nFetchContent_Declare(cutlass)\n')
        hits = N.download_hits({'CMakeLists.txt': cmake})
        self.assertEqual([(x['line'], x['test_only']) for x in hits], [(4, True), (7, False)])
        native = [member('pkg/_ext.cpython-312-x86_64-linux-gnu.so', 'bin', elf=True)]
        outside, _ = N.outside_components(native, SDIST, downloads=hits)
        self.assertTrue(any('CMakeLists.txt:7' in r and 'CMakeLists.txt:4' not in r for r in outside))
        self.assertEqual(N.outside_components(native, SDIST, downloads=hits[:1])[0], [])
        self.assertFalse(N.cmake_test_only('if(NOT BUILD_TESTING)\nFetchContent_Declare(x)\n', 30))

    def test_a_message_mentioning_git_clone_is_not_a_download(self):
        setup = b'print("Install submodules when building from git clone", file=sys.stderr)\n'
        self.assertEqual(N.download_hits({'setup.py': setup}), [])
        self.assertEqual(len(N.download_hits({'setup.py': b'subprocess.check_call("git clone https://x")\n'})), 1)

    def test_a_vendored_copy_with_its_own_licence_still_needs_upstream_verification(self):
        """Review gap on cca0551: a LICENSE in a vendored copy does not establish that upstream has no NOTICE."""
        sdist = dict(SDIST, **{'vendor/libuv/LICENSE': h('mit'), 'vendor/libuv/src/uv.c': h('uv')})
        vendored = N.vendored_dirs(sdist)
        native = [member('pkg/_ext.cpython-312-x86_64-linux-gnu.so', 'bin', elf=True)]
        copies = N.third_party_copies(vendored, native, sdist)
        self.assertEqual(list(copies), ['vendor/libuv'])
        self.assertIn('top-level licence files LICENSE', copies['vendor/libuv'])
        outcome, reason = N.classify(evidence(third_party=copies))
        self.assertEqual(outcome, 'inconclusive')
        self.assertIn('a licence file in a copy does not establish it', reason)
        verified = N.classify(evidence(third_party={}, cleared=['vendor/libuv (libuv/libuv@abc, 2 files matching '
                                                                 'its blobs, no NOTICE-named file)']))
        self.assertEqual(verified[0], 'verified_absent')

    def test_trimmed_third_party_copy_reaching_the_wheel_is_inconclusive(self):
        sdist = dict(SDIST, **{'3rdparty/cutlass/include/gemm.h': h('gemm'), 'vendor/libuv/LICENSE': h('uv-lic'),
                               'vendor/libuv/src/uv.c': h('uv')})
        vendored = N.vendored_dirs(sdist)
        self.assertEqual([(v['dir'], v['top_level_licence_files']) for v in vendored],
                         [('3rdparty/cutlass', []), ('vendor/libuv', ['LICENSE'])])
        shipped = [member('pkg/data/cutlass/include/gemm.h', 'gemm')]
        trimmed = N.third_party_copies(vendored, shipped, sdist)
        self.assertEqual(list(trimmed), ['3rdparty/cutlass'])
        outcome, reason = N.classify(evidence(third_party=trimmed))
        self.assertEqual(outcome, 'inconclusive')
        self.assertIn('3rdparty/cutlass', reason)
        self.assertEqual(N.third_party_copies(vendored, [member('pkg/__init__.py', 'init')], sdist), {})
        cleared = N.classify(evidence(third_party={}, cleared=['3rdparty/cutlass (NVIDIA/cutlass@abc)']))
        self.assertEqual(cleared[0], 'verified_absent')
        self.assertIn('3rdparty/cutlass', cleared[1])

    def test_gitmodules_urls(self):
        text = ('[submodule "3rdparty/cutlass"]\n\tpath = 3rdparty/cutlass\n\turl = https://github.com/NVIDIA/cutlass.git\n'
                '[submodule "spdlog"]\n\turl = git@github.com:gabime/spdlog.git\n\tpath = 3rdparty/spdlog\n')
        self.assertEqual(N.gitmodules_urls(text), {'3rdparty/cutlass': 'https://github.com/NVIDIA/cutlass.git',
                                                   '3rdparty/spdlog': 'git@github.com:gabime/spdlog.git'})

    def test_version_line_and_candidates(self):
        self.assertEqual(N.version_line('[package]\nname = "b"\nversion = "1.0.8"\n', '1.0.8'), 'version = "1.0.8"')
        self.assertIsNone(N.version_line('version = "1.0.80"\n', '1.0.8'))
        self.assertIsNone(N.version_line('__version__ = get_version()\n', '1.0.8'))
        blobs = ['cuda_core/setup.py', 'cuda_pathfinder/cuda/pathfinder/_version.py', 'tests/__init__.py']
        self.assertEqual(N.version_file_candidates(blobs, 'cuda_pathfinder')[0],
                         'cuda_pathfinder/cuda/pathfinder/_version.py')
        many = [f'flashinfer/m{i}/__init__.py' for i in range(40)] + ['version.txt', 'setup.py']
        self.assertEqual(N.version_file_candidates(many, 'flashinfer_python')[:2], ['version.txt', 'setup.py'])


class CommittedPack(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(PACK.read_text(encoding='utf-8'))
        cls.rows = cls.pack['rows']

    def test_covers_exactly_the_flagged_worksheet_rows(self):
        flagged = N.flagged_rows()
        self.assertEqual(len(flagged), 37)
        self.assertEqual(sorted((r['artifact'], r['sha256']) for r in self.rows),
                         sorted((r['artifact'], r['sha256']) for r in flagged))

    def test_one_allowed_outcome_each_with_reason_and_remaining_requirements(self):
        for r in self.rows:
            self.assertIn(r['outcome'], N.OUTCOMES, r['artifact'])
            self.assertTrue(r['reason'] and r['remains'], r['artifact'])
        self.assertEqual(self.pack['counts'], {o: sum(r['outcome'] == o for r in self.rows) for o in N.OUTCOMES})
        self.assertIn('not a decision', self.pack['status'])

    def test_every_found_notice_is_retained_with_matching_hash(self):
        for r in self.rows:
            if r['outcome'] != 'found':
                continue
            self.assertTrue(r['notices'], r['artifact'])
            for n in r['notices']:
                data = (EVIDENCE / n['retained']['file']).read_bytes()
                self.assertTrue(n['retained']['file'].startswith('sources/notice-'))
                self.assertEqual(hashlib.sha256(data).hexdigest(), n['sha256'])
                self.assertEqual(n['retained']['sha256'], n['sha256'])

    def test_retained_version_files_match_their_hashes(self):
        for r in self.rows:
            vc = (r.get('repository_check') or {}).get('version_check') or {}
            if vc.get('verified'):
                data = (EVIDENCE / vc['retained']['file']).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), vc['retained']['sha256'])
                self.assertIn(r['version'], vc['line'])

    def test_verified_absent_rows_meet_every_condition(self):
        for r in (r for r in self.rows if r['outcome'] == 'verified_absent'):
            sdist, listing, traced = r['sdist'], r['sdist_listing'], r['wheel_traced_to_sdist']
            self.assertEqual((sdist['status'], sdist['verified_against_pypi']), ('verified', True), r['artifact'])
            self.assertIn(r['version'], sdist['sdist'])
            self.assertTrue(listing['pkg_info_version_matches'])
            self.assertEqual((listing['notice_named_paths'], listing['notice_like_paths'], r['notices']), ([], [], []))
            self.assertEqual((traced['unmatched'], traced['auditwheel_libs']), (0, []))
            self.assertTrue(all(not b['outside_sdist_reasons'] for b in traced['native_binaries']), r['artifact'])
            cleared = {s['path'] for s in (r.get('repository_check') or {}).get('submodule_checks', [])
                       if s['cleared']}
            self.assertEqual(set(listing['third_party_copies_reaching_wheel']) - cleared, set(), r['artifact'])
            self.assertIn('can be dropped', r['remains'])
            self.assertIn('licence texts', r['remains'])
            repo = r['repository_check']
            self.assertTrue(repo.get('commit') and repo['version_check']['verified'], r['artifact'])
            self.assertEqual((repo['notices'], repo['notice_like'], repo['tree_truncated']), ([], [], False),
                             r['artifact'])

    def test_cleared_submodules_match_the_sdist_copy_and_have_no_notice(self):
        for r in self.rows:
            repo = r.get('repository_check') or {}
            for s in (s for s in repo.get('submodule_checks', []) if s['cleared']):
                self.assertTrue(repo['version_check']['verified'], r['artifact'])
                self.assertEqual(s['sdist_copy_files_matching_pinned_blobs'], s['sdist_copy_files'])
                self.assertEqual((s['notices'], s['notice_like'], s['tree_truncated']), ([], [], False))

    def test_inconclusive_rows_keep_the_question_open(self):
        for r in (r for r in self.rows if r['outcome'] == 'inconclusive'):
            self.assertIn('stays open', r['remains'])
            self.assertFalse(any(n.get('counts_for_outcome') for n in r.get('notices', [])), r['artifact'])

    def test_markdown_lists_every_artifact_once(self):
        md = (EVIDENCE / 'apache_notice_check.md').read_text(encoding='utf-8')
        self.assertIn('not a decision', md)
        for r in self.rows:
            self.assertEqual(md.count(f"| `{r['artifact']}` |"), 1, r['artifact'])


if __name__ == '__main__':
    unittest.main()
