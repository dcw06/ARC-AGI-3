"""Kaggle entry point with bounded, non-game-specific console output."""

from __future__ import annotations

import os
import time
from pathlib import Path

from .competition_loop import CompetitionOrchestrator
from .config import ConfigurationError
from .e1_policy import E1Policy, OpenAICompatibleCompletionClient, binding_from_registry
from .feature_manifest import load_e1_feature_manifests
from .framework_adapter import RemoteFrameworkAdapter
from .production_policy import ModelService, load_operational_primary
from .runtime_audit import validate_mounted_runtime
from .scheduler import QueuedInferenceExecutor
from .watchdog import DeadlineWatchdog


def main() -> int:
    lifecycle_started = time.monotonic()
    print("ARC3_RUN_START", flush=True)
    try:
        audit = validate_mounted_runtime("kaggle_2026_09_07")
        if not audit.passed:
            print(f"ARC3_RUNTIME_AUDIT status=failed checks={len(audit.failures)}", flush=True)
            return 3
        print(f"ARC3_RUNTIME_AUDIT status=passed checks={len(audit.checks)}", flush=True)
        source_root = Path(__file__).resolve().parents[1]
        try:
            primary = load_operational_primary(source_root)
            manifests = load_e1_feature_manifests(source_root / "config/e1_feature_manifests.yaml")
            binding = binding_from_registry(source_root / "config/e1_feature_manifests.yaml")
            if binding != primary.binding or primary.cell_id not in manifests:
                raise ConfigurationError("operational primary and feature registry drifted")
        except (ConfigurationError, OSError, ValueError):
            print("ARC3_PRIMARY_CONFIG status=failed", flush=True)
            return 4

        service: ModelService | None = None
        inference: QueuedInferenceExecutor | None = None
        completion_clients: list[OpenAICompatibleCompletionClient] = []
        policy_factory = None
        try:
            service = ModelService(primary)
            ready_seconds = service.start()
            inference = QueuedInferenceExecutor(
                maxsize=primary.queue_capacity,
                max_age_seconds=primary.queue_max_age_seconds,
                worker_count=primary.queue_workers,
            )
            inference.__enter__()

            def make_policy(client: object) -> E1Policy:
                completion = OpenAICompatibleCompletionClient(
                    primary.base_url,
                    timeout_seconds=primary.request_timeout_seconds,
                )
                completion_clients.append(completion)
                return E1Policy(
                    manifest=manifests[primary.cell_id],
                    binding=binding,
                    client=completion,
                    inference=inference,
                    max_new_tokens=primary.max_new_tokens,
                    seed=primary.request_seed,
                    request_timeout_seconds=primary.request_timeout_seconds,
                )

            policy_factory = make_policy
            print(
                f"ARC3_PRIMARY status=ready cell={primary.cell_id} label=provisional ready_seconds={ready_seconds:.3f}",
                flush=True,
            )
        except Exception:
            if inference is not None:
                inference.__exit__(None, None, None)
                inference = None
            if service is not None:
                service.close()
                service = None
            print("ARC3_PRIMARY status=unavailable fallback=E0", flush=True)

        remaining = primary.hard_seconds - (time.monotonic() - lifecycle_started)
        if remaining <= primary.finalization_reserve_seconds:
            print("ARC3_RUN_FAILED phase=runtime_envelope_exhausted", flush=True)
            return 2

        adapter = RemoteFrameworkAdapter(
            base_url=os.getenv("ARC_BASE_URL", "http://gateway:8001"),
            api_key=os.getenv("ARC_API_KEY", "test-key-123"),
            competition_mode=True,
        )
        game_ids = adapter.list_game_ids()
        watchdog = DeadlineWatchdog(
            hard_seconds=remaining,
            finalization_reserve_seconds=primary.finalization_reserve_seconds,
        )
        try:
            result = CompetitionOrchestrator(
                adapter,
                game_ids,
                max_workers=int(os.getenv("ARC_MAX_CLIENTS", "8")),
                max_actions=int(os.getenv("ARC_MAX_ACTIONS", "80")),
                watchdog=watchdog,
                policy_factory=policy_factory,
                run_tag="plan8-e1s-r-provisional" if policy_factory is not None else "plan8-e0-fallback",
            ).run()
        finally:
            for completion in completion_clients:
                completion.session.close()
            if inference is not None:
                inference.__exit__(None, None, None)
            if service is not None:
                service.close()
        completed = sum(item.status == "complete" for item in result.results)
        print(
            f"ARC3_RUN_END clients={len(result.results)} completed={completed} finalization={result.finalization_status}",
            flush=True,
        )
        return 0 if result.finalization_status == "acknowledged" else 2
    except Exception:
        print("ARC3_RUN_FAILED phase=startup_or_inventory", flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
