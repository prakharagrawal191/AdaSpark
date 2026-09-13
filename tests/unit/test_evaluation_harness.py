"""Day-31 evaluation harness: offline checks. No Spark, no test-split execution.

Every observation used here is a fixture built in-process. Nothing is executed,
nothing is measured, and no artifact is written outside tmp_path.
"""
from __future__ import annotations

import json

import pytest

from sparkrl.evaluation import freeze as freeze_mod
from sparkrl.evaluation.orchestration import (EvaluationExecutionBlocked,
                                              execute_test_run,
                                              preflight_blockers,
                                              validation_run_plan,)
from sparkrl.evaluation.selection import (NoEligibleCandidate,
                                          ValidationObservation,
                                          resolve_baseline_config,
                                          select_baselines,)
from sparkrl.evaluation.spec import (SplitAuthorizationError, authorize_validation_cell,
                                     project_cost, selection_candidates,
                                     validation_cells,)
# aliased on import: pytest would otherwise collect `test_cells` as a test case
# and warn about the `TestSplitSealed` class.
from sparkrl.evaluation.spec import TestSplitSealed as SealedError
from sparkrl.evaluation.spec import test_cells as frozen_test_cells
from sparkrl.experiments.spec import RunSpec, split_of
from sparkrl.spark.config import SparkConfig

pytestmark = [pytest.mark.unit]


CANDIDATES = selection_candidates()


def _observations(time_for, *, usable_for=lambda o: True, reps=1):
    out = []
    for family, scale, seed in validation_cells():
        for point in CANDIDATES:
            for rep in range(1, reps + 1):
                obs = ValidationObservation(
                    family=family, scale=scale, seed=seed,
                    config_name=point.name, grid_index=point.grid_index,
                    rep=rep, execution_time_s=None, usable=True)
                out.append(ValidationObservation(
                    family=family, scale=scale, seed=seed,
                    config_name=point.name, grid_index=point.grid_index,
                    rep=rep, execution_time_s=time_for(obs),
                    usable=usable_for(obs)))
    return out


# -- scope --------------------------------------------------------------------
def test_scope_matches_the_frozen_split():
    cells = validation_cells()
    assert len(cells) == 8
    assert {c[2] for c in cells} == {3}
    assert {c[1] for c in cells} == {"small", "medium"}
    assert len(frozen_test_cells()) == 43
    assert len(CANDIDATES) == 12
    assert all(split_of(*c) == "validation" for c in cells)


# -- A. split authorization ---------------------------------------------------
def test_validation_authorization_refuses_train_and_test():
    authorize_validation_cell("F1_agg", "small", 3)
    with pytest.raises(SplitAuthorizationError):
        authorize_validation_cell("F1_agg", "small", 0)        # train
    with pytest.raises(SplitAuthorizationError):
        authorize_validation_cell("F4_ski", "large", 4)        # test


def test_test_path_authorizes_but_never_executes():
    family, scale, seed = frozen_test_cells()[0]
    run_spec = RunSpec(run_id="x", family=family, scale=scale, seed=seed, rep=1,
                       config=CANDIDATES[0], split="test", timeout_seconds=300.0,
                       order_index=0, block_id="b")
    with pytest.raises(SealedError):
        execute_test_run(run_spec, None)


# -- B. selection is structurally validation-only -----------------------------
def test_selection_refuses_a_single_test_observation():
    obs = _observations(lambda o: 10.0)
    obs.append(ValidationObservation(
        family="F4_ski", scale="large", seed=4, config_name=CANDIDATES[0].name,
        grid_index=0, rep=1, execution_time_s=0.1, usable=True))
    with pytest.raises(SplitAuthorizationError):
        select_baselines(obs)


def test_b1_is_global_and_b2_is_per_family():
    fast_global = CANDIDATES[5].name            # best everywhere except F2_join
    fast_f2 = CANDIDATES[9].name                # best only inside F2_join

    def time_for(o):
        if o.family == "F2_join":
            return 5.0 if o.config_name == fast_f2 else 50.0
        return 5.0 if o.config_name == fast_global else 50.0

    selection = select_baselines(_observations(time_for, reps=3))
    assert selection.b1_config_name == fast_global
    assert selection.b2_config_names["F2_join"] == fast_f2
    assert selection.b2_config_names["F1_agg"] == fast_global
    assert resolve_baseline_config(selection, "B2", "F2_join").name == fast_f2


def test_unusable_runs_are_excluded_but_counted():
    obs = _observations(lambda o: 10.0 + o.grid_index,
                        usable_for=lambda o: o.grid_index != 0)
    selection = select_baselines(obs)
    zero = next(r for r in selection.b1_results if r.grid_index == 0)
    assert zero.n_usable == 0 and zero.n_unusable > 0
    assert zero.eligible is False and zero.median_execution_time_s is None
    assert selection.b1_config_name != CANDIDATES[0].name
    assert selection.n_unusable == zero.n_unusable
    assert selection.n_observations == selection.n_usable + selection.n_unusable


def test_refuses_to_select_when_nothing_is_eligible():
    with pytest.raises(NoEligibleCandidate):
        select_baselines(_observations(lambda o: 1.0, usable_for=lambda o: False))


