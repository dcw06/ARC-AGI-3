"""Offline checks of the native-library provenance pack (scripts/evidence_native.py): parsing and classification
rules on synthetic inputs, and consistency of the committed pack with its retained sources and the local wheels."""
import hashlib
import json
import re
import struct
import unittest

from scripts import evidence_native as N
from scripts.evidence_common import EVIDENCE, WHEELHOUSE, artifact_for, open_wheel

PACK = EVIDENCE / 'native_libraries.json'
DISTRIBUTIONS = ('opencv_python_headless', 'pillow', 'pyzmq')


def tlv(tag, body):
    n = len(body)
    if n < 0x80:
        return bytes([tag, n]) + body
    size = (n.bit_length() + 7) // 8
    return bytes([tag, 0x80 | size]) + n.to_bytes(size, 'big') + body


def oid_bytes(text):
    parts = [int(x) for x in text.split('.')]
    out = bytes([parts[0] * 40 + parts[1]])
    for part in parts[2:]:
        chunk = [part & 0x7F]
        part >>= 7
        while part:
            chunk.append(0x80 | (part & 0x7F))
            part >>= 7
        out += bytes(reversed(chunk))
    return out


def synthetic_elf():
    """A minimal ELF64 LE image with .dynstr/.dynamic/.comment/.gnu_debuglink section headers."""
    shstr = b'\0.shstrtab\0.dynstr\0.dynamic\0.comment\0.gnu_debuglink\0'
    dynstr = b'\0libfoo.so.1\0libc.so.6\0libbar-1234abcd.so.2.0.0\0'
    dynamic = b''.join(struct.pack('<qQ', tag, dynstr.index(name) if name else 0)
                       for tag, name in ((1, b'libfoo.so.1'), (1, b'libc.so.6'), (14, b'libbar'), (0, None)))
    blobs = [('.shstrtab', shstr), ('.dynstr', dynstr), ('.dynamic', dynamic),
             ('.comment', b'GCC: (GNU) 14.2.1\0GCC: (GNU) 8.5.0\0'),
             ('.gnu_debuglink', b'libbar.so.2.0.0-2.0.0-1.el8.x86_64.debug\0\0\0\0\0\0\0\0')]
    data, offsets = bytearray(64), {}
    for name, blob in blobs:
        offsets[name] = len(data)
        data += blob
    shoff = len(data)
    data += struct.pack('<IIQQQQIIQQ', *([0] * 10))
    for name, blob in blobs:
        data += struct.pack('<IIQQQQIIQQ', shstr.index(name.encode()), 1, 0, 0, offsets[name], len(blob), 0, 0, 1, 0)
    data[:64] = (b'\x7fELF' + bytes([2, 1, 1]) + bytes(9) +
                 struct.pack('<HHIQQQIHHHHHH', 3, 62, 1, 0, 0, shoff, 0, 64, 56, 0, 64, len(blobs) + 1, 1))
    return bytes(data)


