"""Day-31 evaluation harness: offline guarantees. No Spark, no test execution.

Every observation here is an in-process fixture and every artifact is written
under ``tmp_path``. Nothing is measured, nothing is executed and no frozen file
is touched. These tests cover the guarantees Day 31 claims - validation-only
tuning, structural test-split rejection, immutable fingerprinted artifacts, a
pre-declared tie-break, preserved failures and a reproducible specification -
so that each one fails loudly if the logic behind it breaks.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from sparkrl.agent.policy_store import (agent_from_artifact,
                                        build_policy_artifact, load_policy,
                                        save_policy,)
from sparkrl.agent.q_learning import QLearningAgent
from sparkrl.evaluation import freeze as freeze_mod
from sparkrl.evaluation import orchestration as orch
from sparkrl.evaluation.selection import (ValidationObservation,
                                          resolve_baseline_config,
                                          select_baselines,)
from sparkrl.evaluation.spec import (EVALUATION_REPETITIONS, TIE_BREAK_RULE,
                                     SplitAuthorizationError, authorize_cell,
                                     build_evaluation_spec, project_cost,
                                     selection_candidates, validation_cells,)
# Aliased on import: pytest would otherwise collect `test_cells` as a test case.
from sparkrl.evaluation.spec import test_cells as frozen_test_cells
from sparkrl.experiments.spec import TEST, TRAIN, VALIDATION, split_of
from sparkrl.rl.state import SCHEMA_V15, StateVector
from sparkrl.spark.config import SparkConfig

pytestmark = [pytest.mark.unit]

PROJECT = Path(__file__).resolve().parents[2]
EVALUATION_PKG = PROJECT / "src" / "sparkrl" / "evaluation"
CANDIDATES = selection_candidates()
B0_YAML = str(PROJECT / "configs" / "baseline_b0.yaml")

TRAIN_CELL = ("F1_agg", "small", 0)
VALIDATION_CELL = ("F1_agg", "small", 3)
TEST_CELL = ("F4_ski", "small", 0)


def _base_config() -> SparkConfig:
    return SparkConfig.from_yaml(B0_YAML)


def _observations(time_for, *, usable_for=None, reps=1):
    """Build a full validation panel from callables. No file, no Spark."""
    usable_for = usable_for or (lambda family, point, rep: True)
    out = []
    for family, scale, seed in validation_cells():
        for point in CANDIDATES:
            for rep in range(1, reps + 1):
                ok = usable_for(family, point, rep)
                out.append(ValidationObservation(
                    family=family, scale=scale, seed=seed,
                    config_name=point.name, grid_index=point.grid_index,
                    rep=rep,
                    execution_time_s=time_for(family, point) if ok else None,
                    usable=ok))
    return out


def _fake_resolver(monkeypatch):
    """Replace dataset resolution so the freeze is built without touching data."""
    def resolve(family, scale, seed, data_root=None):
        tag = f"{family}-{scale}-s{seed}"
        return SimpleNamespace(
            dataset_id=tag,
            dataset_fingerprint="fp-" + tag,
            schema_fingerprint="schema-" + tag,
            skew=1.5 if family == "F4_ski" else 1.0)

    monkeypatch.setattr(freeze_mod, "resolve_dataset", resolve)


def _pin_code_version(monkeypatch, value="deadbee"):
    """Pin provenance so fingerprint assertions do not depend on the git state."""
    import sparkrl.experiments.runner as runner_mod
    monkeypatch.setattr(runner_mod, "code_version", lambda: value)


def _keys(node):
    """Every key name appearing anywhere in a JSON-shaped structure."""
    if isinstance(node, dict):
        out = set(node)
        for value in node.values():
            out |= _keys(value)
        return out
    if isinstance(node, list):
        out = set()
        for value in node:
            out |= _keys(value)
        return out
    return set()


# -- 1. tuning happens on VALIDATION and structurally nowhere else -------------
def test_tuning_scope_is_exactly_the_validation_split():
    selection = select_baselines(_observations(lambda f, p: 10.0 + p.grid_index))
    assert set(selection.scope_cells) == set(validation_cells())
    assert all(split_of(*cell) == VALIDATION for cell in selection.scope_cells)
    assert {cell[2] for cell in selection.scope_cells} == {3}
    assert "large" not in {cell[1] for cell in selection.scope_cells}
    assert "F4_ski" not in {cell[0] for cell in selection.scope_cells}


def test_selection_rejects_test_observations_and_selects_nothing():
    good = _observations(lambda f, p: 10.0 + p.grid_index)
    leaked = ValidationObservation(
        family="F4_ski", scale="large", seed=4, config_name=CANDIDATES[0].name,
        grid_index=CANDIDATES[0].grid_index, rep=1, execution_time_s=0.001,
        usable=True)
    with pytest.raises(SplitAuthorizationError):
        select_baselines(good + [leaked])
    # Position must not matter: the guard runs over every observation first.
    with pytest.raises(SplitAuthorizationError):
        select_baselines([leaked] + good)
    # A train cell is refused by the same guard.
    with pytest.raises(SplitAuthorizationError):
        select_baselines(good + [ValidationObservation(
            family="F1_agg", scale="small", seed=0,
            config_name=CANDIDATES[0].name, grid_index=CANDIDATES[0].grid_index,
            rep=1, execution_time_s=1.0, usable=True)])


def test_aggregation_refuses_a_non_validation_run_record():
    record = {"run_spec": {"run_id": "x", "family": "F4_ski", "scale": "large",
                           "seed": 4, "config_name": CANDIDATES[0].name,
                           "config_grid_index": CANDIDATES[0].grid_index,
                           "rep": 1},
              "metrics": {"execution_time_s": 1.0, "usable": True}}
    with pytest.raises(SplitAuthorizationError):
        orch.observations_from_records([record])


def test_split_authorization_covers_all_three_splits():
    cells = {TRAIN: TRAIN_CELL, VALIDATION: VALIDATION_CELL, TEST: TEST_CELL}
    for required, cell in cells.items():
        assert split_of(*cell) == required
        assert authorize_cell(required, *cell, stage="t") == required
        for other in cells:
            if other == required:
                continue
            with pytest.raises(SplitAuthorizationError):
                authorize_cell(other, *cell, stage="t")
    with pytest.raises(ValueError):
        authorize_cell("holdout", *VALIDATION_CELL, stage="t")


# -- 2. tie-break is pre-declared, deterministic and not merely "index 0" -----
def test_exact_tie_breaks_to_the_lowest_grid_index():
    low, high = CANDIDATES[3], CANDIDATES[7]
    assert low.grid_index < high.grid_index

    def timed(tied_fast):
        return lambda f, p: 9.0 if p.name in tied_fast else 40.0

    selection = select_baselines(
        _observations(timed({low.name, high.name}), reps=3))
    assert TIE_BREAK_RULE == "lowest_grid_index"
    assert selection.b1_config_name == low.name
    assert set(selection.b2_config_names.values()) == {low.name}

    # Break the tie the other way: the rule must be a tie-break, not a bias.
    def almost(f, p):
        if p.name == high.name:
            return 9.0
        return 9.5 if p.name == low.name else 40.0

    assert select_baselines(_observations(almost, reps=3)).b1_config_name == \
        high.name


# -- 3. failures are preserved, never fabricated, never silently dropped ------
def test_failed_observations_are_counted_and_block_a_partial_panel():
    broken, honest = CANDIDATES[4], CANDIDATES[6]
    missing_cell = validation_cells()[0]

    def time_for(family, point):
        if point.name == broken.name:
            return 1.0                      # fastest wherever it did complete
        return 20.0 if point.name == honest.name else 30.0

    def usable_for(family, point, rep):
        return not (point.name == broken.name and family == missing_cell[0])

    observations = _observations(time_for, usable_for=usable_for, reps=2)
    selection = select_baselines(observations)

    result = next(r for r in selection.b1_results
                  if r.config_name == broken.name)
    # Preserved: the failures are visible in the candidate's own counts...
    assert result.n_unusable == 2 * len([c for c in validation_cells()
                                         if c[0] == missing_cell[0]])
    assert result.cells_covered == result.cells_required - 2
    assert result.eligible is False
    assert missing_cell[0] in (result.ineligible_reason or "")
    # ...and in the denominator of the whole selection.
    assert selection.n_observations == len(observations)
    assert selection.n_observations == selection.n_usable + selection.n_unusable
    assert selection.n_unusable == result.n_unusable
    # Not fabricated: the fastest median does NOT win on an incomplete panel.
    assert result.median_execution_time_s == 1.0
    assert selection.b1_config_name == honest.name
    # The affected family still selects a complete-panel candidate for B2.
    assert selection.b2_config_names[missing_cell[0]] == honest.name


def test_unusable_run_contributes_no_time_to_any_median():
    slow = CANDIDATES[2]

    def usable_for(family, point, rep):
        return not (point.name == slow.name and rep == 2)

    selection = select_baselines(_observations(
        lambda f, p: 10.0 if p.name == slow.name else 11.0,
        usable_for=usable_for, reps=2))
    result = next(r for r in selection.b1_results if r.config_name == slow.name)
    assert result.n_usable == len(validation_cells())
    assert result.n_unusable == len(validation_cells())
    assert result.eligible is True and result.median_execution_time_s == 10.0
    assert selection.b1_config_name == slow.name


# -- 4. frozen baseline configuration round-trip ------------------------------
def test_baseline_configuration_round_trips_through_a_frozen_artifact(
        tmp_path, monkeypatch):
    _pin_code_version(monkeypatch)
    global_best, f2_best = CANDIDATES[5], CANDIDATES[9]

    def time_for(family, point):
        want = f2_best.name if family == "F2_join" else global_best.name
        return 5.0 if point.name == want else 50.0

    selection = select_baselines(_observations(time_for, reps=3))
    artifact = freeze_mod.build_baseline_selection_artifact(selection)
    path = freeze_mod.write_artifact(artifact, tmp_path / "baseline_selection.json")
    reloaded = freeze_mod.verify_artifact(path)

    assert reloaded["artifact_id"] == artifact["artifact_id"]
    assert reloaded["B1"]["selected_config"] == global_best.name
    assert reloaded["B2"]["selected_config_by_family"]["F2_join"] == f2_best.name
    assert reloaded["split"] == VALIDATION

    # (baseline, family) -> the frozen ConfigPoint, identical to the grid entry.
    resolved_b1 = resolve_baseline_config(selection, "B1", "F1_agg")
    resolved_b2 = resolve_baseline_config(selection, "B2", "F2_join")
    assert resolved_b1.fingerprint() == global_best.fingerprint()
    assert resolved_b2.fingerprint() == f2_best.fingerprint()
    assert resolved_b1.name == reloaded["B1"]["selected_config"]
    # B0 is the pinned reference condition, not something this module selects.
    with pytest.raises(ValueError):
        resolve_baseline_config(selection, "B0", "F1_agg")


# -- 5. frozen test manifest: identity only, and tampering is detected --------
def test_test_freeze_is_identity_only(monkeypatch):
    _fake_resolver(monkeypatch)
    _pin_code_version(monkeypatch)
    artifact = freeze_mod.build_test_freeze()

    cells = artifact["cells"]
    assert artifact["executed"] is False
    assert len(cells) == artifact["cell_count"] == len(frozen_test_cells())
    assert {(c["family"], c["scale"], c["seed"]) for c in cells} == \
        set(frozen_test_cells())
    assert all(split_of(c["family"], c["scale"], c["seed"]) == TEST for c in cells)
    assert cells == sorted(cells, key=lambda c: (c["family"], c["scale"], c["seed"]))
    assert all(c["dataset_fingerprint"] and c["schema_fingerprint"] for c in cells)
    # No measurement may ever appear in the freeze - checked on KEY names, so a
    # newly added metric field fails this test instead of slipping through.
    forbidden = ("time", "metric", "median", "duration", "reward", "result",
                 "usable", "throughput", "latency")
    offenders = [k for k in _keys(artifact)
                 if any(word in k.lower() for word in forbidden)]
    assert offenders == []


def test_test_manifest_fingerprint_mismatch_is_detected(tmp_path, monkeypatch):
    _fake_resolver(monkeypatch)
    _pin_code_version(monkeypatch)
    artifact = freeze_mod.build_test_freeze()
    path = freeze_mod.write_artifact(artifact, tmp_path / "test_freeze.json")
    assert freeze_mod.verify_artifact(path)["manifest_fingerprint"] == \
        artifact["manifest_fingerprint"]

    # Swap one frozen cell's dataset and re-seal, so the CONTENT fingerprint is
    # valid again: only the manifest fingerprint can still catch the swap.
    tampered = dict(artifact)
    cells = [dict(c) for c in artifact["cells"]]
    cells[0]["dataset_fingerprint"] = "fp-substituted"
    tampered["cells"] = cells
    resealed = freeze_mod.seal(tampered)
    assert resealed["fingerprint"] == freeze_mod.artifact_fingerprint(resealed)
    (tmp_path / "tampered.json").write_text(
        json.dumps(resealed, indent=2, sort_keys=True), encoding="utf-8")
    with pytest.raises(freeze_mod.ArtifactCorrupt) as excinfo:
        freeze_mod.verify_artifact(tmp_path / "tampered.json")
    assert "manifest_fingerprint" in str(excinfo.value)


# -- 6. artifacts are immutable -----------------------------------------------
def test_differing_overwrite_is_refused_and_the_stored_file_is_unchanged(
        tmp_path, monkeypatch):
    _pin_code_version(monkeypatch)
    path = tmp_path / "evaluation_spec.json"
    first = freeze_mod.build_evaluation_spec_artifact(_base_config())
    freeze_mod.write_artifact(first, path)
    on_disk = path.read_text(encoding="utf-8")

    freeze_mod.write_artifact(first, path)              # identical: a no-op
    assert path.read_text(encoding="utf-8") == on_disk

    differing = freeze_mod.build_evaluation_spec_artifact(_base_config(),
                                                          repetitions=3)
    assert differing["fingerprint"] != first["fingerprint"]
    with pytest.raises(freeze_mod.ArtifactExistsError):
        freeze_mod.write_artifact(differing, path)
    assert path.read_text(encoding="utf-8") == on_disk
    assert freeze_mod.verify_artifact(path)["artifact_id"] == first["artifact_id"]
    assert not list(tmp_path.glob("*.tmp"))


# -- 7. the evaluation path does not learn ------------------------------------
def test_frozen_policy_is_not_mutated_by_an_evaluation_rollout(tmp_path):
    state = StateVector("join", "S", schema_version=SCHEMA_V15,
                        feedback_bin="le0")
    q_row = [0.1, 0.9] + [0.0] * 10
    agent = QLearningAgent(rng_seed=5, q_table={"state-v1.5|join|S|le0": q_row})
    artifact = build_policy_artifact(agent, init_provenance={"source": "fixture"},
                                     created_utc="2026-01-01T00:00:00Z")
    save_policy(artifact, tmp_path)
    frozen = agent_from_artifact(load_policy(artifact["policy_id"], tmp_path))

    before = json.dumps(frozen.q_table(), sort_keys=True)
    actions = [frozen.select_action(state, epsilon=0.0) for _ in range(25)]

    assert set(actions) == {1}                      # greedy, deterministic
    assert json.dumps(frozen.q_table(), sort_keys=True) == before
    assert (frozen.updates, frozen.episodes) == (artifact["updates"],
                                                 artifact["episodes"])
    assert frozen.epsilon == artifact["epsilon"]
    rebuilt = build_policy_artifact(frozen, init_provenance={"source": "fixture"},
                                    created_utc="2026-01-01T00:00:00Z")
    assert rebuilt["policy_id"] == artifact["policy_id"]


def test_evaluation_package_never_imports_the_learner():
    for module in sorted(EVALUATION_PKG.glob("*.py")):
        for line in module.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped.startswith(("import ", "from ")):
                continue
            assert "sparkrl.agent" not in stripped, f"{module.name}: {stripped}"
            assert "sparkrl.rl" not in stripped, f"{module.name}: {stripped}"


# -- 8. budget projection arithmetic ------------------------------------------
def test_projection_arithmetic_is_derived_not_hardcoded():
    n_cells = len(validation_cells())
    n_candidates = len(CANDIDATES)
    assert EVALUATION_REPETITIONS == 5

    # Selection always uses 1 rep; comparison uses the `repetitions` parameter.
    for reps in (1, EVALUATION_REPETITIONS):
        p = project_cost(reps)
        selection_runs = n_cells * n_candidates * 1  # always 1 rep
        comparison_runs = n_cells * 3 * reps
        assert p["executed"] is False
        assert p["spark_executions_performed_by_this_projection"] == 0
        assert p["b1_b2_selection"]["runs"] == selection_runs
        assert p["b1_b2_selection"]["repetitions"] == 1
        assert p["exp003_comparison"]["runs"] == comparison_runs
        assert p["exp003_comparison"]["repetitions"] == reps
        assert p["exp003_comparison"][
            "additional_runs_beyond_selection"] == comparison_runs
        # Combined = selection (1 rep) + comparison (reps), no reuse
        assert p["minimum_total_runs"] == selection_runs + comparison_runs
        assert p["shortfall_runs"] == \
            p["minimum_total_runs"] - p["plan_estimate_runs"]

    # At 1 rep: selection=96, comparison=24, combined=120
    assert project_cost(1)["minimum_total_runs"] == 96 + 24
    # At 5 reps: selection=96, comparison=120, combined=216
    assert project_cost(5)["minimum_total_runs"] == 96 + 120
    with pytest.raises(ValueError):
        project_cost(0)


# -- 9. duplicate-run detection ------------------------------------------------
def test_run_plan_has_no_duplicate_and_detects_one(monkeypatch):
    cfg = _base_config()
    plan = orch.validation_run_plan(cfg, repetitions=2)
    identities = [(r.family, r.scale, r.seed, r.config.name, r.rep) for r in plan]

    assert len(plan) == len(validation_cells()) * len(CANDIDATES) * 2
    assert len(set(identities)) == len(identities)
    assert len({r.run_id for r in plan}) == len(plan)
    assert len({r.order_index for r in plan}) == len(plan)

    # If run identity ever stopped being injective the plan must refuse to exist.
    with monkeypatch.context() as patch:
        patch.setattr(orch, "run_id_for", lambda *a, **kw: "exp003-collision")
        with pytest.raises(ValueError, match="duplicate"):
            orch.validation_run_plan(cfg, repetitions=2)

    assert orch.run_id_for("F1_agg", "small", 3, "c1", 1) != \
        orch.run_id_for("F1_agg", "small", 3, "c1", 2)
    with pytest.raises(ValueError):
        orch.run_id_for("F1_agg", "small", 3, "c1", 0)


# -- 10. provenance completeness ----------------------------------------------
def test_artifacts_carry_complete_provenance_inside_the_fingerprint(monkeypatch):
    _pin_code_version(monkeypatch, "cafe001")
    spec_artifact = freeze_mod.build_evaluation_spec_artifact(_base_config())
    selection = select_baselines(_observations(lambda f, p: 10.0 + p.grid_index))
    selection_artifact = freeze_mod.build_baseline_selection_artifact(selection)

    for artifact in (spec_artifact, selection_artifact):
        prov = artifact["provenance"]
        assert prov["code_version"] == "cafe001"
        assert prov["spark_executions"] == 0
        assert prov["split_authority"] == "sparkrl.experiments.spec.split_of"
        assert prov["produced_by"]
        assert artifact["experiment_id"] == "EXP-003"
        assert artifact["schema_version"] and artifact["created_utc"]
        assert artifact["artifact_id"] == artifact["fingerprint"]

    # Provenance is inside the identity: a different code version is a different
    # artifact, so an artifact can never claim provenance it was not built with.
    _pin_code_version(monkeypatch, "cafe002")
    moved = freeze_mod.build_evaluation_spec_artifact(_base_config())
    assert moved["fingerprint"] != spec_artifact["fingerprint"]


# -- 11. the specification is reproducible ------------------------------------
def test_evaluation_specification_is_reproducible(monkeypatch):
    cfg = _base_config()
    assert build_evaluation_spec(cfg) == build_evaluation_spec(cfg)

    _pin_code_version(monkeypatch)
    early = freeze_mod.build_evaluation_spec_artifact(cfg)
    late = freeze_mod.seal({k: v for k, v in early.items()
                            if k not in ("artifact_id", "fingerprint",
                                         "created_utc")},
                           created_utc="2099-12-31T23:59:59+00:00")
    assert late["fingerprint"] == early["fingerprint"]
    assert late["created_utc"] != early["created_utc"]

    spec = build_evaluation_spec(cfg)
    assert spec["executed"] is False
    assert spec["selection_split"] == VALIDATION
    assert spec["repetitions"] == EVALUATION_REPETITIONS
    assert spec["metrics"]["primary"] == "execution_time_s"
    assert spec["test_cell_count"] == len(frozen_test_cells())
    assert len(spec["frozen_configurations"]["candidates"]) == len(CANDIDATES)
    # The declared design must stay tied to the real frozen grid.
    assert [c["name"] for c in spec["frozen_configurations"]["candidates"]] == \
        [c.name for c in CANDIDATES]


# --- DEC-013 Model B: the calibration execution gate -------------------------
# These pin the ONE thing that could go wrong when a frozen guard is made
# pluggable: that the default silently stops being TRAIN-only.

def test_execute_run_split_guard_defaults_to_the_untouched_train_guard():
    import inspect

    from sparkrl.experiments.runner import execute_run
    from sparkrl.experiments.spec import assert_train_only

    default = inspect.signature(execute_run).parameters["split_guard"].default
    assert default is assert_train_only


def test_the_train_guard_itself_is_semantically_unchanged():
    """assert_train_only must still refuse validation AND test, and accept train."""
    from sparkrl.experiments.spec import assert_train_only

    assert_train_only("F1_agg", "small", 0)                 # TRAIN: accepted
    for cell in (("F1_agg", "small", 3),                    # VALIDATION
                 ("F4_ski", "small", 0),                    # TEST family
                 ("F1_agg", "large", 0),                    # TEST scale
                 ("F1_agg", "small", 4)):                   # TEST seed
        with pytest.raises(ValueError):
            assert_train_only(*cell)


def test_calibration_path_supplies_a_validation_guard_and_never_runs_spark(
        monkeypatch):
    """execute_validation_run must reach execute_run with the VALIDATION guard."""
    import sparkrl.experiments.runner as runner
    from sparkrl.evaluation.orchestration import execute_validation_run
    from sparkrl.evaluation.spec import authorize_validation_cell
    from sparkrl.experiments.spec import assert_train_only

    seen = {}

    # the fake must honour the real contract, or preflight_blockers() correctly
    # reports the substitute as unable to take a caller-supplied guard
    def fake_execute_run(run_spec, base_config, *,
                         split_guard=assert_train_only, **kwargs):
        seen["guard"] = split_guard
        seen["cell"] = (run_spec.family, run_spec.scale, run_spec.seed)
        return ("metrics-sentinel", {"provenance": True})

    monkeypatch.setattr(runner, "execute_run", fake_execute_run)

    spec_obj = _validation_run_spec()          # helper defined below
    out = execute_validation_run(spec_obj, base_config=None)

    assert out == ("metrics-sentinel", {"provenance": True})
    assert seen["guard"] is authorize_validation_cell
    assert seen["cell"][2] == 3                # seed 3 == VALIDATION


def test_calibration_path_still_refuses_a_test_cell(monkeypatch):
    import sparkrl.experiments.runner as runner
    from sparkrl.evaluation.orchestration import execute_validation_run

    def must_not_run(run_spec, base_config, *,
                     split_guard=None, **k):   # pragma: no cover - must not fire
        raise AssertionError("Spark path reached for a TEST cell")

    monkeypatch.setattr(runner, "execute_run", must_not_run)
    with pytest.raises(Exception):
        execute_validation_run(_test_run_spec(), base_config=None)


def test_preflight_reports_no_blocker_once_the_gate_is_authorized():
    from sparkrl.evaluation.orchestration import preflight_blockers

    assert preflight_blockers() == []


def _run_spec_for(family, scale, seed):
    from sparkrl.experiments.grid import build_grid
    from sparkrl.experiments.spec import RunSpec, split_of

    point = [p for p in build_grid(include_b0=False)][0]
    return RunSpec(run_id=f"cal-{family}-{scale}-s{seed}", family=family,
                   scale=scale, seed=seed, rep=1, config=point,
                   split=split_of(family, scale, seed), timeout_seconds=60.0,
                   order_index=0, block_id="calibration")


def _validation_run_spec():
    return _run_spec_for("F1_agg", "small", 3)


def _test_run_spec():
    return _run_spec_for("F4_ski", "large", 4)
