"""Adapt the existing four-stage memory-stress evaluator, retaining coexisting faults."""
from research.evidence_memory_stress_v1 import diagnostics as D
from research.evidence_memory_v1 import readers as RD
from . import schema as S, score as SC


def evaluate(truth, store, package, output, task, allowed_ids, writer_faults=False):
    # Injective category adapter: all new task vocabularies have <=4 categories.
    # This is internal scoring only, never a reader-visible factual-recall task.
    mapping = dict(zip(S.TASKS[task], RD.RECALL_VALUES))
    translated = lambda key: {'values': [mapping[key['answer']]]}
    scored = SC.score(output, task, package, allowed_ids)
    try:
        parsed = S.validate_response(output, task, allowed_ids)
        surrogate = S.compact({'values': [mapping[parsed['answer']]]})
    except (ValueError, TypeError, KeyError):
        surrogate = output  # remains invalid, never repaired
    base = D.attribution(translated(truth), translated(store), translated(package), surrogate,
                         {'kind': 'recall'}, writer_faults)
    end = SC.score(output, task, truth, allowed_ids)
    # Preserve prior category attribution; add independent provenance loss flags.
    return {**base, **scored,
            'writer_category_loss_or_distortion': base['writer_store_loss_or_distortion'],
            'selection_category_loss_or_distortion': base['selection_loss_or_distortion'],
            'writer_store_loss_or_distortion': store != truth,
            'selection_loss_or_distortion': package != store,
            'correct_truth': end['correct'],
            'correct_package': scored['correct'], 'reader_error': not scored['correct'],
            'writer_reference_loss_or_distortion': store != truth,
            'selection_reference_loss_or_distortion': package != store,
            'full_source': truth, 'full_store': store, 'selected_package': package,
            'response': output, 'end_to_end_category_correct': end['category_correct']}
