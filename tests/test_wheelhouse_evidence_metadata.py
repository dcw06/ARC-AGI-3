"""Declared-licence discrepancies pack (offline): the helpers behave on synthetic inputs, and the committed pack covers
exactly ninja, regex and prometheus_client with an allowed classification, intact retained sources, and retained
licence texts that carry the licence each finding relies on."""
import hashlib
import json
import struct
import unittest
from pathlib import Path

from scripts import evidence_metadata as M

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'reports/wheelhouse_evidence'
DISTRIBUTIONS = ['ninja', 'regex', 'prometheus_client']


class LicenceSignals(unittest.TestCase):
    def test_bsd_wording_in_a_comment_block_and_its_variant(self):
        header = ('/*\n * Copyright (C) 2024 Someone\n *\n * Redistribution and use in source and binary forms, with '
                  'or without\n * modification, are permitted provided that the following conditions are\n * met:\n */')
        self.assertEqual(M.licence_signals(header)['text'], ['BSD-2-Clause-style'])
        three = header + '\n * Neither the name of the copyright holder nor the names of its contributors may be used'
        self.assertEqual(M.licence_signals(three)['text'], ['BSD-3-Clause-style'])

    def test_platform_macros_are_not_licence_signals(self):
        signals = M.licence_signals('// ppoll() exists on FreeBSD\n#if defined(__FreeBSD__)\n#include <x.h>\n#endif\n')
        self.assertFalse(M.any_signal(signals))

    def test_cnri_statement_across_comment_lines_is_a_reference_not_a_text(self):
        python = ("# This version of the SRE library can be redistributed under CNRI's\n"
                  '# Python 1.6 license.  For any other use, please contact Secret Labs\n')
        c_source = python.replace('# ', ' * ')
        for text in (python, c_source):
            signals = M.licence_signals(text)
            self.assertEqual(signals['reference'], ['CNRI-Python'])
            self.assertEqual(signals['text'], [])
        self.assertEqual(M.licence_signals('CNRI OPEN SOURCE LICENSE AGREEMENT\n\nIMPORTANT')['text'], ['CNRI-Python'])
        self.assertEqual(M.licence_signals('CNRI LICENSE AGREEMENT FOR PYTHON 1.6.1\n---')['text'], ['CNRI-Python'])

    def test_apache_mit_spdx_and_classifier_references(self):
        apache = ('                                 Apache License\n                           Version 2.0, January 2004\n'
                  '   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION\n')
        self.assertEqual(M.licence_signals(apache), {'text': ['Apache-2.0'], 'reference': ['Apache-2.0'], 'spdx': []})
        mit = ('// Licensed under the MIT License <http://opensource.org/licenses/MIT>.\n'
               '// SPDX-License-Identifier: MIT\n// Permission is hereby granted, free of charge, to any person\n')
        self.assertEqual(M.licence_signals(mit), {'text': ['MIT'], 'reference': ['MIT'], 'spdx': ['MIT']})
        classifier = 'Classifier: License :: OSI Approved :: BSD License\n'
        self.assertEqual(M.licence_signals(classifier)['reference'], ['BSD (variant not named)'])
        notice = 'This product bundles decorator 4.0.10 which is available under a "2-clause BSD"\nlicense.'
        self.assertEqual(M.licence_signals(notice)['reference'], ['BSD-2-Clause'])
        self.assertEqual(M.licence_signals('license = "Apache-2.0 AND CNRI-Python"')['reference'],
                         ['Apache-2.0', 'CNRI-Python'])


