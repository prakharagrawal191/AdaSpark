"""Day-31 evaluation specification: scope, split authorization, cost projection.

PLAN line 277 (frozen, verbatim):

    | 31 | Eval harness + B1/B2 | frozen test set; static baselines tuned on
    validation | configs frozen |

Day 31 BUILDS the harness, DECLARES what later days will run, SELECTS B1/B2 on
the VALIDATION split and FREEZES the TEST-split identity. It executes nothing on
the test split: EXP-005 (~245 runs) is Day 32-33 and EXP-006 (~100 runs) is
Day 34 (PLAN lines 312-313); ARCHITECTURE_FREEZE line 73 states "Frozen policies
evaluated once on test (EXP-005/006)".

What this package owns
----------------------
    evaluation specification | split AUTHORIZATION | frozen baseline loading |
    configuration-freeze verification | execution ORCHESTRATION | aggregation |
    provenance

What it deliberately does NOT own (all of it already exists and is frozen)
-------------------------------------------------------------------------
Spark sessions (``sparkrl.spark.session``), timed execution and warm-up
(``sparkrl.spark.runner``), event-log parsing (``sparkrl.monitoring``), metric
merging and the ``usable`` definition (``sparkrl.monitoring.merge``),
configuration identity and fingerprints (``sparkrl.experiments.grid``), split
classification (``sparkrl.experiments.spec.split_of``) and run execution
(``sparkrl.experiments.runner.execute_run``).

Split authority
---------------
``sparkrl.experiments.spec.split_of`` is the single authority and is NOT
re-implemented, re-derived or weakened here. This module adds only an explicit
AUTHORIZATION layer on top of it: a stage declares which split it may touch, and
any cell that disagrees raises :class:`SplitAuthorizationError` before anything
is read, resolved or executed.
"""
from __future__ import annotations

from typing import Any, Sequence

from sparkrl.experiments.grid import (ConfigPoint, GRID_VERSION, build_grid,
                                      grid_fingerprint,)
from sparkrl.experiments.spec import TEST, TRAIN, VALIDATION, split_of
from sparkrl.workloads.base import FAMILIES, SCALES, SEEDS

EVAL_SPEC_VERSION = "eval-spec/v1"
EXPERIMENT_ID = "EXP-003"

# PLAN section 22: the primary metric is median end-to-end execution time.
# ``execution_time_s`` is the frozen Day-3 runner clock (warm-up excluded); no
# other clock is admissible.
SELECTION_METRIC = "execution_time_s"
SELECTION_METRIC_SOURCE = "runner"
SELECTION_STATISTIC = "median"
SELECTION_DIRECTION = "lower_is_better"

# PLAN section 23: "all evaluation = 5 repetitions x fixed seeds, medians analyzed".
EVALUATION_REPETITIONS = 5

# PLAN line 310, EXP-003 register row: "~30" runs.
EXP003_PLAN_RUN_ESTIMATE = 30

# PLAN lines 153/154 - the two frozen static baselines Day 31 must produce.
B1_DEFINITION = "Static global: one config tuned on validation, used everywhere"
B2_DEFINITION = "Static per-family: best validation-grid config per family"
BASELINES_IN_SCOPE: tuple[str, ...] = ("B0", "B1", "B2")

# -- tie-break (PRE-DECLARED) -------------------------------------------------
# PLAN freezes NO tie-break rule for baseline selection. Inventing one after
# looking at measurements would be a post-hoc degree of freedom, so the rule is
# declared here, in advance of any validation observation existing, and mirrors
# the already-frozen Day-26 agent rule "ties break to the LOWEST action index".
TIE_BREAK_RULE = "lowest_grid_index"
TIE_BREAK_NOTE = (
    "PLAN freezes no tie-break rule for B1/B2 selection. This rule was declared "
    "on Day 31 BEFORE any validation observation was measured, and mirrors the "
    "frozen Day-26 agent rule 'ties break to the LOWEST action index'. Grid order "
    "is frozen by sparkrl.experiments.grid (GRID_VERSION " + GRID_VERSION + ").")

# Pre-declared eligibility rule (also frozen before any measurement exists).
# Medians taken over DIFFERENT cell panels are not comparable, so a candidate is
# eligible only if it has at least this many usable observations in EVERY cell of
# the scope it is being selected over.
MIN_USABLE_PER_CELL = 1


