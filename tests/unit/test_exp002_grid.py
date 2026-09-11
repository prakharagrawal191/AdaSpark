"""Unit tests for the EXP-002 configuration grid (PLAN section 14 action space).

Pure Python: no Spark session is ever created, only SparkConfig objects.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

from sparkrl.experiments.grid import (B0_DRIVER_MEMORY, GRID_VERSION,
                                      PARALLELISM_LEVELS,
                                      SHUFFLE_PARTITION_LEVELS,
                                      VARIED_PARAMETERS, ConfigPoint,
                                      assert_b0_unchanged, b0_point,
                                      build_grid, grid_fingerprint,
                                      validate_grid,)
from sparkrl.spark.config import SparkConfig

pytestmark = [pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[2]
B0_YAML = REPO_ROOT / "configs" / "baseline_b0.yaml"


def _varied(**over) -> ConfigPoint:
    """A structurally valid varied point, mutated by keyword for rejection tests."""
    base = dict(name="G-p2-sp16", grid_index=0, is_reference=False,
                master="local[2]", shuffle_partitions=16, default_parallelism=2,
                driver_memory=B0_DRIVER_MEMORY, aqe_enabled=False)
    base.update(over)
    return ConfigPoint(**base)


# --- shape ---------------------------------------------------------------

def test_grid_has_thirteen_points_twelve_varied_one_reference():
    grid = build_grid()
    assert len(grid) == 13
    assert len([p for p in grid if not p.is_reference]) == 12
    assert len([p for p in grid if p.is_reference]) == 1
    assert grid[0].name == "B0"  # reference first (frozen enumeration order)


def test_build_grid_without_b0_has_twelve_points_and_no_reference():
    grid = build_grid(include_b0=False)
    assert len(grid) == 12
    assert not any(p.is_reference for p in grid)
    assert "B0" not in {p.name for p in grid}
    assert b0_point() in build_grid()


def test_no_duplicate_names_or_fingerprints():
    grid = build_grid()
    names = [p.name for p in grid]
    prints = [p.fingerprint() for p in grid]
    assert len(set(names)) == len(names) == 13
    assert len(set(prints)) == len(prints) == 13


# --- configuration identity ---------------------------------------------

def test_fingerprint_is_stable_and_is_sha256_over_canonical_knobs():
    point = build_grid(include_b0=False)[5]
    assert point.fingerprint() == point.fingerprint()  # stable across calls
    expected = hashlib.sha256(
        json.dumps(point.knobs(), sort_keys=True,
                   separators=(",", ":")).encode("utf-8")).hexdigest()
    assert point.fingerprint() == expected
    assert len(point.fingerprint()) == 64


def test_fingerprint_depends_only_on_knobs_not_on_name_or_index():
    point = build_grid(include_b0=False)[0]
    renamed = dataclasses.replace(point, name="renamed", grid_index=99)
    assert renamed.fingerprint() == point.fingerprint()
    assert dataclasses.replace(point, shuffle_partitions=32).fingerprint() \
        != point.fingerprint()


def test_grid_fingerprint_is_stable_and_version_tagged():
    assert grid_fingerprint() == grid_fingerprint(build_grid())
    assert grid_fingerprint(build_grid(include_b0=False)) != grid_fingerprint()
    assert GRID_VERSION == "exp002-grid/v1"


# --- PLAN section 14 levels and enumeration order ------------------------

def test_varied_points_use_only_plan_14_levels_and_couple_parallelism():
    for p in build_grid(include_b0=False):
        assert p.parallelism in PARALLELISM_LEVELS
        assert p.shuffle_partitions in SHUFFLE_PARTITION_LEVELS
        assert p.default_parallelism == p.parallelism   # local[N] <-> default.parallelism
        assert p.master == "local[%d]" % p.parallelism
        assert p.name == "G-p%d-sp%d" % (p.parallelism, p.shuffle_partitions)
    combos = {(p.parallelism, p.shuffle_partitions)
              for p in build_grid(include_b0=False)}
    assert combos == {(par, sp) for par in PARALLELISM_LEVELS
                      for sp in SHUFFLE_PARTITION_LEVELS}


def test_grid_index_ordering_and_plan_b_anchor_subset():
    by_index = {p.grid_index: p for p in build_grid(include_b0=False)}
    assert sorted(by_index) == list(range(12))
    for p_idx, parallelism in enumerate(PARALLELISM_LEVELS):
        for s_idx, partitions in enumerate(SHUFFLE_PARTITION_LEVELS):
            point = by_index[p_idx * 4 + s_idx]
            assert (point.parallelism, point.shuffle_partitions) \
                == (parallelism, partitions)
    # ARCHITECTURE_FREEZE COMP-RL-07: Plan-B subset is indices {0,3,6,9}.
    assert [by_index[i].name for i in (0, 3, 6, 9)] == [
        "G-p2-sp16", "G-p2-sp128", "G-p4-sp64", "G-p8-sp32"]


def test_b0_reference_point_matches_the_frozen_definition():
    b0 = b0_point()
    assert (b0.name, b0.is_reference, b0.grid_index) == ("B0", True, None)
    assert b0.master == "local[2]"
    assert b0.shuffle_partitions == 200
    assert b0.default_parallelism is None
    assert b0.driver_memory == "6g"
    assert b0.aqe_enabled is False


# --- frozen controls -----------------------------------------------------

def test_aqe_is_off_on_every_grid_point():
    assert all(p.aqe_enabled is False for p in build_grid())
    assert all(p.knobs()["spark.sql.adaptive.enabled"] is False for p in build_grid())


def test_driver_memory_is_frozen_on_every_grid_point():
    assert all(p.driver_memory == B0_DRIVER_MEMORY for p in build_grid())


# --- invalid configuration rejection ------------------------------------

def test_validate_grid_accepts_the_real_grid():
    assert validate_grid(build_grid()) is None


def test_validate_grid_rejects_aqe_enabled():
    with pytest.raises(ValueError, match="AQE"):
        validate_grid([_varied(aqe_enabled=True)])


def test_validate_grid_rejects_an_empty_grid():
    with pytest.raises(ValueError, match="empty"):
        validate_grid([])


def test_validate_grid_rejects_duplicate_names():
    a = _varied(name="G-dup", grid_index=0)
    b = _varied(name="G-dup", grid_index=1, shuffle_partitions=32)
    with pytest.raises(ValueError, match="duplicate configuration names"):
        validate_grid([a, b])


def test_validate_grid_rejects_duplicate_fingerprints():
    a = _varied(name="G-p2-sp16", grid_index=0)
    clone = dataclasses.replace(a, name="G-p2-sp16-copy", grid_index=1)
    with pytest.raises(ValueError, match="duplicate configuration fingerprints"):
        validate_grid([a, clone])


def test_validate_grid_rejects_non_contiguous_indices():
    grid = build_grid(include_b0=False)
    with pytest.raises(ValueError, match="contiguous"):
        validate_grid([grid[0], grid[2]])


def test_validate_grid_rejects_two_reference_points():
    b0 = b0_point()
    other = dataclasses.replace(b0, name="B0-alt", shuffle_partitions=201)
    with pytest.raises(ValueError, match="more than one reference"):
        validate_grid([b0, other])


def test_validate_grid_rejects_off_grid_parallelism():
    with pytest.raises(ValueError, match="outside PLAN-14 levels"):
        validate_grid([_varied(name="G-p3-sp16", master="local[3]",
                               default_parallelism=3)])


def test_validate_grid_rejects_off_grid_shuffle_level():
    with pytest.raises(ValueError, match="outside"):
        validate_grid([_varied(name="G-p2-sp17", shuffle_partitions=17)])


def test_validate_grid_rejects_decoupled_default_parallelism():
    with pytest.raises(ValueError, match="default_parallelism"):
        validate_grid([_varied(default_parallelism=4)])


def test_validate_grid_rejects_changed_driver_memory():
    with pytest.raises(ValueError, match="driver memory"):
        validate_grid([_varied(driver_memory="8g")])


def test_validate_grid_rejects_a_non_local_master():
    with pytest.raises(ValueError, match="local"):
        validate_grid([_varied(master="yarn")])


# --- delta from B0 -------------------------------------------------------

def test_delta_from_b0_is_empty_for_the_reference():
    assert b0_point().delta_from_b0() == {}


def test_delta_from_b0_names_exactly_the_differing_varied_parameters():
    b0_knobs = b0_point().knobs()
    for p in build_grid(include_b0=False):
        delta = p.delta_from_b0()
        expected = {k for k, v in p.knobs().items() if v != b0_knobs[k]}
        assert set(delta) == expected
        assert expected  # every candidate differs from the reference somehow
        assert set(delta) <= set(VARIED_PARAMETERS)
        for key, change in delta.items():
            assert change == {"b0": b0_knobs[key], "candidate": p.knobs()[key]}


def test_delta_from_b0_for_a_named_point():
    point = next(p for p in build_grid() if p.name == "G-p4-sp32")
    assert point.delta_from_b0() == {
        "spark.default.parallelism": {"b0": None, "candidate": 4},
        "spark.master": {"b0": "local[2]", "candidate": "local[4]"},
        "spark.sql.shuffle.partitions": {"b0": 200, "candidate": 32},
    }


# --- application to SparkConfig -----------------------------------------

def test_apply_to_sets_requested_knobs_and_preserves_frozen_controls():
    base = SparkConfig.from_yaml(B0_YAML)
    point = next(p for p in build_grid() if p.name == "G-p8-sp128")
    cfg = point.apply_to(base)
    assert cfg.master == "local[8]"
    assert cfg.shuffle_partitions == 128
    assert cfg.default_parallelism == 8
    assert cfg.aqe_enabled is False
    assert cfg.driver_memory == base.driver_memory
    assert cfg.warmup_runs == base.warmup_runs          # warm-up policy untouched
    assert cfg.warmup_micro_job == base.warmup_micro_job
    assert base.master == "local[2]"                    # original untouched


def test_apply_to_forces_aqe_off_even_if_the_base_had_it_on():
    base = SparkConfig.from_yaml(B0_YAML).with_overrides(aqe_enabled=True)
    cfg = build_grid(include_b0=False)[0].apply_to(base)
    assert cfg.aqe_enabled is False
    assert cfg.warmup_runs == base.warmup_runs


def test_apply_to_b0_materialises_sparks_own_local_mode_default_parallelism():
    """B0 declares default_parallelism=None; the SESSION must still hold 2.

    ``spark.default.parallelism`` survives SparkContext.stop() inside one JVM, so
    leaving it unset lets the previous run's value leak in. Applying B0 therefore
    materialises Spark's own local-mode default (N from local[N] = 2) explicitly.
    The declared identity keeps None - that is what B0 specifies.
    """
    base = SparkConfig.from_yaml(B0_YAML)
    point = b0_point()
    assert point.default_parallelism is None          # declared identity
    assert point.effective_default_parallelism() == 2  # what the session must hold

    cfg = point.apply_to(base)
    assert (cfg.master, cfg.shuffle_partitions, cfg.default_parallelism) \
        == ("local[2]", 200, 2)
    assert cfg.aqe_enabled is False
    # the declared B0 (the yaml) is untouched by applying it
    assert assert_b0_unchanged(base) is None


def test_effective_default_parallelism_matches_local_n_for_every_point():
    for point in build_grid():
        assert point.effective_default_parallelism() == point.parallelism


# --- B0 drift guard ------------------------------------------------------

def test_assert_b0_unchanged_passes_on_the_real_baseline_file():
    assert assert_b0_unchanged(SparkConfig.from_yaml(B0_YAML)) is None


@pytest.mark.parametrize("override, expected", [
    ({"master": "local[4]"}, "master"),
    ({"shuffle_partitions": 64}, "shuffle_partitions"),
    ({"default_parallelism": 4}, "default_parallelism"),
    ({"driver_memory": "8g"}, "driver_memory"),
    ({"aqe_enabled": True}, "aqe_enabled"),
])
def test_assert_b0_unchanged_detects_drift(override, expected):
    drifted = SparkConfig.from_yaml(B0_YAML).with_overrides(**override)
    with pytest.raises(ValueError, match=expected):
        assert_b0_unchanged(drifted)
