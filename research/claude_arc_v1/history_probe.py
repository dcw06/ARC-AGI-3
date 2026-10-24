"""CPU-only prompt-size measurements. Characters/bytes are never called model tokens."""
from dataclasses import replace
import json
import numpy as np
from arcengine import GameState
from agent.action import ActionDecision
from agent.state import Observation
from .config import Config
from .policy import Policy


def measure():
    rows = []
    for pattern in ('one_digit', 'two_digit', 'mixed_palette'):
        for frame_count in (1, 3):
            for count in (0, 1, 3, 6):
                c = replace(Config(), stage='history')
                p = Policy(c)
                def observed(step):
                    frames = []
                    for offset in range(frame_count):
                        if pattern == 'mixed_palette':
                            frame = (np.arange(4096).reshape(64, 64) + step + offset) % 16
                        else:
                            frame = np.full((64, 64), (step + offset) % 2 + (10 if pattern == 'two_digit' else 0))
                        frames.append(frame.astype(np.uint8))
                    return Observation('synthetic-size-probe', tuple(frames), GameState.NOT_FINISHED,
                                       0, 3, 'synthetic-guid', (1, 6))
                before = observed(0)
                for step in range(count):
                    after = observed(step + 1)
                    p.observe(before, ActionDecision(1, {}, source='synthetic'), after, {})
                    before = after
                request = p.request(before)
                user = request['messages'][1]['content']
                raw = json.dumps(request, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
                rows.append({'pattern': pattern, 'frames_per_observation': frame_count,
                    'history_transitions': count, 'rendered_history_transitions': min(count, c.history_limit),
                    'user_characters': len(user), 'user_utf8_bytes': len(user.encode()),
                    'request_characters': len(raw), 'request_utf8_bytes': len(raw.encode())})
    return {'schema': 'claude_arc_v1_history_size_probe', 'method': 'synthetic 64x64 grids; no model or engine calls',
            'history_limit': 6, 'configured_input_token_cap': Config().max_input_tokens,
            'model_token_counts': None, 'token_count_status': 'not_measured_no_provider_or_model_tokenizer_called',
            'configuration_pass_or_fail': 'unknown_until_exact_backend_token_count_is_measured',
            'truncation_policy_changed': False, 'rows': rows}


if __name__ == '__main__':
    print(json.dumps(measure(), sort_keys=True, indent=2))
