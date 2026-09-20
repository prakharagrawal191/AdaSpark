"""Unit tests: EXP-008 A4 mode4 action subset (DEC-030 section 4). NO Spark.

A4 is an ACTION-AVAILABILITY change and nothing else. These tests pin that:

* ``mode12`` is unchanged - all 12 frozen configurations, same order, same
  identities, so the main study cannot drift.
* ``mode4`` is exactly ``{0, 3, 6, 9}`` with the four DEC-030 section 4.3
  configurations (0 -> local[2]/sp16, 3 -> local[2]/sp128, 6 -> local[4]/sp64,
  9 -> local[8]/sp32).
* The ORIGINAL action indices are preserved - never renumbered to 0..3 - so an
  action means the same thing in a mode4 log as in a mode12 log.
* Every non-mode4 action is rejected BEFORE any Spark execution.
* Q rows stay 12-wide: mode4 restricts SELECTION, it does not project.
"""
from __future__ import annotations

import pytest

from sparkrl.agent.q_learning import (AgentConfig, QLearningAgent,
                                      state_key_of)
from sparkrl.experiments.grid import build_grid
from sparkrl.rl.state import SCHEMA_V15, StateVector
from sparkrl.rl.action import (MODE4, MODE4_SUBSET, MODE12, ActionMapper,
                               InvalidAction)
from sparkrl.training.exp008 import (A4_ACTION_MODE, A4_ACTION_SUBSET,
                                     ARM_A4_MODE4, NON_A4_ACTIONS,
                                     Exp008ScopeError,
                                     a4_action_configurations, guard_action,
                                     guard_action_mode_for_arm,
                                     guard_q0_action_indices)

pytestmark = [pytest.mark.unit]

# DEC-030 section 4.3, transcribed from the decision table (not from the code).
DEC030_MODE4 = {0: (2, 16), 3: (2, 128), 6: (4, 64), 9: (8, 32)}
DEC030_MODE12 = {
    0: (2, 16), 1: (2, 32), 2: (2, 64), 3: (2, 128),
    4: (4, 16), 5: (4, 32), 6: (4, 64), 7: (4, 128),
    8: (8, 16), 9: (8, 32), 10: (8, 64), 11: (8, 128),
}


# --- mode12 unchanged -----------------------------------------------------------
def test_mode12_is_the_unchanged_frozen_twelve_action_grid():
    mapper = ActionMapper(mode=MODE12)
    assert mapper.size == 12
    assert mapper.allowed_actions() == tuple(range(12))
    for action, (par, shuffle) in DEC030_MODE12.items():
        point = mapper.describe(action)
        assert (point.parallelism, point.shuffle_partitions) == (par, shuffle)
        assert point.grid_index == action


def test_mode12_grid_order_is_parallelism_times_four_plus_shuffle():
    points = sorted((p for p in build_grid(include_b0=True)
                     if p.grid_index is not None), key=lambda p: p.grid_index)
    assert len(points) == 12
    for i, p in enumerate(points):
        assert p.grid_index == i
        assert DEC030_MODE12[i] == (p.parallelism, p.shuffle_partitions)


# --- mode4 subset ---------------------------------------------------------------
def test_mode4_subset_is_exactly_zero_three_six_nine():
    assert MODE4_SUBSET == frozenset({0, 3, 6, 9})
    assert A4_ACTION_SUBSET is MODE4_SUBSET        # reused, never redefined
    assert A4_ACTION_MODE == MODE4
    assert sorted(A4_ACTION_SUBSET) == [0, 3, 6, 9]
    assert MODE4_SUBSET < set(range(12))           # strictly contained


def test_mode4_exposes_only_the_four_actions():
    mapper = ActionMapper(mode=MODE4)
    assert mapper.size == 4
    assert mapper.allowed_actions() == (0, 3, 6, 9)
    assert guard_q0_action_indices(MODE4) == (0, 3, 6, 9)
    assert guard_q0_action_indices(MODE12) == tuple(range(12))


@pytest.mark.parametrize("action,expected", sorted(DEC030_MODE4.items()))
def test_mode4_action_mappings_match_dec030_exactly(action, expected):
    point = ActionMapper(mode=MODE4).describe(action)
    assert (point.parallelism, point.shuffle_partitions) == expected


def test_a4_action_configurations_report_the_four_frozen_rows():
    rows = a4_action_configurations()
    assert [r["action_index"] for r in rows] == [0, 3, 6, 9]
    for row in rows:
        par, shuffle = DEC030_MODE4[row["action_index"]]
        assert (row["parallelism"], row["shuffle_partitions"]) == (par, shuffle)
        # identity is carried, not re-derived
        assert row["grid_index"] == row["action_index"]
        assert row["is_reference"] is False


