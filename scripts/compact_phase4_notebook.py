"""Losslessly re-encode embedded files; create a GPU-disabled packaging review."""
import argparse
import ast
import base64
import hashlib
import json
import lzma
from pathlib import Path
import zlib

MAX_NOTEBOOK_BYTES=900_000


def compact(notebook):
    result=json.loads(json.dumps(notebook))
    changed=0
    for cell in result['cells']:
        if cell['cell_type']!='code': continue
        code=cell['source']
        if not isinstance(code,str): raise ValueError('expected string source')
        tree=ast.parse(code)
        for node in ast.walk(tree):
            if not isinstance(node,ast.Assign) or not any(isinstance(t,ast.Name) and t.id=='payload' for t in node.targets):continue
            expression=ast.get_source_segment(code,node.value)
            if not expression.startswith('json.loads(zlib.decompress(base64.b64decode('):
                raise ValueError('unexpected payload decoder')
            literal=node.value.args[0].args[0].args[0].value
            raw=zlib.decompress(base64.b64decode(literal,validate=True))
            packed=base64.b85encode(lzma.compress(raw,preset=9)).decode('ascii')
            if lzma.decompress(base64.b85decode(packed))!=raw:
                raise ValueError('payload round-trip mismatch')
            replacement="json.loads(__import__('lzma').decompress(base64.b85decode("+repr(packed)+")))"
            if code.count(expression)!=1:raise ValueError('ambiguous payload replacement')
            cell['source']=code.replace(expression,replacement)
            compile(cell['source'],'<compact-notebook>','exec')
            changed+=1
    if changed!=1:raise ValueError('expected exactly one embedded source payload')
    encoded=json.dumps(result,indent=1).encode('utf-8')
    if len(encoded)>=MAX_NOTEBOOK_BYTES:
        raise ValueError('notebook exceeds conservative 900,000-byte upload guard')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    original=args.input/'profile.ipynb'
    notebook=compact(json.loads(original.read_text(encoding='utf-8')))
    metadata=json.loads((args.input/'kernel-metadata.json').read_text())
    metadata['enable_gpu']=False
    args.output.mkdir(parents=True,exist_ok=False)
    for name,data in [('profile.ipynb',notebook),('kernel-metadata.json',metadata)]:
        (args.output/name).write_bytes(json.dumps(data,indent=1).encode('utf-8'))
    report={'status':'packaging_review_only_no_launch_authority',
        'input_notebook_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),
        'original_bytes':original.stat().st_size,
        'compact_bytes':(args.output/'profile.ipynb').stat().st_size,
        'maximum_bytes':MAX_NOTEBOOK_BYTES,'embedded_payload_bytes_unchanged':True,
        'artifacts':{name:hashlib.sha256((args.output/name).read_bytes()).hexdigest()
                     for name in ('profile.ipynb','kernel-metadata.json')}}
    (args.output/'packaging-review.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))


if __name__=='__main__':main()
