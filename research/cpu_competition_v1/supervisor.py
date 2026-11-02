"""Offline CPU install and bounded worker; imports the game SDK only after install."""
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time


def entry(root, wheels, *, scored, finalize=lambda completed: None, diagnostics=None):
    from research.initial_geometry_assistance_v1.live_resources import HardDeadline, Processes, environment
    from research.initial_geometry_assistance_v1.live_io import sha
    root, wheels = Path(root).resolve(), Path(wheels).resolve()
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError('this pinned CPU package requires Python 3.12')
    started = time.monotonic()
    final = started+3300
    work = final-300
    diagnostics = Path(diagnostics) if diagnostics is not None else None
    if diagnostics is not None:
        diagnostics.mkdir(parents=True, exist_ok=False)
    watcher = HardDeadline(final)
    watcher.start()
    processes = Processes(watcher)
    temporary = Path(tempfile.mkdtemp(prefix='arc3-cpu-runtime-'))
    log = temporary/'worker.log'
    env = dict(environment(), PYTHONPATH=str(root), CUDA_VISIBLE_DEVICES='',
               NVIDIA_VISIBLE_DEVICES='void', PYTHONDONTWRITEBYTECODE='1')
    if scored:
        env['KAGGLE_IS_COMPETITION_RERUN']='1'
    completed = False
    failure_type = None
    phase = 'wheel_verification'
    def milestone(name):
        print(json.dumps(dict(event='cpu_stage', phase=name,
            elapsed_seconds=time.monotonic()-started)), flush=True)
    try:
        milestone(phase)
        pins = json.loads((root/'research/cpu_competition_v1/wheels.json').read_bytes())
        for name, pin in pins.items():
            if time.monotonic() >= work:
                raise TimeoutError('wheel verification deadline')
            path = wheels/name
            if path.is_symlink() or not path.is_file() or path.stat().st_size != pin['bytes'] or sha(path) != pin['sha256']:
                raise ValueError('competition CPU wheel differs: '+name)
        python = temporary/'venv/bin/python'
        phase = 'environment_creation'
        milestone(phase)
        processes.command([sys.executable,'-m','venv','--without-pip',str(temporary/'venv')],
            log,min(work,time.monotonic()+120),env,'CPU venv without ensurepip')
        phase = 'offline_installation'
        milestone(phase)
        processes.command([sys.executable,'-m','pip','--python',str(python),'install',
            '--no-index','--no-cache-dir','--require-hashes','--only-binary=:all:',
            '--find-links',str(wheels),'-r',str(root/'research/cpu_competition_v1/requirements.lock')],
            log,min(work,time.monotonic()+600),env,'Competition-provided CPU wheels')
        # No gateway calls in validation. Tests use synthetic adapters only.
        if not scored:
            phase = 'validation_contracts_and_gateway_integration'
            milestone(phase)
            test_bootstrap = ('import sys,runpy; sys.path.insert(0,sys.argv.pop(1)); '
                              'runpy.run_module("unittest",run_name="__main__",alter_sys=True)')
            result = processes.command([str(python),'-B','-c',test_bootstrap,str(root),
                'tests.test_cpu_competition_v1','tests.test_cpu_competition_packaging_v1',
                'tests.test_cpu_gateway_readiness_v1','tests.test_cpu_competition_gateway_v1',
                'tests.test_ls20_overfit_v1'],
                log,min(work,time.monotonic()+120),env,'CPU synthetic contracts')
        else:
            phase = 'scored_gateway_worker'
            milestone(phase)
            left_work = int(work-time.monotonic())
            left_final = int(final-60-time.monotonic())
            if left_work <= 0:
                raise TimeoutError('no CPU game admission budget remains')
            result = processes.command([str(python),'-B',str(root/'research/cpu_competition_v1/runtime.py'),
                '--program',str(root/'research/ls20_overfit_v1/policy_seed0.json'),
                '--work-seconds',str(left_work),'--final-seconds',str(left_final)],
                log,final-30,env,'Single-scorecard CPU competition agent')
        print(result.stdout[-3000:],flush=True)
        completed = True
    except BaseException as exc:
        failure_type = type(exc).__name__
        raise
    finally:
        receipt=processes.stop(final)
        # Keep a bounded diagnostic tail before deleting the temporary runtime.
        # This is a worker/cleanup record, not a passing final-lifecycle verdict.
        if diagnostics is not None:
            if log.is_file():
                with log.open('rb') as stream:
                    stream.seek(0, os.SEEK_END)
                    stream.seek(max(0, stream.tell()-2*1024*1024))
                    with (diagnostics/'worker.log').open('xb') as output:
                        output.write(stream.read(2*1024*1024))
            record = dict(phase=phase, worker_completed=completed,
                failure_type=failure_type, cleanup=receipt,
                elapsed_seconds=time.monotonic()-started,
                final_lifecycle_verdict='not_certified_by_this_diagnostic')
            with (diagnostics/'worker-cleanup.json').open('x', encoding='utf-8') as output:
                json.dump(record, output, sort_keys=True)
        if receipt['groups_absent'] is not True or receipt['error'] or receipt['interrupted']:
            raise RuntimeError('CPU process cleanup unverified')
        shutil.rmtree(temporary)
        if time.monotonic() >= final:
            raise TimeoutError('CPU cleanup deadline')
        try:
            finalize(completed)
        finally:
            if time.monotonic() >= final:
                raise TimeoutError('CPU artifact/source finalization deadline')
            watcher.close()
            if time.monotonic() >= final:
                raise TimeoutError('CPU final deadline')
    print(json.dumps(dict(cpu_lifecycle_closed=True,elapsed_seconds=time.monotonic()-started,
                         GPU_jobs=0,model_generations=0)),flush=True)
