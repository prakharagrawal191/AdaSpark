"""B1/B2 selection on the VALIDATION split - and structurally nowhere else.

Frozen definitions (PLAN lines 153-154, implemented exactly, nothing invented):

    B1 | Static global     | one config tuned on validation, used everywhere
    B2 | Static per-family | best validation-grid config per family

Leakage prevention is STRUCTURAL, not documentary
-------------------------------------------------
:func:`select_baselines` accepts only :class:`ValidationObservation` values and
runs every one of them through ``authorize_validation_cell`` -> ``split_of``
before any arithmetic happens. A single TEST (or TRAIN) cell in the input raises
``SplitAuthorizationError`` and no selection is produced. There is no flag, no
keyword and no code path in this module that admits a non-validation cell.

This module is pure: it reads no files, opens no Spark session and executes
nothing. It turns observations into a selection, and that is all.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from sparkrl.evaluation.spec import (MIN_USABLE_PER_CELL, SELECTION_DIRECTION,
                                     SELECTION_METRIC, SELECTION_METRIC_SOURCE,
                                     SELECTION_STATISTIC, TIE_BREAK_NOTE,
                                     TIE_BREAK_RULE, authorize_validation_cell,
                                     selection_candidates, validation_cells,)
from sparkrl.experiments.spec import VALIDATION

SELECTION_VERSION = "eval-selection/v1"


class NoEligibleCandidate(RuntimeError):
    """Every candidate failed the pre-declared eligibility rule for a scope."""


@dataclass(frozen=True)
class ValidationObservation:
    """One measured observation on a validation cell.

    ``usable`` is the frozen Day-19 validity definition, carried through
    unchanged; this module never re-derives it.
    """

    family: str
    scale: str
    seed: int
    config_name: str
    grid_index: int
    rep: int
    execution_time_s: float | None
    usable: bool
    execution_time_source: str | None = SELECTION_METRIC_SOURCE

    @property
    def cell(self) -> tuple[str, str, int]:
        return (self.family, self.scale, self.seed)

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "ValidationObservation":
        """Build from a run record written by ``sparkrl.experiments.runner``."""
        run_spec = record.get("run_spec") or {}
        metrics = record.get("metrics") or {}
        grid_index = run_spec.get("config_grid_index")
        if grid_index is None:
            raise ValueError(
                f"run {run_spec.get('run_id')!r} has no config_grid_index; B0 (the "
                f"reference condition) is not a B1/B2 candidate")
        return cls(
            family=str(run_spec["family"]),
            scale=str(run_spec["scale"]),
            seed=int(run_spec["seed"]),
            config_name=str(run_spec["config_name"]),
            grid_index=int(grid_index),
            rep=int(run_spec.get("rep", 1)),
            execution_time_s=metrics.get(SELECTION_METRIC),
            usable=bool(metrics.get("usable", False)),
            execution_time_source=metrics.get("execution_time_source"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family, "scale": self.scale, "seed": self.seed,
            "config_name": self.config_name, "grid_index": self.grid_index,
            "rep": self.rep, SELECTION_METRIC: self.execution_time_s,
            "usable": self.usable,
            "execution_time_source": self.execution_time_source,
        }


@dataclass(frozen=True)
class CandidateResult:
    """One candidate configuration scored over one scope."""

    config_name: str
    grid_index: int
    n_usable: int
    n_unusable: int
    cells_covered: int
    cells_required: int
    median_execution_time_s: float | None
    eligible: bool
    ineligible_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "config_name": self.config_name,
            "grid_index": self.grid_index,
            "n_usable": self.n_usable,
            "n_unusable": self.n_unusable,
            "cells_covered": self.cells_covered,
            "cells_required": self.cells_required,
            "median_" + SELECTION_METRIC: self.median_execution_time_s,
            "eligible": self.eligible,
            "ineligible_reason": self.ineligible_reason,
        }


@dataclass(frozen=True)
class BaselineSelection:
    """The frozen B1/B2 outcome. Contains VALIDATION results only."""

    b1_config_name: str
    b1_results: tuple[CandidateResult, ...]
    b2_config_names: dict[str, str]
    b2_results: dict[str, tuple[CandidateResult, ...]]
    scope_cells: tuple[tuple[str, str, int], ...]
    n_observations: int
    n_usable: int
    n_unusable: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "selection_version": SELECTION_VERSION,
            "split": VALIDATION,
            "metric": SELECTION_METRIC,
            "metric_source_required": SELECTION_METRIC_SOURCE,
            "statistic": SELECTION_STATISTIC,
            "direction": SELECTION_DIRECTION,
            "tie_break": {"rule": TIE_BREAK_RULE, "note": TIE_BREAK_NOTE},
            "eligibility": {"min_usable_per_cell": MIN_USABLE_PER_CELL},
            "validation_scope": [{"family": f, "scale": s, "seed": d}
                                 for f, s, d in self.scope_cells],
            "observation_counts": {
                "total": self.n_observations,
                "usable": self.n_usable,
                "unusable_excluded": self.n_unusable,
            },
            "B1": {
                "scope": "global",
                "selected_config": self.b1_config_name,
                "candidates": [r.to_dict() for r in self.b1_results],
            },
            "B2": {
                "scope": "per_family",
                "selected_config_by_family": dict(sorted(
                    self.b2_config_names.items())),
                "candidates_by_family": {
                    fam: [r.to_dict() for r in results]
                    for fam, results in sorted(self.b2_results.items())},
            },
        }


def _median(values: Sequence[float]) -> float | None:
    return round(statistics.median(values), 6) if values else None


def _score(candidate_names: Sequence[tuple[str, int]],
           observations: Sequence[ValidationObservation],
           scope_cells: Sequence[tuple[str, str, int]]) -> list[CandidateResult]:
    """Score every candidate over one scope. Unusable runs are counted, not dropped."""
    results: list[CandidateResult] = []
    required = set(scope_cells)
    for name, grid_index in candidate_names:
        mine = [o for o in observations if o.config_name == name]
        usable = [o for o in mine
                  if o.usable and o.execution_time_s is not None]
        unusable = len(mine) - len(usable)
        covered = {c for c in required
                   if sum(1 for o in usable if o.cell == c) >= MIN_USABLE_PER_CELL}
        missing = sorted(required - covered)
        reason = None
        if missing:
            reason = (
                "fewer than {n} usable observation(s) on cell(s) {cells}; medians "
                "over unequal panels are not comparable".format(
                    n=MIN_USABLE_PER_CELL,
                    cells=[f"{f}/{s}/seed{d}" for f, s, d in missing]))
        results.append(CandidateResult(
            config_name=name, grid_index=grid_index,
            n_usable=len(usable), n_unusable=unusable,
            cells_covered=len(covered), cells_required=len(required),
            median_execution_time_s=_median(
                [float(o.execution_time_s) for o in usable]),
            eligible=not missing, ineligible_reason=reason))
    return sorted(results, key=lambda r: r.grid_index)


def _pick(results: Sequence[CandidateResult], scope: str) -> CandidateResult:
    """Lowest median wins; ties break to the LOWEST frozen grid index."""
    eligible = [r for r in results
                if r.eligible and r.median_execution_time_s is not None]
    if not eligible:
        raise NoEligibleCandidate(
            f"no candidate is eligible over scope {scope!r}: every configuration is "
            f"missing usable observations on at least one validation cell. "
            f"Selection is refused rather than made on an incomplete panel.")
    return min(eligible,
               key=lambda r: (r.median_execution_time_s, r.grid_index))


def select_baselines(validation_observations: Iterable[ValidationObservation],
                     ) -> BaselineSelection:
    """Select B1 (global) and B2 (per family) from VALIDATION observations only.

    Every observation is authorized against ``split_of`` before it is used. A
    non-validation cell raises ``SplitAuthorizationError`` and nothing is
    selected. The candidate set is the frozen 12-configuration grid; B0 is the
    reference condition, never a candidate.
    """
    observations = list(validation_observations)
    if not observations:
        raise ValueError("no validation observations supplied; nothing to select")

    candidates = selection_candidates()
    candidate_index = {c.name: int(c.grid_index) for c in candidates}
    candidate_names = sorted(candidate_index.items(), key=lambda kv: kv[1])
    scope = validation_cells()
    scope_set = set(scope)

    for obs in observations:
        # The structural guard: split_of is asked about EVERY observation before
        # any of it reaches the arithmetic below.
        authorize_validation_cell(obs.family, obs.scale, obs.seed)
        if obs.cell not in scope_set:
            raise ValueError(
                f"{obs.family}/{obs.scale}/seed{obs.seed} is not in the declared "
                f"validation scope")
        if obs.config_name not in candidate_index:
            raise ValueError(
                f"{obs.config_name!r} is not one of the {len(candidate_index)} frozen "
                f"grid candidates; B1/B2 are selected from the validation grid only")
        if candidate_index[obs.config_name] != obs.grid_index:
            raise ValueError(
                f"{obs.config_name!r} carries grid_index {obs.grid_index}, frozen grid "
                f"says {candidate_index[obs.config_name]}")
        if obs.usable and obs.execution_time_source not in (
                None, SELECTION_METRIC_SOURCE):
            raise ValueError(
                f"{obs.config_name} on {obs.family}/{obs.scale}/seed{obs.seed}: "
                f"execution_time_source is {obs.execution_time_source!r}, not the "
                f"authoritative {SELECTION_METRIC_SOURCE!r} clock")

    n_usable = sum(1 for o in observations
                   if o.usable and o.execution_time_s is not None)

    b1_results = _score(candidate_names, observations, scope)
    b1 = _pick(b1_results, "global")

    b2_results: dict[str, tuple[CandidateResult, ...]] = {}
    b2_names: dict[str, str] = {}
    families = sorted({f for f, _s, _d in scope})
    for family in families:
        fam_cells = [c for c in scope if c[0] == family]
        fam_obs = [o for o in observations if o.family == family]
        results = _score(candidate_names, fam_obs, fam_cells)
        b2_results[family] = tuple(results)
        b2_names[family] = _pick(results, family).config_name

    return BaselineSelection(
        b1_config_name=b1.config_name,
        b1_results=tuple(b1_results),
        b2_config_names=b2_names,
        b2_results=b2_results,
        scope_cells=tuple(scope),
        n_observations=len(observations),
        n_usable=n_usable,
        n_unusable=len(observations) - n_usable)


def resolve_baseline_config(selection: BaselineSelection, baseline: str,
                            family: str):
    """Frozen-baseline loading: (B1|B2, family) -> the frozen ConfigPoint."""
    by_name = {c.name: c for c in selection_candidates()}
    if baseline == "B1":
        return by_name[selection.b1_config_name]
    if baseline == "B2":
        try:
            return by_name[selection.b2_config_names[family]]
        except KeyError:
            raise KeyError(
                f"no B2 configuration selected for family {family!r}") from None
    raise ValueError(
        f"unknown baseline {baseline!r}; this module selects B1 and B2 only "
        f"(B0 is the pinned reference in configs/baseline_b0.yaml)")
