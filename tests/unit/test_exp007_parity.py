"""Unit tests: EXP-007 control parity and training-control semantics (DEC-023
section 5 + task gates C/G/H).

Proves A1/A2 inherit the SAME frozen training machinery as the main study:
action space, reward, T_ref source, gamma, epsilon schedule, checkpoint
cadence, early-stop semantics, TRAIN cell set, dataset seed. Drives the REAL
training loop against a FakeEnv (scripted rewards, no Spark). NO Spark.
"""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from sparkrl.agent.policy_store import load_policy
from sparkrl.agent.q0 import (VARIANT_A1, VARIANT_A2, build_neutral_q0,
                              build_q0_from_exp002)
from sparkrl.agent.q_learning import AgentConfig, QLearningAgent
from sparkrl.rl.env import SparkTuningEnv
from sparkrl.rl.state import SCHEMA_V1, SCHEMA_V15, SCHEMA_V2, StateEncoder
from sparkrl.rl.tref import TRefStore
from sparkrl.spark.config import SparkConfig
from sparkrl.training.loop import (CALIBRATED_DATASET_SEED,
                                   CHECKPOINT_EVERY_EPISODES,
                                   EARLY_STOP_STABLE_EPOCHS, EPOCH_DEFINITION,
                                   KIND_TRAINING, STATUS_COMPLETED,
                                   TrainingConfig, build_env_and_agent,
                                   build_plan, greedy_snapshot, run_training)

pytestmark = [pytest.mark.unit]

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

SMALL_BYTES = 100 * 1024 * 1024      # bin S, like every measured TRAIN cell


def store() -> TRefStore:
    return TRefStore(mapping=GATE)


def cfg() -> TrainingConfig:
    return TrainingConfig.from_yaml()


def variant_plan(tmp_path, *, variant="A1", seed=0, episodes=7, **kw):
    return build_plan(agent_rng_seed=seed, episodes=episodes,
                      variant=variant, config=cfg(), tref_store=store(),
                      run_root=tmp_path, now_utc="20260917T000000Z", **kw)


# --- FakeEnv: the same duck-typed stand-in the existing training tests use -------
@dataclass(frozen=True)
class FakeStep:
    run_id: str
    episode_key: str
    action_index: int
    action_mode: str
    config_name: str
    config_fingerprint: str
    metrics: dict[str, Any]
    env_version: str = "fake-env/v1"


class FakeEnv:
    env_version = "fake-env/v1"

    def __init__(self, reward: float, *, budget_limit: int,
                 encoder: StateEncoder) -> None:
        self._reward = reward
        self._budget_limit = int(budget_limit)
        self._used = 0
        self._episode = None
        self.encoder = encoder

    @property
    def budget_limit(self) -> int:
        return self._budget_limit

    @property
    def executions_used(self) -> int:
        return self._used

    @property
    def budget_remaining(self) -> int:
        return self._budget_limit - self._used

    def reset(self, *, family, scale, seed=0, rep=1, last_reward=None):
        from sparkrl.rl.state import FeedbackState
        state = self.encoder.encode(family, SMALL_BYTES,
                                    last_reward=last_reward)
        self._episode = {"family": family, "scale": scale, "seed": seed,
                         "rep": rep, "last_reward": last_reward}
        if isinstance(state, FeedbackState):
            key = f"fake-{state.feedback_bin}"
        else:
            key = f"fake-{state.workload_class}-{state.input_size_bin}"
        return (type("Obs", (), {"state": state})(),
                {"episode_key": f"{key}-seed{seed}-rep{rep}"})

    def step(self, action: int):
        ep = self._episode
        assert ep is not None, "step() before reset()"
        self._used += 1
        from sparkrl.rl.state import FeedbackState
        base = self.encoder.encode(ep["family"], SMALL_BYTES,
                                   last_reward=None)
        after = self.encoder.encode(ep["family"], SMALL_BYTES,
                                    last_reward=self._reward)
        prefix = (after.feedback_bin if isinstance(base, FeedbackState)
                  else f"{base.workload_class}-{base.input_size_bin}")
        info = FakeStep(
            run_id=f"env-{prefix}-s{ep['seed']}-cfg{action:02d}-r{ep['rep']}",
            episode_key=f"fake|{prefix}|seed{ep['seed']}|rep{ep['rep']}",
            action_index=int(action), action_mode="mode12",
            config_name=f"cfg{action:02d}", config_fingerprint=f"fp{action:02d}",
            metrics={"usable": True, "timeout": False})
        self._episode = None
        return after, self._reward, True, False, info