# -- C. tie-break is pre-declared and deterministic ---------------------------
def test_ties_break_to_the_lowest_grid_index():
    selection = select_baselines(_observations(lambda o: 12.5))
    assert selection.b1_config_name == CANDIDATES[0].name
    assert min(c.grid_index for c in CANDIDATES) == 0
    for family in selection.b2_config_names:
        assert selection.b2_config_names[family] == CANDIDATES[0].name


# -- D. projection computes and executes nothing ------------------------------
def test_projection_arithmetic():
    p = project_cost()
    assert p["executed"] is False
    assert p["spark_executions_performed_by_this_projection"] == 0
    # Independently verified: selection = 12 configs x 8 cells x 1 rep = 96
    assert p["b1_b2_selection"]["runs"] == 12 * 8 * 1
    assert p["b1_b2_selection"]["repetitions"] == 1
    # Comparison = 3 strategies x 8 cells x 5 reps = 120
    assert p["exp003_comparison"]["runs"] == 3 * 8 * 5
    assert p["exp003_comparison"]["repetitions"] == 5
    # Combined = 96 + 120 = 216 (different rep counts, no reuse)
    assert p["minimum_total_runs"] == 96 + 120
    assert p["shortfall_runs"] == p["minimum_total_runs"] - 30
    assert p["shortfall_runs"] == 186


def test_validation_plan_is_deterministic_and_validation_only():
    cfg = SparkConfig.from_yaml("configs/baseline_b0.yaml")
    plan = validation_run_plan(cfg, repetitions=5)
    assert len(plan) == 8 * 12 * 5
    assert [r.run_id for r in plan] == [
        r.run_id for r in validation_run_plan(cfg, repetitions=5)]
    assert {r.split for r in plan} == {"validation"}


def test_calibration_is_authorized_without_weakening_the_train_guard():
    """DEC-013 Model B replaced the blocker; the guard itself is NOT weakened.

    Before DEC-013 this test asserted that preflight REPORTED a blocker, which was
    the correct invariant while validation execution was unauthorized. The signed
    decision inverts it: the calibration stage now supplies its own VALIDATION-only
    authorization, so the blocker is gone - but assert_train_only must still refuse
    everything it refused before, and TEST must still be sealed.
    """
    from sparkrl.experiments.spec import assert_train_only

    # 1. the gate is open for calibration
    assert preflight_blockers() == []

    # 2. the frozen guard is semantically UNCHANGED
    assert_train_only("F1_agg", "small", 0)                  # TRAIN still accepted
    for cell in (("F1_agg", "small", 3),                     # VALIDATION
                 ("F4_ski", "small", 0),                     # TEST family
                 ("F1_agg", "large", 0),                     # TEST scale
                 ("F1_agg", "small", 4)):                    # TEST seed
        with pytest.raises(ValueError):
            assert_train_only(*cell)

    # 3. TEST execution remains sealed regardless of the calibration gate
    from sparkrl.evaluation.orchestration import assert_test_execution_permitted
    with pytest.raises(Exception):
        assert_test_execution_permitted()


# -- E. artifacts are fingerprinted and immutable -----------------------------
def test_fingerprint_excludes_id_and_timestamp():
    body = {"schema_version": "t/v1", "payload": [1, 2, 3]}
    a = freeze_mod.seal(body, created_utc="2026-01-01T00:00:00+00:00")
    b = freeze_mod.seal(body, created_utc="2030-12-31T23:59:59+00:00")
    assert a["fingerprint"] == b["fingerprint"] == a["artifact_id"]
    assert freeze_mod.seal({**body, "payload": [1, 2]})["fingerprint"] != a["fingerprint"]


def test_artifacts_refuse_a_differing_overwrite(tmp_path):
    path = tmp_path / "artifact.json"
    a = freeze_mod.seal({"schema_version": "t/v1", "payload": 1})
    freeze_mod.write_artifact(a, path)
    freeze_mod.write_artifact(a, path)                       # identical rebuild: no-op
    assert freeze_mod.verify_artifact(path)["artifact_id"] == a["artifact_id"]
    with pytest.raises(freeze_mod.ArtifactExistsError):
        freeze_mod.write_artifact(
            freeze_mod.seal({"schema_version": "t/v1", "payload": 2}), path)


def test_tampering_is_detected(tmp_path):
    path = tmp_path / "artifact.json"
    freeze_mod.write_artifact(
        freeze_mod.seal({"schema_version": "t/v1", "cells": [{"family": "F1_agg"}]}),
        path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["cells"] = [{"family": "F4_ski"}]
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(freeze_mod.ArtifactCorrupt):
        freeze_mod.verify_artifact(path)


def test_selection_artifact_carries_no_test_cell():
    selection = select_baselines(_observations(lambda o: 10.0 + o.grid_index))
    artifact = freeze_mod.build_baseline_selection_artifact(selection)
    blob = json.dumps(artifact)
    assert "F4_ski" not in blob and "large" not in blob and '"seed": 4' not in blob
    assert artifact["split"] == "validation"
    assert artifact["contains_test_data"] is False
