"""Kaggle CLI access with local credential loading and secret-redacted output."""
import os
from pathlib import Path
import subprocess
import sys
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def environment():
    env = os.environ.copy()
    native = Path(r'\\wsl.localhost\Ubuntu\home\jingjing\AGI') if os.name == 'nt' else Path('/home/jingjing/AGI')
    for folder in (ROOT, native):
        values = dotenv_values(folder/'.env', interpolate=False)
        for name in ('KAGGLE_API_TOKEN', 'KAGGLE_USERNAME', 'KAGGLE_KEY'):
            if values.get(name) and not env.get(name):
                env[name] = values[name]
        token = folder/'.kaggle/access_token'
        if token.is_file() and not env.get('KAGGLE_API_TOKEN'):
            env['KAGGLE_API_TOKEN'] = token.read_text().strip()
    if not env.get('KAGGLE_API_TOKEN') and not (env.get('KAGGLE_USERNAME') and env.get('KAGGLE_KEY')):
        raise RuntimeError('Kaggle credentials missing')
    return env


if __name__ == '__main__':
    args = sys.argv[1:]
    # This helper is read-only. The one-shot upload must use the bound launcher.
    if args[:2] not in (['kernels', 'status'], ['kernels', 'list'], ['kernels', 'pull'],
                       ['kernels', 'files'], ['kernels', 'output'],
                       ['datasets', 'files']) and args not in (['kernels', 'push', '--help'], ['quota']):
        raise PermissionError('only inspection/download commands supported')
    env = environment()
    executable = 'kaggle.exe' if os.name == 'nt' else 'kaggle'
    result = subprocess.run([str(Path(sys.executable).with_name(executable)), *args],
                            env=env, capture_output=True, text=True, timeout=90)
    output = result.stdout+result.stderr
    for name in ('KAGGLE_API_TOKEN', 'KAGGLE_KEY'):
        if env.get(name):
            output = output.replace(env[name], '[REDACTED]')
    print(output, end='')
    raise SystemExit(result.returncode)
