"""Keep action admission separate from bounded engine cleanup."""
import math
from research.initial_geometry_assistance_v1.engine_bridge import BridgeEngine


class FeedbackEngine(BridgeEngine):
    def __init__(self, python, game_id, games, recordings, log, deadline, *, cleanup_deadline, env, on_effect):
        if (type(deadline) not in (int, float) or type(cleanup_deadline) not in (int, float) or
                not math.isfinite(deadline) or not math.isfinite(cleanup_deadline) or
                not deadline < cleanup_deadline <= deadline+300):
            raise ValueError('engine cleanup deadline must stay within the lifecycle reserve')
        self.closing = False
        super().__init__(python, game_id, games, recordings, log, deadline, env=env, on_effect=on_effect)
        self.cleanup_deadline = cleanup_deadline

    def bootstrap(self):
        if self.closing: raise RuntimeError('engine cleanup started; no further work')
        return super().bootstrap()

    def dispatch(self, action):
        if self.closing: raise RuntimeError('engine cleanup started; no further work')
        return super().dispatch(action)

    def close(self):
        # No bootstrap/dispatch can follow close. The supervisor's independent
        # watchdog still bounds this cleanup by the 3,300-second lifecycle.
        self.closing = True
        self.deadline = self.cleanup_deadline
        return super().close()
