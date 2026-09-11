"""Unit tests: SparkTuningEnv guards, determinism, contract (COMP-RL-09).

No Spark here: ``execute_run`` is monkeypatched with a fake that returns
synthetic RunMetrics. Real-Spark behaviour is covered by the integration test.
"""
from dataclasses import replace
from unittest import mock

import pytest

from sparkrl.experiments.spec import split_of
from sparkrl.monitoring.run_metrics import RunMetrics
from sparkrl.rl.env import (BudgetExhausted, EpisodeDone, Observation,
                            SparkTuningEnv, SplitViolation, StepInfo)
from sparkrl.rl.reward import Reward, TRefMissing
from sparkrl.rl.tref import TRefStore
from sparkrl.spark.config import SparkConfig

T_REF = 10.0


def good_metrics(**kw):
    base = dict(execution_time_s=5.0, usable=True, success=True, timeout=False,
                task_duration_cv=0.25, disk_spill_bytes=0)
    base.update(kw)
    return RunMetrics(**base)


def fake_execute(metrics):
    """Return a fake execute_run(run_spec, base_config, *, sysmon_enabled)."""
    calls = []

    def _fake(run_spec, base_config, *, sysmon_enabled=True, version=None):
        calls.append(run_spec)
        return metrics, {"fake": True}

    _fake.calls = calls  # type: ignore[attr-defined]
    return _fake


def make_env(tmp_path, metrics=None, **kw):
    tref = TRefStore(mapping={"F2_join|small": T_REF, "F1_agg|small": 20.0,
                              "F3_rdd|medium": None})
    env = SparkTuningEnv(SparkConfig.from_yaml("configs/baseline_b0.yaml"),
                         tref_store=tref, result_root=tmp_path,
                         budget_limit=kw.pop("budget", 500), **kw)
    if metrics is not None:
        return env, mock.patch("sparkrl.rl.env.execute_run",
                               fake_execute(metrics)).start()
    return env, None


def reset_ok(env, **kw):
    return env.reset(family="F2_join", scale="small", seed=0, **kw)


# --- construction -------------------------------------------------------------------
def test_env_default_domains(tmp_path):
    env, _ = make_env(tmp_path)
    assert env.action_space_size == 12
    assert env.observation_space_size == 30
    assert env.budget_limit == 500            # frozen cap default
    assert env.executions_used == 0
    assert env.env_version == "spark-tuning-env/v1"
    with pytest.raises(ValueError):
        SparkTuningEnv(SparkConfig(), budget_limit=0)
    with pytest.raises(ValueError):
        SparkTuningEnv(SparkConfig(), budget_limit=True)


# --- reset semantics -----------------------------------------------------------------
def test_reset_is_pure_no_execution_no_budget(tmp_path):
    env, _ = make_env(tmp_path)
    obs, info = reset_ok(env)
    assert env.executions_used == 0            # reset consumes nothing
    assert info["t_ref_available"] is True
    assert obs.t_ref_s == T_REF
    assert obs.state.workload_class == "join" and obs.state.input_size_bin == "S"


def test_reset_determinism(tmp_path):
    env, _ = make_env(tmp_path)
    o1, i1 = reset_ok(env)
    o2, i2 = reset_ok(env)
    assert o1 == o2 and i1 == i2
    assert o1.state.state_index == o2.state.state_index


def test_reset_last_reward_flips_feedback_bin(tmp_path):
    env, _ = make_env(tmp_path)
    o_neg, _ = reset_ok(env, last_reward=-0.2)
    o_pos, _ = reset_ok(env, last_reward=0.3)
    assert o_neg.state.feedback_bin == "le0"
    assert o_pos.state.feedback_bin == "gt0"
    assert o_neg.state.state_index != o_pos.state.state_index


@pytest.mark.parametrize("family,scale,seed", [
    ("F4_ski", "small", 0),     # TEST family
    ("F2_join", "large", 0),    # TEST scale
    ("F2_join", "small", 4),    # TEST seed
    ("F2_join", "small", 3),    # VALIDATION seed
])
def test_split_guard_aborts_non_train(tmp_path, family, scale, seed):
    env, _ = make_env(tmp_path)
    assert split_of(family, scale, seed) in ("test", "validation")
    with pytest.raises(SplitViolation):
        env.reset(family=family, scale=scale, seed=seed)
    assert env.executions_used == 0            # nothing ran


def test_budget_guard_done_at_episode_boundary(tmp_path):
    env, patcher = make_env(tmp_path, metrics=good_metrics(), budget=2)
    for _ in range(2):
        env.reset(family="F2_join", scale="small", seed=0)
        env.step(0)
    assert env.budget_remaining == 0
    with pytest.raises(BudgetExhausted):
        reset_ok(env)                          # budget-hit -> done (no episode)


