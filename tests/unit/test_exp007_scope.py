"""Unit tests: EXP-007 frozen scope, budget, split and seed guards (DEC-023
as amended by DEC-025: episodes per seed 42 -> 35).

Pure non-Spark validation: budget arithmetic (Gate F), TRAIN-only split
(Gate D), seed isolation (Gate E), and the variant plan guards of
``build_plan``. Nothing here launches Spark or ``run_training.py``.
"""
import json

import pytest

from sparkrl.training import ablation as ab
from sparkrl.training.ablation import (ABLATION_EPISODES_PER_SEED,
                                       ABLATION_EPOCHS, ABLATION_SEEDS,
                                       ABLATION_TRAIN_CELLS, EXP007_ID,
                                       combined_planned, exp007_budget_summary,
                                       planned_executions, sc6_headroom,
                                       sc6_remaining)
from sparkrl.training.loop import (BudgetPlanError, TrainingConfig,
                                   TrainingPlanError, build_plan)

pytestmark = [pytest.mark.unit]

# The measured EXP-002 calibration (results/experiments/exp-002/analysis/
# gate.json): F3_rdd|medium is null; every other TRAIN cell is calibrated.
GATE = {
    "F1_agg|medium": 36.669743,
    "F1_agg|small": 22.347372,
    "F2_join|medium": 16.126881,
    "F2_join|small": 2.214523,
    "F3_rdd|medium": None,
    "F3_rdd|small": 25.109380,
    "F5_mixed|medium": 32.759411,
    "F5_mixed|small": 3.903756,
}

FROZEN_CELLS = ("F1_agg|medium", "F1_agg|small", "F2_join|medium",
                "F2_join|small", "F3_rdd|small", "F5_mixed|medium",
                "F5_mixed|small")


def cfg() -> TrainingConfig:
    return TrainingConfig.from_yaml()


def store():
    from sparkrl.rl.tref import TRefStore
    return TRefStore(mapping=GATE)


def variant_plan(tmp_path, *, variant="A1", seed=0, episodes=35, **kw):
    return build_plan(agent_rng_seed=seed, episodes=episodes,
                      variant=variant, config=cfg(), tref_store=store(),
                      run_root=tmp_path, now_utc="20260917T000000Z", **kw)


# --- Gate F: budget arithmetic (DEC-023 s.8 as amended by DEC-025 s.1/3/4) ----
def test_budget_summary_matches_dec025_amended_scope():
    assert ABLATION_EPISODES_PER_SEED == 35
    assert ABLATION_EPOCHS == 5 and ABLATION_TRAIN_CELLS == 7
    assert planned_executions("A1") == 70
    assert planned_executions("A2") == 70
    assert combined_planned() == 140
    assert sc6_remaining() == 164
    assert sc6_headroom() == 24
    summary = exp007_budget_summary()
    assert summary["experiment_id"] == EXP007_ID
    assert summary["planned_max_per_seed"] == 35
    assert summary["a1_planned_max"] == 70
    assert summary["a2_planned_max"] == 70
    assert summary["combined_planned_max"] == 140
    assert summary["sc6_remaining"] == 164
    assert summary["headroom"] == 24
    assert summary["seeds_per_variant"] == [0, 1]
    assert summary["sc6_cap"] == 500        # the frozen cap is NOT raised
    assert summary["sc6_ledger_cited"] == "336/500"   # historical ledger, cited


def test_planned_executions_rejects_unknown_variants():
    with pytest.raises(ValueError):
        planned_executions("A3")
    with pytest.raises(ValueError):
        planned_executions("full")


def test_variant_run_budget_defaults_to_the_plan_not_the_cap(tmp_path):
    plan = variant_plan(tmp_path, variant="A1", episodes=35)
    assert len(plan.episodes) == 35
    assert plan.budget_limit == 35          # a run can never exceed its plan
    assert plan.budget_limit < 500          # the 500 cap is untouched


def test_variant_plan_cannot_plan_more_than_35_episodes(tmp_path):
    with pytest.raises(BudgetPlanError):
        variant_plan(tmp_path, variant="A2", episodes=36)


def test_variant_plan_accepts_exactly_35_per_seed(tmp_path):
    for variant, seed in (("A1", 0), ("A1", 1), ("A2", 0), ("A2", 1)):
        plan = variant_plan(tmp_path, variant=variant, seed=seed, episodes=35)
        assert len(plan.episodes) == ABLATION_EPISODES_PER_SEED


