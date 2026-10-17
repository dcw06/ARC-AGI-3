"""Bounded one-image Semantic-SAM smoke. No provider calls or inference on import."""
import csv
import ctypes
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import zipfile

from certification.direct_publisher_smoke_v1.server import ModelServer, defer_startup_signals
from .archive_transport import canonical, digest, restore
from .transport_check import alarm, LifecycleDeadline, write

SCOPE = dict(gpu_count=1, gpu_name_contains='RTX PRO 6000', session_timeout_seconds=3600,
    worker_seconds=3300, work_seconds=3000, cleanup_reserve_seconds=300,
    attempts=1, automatic_retries=0, access='account_holder_only', internet=False, tpu=False,
    model='semantic_sam_l', modes=['seeded','automatic'], granularity=1, smoke_case='board-06',
    image_size_wh=[448,448], automatic_grid_side=16, automatic_point_batch=16,
    max_scored_proposals=96, new_molmopoint_generations=0, model_http_requests=0,
    game_actions=0, scorecards=0, whole_job_cap_seconds=None,
    provider_overhead_may_exceed_one_hour=True)
PREFIX = Path('/tmp/arc3-semantic-runtime-r1')
COMPETITION = 'arc-prize-2026-arc-agi-3'


def check(deadline):
    if time.monotonic() >= deadline: raise LifecycleDeadline('Semantic-SAM lifecycle deadline reached')


