"""Credential-free settings. Reading settings never creates a client or a game."""
from dataclasses import asdict, dataclass
import json
import math
from urllib.parse import urlsplit

STAGES = ('baseline', 'history', 'hypotheses', 'experiments', 'world_model', 'planning')


def strict_json(raw):
    def constant(value):
        raise ValueError('non-finite JSON')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    def finite(text):
        value = float(text)
        if not math.isfinite(value):
            raise ValueError('non-finite JSON number')
        return value
    return json.loads(raw, parse_constant=constant, parse_float=finite, object_pairs_hook=pairs)


@dataclass(frozen=True)
class Config:
    live_enabled: bool = False
    backend: str = 'anthropic'
    model: str = 'claude-opus-5'
    stage: str = 'baseline'
    mode: str = 'online'
    games: tuple = ('ls20',)
    max_actions_per_game: int = 96
    max_model_calls: int = 96
    max_output_tokens: int = 2048
    max_input_tokens: int = 32768
    request_timeout_seconds: float = 120
    run_seconds: float = 1800
    cleanup_seconds: float = 30
    spend_limit_usd: float = 0
    input_usd_per_million: float = 5
    output_usd_per_million: float = 25
    anthropic_version: str = '2023-06-01'
    thinking: str = 'adaptive'
    effort: str = 'medium'
    local_model_url: str = 'http://127.0.0.1:8000'
    arc_base_url: str = 'https://three.arcprize.org'
    history_limit: int = 6
    exposure: str = 'exposed_development'

    def __post_init__(self):
        if type(self.live_enabled) is not bool:
            raise ValueError('live_enabled must be boolean')
        if self.backend not in ('anthropic', 'local_openai') or self.stage not in STAGES:
            raise ValueError('unknown backend or stage')
        if self.mode not in ('online', 'competition') or self.exposure not in ('exposed_development', 'reserved_evaluation'):
            raise ValueError('unknown mode or exposure classification')
        if not isinstance(self.model, str) or not self.model or not isinstance(self.anthropic_version, str):
            raise ValueError('explicit model and API version required')
        if self.thinking not in ('adaptive', 'disabled') or self.effort not in ('low', 'medium', 'high'):
            raise ValueError('unsupported thinking/effort configuration')
        if not isinstance(self.games, (list, tuple)) or any(not isinstance(g, str) or not g for g in self.games):
            raise ValueError('games must be game IDs')
        object.__setattr__(self, 'games', tuple(self.games))
        if len(set(self.games)) != len(self.games):
            raise ValueError('duplicate games')
        if self.mode == 'online' and not self.games:
            raise ValueError('online mode needs an explicit game list')
        if self.mode == 'competition' and self.games:
            raise ValueError('competition uses the entire live inventory: games must be empty')
        for name in ('max_actions_per_game', 'max_model_calls', 'max_output_tokens', 'max_input_tokens', 'history_limit'):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(name + ' must be a positive integer')
        for name in ('request_timeout_seconds', 'run_seconds', 'cleanup_seconds', 'spend_limit_usd',
                     'input_usd_per_million', 'output_usd_per_million'):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError(name + ' must be finite and nonnegative')
        if self.request_timeout_seconds <= 0 or self.cleanup_seconds <= 0 or self.run_seconds <= self.cleanup_seconds:
            raise ValueError('invalid lifecycle limits')
        if self.backend == 'anthropic' and min(self.input_usd_per_million, self.output_usd_per_million) <= 0:
            raise ValueError('Anthropic prices must be positive; confirm current rates before execution')
        arc = urlsplit(self.arc_base_url)
        if (arc.scheme != 'https' or arc.hostname not in ('three.arcprize.org', 'arcprize.org')
                or arc.port not in (None, 443) or arc.username or arc.password or arc.path not in ('', '/')
                or arc.query or arc.fragment):
            raise ValueError('ARC URL must be an official HTTPS origin')
        local = urlsplit(self.local_model_url)
        if (local.scheme != 'http' or local.hostname not in ('127.0.0.1', 'localhost', '::1')
                or local.username or local.password or local.query or local.fragment or local.path not in ('', '/', '/v1')):
            raise ValueError('local model must use a loopback HTTP endpoint')

    @classmethod
    def load(cls, path):
        from pathlib import Path
        value = strict_json(Path(path).read_bytes())
        if not isinstance(value, dict):
            raise ValueError('configuration must be an object')
        return cls(**value)

    def public(self):
        return asdict(self)
