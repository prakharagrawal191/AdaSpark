"""Unit tests: EXP-007 A1/A2 state representations (DEC-023 sections 2-3).

A1 = the frozen ``state-v1`` encoder, reused unchanged (15 states, context
only). A2 = the new feedback-only ``state-v2`` space (2 states, DEC-023
section 3). Also pins that A1/A2 can never accidentally produce a full
``state-v1.5`` key and that v1/v1.5 behavior is untouched. NO Spark.
"""
import json

import pytest

from sparkrl.agent.q_learning import (InvalidTransition, QLearningAgent,
                                      Transition, state_key_of)
from sparkrl.rl.state import (ENCODER_SCHEMAS, FEEDBACK_BINS, SCHEMA_V1,
                              SCHEMA_V15, SCHEMA_V2, SIZE_BINS,
                              SUPPORTED_SCHEMAS, WORKLOAD_CLASSES,
                              FeedbackState, StateEncoder, StateVector,
                              feedback_bin_of)

pytestmark = [pytest.mark.unit]

MIB = 1024 * 1024
GIB = 1024 * MIB

A1_ENCODER = StateEncoder(schema_version=SCHEMA_V1)
A2_ENCODER = StateEncoder(schema_version=SCHEMA_V2)

FAMILIES = ("F1_agg", "F2_join", "F3_rdd", "F4_ski", "F5_mixed")


# --- Gate A: A1 cardinality + exact combinations ---------------------------------
def test_a1_space_size_is_15():
    assert StateVector.space_size(SCHEMA_V1) == 15
    assert StateVector.space_size(SCHEMA_V1) == len(WORKLOAD_CLASSES) * len(SIZE_BINS)


def test_a1_all_state_combinations_exist():
    keys = set()
    for f in FAMILIES:
        for b in (100 * MIB, GIB, 3 * GIB):
            keys.add(state_key_of(A1_ENCODER.encode(f, b)))
    assert len(keys) == 15
    expected = {f"state-v1|{c}|{b}|None"
                for c in WORKLOAD_CLASSES for b in SIZE_BINS}
    assert keys == expected


def test_a1_encodes_class_and_size_bin():
    s = A1_ENCODER.encode("F2_join", GIB)
    assert s.workload_class == "join"
    assert s.input_size_bin == "M"
    assert s.schema_version == SCHEMA_V1
    s_small = A1_ENCODER.encode("F2_join", 100 * MIB)
    assert s_small.input_size_bin == "S"
    assert s_small.state_index != s.state_index


def test_a1_distinct_classes_and_bins_are_distinct_states():
    indices = set()
    for f in FAMILIES:
        for b in (100 * MIB, GIB, 3 * GIB):
            indices.add(A1_ENCODER.encode(f, b).state_index)
    assert len(indices) == 15                   # all 15 indices reachable
    assert sorted(indices) == list(range(15))


# --- A1: feedback must be absent --------------------------------------------------
@pytest.mark.parametrize("reward", [None, -1.0, 0.0, 0.5, 12.0])
def test_a1_feedback_cannot_change_the_state(reward):
    base = A1_ENCODER.encode("F2_join", GIB, last_reward=reward)
    assert base.feedback_bin is None
    assert base == A1_ENCODER.encode("F2_join", GIB, last_reward=None)
    assert base.key() == A1_ENCODER.encode("F2_join", GIB, last_reward=None).key()
    assert base.state_index == A1_ENCODER.encode("F2_join", GIB).state_index


def test_a1_forces_feedback_bin_none_and_rejects_feedback():
    with pytest.raises(ValueError):
        StateVector("join", "M", schema_version=SCHEMA_V1, feedback_bin="gt0")
    with pytest.raises(ValueError):
        StateVector("join", "M", schema_version=SCHEMA_V1, feedback_bin="le0")


def test_a1_state_key_cannot_contain_a_feedback_bin():
    for f in FAMILIES:
        s = A1_ENCODER.encode(f, GIB, last_reward=5.0)
        assert s.feedback_bin is None
        assert state_key_of(s).endswith("|None")