class Helpers(unittest.TestCase):
    def test_leading_comment_blocks(self):
        self.assertEqual(M.leading_comment('/* a\n * b\n */\nint x;\n'), (1, 3))
        self.assertEqual(M.leading_comment('#!/usr/bin/python\n\n# Copyright\n#\n# Licensed\n\n"""doc"""\n'), (3, 5))
        self.assertEqual(M.leading_comment('# LICENSE\n\n# Copyright\n# DAMAGE.\n\n"""doc"""\n'), (1, 4))
        self.assertEqual(M.leading_comment('// one\n// two\n#pragma once\n'), (1, 2))
        self.assertIsNone(M.leading_comment('import os\n# late comment\n'))
        self.assertIsNone(M.leading_comment('/* never closed\n'))

    def test_excerpt(self):
        self.assertEqual(M.excerpt('a\nb\nc\nd\n', (2, 3)), 'b\nc\n')

    def test_declared_fields_ignore_the_description(self):
        metadata = ('Metadata-Version: 2.4\nName: x\nLicense-Expression: Apache-2.0 AND BSD-2-Clause\n'
                    'Classifier: License :: OSI Approved :: BSD License\nClassifier: Typing :: Typed\n'
                    'License-File: LICENSE\n\nLicense: words in the description\n')
        self.assertEqual(M.declared_fields(metadata), ['License-Expression: Apache-2.0 AND BSD-2-Clause',
                                                       'Classifier: License :: OSI Approved :: BSD License',
                                                       'License-File: LICENSE'])

    def test_classify(self):
        self.assertEqual(M.classify(True, True, True), 'explained')
        self.assertEqual(M.classify(True, None, True), 'partially_explained')
        self.assertEqual(M.classify(True, True, False), 'partially_explained')
        self.assertEqual(M.classify(False, True, True), 'unexplained')
        self.assertEqual(set(M.CLASSIFICATIONS), {'explained', 'partially_explained', 'unexplained'})

    def test_include_closure(self):
        sources = {'src/a.cc': '#include "hash_map.h"\n#include "build/browse_py.h"\n',
                   'src/hash_map.h': '#include <string>\n#include "third_party/r/r.h"\n',
                   'src/third_party/r/r.h': '#include <stdint.h>\n',
                   'src/b.cc': '#include "util.h"\n', 'src/util.h': ''}
        self.assertEqual(M.include_closure(sources, 'src/a.cc'),
                         {'src/a.cc', 'src/hash_map.h', 'src/third_party/r/r.h'})
        self.assertEqual(M.include_closure(sources, 'src/b.cc'), {'src/b.cc', 'src/util.h'})

    def test_cmake_linux_sources(self):
        cmake = ('add_library(libninja-re2c OBJECT ${PROJECT_BINARY_DIR}/lexer.cc)\nelse()\n'
                 'add_library(libninja-re2c OBJECT src/lexer.cc)\nendif()\n'
                 'add_library(libninja OBJECT\n\tsrc/build.cc\n\tsrc/util.cc\n)\nif(WIN32)\n'
                 '\ttarget_sources(libninja PRIVATE\n\t\tsrc/subprocess-win32.cc\n\t\tsrc/getopt.c\n\t)\nelse()\n'
                 '\ttarget_sources(libninja PRIVATE\n\t\tsrc/subprocess-posix.cc\n\t)\n'
                 '\tif(CMAKE_SYSTEM_NAME STREQUAL "AIX")\n\t\ttarget_sources(libninja PRIVATE src/getopt.c)\n'
                 '\tendif()\nendif()\nadd_executable(ninja src/ninja.cc)\n'
                 'target_sources(ninja PRIVATE windows/ninja.manifest)\ntarget_sources(ninja PRIVATE src/browse.cc)\n')
        self.assertEqual(M.cmake_linux_sources(cmake), ['src/browse.cc', 'src/build.cc', 'src/lexer.cc',
                                                        'src/ninja.cc', 'src/subprocess-posix.cc', 'src/util.cc'])

    def test_binary_helpers(self):
        value = 0x2d358dccaa6c78a5
        self.assertEqual(M.count_u64(b'xx' + struct.pack('<Q', value) * 2 + b'yy', value), 2)
        data = b'\x00\x01 RE 2.3.0 Copyright (c) 1997-2002 by Secret Labs AB \x00ninja: build stopped\x00FreeBSD\x00'
        self.assertEqual(M.compiled_markers(data), ['RE 2.3.0 Copyright (c) 1997-2002 by Secret Labs AB'])
        self.assertTrue(M.is_text(b'plain'))
        self.assertFalse(M.is_text(b'\x7fELF\x00\x00'))


