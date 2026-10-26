"""One prospective, no-retry step and offline artifact verification."""
import copy
import json
import os
from pathlib import Path
import time

from .contract import M1View, digest, normalize_outcome, require
from .hypotheses import HypothesisManager


def write_once(path, payload):
    """Exclusive creation prevents overwriting a prepared/uncertain dispatch."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(dict(payload=payload, sha256=digest(payload)), sort_keys=True,
                     allow_nan=False).encode() + b'\n'
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def read_checked(path):
    envelope = json.loads(Path(path).read_text(encoding='utf-8'))
    require(set(envelope) == {'payload', 'sha256'} and digest(envelope['payload']) == envelope['sha256'],
            'journal checksum mismatch')
    return envelope['payload']


def execute_step(memory, action, dispatch, directory, *, producer_commit, mode='competing'):
    """memory implements Mac snapshot/append/save; dispatch returns an outcome dict.

    The directory is a fresh run directory. Existing prediction files prohibit a
    retry, including after a process dies between sealing and receiving a result.
    The host must stop after any exception; this is not the production supervisor.
    """
    before = memory.snapshot()
    view = M1View(before, producer_commit)
    manager = HypothesisManager(view)
    prediction = manager.predict(action, mode)
    root = Path(directory)
    step = f"step-{len(view.history):04d}"
    # Both files are flushed before the dispatch callback can run.
    write_once(root / f'{step}.before.json', before)
    write_once(root / f'{step}.prediction.json', prediction)
    start = time.monotonic()
    try:
        outcome = normalize_outcome(dispatch(copy.deepcopy(prediction['action'])))
    except Exception as exc:
        # An exception or malformed reply cannot establish that nothing was sent.
        outcome = dict(status='outcome_unknown', reason='dispatch raised/returned invalid data: ' + type(exc).__name__)
    elapsed = time.monotonic() - start
    transition = memory.append(prediction['action'], outcome, elapsed_seconds=elapsed)
    after = memory.snapshot()
    after_view = M1View(after, producer_commit)
    require(len(after_view.history) == len(view.history) + 1 and
            after['transitions'][:-1] == before['transitions'], 'memory did not append exactly one transition')
    write_once(root / f'{step}.after.json', after)
    # Persist Mac's own restorable envelope as well as the audit snapshots.
    memory.save(root / 'memory.json')
    result = dict(prediction_id=prediction['prediction_id'], transition_id=transition['id'],
                  status=outcome['status'], elapsed_seconds=elapsed,
                  after_snapshot_sha256=digest(after), label=after_view.history[-1]['label'])
    write_once(root / f'{step}.result.json', result)
    return copy.deepcopy(result)


def replay_step(directory, step, producer_commit):
    """Validate bindings/chronology and score the retained prospective forecast.

    Checksum files cannot authenticate chronology against a malicious publisher.
    Runtime callback-order tests establish the implementation's write-before-act order.
    """
    root = Path(directory)
    stem = f'step-{step:04d}'
    before = read_checked(root / f'{stem}.before.json')
    prediction = read_checked(root / f'{stem}.prediction.json')
    after = read_checked(root / f'{stem}.after.json')
    result = read_checked(root / f'{stem}.result.json')
    return replay_payloads(before, prediction, after, result, step, producer_commit)


def replay_payloads(before, prediction, after, result, step, producer_commit):
    """Same verifier for the standalone JSON trace bundle and on-disk records."""
    view, post_view = M1View(before, producer_commit), M1View(after, producer_commit)
    require(len(view.history) == step and len(post_view.history) == step + 1,
            'step chronology mismatch')
    require(after['initial'] == before['initial'] and after['episode_id'] == before['episode_id']
            and after['transitions'][:-1] == before['transitions'], 'history prefix mismatch')
    expected = HypothesisManager(view).predict(prediction['action'], prediction['mode'])
    require(prediction == expected, 'prediction does not reconstruct from before evidence')
    record = post_view.history[-1]
    require(record['action'] == prediction['action'], 'predicted/dispatched action mismatch')
    require(result == dict(prediction_id=prediction['prediction_id'], transition_id=record['id'],
        status=record['outcome']['status'], elapsed_seconds=after['transitions'][-1]['elapsed_seconds'],
        after_snapshot_sha256=digest(after), label=record['label']), 'result binding mismatch')
    label = record['label']
    return dict(step=step, label=label, scored=label is not None,
        covered=label is not None and len(prediction['predicted_labels']) == 1,
        correct=label is not None and prediction['predicted_labels'] == [label],
        prediction_status=prediction['status'])
