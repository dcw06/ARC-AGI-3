"""Prospective bootstrap repair; independent of the consumed installation probe.

Use host pip's --python support to manage an empty venv without ensurepip.
No GPU, network download, authorization, or notebook execution occurs here.
"""
import json
import os
from pathlib import Path
import re
import sys
import time

from certification.phase4_v6.target_install_probe import command, LOG_BYTES, digest

ENVIRONMENT_PINS = ['arc-agi==0.9.8', 'arcengine==0.9.3', 'requests==2.33.1',
                    'numpy==2.4.4', 'pydantic==2.13.2', 'python-dotenv==1.2.2']


def verify_environment_wheels(wheels, manifest):
    wheels = Path(wheels)
    expected = {Path(name).name: info for name, info in manifest['files'].items()
                if name.startswith('wheels/')}
    if (wheels.is_symlink() or len(expected) != 31
            or {path.name for path in wheels.iterdir()} != set(expected)):
        raise ValueError('frozen environment inventory mismatch')
    for name, info in expected.items():
        path = wheels/name
        if (path.is_symlink() or path.stat().st_size != info['bytes']
                or digest(path) != info['sha256']):
            raise ValueError('frozen environment wheel mismatch: '+name)
    return len(expected)


class CleanEnvironment:
    def __init__(self, scratch, output, *, host_python=sys.executable, seconds=300):
        self.scratch, self.output = Path(scratch).resolve(), Path(output).resolve()
        self.output.mkdir(parents=True, exist_ok=False)
        self.host = str(host_python)
        self.venv = self.scratch/'venv'
        self.python = str(self.venv/'bin/python')
        self.started = time.monotonic()
        self.deadline = self.started+seconds
        self.stages = []
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith('PIP_') and key not in
                    ('PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV')}
        self.env.update(PIP_CONFIG_FILE=os.devnull, PIP_NO_INDEX='1',
                        PIP_DISABLE_PIP_VERSION_CHECK='1', PIP_NO_CACHE_DIR='1',
                        PYTHONNOUSERSITE='1', PYTHONDONTWRITEBYTECODE='1',
                        TMPDIR=str(self.scratch), XDG_CACHE_HOME=str(self.scratch/'cache'),
                        HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')

    def execute(self, stage, argv):
        if any(row['stage'] == stage for row in self.stages):
            raise ValueError('stage cannot be retried: '+stage)
        row = {'stage': stage, 'started_seconds': time.monotonic()-self.started,
               'passed': False, 'error': None}
        self.stages.append(row)
        log = self.output/'stages.log'
        try:
            if time.monotonic() >= self.deadline-5:
                raise TimeoutError('stage deadline exhausted before launch')
            header = ('\n=== '+stage+' ===\n').encode()
            if (log.stat().st_size if log.exists() else 0)+len(header) > LOG_BYTES:
                raise ValueError('stage log budget exhausted')
            with log.open('ab') as stream:
                stream.write(header)
            command(argv, log, self.deadline, self.env)
            row['passed'] = True
        except Exception as exc:
            row['error'] = type(exc).__name__+': '+str(exc)[:512]
            raise RuntimeError('bootstrap stage failed: '+stage) from exc
        finally:
            row['ended_seconds'] = time.monotonic()-self.started
            (self.output/'stages.json').write_text(json.dumps(self.stages, indent=2))

    def bootstrap(self):
        if self.venv.exists():
            raise FileExistsError('refusing to reuse an existing environment')
        self.execute('host_inventory', [self.host, '-I', '-c',
            "import importlib.metadata as m,json,platform,sys; "
            "print(json.dumps({'python':platform.python_version(),'executable':sys.executable,"
            "'platform':platform.platform(),'pip':m.version('pip')})); "
            "assert sys.version_info[:2]==(3,12); assert platform.system()=='Linux'; "
            "assert platform.machine()=='x86_64'"])
        self.execute('create_empty_venv', [self.host, '-I', '-m', 'venv',
                                         '--without-pip', str(self.venv)])
        self.execute('verify_empty_isolated_venv', [self.python, '-I', '-c',
            "import importlib.metadata as m,importlib.util,json,site,sys; "
            "packages=[d.metadata['Name'] for d in m.distributions()]; "
            "print(json.dumps({'packages':packages,'prefix':sys.prefix,'base_prefix':sys.base_prefix,"
            "'user_site_enabled':site.ENABLE_USER_SITE})); "
            "assert sys.prefix!=sys.base_prefix; assert site.ENABLE_USER_SITE is False; "
            "assert not packages; assert importlib.util.find_spec('pip') is None"])
        self.execute('host_pip_targets_empty_venv', self.pip()+['--version'])

    def pip(self):
        return [self.host, '-I', '-m', 'pip', '--python', self.python,
                '--disable-pip-version-check', '--no-input']

    def install(self, stage, wheels, pins):
        if not pins or any(not re.fullmatch(r'[A-Za-z0-9_.-]+==[A-Za-z0-9_.+!-]+', pin)
                           for pin in pins):
            raise ValueError('exact package pins required')
        self.execute(stage, self.pip()+['install', '--no-index', '--no-cache-dir',
            '--only-binary=:all:', '--find-links', str(Path(wheels).resolve()),
            '--report', str(self.output/(stage+'.json')), *pins])

    def check(self):
        self.execute('dependency_check', self.pip()+['check'])
        self.execute('installed_inventory', self.pip()+['freeze', '--all'])
