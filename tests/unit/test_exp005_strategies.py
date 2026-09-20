"""EXP-005 strategy resolution tests (DEC-016 Decisions A and F).

Fixtures and frozen artifacts only: no Spark, no session, no execution, and no
TEST access. Every assertion here is about PRE-EXECUTION configuration choice.
"""
from __future__ import annotations

import pytest

from sparkrl.evaluation.strategies import (B3_K, B4_BUDGET, IMPLEMENTED,
                                           RESOLVED_SPECIFICATIONS,
                                           StrategyResolutionError,
                                           b3_parallelism, b3_partitions,
                                           describe_all, input_gb, resolve)
from sparkrl.spark.config import SparkConfig

pytestmark = [pytest.mark.unit]


# --- B0' identity: DEC-016 Decision A ----------------------------------------
def test_b0_prime_differs_from_b0_in_aqe_alone():
    """The whole justification for B0' being mechanical rests on this."""
    from dataclasses import asdict
    b0 = asdict(resolve("B0").config)
    bp = asdict(resolve("B0'").config)
    differing = {k for k in set(b0) | set(bp) if b0.get(k) != bp.get(k)}
    # app_name differs only so the two are distinguishable in event logs; it is
    # observability metadata, not a tuning value.
    assert differing <= {"aqe_enabled", "app_name"}, differing
    assert b0["aqe_enabled"] is False
    assert bp["aqe_enabled"] is True


def test_b0_prime_is_rejected_if_it_ever_loses_aqe():
    """A B0' that is not AQE-on is not B0' (PLAN:152)."""
    import sparkrl.evaluation.strategies as strat
    original = strat.B0_PRIME_CONFIG
    try:
        strat.B0_PRIME_CONFIG = strat.B0_CONFIG          # AQE-off stand-in
        with pytest.raises(StrategyResolutionError):
            resolve("B0'")
    finally:
        strat.B0_PRIME_CONFIG = original


def test_b0_prime_records_that_execution_is_not_authorized():
    prov = resolve("B0'").provenance
    assert "NOT AUTHORIZED" in prov["execution_gate"]
    assert prov["decision"] == "DEC-016 Decision A"


def test_b0_remains_aqe_off():
    assert resolve("B0").config.aqe_enabled is False


# --- B3: DEC-016 Decision B, and the collapse onto B1 ------------------------
def test_b3_k_is_the_spark_default_partition_size_and_nothing_else():
    """k must remain derivable from outside this project."""
    assert B3_K == pytest.approx(1e9 / 134217728)


def test_b3_collapses_onto_b1_at_this_data_scale():
    """The recorded finding: at 0.039-0.404 GB the rule always clamps to 16."""
    b1 = resolve("B1")
    for family, scale, seed in (("F1_agg", "small", 0), ("F1_agg", "medium", 0),
                                ("F1_agg", "large", 3), ("F5_mixed", "large", 3)):
        b3 = resolve("B3", family=family, scale=scale, dataset_seed=seed)
        assert b3.provenance["partitions"] == 16
        assert b3.config_name == b1.config_name
        assert b3.config_fingerprint == b1.config_fingerprint


def test_b3_rule_is_a_real_clamp_not_a_hardcoded_16():
    """If the data were larger the rule must move; 16 is the clamp, not a constant."""
    assert b3_partitions(0.04) == 16          # below the floor -> clamped
    assert b3_partitions(5.0) == 32           # 37.3 -> nearest frozen level
    assert b3_partitions(20.0) == 128         # 149 -> clamped at the ceiling


def test_b3_parallelism_respects_the_frozen_levels():
    assert b3_parallelism() in (2, 4, 8)


def test_b3_input_gb_comes_from_the_frozen_manifests():
    gb = input_gb("F1_agg", "large", 3)
    assert 0.3 < gb < 0.5                      # measured compressed Parquet
    assert resolve("B3", family="F1_agg", scale="large",
                   dataset_seed=3).provenance["input_gb"] == gb


def test_b3_requires_the_full_cell_identity():
    with pytest.raises(StrategyResolutionError):
        resolve("B3", family="F1_agg")         # scale and seed missing


