"""Integration: reset -> action -> REAL Spark execution -> metrics -> transition.

One live run (F2_join / small / seed 0, action 0 = local[2]+sp16, AQE OFF)
through the frozen experiment-runner pipeline. T_ref comes from the EXP-002
gate artifact (read-only). No experiment study, no grid, no EXP-003.
"""
import json

import pytest

from sparkrl.rl.env import ENV_VERSION, SparkTuningEnv
from sparkrl.rl.tref import TRefStore
from sparkrl.spark.config import SparkConfig

pytestmark = pytest.mark.integration


def test_env_end_to_end_real_spark(tmp_path):
    base = SparkConfig.from_yaml("configs/baseline_b0.yaml")
    env = SparkTuningEnv(base, tref_store=TRefStore(), result_root=tmp_path,
                         sysmon_enabled=True)
    assert env.budget_limit == 500

    obs, info = env.reset(family="F2_join", scale="small", seed=0)
    assert info["t_ref_available"] is True
    assert obs.t_ref_s == pytest.approx(2.214523)   # EXP-002 B0 median
    assert obs.state.workload_class == "join"
    assert obs.state.input_size_bin == "S"
    assert info["budget_remaining"] == 500
    assert env.executions_used == 0                 # reset consumed nothing

    state_next, reward, terminated, truncated, step = env.step(0)
    assert terminated is True and truncated is False
    assert env.executions_used == 1

    # authoritative runner timing propagated, never replaced
    t = step.metrics["execution_time_s"]
    assert isinstance(t, float) and t > 0.0
    assert step.metrics["execution_time_source"] == "runner"
    assert step.metrics["event_log_status"] == "COMPLETE"
    assert step.metrics["aqe_enabled"] is False
    assert step.provenance["spark_config_fingerprint"]
    assert step.run_id == "env-F2_join-small-s0-G-p2-sp16-r1"
    assert step.config_name == "G-p2-sp16"
    assert step.cached is False

    # reward from the frozen formula, finite and bounded below by -1
    assert -1.0 <= reward <= 2.0
    assert step.reward.formula_id == "R3"
    assert step.reward.t_ref_s == pytest.approx(2.214523)

    # deterministic transition record with full provenance
    rec_path = (tmp_path / "F2_join" / "small" / "seed0" / "G-p2-sp16"
                / "rep1.json")
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    assert rec["env_version"] == ENV_VERSION
    assert rec["run_id"] == step.run_id
    assert rec["metrics"]["execution_time_s"] == t
    assert rec["state_before"]["state_index"] == obs.state.state_index