def test_variant_plan_epochs_are_five_complete_round_robin_passes(tmp_path):
    # DEC-025 sections 3-4: 35 = 5 x 7 must be FIVE COMPLETE epochs - every
    # cell visited exactly once per epoch and no partial trailing epoch.
    plan = variant_plan(tmp_path, variant="A1", episodes=35)
    epochs = [ep.epoch for ep in plan.episodes]
    assert epochs == [e for e in range(1, ABLATION_EPOCHS + 1)
                      for _ in range(ABLATION_TRAIN_CELLS)]
    assert len(plan.episodes) == ABLATION_EPOCHS * ABLATION_TRAIN_CELLS
    assert plan.episodes_per_epoch == ABLATION_TRAIN_CELLS


def test_budget_arithmetic_is_pure_no_execution_side_effect():
    assert combined_planned() == combined_planned() == 140
    assert sc6_remaining() == 164 and sc6_headroom() == 24
    assert 336 + combined_planned() <= 500   # 336 spent + 140 planned = 476


# --- Gate D: TRAIN-only (existing split guard, unchanged) ---------------------------
def test_variant_plan_rejects_test_cells(tmp_path):
    for cell in ("F4_ski|small",        # TEST family
                 "F1_agg|large",        # TEST scale
                 "F4_ski|large"):       # TEST family x TEST scale
        with pytest.raises(TrainingPlanError):
            variant_plan(tmp_path, variant="A1", cell_keys=[cell])


def test_variant_plan_accepts_train_cells(tmp_path):
    for cell in ("F1_agg|small", "F2_join|medium", "F3_rdd|small",
                 "F5_mixed|small"):
        plan = variant_plan(tmp_path, variant="A2", cell_keys=[cell],
                            episodes=7)
        assert [c.key() for c in plan.cells] == [cell]


def test_variant_plan_rejects_validation_seed(tmp_path):
    # dataset seed 3 is the VALIDATION seed of PLAN section 18; build_plan
    # refuses it (T_REF CALIBRATION message) before any cell is resolved.
    with pytest.raises(TrainingPlanError) as exc:
        build_plan(agent_rng_seed=0, episodes=3, dataset_seed=3,
                   variant="A1", config=cfg(), tref_store=store(),
                   run_root=tmp_path)
    msg = str(exc.value)
    assert "dataset_seed=3" in msg or "seed 3" in msg


def test_frozen_train_cells_of_dec023_are_exactly_the_derived_set(tmp_path):
    # The 7 DEC-023 cells are the derived TRAIN x T_ref cells (F3_rdd|medium
    # excluded because t_ref is null) - derived, never hard-coded.
    plan = variant_plan(tmp_path, variant="A1", episodes=7)
    assert tuple(c.key() for c in plan.cells) == FROZEN_CELLS
    excluded = {e["cell"]: e["reason"] for e in plan.excluded}
    assert excluded["F3_rdd|medium"] == "t_ref_null"


def test_full_default_plan_carries_all_seven_cells(tmp_path):
    # 35 episodes = 5 epochs x 7 cells requires the default (uncut) cell set.
    plan = variant_plan(tmp_path, variant="A2", episodes=35)
    assert len(plan.cells) == ABLATION_TRAIN_CELLS


# --- Gate E: seeds (DEC-023 section 7) ----------------------------------------------
def test_variant_accepts_only_frozen_seeds(tmp_path):
    for seed in (0, 1):
        plan = variant_plan(tmp_path, variant="A1", seed=seed, episodes=7)
        assert plan.agent_rng_seed == seed


def test_variant_rejects_main_study_seed_2(tmp_path):
    with pytest.raises(TrainingPlanError) as exc:
        variant_plan(tmp_path, variant="A1", seed=2, episodes=7)
    assert "seed 2" in str(exc.value)
    with pytest.raises(TrainingPlanError):
        variant_plan(tmp_path, variant="A2", seed=2, episodes=7)


def test_variant_rejects_test_seed_4(tmp_path):
    with pytest.raises(TrainingPlanError):
        variant_plan(tmp_path, variant="A1", seed=4, episodes=7)


def test_dataset_seed_is_always_zero(tmp_path):
    for variant in ("A1", "A2"):
        plan = variant_plan(tmp_path, variant=variant, episodes=7)
        assert plan.dataset_seed == 0
        assert {c.dataset_seed for c in plan.cells} == {0}


def test_agent_seed_and_dataset_seed_remain_distinct_concepts(tmp_path):
    plan = variant_plan(tmp_path, variant="A1", seed=1, episodes=7)
    assert plan.agent_rng_seed == 1          # exploration replicate
    assert plan.dataset_seed == 0            # workload instance seed
    run = json.loads(json.dumps(plan.to_dict()))
    assert run["agent_rng_seed"] == 1 and run["dataset_seed"] == 0
    assert "seed_semantics" in run
