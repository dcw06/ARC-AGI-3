"""Track 3 launch override and bounded running-server cache-configuration evidence.

vLLM 0.19.0 exposes CacheConfig.metrics_info() through vllm:cache_config_info.
The endpoint is queried once, before the canary; absence is a startup failure.
"""
import hashlib
import json
import re
import time
from urllib.parse import urlsplit
from urllib.request import urlopen

LIMIT = 256 * 1024
KIND = 'stagnation_supervision_effective_server_configuration_r1'
DISABLE = '--no-enable-prefix-caching'


def cache_disabled_argv(argv):
    value = list(argv)
    flags = [x for x in value if x.startswith(('--enable-prefix-caching', DISABLE))]
    if flags != ['--enable-prefix-caching']:
        raise ValueError('unexpected inherited prefix-cache launch configuration')
    value[value.index('--enable-prefix-caching')] = DISABLE
    return value


def cache_config(body):
    """Parse the exact single-engine info gauge, never infer caching from zero hits."""
    if type(body) is not str or len(body.encode()) > LIMIT:
        raise ValueError('cache metrics body limit')
    rows = [line for line in body.splitlines() if line.startswith('vllm:cache_config_info{')]
    if len(rows) != 1:
        raise ValueError('missing or ambiguous running cache configuration')
    match = re.fullmatch(r'vllm:cache_config_info\{(.*)\} 1(?:\.0)?', rows[0])
    if not match:
        raise ValueError('cache configuration gauge')
    labels, pos = {}, 0
    text = match[1]
    for item in re.finditer(r'([a-zA-Z_][a-zA-Z0-9_]*)=("(?:[^"\\]|\\.)*")(?:,|$)', text):
        if item.start() != pos or item[1] in labels:
            raise ValueError('cache configuration labels')
        labels[item[1]] = json.loads(item[2])
        pos = item.end()
    if pos != len(text) or labels.get('engine') != '0' or labels.get('enable_prefix_caching') != 'False':
        raise ValueError('running server prefix caching is not explicitly disabled')
    return labels


def validate(record, *, mode):
    if record.get('kind') != KIND or record.get('status') != 'verified' or record.get('mode') != mode:
        raise ValueError('server configuration receipt')
    raw = record.get('metrics_body')
    if (type(raw) is not str or record.get('metrics_sha256') != hashlib.sha256(raw.encode()).hexdigest()
            or record.get('cache_configuration') != cache_config(raw)):
        raise ValueError('server configuration evidence binding')
    argv = record.get('argv', [])
    if (type(argv) is not list or argv.count(DISABLE) != 1
            or any(x.startswith('--enable-prefix-caching') for x in argv)):
        raise ValueError('effective server argv caching drift')
    if mode == 'live' and record.get('evidence_class') != 'running_server_metrics':
        raise ValueError('live configuration needs running server evidence')
    if mode == 'rehearsal' and record.get('evidence_class') != 'injected_not_target_evidence':
        raise ValueError('rehearsal configuration label')
    return record


def rehearsal_record():
    raw = 'vllm:cache_config_info{enable_prefix_caching="False",engine="0"} 1.0\n'
    return {'kind': KIND, 'status': 'verified', 'mode': 'rehearsal',
            'evidence_class': 'injected_not_target_evidence', 'argv': [DISABLE],
            'metrics_body': raw, 'metrics_sha256': hashlib.sha256(raw.encode()).hexdigest(),
            'cache_configuration': cache_config(raw), 'checked_monotonic': time.monotonic()}


def model_owner(primary, retain):
    from certification.phase4_integrated_v2.model_process import ModelService

    class Owner(ModelService):
        def _argv_and_env(self):
            argv, env = super()._argv_and_env()
            argv = cache_disabled_argv(argv)
            self.effective = {'kind': KIND, 'status': 'launch_requested', 'mode': 'live',
                              'evidence_class': 'running_server_metrics', 'argv': argv}
            retain(self.effective)
            return argv, env

        def _completion_canary(self):
            # Called by ModelService.start only after /v1/models responds successfully.
            # The one inference canary still runs through SupervisionModelService later.
            parts = urlsplit(self.primary.base_url)
            url = f'{parts.scheme}://{parts.netloc}/metrics'
            record = {**self.effective, 'status': 'received', 'metrics_url': url,
                      'server_pid': self.process.pid}
            try:
                with urlopen(url, timeout=5) as response:
                    raw = response.read(LIMIT + 1)
                record.update(metrics_body=raw[:LIMIT].decode('utf-8', errors='replace'),
                              metrics_bytes=len(raw), metrics_truncated=len(raw) > LIMIT,
                              metrics_sha256=hashlib.sha256(raw).hexdigest(),
                              checked_monotonic=time.monotonic())
                retain(record)  # Received bytes survive parsing and every later validation.
                if len(raw) > LIMIT:
                    raise ValueError('cache metrics body limit')
                record.update(cache_configuration=cache_config(raw.decode()), status='verified')
                validate(record, mode='live')
                retain(record)
            except Exception as exc:
                record.update(status='failed', error=type(exc).__name__ + ': ' + str(exc)[:200])
                retain(record)
                raise

    return Owner(primary)
