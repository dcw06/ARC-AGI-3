"""Acquire one immutable public snapshot locally; never upload or load weights."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research.molmopoint_identification_v1.adapter import MODEL, REVISION, verify_snapshot


def acquire(destination, metadata, resume=False):
    destination, metadata = Path(destination), Path(metadata)
    destination.mkdir(parents=True, exist_ok=resume)
    pin = json.loads((ROOT/'research/molmopoint_identification_v1/model_pin.json').read_bytes())
    total = sum(max(0,row['bytes']-sum(p.stat().st_size for p in
        (destination/row['name'],destination/(row['name']+'.partial')) if p.is_file())) for row in pin['files'])
    if shutil.disk_usage(destination).free < total+5*1024**3:
        raise OSError('insufficient destination free space including reserve')
    # No hidden download retries; partial files remain for diagnosis, never loadable.
    def one(row):
        path = destination/row['name']
        path.parent.mkdir(parents=True, exist_ok=True)
        local = metadata/row['name']
        if path.exists():
            if not resume:
                raise FileExistsError(path.name)
        elif local.is_file():
            shutil.copyfile(local, path)
        else:
            partial = path.with_name(path.name+'.partial')
            start, size = time.monotonic(), 0
            url = f'https://huggingface.co/{MODEL}/resolve/{REVISION}/{row["name"]}'
            digest = hashlib.sha256()
            if partial.exists():
                if not resume:
                    raise FileExistsError(partial.name)
                with partial.open('rb') as previous:
                    for chunk in iter(lambda:previous.read(8*1024*1024),b''):
                        digest.update(chunk)
                        size += len(chunk)
            request = urllib.request.Request(url,headers={'Range':f'bytes={size}-'} if size else {})
            with urllib.request.urlopen(request, timeout=60) as source, partial.open('ab' if size else 'xb') as target:
                if size and (source.status != 206 or source.headers.get('Content-Range') != f'bytes {size}-{row["bytes"]-1}/{row["bytes"]}'):
                    raise ValueError('server did not honor exact partial-file continuation')
                while True:
                    if time.monotonic()-start > 3600:
                        raise TimeoutError('checkpoint acquisition deadline reached')
                    chunk = source.read(8*1024*1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > row['bytes']:
                        raise ValueError('upstream file larger than immutable pin')
                    digest.update(chunk)
                    target.write(chunk)
            if size != row['bytes'] or digest.hexdigest() != row['upstream_sha256']:
                raise ValueError('checkpoint shard differs from immutable size/SHA256 pin')
            partial.rename(path)
        print(json.dumps({'file_verified_or_staged': row['name'], 'bytes': row['bytes']}), flush=True)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(one, pin['files']))
    receipt = verify_snapshot(destination)
    receipt.update(weights_downloaded=True, pretrained_weights_loaded=False,
                   acquisition='immutable revision; eight streams; no automatic retries',
                   explicitly_resumed_acquisition=resume)
    (destination.parent/(destination.name+'-receipt.json')).write_text(
        json.dumps(receipt, sort_keys=True, indent=2)+'\n', encoding='utf-8')
    print('ALL_SNAPSHOT_FILES_VERIFIED', flush=True)


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--destination', required=True)
    cli.add_argument('--metadata', required=True)
    cli.add_argument('--resume', action='store_true', help='explicitly continue retained partial downloads; every final hash is rechecked')
    args = cli.parse_args()
    acquire(args.destination, args.metadata, args.resume)