class SplitAuthorizationError(RuntimeError):
    """A cell was offered to a stage not authorized for that split.

    Modelled on ``sparkrl.rl.env.SplitViolation``: the guard is code, not prose.
    """


class TestSplitSealed(RuntimeError):
    """A TEST-split EXECUTION was attempted. Day 31 may declare, never execute."""


def authorize_cell(required_split: str, family: str, scale: str, seed: int, *,
                   stage: str) -> str:
    """Authorize one cell for a stage, or refuse loudly.

    ``split_of`` remains the sole classifier; this only asserts agreement.
    """
    if required_split not in (TRAIN, VALIDATION, TEST):
        raise ValueError(f"unknown required split {required_split!r}")
    split = split_of(family, scale, seed)
    if split != required_split:
        raise SplitAuthorizationError(
            f"{stage} is authorized for split={required_split!r} only; "
            f"{family}/{scale}/seed{seed} is split={split!r}. "
            f"No test metric may influence training or tuning (PLAN section 18).")
    return split


def authorize_validation_cell(family: str, scale: str, seed: int, *,
                              stage: str = "B1/B2 selection") -> str:
    """The selection path. VALIDATION and nothing else."""
    return authorize_cell(VALIDATION, family, scale, seed, stage=stage)


def authorize_test_cell(family: str, scale: str, seed: int, *,
                        stage: str = "EXP-005/006 test evaluation") -> str:
    """The test path. TEST and nothing else. NOT invoked on Day 31.

    Authorizing a test cell is not the same as being allowed to run it: the
    execution seal lives in :func:`assert_test_execution_permitted`.
    """
    return authorize_cell(TEST, family, scale, seed, stage=stage)


def assert_test_execution_permitted() -> None:
    """Always refuses. The test split is opened by EXP-005/006, not by Day 31."""
    raise TestSplitSealed(
        "Day 31 builds the harness and freezes the test-set IDENTITY; it executes "
        "no test run. EXP-005 (test split, ~245 runs) is Day 32-33 and EXP-006 "
        "(unseen L/F4/seeds, ~100 runs) is Day 34 (PLAN lines 312-313). Opening "
        "the seal is an operator decision recorded as a DEC, not a code change.")


# -- scope --------------------------------------------------------------------
def cells_for_split(split: str) -> tuple[tuple[str, str, int], ...]:
    """Every (family, scale, seed) cell classified into ``split`` by split_of."""
    return tuple((fam, scale, seed)
                 for fam in FAMILIES for scale in SCALES for seed in SEEDS
                 if split_of(fam, scale, seed) == split)


def validation_cells() -> tuple[tuple[str, str, int], ...]:
    return cells_for_split(VALIDATION)


def test_cells() -> tuple[tuple[str, str, int], ...]:
    return cells_for_split(TEST)


def validation_families() -> tuple[str, ...]:
    """Families that actually have validation cells (B2 is selected per family)."""
    seen: list[str] = []
    for fam, _scale, _seed in validation_cells():
        if fam not in seen:
            seen.append(fam)
    return tuple(seen)


def selection_candidates() -> tuple[ConfigPoint, ...]:
    """The candidate set for B1/B2: the 12 frozen grid configurations.

    B0 is excluded by definition - PLAN calls B1/B2 the best *validation-grid*
    configuration, and B0 is the reference condition they are compared against,
    not a candidate to be selected.
    """
    return build_grid(include_b0=False)