def walk_records(node):
    """Every retained-source provenance record (has 'file' under sources/ and a sha256) anywhere in the pack."""
    if isinstance(node, dict):
        if isinstance(node.get('file'), str) and node['file'].startswith('sources/') and 'sha256' in node:
            yield node
        for value in node.values():
            yield from walk_records(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk_records(value)


class Helpers(unittest.TestCase):
    def test_libtool_suffix(self):
        self.assertEqual(N.libtool_suffix('7:5:2'), '5.2.5')     # libzmq v4.3.5 LTVER
        self.assertEqual(N.libtool_suffix('26:6:20'), '6.20.6')  # FreeType 2.14.3 version_info
        self.assertEqual(N.libtool_suffix('2:18:0'), '2.0.18')

    def test_so_suffix_is_only_a_clue_extractor(self):
        self.assertEqual(N.so_suffix('pyzmq.libs/libzmq-7b073b3d.so.5.2.5'), '5.2.5')
        self.assertEqual(N.so_suffix('x.libs/libcrypto-bdaed0ea.so.1.1.1k'), '1.1.1k')
        self.assertIsNone(N.so_suffix('x.libs/libopenblasp-r0-59ffcd50.3.15.so'))

    def test_pin_line(self):
        text = '#!/bin/bash\n# comment\nFREETYPE_VERSION=2.14.3\nHARFBUZZ_VERSION=13.2.1\n'
        self.assertEqual(N.pin_line(text, r'^HARFBUZZ_VERSION=(\S+)'),
                         {'line': 4, 'text': 'HARFBUZZ_VERSION=13.2.1', 'value': '13.2.1'})
        self.assertIsNone(N.pin_line(text, r'^ZSTD_VERSION=(\S+)'))
        multi = 'a\nLIBRARY_CURRENT=2\nLIBRARY_REVISION=18\nLIBRARY_AGE=0\n'
        found = N.pin_line(multi, r'^LIBRARY_CURRENT=(\d+)\s+LIBRARY_REVISION=(\d+)\s+LIBRARY_AGE=(\d+)')
        self.assertEqual((found['line'], found['value']), (2, '2:18:0'))
        self.assertEqual(N.pin_line('  ./configure --x \\\n', r'(\./configure .*)')['value'], './configure --x')

    def test_expand(self):
        self.assertEqual(N.expand('https://x/ffmpeg-${FFMPEG_VERSION}.tar.gz', {'FFMPEG_VERSION': '8.0.1'}),
                         'https://x/ffmpeg-8.0.1.tar.gz')
        self.assertEqual(N.expand('v$ZSTD_VERSION/$OTHER', {'ZSTD_VERSION': '1.5.7'}), 'v1.5.7/$OTHER')

    def test_checksum_lines(self):
        self.assertEqual(N.checksum_lines('curl -O https://a/b.tar.gz\nmake\n'), [])
        self.assertEqual([f['line'] for f in N.checksum_lines('X=1\necho abc  b.tar.gz | sha256sum -c\n')], [2])

    def test_rpm_build_from_debuglink(self):
        self.assertEqual(N.rpm_build('libcrypto.so.1.1.1k-1.1.1k-14.el8_6.x86_64.debug'),
                         ('libcrypto.so.1.1.1k', '1.1.1k-14.el8_6'))
        self.assertEqual(N.rpm_build('libopenblasp-r0.3.15.so-0.3.15-6.el8.x86_64.debug'),
                         ('libopenblasp-r0.3.15.so', '0.3.15-6.el8'))
        self.assertEqual(N.rpm_build('libgfortran.so.5.0.0-8.5.0-28.el8_10.alma.1.x86_64.debug')[1],
                         '8.5.0-28.el8_10.alma.1')
        self.assertIsNone(N.rpm_build('libfoo.so.debug'))
        self.assertIsNone(N.rpm_build(None))

    def test_ffmpeg_licence_label(self):
        self.assertEqual(N.ffmpeg_licence(['--enable-openssl', '--enable-libvpx', '--enable-shared']),
                         'LGPL version 2.1 or later')
        self.assertEqual(N.ffmpeg_licence(['--enable-gpl']), 'GPL version 2 or later')
        self.assertEqual(N.ffmpeg_licence(['--enable-version3']), 'LGPL version 3 or later')
        self.assertEqual(N.ffmpeg_licence(['--enable-gpl', '--enable-version3']), 'GPL version 3 or later')
        self.assertEqual(N.ffmpeg_licence(['--enable-gpl', '--enable-nonfree']), 'nonfree and unredistributable')

    def test_chain_status(self):
        full = dict(commit='attested', pin='explicit', source='upstream_url_with_checksum', environment='same_run',
                    corroboration='embedded_version')
        self.assertEqual(N.chain_status(**full), ('complete', []))
        status, missing = N.chain_status(**dict(full, source='upstream_url'))  # a URL without a checksum
        self.assertEqual(status, 'partial')
        self.assertTrue(any('no checksum pinned' in m for m in missing))
        self.assertEqual(N.chain_status(**dict(full, commit='tag_resolved'))[0], 'complete')
        self.assertEqual(N.chain_status(**dict(full, corroboration='libtool_mapping'))[0], 'complete')
        status, missing = N.chain_status(**dict(full, environment='prebuilt_image'))
        self.assertEqual((status, len(missing)), ('partial', 1))
        self.assertEqual(N.chain_status(**dict(full, source='unpinned_mirror'))[0], 'partial')
        self.assertEqual(N.chain_status(**dict(full, corroboration=None))[0], 'partial')
        self.assertEqual(N.chain_status(**dict(full, commit=None))[0], 'partial')
        self.assertEqual(N.chain_status(**dict(full, pin='package_named', source='distro_srpm',
                                               corroboration='package_build_id'))[0], 'partial')
        self.assertEqual(N.chain_status(**dict(full, pin='package_transitive'))[0], 'clue_only')
        self.assertEqual(N.chain_status(**dict(full, pin=None))[0], 'clue_only')

    def test_der_extensions(self):
        def ext(oid, value):
            return tlv(0x30, tlv(0x06, oid_bytes(oid)) + tlv(0x04, value))
        long_uri = b'https://github.com/o/r/.github/workflows/w.yml@refs/tags/1' * 3
        cert = tlv(0x30, tlv(0x30, tlv(0xA3, tlv(0x30,
                   ext('1.3.6.1.4.1.57264.1.13', tlv(0x0C, b'3c41c09506')) +
                   ext('1.3.6.1.4.1.57264.1.5', b'python-pillow/Pillow') +
                   tlv(0x30, tlv(0x06, oid_bytes('2.5.29.15')) + tlv(0x01, b'\xff') + tlv(0x04, b'\x03\x02\x07\x80')) +
                   ext('1.3.6.1.4.1.57264.1.18', tlv(0x0C, long_uri))))))
        claims = N.der_extensions(cert)
        self.assertEqual(claims['1.3.6.1.4.1.57264.1.13'], '3c41c09506')
        self.assertEqual(claims['1.3.6.1.4.1.57264.1.5'], 'python-pillow/Pillow')
        self.assertEqual(claims['1.3.6.1.4.1.57264.1.18'], long_uri.decode())
        self.assertNotIn('2.5.29.15', claims)

    def test_elf_dynamic(self):
        info = N.elf_dynamic(synthetic_elf())
        self.assertEqual(info['soname'], 'libbar-1234abcd.so.2.0.0')
        self.assertEqual(info['needed'], ['libfoo.so.1', 'libc.so.6'])
        self.assertEqual(info['compiler_comment'], ['GCC: (GNU) 14.2.1', 'GCC: (GNU) 8.5.0'])
        self.assertEqual(N.rpm_build(info['debuglink']), ('libbar.so.2.0.0', '2.0.0-1.el8'))
        self.assertIsNone(N.elf_dynamic(b'not an elf at all' * 8))

    def test_version_patterns(self):
        pats = N.version_patterns([r'\x00{vn}\x00', r'libvpx {v}'], 'v1.15.2')
        self.assertTrue(re.search(pats[0], b'x\x001.15.2\x00y'))
        self.assertFalse(re.search(pats[0], b'x\x0011.15.2\x00y'))
        self.assertTrue(re.search(pats[1], b'libvpx v1.15.2'))

    def test_shell_list(self):
        text = 'A="\n    x\n"\nEXTERNAL_LIBRARY_NONFREE_LIST="\n    decklink\n    libfdk_aac\n"\n'
        self.assertEqual(N.shell_list(text, 'EXTERNAL_LIBRARY_NONFREE_LIST'), ['decklink', 'libfdk_aac'])
        self.assertIsNone(N.shell_list(text, 'MISSING'))


@unittest.skipUnless(PACK.exists(), 'native_libraries.json not generated')
class CommittedPack(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack = json.loads(PACK.read_text(encoding='utf-8'))
        cls.wheels = {w['distribution']: w for w in cls.pack['wheels']}

    def test_covers_the_three_exact_wheels(self):
        self.assertEqual(set(self.wheels), set(DISTRIBUTIONS))
        for distribution, wheel in self.wheels.items():
            artifact = artifact_for(distribution)
            self.assertEqual((wheel['artifact'], wheel['sha256']), (artifact['filename'], artifact['sha256']))
            self.assertIn(wheel['build_commit']['status'], ('attested', 'tag_resolved'))
            self.assertRegex(wheel['build_commit']['commit'], r'^[0-9a-f]{40}$')

    def test_every_bundled_library_has_a_chain_status(self):
        for distribution, wheel in self.wheels.items():
            statuses = {r['path']: c['chain_status'] for c in wheel['components'] for r in c['files']}
            self.assertTrue(wheel['bundled_libraries'], distribution)
            self.assertEqual(set(statuses), set(wheel['bundled_libraries']), distribution)
            self.assertEqual(wheel['unassigned_bundled_libraries'], [])
            for path, status in statuses.items():
                self.assertIn(status, N.STATUSES, path)

    def test_status_follows_recorded_links(self):
        for wheel in self.wheels.values():
            for c in wheel['components']:
                links = c['chain_links']
                self.assertEqual(N.chain_status(links['build_commit'], links['pin'], links['source'],
                                                links['build_environment'], links['corroboration']),
                                 (c['chain_status'], c['missing_links']), c['key'])

    def test_local_wheel_listing_matches_pack(self):
        for distribution, wheel in self.wheels.items():
            artifact = artifact_for(distribution)
            if not (WHEELHOUSE / artifact['filename']).exists():
                self.skipTest('local wheelhouse not available')
            z = open_wheel(artifact)
            listing = {n for n in z.namelist() if '.libs/' in n and not n.endswith('/')}
            self.assertEqual(listing, set(wheel['bundled_libraries']), distribution)
            for c in wheel['components']:
                for r in c['files']:
                    self.assertEqual(hashlib.sha256(z.read(r['path'])).hexdigest(), r['sha256'], r['path'])

    def test_retained_sources_match_their_hashes(self):
        records = list(walk_records(self.pack))
        self.assertGreater(len(records), 20)
        for record in records:
            path = EVIDENCE / record['file']
            self.assertTrue(path.name.startswith('native-'), path)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record['sha256'], path)

    def test_ffmpeg_configure_flags_and_licence_logic(self):
        f = self.wheels['opencv_python_headless']['ffmpeg_licence_logic']
        self.assertEqual(f['licence_relevant_flags_present'], [])
        self.assertTrue(f['embedded_equals_dockerfile'])
        self.assertEqual(f['embedded_licence_strings'], ['LGPL version 2.1 or later'])
        self.assertEqual(f['label_from_flags'], 'LGPL version 2.1 or later')
        self.assertFalse(any(f['openssl_in_lists'].values()))
        configure = (EVIDENCE / f['configure_retained']['file']).read_text(encoding='utf-8')
        self.assertIn('license="LGPL version 2.1 or later"', configure)

    def test_markdown_written(self):
        md = (EVIDENCE / 'native_libraries.md').read_text(encoding='utf-8')
        self.assertIn('not a decision', md)
        for distribution in DISTRIBUTIONS:
            self.assertIn(f'## {distribution}', md)


if __name__ == '__main__':
    unittest.main()
