from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping, Protocol
import time
import requests
FeatureManifestError=ValueError

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
    finish_reason: str | None = None


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
            finish_reason=value['choices'][0].get('finish_reason'),
        )