# --- index preservation / no renumbering ----------------------------------------
def test_mode4_preserves_original_indices_and_never_renumbers():
    mode4, mode12 = ActionMapper(mode=MODE4), ActionMapper(mode=MODE12)
    assert mode4.allowed_actions() != tuple(range(4))     # NOT compacted
    for action in sorted(MODE4_SUBSET):
        a, b = mode4.describe(action), mode12.describe(action)
        assert a.name == b.name
        assert a.grid_index == b.grid_index == action
        assert (a.parallelism, a.shuffle_partitions) == (b.parallelism,
                                                         b.shuffle_partitions)


def test_mode4_identity_is_stable_for_logs_and_manifests():
    """A mode4 log row names the same configuration as a mode12 log row."""
    names4 = {a: ActionMapper(mode=MODE4).describe(a).name
              for a in sorted(MODE4_SUBSET)}
    assert names4 == {0: "G-p2-sp16", 3: "G-p2-sp128",
                      6: "G-p4-sp64", 9: "G-p8-sp32"}


# --- rejection of non-mode4 actions ---------------------------------------------
def test_non_mode4_actions_are_the_complement():
    assert NON_A4_ACTIONS == (1, 2, 4, 5, 7, 8, 10, 11)
    assert set(NON_A4_ACTIONS) | set(MODE4_SUBSET) == set(range(12))
    assert not set(NON_A4_ACTIONS) & set(MODE4_SUBSET)


@pytest.mark.parametrize("action", [1, 2, 4, 5, 7, 8, 10, 11])
def test_mode4_rejects_every_non_subset_action_before_execution(action):
    with pytest.raises(InvalidAction):
        ActionMapper(mode=MODE4).describe(action)
    with pytest.raises(InvalidAction):
        guard_action(action, mode=MODE4)
    # ...and the same index remains perfectly valid under mode12.
    assert guard_action(action, mode=MODE12) == action


@pytest.mark.parametrize("action", [-1, 12, 99, True, 1.5, "0", None])
def test_malformed_actions_are_rejected_in_both_modes(action):
    for mode in (MODE4, MODE12):
        with pytest.raises(InvalidAction):
            guard_action(action, mode=mode)


def test_a4_arm_is_frozen_to_mode4():
    guard_action_mode_for_arm(ARM_A4_MODE4, MODE4)        # the only admissible
    with pytest.raises(Exp008ScopeError):
        guard_action_mode_for_arm(ARM_A4_MODE4, MODE12)
    with pytest.raises(Exp008ScopeError):
        guard_action_mode_for_arm(ARM_A4_MODE4, "mode8")


# --- selection restriction, not projection --------------------------------------
def _mode4_agent(row: list[float]) -> tuple[QLearningAgent, StateVector]:
    state = StateVector(workload_class="agg", input_size_bin="S",
                        feedback_bin="le0", schema_version=SCHEMA_V15)
    cfg = AgentConfig(alpha=0.2, gamma=0.0, epsilon_start=1.0, epsilon_min=0.05,
                      epsilon_decay=0.95, q0_default=0.5, action_mode=MODE4)
    return QLearningAgent(cfg, rng_seed=0,
                          q_table={state_key_of(state): list(row)}), state


def test_agent_rows_stay_twelve_wide_and_selection_is_restricted():
    """mode4 restricts SELECTION; the Q row is never projected to 4 values."""
    row = [0.0] * 12
    row[1] = 99.0        # global maximum, deliberately OUTSIDE mode4
    row[6] = 1.0         # maximum inside mode4
    agent, state = _mode4_agent(row)
    assert agent.allowed_actions() == (0, 3, 6, 9)
    assert len(agent.q_table()[state_key_of(state)]) == 12
    assert len(agent.q_values(state)) == 12
    assert agent.select_action(state, epsilon=0.0) == 6   # never reaches 1


def test_exploration_never_leaves_the_subset():
    agent, state = _mode4_agent([0.0] * 12)
    assert {agent.select_action(state, epsilon=1.0) for _ in range(200)} <= {
        0, 3, 6, 9}


def test_tie_breaking_is_lowest_index_within_the_subset():
    row = [0.0] * 12
    for a in (3, 6, 9):
        row[a] = 1.0
    agent, state = _mode4_agent(row)
    assert agent.select_action(state, epsilon=0.0) == 3   # lowest of the tied


def test_mode12_agent_is_unaffected_by_the_a4_support():
    row = [0.0] * 12
    row[1] = 99.0
    state = StateVector(workload_class="agg", input_size_bin="S",
                        feedback_bin="le0", schema_version=SCHEMA_V15)
    agent = QLearningAgent(AgentConfig.from_yaml(), rng_seed=0,
                           q_table={state_key_of(state): row})
    assert agent.config.action_mode == MODE12        # frozen default
    assert agent.allowed_actions() == tuple(range(12))
    assert agent.select_action(state, epsilon=0.0) == 1