def variant_run(tmp_path, *, variant, episodes=7, reward=0.4, seed=0):
    plan = build_plan(agent_rng_seed=seed, episodes=episodes, variant=variant,
                      run_kind=KIND_TRAINING, config=cfg(), tref_store=store(),
                      run_root=tmp_path, now_utc="20260917T000000Z")
    encoder = StateEncoder(schema_version=plan.state_schema)
    env = FakeEnv(reward, budget_limit=plan.budget_limit, encoder=encoder)
    agent = QLearningAgent(AgentConfig.from_yaml(), rng_seed=seed)
    result = run_training(plan, env=env, agent=agent,
                          q0_provenance={"source": "fake-q0", "variant": variant},
                          config=cfg())
    lines = [json.loads(ln) for ln in
             Path(result.episode_log_path).read_text(encoding="utf-8").splitlines()
             if ln.strip()]
    manifest = json.loads(Path(result.manifest_path).read_text(encoding="utf-8"))
    return plan, env, agent, result, lines, manifest


# --- Gate C: control parity across A1 / A2 (and the main study) ---------------------
def test_variant_plans_share_frozen_controls(tmp_path):
    plans = {v: variant_plan(tmp_path, variant=v) for v in (VARIANT_A1, VARIANT_A2)}
    keys = set()
    for v, p in plans.items():
        assert p.variant == v
        assert p.run_kind == KIND_TRAINING
        assert p.dataset_seed == CALIBRATED_DATASET_SEED == 0
        assert p.agent_rng_seed == 0
        keys |= {c.key() for c in p.cells}
        assert [e.index for e in p.episodes] == list(range(1, 8))
    # same 7 TRAIN cells for both arms
    assert keys == {c for c in GATE if GATE[c] is not None}
    assert len(keys) == 7


def test_frozen_agent_config_is_identical_for_all_arms():
    base = AgentConfig.from_yaml()
    assert base.gamma == 0.0
    assert base.epsilon_start == 1.0
    assert base.epsilon_min == 0.05
    assert base.epsilon_decay == 0.95
    assert base.q0_default == 0.5
    assert base.alpha == 0.2
    assert base.action_mode == "mode12"


def test_variant_training_control_constants_unchanged():
    assert CHECKPOINT_EVERY_EPISODES == 25
    assert EARLY_STOP_STABLE_EPOCHS == 2
    assert EPOCH_DEFINITION == "one_full_pass_over_the_planned_cell_cycle"
    assert cfg().checkpoint_every_episodes == 25
    assert cfg().early_stop_stable_epochs == 2
    assert cfg().dataset_seed == 0


def test_epsilon_schedule_identical_for_both_variants(tmp_path):
    eps = {}
    for v in (VARIANT_A1, VARIANT_A2):
        _, _, agent, result, lines, _ = variant_run(tmp_path / v, variant=v)
        eps[v] = [ln["epsilon_used"] for ln in lines]
        assert abs(agent.epsilon - max(0.05, 1.0 * 0.95 ** len(lines))) < 1e-12
    assert eps[VARIANT_A1] == eps[VARIANT_A2]


def test_reward_and_tref_source_identical_for_both_variants(tmp_path):
    for v in (VARIANT_A1, VARIANT_A2):
        plan = variant_plan(tmp_path / f"p-{v}", variant=v)
        assert plan.t_ref_source == store().source
        for c in plan.cells:
            assert c.t_ref_s == GATE[c.key()]


def test_checkpoint_cadence_identical_for_both_variants(tmp_path):
    # 36 episodes would exceed the amended 35-per-seed plan, so the cadence is
    # asserted on a 35-episode plan: checkpoints at 25, then the final at 35
    # (the frozen runner pattern "25/50/75/final" truncated to one arm's plan).
    for v in (VARIANT_A1, VARIANT_A2):
        _, _, _, result, _, manifest = variant_run(
            tmp_path / f"c-{v}", variant=v, episodes=35, reward=-0.5)
        cadence = [c["episode_index"] for c in manifest["checkpoints"]]
        assert cadence[0] == CHECKPOINT_EVERY_EPISODES == 25
        assert result.final_policy_id == manifest["checkpoints"][-1]["policy_id"]
        assert all(1 <= c <= 35 for c in cadence)


def test_early_stop_semantics_identical_for_both_variants(tmp_path):
    # reward == q0_default makes every update a zero-delta no-op, so the
    # greedy snapshot changes only when a new state key appears; the frozen
    # rule (identical snapshot at 3 consecutive epoch boundaries) must
    # early-stop BOTH arms with the same streak pattern.
    for v in (VARIANT_A1, VARIANT_A2):
        _, _, _, result, _, manifest = variant_run(
            tmp_path / f"e-{v}", variant=v, episodes=35, reward=0.5)
        assert result.status == STATUS_COMPLETED
        assert result.stop_reason == "early_stop_policy_stable"
        assert result.early_stopped is True
        assert manifest["early_stop"]["stable_epochs_required"] == 2
        assert manifest["early_stop"]["rule"] == (
            "greedy snapshot identical at 3 consecutive epoch boundaries")
        streaks = [e["stability_streak"] for e in manifest["epochs"]]
        assert streaks[-1] >= 2
        assert result.episodes_completed < 35      # stopped before the plan


