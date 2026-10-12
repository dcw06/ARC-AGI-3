"""One-scorecard E1S-R competition worker. No game-specific policy or model imports."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import threading
import time

from agent.competition_loop import CompetitionOrchestrator
from agent.e1_policy import CompletionResult, E1Policy, OpenAICompatibleCompletionClient, binding_from_registry
from agent.scored_transport import bounded_json_post
from agent.feature_manifest import load_e1_feature_manifests
from agent.framework_adapter import RemoteFrameworkAdapter
from agent.runtime_audit import validate_mounted_runtime
from agent.scheduler import QueuedInferenceExecutor
from agent.watchdog import DeadlineWatchdog

class CountedClient(OpenAICompatibleCompletionClient):
    lock = threading.Lock()
    entered = 0
    deadline = 0.0
    maximum = 8800

    def complete(self, request):
        with self.lock:
            if getattr(self, '_overdue', False) or getattr(self, '_inflight', False):
                raise TimeoutError('overdue or active completion transport cannot be reused')
            if time.monotonic() >= self.deadline or self.entered >= self.maximum:
                raise TimeoutError('scored request admission closed')
            type(self).entered += 1
            self._inflight = True
        # No redirect or retry can turn one admitted generation into multiple calls.
        started = time.monotonic()
        try:
            value = bounded_json_post(self.session, f'{self.base_url}/v1/chat/completions', request,
                                      deadline=self.deadline, timeout_seconds=min(120,self.timeout_seconds))
            content = value['choices'][0]['message']['content']
            if not isinstance(content, str):
                raise ValueError('completion content must be text')
            usage = value.get('usage') or {}
            if time.monotonic() >= min(self.deadline, started+min(120,self.timeout_seconds)):
                raise TimeoutError('completion response arrived after its absolute deadline')
            return CompletionResult(content, usage.get('prompt_tokens'), usage.get('completion_tokens'),
                                    time.monotonic()-started)
        except BaseException as exc:
            import requests
            if isinstance(exc, (requests.Timeout, TimeoutError)) or not isinstance(exc, Exception):
                self._overdue = True
            raise
        finally:
            with self.lock:
                self._inflight = False

def main():
    root, started, result_path = Path(sys.argv[1]), float(sys.argv[2]), Path(sys.argv[3])
    spec = json.loads((root/'config/scored_submission_v1.json').read_bytes())
    if not os.environ.get('KAGGLE_IS_COMPETITION_RERUN'):
        raise PermissionError('competition worker cannot run outside the scored rerun')
    if spec['authorized_seconds'] != 3600 or spec['study_cutoff_seconds'] != 3000:
        raise ValueError('one-hour budget drift')
    audit = validate_mounted_runtime('kaggle_2026_09_07')
    if not audit.passed:
        raise ValueError('game interpreter does not match the pinned competition SDK')
    CountedClient.deadline = started + spec['study_cutoff_seconds']
    CountedClient.entered = 0
    manifests = load_e1_feature_manifests(root/'config/e1_feature_manifests.yaml')
    binding = binding_from_registry(root/'config/e1_feature_manifests.yaml')
    watchdog = DeadlineWatchdog(spec['internal_seconds'],300,started_monotonic=started)
    adapter = RemoteFrameworkAdapter(base_url='http://gateway:8001', api_key='test-key-123', competition_mode=True,
                                     timeout_seconds=10, action_admission=lambda: not watchdog.stop_admission)
    games = adapter.list_game_ids()
    if not games or len(games) > spec['maximum_games'] or len(set(games)) != len(games):
        raise ValueError('invalid or over-budget competition inventory')
    remaining = started + spec['internal_seconds'] - time.monotonic()
    if remaining <= 300:
        raise TimeoutError('no game admission time remains')
    clients = []
    with QueuedInferenceExecutor(maxsize=110, max_age_seconds=120, worker_count=8) as executor:
        def factory(client):
            completion = CountedClient('http://127.0.0.1:8000/v1', timeout_seconds=120)
            # The transport itself also refuses redirects; the frozen E1 policy remains unchanged.
            clients.append(completion)
            return E1Policy(manifest=manifests['E1S-R'], binding=binding, client=completion, inference=executor,
                            max_new_tokens=128, seed=0, request_timeout_seconds=120)
        try:
            result = CompetitionOrchestrator(adapter, games, max_workers=8, max_actions=80,
                watchdog=watchdog, policy_factory=factory,
                run_tag='e1s-r-one-hour-budget-limited').run()
        finally:
            for client in clients:
                client.session.close()
    rows = [asdict(row) for row in result.results]
    summary = {'policy':'E1S-R', 'budget_limited':True, 'available_games':len(games),
        'attempted_games':sum(row['status'] != 'untouched' for row in rows),
        'levels_completed':sum(row['levels_completed'] for row in rows),
        'acknowledged_actions':sum(row['acknowledged_actions'] for row in rows),
        'ambiguous_actions':sum(row['ambiguous_actions'] for row in rows),
        'model_generations':CountedClient.entered, 'policy_failures':sum(row['policy_failures'] for row in rows),
        'finalization_status':result.finalization_status, 'elapsed_seconds':time.monotonic()-started}
    # Only aggregate performance; no hidden-game identifiers, frames, responses or package contents.
    result_path.write_text(json.dumps(summary, sort_keys=True)+'\n')
    if result.finalization_status != 'acknowledged':
        raise RuntimeError('competition scorecard close was not acknowledged')

if __name__ == '__main__':
    main()
