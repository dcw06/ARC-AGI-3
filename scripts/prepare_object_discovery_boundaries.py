"""Prepare a new private CPU-only object-discovery draft; no model execution."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from research.object_discovery_boundaries_v1.prepare import prepare
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--output',required=True)
    p.add_argument('--prompt-profile',choices=['legacy_whole_v1','detailed_whole_v2'],default='legacy_whole_v1')
    a=p.parse_args();print(json.dumps(prepare(a.source,a.output,prompt_profile=a.prompt_profile),indent=2))