# -- cost projection (computes, never executes) -------------------------------
def project_cost(repetitions: int = EVALUATION_REPETITIONS) -> dict[str, Any]:
    """Project the execution count for selection and EXP-003. Runs NOTHING."""
    if repetitions < 1:
        raise ValueError(f"repetitions must be >= 1, got {repetitions}")
    cells = validation_cells()
    candidates = selection_candidates()
    n_cells, n_cand = len(cells), len(candidates)

    # B1/B2 selection uses ONE repetition per cell (the task's independently
    # verified calculation: 12 configs x 8 cells x 1 rep = 96 executions).
    selection_repetitions = 1
    selection_runs = n_cells * n_cand * selection_repetitions
    comparison_runs = n_cells * len(BASELINES_IN_SCOPE) * repetitions
    # Selection and comparison use DIFFERENT repetition counts (1 vs 5), so the
    # selection grid CANNOT be reused for the comparison: every comparison run is
    # additional. The combined cost is the sum of both phases.
    comparison_additional_runs = comparison_runs
    minimum_total = selection_runs + comparison_additional_runs

    return {
        "projection_version": EVAL_SPEC_VERSION,
        "executed": False,
        "repetitions": repetitions,
        "repetitions_authority": (
            "PLAN section 23: all evaluation = 5 repetitions x fixed seeds, "
            "medians analyzed"),
        "validation_cells": [
            {"family": f, "scale": s, "seed": d} for f, s, d in cells],
        "validation_cell_count": n_cells,
        "candidate_configurations": [c.name for c in candidates],
        "candidate_count": n_cand,
        "b1_b2_selection": {
            "formula": "candidates x validation_cells x 1_repetition",
            "runs": selection_runs,
            "repetitions": selection_repetitions,
            "note": (
                "Independently verified: 12 configs x 8 cells x 1 rep = 96 executions. "
                "One repetition per cell suffices to identify the best grid config."),
        },
        "exp003_comparison": {
            "strategies": list(BASELINES_IN_SCOPE),
            "formula": "strategies x validation_cells x repetitions",
            "runs": comparison_runs,
            "repetitions": repetitions,
            "additional_runs_beyond_selection": comparison_additional_runs,
            "reuse_note": (
                "Selection uses 1 rep, comparison uses {reps} reps; at different "
                "repetition counts the selection grid cannot be reused for the "
                "comparison, so every comparison run is additional. Combined cost "
                "is the sum of both phases ({sel} + {cmp} = {tot})."
            ).format(reps=repetitions, sel=selection_runs,
                     cmp=comparison_additional_runs, tot=minimum_total),
        },
        "minimum_total_runs": minimum_total,
        "plan_estimate_runs": EXP003_PLAN_RUN_ESTIMATE,
        "plan_estimate_source": "PLAN line 310, EXP-003 register row ('~30')",
        "shortfall_runs": minimum_total - EXP003_PLAN_RUN_ESTIMATE,
        "shortfall_note": (
            "PLANNING-BUDGET DISCREPANCY: the independently verified combined "
            "projection is {proj} runs ({sel} selection + {cmp} comparison); "
            "PLAN line 310 estimates ~{plan} runs. The gap of {gap} runs is "
            "reported, not resolved: how much of it to spend is an operator / "
            "supervisor decision, not a Day-31 code change."
        ).format(proj=minimum_total, sel=selection_runs,
                 cmp=comparison_additional_runs,
                 plan=EXP003_PLAN_RUN_ESTIMATE,
                 gap=minimum_total - EXP003_PLAN_RUN_ESTIMATE),
        "budget_note": (
            "EXP-003 is a SEPARATE register line (PLAN line 310) and is NOT charged "
            "to the frozen 500-execution TRAINING cap (SC6)."),
        "spark_executions_performed_by_this_projection": 0,
    }


