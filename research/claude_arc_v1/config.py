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
    # Subscription path: the Claude Code CLI in print mode (no tools, settings or API key).
    claude_cli: str = 'claude'
    # Prompt rendering only; recorded evidence always keeps the full integer frames.
    grid_encoding: str = 'json'
    # Defaults preserve the original stop-everything behaviour.
    on_model_failure: str = 'stop_attempt'
    model_retries_per_action: int = 0
    # Wait before resending after a no-reply failure (CLI error, timeout, network); counts toward the idle guard.
    model_retry_backoff_seconds: float = 0
    clear_hypotheses_on_level: bool = True
    # Controller-issued level RESETs after GAME_OVER (each counts as an action); 0 ends the game at GAME_OVER.
    resets_per_game: int = 0
    # Let hypotheses cite observed boards (o0 = initial board, oN = board after tN), not only transitions.
    observation_evidence_ids: bool = False
    # hex_rows history: only the N newest entries carry a full board (older ones keep action, changes and effects).
    # 0 keeps every shown board. Boards dominate prompt size, and so subscription usage.
    history_board_limit: int = 0

    def __post_init__(self):
        if any(type(getattr(self, name)) is not bool for name in
               ('live_enabled', 'clear_hypotheses_on_level', 'observation_evidence_ids')):
            raise ValueError('live_enabled, clear_hypotheses_on_level and observation_evidence_ids must be boolean')
        if self.backend not in ('anthropic', 'local_openai', 'claude_code') or self.stage not in STAGES:
            raise ValueError('unknown backend or stage')
        if self.grid_encoding not in ('json', 'hex_rows') or self.on_model_failure not in ('stop_attempt', 'next_game'):
            raise ValueError('unknown grid encoding or model-failure policy')
        if type(self.model_retries_per_action) is not int or not 0 <= self.model_retries_per_action <= 3:
            raise ValueError('model_retries_per_action must be an integer from 0 to 3')
        if type(self.resets_per_game) is not int or not 0 <= self.resets_per_game <= 50:
            raise ValueError('resets_per_game must be an integer from 0 to 50')
        if type(self.history_board_limit) is not int or self.history_board_limit < 0:
            raise ValueError('history_board_limit must be a nonnegative integer')
        if not isinstance(self.claude_cli, str) or not self.claude_cli or '\n' in self.claude_cli:
            raise ValueError('claude_cli must name an executable')
        if self.mode not in ('online', 'competition') or self.exposure not in ('exposed_development', 'reserved_evaluation'):
            raise ValueError('unknown mode or exposure classification')
        if not isinstance(self.model, str) or not self.model or not isinstance(self.anthropic_version, str):
            raise ValueError('explicit model and API version required')
        if self.thinking not in ('adaptive', 'disabled') or self.effort not in ('low', 'medium', 'high', 'xhigh', 'max'):
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
                     'input_usd_per_million', 'output_usd_per_million', 'model_retry_backoff_seconds'):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError(name + ' must be finite and nonnegative')
        if self.request_timeout_seconds <= 0 or self.cleanup_seconds <= 0 or self.run_seconds <= self.cleanup_seconds:
            raise ValueError('invalid lifecycle limits')
        # ARC scorecards auto-close after 15 minutes without activity; keep the longest model wait under 14.
        if (self.request_timeout_seconds * (1 + self.model_retries_per_action)
                + self.model_retry_backoff_seconds * self.model_retries_per_action) >= 840:
            raise ValueError('model wait could exceed the 15-minute scorecard inactivity window')
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
