"""Unit tests: tabular Q-learning agent (COMP-RL-10) - updates, epsilon, determinism.

No Spark. Hand-calculated fixtures only.
"""
import pytest

from sparkrl.agent.q_learning import (AgentConfig, InvalidTransition,
                                      QLearningAgent, Transition)
from sparkrl.agent.policy_store import (PolicyCorrupt, PolicyExistsError,
                                        PolicyVersionMismatch,
                                        agent_from_artifact,
                                        build_policy_artifact, load_policy,
                                        policy_fingerprint, save_policy)
from sparkrl.rl.state import SCHEMA_V15, StateVector

S_A = StateVector("join", "S", schema_version=SCHEMA_V15, feedback_bin="le0")
S_B = StateVector("join", "M", schema_version=SCHEMA_V15, feedback_bin="le0")


def make_agent(**kw):
    cfg = AgentConfig.from_yaml()
    return QLearningAgent(cfg, rng_seed=kw.pop("rng_seed", 0),
                          q_table=kw.pop("q_table", None), **kw)


def test_config_frozen_values():
    cfg = AgentConfig.from_yaml()
    assert (cfg.alpha, cfg.gamma, cfg.epsilon_start, cfg.epsilon_min,
            cfg.epsilon_decay, cfg.q0_default) == (0.2, 0.0, 1.0, 0.05,
                                                   0.95, 0.5)


# --- update rule (hand-calculated) --------------------------------------------
def test_terminal_update_no_bootstrap():
    ag = make_agent(q_table={"state-v1.5|join|S|le0": [1.0] * 12})
    d = ag.update(Transition(S_A, 0, reward=2.0, next_state=None,
                             terminated=True))
    assert ag.q_values(S_A)[0] == pytest.approx(1.2)   # 1 + 0.2*(2-1)
    assert d == pytest.approx(0.2)


def test_nonterminal_update_bootstraps_with_gamma():
    cfg = AgentConfig(alpha=0.2, gamma=0.9, epsilon_start=1.0,
                      epsilon_min=0.05, epsilon_decay=0.95, q0_default=0.5)
    q_sa = [1.0] * 12
    q_next = [3.0, 4.0] + [0.0] * 10
    ag = QLearningAgent(cfg, rng_seed=0,
                        q_table={"state-v1.5|join|S|le0": q_sa,
                                 "state-v1.5|join|M|le0": q_next})
    d = ag.update(Transition(S_A, 1, reward=2.0, next_state=S_B,
                             terminated=False))
    # target = 2 + 0.9*4 = 5.6 ; delta = 0.2*(5.6-1) = 0.92 ; Q = 1.92
    assert ag.q_values(S_A)[1] == pytest.approx(1.92)
    assert d == pytest.approx(0.92)


def test_nonterminal_without_next_state_rejected():
    ag = make_agent()
    with pytest.raises(InvalidTransition):
        ag.update(Transition(S_A, 0, reward=1.0, next_state=None,
                             terminated=False))


def test_invalid_transition_leaves_q_untouched():
    ag = make_agent(q_table={"state-v1.5|join|S|le0": [0.7] * 12})
    cases = [Transition(S_A, 12, 1.0, None, True),
             Transition(S_A, -1, 1.0, None, True),
             Transition(S_A, True, 1.0, None, True),      # type: ignore[arg-type]
             Transition(S_A, 0, float("nan"), None, True),
             Transition(S_A, 0, "x", None, True)]         # type: ignore[arg-type]
    for t in cases:
        with pytest.raises(InvalidTransition):
            ag.update(t)
    assert ag.q_values(S_A) == (0.7,) * 12
    assert ag.updates == 0


# --- epsilon-greedy -------------------------------------------------------------
def test_epsilon_zero_is_greedy_lowest_index_tiebreak():
    ag = make_agent(q_table={"state-v1.5|join|S|le0": [0.5] * 12})
    for _ in range(20):
        assert ag.select_action(S_A, epsilon=0.0) == 0     # tie -> lowest index
    ag._q["state-v1.5|join|S|le0"][2] = 0.9                # action 2 now best
    for _ in range(20):
        assert ag.select_action(S_A, epsilon=0.0) == 2


def test_epsilon_one_always_explores_and_stays_in_domain():
    ag = make_agent(rng_seed=7)
    for _ in range(50):
        a = ag.select_action(S_A, epsilon=1.0)
        assert a in ag.allowed_actions()


def test_seeded_sequence_deterministic():
    seq1 = []
    ag = make_agent(rng_seed=42)
    for _ in range(8):
        seq1.append(ag.select_action(S_A, epsilon=0.5))
    ag2 = make_agent(rng_seed=42)
    seq2 = [ag2.select_action(S_A, epsilon=0.5) for _ in range(8)]
    assert seq1 == seq2
    ag3 = make_agent(rng_seed=43)
    assert [ag3.select_action(S_A, epsilon=0.5) for _ in range(8)] != seq1


def test_mode4_selection_restricted():
    cfg = AgentConfig.from_yaml()
    ag = QLearningAgent(cfg, rng_seed=0)     # default mode12
    ag_m4 = QLearningAgent(AgentConfig(alpha=0.2, gamma=0.0, epsilon_start=1.0,
                                       epsilon_min=0.05, epsilon_decay=0.95,
                                       q0_default=0.5, action_mode="mode4"),
                           rng_seed=0)
    for _ in range(30):
        a = ag_m4.select_action(S_A, epsilon=1.0)
        assert a in (0, 3, 6, 9)


def test_epsilon_decay_frozen_schedule():
    ag = make_agent()
    assert ag.epsilon == 1.0
    assert ag.end_episode() == pytest.approx(0.95)
    ag.epsilon = 0.051
    assert ag.end_episode() == pytest.approx(0.05)   # floor: 0.051*0.95 < 0.05
    assert ag.epsilon == pytest.approx(0.05)


def test_mode4_q0_default_row_is_12_wide():
    ag = make_agent()
    assert len(ag.q_values(S_A)) == 12                # full grid always