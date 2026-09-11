"""Unit tests: the frozen R3 reward formula (COMP-RL-08, PLAN section 15)."""
import pytest
import yaml

from sparkrl.rl.reward import (FROZEN_WEIGHTS, Reward, RewardCalculator,
                               TRefMissing, load_reward_config)

CALC = RewardCalculator()  # loads + frozen-validates configs/reward.yaml


def metrics(t=None, cv=None, spill=None):
    return {"execution_time_s": t, "task_duration_cv": cv,
            "disk_spill_bytes": spill}


# --- config frozen-validation ---------------------------------------------------
def test_reward_yaml_matches_frozen_plan15_values():
    w = load_reward_config()
    for key, frozen in FROZEN_WEIGHTS.items():
        assert w[key] == frozen, key


def test_tampered_reward_yaml_is_refused(tmp_path):
    bad = dict(FROZEN_WEIGHTS, w_time_improvement=0.9)
    p = tmp_path / "reward.yaml"
    p.write_text(yaml.safe_dump({**bad, "formula": "R3"}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_reward_config(p)


# --- exact fixture mathematics ---------------------------------------------------
def test_fast_clean_run_positive_reward():
    # T_ref=10, T=5 -> delta=+0.5 (clip no-op); cv=0.25 -> 0.2*(1-0.5)=+0.1;
    # spill=0 with input given -> ratio 0 -> -0.2*0 = 0
    r = CALC.compute(metrics(5.0, 0.25, 0), t_ref=10.0, input_bytes=1000,
                     failed=False)
    assert r.value == pytest.approx(0.6)
    assert r.terms["time_term"] == pytest.approx(0.5)
    assert r.terms["task_term"] == pytest.approx(0.1)
    assert r.terms["spill_term"] == pytest.approx(0.0)
    assert r.missing == () and r.failed is False


def test_slow_run_clipped_at_minus_one():
    # T=20 vs T_ref=10 -> delta=-1.0 (clip); cv=0.5 -> 0; spill ratio
    # 0.05/0.10=0.5 -> -0.1  =>  R = -1.0 + 0.0 - 0.1 = -1.1
    r = CALC.compute(metrics(20.0, 0.5, 50), t_ref=10.0, input_bytes=1000,
                     failed=False)
    assert r.value == pytest.approx(-1.1)
    assert r.terms["time_delta"] == pytest.approx(-1.0)


def test_clipping_upper_bound():
    # T=1 vs T_ref=10 -> delta=0.9; hmm 0.9 < 1.0 so no clip; use T=0.1:
    # delta=0.99 -> clip no-op; to test the +1 clip use T -> 0:
    r = CALC.compute(metrics(1e-9, 0.0, 0), t_ref=10.0, input_bytes=1000,
                     failed=False)
    assert r.terms["time_delta"] == pytest.approx(1.0, abs=1e-9)
    assert r.terms["time_term"] == pytest.approx(1.0)


def test_spill_penalty_saturates_at_reference_ratio():
    # ratio 0.10 == reference -> penalty -0.2 (full); ratio 0.5 -> also -0.2
    r1 = CALC.compute(metrics(10.0, 0.0, 100), t_ref=10.0, input_bytes=1000,
                      failed=False)
    r2 = CALC.compute(metrics(10.0, 0.0, 500), t_ref=10.0, input_bytes=1000,
                      failed=False)
    assert r1.terms["spill_term"] == pytest.approx(-0.2)
    assert r2.terms["spill_term"] == pytest.approx(-0.2)


def test_missing_cv_recorded_not_fabricated():
    r = CALC.compute(metrics(5.0, None, 0), t_ref=10.0, input_bytes=1000,
                     failed=False)
    assert r.value == pytest.approx(0.5)          # time term only
    assert "task_duration_cv" in r.missing
    assert r.terms["task_term"] == 0.0


def test_missing_input_bytes_recorded_not_fabricated():
    r = CALC.compute(metrics(5.0, 0.0, 999), t_ref=10.0, input_bytes=None,
                     failed=False)
    assert r.value == pytest.approx(0.7)          # 0.5 + 0.2 (cv=0 -> +0.2)
    assert "input_bytes" in r.missing


def test_failed_run_is_exactly_minus_one():
    r = CALC.compute(metrics(None, None, None), t_ref=10.0, input_bytes=1000,
                     failed=True)
    assert r.value == -1.0 and r.failed is True
    assert r.terms == {"failure": -1.0}


def test_timeout_counts_as_failure():
    r = CALC.compute(metrics(999.0, 0.1, 0), t_ref=10.0, input_bytes=1000,
                     failed=True)
    assert r.value == -1.0


# --- hard errors ------------------------------------------------------------------
def test_missing_tref_is_hard_error():
    with pytest.raises(TRefMissing):
        CALC.compute(metrics(5.0, 0.0, 0), t_ref=None, input_bytes=1000,
                     failed=False)
    with pytest.raises(TRefMissing):
        CALC.compute(metrics(5.0, 0.0, 0), t_ref=0.0, input_bytes=1000,
                     failed=False)
    with pytest.raises(TRefMissing):
        CALC.compute(metrics(5.0, 0.0, 0), t_ref=-3.0, input_bytes=1000,
                     failed=False)


def test_usable_run_without_timing_is_error_not_zero():
    with pytest.raises(TRefMissing):
        CALC.compute(metrics(None, 0.1, 0), t_ref=10.0, input_bytes=1000,
                     failed=False)


# --- determinism -------------------------------------------------------------------
def test_reward_is_deterministic_and_order_independent():
    m1 = {"execution_time_s": 5.0, "task_duration_cv": 0.25,
          "disk_spill_bytes": 0, "extra_key": "ignored"}
    m2 = {"extra_key": "ignored", "disk_spill_bytes": 0,
          "task_duration_cv": 0.25, "execution_time_s": 5.0}
    r1 = CALC.compute(m1, t_ref=10.0, input_bytes=1000, failed=False)
    r2 = CALC.compute(m2, t_ref=10.0, input_bytes=1000, failed=False)
    assert r1.value == r2.value
    assert r1.to_dict() == r2.to_dict()


def test_reward_to_dict_shape():
    d = Reward(value=0.5, t_ref_s=10.0).to_dict()
    assert set(d) == {"formula_id", "value", "t_ref_s", "failed", "terms",
                      "missing"}
