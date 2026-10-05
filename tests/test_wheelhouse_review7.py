"""Regressions for the review of b289f51/127633e: the NVIDIA licence reconciliation against version-specific primary
sources (cuFile and nvJitLink are an applicability discrepancy, not "no grant"), repository licence sources pinned to
a commit that carries the exact version, and batch-2 proposals for the unflagged artifacts."""
import csv
import hashlib
import json
import unittest

from scripts import gather_upstream_licenses as G
from scripts import propose_wheelhouse_dispositions as Q
from scripts import reconcile_nvidia_licences as R


def load_csv(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return list(csv.DictReader(stream))


class Reconciliation(unittest.TestCase):
    def setUp(self):
        self.report = json.loads(R.OUT_JSON.read_text(encoding='utf-8'))
        self.wheels = {w['artifact'].split('-')[0]: w for w in self.report['wheels']}

    def test_attachment_a_section_and_name_matching(self):
        text = ('Contents 2.6. Attachment A 2.7. Attachment B ... 2.6. Attachment A Component Linux libnvJitLink.so, '
                'libnvJitLink_static.a libcufile_rdma.so 2.7. Attachment B other')
        section = R.attachment_a(text)
        self.assertTrue(section.startswith('Attachment A Component'))
        self.assertTrue(R.listed('libnvJitLink.so', section))
        self.assertTrue(R.listed('libcufile_rdma.so', section))
        self.assertFalse(R.listed('libcufile.so', section))  # not a prefix match
        self.assertEqual(R.normalised('nvidia/cu12/lib/libnvJitLink.so.12'), 'libnvJitLink.so')
        self.assertEqual(R.attachment_a('no attachments here'), '')

    def retained_copy(self):
        """A temporary copy of the retained sources and an index of them, for tampering."""
        import shutil
        import tempfile
        from pathlib import Path
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder)
        for path in R.SOURCES_DIR.iterdir():
            shutil.copy(path, folder / path.name)
        return folder, json.loads((folder / 'index.json').read_text(encoding='utf-8'))

    def test_committed_extractions_reproduce_from_the_verified_html(self):
        folder, index = self.retained_copy()
        for sid, entry in index.items():
            if entry['file'].endswith('.html'):
                text = R.source_text(index, sid, folder)
                self.assertEqual(text.encode('utf-8'), (folder / entry['text_file']).read_bytes())

    def test_altered_extraction_is_refused(self):
        folder, index = self.retained_copy()
        entry = index['cuda-12.8.1-eula']
        path = folder / entry['text_file']
        forged = path.read_bytes().replace(b'Attachment A', b'Attachment A libinvented.so', 1)
        path.write_bytes(forged)
        with self.assertRaises(SystemExit):  # recorded hash no longer matches
            R.source_text(index, 'cuda-12.8.1-eula', folder)
        entry['text_sha256'] = hashlib.sha256(forged).hexdigest()
        with self.assertRaises(SystemExit):  # hash updated too: still differs from a fresh extraction
            R.source_text(index, 'cuda-12.8.1-eula', folder)

    def test_altered_html_or_missing_extraction_hash_is_refused(self):
        folder, index = self.retained_copy()
        entry = dict(index['nvshmem-sla-latest'])
        del entry['text_sha256']
        with self.assertRaises(SystemExit):
            R.source_text(dict(index, **{'nvshmem-sla-latest': entry}), 'nvshmem-sla-latest', folder)
        page = folder / index['cuda-12.8.1-eula']['file']
        page.write_bytes(page.read_bytes() + b'<p>libinvented.so</p>')
        with self.assertRaises(SystemExit):
            R.source_text(index, 'cuda-12.8.1-eula', folder)

    def test_retained_primary_sources_match_their_hashes(self):
        for sid, entry in self.report['sources'].items():
            with self.subTest(source=sid):
                data = (R.SOURCES_DIR / entry['file']).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), entry['sha256'])
                self.assertTrue(entry['url'].startswith('https://') and entry['retrieved_on'])

    def test_cufile_and_nvjitlink_are_listed_officially_but_not_in_the_bundled_text(self):
        for prefix in ('nvidia_cufile_cu12', 'nvidia_nvjitlink_cu12'):
            with self.subTest(prefix=prefix):
                files = self.wheels[prefix]['library_files']
                self.assertTrue(files)
                self.assertTrue(all(f['in_official_attachment_a'] for f in files))
                self.assertFalse(any(f['in_bundled_attachment_a'] for f in files))
                self.assertEqual(self.wheels[prefix]['primary_source'], 'cuda-12.8.1-eula')

    def test_nvshmem_and_cutlass_have_their_own_primary_sources(self):
        self.assertEqual(self.wheels['nvidia_nvshmem_cu12']['primary_source'], 'nvshmem-v3.4.5-0-license')
        cutlass = self.wheels['nvidia_cutlass_dsl_libs_base']
        self.assertTrue(cutlass['bundled_identical_to_primary'])
        self.assertTrue(any('flashinfer-python' in x for x in cutlass['required_by']))
        self.assertTrue(any('quack-kernels' in x for x in cutlass['required_by']))
        self.assertIn('not a finding that no grant exists', self.report['findings']['nvidia_cufile_cu12'])


