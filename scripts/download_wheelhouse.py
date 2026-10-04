"""Manifest-bound wheel download for the wheelhouse replacement (R2). Download only: it never resolves versions,
never installs anything and never uploads.

Gate: it refuses to run unless --approved-manifest-sha256 equals both the manifest's recorded digest and the digest
recomputed from its artifact list. The approval therefore names exactly one manifest.

  python scripts/download_wheelhouse.py --approved-manifest-sha256 <digest> [--dest DIR] [--workers N]

Behaviour per artifact (only URLs listed in the manifest, only on files.pythonhosted.org, naming that exact file):
- an existing file is reused only after its size and SHA-256 verify; a mismatching file is moved aside, not used;
- downloads go to a temporary file, bounded by the expected size, a per-file absolute deadline (shared by retries,
  backoff and every read) and per-operation timeouts; reads use read1() so trickling data cannot outlast the deadline;
- the file is renamed into place only after its size and SHA-256 verify.
The destination must be outside the git repository (default: ~/.local/share/agi/wheelhouse-r2).
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.check_wheelhouse_metadata import (  # noqa: E402
    STALL_ENV, DeadlineExceeded, _artifact_url_ok, _NoRedirect, _set_read_timeout, run_worker)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'reports/wheelhouse_download_manifest.json'
DEFAULT_DEST = Path.home() / '.local/share/agi/wheelhouse-r2'
ATTEMPTS = 3
OPERATION_TIMEOUT = 60.0      # seconds per connect or read, further capped by the time remaining
BASE_DEADLINE = 300.0         # seconds per file, plus the size-proportional allowance below
MIN_RATE = 1024 ** 2          # bytes/second assumed for the size-proportional allowance (1 MiB/s)
CHUNK = 1024 ** 2
MAX_WORKERS = 4
# The user's recorded approval (download only), named by digest. Other tools bind to it via load_manifest().
APPROVED_MANIFEST_SHA256 = '3691cb8854df4d8ff10e42ca9957fddb9a8ae0362064e7b31b3205891af0d546'


class DownloadError(Exception):
    pass


def manifest_digest(manifest):
    canonical = json.dumps(manifest['artifacts'], sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(canonical).hexdigest()


def load_manifest(path, approved):
    manifest = json.loads(Path(path).read_text(encoding='utf-8'))
    recomputed = manifest_digest(manifest)
    if manifest.get('manifest_sha256') != recomputed:
        raise SystemExit('the manifest digest does not match its artifact list')
    if approved != recomputed:
        raise SystemExit('refused: --approved-manifest-sha256 does not name this manifest')
    names = [a['filename'] for a in manifest['artifacts']]
    if len(names) != len(set(names)) or len(names) != manifest.get('artifact_count'):
        raise SystemExit('the manifest has duplicate artifacts or a wrong count')
    if sum(a['size'] for a in manifest['artifacts']) != manifest.get('total_bytes'):
        raise SystemExit('the manifest total does not match its artifacts')
    for a in manifest['artifacts']:
        if not _artifact_url_ok(a['url'], a['filename']) or Path(a['filename']).name != a['filename']:
            raise SystemExit(f"refused: {a['filename']} is not an allowed exact-artifact URL or a plain file name")
    return manifest


def check_destination(dest):
    dest = Path(dest).resolve()
    if dest == ROOT.resolve() or ROOT.resolve() in dest.parents:
        raise SystemExit(f'refused: the destination {dest} is inside the git repository')
    return dest


def file_digest(path):
    h, size = hashlib.sha256(), 0
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(CHUNK), b''):
            h.update(block)
            size += len(block)
    return size, h.hexdigest()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Downloader:
    def __init__(self, dest, opener=None, clock=time.monotonic, sleep=time.sleep):
        self.dest = dest
        self.partial = dest / '.partial'
        self._opener = opener  # None: each attempt runs in a killable worker process (real network)
        self._clock, self._sleep = clock, sleep
        self.requests = []

    def _remaining(self, deadline, what):
        left = deadline - self._clock()
        if left <= 0:
            raise DownloadError(f'deadline exhausted before {what}')
        return left

    def fetch(self, artifact):
        final = self.dest / artifact['filename']
        if final.exists():
            size, digest = file_digest(final)
            if (size, digest) == (artifact['size'], artifact['sha256']):
                return {'filename': artifact['filename'], 'status': 'reused_verified'}
            final.replace(final.with_name(final.name + f'.mismatch-{int(time.time())}'))
        deadline = self._clock() + BASE_DEADLINE + artifact['size'] / MIN_RATE
        last = None
        for attempt in range(ATTEMPTS):
            try:
                self._attempt(artifact, final, deadline)
                return {'filename': artifact['filename'], 'status': 'downloaded_verified'}
            except DownloadError as error:
                last = error
                if 'deadline' in str(error) or 'hash' in str(error) or 'size' in str(error):
                    break
            if attempt + 1 < ATTEMPTS:
                left = self._remaining(deadline, 'backoff')
                if 2 ** attempt >= left:
                    break
                self._sleep(2 ** attempt)
        return {'filename': artifact['filename'], 'status': 'failed', 'reason': str(last)}

    def _attempt(self, artifact, final, deadline):
        url = artifact['url']
        if not _artifact_url_ok(url, artifact['filename']):
            raise DownloadError(f'refused URL {url}')
        self.partial.mkdir(parents=True, exist_ok=True)
        temp = self.partial / f"{artifact['filename']}.{os.getpid()}.tmp"
        left = self._remaining(deadline, f'requesting {url}')
        self.requests.append(url)
        request = urllib.request.Request(url, headers={'User-Agent': 'arc-agi-3-wheelhouse-r2-download'})
        timeout = min(OPERATION_TIMEOUT, left)
        if self._opener is not None:  # injected opener (tests): in-process
            self._stream(self._opener, request, timeout, artifact, final, temp, deadline)
            return
        try:
            message = run_worker(_process_download, (url, str(temp), artifact['size'], timeout,
                                                     deadline - self._clock()), deadline, self._clock,
                                 f'downloading {url}')
        except DeadlineExceeded as error:
            temp.unlink(missing_ok=True)  # the worker process has been killed and reaped
            raise DownloadError(f'deadline: {error}') from error
        try:
            if message[0] != 'ok':
                raise DownloadError(message[1])
            size, digest = file_digest(temp)  # verified again in this process before completion
            if size != artifact['size']:
                raise DownloadError(f'size {size} differs from the expected {artifact["size"]}')
            if digest != artifact['sha256']:
                raise DownloadError(f'hash mismatch for {artifact["filename"]}')
            os.replace(temp, final)
        finally:
            temp.unlink(missing_ok=True)

    def _stream(self, opener, request, timeout, artifact, final, temp, deadline):
        url = artifact['url']
        try:
            with opener.open(request, timeout=timeout) as response:
                if response.status != 200:
                    raise DownloadError(f'HTTP {response.status} for {url}')
                h, size = hashlib.sha256(), 0
                reader = getattr(response, 'read1', None) or response.read
                with open(temp, 'wb') as out:
                    while True:
                        left = self._remaining(deadline, f'reading {url}')
                        _set_read_timeout(response, min(OPERATION_TIMEOUT, left))
                        chunk = reader(min(CHUNK, artifact['size'] + 1 - size))
                        self._remaining(deadline, f'completing a read of {url}')
                        if not chunk:
                            break
                        size += len(chunk)
                        if size > artifact['size']:
                            raise DownloadError(f'size exceeds the expected {artifact["size"]} bytes for {url}')
                        h.update(chunk)
                        out.write(chunk)
            if size != artifact['size']:
                raise DownloadError(f'size {size} differs from the expected {artifact["size"]}')
            if h.hexdigest() != artifact['sha256']:
                raise DownloadError(f'hash mismatch for {artifact["filename"]}')
            os.replace(temp, final)
        except urllib.error.HTTPError as error:
            raise DownloadError(f'HTTP {error.code} for {url} (redirects are not followed)') from error
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as error:
            raise DownloadError(f'{type(error).__name__} for {url}: {error}') from error
        finally:
            temp.unlink(missing_ok=True)


def _process_download(conn, url, temp, size_limit, timeout, seconds_left):
    """Worker process: stream one artifact into `temp`, bounded by size and by its own copy of the deadline."""
    deadline = time.monotonic() + seconds_left

    def remaining(what):
        left = deadline - time.monotonic()
        if left <= 0:
            raise DownloadError(f'deadline exhausted in the worker before {what}')
        return left
    try:
        stall = float(os.environ.get(STALL_ENV) or 0)
        if stall:
            time.sleep(stall)
        request = urllib.request.Request(url, headers={'User-Agent': 'arc-agi-3-wheelhouse-r2-download'})
        with urllib.request.build_opener(_NoRedirect).open(request, timeout=timeout) as response:
            if response.status != 200:
                raise DownloadError(f'HTTP {response.status} for {url}')
            reader = getattr(response, 'read1', None) or response.read
            size = 0
            with open(temp, 'wb') as out:
                while True:
                    left = remaining(f'reading {url}')
                    _set_read_timeout(response, min(OPERATION_TIMEOUT, left))
                    chunk = reader(min(CHUNK, size_limit + 1 - size))
                    remaining(f'completing a read of {url}')
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > size_limit:
                        raise DownloadError(f'size exceeds the expected {size_limit} bytes for {url}')
                    out.write(chunk)
        conn.send(('ok', size))
    except urllib.error.HTTPError as error:
        conn.send(('error', f'HTTP {error.code} for {url} (redirects are not followed)'))
    except (DownloadError, urllib.error.URLError, OSError) as error:
        conn.send(('error', f'{type(error).__name__}: {error}'))
    finally:
        conn.close()


def run(manifest, dest, workers=MAX_WORKERS, downloader=None):
    dest.mkdir(parents=True, exist_ok=True)
    downloader = downloader or Downloader(dest)
    workers = max(1, min(workers, MAX_WORKERS))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(downloader.fetch, manifest['artifacts']))
    record = {'manifest_sha256': manifest['manifest_sha256'], 'artifact_count': manifest['artifact_count'],
              'total_bytes': manifest['total_bytes'], 'results': results,
              'complete': all(r['status'] in ('reused_verified', 'downloaded_verified') for r in results)}
    (dest / 'download-record.json').write_text(json.dumps(record, indent=1) + '\n', encoding='utf-8')
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--approved-manifest-sha256', required=True)
    parser.add_argument('--manifest', default=str(MANIFEST))
    parser.add_argument('--dest', default=str(DEFAULT_DEST))
    parser.add_argument('--workers', type=int, default=3)
    args = parser.parse_args(argv)
    manifest = load_manifest(args.manifest, args.approved_manifest_sha256)
    dest = check_destination(args.dest)
    record = run(manifest, dest, args.workers)
    counts = {}
    for r in record['results']:
        counts[r['status']] = counts.get(r['status'], 0) + 1
    print(json.dumps({'complete': record['complete'], 'counts': counts, 'dest': str(dest)}))
    return 0 if record['complete'] else 1


if __name__ == '__main__':
    sys.exit(main())
