"""Unit tests: EXP-007 A1/A2 neutral Q0 initialization (DEC-023 section 4).

Proves: every valid (state, action) pair initializes to exactly 0.5; no
missing pairs; no EXP-002 Q0 projection / median pooling; repeated
initialization is identical; the main-study Q0 builder is untouched. NO
Spark, no record store, no gate artifact.
"""
from pathlib import Path

import pytest
import yaml

from sparkrl.agent.q0 import (ABLATION_VARIANTS, Q0_NEUTRAL_VERSION,
                              Q0SourceError, VARIANT_A1, VARIANT_A2,
                              build_neutral_q0, build_q0_from_exp002,
                              neutral_q0_states, neutral_state_schema)
from sparkrl.agent.q_learning import (FROZEN_HYPERPARAMS, QLearningAgent,
                                      state_key_of)
from sparkrl.rl.state import (FEEDBACK_BINS, SCHEMA_V1, SCHEMA_V2,
                              SIZE_BINS, WORKLOAD_CLASSES, FeedbackState,
                              StateVector)

pytestmark = [pytest.mark.unit]

RL_YAML = Path(__file__).resolve().parents[2] / "configs" / "rl.yaml"


def a1_keys() -> set[str]:
    return {state_key_of(s) for s in neutral_q0_states(VARIANT_A1)}


def a2_keys() -> set[str]:
    return {state_key_of(s) for s in neutral_q0_states(VARIANT_A2)}


# --- Gate B: A1 = 15 states x 12 actions, all 0.5 --------------------------------
def test_a1_neutral_q0_cardinality_and_values():
    r = build_neutral_q0(VARIANT_A1)
    expected = {f"state-v1|{c}|{b}|None"
                for c in WORKLOAD_CLASSES for b in SIZE_BINS}
    assert set(r.q_table) == expected
    assert len(r.q_table) == 15
    assert all(len(row) == 12 for row in r.q_table.values())
    assert all(v == 0.5 for row in r.q_table.values() for v in row)
    assert r.provenance["pairs_initialized"] == 15 * 12
    assert r.provenance["q0_version"] == Q0_NEUTRAL_VERSION


def test_a2_neutral_q0_cardinality_and_values():
    r = build_neutral_q0(VARIANT_A2)
    assert set(r.q_table) == {"state-v2|le0", "state-v2|gt0"}
    assert len(r.q_table) == 2
    assert all(len(row) == 12 for row in r.q_table.values())
    assert all(v == 0.5 for row in r.q_table.values() for v in row)
    assert r.provenance["pairs_initialized"] == 2 * 12


# --- no missing pairs, exhaustive over the frozen spaces ---------------------------
def test_neutral_q0_states_are_exhaustive():
    assert len(neutral_q0_states(VARIANT_A1)) == 15
    assert len({s.state_index for s in neutral_q0_states(VARIANT_A1)}) == 15
    assert len(neutral_q0_states(VARIANT_A2)) == 2
    assert [s.feedback_bin for s in neutral_q0_states(VARIANT_A2)] == list(FEEDBACK_BINS)


# --- no EXP-002 projection / no v1.5 rows / no prior policy ------------------------
def test_no_projection_from_exp002():
    r1, r2 = build_neutral_q0(VARIANT_A1), build_neutral_q0(VARIANT_A2)
    assert r1.provenance["projection_from_exp002"] is False
    assert r2.provenance["projection_from_exp002"] is False
    assert r1.provenance["aggregation"] is None          # no median pooling
    assert r1.provenance["source"] == "neutral_default"
    for r in (r1, r2):
        assert not any(k.startswith("state-v1.5|") for k in r.q_table)
    assert a1_keys().isdisjoint(a2_keys())
    # the value is the frozen configs/rl.yaml q0_default, not a derived number
    raw = yaml.safe_load(RL_YAML.read_text(encoding="utf-8"))
    assert FROZEN_HYPERPARAMS["q0_default"] == raw["q0_default"] == 0.5
    assert r1.provenance["q0_default"] == 0.5


def test_neutral_q0_has_no_dependency_on_the_exp002_record_store(monkeypatch):
    def explode(*a, **k):  # noqa: ANN002, ANN003
        raise AssertionError("neutral Q0 must not read EXP-002 records")
    monkeypatch.setattr("sparkrl.agent.q0.load_records", explode)
    r = build_neutral_q0(VARIANT_A2)
    assert all(v == 0.5 for row in r.q_table.values() for v in row)


def test_repeated_initialization_is_identical():
    for variant in ABLATION_VARIANTS:
        a, b = build_neutral_q0(variant), build_neutral_q0(variant)
        assert a.q_table == b.q_table
        assert a.provenance == b.provenance
        assert list(a.q_table) == list(b.q_table)   # deterministic order


def test_unknown_variant_is_a_hard_error():
    for bad in ("A3", "a1", "FULL", None, ""):
        with pytest.raises(ValueError):
            build_neutral_q0(bad)          # type: ignore[arg-type]
        with pytest.raises(ValueError):
            neutral_state_schema(bad)      # type: ignore[arg-type]


def test_variant_state_schemas_are_frozen():
    assert neutral_state_schema(VARIANT_A1) == SCHEMA_V1
    assert neutral_state_schema(VARIANT_A2) == SCHEMA_V2
    assert ABLATION_VARIANTS == (VARIANT_A1, VARIANT_A2)


# --- the frozen agent consumes the neutral table -------------------------------------
def test_agent_sees_all_fifty_cent_rows():
    ag = QLearningAgent(q_table=build_neutral_q0(VARIANT_A1).q_table, rng_seed=0)
    assert ag.n_states == 15
    for c in WORKLOAD_CLASSES:
        for b in SIZE_BINS:
            row = ag.q_values(StateVector(c, b, SCHEMA_V1))
            assert row == (0.5,) * 12
    ag2 = QLearningAgent(q_table=build_neutral_q0(VARIANT_A2).q_table, rng_seed=1)
    assert ag2.n_states == 2
    for fb in FEEDBACK_BINS:
        assert ag2.q_values(FeedbackState(fb)) == (0.5,) * 12


# --- main-study Q0 builder untouched (regression guard) ------------------------------
def test_main_study_q0_still_refuses_empty_record_store(tmp_path):
    with pytest.raises(Q0SourceError):
        build_q0_from_exp002(result_root=tmp_path,
                             spec_path="experiments/exp002.yaml")