class CommittedPack(unittest.TestCase):
    def setUp(self):
        self.pack = json.loads((EVIDENCE / 'metadata_discrepancies.json').read_text(encoding='utf-8'))
        self.wheels = {w['distribution']: w for w in self.pack['wheels']}
        self.retained = {r['file']: r for r in self.pack['retained_sources']}

    def test_covers_exactly_the_three_wheels_with_allowed_classifications(self):
        self.assertEqual([w['distribution'] for w in self.pack['wheels']], DISTRIBUTIONS)
        self.assertIn('not a decision', self.pack['status'])
        for w in self.pack['wheels']:
            self.assertIn(w['classification'], M.CLASSIFICATIONS)
            if w['classification'] == 'explained':
                self.assertIs(w['component']['ships_in_wheel'], True)
                self.assertTrue(w['licence_text_location']['retained'])
            self.assertTrue(w['proposed_obligation'])
            self.assertTrue(w['uncertainty'])

    def test_wheels_are_the_approved_artifacts(self):
        manifest = json.loads((ROOT / 'reports/wheelhouse_download_manifest.json').read_text(encoding='utf-8'))
        approved = {a['filename']: a['sha256'] for a in manifest['artifacts']}
        for w in self.pack['wheels']:
            self.assertEqual(approved[w['wheel']['artifact']], w['wheel']['sha256'])
            self.assertTrue(w['sdist']['verified_against_pypi'])

    def test_retained_sources_match_their_hashes_and_naming(self):
        self.assertEqual(len(self.retained), len(self.pack['retained_sources']))
        for name, record in self.retained.items():
            self.assertTrue(any(name.startswith(f'sources/metadata-{d}-') for d in DISTRIBUTIONS), name)
            data = (EVIDENCE / name).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), record['sha256'], name)
            self.assertEqual(len(data), record['bytes'], name)
        for w in self.pack['wheels']:
            for name in w['licence_text_location']['retained']:
                self.assertIn(name, self.retained)

    def test_retained_licence_texts_carry_the_licence_relied_on(self):
        def text_families(name):
            return M.licence_signals((EVIDENCE / name).read_text(encoding='utf-8'))['text']
        self.assertIn('BSD-2-Clause-style', text_families('sources/metadata-ninja-rapidhash-licence-header.txt'))
        self.assertIn('MIT', text_families('sources/metadata-ninja-emhash-licence-header.txt'))
        self.assertIn('CNRI-Python', text_families('sources/metadata-regex-spdx-v3.27.0-CNRI-Python.txt'))
        self.assertIn('CNRI-Python', text_families('sources/metadata-regex-cpython-v3.1-LICENSE.txt'))
        self.assertIn('BSD-2-Clause-style',
                      text_families('sources/metadata-prometheus_client-decorator-licence-header.txt'))
        self.assertIn('CNRI-Python', M.licence_signals((EVIDENCE / 'sources/metadata-regex-_regex.c-licence-header.txt')
                                                       .read_text(encoding='utf-8'))['reference'])

    def test_component_files_ship_in_the_wheel(self):
        ninja = self.wheels['ninja']
        self.assertEqual(ninja['component']['shipped_as']['path'], M.NINJA_BINARY)
        self.assertTrue(all(ninja['binary_evidence']['rapidhash_secret_occurrences'].values()))
        self.assertTrue(ninja['binary_evidence']['kNinjaVersion_embedded_in_binary'])
        regex_paths = {f['path'] for f in self.wheels['regex']['component']['files_in_wheel']}
        self.assertTrue({'regex/_main.py', 'regex/_regex_core.py'} <= regex_paths)
        prom = self.wheels['prometheus_client']['component']
        self.assertEqual([f['path'] for f in prom['files_in_wheel']], ['prometheus_client/decorator.py'])
        self.assertTrue(prom['notice_points_to_it'])

    def test_markdown_states_status_and_every_wheel(self):
        text = (EVIDENCE / 'metadata_discrepancies.md').read_text(encoding='utf-8')
        self.assertIn('a proposal, not a decision', text)
        for w in self.pack['wheels']:
            self.assertIn(f"## {w['distribution']} {w['version']}", text)
            self.assertIn(f"**Classification: {w['classification']}**", text)


if __name__ == '__main__':
    unittest.main()
