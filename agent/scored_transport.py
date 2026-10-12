"""One-shot JSON response with an absolute caller deadline, including body decoding."""
import _thread
import json
import time


def bounded_json_post(session, url, request, *, deadline, timeout_seconds=120, maximum_bytes=1024*1024):
    import requests

    until = min(deadline, time.monotonic()+timeout_seconds)
    if time.monotonic() >= until:
        raise requests.Timeout('completion response deadline expired before admission')
    finished = _thread.allocate_lock()
    finished.acquire()
    outcome = {}

    def work():
        response = None
        try:
            remaining = until-time.monotonic()
            if remaining <= 0:
                raise requests.Timeout('completion response deadline expired before transport')
            response = session.post(url, json=dict(request), timeout=remaining,
                                    stream=True, allow_redirects=False)
            if response.is_redirect:
                raise requests.TooManyRedirects('completion redirects disabled')
            response.raise_for_status()
            raw = bytearray()
            for chunk in response.iter_content(chunk_size=4096):
                if time.monotonic() >= until:
                    raise requests.Timeout('completion response deadline exceeded')
                raw.extend(chunk)
                if len(raw) > maximum_bytes:
                    raise ValueError('completion response exceeds byte limit')
            outcome['value'] = json.loads(raw)
        except BaseException as exc:
            outcome['error'] = exc
        finally:
            try:
                if response is not None:
                    response.close()
            except BaseException as exc:
                outcome['error'] = exc
            finally:
                finished.release()

    # Socket timeouts alone permit a peer to drip bytes indefinitely. A bounded
    # parent wait also covers headers, reads, JSON decoding and response close.
    # An overdue daemon worker can only publish an ignored result; its client
    # must never be reused and the owned worker group is terminated on shutdown.
    _thread.start_new_thread(work, ())
    if not finished.acquire(timeout=max(0, until-time.monotonic())) or time.monotonic() >= until:
        raise requests.Timeout('absolute completion response deadline exceeded')
    if 'error' in outcome:
        raise outcome['error']
    return outcome['value']
