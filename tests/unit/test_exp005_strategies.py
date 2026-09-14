"""EXP-005 strategy resolution tests (DEC-016 Decisions A and F).

Fixtures and frozen artifacts only: no Spark, no session, no execution, and no
TEST access. Every assertion here is about PRE-EXECUTION configuration choice.
"""
from __future__ import annotations

import pytest

from sparkrl.evaluation.strategies import (IMPLEMENTED, OPEN_SPECIFICATIONS,
                                           StrategyResolutionError,
                                           StrategyUnspecified, describe_all,
                                           resolve)
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


# --- B3/B4 must refuse rather than invent ------------------------------------
@pytest.mark.parametrize("sid,decision", [("B3", "Decision B"), ("B4", "Decision C")])
def test_unspecified_strategies_refuse_and_name_their_decision(sid, decision):
    with pytest.raises(StrategyUnspecified) as exc:
        resolve(sid)
    assert decision in str(exc.value)
    assert "OPEN" in str(exc.value)


def test_unspecified_strategies_are_not_in_the_implemented_set():
    assert "B3" not in IMPLEMENTED and "B4" not in IMPLEMENTED
    assert set(OPEN_SPECIFICATIONS) == {"B3", "B4"}


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


def test_inventory_reports_open_specifications_honestly():
    inv = describe_all()
    assert inv["B3"].startswith("OPEN") and inv["B4"].startswith("OPEN")
    assert "DEC-015" in inv["RL-s0/RL-s1/RL-s2"]
