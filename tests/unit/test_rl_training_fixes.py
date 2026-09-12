"""Unit-test probes for the operator-applied CONFIRMED fixes.
Drive the loop against the same
FakeEnv fakes: fakes only, NO Spark, NO learning claims.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from sparkrl.rl.env import EpisodeDone, TRefMissing
from sparkrl.training.loop import (BudgetPlanError, TrainingPlanError,
                                   build_plan, trainable_cells)

from tests.unit.test_rl_training import cfg, drive, read_lines, store

pytestmark = [pytest.mark.unit]


# --- fix 1: split seeds name the split, TRAIN seeds name calibration --------
@pytest.mark.parametrize("seed", [3, 4])
def test_split_dataset_seeds_refuse_with_a_split_reason(seed):
    with pytest.raises(TrainingPlanError) as exc:
        build_plan(agent_rng_seed=0, episodes=1, dataset_seed=seed,
                   config=cfg(), tref_store=store(),
                   run_root=Path(tempfile.gettempdir()))
    assert "SPLIT" in str(exc.value)
    assert "T_REF CALIBRATION" not in str(exc.value)


@pytest.mark.parametrize("seed", [3, 4])
def test_split_dataset_seeds_have_no_trainable_cell_because_of_the_split(
        seed):
    with pytest.raises(TrainingPlanError) as exc:
        trainable_cells(store(), dataset_seed=seed)
    assert "SPLIT" in str(exc.value)


def test_train_but_uncalibrated_seed_keeps_the_calibration_reason():
    with pytest.raises(TrainingPlanError) as exc:
        build_plan(agent_rng_seed=0, episodes=1, dataset_seed=2,
                   config=cfg(), tref_store=store(),
                   run_root=Path(tempfile.gettempdir()))
    msg = str(exc.value)
    assert "T_REF CALIBRATION" in msg and "SPLIT" not in msg


# --- fix 6: the failed flag, not the -1.0 sentinel ---------------------------
def test_usable_clipped_minus_one_is_not_a_failed_predecessor(tmp_path):
    # every episode is usable with reward exactly -1.0 (the clip case):
    # the second line onward must still say the predecessor did NOT fail.
    _, _, _, result = drive(tmp_path, episodes=3, rewards=[-1.0])
    lines = read_lines(result)
    assert len(lines) == 3
    assert lines[0]["last_reward_in"] is None
    assert lines[0]["feedback_from_failed_episode"] is False
    assert all(ln["feedback_from_failed_episode"] is False for ln in lines[1:])
    assert [ln["failed"] for ln in lines] == [False, False, False]


# --- fix 7: planned step aborts carry no uncertain-budget stamp --------------
@pytest.mark.parametrize("exc,reason", [
    (TRefMissing("boom"), "tref_missing"),
    (EpisodeDone("boom"), "episode_done"),
])
def test_planned_step_aborts_have_exact_budget_accounting(tmp_path, exc,
                                                          reason):
    with pytest.raises(type(exc)):
        drive(tmp_path, episodes=5, rewards=[0.5], step_raises={2: exc})
    run_dir = next(tmp_path.glob("train-*"))
    man = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert man["status"] == "failed" and man["stop_reason"] == reason
    assert "interrupted_mid_step" not in man
    assert "uncertain" not in man.get("budget_accounting", "")


# A mid-step KeyboardInterrupt does NOT propagate: the loop catches it, writes
# the uncertain-budget manifest and returns exit_code 130. That contract is
# covered by test_interrupt_during_step_writes_no_checkpoint in
# tests/unit/test_rl_training.py, which asserts the same stamp this fix
# preserves.


# --- fix 8: the smoke branch binds the frozen cap -----------------------------
def test_smoke_episodes_above_the_cap_are_refused(tmp_path):
    with pytest.raises(BudgetPlanError):
        build_plan(agent_rng_seed=0, episodes=600, run_kind="smoke",
                   cell_keys=["F1_agg|small"], config=cfg(),
                   tref_store=store(), run_root=tmp_path)


def test_smoke_budget_is_honored_but_cannot_exceed_the_cap(tmp_path):
    with pytest.raises(BudgetPlanError):
        build_plan(agent_rng_seed=0, episodes=3, run_kind="smoke",
                   cell_keys=["F1_agg|small"], config=cfg(), budget_limit=501,
                   tref_store=store(), run_root=tmp_path)
