"""Unit tests: frozen v1/v1.5 state spaces (COMP-RL-06, PLAN section 13)."""
import pytest

from sparkrl.rl.state import (FEEDBACK_BINS, FAMILY_TO_CLASS, SCHEMA_V1,
                              SCHEMA_V15, SIZE_BINS, WORKLOAD_CLASSES,
                              StateEncoder, StateVector, feedback_bin_of,
                              size_bin_of)

MIB = 1024 * 1024
GIB = 1024 * MIB


# --- frozen category sets -----------------------------------------------------
def test_frozen_category_sets():
    assert WORKLOAD_CLASSES == ("agg", "join", "rdd_sort", "skew_join", "mixed")
    assert SIZE_BINS == ("S", "M", "L")
    assert FEEDBACK_BINS == ("le0", "gt0")
    assert FAMILY_TO_CLASS == {"F1_agg": "agg", "F2_join": "join",
                               "F3_rdd": "rdd_sort", "F4_ski": "skew_join",
                               "F5_mixed": "mixed"}


def test_space_sizes_15_and_30():
    assert StateVector.space_size(SCHEMA_V1) == 15
    assert StateVector.space_size(SCHEMA_V15) == 30


def test_unknown_schema_rejected():
    with pytest.raises(ValueError):
        StateVector("agg", "S", schema_version="state-v9")
    with pytest.raises(ValueError):
        StateEncoder(schema_version="state-v9")


# --- size bins (frozen byte thresholds) ----------------------------------------
@pytest.mark.parametrize("bytes_,expected", [
    (0, "S"), (100 * MIB, "S"), (512 * MIB - 1, "S"),
    (512 * MIB, "M"), (GIB, "M"), (2 * GIB - 1, "M"),
    (2 * GIB, "L"), (4 * GIB, "L"),
])
def test_size_bin_thresholds(bytes_, expected):
    assert size_bin_of(bytes_) == expected


def test_size_bin_missing_is_error_not_zero():
    with pytest.raises(ValueError):
        size_bin_of(None)
    with pytest.raises(ValueError):
        size_bin_of(-1)


# --- feedback bins --------------------------------------------------------------
def test_feedback_none_maps_to_pessimistic_default():
    assert feedback_bin_of(None) == "le0"       # documented Day-25 convention
    assert feedback_bin_of(0.0) == "le0"
    assert feedback_bin_of(-0.5) == "le0"
    assert feedback_bin_of(0.001) == "gt0"


# --- encoding -------------------------------------------------------------------
def test_encode_all_families_v15():
    enc = StateEncoder()
    got = {f: enc.encode(f, GIB) for f in FAMILY_TO_CLASS}
    assert got["F1_agg"].workload_class == "agg"
    assert got["F2_join"].workload_class == "join"
    assert got["F3_rdd"].workload_class == "rdd_sort"
    assert got["F4_ski"].workload_class == "skew_join"
    assert got["F5_mixed"].workload_class == "mixed"
    assert all(s.feedback_bin == "le0" for s in got.values())  # no history


def test_encode_unknown_family_rejected():
    with pytest.raises(ValueError):
        StateEncoder().encode("F9_unknown", GIB)


def test_state_index_ranges_and_determinism():
    enc = StateEncoder()
    for family in FAMILY_TO_CLASS:
        for b in (100 * MIB, GIB, 3 * GIB):
            s = enc.encode(family, b)
            assert 0 <= s.state_index < 30
    # determinism: same inputs -> identical value object
    a = enc.encode("F2_join", GIB, last_reward=0.5)
    b = enc.encode("F2_join", GIB, last_reward=0.5)
    assert a == b and a.key() == b.key() and hash(a) == hash(b)
    # feedback flips the bin and the index
    neg = enc.encode("F2_join", GIB, last_reward=-1.0)
    assert neg.feedback_bin == "le0" and a.feedback_bin == "gt0"
    assert neg.state_index != a.state_index


def test_v1_schema_ignores_feedback():
    enc = StateEncoder(schema_version=SCHEMA_V1)
    s = enc.encode("F2_join", GIB, last_reward=5.0)
    assert s.feedback_bin is None
    assert 0 <= s.state_index < 15
    with pytest.raises(ValueError):
        StateVector("join", "M", schema_version=SCHEMA_V1, feedback_bin="gt0")


def test_to_dict_deterministic_serializable():
    import json
    enc = StateEncoder()
    s = enc.encode("F1_agg", GIB)
    d1 = s.to_dict()
    d2 = json.loads(json.dumps(s.to_dict()))
    assert d1 == d2
    assert d1["state_index"] == s.state_index
