"""Unit tests: the frozen 12-action domain and Plan-B mode4 (COMP-RL-07)."""
import pytest

from sparkrl.experiments.grid import grid_fingerprint
from sparkrl.rl.action import (MODE12, MODE4, MODE4_SUBSET, ActionMapper,
                               InvalidAction)
from sparkrl.spark.config import SparkConfig

# Expected (parallelism, shuffle_partitions) under the frozen enumeration
# grid_index = parallelism_index * 4 + shuffle_index (PLAN section 14).
EXPECTED = {0: (2, 16), 1: (2, 32), 2: (2, 64), 3: (2, 128),
            4: (4, 16), 5: (4, 32), 6: (4, 64), 7: (4, 128),
            8: (8, 16), 9: (8, 32), 10: (8, 64), 11: (8, 128)}


@pytest.fixture()
def base():
    return SparkConfig.from_yaml("configs/baseline_b0.yaml")


def test_mode12_has_exactly_12_frozen_points():
    m = ActionMapper()
    assert m.size == 12
    assert m.allowed_actions() == tuple(range(12))
    for i, (p, sp) in EXPECTED.items():
        point = m.describe(i)
        assert point.parallelism == p and point.shuffle_partitions == sp
        assert point.grid_index == i and not point.is_reference


def test_b0_is_not_an_action():
    m = ActionMapper()
    names = {m.describe(i).name for i in range(12)}
    assert "B0" not in names
    assert all(not m.describe(i).is_reference for i in range(12))


def test_frozen_grid_fingerprint_matches_exp002():
    assert ActionMapper().grid_fingerprint == grid_fingerprint()


def test_invalid_actions_rejected_before_execution(base):
    m = ActionMapper()
    for bad in (-1, 12, 100, "3", 2.0, None, True, False):
        with pytest.raises(InvalidAction):
            m.describe(bad)  # type: ignore[arg-type]


def test_to_config_applies_frozen_knobs(base):
    m = ActionMapper()
    for i, (p, sp) in EXPECTED.items():
        cfg, point, fp = m.to_config(i, base)
        assert cfg.master == f"local[{p}]"
        assert cfg.shuffle_partitions == sp
        assert cfg.default_parallelism == p
        assert cfg.aqe_enabled is False           # frozen control
        assert point.name == m.describe(i).name
        assert fp == cfg.fingerprint() and len(fp) == 64
    # determinism
    fp1 = m.to_config(5, base)[2]
    fp2 = m.to_config(5, base)[2]
    assert fp1 == fp2


def test_mode4_is_frozen_subset_of_mode12():
    assert MODE4 == "mode4"
    assert MODE4_SUBSET == frozenset({0, 3, 6, 9})
    m4 = ActionMapper(mode=MODE4)
    assert m4.size == 4
    assert m4.allowed_actions() == (0, 3, 6, 9)
    m12 = ActionMapper()
    for i in MODE4_SUBSET:
        assert m4.describe(i).name == m12.describe(i).name  # same configs


def test_mode4_rejects_non_subset_indices():
    m = ActionMapper(mode=MODE4)
    for bad in (1, 2, 4, 5, 7, 8, 10, 11, -1, 12):
        with pytest.raises(InvalidAction):
            m.describe(bad)


def test_unknown_mode_rejected():
    with pytest.raises(ValueError):
        ActionMapper(mode="mode99")