# --- Gate A: A2 cardinality + exact mapping ----------------------------------------
def test_a2_space_size_is_2():
    assert FeedbackState.space_size() == 2
    assert StateVector.space_size(SCHEMA_V2) == 2


def test_a2_exact_two_state_mapping():
    le0 = FeedbackState(feedback_bin="le0")
    gt0 = FeedbackState(feedback_bin="gt0")
    assert le0.key() == ("state-v2", "le0")
    assert gt0.key() == ("state-v2", "gt0")
    assert state_key_of(le0) == "state-v2|le0"
    assert state_key_of(gt0) == "state-v2|gt0"
    assert le0.state_index == 0 and gt0.state_index == 1
    assert le0 != gt0


def test_a2_encoder_produces_exactly_the_two_frozen_states():
    seen = set()
    for reward in (None, -100.0, -0.001, 0.0, 0.001, 1.0, 42.0):
        s = A2_ENCODER.encode("F2_join", GIB, last_reward=reward)
        assert isinstance(s, FeedbackState)
        seen.add(s.feedback_bin)
    assert seen == {"le0", "gt0"}              # no third state, ever
    # no-history convention is shared with v1.5: None -> le0 (deterministic)
    assert A2_ENCODER.encode("F1_agg", 100 * MIB).feedback_bin == "le0"
    assert feedback_bin_of(None) == "le0"


def test_a2_workload_class_changes_do_not_change_the_state():
    states = {A2_ENCODER.encode(f, GIB, last_reward=0.5) for f in FAMILIES}
    assert len(states) == 1
    assert next(iter(states)) == FeedbackState("gt0")


def test_a2_size_bin_changes_do_not_change_the_state():
    states = {A2_ENCODER.encode("F2_join", b, last_reward=-0.2)
              for b in (100 * MIB, GIB, 3 * GIB)}
    assert len(states) == 1
    assert next(iter(states)) == FeedbackState("le0")
    # even an absent size cannot leak into an A2 state
    s = A2_ENCODER.encode("F2_join", None, last_reward=-0.2)
    assert s == FeedbackState("le0")


@pytest.mark.parametrize("bad", ["gt1", "lt0", "", "GT0", "le0 ", None, 0])
def test_a2_invalid_feedback_fails_deterministically(bad):
    with pytest.raises(ValueError):
        FeedbackState(feedback_bin=bad)


def test_a2_rejects_any_other_schema_identifier():
    with pytest.raises(ValueError):
        FeedbackState("le0", schema_version=SCHEMA_V15)
    with pytest.raises(ValueError):
        FeedbackState("le0", schema_version=SCHEMA_V1)
    with pytest.raises(ValueError):
        FeedbackState("le0", schema_version="state-v9")


def test_a2_key_carries_no_hidden_workload_or_size_information():
    for fb in FEEDBACK_BINS:
        s = FeedbackState(fb)
        assert len(s.key()) == 2
        assert s.key() == (SCHEMA_V2, fb)
        text = state_key_of(s)
        assert text == f"state-v2|{fb}"
        for cls in WORKLOAD_CLASSES:           # no class name in the key
            assert cls not in text
        for b in SIZE_BINS:                    # no size bin in the key
            assert f"|{b}|" not in text and not text.endswith(f"|{b}")
    d = FeedbackState("gt0").to_dict()
    assert set(d) == {"schema_version", "feedback_bin", "state_index"}


def test_a2_deterministic_equality_hash_and_serialization():
    a = A2_ENCODER.encode("F2_join", GIB, last_reward=1.0)
    b = FeedbackState("gt0")
    assert a == b and a.key() == b.key() and hash(a) == hash(b)
    d1 = a.to_dict()
    assert d1 == json.loads(json.dumps(d1))
    assert d1 == {"schema_version": "state-v2", "feedback_bin": "gt0",
                  "state_index": 1}