# -- the versioned evaluation specification -----------------------------------
def build_evaluation_spec(base_config: Any,
                          repetitions: int = EVALUATION_REPETITIONS
                          ) -> dict[str, Any]:
    """Declare what a later day WILL run. Executes nothing.

    ``base_config`` is the loaded frozen ``configs/baseline_b0.yaml`` SparkConfig;
    the warm-up / timeout / AQE facts are READ from it rather than restated, so
    the declared design cannot drift from the executed one.
    """
    candidates = selection_candidates()
    if base_config.aqe_enabled:
        raise ValueError(
            "base configuration has AQE enabled; the main study is AQE-off "
            "(PLAN sections 7/11). AQE-on is B0'/EXP-005b, not EXP-003.")
    return {
        "schema_version": EVAL_SPEC_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "declared_on": "Day 31 (PLAN line 277)",
        "executed": False,
        "baselines": {
            "B0": {"definition": "Spark default, out-of-box settings pinned",
                   "source": "configs/baseline_b0.yaml", "selected": False},
            "B1": {"definition": B1_DEFINITION, "scope": "global",
                   "selected_on": VALIDATION},
            "B2": {"definition": B2_DEFINITION, "scope": "per_family",
                   "selected_on": VALIDATION},
        },
        "split_authority": "sparkrl.experiments.spec.split_of",
        "selection_split": VALIDATION,
        "validation_cells": [{"family": f, "scale": s, "seed": d}
                             for f, s, d in validation_cells()],
        "validation_families": list(validation_families()),
        "test_split_status": "DECLARED_AND_SEALED (identity in test_freeze.json)",
        "test_cell_count": len(test_cells()),
        "frozen_configurations": {
            "grid_version": GRID_VERSION,
            "grid_fingerprint": grid_fingerprint(candidates),
            "candidate_count": len(candidates),
            "candidates": [c.to_dict() for c in candidates],
        },
        "repetitions": repetitions,
        "warmup_policy": {
            "warmup_runs": base_config.warmup_runs,
            "warmup_micro_job": base_config.warmup_micro_job,
            "warmup_excluded_from_timing": True,
            "owner": "sparkrl.spark.runner (Day 3, frozen)",
        },
        "aqe_enabled": base_config.aqe_enabled,
        "timing_semantics": {
            "metric": SELECTION_METRIC,
            "required_source": SELECTION_METRIC_SOURCE,
            "clock": "Day-3 runner clock, warm-up excluded",
            "note": ("a run whose execution_time_source is not the runner clock is "
                     "refused as unusable by sparkrl.experiments.runner"),
        },
        "metrics": {
            "primary": SELECTION_METRIC,
            "primary_statistic": SELECTION_STATISTIC,
            "direction": SELECTION_DIRECTION,
            "secondary": ["task duration CV", "spill_disk_MB per input GB"],
            "authority": "PLAN section 22",
        },
        "failure_handling": {
            "validity_rule": ("an observation counts only when RunMetrics.usable is "
                              "true (sparkrl.monitoring.merge, Day 19)"),
            "unusable_runs": "counted and reported, never silently dropped",
            "statuses": ["COMPLETED", "INCOMPLETE", "FAILED", "SKIPPED"],
            "timeout_seconds": base_config.timeout_seconds,
        },
        "tie_break": {"rule": TIE_BREAK_RULE, "note": TIE_BREAK_NOTE},
        "eligibility": {
            "min_usable_per_cell": MIN_USABLE_PER_CELL,
            "note": ("medians over different cell panels are not comparable, so a "
                     "candidate missing a cell is reported ineligible, not ranked"),
        },
        "fairness": (
            "identical code path, seeds, repetitions, warm-up and timeouts for every "
            "strategy (PLAN section 17)"),
        "projection": project_cost(repetitions),
    }


def summarize_projection(projection: dict[str, Any]) -> str:
    """Human-readable projection block. Pure formatting, no computation."""
    lines = [
        "Day-31 cost projection (EXP-003 / B1 / B2). NOTHING WAS EXECUTED.",
        "",
        "  repetitions (PLAN section 23, frozen)   : {}".format(
            projection["repetitions"]),
        "  validation cells                        : {}".format(
            projection["validation_cell_count"]),
        "  candidate configurations (frozen grid)  : {}".format(
            projection["candidate_count"]),
        "",
        "  (i)  B1/B2 selection   {} x {} x {} = {} runs".format(
            projection["candidate_count"], projection["validation_cell_count"],
            projection["b1_b2_selection"]["repetitions"],
            projection["b1_b2_selection"]["runs"]),
        "  (ii) EXP-003 B0/B1/B2  {} x {} x {} = {} runs".format(
            len(projection["exp003_comparison"]["strategies"]),
            projection["validation_cell_count"],
            projection["exp003_comparison"]["repetitions"],
            projection["exp003_comparison"]["runs"]),
        "       additional beyond (i): {} runs (different rep counts, no reuse)".format(
            projection["exp003_comparison"]["additional_runs_beyond_selection"]),
        "",
        "  combined (i + ii)                       : {} runs".format(
            projection["minimum_total_runs"]),
        "  PLAN line 310 estimate                  : ~{} runs".format(
            projection["plan_estimate_runs"]),
        "  shortfall (projected - plan)            : {} runs".format(
            projection["shortfall_runs"]),
        "",
        "  " + projection["shortfall_note"],
        "  " + projection["budget_note"],
        "",
        "  Spark executions performed by this projection: {}".format(
            projection["spark_executions_performed_by_this_projection"]),
    ]
    return "\n".join(lines)


def validation_cell_list(cells: Sequence[tuple[str, str, int]] | None = None
                         ) -> list[dict[str, Any]]:
    """Serializable validation-cell list (used by the artifacts)."""
    cells = validation_cells() if cells is None else cells
    return [{"family": f, "scale": s, "seed": d} for f, s, d in cells]
