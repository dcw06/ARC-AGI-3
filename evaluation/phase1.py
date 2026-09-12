"""Frozen Phase 1 selection and paired-inference calculations."""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from statistics import fmean
from typing import Mapping, Sequence


E1_FACTORIAL_CELLS = ("E1S-R", "E1S-F", "E1C-R", "E1C-F")


@dataclass(frozen=True, slots=True)
class CrossValidatedSelection:
    fold_choices: tuple[str, ...]
    held_out_scores: tuple[float, ...]
    selection_procedure_mean: float
    final_fixed_candidate: str
    final_fixed_candidate_mean: float


@dataclass(frozen=True, slots=True)
class PairedInference:
    mean_difference: float
    nonzero_pairs: int
    one_sided_p_value: float | None
    status: str


@dataclass(frozen=True, slots=True)
class FactorialContrast:
    name: str
    per_game: tuple[tuple[str, float], ...]
    mean_effect: float
    nonzero_pairs: int
    two_sided_p_value: float | None
    status: str


@dataclass(frozen=True, slots=True)
class CausalFourCellAnalysis:
    cell_means: tuple[tuple[str, float], ...]
    selection: CrossValidatedSelection
    contrasts: tuple[FactorialContrast, ...]


def _validate_complete(
    scores: Mapping[str, Mapping[str, float]],
    games: Sequence[str],
) -> None:
    expected = set(games)
    if len(expected) != len(games) or not scores:
        raise ValueError("games must be unique and candidate scores non-empty")
    for candidate, values in scores.items():
        if set(values) != expected:
            raise ValueError(f"candidate {candidate} does not have the exact frozen game set")
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values.values()):
            raise ValueError(f"candidate {candidate} has a non-numeric score")


def cross_validated_selection(
    scores: Mapping[str, Mapping[str, float]],
    folds: Mapping[str, int],
    *,
    tie_break_order: Sequence[str],
) -> CrossValidatedSelection:
    games = tuple(folds)
    _validate_complete(scores, games)
    if set(scores) != set(tie_break_order):
        raise ValueError("tie-break order must contain each candidate exactly once")
    fold_ids = sorted(set(folds.values()))
    if len(fold_ids) < 2 or any(not isinstance(value, int) for value in fold_ids):
        raise ValueError("at least two integer folds are required")
    rank = {candidate: index for index, candidate in enumerate(tie_break_order)}
    choices: list[str] = []
    held_out: list[float] = []
    for fold in fold_ids:
        training = [game for game in games if folds[game] != fold]
        testing = [game for game in games if folds[game] == fold]
        if not training or not testing:
            raise ValueError("each fold requires training and held-out games")
        means = {
            candidate: fmean(values[game] for game in training)
            for candidate, values in scores.items()
        }
        choice = min(means, key=lambda candidate: (-means[candidate], rank[candidate]))
        choices.append(choice)
        held_out.extend(scores[choice][game] for game in testing)
    full_means = {
        candidate: fmean(values[game] for game in games)
        for candidate, values in scores.items()
    }
    fixed = min(full_means, key=lambda candidate: (-full_means[candidate], rank[candidate]))
    return CrossValidatedSelection(
        fold_choices=tuple(choices),
        held_out_scores=tuple(held_out),
        selection_procedure_mean=fmean(held_out),
        final_fixed_candidate=fixed,
        final_fixed_candidate_mean=full_means[fixed],
    )


def paired_inference(
    candidate: Mapping[str, float],
    comparator: Mapping[str, float],
    *,
    alpha: float = 0.10,
    minimum_nonzero_pairs: int = 5,
    safety_passed: bool = True,
) -> PairedInference:
    if set(candidate) != set(comparator) or not candidate:
        raise ValueError("paired inference requires the exact same non-empty game set")
    differences = tuple(float(candidate[game]) - float(comparator[game]) for game in candidate)
    observed = fmean(differences)
    nonzero = tuple(value for value in differences if value != 0)
    if len(nonzero) < minimum_nonzero_pairs:
        return PairedInference(observed, len(nonzero), None, "Provisional primary")
    exceedances = 0
    permutations = 1 << len(nonzero)
    for signs in itertools.product((-1.0, 1.0), repeat=len(nonzero)):
        permuted = sum(sign * value for sign, value in zip(signs, nonzero)) / len(differences)
        if permuted >= observed - 1e-15:
            exceedances += 1
    p_value = exceedances / permutations
    status = (
        "Accepted"
        if safety_passed and observed > 0 and p_value <= alpha
        else "Provisional primary"
    )
    return PairedInference(observed, len(nonzero), p_value, status)


def _factorial_contrast(
    name: str,
    values: Mapping[str, float],
    *,
    minimum_nonzero_pairs: int,
) -> FactorialContrast:
    ordered = tuple((game, float(value)) for game, value in values.items())
    observed = fmean(value for _, value in ordered)
    nonzero = tuple(value for _, value in ordered if value != 0)
    if len(nonzero) < minimum_nonzero_pairs:
        return FactorialContrast(
            name, ordered, observed, len(nonzero), None, "Provisional"
        )
    exceedances = 0
    permutations = 1 << len(nonzero)
    for signs in itertools.product((-1.0, 1.0), repeat=len(nonzero)):
        permuted = sum(sign * value for sign, value in zip(signs, nonzero)) / len(ordered)
        if abs(permuted) >= abs(observed) - 1e-15:
            exceedances += 1
    return FactorialContrast(
        name,
        ordered,
        observed,
        len(nonzero),
        exceedances / permutations,
        "Estimable",
    )


def causal_four_cell_analysis(
    scores: Mapping[str, Mapping[str, float]],
    folds: Mapping[str, int],
    *,
    tie_break_order: Sequence[str] = E1_FACTORIAL_CELLS,
    minimum_nonzero_pairs: int = 5,
) -> CausalFourCellAnalysis:
    """Analyze the frozen 2x2 E1 design using paired game-level contrasts.

    Representation is coded F minus R, safe operations are coded C minus S,
    and interaction is the C representation effect minus the S representation
    effect. The same game set is required in every cell.
    """
    if tuple(tie_break_order) != E1_FACTORIAL_CELLS or set(scores) != set(E1_FACTORIAL_CELLS):
        raise ValueError("causal E1 analysis requires the exact frozen four-cell design")
    games = tuple(folds)
    _validate_complete(scores, games)
    if minimum_nonzero_pairs < 1:
        raise ValueError("minimum_nonzero_pairs must be positive")

    sr, sf, cr, cf = (scores[cell] for cell in E1_FACTORIAL_CELLS)
    representation = {
        game: 0.5 * ((sf[game] - sr[game]) + (cf[game] - cr[game]))
        for game in games
    }
    safe_operations = {
        game: 0.5 * ((cr[game] - sr[game]) + (cf[game] - sf[game]))
        for game in games
    }
    interaction = {
        game: (cf[game] - cr[game]) - (sf[game] - sr[game])
        for game in games
    }
    return CausalFourCellAnalysis(
        cell_means=tuple(
            (cell, fmean(scores[cell][game] for game in games))
            for cell in E1_FACTORIAL_CELLS
        ),
        selection=cross_validated_selection(
            scores, folds, tie_break_order=tie_break_order
        ),
        contrasts=tuple(
            _factorial_contrast(
                name, values, minimum_nonzero_pairs=minimum_nonzero_pairs
            )
            for name, values in (
                ("representation_F_minus_R", representation),
                ("safe_operations_C_minus_S", safe_operations),
                ("interaction_difference_in_differences", interaction),
            )
        ),
    )
