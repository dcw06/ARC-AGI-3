"""Stateless E1S/E1C policies bound to the frozen Phase 1 manifests."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

import numpy as np
import requests

from .action import ActionDecision
from .feature_manifest import E1FeatureManifest, FeatureManifestError, validate_e1_proposal
from .representation import (
    FeatureObservationBundle,
    RawObservationBundle,
    build_feature_bundle,
    build_raw_bundle,
    representation_digest,
)
from .safe_operations import SAFE_OPERATIONS, SafeOperationLimits, SafeOperationWorkspace
from .scheduler import InferenceQueueError, QueuedInferenceExecutor
from .state import GameRuntimeState


@dataclass(frozen=True, slots=True)
class E1ModelBinding:
    candidate_id: str
    model_id: str
    revision: str
    engine: str
    reasoning_setting: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "E1ModelBinding":
        expected = {"candidate_id", "model_id", "revision", "engine", "reasoning_setting"}
        if set(value) != expected or not all(isinstance(value[key], str) and value[key] for key in expected):
            raise FeatureManifestError("E1 model binding must contain five non-empty exact fields")
        return cls(**{key: value[key] for key in expected})


@dataclass(frozen=True, slots=True)
class CompletionResult:
    content: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    elapsed_seconds: float | None = None


class CompletionClient(Protocol):
    def complete(self, request: Mapping[str, Any]) -> CompletionResult: ...


class OpenAICompatibleCompletionClient:
    """Small pinned transport for a local OpenAI-compatible model server."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8000",
        *,
        timeout_seconds: float = 300.0,
        session: requests.Session | None = None,
    ) -> None:
        normalized = base_url.rstrip("/")
        self.base_url = normalized[:-3] if normalized.endswith("/v1") else normalized
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def complete(self, request: Mapping[str, Any]) -> CompletionResult:
        started = time.monotonic()
        response = self.session.post(
            f"{self.base_url}/v1/chat/completions",
            json=dict(request),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        value = response.json()
        try:
            content = value["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise FeatureManifestError("model server returned no assistant content") from exc
        if not isinstance(content, str):
            raise FeatureManifestError("model server assistant content must be text")
        usage = value.get("usage") if isinstance(value, Mapping) else None
        return CompletionResult(
            content=content,
            prompt_tokens=usage.get("prompt_tokens") if isinstance(usage, Mapping) else None,
            completion_tokens=usage.get("completion_tokens") if isinstance(usage, Mapping) else None,
            elapsed_seconds=time.monotonic() - started,
        )


def e1_system_prompt(manifest: E1FeatureManifest) -> str:
    """Return the frozen instruction shared by runtime and profile fixtures."""
    common = (
        "You control one ARC-AGI-3 game from a stateless observation. "
        "history_compaction explicitly reports any older transitions omitted from this prompt. "
        "Return only compact JSON, never Markdown. Keep every response under 64 tokens. "
        "Omit intent and rationale. A final response must contain only "
        '{"action":{"action_id":1,"action_data":{}}}. Use exactly one currently legal '
        "action_id from 1 through 7. ACTION6 alone requires integer x and y in [0,63]. "
        "Do not emit reset/action 0."
    )
    if manifest.workspace == "none":
        return common
    operations = ",".join(sorted(SAFE_OPERATIONS))
    return (
        common
        + " Before the final response you may instead request one bounded operation as "
        + '{"operation":"name","arguments":{...}}. Available operations: '
        + operations
        + ". Available arrays are current, before, after, and previous_1 through "
        + f"previous_{manifest.recent_transition_limit} when present. "
        + f"At most {manifest.workspace_invocation_limit} operation requests are accepted."
    )


def _strict_object(text: str) -> Mapping[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise FeatureManifestError("model response is not one strict JSON object") from exc
    if not isinstance(value, Mapping):
        raise FeatureManifestError("model response must be a JSON object")
    return value


def _workspace_arrays(bundle: RawObservationBundle | FeatureObservationBundle) -> dict[str, np.ndarray]:
    raw = bundle.raw if isinstance(bundle, FeatureObservationBundle) else bundle
    arrays = {"current": raw.current_frame.unpack(), "after": raw.current_frame.unpack()}
    if raw.previous_final_frame is not None:
        arrays["before"] = raw.previous_final_frame.unpack()
    else:
        arrays["before"] = raw.current_frame.unpack()
    if raw.recent_final_frames:
        for offset, frame in enumerate(reversed(raw.recent_final_frames), start=1):
            arrays[f"previous_{offset}"] = frame.unpack()
    return arrays


class E1Policy:
    """One exact E1 factorial cell with no mutable cross-turn model context."""

    def __init__(
        self,
        *,
        manifest: E1FeatureManifest,
        binding: E1ModelBinding,
        client: CompletionClient,
        inference: QueuedInferenceExecutor,
        max_new_tokens: int = 128,
        seed: int = 0,
        request_timeout_seconds: float = 300.0,
    ) -> None:
        if max_new_tokens < 1:
            raise ValueError("max_new_tokens must be positive")
        self.manifest = manifest
        self.binding = binding
        self.client = client
        self.inference = inference
        self.max_new_tokens = max_new_tokens
        self.seed = seed
        self.request_timeout_seconds = request_timeout_seconds

    def propose(self, state: GameRuntimeState) -> ActionDecision:
        bundle = self._bundle(state)
        payload = bundle.policy_payload()
        digest = representation_digest(bundle)
        messages: list[dict[str, str]] = [
            {"role": "system", "content": self._system_prompt()},
            {
                "role": "user",
                "content": json.dumps(
                    {"observation": payload}, sort_keys=True, separators=(",", ":")
                ),
            },
        ]
        workspace = (
            SafeOperationWorkspace(
                _workspace_arrays(bundle),
                limits=SafeOperationLimits(
                    invocations_per_proposal=self.manifest.workspace_invocation_limit
                ),
            )
            if self.manifest.workspace == "safe_operations_v1"
            else None
        )

        # E1S has one inference request.  E1C has one final request plus no
        # more than the workspace's explicitly charged tool turns.
        call_ceiling = 1 if workspace is None else workspace.limits.invocations_per_proposal + 1
        for _ in range(call_ceiling):
            state.counters.inference_requests += 1
            try:
                result = self.inference.execute(
                    client_id=state.observation.game_id,
                    generation=state.counters.controller_iterations,
                    state_hash=digest,
                    callback=lambda current=tuple(messages): self.client.complete(
                        self._request(current)
                    ),
                    timeout_seconds=self.request_timeout_seconds,
                )
            except InferenceQueueError:
                state.counters.inference_queue_failures += 1
                raise
            except requests.RequestException:
                state.counters.inference_transport_failures += 1
                raise
            if not isinstance(result, CompletionResult):
                raise FeatureManifestError("completion client returned the wrong result type")
            state.counters.inference_completions += 1
            for value, label in (
                (result.prompt_tokens, "prompt_tokens"),
                (result.completion_tokens, "completion_tokens"),
            ):
                if value is not None and (
                    isinstance(value, bool) or not isinstance(value, int) or value < 0
                ):
                    raise FeatureManifestError(f"completion client returned invalid {label}")
            if result.elapsed_seconds is not None and result.elapsed_seconds < 0:
                raise FeatureManifestError("completion client returned invalid elapsed_seconds")
            state.counters.inference_prompt_tokens += result.prompt_tokens or 0
            state.counters.inference_completion_tokens += result.completion_tokens or 0
            state.counters.inference_elapsed_seconds += result.elapsed_seconds or 0.0
            response = _strict_object(result.content)
            if set(response) == {"operation", "arguments"}:
                if workspace is None:
                    raise FeatureManifestError("E1S cannot invoke workspace operations")
                operation, arguments = response["operation"], response["arguments"]
                if not isinstance(operation, str) or operation not in SAFE_OPERATIONS:
                    raise FeatureManifestError("model requested an unknown safe operation")
                if not isinstance(arguments, Mapping):
                    raise FeatureManifestError("safe-operation arguments must be an object")
                state.counters.workspace_invocations += 1
                workspace_started = time.monotonic()
                try:
                    value = workspace.invoke(operation, arguments)
                finally:
                    state.counters.workspace_elapsed_seconds += time.monotonic() - workspace_started
                messages.extend(
                    (
                        {"role": "assistant", "content": result.content},
                        {
                            "role": "user",
                            "content": json.dumps(
                                {"operation_result": value},
                                sort_keys=True,
                                separators=(",", ":"),
                            ),
                        },
                    )
                )
                continue
            return validate_e1_proposal(
                response,
                manifest=self.manifest,
                legal_actions=state.observation.available_actions,
            )
        raise FeatureManifestError("E1C exhausted its workspace budget without a final action")

    def _bundle(self, state: GameRuntimeState) -> RawObservationBundle | FeatureObservationBundle:
        if self.manifest.observation_bundle == "R":
            return build_raw_bundle(
                state.observation,
                state.evidence,
                recent_limit=self.manifest.recent_transition_limit,
            )
        if self.manifest.observation_bundle == "F":
            return build_feature_bundle(
                state.observation,
                state.evidence,
                recent_limit=self.manifest.recent_transition_limit,
            )
        raise FeatureManifestError("unknown observation bundle")

    def _request(self, messages: Sequence[Mapping[str, str]]) -> dict[str, Any]:
        request: dict[str, Any] = {
            "model": self.binding.model_id,
            "messages": [dict(message) for message in messages],
            "temperature": 0,
            "seed": self.seed,
            "max_tokens": self.max_new_tokens,
        }
        if self.binding.reasoning_setting == "instruct_non_thinking":
            request["chat_template_kwargs"] = {"enable_thinking": False}
        elif self.binding.reasoning_setting in {"low", "medium", "xhigh"}:
            request["reasoning_effort"] = self.binding.reasoning_setting
        else:
            raise FeatureManifestError("unsupported frozen reasoning setting")
        return request

    def _system_prompt(self) -> str:
        return e1_system_prompt(self.manifest)


def binding_from_registry(path: str | Path) -> E1ModelBinding:
    from .config import load_registry

    value = load_registry(path).get("model_binding")
    if not isinstance(value, Mapping):
        raise FeatureManifestError("E1 model binding is not frozen")
    return E1ModelBinding.from_mapping(value)
