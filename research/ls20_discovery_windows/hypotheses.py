"""Small observational candidate generator with an explicit open-world alternative."""
import copy

from .contract import M1View, VERSION, digest, require, validate_action


def applicable(scope, segment, action, state):
    return (scope['segment'] == segment and
            (scope['action'] is None or scope['action'] == action) and
            (scope['state'] is None or scope['state'] == state))


class HypothesisManager:
    """Learn three generic scopes, never a named game mechanic or fixed palette.

    Candidates predict *appearance after an action*, not a cause or a win rule.
    A contradiction is absorbing for that exact rule/scope. More specific scopes
    and previously unseen outcome categories can be created from later evidence.
    All candidates/evidence are retained; at most max_candidates enter a request.
    """
    def __init__(self, view, max_candidates=4):
        require(isinstance(view, M1View), 'validated M1View required')
        require(type(max_candidates) is int and 2 <= max_candidates <= 4, 'candidate limit must be 2..4')
        self.view, self.max_candidates = view, max_candidates
        self._hypotheses = []
        for record in view.history:
            self._learn(record)

    def _learn(self, record):
        if record['label'] is None:
            return
        action, state, segment = record['action'], record['pre']['state'], record['segment']
        evidence = dict(episode_id=record['episode_id'], segment=segment,
                        kind='transition', id=record['id'])
        for h in self._hypotheses:
            if h['status'] == 'contradicted' or not applicable(h['scope'], segment, action, state):
                continue
            if h['predicted_label'] != record['label']:
                h['counterexamples'].append(evidence)
                h['status'] = 'contradicted'
            else:
                h['supporting_evidence'].append(evidence)
                h['status'] = 'supported' if len(h['supporting_evidence']) >= 2 else 'tentative'
        scopes = [dict(segment=segment, action=action, state=None),
                  dict(segment=segment, action=None, state=state),
                  dict(segment=segment, action=action, state=state)]
        for scope in scopes:
            if any(h['scope'] == scope and h['predicted_label'] == record['label'] for h in self._hypotheses):
                continue
            self._hypotheses.append(dict(id=f'wh{len(self._hypotheses)}', family='observational_effect',
                scope=copy.deepcopy(scope), predicted_label=record['label'], status='tentative',
                confidence_kind='uncalibrated_heuristic', supporting_evidence=[evidence], counterexamples=[]))

    def hypotheses(self):
        return copy.deepcopy(self._hypotheses)

    def predict(self, action, mode='competing'):
        require(not self.view.suspended, 'cannot predict from an unknown current state')
        require(mode in ('competing', 'immediate'), 'unknown comparison mode')
        action = validate_action(action, self.view.current['legal_actions'])
        eligible = [h for h in self._hypotheses if h['status'] != 'contradicted' and
            applicable(h['scope'], self.view.segment, action, self.view.current['state'])]
        # Identical candidate generator and ranking in both comparisons.
        eligible.sort(key=lambda h: (-len(h['supporting_evidence']),
            -(int(h['scope']['action'] is not None) + int(h['scope']['state'] is not None)),
            int(h['id'][2:])))
        selected = eligible[:1 if mode == 'immediate' else self.max_candidates]
        # A presentation cap must not hide known disagreement in the competing arm.
        labels = sorted({h['predicted_label'] for h in (eligible if mode == 'competing' else selected)})
        prediction = dict(version=VERSION, mode=mode, m1_producer_commit=self.view.producer_commit,
            context=self.view.context(), snapshot_sha256=digest(self.view.snapshot), action=action,
            candidate_ids=[h['id'] for h in selected], omitted_candidate_count=len(eligible)-len(selected),
            predicted_labels=labels, status='no_candidates' if not labels else
                ('candidate_agreement' if len(labels) == 1 else 'candidate_disagreement'),
            unknown_alternative=True, confidence_kind='uncalibrated_heuristic',
            objective_hypotheses=[], candidate_targets=[])
        prediction['prediction_id'] = digest(prediction)
        return prediction

    def export(self):
        """W1 -> W2/M2 handoff. No executable world model or objective is asserted."""
        return dict(version=VERSION, m1_producer_commit=self.view.producer_commit,
                    context=self.view.context(), hypotheses=self.hypotheses(),
                    unknown_alternative=True, objective_hypotheses=[], candidate_targets=[])
