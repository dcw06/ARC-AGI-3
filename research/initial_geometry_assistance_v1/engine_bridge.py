"""Offline engine RPC in its own interpreter, inheriting the owned worker group."""
import argparse
import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from certification.direct_publisher_smoke_v1.server import defer_startup_signals
from .live_io import DeadlinePipe

GAMES = ('ls20-9607627b', 's5i5-18d95033', 'cd82-fb555c5d', 'ft09-0d8bbf25',
         'ka59-38d34dbb', 'sc25-635fd71a')


class BridgeEngine:
    def __init__(self, python, game_id, games, recordings, log, deadline, *, env, on_effect=lambda op: None):
        if game_id not in GAMES:
            raise ValueError('unreviewed game')
        self.deadline, self.on_effect = deadline, on_effect
        self.process = None
        self.sequence = 0
        self.broken = self.closed = False
        # Parent worker group owns this child before and after assignment. No setsid.
        self.log = Path(log).open('ab')
        try:
            with defer_startup_signals():
                self.process = subprocess.Popen(
                    [str(python), '-m', __name__, '--game', game_id, '--games', str(games),
                     '--recordings', str(recordings)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=self.log, env=dict(env, CUDA_VISIBLE_DEVICES='', NVIDIA_VISIBLE_DEVICES='void'))
                self.pipe = DeadlinePipe(self.process.stdout, self.process.stdin)
        except BaseException:
            self.log.close()
            raise

    def rpc(self, operation, **kwargs):
        if self.broken or self.closed:
            raise RuntimeError('engine RPC is closed; no retries')
        deadline = min(self.deadline, time.monotonic() + 30)
        if time.monotonic() >= deadline:
            raise TimeoutError('engine admission closed')
        self.sequence += 1
        self.on_effect(operation)  # durable admission before a reset or dispatch
        # Slow evidence writes must not reopen admission.
        if time.monotonic() >= deadline:
            raise TimeoutError('engine admission closed after journal')
        try:
            reply = self.pipe.exchange({'sequence': self.sequence, 'operation': operation, **kwargs}, deadline)
            if set(reply) != {'sequence', 'result', 'error'} or reply['sequence'] != self.sequence or reply['error']:
                raise ValueError('engine RPC error: ' + str(reply.get('error')))
            return reply['result']
        except BaseException:
            self.broken = True
            raise

    def bootstrap(self):
        return self.rpc('bootstrap')

    def dispatch(self, action):
        return self.rpc('dispatch', action=action)

    def close(self):
        try:
            result = self.rpc('close')
            self.closed = True
            self.process.stdin.close()
            code = self.process.wait(timeout=max(0.001, min(5, self.deadline-time.monotonic())))
            if code:
                raise RuntimeError('engine exited with error')
            return result
        finally:
            self.log.close()
            # A broken child is killed with the entire owned worker group by the supervisor.


def serve(game, games, recordings):
    from .engine import OfflineEngine
    output, engine, sequence, bootstrapped = sys.stdout, None, 0, False
    # Upstream engine diagnostics must never corrupt the RPC stream.
    with contextlib.redirect_stdout(sys.stderr):
        engine = OfflineEngine(game, games, recordings)
        for raw in sys.stdin.buffer:
            if len(raw) > 1024 * 1024:
                raise ValueError('oversize engine RPC')
            sequence += 1
            request = json.loads(raw)
            operation = request.get('operation')
            error, result = None, None
            try:
                expected = {'sequence', 'operation'} | ({'action'} if operation == 'dispatch' else set())
                if set(request) != expected or type(request['sequence']) is not int or request['sequence'] != sequence:
                    raise ValueError('engine request contract')
                if operation == 'bootstrap' and not bootstrapped:
                    bootstrapped = True
                    result = engine.bootstrap()
                elif operation == 'dispatch' and bootstrapped:
                    from .policy import parse_answer
                    action = request['action']
                    parse_answer(json.dumps({**action, 'predicted_visible_change': 'unknown'}), list(range(1, 8)))
                    result = engine.dispatch(action)
                elif operation == 'close':
                    result = engine.close()
                else:
                    raise ValueError('engine operation/order contract')
            except BaseException as exc:
                error = type(exc).__name__ + ': ' + str(exc)
            output.write(json.dumps({'sequence': sequence, 'result': result, 'error': error})+'\n')
            output.flush()
            if error or operation == 'close':
                break


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', choices=GAMES, required=True)
    parser.add_argument('--games', type=Path, required=True)
    parser.add_argument('--recordings', type=Path, required=True)
    args = parser.parse_args()
    serve(args.game, args.games, args.recordings)
