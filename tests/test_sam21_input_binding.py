"""Pre-install input binding regressions; no Torch/model import or inference."""
import json
from pathlib import Path
import tempfile
import unittest

from certification.phase4_multimodal_preflight_v3.images import png
from research.object_discovery_boundaries_v1.reference_audit import canonical,digest
from scripts import run_sam21_retained_seeds as R


class InputBinding(unittest.TestCase):
    def test_rehashed_swapped_or_changed_png_refused_before_checkpoint_or_output(self):
        for mutation in ('swap','replace','seed_hash'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);inputs=root/'inputs';inputs.mkdir();frames=[]
                for i in range(1,7):
                    case=f'board-{i:02d}';grid=[[i]*64 for _ in range(64)];raw=png(grid,cell=7)
                    (inputs/(case+'.png')).write_bytes(raw)
                    frames.append(dict(case_id=case,image_sha256=digest(raw),points=[],source_response_valid=True))
                if mutation=='swap':
                    a,b=inputs/'board-01.png',inputs/'board-02.png';x,y=a.read_bytes(),b.read_bytes()
                    a.write_bytes(y);b.write_bytes(x)
                elif mutation=='replace':(inputs/'board-01.png').write_bytes(png([[8]*64 for _ in range(64)],cell=7))
                else:frames[0]['image_sha256']='a'*64
                (inputs/'seeds.json').write_bytes(canonical(dict(frames=frames)))
                # Recompute every local hash, including the policy's manifest pin.
                manifest=canonical({p.name:digest(p.read_bytes()) for p in inputs.iterdir()})
                (inputs/'manifest.json').write_bytes(manifest)
                policy=dict(policy=R.S.POLICY,execution_device='cpu',dtype='float32',threads=4,
                    total_worker_seconds=1200,per_frame_seconds=240,references_available_to_inference=False,
                    adapter_sha256=digest((R.ROOT/'research/object_discovery_boundaries_v1/sam21.py').read_bytes()),
                    seed_manifest_sha256=digest(manifest))
                path=root/'policy.json';path.write_bytes(canonical(policy))
                with self.assertRaisesRegex(ValueError,'seed/image binding differs'):
                    R.run(inputs,root/'unused-checkpoint',root/'unused-acquisition',path,root/'output')
                self.assertFalse((root/'output').exists())


if __name__=='__main__':unittest.main()
