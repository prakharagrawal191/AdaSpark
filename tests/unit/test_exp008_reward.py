"""Unit tests: EXP-008 A3 reward variants (DEC-030 section 3). NO Spark.

Proves the three registered A3 variants behave exactly as DEC-030 froze them:

* ``R3`` is UNCHANGED - the default calculator, the default weights, the
  default formula id and every computed term are identical to the frozen
  primary reward, so the main study cannot drift.
* ``A3-time-only`` is ``R = 1.0 * clip((T_ref - T)/T_ref, -1, +1)`` with
  failure ``-1.0`` exactly, and is a MULTI-TERM REMOVAL: the task-imbalance
  term AND the spill-waste term are both absent (not zero-weighted leftovers,
  not "missing facts").
* ``A3-R4-log-ratio`` is REGISTERED but NOT executable: constructing it raises
  before any computation, and no R3 behaviour, clipping or failure
  transformation is silently substituted.
"""
from __future__ import annotations

import math

import pytest

from sparkrl.rl.reward import (DEFAULT_REWARD_YAML, FORMULA_A3_R4_LOG_RATIO,
                               FORMULA_A3_TIME_ONLY, FORMULA_ID,
                               FROZEN_WEIGHTS, IMPLEMENTED_FORMULAS,
                               R4_UNRESOLVED_SEMANTICS, REGISTERED_FORMULAS,
                               TIME_ONLY_WEIGHTS, IncompleteFormulaError,
                               RewardCalculator, TRefMissing,
                               load_reward_config)

pytestmark = [pytest.mark.unit]

# A run with a bad CV and heavy spill, so R3's two extra terms are non-trivial
# and their absence under time-only is observable rather than coincidental.
METRICS = {"execution_time_s": 80.0, "task_duration_cv": 9.0,
           "disk_spill_bytes": 10 ** 9}
T_REF = 100.0
INPUT_BYTES = 10 ** 6


# --- registry ------------------------------------------------------------------
def test_registry_names_exactly_the_three_dec030_variants():
    assert REGISTERED_FORMULAS == (FORMULA_ID, FORMULA_A3_TIME_ONLY,
                                   FORMULA_A3_R4_LOG_RATIO)
    # Registration is a naming fact; being implemented is a separate fact.
    assert IMPLEMENTED_FORMULAS == (FORMULA_ID, FORMULA_A3_TIME_ONLY)
    assert FORMULA_A3_R4_LOG_RATIO not in IMPLEMENTED_FORMULAS


def test_unregistered_variant_is_refused():
    with pytest.raises(ValueError):
        RewardCalculator(formula="A3-whatever")


# --- R3 unchanged ---------------------------------------------------------------
def test_r3_default_construction_is_unchanged():
    calc = RewardCalculator()
    assert calc.formula_id == FORMULA_ID
    assert calc.weights == load_reward_config(DEFAULT_REWARD_YAML)
    assert calc.weights == FROZEN_WEIGHTS


def test_r3_explicit_and_default_agree_exactly():
    a = RewardCalculator().compute(METRICS, T_REF, INPUT_BYTES, failed=False)
    b = RewardCalculator(formula=FORMULA_ID).compute(METRICS, T_REF,
                                                     INPUT_BYTES, failed=False)
    assert a.to_dict() == b.to_dict()


def test_r3_still_computes_all_four_frozen_terms():
    r = RewardCalculator().compute(METRICS, T_REF, INPUT_BYTES, failed=False)
    assert r.formula_id == FORMULA_ID
    assert set(r.terms) == {"time_delta", "time_term", "task_term",
                            "spill_ratio", "spill_term"}
    assert r.terms["time_term"] == pytest.approx(0.2)
    assert r.terms["task_term"] == pytest.approx(0.0)     # CV 9.0 -> clipped
    assert r.terms["spill_term"] == pytest.approx(-0.2)
    assert r.value == pytest.approx(0.2 + 0.0 - 0.2)


def test_r3_failure_is_minus_one():
    r = RewardCalculator().compute({}, T_REF, INPUT_BYTES, failed=True)
    assert r.value == -1.0 and r.failed is True
    assert r.formula_id == FORMULA_ID


# --- A3-time-only ---------------------------------------------------------------
def test_time_only_weights_are_the_frozen_one_zero_zero_coefficients():
    calc = RewardCalculator(formula=FORMULA_A3_TIME_ONLY)
    assert calc.weights == TIME_ONLY_WEIGHTS
    assert TIME_ONLY_WEIGHTS["w_time_improvement"] == 1.0
    assert TIME_ONLY_WEIGHTS["w_task_imbalance"] == 0.0
    assert TIME_ONLY_WEIGHTS["w_spill_waste"] == 0.0
    assert TIME_ONLY_WEIGHTS["w_failure"] == 1.0
    assert (TIME_ONLY_WEIGHTS["clip_low"],
            TIME_ONLY_WEIGHTS["clip_high"]) == (-1.0, 1.0)
    # The frozen R3 weights are NOT mutated by the additive variant.
    assert FROZEN_WEIGHTS["w_task_imbalance"] == 0.2
    assert FROZEN_WEIGHTS["w_spill_waste"] == 0.2


