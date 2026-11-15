"""Credential-free settings. Reading settings never creates a client or a game."""
from dataclasses import asdict, dataclass, field
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
    # Memory fix (research/memory_fix_v1): keep this many of the current level's most recent actions that
    # ended in GAME_OVER in every later request, each with the board before it and the board it produced.
    # They otherwise leave the input after history_limit actions. 0 is off: requests are the control's.
    pin_game_overs: int = 0
    # On the turn after a GAME_OVER the model must write a lesson: the general rule that explains the game
    # over and how to recognise the same danger elsewhere. Lessons are kept by the controller, outside the
    # eight rewritable notes, and shown in every later request of the game.
    game_over_lessons: bool = False
    # While lessons exist, every reply must check its chosen action against them.
    lesson_check: bool = False
    # Recovery study (research/recovery_v1). Everything below is off by default: requests and control flow
    # are then exactly those of the November 6 control.
    # The model may send RESET (action 0) from a live position, after at least one action on the attempt.
    model_may_reset: bool = False
    # Recovery check after this many consecutive model actions with no new board on the attempt; 0 is off.
    stall_window: int = 0
    # ... and only if the notes kept the same claims and statuses over those actions.
    stall_same_notes: bool = False
    # Recovery check when actions on the level reach this multiple of its human baseline; 0 is off.
    stall_level_ratio: float = 0
    # ... but never before this many actions on the level, so a level with a tiny baseline is not flagged at once.
    stall_level_floor: int = 0
    # Public per-level human baselines by game prefix, e.g. {"bp35": [21, 48, ...]}; used by stall_level_ratio.
    level_baselines: dict = field(default_factory=dict)
    # Refuse a reset that leaves too few actions for a new attempt (recovery.can_pay_back), and say in a
    # recovery check what a reset gives up. The action budget itself is never shown.
    recovery_pricing: bool = False
    # On the turn after a reset, offer to repeat the first N actions of the ended attempt, each one checked.
    replay_after_reset: bool = False
    # Start each game by repeating the first resume_actions actions of a saved run (no model calls), then play on.
    resume_events: str = ''
    resume_actions: int = 0
    # End a game once this many of its levels are completed; 0 plays on as before.
    stop_after_levels: int = 0

    @property
    def recovery_on(self):
        return bool(self.model_may_reset or self.stall_window or self.stall_level_ratio
                    or self.recovery_pricing or self.replay_after_reset)

    def __post_init__(self):
        if type(self.pin_game_overs) is not int or not 0 <= self.pin_game_overs <= 5:
            raise ValueError('pin_game_overs must be an integer from 0 to 5')
        if type(self.game_over_lessons) is not bool or type(self.lesson_check) is not bool:
            raise ValueError('game_over_lessons and lesson_check must be boolean')
        if self.lesson_check and not self.game_over_lessons:
            raise ValueError('lesson_check needs game_over_lessons')
        if any(type(getattr(self, name)) is not bool for name in
               ('model_may_reset', 'stall_same_notes', 'recovery_pricing', 'replay_after_reset')):
            raise ValueError('recovery switches must be boolean')
        if type(self.stall_window) is not int or not 0 <= self.stall_window <= 1000:
            raise ValueError('stall_window must be an integer from 0 to 1000')
        if type(self.stall_level_ratio) not in (int, float) or not 0 <= self.stall_level_ratio <= 5:
            raise ValueError('stall_level_ratio must be a number from 0 to 5')
        if type(self.stall_level_floor) is not int or not 0 <= self.stall_level_floor <= 1000:
            raise ValueError('stall_level_floor must be an integer from 0 to 1000')
        if self.stall_level_floor and not self.stall_level_ratio:
            raise ValueError('stall_level_floor needs stall_level_ratio')
        if (not isinstance(self.level_baselines, dict) or any(
                not isinstance(k, str) or not isinstance(v, (list, tuple)) or not v
                or any(type(n) is not int or n < 1 for n in v) for k, v in self.level_baselines.items())):
            raise ValueError('level_baselines must map a game prefix to positive integers')
        if (self.stall_window or self.stall_level_ratio or self.recovery_pricing) and not self.model_may_reset:
            raise ValueError('recovery checks and pricing need model_may_reset')
        if self.stall_same_notes and not self.stall_window:
            raise ValueError('stall_same_notes needs stall_window')
        if self.stall_level_ratio and not self.level_baselines:
            raise ValueError('stall_level_ratio needs level_baselines')
        if type(self.resume_actions) is not int or self.resume_actions < 0 or not isinstance(self.resume_events, str):
            raise ValueError('resume_actions must be a nonnegative integer and resume_events a path')
        if bool(self.resume_actions) != bool(self.resume_events):
            raise ValueError('resume_events and resume_actions go together')
        if type(self.stop_after_levels) is not int or not 0 <= self.stop_after_levels <= 100:
            raise ValueError('stop_after_levels must be an integer from 0 to 100')
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
