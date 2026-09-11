"""Unit tests for the EXP-002 pre-registered spec: scope, split guards, run plan.

Pure Python: the spec layer never touches Spark, the filesystem (beyond reading
the version-controlled YAML) or the network.
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from sparkrl.experiments.spec import (EXPERIMENT_ID, SPEC_VERSION, TEST, TRAIN,
                                      VALIDATION, ExperimentSpec,
                                      assert_train_only, run_id_for, split_of,
                                      summarize_plan,)
from sparkrl.workloads.base import FAMILIES, SCALES, SEEDS

pytestmark = [pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_YAML = REPO_ROOT / "experiments" / "exp002.yaml"

with open(SPEC_YAML, "r", encoding="utf-8") as _fh:
    _RAW = yaml.safe_load(_fh)

PLANNED_RUNS = 208  # 4 families x 2 scales x 2 reps x 13 configurations


def raw(**over):
    """A fresh copy of the pre-registered YAML, mutated by keyword."""
    out = copy.deepcopy(_RAW)
    out.update(over)
    return out


def spec() -> ExperimentSpec:
    return ExperimentSpec.from_yaml(SPEC_YAML)


# --- the pre-registered spec --------------------------------------------

def test_exp002_yaml_loads_and_validates():
    s = spec()
    assert s.experiment_id == EXPERIMENT_ID == "EXP-002"
    assert s.spec_version == SPEC_VERSION == "exp002-spec/v1"
    assert s.aqe_enabled is False
    assert s.families == ("F1_agg", "F2_join", "F3_rdd", "F5_mixed")
    assert s.scales == ("small", "medium")
    assert s.seeds == (0,)
    assert s.repetitions == 2
    assert len(s.grid) == 13
    assert s.validate() is None


def test_planned_run_count_and_plan_length_are_208():
    s = spec()
    assert s.planned_run_count() == PLANNED_RUNS
    assert len(s.plan()) == PLANNED_RUNS
    assert summarize_plan(s.plan())["total"] == PLANNED_RUNS


def test_spec_fingerprint_is_stable_and_sensitive():
    assert spec().fingerprint() == spec().fingerprint()
    assert len(spec().fingerprint()) == 64
    other = ExperimentSpec.from_dict(raw(order_seed=1))
    assert other.fingerprint() != spec().fingerprint()


# --- schema validation ---------------------------------------------------

def test_from_dict_rejects_a_missing_required_key():
    broken = raw()
    del broken["repetitions"]
    with pytest.raises(ValueError, match="missing required key"):
        ExperimentSpec.from_dict(broken)


def test_from_dict_rejects_aqe_enabled():
    with pytest.raises(ValueError, match="aqe_enabled"):
        ExperimentSpec.from_dict(raw(aqe_enabled=True))


def test_from_dict_rejects_an_unknown_family():
    with pytest.raises(ValueError, match="unknown workload family"):
        ExperimentSpec.from_dict(raw(families=["F9_nope"]))


def test_from_dict_rejects_an_unknown_scale():
    with pytest.raises(ValueError, match="unknown scale"):
        ExperimentSpec.from_dict(raw(scales=["huge"]))


def test_from_dict_rejects_an_unknown_seed():
    with pytest.raises(ValueError, match="unknown seed"):
        ExperimentSpec.from_dict(raw(seeds=[99]))


def test_from_dict_rejects_zero_repetitions():
    with pytest.raises(ValueError, match="repetitions"):
        ExperimentSpec.from_dict(raw(repetitions=0))


def test_from_dict_rejects_a_missing_timeout_for_a_declared_scale():
    with pytest.raises(ValueError, match="no timeout declared"):
        ExperimentSpec.from_dict(raw(timeouts_by_scale={"small": 300.0}))


def test_from_dict_rejects_a_non_positive_timeout():
    with pytest.raises(ValueError, match="must be > 0"):
        ExperimentSpec.from_dict(
            raw(timeouts_by_scale={"small": 300.0, "medium": 0.0}))


def _gate(**over):
    gate = copy.deepcopy(_RAW["gate"])
    gate.update(over)
    return gate


def test_gate_rejects_a_missing_key():
    gate = _gate()
    del gate["noise_rule"]
    with pytest.raises(ValueError, match="gate specification missing key"):
        ExperimentSpec.from_dict(raw(gate=gate))


def test_gate_rejects_a_substituted_metric():
    with pytest.raises(ValueError, match="execution_time_s"):
        ExperimentSpec.from_dict(raw(gate=_gate(metric="total_time_s")))


@pytest.mark.parametrize("bad", [0.0, 1.0, 1.5, -0.1])
def test_gate_rejects_out_of_range_min_relative_spread(bad):
    with pytest.raises(ValueError, match="min_relative_spread"):
        ExperimentSpec.from_dict(raw(gate=_gate(min_relative_spread=bad)))


def test_gate_rejects_a_bad_scope():
    with pytest.raises(ValueError, match="scope"):
        ExperimentSpec.from_dict(raw(gate=_gate(scope="everything")))


def test_gate_rejects_min_families_below_one():
    with pytest.raises(ValueError, match="min_families"):
        ExperimentSpec.from_dict(raw(gate=_gate(min_families=0)))


def test_gate_matches_the_plan_h1_sc1_criterion():
    gate = spec().gate
    assert gate["criterion_id"] == "H1/SC1"
    assert gate["metric"] == "execution_time_s"
    assert gate["statistic"] == "median"
    assert gate["min_relative_spread"] == 0.10
    assert gate["min_families"] == 2
    assert gate["scope"] == "varied_only"


# --- run specification determinism --------------------------------------

def test_run_id_for_is_pure_and_deterministic():
    a = run_id_for("F1_agg", "small", 0, "G-p4-sp32", 1)
    b = run_id_for("F1_agg", "small", 0, "G-p4-sp32", 1)
    assert a == b == "exp002-f1-agg-small-s0-g-p4-sp32-r1"
    assert a != run_id_for("F1_agg", "small", 0, "G-p4-sp32", 2)
    with pytest.raises(ValueError, match="rep"):
        run_id_for("F1_agg", "small", 0, "G-p4-sp32", 0)


def test_two_independent_plans_are_identical():
    first = ExperimentSpec.from_yaml(SPEC_YAML).plan()
    second = ExperimentSpec.from_yaml(SPEC_YAML).plan()
    assert [r.run_id for r in first] == [r.run_id for r in second]
    assert [r.order_index for r in first] == [r.order_index for r in second]
    assert [r.block_id for r in first] == [r.block_id for r in second]


def test_plan_has_no_duplicate_run_ids_and_contiguous_order_indices():
    runs = spec().plan()
    ids = [r.run_id for r in runs]
    assert len(set(ids)) == len(ids) == PLANNED_RUNS
    assert [r.order_index for r in runs] == list(range(PLANNED_RUNS))


def test_every_block_contains_each_configuration_exactly_once():
    runs = spec().plan()
    blocks: dict[str, list[str]] = {}
    for r in runs:
        blocks.setdefault(r.block_id, []).append(r.config.name)
    expected = sorted(p.name for p in spec().grid)
    assert len(blocks) == 4 * 2 * 2      # family x scale x rep
    for block_id, names in blocks.items():
        assert sorted(names) == expected, block_id


def test_order_seed_changes_within_block_order_but_not_the_run_set():
    base = spec().plan()
    reordered = ExperimentSpec.from_dict(raw(order_seed=777)).plan()
    assert [r.run_id for r in base] != [r.run_id for r in reordered]
    assert {r.run_id for r in base} == {r.run_id for r in reordered}
    assert len(reordered) == PLANNED_RUNS
    # identity never depends on execution order
    by_id = {r.run_id: r for r in reordered}
    for r in base:
        assert by_id[r.run_id].config.fingerprint() == r.config.fingerprint()
        assert by_id[r.run_id].block_id == r.block_id


def test_relative_path_is_deterministic_and_unique_per_run():
    runs = spec().plan()
    paths = [r.relative_path() for r in runs]
    assert len(set(p.as_posix() for p in paths)) == PLANNED_RUNS
    assert paths == [r.relative_path() for r in runs]
    first = next(r for r in runs
                 if (r.family, r.scale, r.config.name, r.rep)
                 == ("F1_agg", "small", "B0", 1))
    assert first.relative_path().as_posix() == "F1_agg/small/seed0/B0/rep1.json"


# --- train / validation / test assignment -------------------------------

def test_split_of_classifies_the_canonical_cells():
    assert split_of("F1_agg", "small", 0) == TRAIN
    assert split_of("F1_agg", "small", 3) == VALIDATION
    assert split_of("F4_ski", "small", 0) == TEST
    assert split_of("F1_agg", "large", 0) == TEST
    assert split_of("F1_agg", "small", 4) == TEST


def test_test_membership_dominates_validation_and_train():
    assert split_of("F4_ski", "small", 3) == TEST      # test family beats val seed
    assert split_of("F1_agg", "large", 3) == TEST      # test scale beats val seed
    assert split_of("F4_ski", "large", 4) == TEST


def test_split_of_rejects_unknown_cells():
    with pytest.raises(ValueError, match="unknown family"):
        split_of("F9_nope", "small", 0)
    with pytest.raises(ValueError, match="unknown scale"):
        split_of("F1_agg", "huge", 0)
    with pytest.raises(ValueError, match="unknown seed"):
        split_of("F1_agg", "small", 99)


def test_assert_train_only_guards_every_non_train_cell():
    checked = 0
    for family in FAMILIES:
        for scale in SCALES:
            for seed in SEEDS:
                if split_of(family, scale, seed) == TRAIN:
                    assert assert_train_only(family, scale, seed) is None
                else:
                    checked += 1
                    with pytest.raises(ValueError, match="EXP-002 refuses"):
                        assert_train_only(family, scale, seed)
    assert checked > 0


@pytest.mark.parametrize("override", [
    # timeouts are supplied for 'large' so the split guard, not a missing timeout,
    # is what rejects the spec.
    {"scales": ["small", "large"],
     "timeouts_by_scale": {"small": 300.0, "large": 1800.0}},
    {"families": ["F1_agg", "F4_ski"]},
    {"seeds": [3]},
    {"seeds": [4]},
])
def test_spec_declaring_a_frozen_cell_fails_validation(override):
    with pytest.raises(ValueError, match="EXP-002 refuses"):
        ExperimentSpec.from_dict(raw(**override))


def test_plan_emits_train_runs_only():
    runs = spec().plan()
    assert {r.split for r in runs} == {TRAIN}
    assert summarize_plan(runs)["by_split"] == {TRAIN: PLANNED_RUNS}
    assert all(r.family != "F4_ski" and r.scale != "large" and r.seed == 0
               for r in runs)
    assert all(r.config.aqe_enabled is False for r in runs)


def test_to_dict_records_the_split_policy_and_plan_size():
    payload = spec().to_dict(include_plan=True)
    assert payload["planned_run_count"] == PLANNED_RUNS
    assert len(payload["plan"]) == PLANNED_RUNS
    assert payload["split"]["exp002_uses"] == TRAIN
    assert payload["split"]["test_family"] == "F4_ski"
    assert payload["split"]["test_scale"] == "large"
    assert payload["aqe_enabled"] is False
