"""Synthetic binding regressions; never uploads, reserves or loads a model."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts import build_molmopoint_live as B


class LiveBuilder(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.base = Path(temp.name); self.previous = self.base/'previous'; self.previous.mkdir()
        self.datasets = [dict(kind=k,ref='owner/'+k,version=1,files=[
            dict(name='f'+str(i),bytes=i,sha256='a'*64) for i in range(n)])
            for k,n in [('wheelhouse',177),('model',33),('inputs',9)]]
        def raw(value): return B.canonical(value)
        source = 'research/molmopoint_identification_v1/__init__.py'
        runtime = {'protocol.json':raw({'datasets':self.datasets}),
                   'reviewed-source/'+source:(B.ROOT/source).read_bytes()}
        runtime['runtime-lock.json'] = raw({'artifacts':{n:B.D.digest(v) for n,v in runtime.items()}})
        files = {'runtime/'+n:v for n,v in runtime.items()}
        files.update({'profile.ipynb':raw({'cells':[
            dict(cell_type='code',id='launch-authority',source=['AUTHORITY = None\n']),
            dict(cell_type='code',id='bootstrap',source=['pass\n'])]}),
            'kernel-metadata.json':raw({'id':'owner/probe','title':'Probe','docker_image':'synthetic@sha256:pin'}),
            'evaluation-binding.json':raw({'source_sha256':{}})})
        for n,v in files.items(): self.write(self.previous/n,v,raw=True)
        self.write(self.previous/'review-lock.json',{'artifacts':{n:B.D.digest(v) for n,v in files.items()}})
        model = dict(self.datasets[1]); model['files'] = list(model['files'])
        licence = (B.ROOT/'research/molmopoint_identification_v1/LICENSE-APACHE-2.0.txt').read_bytes()
        model['files'].append(dict(name='LICENSE-APACHE-2.0.txt',bytes=len(licence),sha256=B.D.digest(licence)))
        items = [dict(d,expected_private=True,expected_collaborators=0) for d in (model,self.datasets[2])]
        self.plan = self.base/'plan.json'; self.write(self.plan,{'datasets':items})
        self.receipts = {}
        for d in items:
            p = self.base/(d['kind']+'.json'); self.receipts[d['kind']] = p
            self.write(p,dict(ref=d['ref'],provider_writes=0,checks=dict(
                current=dict(ref=d['ref'],private=True,version=1),
                metadata=dict(private=True,collaborators=0,error=False),status='ready',
                inventory=dict(files={r['name']:r['bytes'] for r in d['files']},error=False,has_next_page=False,matches=True))))
        self.validation = self.base/'validation.json'
        names = [source,'scripts/build_molmopoint_live.py'] + [
            'research/molmopoint_identification_v1/'+n+'.py' for n in ('deployment','operations','operator','kaggle_operator')]
        self.write(self.validation,dict(linux=dict(tests=1,failures=0,errors=0,skipped=0,returncode=0),
            source_sha256={n:B.D.digest((B.ROOT/n).read_bytes()) for n in names},evidence_sha256={}))
        self.amendment = self.base/'amendment.json'
        self.write(self.amendment,dict(approved_time_policy_change=True,accepted_provider_overhead=True,
            session_timeout_seconds=3600,worker_seconds=3300,owner_answer='SYNTHETIC TEST ONLY'))
        self.known = self.base/'known.json'; self.write(self.known,{'target':'owner/known'})

    def write(self,p,v,*,raw=False):
        p.parent.mkdir(parents=True,exist_ok=True); p.write_bytes(v if raw else B.canonical(v))

    def build(self,name='live'):
        return B.build(self.previous,self.plan,self.receipts,self.validation,self.amendment,self.known,self.base/name)

    def test_reproducible_live_template_keeps_authority_empty(self):
        first = self.build(); second = self.build('again')
        self.assertEqual(first['review_lock_sha256'],second['review_lock_sha256'])
        package = self.base/'live'
        self.assertIsNone(B.D.authority_from(json.loads((package/'profile.ipynb').read_bytes())))
        self.assertEqual(json.loads((package/'runtime/protocol.json').read_bytes())['scope']['max_tokens_per_generation'],1024)
        self.assertEqual(json.loads((package/'launch-spec.json').read_bytes())['save_fields']['machine_shape'],'NvidiaRtxPro6000')
        with self.assertRaisesRegex(ValueError,'missing'):
            B.D.verify_authority(package,None)

    def test_inventory_claim_cannot_change_frozen_weight_or_prompt_hashes(self):
        plan = json.loads(self.plan.read_bytes()); plan['datasets'][0]['files'][0]['sha256'] = 'b'*64
        self.write(self.plan,plan)
        with self.assertRaisesRegex(ValueError,'differs from frozen'): self.build()

    def test_unverified_or_shared_dataset_refuses_before_build(self):
        p = self.receipts['model']; original = json.loads(p.read_bytes())
        for key,value in [('private',False),('collaborators',1)]:
            changed = json.loads(json.dumps(original)); changed['checks']['metadata'][key] = value
            self.write(p,changed)
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'verification incomplete'): self.build()
        self.assertFalse((self.base/'live').exists())

    def test_validation_must_cover_current_builder_and_operator(self):
        value = json.loads(self.validation.read_bytes()); value['source_sha256'] = {}
        self.write(self.validation,value)
        with self.assertRaisesRegex(ValueError,'complete current'): self.build()


if __name__ == '__main__': unittest.main()
