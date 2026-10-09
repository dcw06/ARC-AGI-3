"""One lifecycle clock (installation start through cleanup) and the model-request ledger."""
import time


class BudgetExceeded(TimeoutError):
    pass


class RequestRefused(RuntimeError):
    pass


class Clock:
    """Monotonic time since the notebook's first cell. Phases get ceilings; no new model request is admitted after
    the admission cutoff; cleanup keeps its reserve up to the internal deadline."""

    def __init__(self, limits, started, now=time.monotonic):
        self.limits, self.started, self.now = limits, started, now
        self.phases = []

    def elapsed(self):
        return self.now() - self.started

    def remaining(self):
        return self.limits['internal_seconds'] - self.elapsed()

    def admission_open(self):
        return self.elapsed() < self.limits['admission_cutoff_seconds']

    def phase_deadline(self, ceiling):
        """Absolute monotonic deadline for a phase: its own ceiling, never beyond the admission cutoff."""
        return min(self.now() + ceiling, self.started + self.limits['admission_cutoff_seconds'])

    def cleanup_deadline(self):
        return self.started + self.limits['internal_seconds']

    def check(self, what):
        if self.elapsed() >= self.limits['internal_seconds']:
            raise BudgetExceeded(f'{what}: internal deadline reached')

    def record(self, name, begin, outcome):
        self.phases.append({'phase': name, 'began_at': round(begin - self.started, 3),
                            'seconds': round(self.now() - begin, 3), 'outcome': outcome})


class Ledger:
    """Every HTTP request to the model server, in order. Only planned request ids are admitted, each at most its
    `max_issues` (default 1); the total never exceeds `maximum_model_requests`; nothing is admitted after the
    admission cutoff. Refusals are recorded too."""

    def __init__(self, plan, maximum, clock):
        self.plan = {item['id']: item for item in plan}
        self.order = [item['id'] for item in plan]
        self.maximum, self.clock = maximum, clock
        self.entries, self.refusals = [], []
        worst = sum(item.get('max_issues', 1) for item in plan)
        if worst > maximum:
            raise ValueError(f'the plan allows {worst} requests, above the cap of {maximum}')

    def issued(self, request_id=None):
        return [e for e in self.entries if request_id is None or e['id'] == request_id]

    def admit(self, request_id):
        item = self.plan.get(request_id)
        reason = None
        if item is None:
            reason = 'not in the frozen request plan'
        elif len(self.issued(request_id)) >= item.get('max_issues', 1):
            reason = 'already issued the permitted number of times'
        elif len(self.entries) >= self.maximum:
            reason = f'model-request cap of {self.maximum} reached'
        elif not self.clock.admission_open():
            reason = 'admission cutoff passed'
        if reason:
            self.refusals.append({'id': request_id, 'reason': reason, 'at': round(self.clock.elapsed(), 3)})
            raise RequestRefused(f'{request_id}: {reason}')
        entry = {'id': request_id, 'kind': item['kind'], 'method': item['method'], 'path': item['path'],
                 'sequence': len(self.entries) + 1, 'issued_at': round(self.clock.elapsed(), 3), 'outcome': None}
        self.entries.append(entry)
        return item, entry

    def summary(self):
        kinds = {}
        for e in self.entries:
            kinds[e['kind']] = kinds.get(e['kind'], 0) + 1
        return {'maximum_model_requests': self.maximum, 'issued': len(self.entries), 'by_kind': kinds,
                'counting_rule': 'every HTTP request to the model server, including startup and cancellation probes; '
                                 'readiness is detected by TCP connection only',
                'entries': self.entries, 'refusals': self.refusals}
