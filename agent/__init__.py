"""Competition-safe ARC-AGI-3 agent package."""

__all__ = ["ActionDecision", "CompetitionAgentLoop", "DisplayPoint"]


def __getattr__(name):
    """Keep the installation bootstrap standard-library-only."""
    if name in ("ActionDecision", "DisplayPoint"):
        from .action import ActionDecision, DisplayPoint
        return {"ActionDecision": ActionDecision, "DisplayPoint": DisplayPoint}[name]
    if name == "CompetitionAgentLoop":
        from .competition_loop import CompetitionAgentLoop
        return CompetitionAgentLoop
    raise AttributeError(name)