# --- isolation: A1/A2 can never produce a full v1.5 key -----------------------------
def test_v15_key_sets_are_disjoint_from_a1_and_a2():
    v15_keys = {state_key_of(StateVector(c, b, SCHEMA_V15, fb))
                for c in WORKLOAD_CLASSES for b in SIZE_BINS
                for fb in FEEDBACK_BINS}
    assert len(v15_keys) == 30
    a1_keys = {state_key_of(A1_ENCODER.encode(f, b))
               for f in FAMILIES for b in (100 * MIB, GIB, 3 * GIB)}
    a2_keys = {state_key_of(FeedbackState(fb)) for fb in FEEDBACK_BINS}
    assert a1_keys.isdisjoint(v15_keys)
    assert a2_keys.isdisjoint(v15_keys)
    assert a1_keys.isdisjoint(a2_keys)
    assert all(k.startswith("state-v1.5|") for k in v15_keys)
    assert all(k.startswith("state-v1|") for k in a1_keys)
    assert all(k.startswith("state-v2|") for k in a2_keys)


def test_a2_state_is_never_a_statevector_and_vice_versa():
    assert not isinstance(FeedbackState("le0"), StateVector)
    # StateVector cannot masquerade under the A2 schema: state-v2 is not in
    # the frozen SUPPORTED_SCHEMAS pair, so the attempt is a hard error.
    assert SCHEMA_V2 not in SUPPORTED_SCHEMAS
    assert SUPPORTED_SCHEMAS == (SCHEMA_V1, SCHEMA_V15)   # main-study pin
    assert ENCODER_SCHEMAS == (SCHEMA_V1, SCHEMA_V15, SCHEMA_V2)
    with pytest.raises(ValueError):
        StateVector("join", "S", schema_version=SCHEMA_V2)


def test_unknown_encoder_schema_still_rejected():
    with pytest.raises(ValueError):
        StateEncoder(schema_version="state-v9")


# --- main-study regression guards (v1 / v1.5 untouched) ------------------------------
def test_v1_and_v15_behavior_unchanged():
    assert StateVector.space_size(SCHEMA_V15) == 30
    enc = StateEncoder()
    s = enc.encode("F2_join", GIB, last_reward=0.5)
    assert isinstance(s, StateVector)
    assert s.schema_version == SCHEMA_V15 and s.feedback_bin == "gt0"
    assert s.state_index == (WORKLOAD_CLASSES.index("join")
                             * len(SIZE_BINS) * len(FEEDBACK_BINS)
                             + SIZE_BINS.index("M") * len(FEEDBACK_BINS) + 1)
    s1 = A1_ENCODER.encode("F2_join", GIB, last_reward=0.5)
    assert s1.feedback_bin is None
    assert s1.state_index == (WORKLOAD_CLASSES.index("join")
                              * len(SIZE_BINS) + SIZE_BINS.index("M"))


# --- the learner accepts both state types (A2 path through the frozen agent) ---------
def test_agent_updates_on_a2_feedback_state():
    ag = QLearningAgent(rng_seed=0)
    s = FeedbackState("le0")
    delta = ag.update(Transition(s, 3, reward=1.0, next_state=None,
                                 terminated=True))
    assert ag.updates == 1
    assert ag.q_table()["state-v2|le0"][3] == pytest.approx(0.5 + delta)
    # v1.5 transitions still work unchanged (frozen update rule)
    s15 = StateVector("join", "S", SCHEMA_V15, "le0")
    ag.update(Transition(s15, 0, reward=-1.0, next_state=None, terminated=True))
    assert ag.q_table()[state_key_of(s15)][0] == pytest.approx(
        0.5 + 0.2 * (-1.0 - 0.5))


def test_agent_still_rejects_non_state_objects():
    ag = QLearningAgent(rng_seed=0)
    with pytest.raises(InvalidTransition):
        ag.update(Transition(("join", "S"), 0, reward=1.0, next_state=None,
                             terminated=True))