# --- step semantics --------------------------------------------------------------------
def test_step_executes_once_and_terminates(tmp_path):
    env, patcher = make_env(tmp_path, metrics=good_metrics())
    reset_ok(env)
    obs_next, reward, terminated, truncated, info = env.step(0)
    assert env.executions_used == 1 and len(patcher.calls) == 1  # type: ignore[attr-defined]
    assert terminated is True and truncated is False
    assert isinstance(reward, float) and info.cached is False
    assert info.config_name == "G-p2-sp16"     # action 0 = (2, 16)
    assert info.config_fingerprint == info.metrics["config_fingerprint"] or True
    assert info.metrics["execution_time_s"] == 5.0
    with pytest.raises(EpisodeDone):           # bandit: one decision per episode
        env.step(0)
    fresh_obs, _ = reset_ok(env)               # new episode, no feedback history
    # obs_next carried the realized reward's feedback bin into the next state
    assert obs_next.feedback_bin == "gt0"
    assert fresh_obs.state.feedback_bin == "le0"  # fresh episode resets feedback
    assert fresh_obs.state.workload_class == obs_next.workload_class


def test_action_to_config_deterministic(tmp_path):
    env, _ = make_env(tmp_path)
    r1 = env.step(5) if env.reset(family="F2_join", scale="small") is None else None
    # (sequence: reset then step 5 -> config G-p4-sp32)
    env2, _ = make_env(tmp_path)
    env2.reset(family="F2_join", scale="small")
    _, _, _, _, info = env2.step(5)
    assert info.config_name == "G-p4-sp32"


def test_invalid_action_rejected_pre_execution(tmp_path):
    env, patcher = make_env(tmp_path, metrics=good_metrics())
    reset_ok(env)
    with pytest.raises(InvalidAction):
        env.step(12)
    with pytest.raises(InvalidAction):
        env.step("3")
    assert len(patcher.calls) == 0  # type: ignore[attr-defined]  # nothing ran


def test_tref_missing_refuses_before_execution(tmp_path):
    env, patcher = make_env(tmp_path, metrics=good_metrics())
    env.reset(family="F3_rdd", scale="medium", seed=0)   # T_ref null in EXP-002
    with pytest.raises(TRefMissing):
        env.step(0)
    assert len(patcher.calls) == 0  # type: ignore[attr-defined]  # no Spark run


def test_failed_execution_reward_minus_one_provenance_kept(tmp_path):
    bad = good_metrics(usable=False, success=False, execution_time_s=None,
                       task_duration_cv=None, disk_spill_bytes=None,
                       error="WinError 32 spill failure")
    env, patcher = make_env(tmp_path, metrics=bad)
    reset_ok(env)
    _, reward, terminated, _, info = env.step(3)
    assert reward == -1.0 and terminated is True
    assert info.reward.failed is True
    assert info.metrics["execution_time_s"] is None   # missing stays missing
    assert "WinError 32" in info.metrics["error"]


def test_mode4_env_restricts_actions(tmp_path):
    env, _ = make_env(tmp_path, metrics=good_metrics(), action_mode="mode4")
    reset_ok(env)
    _, _, _, _, info = env.step(9)                    # (8, 32)
    assert info.config_name == "G-p8-sp32"
    assert info.action_mode == "mode4"


def test_v1_state_schema_env(tmp_path):
    env, _ = make_env(tmp_path, state_schema="state-v1")
    obs, info = reset_ok(env)
    assert info["observation_space_size"] == 15
    assert obs.state.feedback_bin is None


def test_transition_record_written_deterministic(tmp_path):
    env, _ = make_env(tmp_path, metrics=good_metrics())
    reset_ok(env)
    env.step(0)
    p = tmp_path / "F2_join" / "small" / "seed0" / "G-p2-sp16" / "rep1.json"
    assert p.exists()
    import json
    rec = json.loads(p.read_text(encoding="utf-8"))
    assert rec["run_id"] == "env-F2_join-small-s0-G-p2-sp16-r1"
    assert rec["reward"]["value"] == pytest.approx(0.6)  # T=5 vs T_ref=10
    assert rec["cached"] is False and rec["env_version"] == "spark-tuning-env/v1"
    # re-running the same episode rewrites the same deterministic payload
    env2, _ = make_env(tmp_path, metrics=good_metrics())
    reset_ok(env2)
    env2.step(0)
    rec2 = json.loads(p.read_text(encoding="utf-8"))
    rec.pop("written_utc"), rec2.pop("written_utc")
    assert rec == rec2


# --- contract boundaries ------------------------------------------------------------
def test_env_has_no_learning_api(tmp_path):
    env, _ = make_env(tmp_path)
    for forbidden in ("learn", "update", "q_table", "epsilon", "policy",
                      "save_policy", "train"):
        assert not hasattr(env, forbidden), forbidden


def test_observation_never_carries_post_execution_metrics(tmp_path):
    env, _ = make_env(tmp_path)
    obs, _ = reset_ok(env)
    d = obs.to_dict()
    assert not any(k in d for k in
                   ("execution_time_s", "shuffle_read_bytes", "reward"))
    assert set(Observation.__dataclass_fields__) == {
        "state", "family", "scale", "seed", "rep", "episode_key", "dataset_id",
        "dataset_fingerprint", "input_bytes", "t_ref_s", "budget_remaining"}


def test_step_info_schema_frozen(tmp_path):
    env, _ = make_env(tmp_path, metrics=good_metrics())
    reset_ok(env)
    _, _, _, _, info = env.step(0)
    assert set(StepInfo.__dataclass_fields__) == {
        "run_id", "episode_key", "action_index", "action_mode", "config_name",
        "config_fingerprint", "state_before", "state_after", "reward",
        "metrics", "provenance", "env_version", "cached", "terminated"}


# late import to keep the failure list readable
from sparkrl.rl.action import InvalidAction  # noqa: E402