# --- B4: frozen only by its TRAIN search -------------------------------------
def test_b4_refuses_until_its_train_search_has_run():
    import sparkrl.evaluation.strategies as strat
    if strat.B4_SELECTION_ARTIFACT.exists():
        pytest.skip("B4 search artifact exists; refusal path not exercisable")
    with pytest.raises(StrategyResolutionError) as exc:
        resolve("B4")
    assert "has not been run" in str(exc.value)
    assert "Nothing is guessed" in str(exc.value)


def test_b4_budget_is_the_completed_rl_schedule():
    assert B4_BUDGET == 84


def test_all_six_baselines_are_implemented_and_history_is_retained():
    assert set(IMPLEMENTED) == {"B0", "B0'", "B1", "B2", "B3", "B4"}
    assert set(RESOLVED_SPECIFICATIONS) == {"B3", "B4"}


# --- B1/B2 come from the frozen validation selection -------------------------
def test_b1_matches_the_frozen_selection_artifact():
    import json
    from sparkrl.evaluation.strategies import SELECTION_ARTIFACT
    art = json.loads(SELECTION_ARTIFACT.read_text(encoding="utf-8"))
    assert resolve("B1").config_name == art["B1"]["selected_config"]


@pytest.mark.parametrize("family", ["F1_agg", "F2_join", "F3_rdd", "F5_mixed"])
def test_b2_is_per_family_and_matches_the_artifact(family):
    import json
    from sparkrl.evaluation.strategies import SELECTION_ARTIFACT
    art = json.loads(SELECTION_ARTIFACT.read_text(encoding="utf-8"))
    expected = art["B2"]["selected_config_by_family"][family]
    assert resolve("B2", family=family).config_name == expected


def test_b2_requires_a_family():
    with pytest.raises(StrategyResolutionError):
        resolve("B2")


def test_b2_is_undefined_on_the_unseen_family_f4_ski_dec019():
    """PIN the XP-005 specification gap (DEC-019): B2 has no F4_ski config.

    Validation contains only {F1_agg, F2_join, F3_rdd, F5_mixed} and F4_ski is
    the deliberately unseen TEST family, so the frozen per-family map cannot
    cover it. The driver must record INCOMPLETE, never fall back or tune.
    """
    import json
    from sparkrl.evaluation.strategies import SELECTION_ARTIFACT
    art = json.loads(SELECTION_ARTIFACT.read_text(encoding="utf-8"))
    assert set(art["B2"]["selected_config_by_family"]) == {
        "F1_agg", "F2_join", "F3_rdd", "F5_mixed"}
    with pytest.raises(StrategyResolutionError) as exc:
        resolve("B2", family="F4_ski")
    assert "no frozen configuration" in str(exc.value)
    assert "F4_ski" in str(exc.value)


def test_b1_b2_are_aqe_off_like_the_main_study():
    assert resolve("B1").config.aqe_enabled is False
    assert resolve("B2", family="F1_agg").config.aqe_enabled is False


# --- leakage and provenance ---------------------------------------------------
def test_selection_artifact_is_refused_if_it_ever_reports_test_data(tmp_path):
    import json
    from sparkrl.evaluation.strategies import SELECTION_ARTIFACT
    art = json.loads(SELECTION_ARTIFACT.read_text(encoding="utf-8"))
    art["contains_test_data"] = True
    tainted = tmp_path / "tainted.json"
    tainted.write_text(json.dumps(art), encoding="utf-8")
    with pytest.raises(StrategyResolutionError) as exc:
        resolve("B1", artifact_path=tainted)
    assert "contains_test_data" in str(exc.value)


def test_every_resolution_carries_provenance_and_a_fingerprint():
    for sid, fam in (("B0", None), ("B0'", None), ("B1", None), ("B2", "F1_agg")):
        r = resolve(sid, family=fam)
        assert r.provenance and r.describe
        assert len(r.config_fingerprint) == 64
        assert isinstance(r.config, SparkConfig)


def test_unknown_strategy_is_refused_and_names_the_rl_arms():
    with pytest.raises(StrategyResolutionError) as exc:
        resolve("RL-s0")
    assert "policy_store" in str(exc.value)


def test_inventory_names_the_collapse_and_the_rl_arms():
    inv = describe_all()
    assert "collapses onto B1" in inv["B3"]
    assert "DEC-015" in inv["RL-s0/RL-s1/RL-s2"]
