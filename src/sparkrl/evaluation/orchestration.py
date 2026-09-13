"""Controlled execution ORCHESTRATION for the evaluation harness.

This module owns queue shape and authorization and NOTHING else. Every actual
measurement is delegated, unchanged, to
``sparkrl.experiments.runner.execute_run`` - which owns session creation,
warm-up, the authoritative Day-3 timing clock, the timeout, event-log parsing,
metric merging and the ``usable`` definition. No Spark call, no timer and no
parser appears here.

It is split-aware in both directions: the validation path authorizes VALIDATION
only, and the test path authorizes TEST only and then refuses to execute,
because Day 31 does not open the test split.
"""
from __future__ import annotations

import random
from typing import Any, Iterable, Sequence

from sparkrl.evaluation.selection import ValidationObservation
from sparkrl.evaluation.spec import (EVALUATION_REPETITIONS,
                                     assert_test_execution_permitted,
                                     authorize_test_cell,
                                     authorize_validation_cell,
                                     selection_candidates, validation_cells,)
from sparkrl.experiments.spec import RunSpec, VALIDATION, split_of

# Frozen queue order seed (randomized complete block design, mirroring EXP-002).
ORDER_SEED = 31


class EvaluationExecutionBlocked(RuntimeError):
    """A precondition prevents evaluation execution. Nothing was run."""


def run_id_for(family: str, scale: str, seed: int, config_name: str,
               rep: int) -> str:
    """Deterministic EXP-003 run identity (the EXP-002 helper is exp002-namespaced)."""
    if rep < 1:
        raise ValueError(f"rep must be >= 1, got {rep}")
    return f"exp003-{family}-{scale}-s{seed}-{config_name}-r{rep}".replace(
        "_", "-").lower()


def validation_run_plan(base_config: Any,
                        repetitions: int = EVALUATION_REPETITIONS
                        ) -> tuple[RunSpec, ...]:
    """The deterministic validation selection queue. Builds only; runs nothing."""
    if repetitions < 1:
        raise ValueError(f"repetitions must be >= 1, got {repetitions}")
    candidates = list(selection_candidates())
    runs: list[RunSpec] = []
    order = 0
    cells = validation_cells()
    scales = sorted({s for _f, s, _d in cells})
    for scale in scales:
        for rep in range(1, repetitions + 1):
            for family, cell_scale, seed in cells:
                if cell_scale != scale:
                    continue
                authorize_validation_cell(family, scale, seed)
                block_id = f"{family}|{scale}|rep{rep}"
                points = list(candidates)
                random.Random(f"{ORDER_SEED}|{block_id}").shuffle(points)
                for point in points:
                    runs.append(RunSpec(
                        run_id=run_id_for(family, scale, seed, point.name, rep),
                        family=family, scale=scale, seed=seed, rep=rep,
                        config=point, split=split_of(family, scale, seed),
                        timeout_seconds=float(base_config.timeout_seconds),
                        order_index=order, block_id=block_id))
                    order += 1
    ids = [r.run_id for r in runs]
    if len(set(ids)) != len(ids):
        raise ValueError("validation run plan contains duplicate run ids")
    return tuple(runs)


def preflight_blockers() -> list[str]:
    """Preconditions that would prevent executing the validation queue.

    Probed at runtime rather than asserted in prose, so the answer cannot drift
    from the code. Nothing here weakens or edits a guard; it only reports.
    """
    import inspect

    from sparkrl.experiments.runner import execute_run
    from sparkrl.experiments.spec import assert_train_only

    blockers: list[str] = []
    family, scale, seed = validation_cells()[0]

    # 1. the calibration authorization must admit this validation cell
    try:
        authorize_validation_cell(family, scale, seed)
    except Exception as exc:                       # noqa: BLE001 - reported, not raised
        blockers.append(
            "the DEC-013 calibration authorization refuses the validation cell "
            f"{family}/{scale}/seed{seed}: {exc}")

    # 2. execute_run must accept a caller-supplied guard (DEC-013 Model B), and
    #    its DEFAULT must still be the untouched TRAIN-only guard.
    params = inspect.signature(execute_run).parameters
    if "split_guard" not in params:
        blockers.append(
            "sparkrl.experiments.runner.execute_run does not accept split_guard, "
            "so the calibration stage cannot supply its own authorization "
            "(DEC-013 Model B). The EXP-003 validation queue cannot execute.")
    elif params["split_guard"].default is not assert_train_only:
        blockers.append(
            "execute_run's split_guard default is not assert_train_only; the "
            "frozen TRAIN-only behaviour of every other caller is not preserved.")
    return blockers


def execute_validation_run(run_spec: RunSpec, base_config: Any, **kwargs: Any):
    """Execute ONE validation observation by delegating to the frozen runner."""
    authorize_validation_cell(run_spec.family, run_spec.scale, run_spec.seed)
    blockers = preflight_blockers()
    if blockers:
        raise EvaluationExecutionBlocked(" | ".join(blockers))

    from sparkrl.experiments.runner import execute_run   # lazy: keeps import light

    # DEC-013 Model B: the calibration stage supplies its OWN authorization,
    # which admits VALIDATION only. assert_train_only is untouched and remains
    # execute_run's default for every other caller.
    kwargs.setdefault("split_guard", authorize_validation_cell)
    return execute_run(run_spec, base_config, **kwargs)


def execute_test_run(run_spec: RunSpec, base_config: Any, **kwargs: Any):
    """The test path. Authorizes TEST, then refuses. NOT invoked on Day 31."""
    authorize_test_cell(run_spec.family, run_spec.scale, run_spec.seed)
    assert_test_execution_permitted()      # always raises TestSplitSealed


def observations_from_records(records: Iterable[dict[str, Any]]
                              ) -> list[ValidationObservation]:
    """Aggregate stored run records into validation observations.

    Records outside the validation split are refused, not filtered out: a test
    record reaching this function means something upstream is wrong, and quietly
    dropping it would hide that.
    """
    out: list[ValidationObservation] = []
    for record in records:
        run_spec = record.get("run_spec") or {}
        authorize_validation_cell(
            str(run_spec["family"]), str(run_spec["scale"]), int(run_spec["seed"]),
            stage="validation result aggregation")
        out.append(ValidationObservation.from_record(record))
    return out


def summarize_observations(observations: Sequence[ValidationObservation]
                           ) -> dict[str, Any]:
    """Counts only - usable, unusable and coverage. No metric is claimed here."""
    usable = [o for o in observations if o.usable and o.execution_time_s is not None]
    return {
        "split": VALIDATION,
        "total": len(observations),
        "usable": len(usable),
        "unusable_excluded": len(observations) - len(usable),
        "cells_observed": len({o.cell for o in observations}),
        "configurations_observed": len({o.config_name for o in observations}),
    }
