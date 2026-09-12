"""Integration (real Spark): agent <-> environment, one episode.

state -> agent.select_action() -> env.step() -> reward -> agent.update() ->
transition record + policy artifact. Small (F2_join/small/seed0, action
selected greedily over the Q0-initialized policy, AQE OFF). NOT a training
experiment.
"""
import json

import pytest

from sparkrl.agent import QLearningAgent, build_policy_artifact, save_policy
from sparkrl.agent.q0 import build_q0_from_exp002
from sparkrl.agent.q_learning import Transition, state_key_of
from sparkrl.rl.env import SparkTuningEnv
from sparkrl.spark.config import SparkConfig

pytestmark = pytest.mark.integration


def test_agent_env_one_real_episode(tmp_path):
    q0 = build_q0_from_exp002()
    agent = QLearningAgent(q_table=q0.q_table, rng_seed=0)
    env = SparkTuningEnv(SparkConfig.from_yaml("configs/baseline_b0.yaml"),
                         result_root=tmp_path, sysmon_enabled=True)

    obs, _ = env.reset(family="F2_join", scale="small", seed=0)
    action = agent.select_action(obs.state, epsilon=0.0)   # greedy
    state_next, reward, terminated, _, step = env.step(action)

    # agent consumes the environment's authoritative reward - never recomputes
    assert -1.0 <= reward <= 2.0
    assert step.reward.formula_id == "R3"
    assert terminated is True
    assert reward == step.reward.value

    delta = agent.update(Transition(
        state=obs.state, action=action, reward=reward,
        next_state=state_next, terminated=terminated, info=step.to_dict()))
    assert isinstance(delta, float)
    assert agent.updates == 1 and env.executions_used == 1
    # Q moved toward the realized reward (gamma=0, alpha=0.2)
    old_q = agent.q_values(obs.state)[action]
    key = state_key_of(obs.state)
    q0_value = q0.q_table[key][action]
    assert old_q == pytest.approx(q0_value + 0.2 * (reward - q0_value))

    # policy artifact persists the post-update state immutably
    art = build_policy_artifact(agent, init_provenance=dict(q0.provenance))
    path = save_policy(art, tmp_path)
    rec = json.loads(path.read_text(encoding="utf-8"))
    assert rec["updates"] == 1 and rec["q_table"] == agent.q_table()
    assert rec["contract_versions"]["reward_formula"] == "R3"