class RepositorySources(unittest.TestCase):
    def test_version_line_must_match_a_whole_line(self):
        self.assertTrue(G.version_confirmed('[project]\nversion = "0.5.1"\n', 'version = "0.5.1"'))
        self.assertFalse(G.version_confirmed('version = "0.5.10"\n', 'version = "0.5.1"'))

    def test_a_ref_without_the_exact_version_is_refused(self):
        responses = {'https://api.github.com/repos/o/r/commits/v0.5.1': json.dumps({'sha': 'c' * 40}).encode(),
                     f"https://raw.githubusercontent.com/o/r/{'c' * 40}/pyproject.toml": b'version = "0.0.12"\n'}
        source = G.repo('o/r', 'v0.5.1', ['LICENSE'], 'pyproject.toml', 'version = "0.5.1"')
        with self.assertRaises(SystemExit):
            G.repository_files(source, get=lambda url, cap: responses[url])

    def test_a_confirmed_ref_is_pinned_to_its_commit(self):
        base = f"https://raw.githubusercontent.com/o/r/{'d' * 40}/"
        responses = {'https://api.github.com/repos/o/r/commits/v1': json.dumps({'sha': 'd' * 40}).encode(),
                     base + 'pyproject.toml': b'version = "1.0"\n', base + 'LICENSE': b'MIT', base + 'NOTICE': b'n'}
        record, members = G.repository_files(G.repo('o/r', 'v1', ['LICENSE', 'NOTICE'], 'pyproject.toml',
                                                    'version = "1.0"'), get=lambda url, cap: responses[url])
        self.assertEqual(record['commit'], 'd' * 40)
        self.assertEqual([m[0] for m in members], ['LICENSE', 'NOTICE'])
        self.assertTrue(record['files']['NOTICE']['url'].startswith(base))

    def test_committed_repository_sources_are_commit_pinned_and_version_checked(self):
        index = json.loads(G.INDEX.read_text(encoding='utf-8'))
        repository = [e for e in index if e['source']['kind'] == 'repository_files_at_release_commit']
        self.assertEqual(len(repository), 5)
        for e in repository:
            with self.subTest(artifact=e['artifact']):
                self.assertRegex(e['source']['commit'], '^[0-9a-f]{40}$')
                self.assertTrue(e['source']['version_check']['confirmed'])
                self.assertIn(e['source']['commit'], e['source']['url'])
        semconv = next(e for e in repository if e['project'] == 'opentelemetry-semantic-conventions-ai')
        self.assertNotEqual(semconv['source']['ref'], 'v0.5.1')  # the monorepo tag is an unrelated release
        notices = {e['project'] for e in repository if any(f['member'] == 'NOTICE' for f in e['files'])}
        self.assertEqual(notices, {'flashinfer-cubin', 'model-hosting-container-standards'})


class Proposals(unittest.TestCase):
    def setUp(self):
        self.rows = {r['artifact'].split('-')[0]: r for r in load_csv(Q.OUT_CSV)}

    def test_cufile_and_nvjitlink_are_an_applicability_discrepancy(self):
        for prefix in ('nvidia_cufile_cu12', 'nvidia_nvjitlink_cu12'):
            with self.subTest(prefix=prefix):
                row = self.rows[prefix]
                self.assertEqual(row['proposed_disposition'], 'needs_qualified_review')
                self.assertIn('applicability discrepancy', row['group'])
                self.assertIn('official CUDA 12.8.1', row['rationale'])

    def test_cutlass_is_not_dropped_for_an_unused_inference_path(self):
        row = self.rows['nvidia_cutlass_dsl_libs_base']
        self.assertIn('flashinfer-python', row['rationale'])
        self.assertIn('quack-kernels', row['rationale'])
        self.assertIn('explicitly revised dependency set', row['alternative_if_not_cleared'])
        self.assertIn('never because an inference path seems not to use it', row['alternative_if_not_cleared'])

    def test_kaggle_image_libraries_are_a_new_runtime_revision(self):
        self.assertIn('new runtime revision', Q.NVIDIA_ALTERNATIVE)
        self.assertIn('never a silent substitution', Q.NVIDIA_ALTERNATIVE)

    def test_every_row_has_a_proposal_and_none_is_bulk_approved(self):
        rows = list(self.rows.values())
        self.assertEqual(len(rows), 174)
        self.assertTrue({r['proposed_disposition'] for r in rows} <= Q.PROPOSED_VALUES)
        self.assertNotIn('approved', {r['proposed_disposition'] for r in rows})

    def test_batch_two_rule(self):
        base = {'artifact': 'x-1.0-py3-none-any.whl', 'licence_documents': 'x-1.0.dist-info/LICENSE'}
        agree = Q.unflagged_proposal(dict(base, metadata_declared='MIT', detected_families='MIT'))
        self.assertEqual(agree['proposed_disposition'], 'approved_with_conditions')
        missing = Q.unflagged_proposal(dict(base, metadata_declared='Apache-2.0 AND CNRI-Python',
                                            detected_families='Apache-2.0'))
        self.assertEqual(missing['proposed_disposition'], 'needs_qualified_review')
        choice = Q.unflagged_proposal(dict(base, metadata_declared='Apache-2.0 OR BSD-3-Clause',
                                           detected_families='Apache-2.0'))
        self.assertEqual(choice['proposed_disposition'], 'approved_with_conditions')
        self.assertIn('NOTICE', choice['questions_for_reviewer'])
        undeclared = Q.unflagged_proposal(dict(base, metadata_declared='', detected_families='Apache-2.0'))
        self.assertEqual(undeclared['proposed_disposition'], 'needs_qualified_review')
        self.assertEqual(Q.declared_families('BSD; OSI Approved :: BSD License'), (['BSD-any'], 'AND'))


if __name__ == '__main__':
    unittest.main()