@pytest.mark.parametrize("t_exec", [1.0, 50.0, 80.0, 100.0, 120.0, 250.0])
def test_time_only_is_exactly_the_frozen_formula(t_exec):
    """R = 1.0 * clip((T_ref - T)/T_ref, -1, +1), recomputed independently."""
    r = RewardCalculator(formula=FORMULA_A3_TIME_ONLY).compute(
        {"execution_time_s": t_exec}, T_REF, INPUT_BYTES, failed=False)
    expected = 1.0 * max(-1.0, min(1.0, (T_REF - t_exec) / T_REF))
    assert r.value == pytest.approx(expected)
    assert r.formula_id == FORMULA_A3_TIME_ONLY
    assert -1.0 <= r.value <= 1.0


def test_time_only_failure_is_exactly_minus_one():
    r = RewardCalculator(formula=FORMULA_A3_TIME_ONLY).compute(
        METRICS, T_REF, INPUT_BYTES, failed=True)
    assert r.value == -1.0
    assert r.failed is True
    assert r.formula_id == FORMULA_A3_TIME_ONLY
    assert r.terms == {"failure": -1.0}


def test_time_only_has_no_task_imbalance_term_and_no_spill_term():
    """Multi-term REMOVAL: both inputs are removed, not merely zero-weighted.

    They are therefore never read, so they can never appear as terms and can
    never be reported as missing facts either.
    """
    r = RewardCalculator(formula=FORMULA_A3_TIME_ONLY).compute(
        METRICS, T_REF, INPUT_BYTES, failed=False)
    assert set(r.terms) == {"time_delta", "time_term"}
    assert "task_term" not in r.terms and "spill_term" not in r.terms
    assert "spill_ratio" not in r.terms
    assert r.missing == ()


def test_time_only_ignores_cv_and_spill_entirely():
    """Same timing, wildly different CV/spill -> identical reward."""
    calc = RewardCalculator(formula=FORMULA_A3_TIME_ONLY)
    a = calc.compute({"execution_time_s": 80.0}, T_REF, INPUT_BYTES,
                     failed=False)
    b = calc.compute({"execution_time_s": 80.0, "task_duration_cv": 0.0,
                      "disk_spill_bytes": 0}, T_REF, 1, failed=False)
    c = calc.compute(METRICS, T_REF, INPUT_BYTES, failed=False)
    assert a.value == b.value == c.value
    # ...while R3 is genuinely sensitive to exactly those inputs.
    r3 = RewardCalculator()
    clean = r3.compute({"execution_time_s": 80.0, "task_duration_cv": 0.0,
                        "disk_spill_bytes": 0}, T_REF, INPUT_BYTES,
                       failed=False)
    dirty = r3.compute(METRICS, T_REF, INPUT_BYTES, failed=False)
    assert clean.value != dirty.value


def test_time_only_keeps_the_frozen_t_ref_and_timing_rules():
    calc = RewardCalculator(formula=FORMULA_A3_TIME_ONLY)
    for bad_t_ref in (None, 0.0, -1.0):
        with pytest.raises(TRefMissing):
            calc.compute({"execution_time_s": 80.0}, bad_t_ref, INPUT_BYTES,
                         failed=False)
    with pytest.raises(TRefMissing):     # usable run without its timing
        calc.compute({}, T_REF, INPUT_BYTES, failed=False)


# --- A3-R4-log-ratio: registered, NOT executable --------------------------------
def test_r4_is_registered():
    assert FORMULA_A3_R4_LOG_RATIO in REGISTERED_FORMULAS


def test_r4_cannot_be_constructed_and_never_computes():
    with pytest.raises(IncompleteFormulaError) as exc:
        RewardCalculator(formula=FORMULA_A3_R4_LOG_RATIO)
    message = str(exc.value)
    # The refusal must name every unresolved semantic DEC-030 left open.
    for field in R4_UNRESOLVED_SEMANTICS:
        assert field in message


def test_r4_unresolved_semantics_cover_the_dec030_list():
    for field in ("failure_rule", "clipping", "edge_T_le_0",
                  "edge_T_ref_le_0", "edge_missing_execution_time",
                  "edge_failures_timeouts", "coefficients"):
        assert field in R4_UNRESOLVED_SEMANTICS


def test_r4_does_not_silently_fall_back_to_r3_or_time_only():
    """No calculator exists for R4, so no substituted behaviour can exist."""
    with pytest.raises(IncompleteFormulaError):
        RewardCalculator(formula=FORMULA_A3_R4_LOG_RATIO)
    # And nothing anywhere maps R4 onto an implemented weight set.
    assert FORMULA_A3_R4_LOG_RATIO not in IMPLEMENTED_FORMULAS
    # The registered formula itself is well defined but deliberately uncomputed.
    assert math.isclose(-math.log(80.0 / T_REF), 0.22314355131420976)
