"""Synthetic package-isolation tests; no weights, provider or compute."""
import base64
import json
from pathlib import Path
import tempfile
import unittest
from scripts import build_object_boundary_live as B
from tests import test_object_boundary_preparation as preparation_fixture


class Builder(unittest.TestCase):
    def setUp(self):
        self.fixture=preparation_fixture.Preparation();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.previous=self.root/'previous';self.previous.mkdir()
        self.datasets=[dict(kind=k,ref='owner/'+k,version=1,files=[dict(name='f'+str(i),bytes=i,sha256='a'*64) for i in range(n)])
                       for k,n in [('wheelhouse',177),('model',34),('inputs',9)]]
        files={'runtime/protocol.json':B.canonical(dict(datasets=self.datasets)),
            'profile.ipynb':B.canonical(dict(cells=[dict(id='launch-authority',cell_type='code',source=['AUTHORITY = None\n']),
                                                dict(id='bootstrap',cell_type='code',source=['pass\n'])])),
            'kernel-metadata.json':B.canonical(dict(id='owner/old',title='old',docker_image='pinned')),
            'launch-spec.json':B.canonical(dict(save_fields=dict(slug='owner/old',new_title='old')))}
        for name,raw in files.items():self.write(self.previous/name,raw)
        self.write(self.previous/'review-lock.json',B.canonical(dict(artifacts={n:B.D.digest(r) for n,r in files.items()})))
        self.refs=self.root/'references';self.refs.mkdir()
        original=B.canonical(self.fixture.review)
        att=B.canonical(dict(export_sha256=B.D.digest(original)))
        review=dict(self.fixture.review,owner_confirmation_sha256=B.D.digest(att))
        refs={'original-owner-export.json':original,'owner-attestation.json':att,'confirmed-review.json':B.canonical(review)}
        for n,r in refs.items():self.write(self.refs/n,r)
        self.write(self.refs/'manifest.json',B.canonical({n:B.D.digest(r) for n,r in refs.items()}))
        context=dict(status='passed_read_only',provider_writes=0,new_target='owner/uncued',known_target='owner/old',datasets=[
            dict(kind=d['kind'],facts=dict(ref=d['ref'],version=1,private=True,ready=True,collaborators=0),
                 files={r['name']:r['bytes'] for r in d['files']},inventory=dict(passed=True)) for d in self.datasets])
        self.context=self.root/'context.json';self.write(self.context,B.canonical(context))
        names=[p.relative_to(B.ROOT).as_posix() for base in ('research/object_discovery_boundaries_v1','research/molmopoint_identification_v1',
            'research/object_identification_v1','certification/direct_publisher_smoke_v1','certification/phase4_multimodal_preflight_v3')
            for p in (B.ROOT/base).iterdir() if p.is_file()]
        names.append('scripts/build_object_boundary_live.py')
        self.validation=self.root/'validation.json'
        self.write(self.validation,B.canonical(dict(linux=dict(tests=1,failures=0,errors=0,skipped=0,returncode=0),
            source_sha256={n:B.D.digest((B.ROOT/n).read_bytes()) for n in names})))

    def write(self,path,raw):path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)

    def build(self,name='package'):
        return B.build(self.previous,self.fixture.prep,self.refs,self.context,self.validation,self.root/name)

    def test_reproducible_seal_keeps_masks_outside_payload_and_no_authority(self):
        a=self.build('a');b=self.build('b');self.assertEqual(a['review_lock_sha256'],b['review_lock_sha256'])
        package=self.root/'a';payload=json.loads((package/'runtime-payload.json').read_bytes())
        self.assertFalse(any('references' in n or 'scoring' in n or 'evaluation' in n for n in payload))
        binding=json.loads((package/'evaluation-binding.json').read_bytes())
        self.assertIn('research/object_discovery_boundaries_v1/experiment.py',binding['source_sha256'])
        self.assertEqual(sum(n.startswith('agent-inputs/') for n in payload),7)
        self.assertNotIn('reviewed-source/research/molmopoint_identification_v1/inference.py',payload)
        requests=base64.b64decode(payload['agent-inputs/requests.jsonl'])
        self.assertNotIn(b'Synthetic label',requests)
        self.assertTrue((package/'references/confirmed-review.json').exists())
        book=json.loads((package/'profile.ipynb').read_bytes());self.assertIsNone(B.D.authority_from(book))
        with self.assertRaisesRegex(SystemExit,'APPROVAL REQUIRED'):
            exec(compile(''.join(book['cells'][-1]['source']),'<review>','exec'),{'AUTHORITY':None})

    def test_changed_reference_manifest_is_refused(self):
        self.write(self.refs/'confirmed-review.json',b'{}')
        with self.assertRaisesRegex(ValueError,'reference manifest'):self.build()

    def test_detailed_profile_is_bound_in_runtime_and_replay(self):
        from research.object_discovery_boundaries_v1.prepare import prepare,requests_for
        from research.object_discovery_boundaries_v1.prompts import DETAILED_PROFILE,DETAILED_PROMPT
        detailed=self.fixture.base/'detailed-preparation'
        prepare(self.fixture.base/'source',detailed,prompt_profile=DETAILED_PROFILE)
        self.fixture.prep=detailed
        self.build('detailed')
        package=self.root/'detailed'
        protocol=json.loads((package/'runtime/protocol.json').read_bytes())
        self.assertEqual(protocol['prompt_profile'],DETAILED_PROFILE)
        self.assertEqual({r['prompt'] for r in requests_for(package/'runtime/agent-inputs',prompt_profile=DETAILED_PROFILE)},
                         {DETAILED_PROMPT})
        self.assertTrue((package/'runtime/reviewed-source/research/object_discovery_boundaries_v1/prompts.py').is_file())
        self.assertEqual(json.loads((package/'kernel-metadata.json').read_bytes())['title'],
                         'ARC3 MolmoPoint Generic Discovery V2')

    def test_changed_source_validation_is_refused(self):
        validation=json.loads(self.validation.read_bytes());validation['source_sha256']['scripts/build_object_boundary_live.py']='a'*64
        self.write(self.validation,B.canonical(validation))
        with self.assertRaisesRegex(ValueError,'verification stale'):self.build()

    def test_shared_dataset_is_refused_before_package_creation(self):
        context=json.loads(self.context.read_bytes());context['datasets'][1]['facts']['collaborators']=1
        self.write(self.context,B.canonical(context))
        with self.assertRaisesRegex(ValueError,'privacy/readiness'):self.build()

    def test_explicit_successor_title_must_match_new_target(self):
        context=json.loads(self.context.read_bytes())
        context.update(new_target='owner/generic-v2-r2',new_title='Generic V2 R2')
        self.write(self.context,B.canonical(context))
        self.build('successor')
        package=self.root/'successor'
        self.assertEqual(json.loads((package/'kernel-metadata.json').read_bytes())['title'],'Generic V2 R2')
        context['new_title']='An unrelated title'
        self.write(self.context,B.canonical(context))
        with self.assertRaisesRegex(ValueError,'title must match'):
            self.build('mismatched')


if __name__=='__main__':unittest.main()