class Commands:
    """Register before spawn; kill before census; never catch the final alarm."""
    def __init__(self):
        self.entries = []
        self.libc = ctypes.CDLL(None, use_errno=True)
        previous = ctypes.c_int()
        if self.libc.prctl(37, ctypes.byref(previous),0,0,0): raise OSError('subreaper read failed')
        self.previous = previous.value
        if self.libc.prctl(36,1,0,0,0): raise OSError('subreaper enable failed')

    def members(self, pgid, deadline):
        members = []
        for path in Path('/proc').iterdir():
            check(deadline)
            if path.name.isdigit():
                try:
                    fields = (path/'stat').read_text().rsplit(')',1)[1].split()
                    if int(fields[2]) == pgid: members.append(int(path.name))
                except (FileNotFoundError,ProcessLookupError): pass
        return sorted(members)

    def emergency(self):
        # No census, file write or blocking wait before emergency SIGKILL.
        for entry in self.entries:
            group = entry['group']
            if not entry['retired'] and group.process is not None:
                try: os.killpg(group.process.pid,signal.SIGKILL)
                except ProcessLookupError: pass

    def retire(self, entry, deadline):
        if entry['retired']: return entry['receipt']
        check(deadline)
        group = entry['group']
        if group.process is None:
            if group.ownership != 'never_spawned': raise RuntimeError('spawn ownership uncertain')
            remaining = []
        else:
            # start_new_session guarantees this PID is our group, including
            # the handle-assigned/group-registration-interrupted case.
            try: os.killpg(group.process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            group.process.wait(timeout=max(.001,deadline-time.monotonic()))
            while True:
                check(deadline)
                try:
                    while os.waitpid(-group.process.pid,os.WNOHANG)[0]: check(deadline)
                except ChildProcessError: pass
                remaining = self.members(group.process.pid,deadline)
                if not remaining: break
                time.sleep(min(.02,max(0,deadline-time.monotonic())))
            if group.ownership != 'registered': raise RuntimeError('spawn ownership uncertain after emergency kill')
        check(deadline)
        if hasattr(group,'_log'): group._log.close()
        entry['receipt'] = dict(ownership=group.ownership,pgid=group.pgid,groups_absent=not remaining)
        entry['retired'] = True
        return entry['receipt']

    def command(self, argv, log, deadline, env):
        check(deadline)
        with defer_startup_signals():
            entry = dict(group=ModelServer(argv,env,log,None,None,inherit_env=False),retired=False)
            self.entries.append(entry)  # ownership recorded before entering Popen
            entry['group'].start()
        process = entry['group'].process
        try: code = process.wait(timeout=max(.001,deadline-time.monotonic()))
        except subprocess.TimeoutExpired as error: raise TimeoutError('command deadline reached') from error
        self.retire(entry,deadline)
        if code: raise RuntimeError('command exited ' + str(code) + '; retained log: ' + Path(log).name)
        check(deadline)
        with Path(log).open('rb') as stream:
            stream.seek(0,os.SEEK_END)
            stream.seek(max(0,stream.tell()-1024*1024))
            return stream.read().decode(errors='replace')

    def stop(self, deadline):
        receipts = [self.retire(entry,deadline) for entry in self.entries]
        check(deadline)
        if self.libc.prctl(36,self.previous,0,0,0): raise OSError('subreaper restore failed')
        return dict(groups=receipts,groups_absent=all(row['groups_absent'] for row in receipts))


def environment(sandbox, gpu):
    paths = os.environ.get('LD_LIBRARY_PATH','').split(os.pathsep)
    if any('\n' in path or '\0' in path for path in paths): raise ValueError('invalid driver search path')
    env = dict(PATH=str(PREFIX/'bin')+os.pathsep+os.defpath,HOME=str(sandbox),TMPDIR=str(sandbox),
        PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
        HF_HUB_DISABLE_TELEMETRY='1',HF_HOME=str(sandbox/'hf'),PIP_NO_INDEX='1',MPLBACKEND='Agg',
        CUDA_VISIBLE_DEVICES=gpu,NVIDIA_VISIBLE_DEVICES=gpu,OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4')
    driver_paths = list(dict.fromkeys(path for path in paths if path and os.path.isabs(path)))
    if driver_paths: env['LD_LIBRARY_PATH'] = os.pathsep.join(driver_paths)
    return env


def extract_tar(archive, destination, deadline, *, create=True):
    if create: destination.mkdir(exist_ok=False)
    with tarfile.open(archive) as source:
        for member in source:
            check(deadline)
            source.extract(member,destination,filter='data')
            check(deadline)


def stage(mount, sandbox, protocol, deadline, claim_prefix):
    restored = sandbox/'originals'
    receipt = restore(mount,restored,protocol['transport_manifest_sha256'],
                      protocol['original_manifest_sha256'],lambda: check(deadline))
    if PREFIX.exists() or PREFIX.is_symlink(): raise FileExistsError('preserve pre-existing runtime prefix')
    if shutil.disk_usage(sandbox).free < 9548014758 + 512*1024**2:
        raise ValueError('insufficient free space for isolated runtime')
    claim_prefix()
    extract_tar(restored/'semantic-runtime-py310-cu128-r1.tar',PREFIX,deadline,create=False)
    (restored/'semantic-runtime-py310-cu128-r1.tar').unlink()
    extract_tar(restored/'retained-seed-inputs.tar',sandbox/'inputs',deadline)
    upstream = sandbox/'upstream'; upstream.mkdir()
    with zipfile.ZipFile(restored/'semantic-sam-pinned-source.zip') as source:
        for member in source.infolist():
            check(deadline)
            destination = upstream/member.filename
            if '\\' in member.filename or not destination.resolve().is_relative_to(upstream):
                raise ValueError('unsafe upstream archive path')
            source.extract(member,upstream)
            check(deadline)
    roots = list(upstream.glob('*/configs/semantic_sam_only_sa-1b_swinL.yaml'))
    if len(roots) != 1: raise ValueError('exactly one Semantic-SAM upstream root required')
    return receipt, roots[0].parent.parent


def authority_check(protocol, authority):
    if canonical(protocol.get('scope')) != canonical(SCOPE): raise ValueError('GPU smoke scope differs')
    if (type(authority) is not dict or authority.get('approved') is not True or
            not authority.get('owner_answer') or authority.get('claim_consumed') is not True or
            not authority.get('attempt_id') or authority.get('protocol_sha256') != digest(canonical(protocol)) or
            canonical(authority.get('scope')) != canonical(SCOPE)):
        raise PermissionError('actual scoped GPU approval and single-use claim required')
    if protocol.get('competition_sources') != [COMPETITION]:
        raise PermissionError('RTX smoke requires the exact ARC-AGI-3 competition binding')
    for name in ('review_lock_sha256','runtime_lock_sha256'):
        if not __import__('re').fullmatch('[0-9a-f]{64}',str(authority.get(name,''))):
            raise PermissionError('exact GPU package authority required')


def run(protocol, authority, *, input_root='/kaggle/input',output='/kaggle/working/semantic-sam-smoke-v1'):
    authority_check(protocol,authority)  # before mounts, subprocesses or GPU queries
    if sys.platform != 'linux' or sys.version_info[:2] != (3,12): raise ValueError('pinned Linux Python 3.12 host required')
    if PREFIX.exists() or PREFIX.is_symlink(): raise FileExistsError('preserve pre-existing runtime')
    output = Path(output); output.mkdir(parents=True,exist_ok=False)
    sandbox = Path('/tmp/arc3-semantic-smoke-sandbox-r1')
    if sandbox.exists() or sandbox.is_symlink(): raise FileExistsError('preserve pre-existing sandbox')
    started = time.monotonic(); deadline = started+3300; work = started+3000
    owners = Commands()
    try:
        with alarm(deadline,work) as final_phase:
            return execute(protocol,authority,output,sandbox,started,deadline,work,owners,final_phase,input_root=input_root)
    except BaseException:
        owners.emergency()
        raise


def execute(protocol,authority,output,sandbox,started,deadline,work,owners,final_phase,*,input_root='/kaggle/input'):
    result = dict(schema='semantic_sam_gpu_smoke_v1',status='not_complete',scope=SCOPE,
        review_lock_sha256=authority['review_lock_sha256'],attempt_id=authority['attempt_id'],
        model_http_requests=0,new_molmopoint_generations=0,game_actions=0,scorecards=0)
    failure = None; gpu = None; count = 0; prefix_owned = False; sandbox_owned = False
    def claim_prefix():
        nonlocal prefix_owned
        with defer_startup_signals():
            PREFIX.mkdir(exist_ok=False)
            prefix_owned = True
    def command(argv,label,until,env):
        nonlocal count
        count += 1
        return owners.command(argv,output/(str(count)+'-'+label+'.log'),until,env)
    def query(apps=False,until=work):
        binary = shutil.which('nvidia-smi')
        if not binary: raise ValueError('nvidia-smi unavailable')
        flag = '--query-compute-apps=gpu_uuid,pid' if apps else '--query-gpu=uuid,name'
        text = command([binary,flag,'--format=csv,noheader,nounits'],'gpu-census',min(until,time.monotonic()+10),
                       environment(sandbox,gpu or ''))
        if len(text)>16384: raise ValueError('oversized GPU census')
        return [[part.strip() for part in row] for row in csv.reader(text.strip().splitlines()) if row]
    try:
        rows = query()
        if len(rows)!=1 or len(rows[0])!=2 or 'RTX PRO 6000' not in rows[0][1]:
            raise ValueError('exactly one RTX PRO 6000 required; no fallback')
        gpu = rows[0][0]; result['gpu'] = dict(uuid=gpu,name=rows[0][1])
        if query(True): raise ValueError('GPU already has a compute process')
        owner,slug = protocol['dataset_ref'].split('/')
        root = Path(input_root)
        mounts = [p for p in (root/slug,root/'datasets'/owner/slug) if p.is_dir()]
        if len(mounts)!=1: raise ValueError('one exact private transport mount required')
        with defer_startup_signals():
            sandbox.mkdir(mode=0o700,exist_ok=False)
            sandbox_owned = True
        result['restoration'],source = stage(mounts[0],sandbox,protocol,work,claim_prefix)
        code = Path(__file__).resolve().parents[2]
        env = environment(sandbox,gpu)
        for mode in SCOPE['modes']:
            check(work)
            argv = [str(PREFIX/'bin/python'),'-I',str(code/'scripts/run_granularity_segmentation.py'),
                '--worker','--execute','--deadline',str(work),'--seconds','3000',
                '--model','semantic_sam_l','--mode',mode,'--granularity','1','--device','cuda',
                '--inputs',str(sandbox/'inputs'),'--source',str(source),
                '--checkpoint',str(sandbox/'originals/semantic_sam_l.pt'),
                '--checkpoint-receipt',str(sandbox/'originals/checkpoint-receipt.json'),
                '--runtime-lock',str(sandbox/'originals/semantic-runtime-versions-r2.json'),
                '--output',str(output/mode),'--smoke-case','board-06']
            (output/mode).mkdir()
            command(argv,mode,work,env)
            summary = json.loads((output/mode/'worker-result.json').read_bytes())
            if summary['cases']!=['board-06'] or summary['purpose']!='one_image_runtime_smoke':
                raise ValueError('worker scope differs')
        check(work)
    except LifecycleDeadline as error:
        # Work checks may use this same exception before the final deadline.
        if time.monotonic()>=deadline: raise
        failure = error; result.update(error_type=type(error).__name__,error=str(error)[:1000])
    except BaseException as error:
        failure = error; result.update(error_type=type(error).__name__,error=str(error)[:1000])
    final_phase(); check(deadline)
    try:
        result['cleanup'] = owners.stop(deadline)
        check(deadline)
        if not result['cleanup']['groups_absent']: raise RuntimeError('owned groups remain')
        if gpu is None or query(True,deadline): raise ValueError('GPU cleanup unverified')
        rows = query(False,deadline)
        if rows != [[gpu,result['gpu']['name']]]: raise ValueError('GPU identity changed')
        result['gpu_cleanup_verified'] = True
        result['cleanup'] = owners.stop(deadline)
        if prefix_owned:
            if PREFIX.is_symlink() or PREFIX.parent != Path('/tmp'): raise ValueError('unsafe runtime cleanup')
            if PREFIX.exists(): shutil.rmtree(PREFIX)
        check(deadline)
        if sandbox_owned and sandbox.exists():
            if sandbox.is_symlink() or sandbox.parent != Path('/tmp'): raise ValueError('unsafe sandbox cleanup')
            shutil.rmtree(sandbox)
        check(deadline)
        result['temporary_environment_removed'] = not PREFIX.exists() and not sandbox.exists()
        if not result['temporary_environment_removed']: raise RuntimeError('temporary files remain')
    except LifecycleDeadline: raise
    except BaseException as error:
        failure = failure or error; result['cleanup_error'] = type(error).__name__+': '+str(error)[:1000]
    check(deadline)
    result['output_sha256'] = {}
    for path in sorted(output.rglob('*')):
        check(deadline)
        if path.is_file():
            import hashlib
            hasher = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda:stream.read(8*1024*1024),b''):
                    check(deadline); hasher.update(block)
            result['output_sha256'][path.relative_to(output).as_posix()] = hasher.hexdigest()
    result['status'] = 'provisional_complete' if failure is None else 'failed'
    result['elapsed_before_receipt_write_seconds'] = time.monotonic()-started
    raw = canonical(result); write(output/'result.json',raw); check(deadline)
    if failure is not None: raise RuntimeError('GPU smoke failed; preserve consumed attempt') from failure
    witness = canonical(dict(result_sha256=digest(raw),elapsed_after_receipt_write_seconds=time.monotonic()-started,
                             provider_COMPLETE_and_cell_marker_required=True))
    write(output/'completion-witness.json',witness); check(deadline)
    print('SEMANTIC_SAM_SMOKE_RETURNED '+digest(witness),flush=True); check(deadline)
    return result