def test_round_robin_ordering_identical_for_both_variants(tmp_path):
    order = {}
    for v in (VARIANT_A1, VARIANT_A2):
        _, _, _, _, lines, _ = variant_run(
            tmp_path / f"r-{v}", variant=v, episodes=14)
        order[v] = [ln["episode_key"] for ln in lines[:7]]
        assert {ln["epoch_index"] for ln in lines} == {1, 2}
    assert order[VARIANT_A1] == order[VARIANT_A2]


def test_action_space_is_mode12_for_both_variants(tmp_path):
    for v in (VARIANT_A1, VARIANT_A2):
        _, _, agent, _, lines, _ = variant_run(tmp_path / f"a-{v}", variant=v)
        assert agent.allowed_actions() == tuple(range(12))
        assert all(0 <= ln["action_index"] < 12 for ln in lines)


def test_variant_manifests_record_variant_and_state_schema(tmp_path):
    for v, schema in ((VARIANT_A1, SCHEMA_V1), (VARIANT_A2, SCHEMA_V2)):
        plan, _, _, _, lines, manifest = variant_run(
            tmp_path / f"m-{v}", variant=v)
        assert manifest["exp007_variant"] == v
        assert manifest["state_schema"] == schema
        assert manifest["status"] == "completed"
        keys = {ln["state_key_before"] for ln in lines}
        assert all(k.startswith(f"{schema}|") for k in keys)
        if v == VARIANT_A2:
            assert keys <= {"state-v2|le0", "state-v2|gt0"}
        else:
            assert all(k.endswith("|None") for k in keys)


def test_main_study_plan_remains_v15_untouched(tmp_path):
    plan = build_plan(agent_rng_seed=0, episodes=7, config=cfg(),
                      tref_store=store(), run_root=tmp_path,
                      now_utc="20260917T000000Z")
    assert plan.variant is None
    assert plan.state_schema == SCHEMA_V15
    assert plan.to_dict()["exp007_variant"] is None


def test_build_env_and_agent_selects_encoder_and_neutral_q0(tmp_path):
    base = SparkConfig()          # a config object; no Spark session is built
    for v, schema, n_states in ((VARIANT_A1, SCHEMA_V1, 15),
                                (VARIANT_A2, SCHEMA_V2, 2)):
        plan = build_plan(agent_rng_seed=0, episodes=7, variant=v,
                          config=cfg(), tref_store=store(), run_root=tmp_path,
                          now_utc="20260917T000000Z")
        env, agent, prov = build_env_and_agent(plan, base,
                                               sysmon_enabled=False)
        assert isinstance(env, SparkTuningEnv)
        assert env.encoder.schema_version == schema
        assert env.observation_space_size == n_states
        assert env.action_mapper.mode == "mode12"
        assert agent.n_states == n_states
        assert all(val == 0.5 for row in agent.q_table().values()
                   for val in row)
        assert prov["projection_from_exp002"] is False
        assert prov["source"] == "neutral_default"


def test_build_env_and_agent_main_study_uses_exp002_q0(tmp_path):
    plan = build_plan(agent_rng_seed=0, episodes=7, config=cfg(),
                      tref_store=store(), run_root=tmp_path,
                      now_utc="20260917T000000Z")
    env, agent, prov = build_env_and_agent(plan, SparkConfig(),
                                           sysmon_enabled=False)
    assert env.encoder.schema_version == SCHEMA_V15
    # the stored EXP-002 Q0 has the MEASURED 4 evidence-bearing v1.5 rows
    # (results/experiments/exp-002; DAY28 audit: pairs_initialized = 4)
    assert agent.n_states == 4
    assert all(k.startswith("state-v1.5|") for k in agent.q_table())
    assert any(v != 0.5 for row in agent.q_table().values() for v in row)
    assert prov["source"] == "exp002"


def test_no_test_cells_in_any_variant_transition_log(tmp_path):
    for v in (VARIANT_A1, VARIANT_A2):
        _, _, _, _, lines, _ = variant_run(tmp_path / f"t-{v}", variant=v)
        for ln in lines:
            family, scale, _, _ = ln["episode_key"].split("|")
            assert family != "F4_ski"
            assert scale != "large"


# --- Gate G: main-study machinery unchanged (regression guards) ----------------------
def test_greedy_snapshot_still_side_effect_free():
    ag = QLearningAgent(AgentConfig.from_yaml(), rng_seed=0)
    assert greedy_snapshot(ag) == {}   # no rows inserted by a probe
    assert ag.n_states == 0


def test_neutral_q0_and_exp002_q0_are_separate_apis(tmp_path):
    with pytest.raises(Exception):
        build_q0_from_exp002(result_root=tmp_path,
                             spec_path="experiments/exp002.yaml")
    # ... while the neutral builder is unaffected
    for v in (VARIANT_A1, VARIANT_A2):
        assert build_neutral_q0(v).provenance["variant"] == v
