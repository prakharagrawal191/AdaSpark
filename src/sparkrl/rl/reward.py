"""Reward calculator: the FROZEN R3 formula (COMP-RL-08) - no tuning, no learning.

Frozen source (PLAN section 15):

    R = 1.0 * clip((T_ref - T) / T_ref, -1, +1)          # primary time term
      + 0.2 * (1 - min(1, CV_task / 0.5))                # task-imbalance term
      - 0.2 * min(1, (spill_disk_bytes / input_bytes) / 0.10)   # spill waste
      - 1.0 * 1[failure or timeout]

    T_ref = default-configuration time for the same workload instance + seed,
    calibrated once (EXP-002/003); used only for reward normalization and
    NEVER shown to the agent as state.

Weights live in ``configs/reward.yaml`` and are frozen (Day-25) - the
calculator validates them against the frozen values and refuses any other
number. Behaviour on missing facts is explicit, never fabricated:

* ``T_ref`` missing / non-positive  -> ``TRefMissing`` (COMP-RL-08 hard error),
  raised BEFORE any Spark execution by the environment.
* failed / timed-out run            -> R = -1.0 exactly (PLAN section 13:
  "missing features at decision time => run-failure path (reward -1)").
  No other terms are computed from a failed run.
* ``task_duration_cv`` is None      -> task-imbalance term contributes 0.0 and
  is listed in ``missing`` (recorded, never guessed).
* ``input_bytes`` unavailable       -> spill term contributes 0.0 and is
  listed in ``missing``.

This module computes; it does NOT optimize, adapt, or store anything.

ADDITIVE EXP-008 SUPPORT (DEC-030 section 3; default-preserving)
---------------------------------------------------------------
DEC-030 froze the A3 reward variants. This module now also registers:

* ``R3``              - the frozen primary formula above. UNCHANGED: the
                        default constructor and the default compute path are
                        byte/behaviour equivalent to the pre-EXP-008 code.
* ``A3-time-only``    - ``R = 1.0 * clip((T_ref - T) / T_ref, -1, +1)`` with
                        failure ``R = -1.0`` exactly. This is a MULTI-TERM
                        REMOVAL from R3: BOTH the task-imbalance term and the
                        spill-waste term are removed simultaneously. It is NOT
                        a one-factor ablation.
* ``A3-R4-log-ratio`` - REGISTERED ONLY. DEC-030 section 3.3 / section 12
                        field 15 leaves the complete R4 specification
                        unresolved (failure rule, coefficients, clipping,
                        T<=0, T_ref<=0, missing timing, timeout semantics).
                        R4 therefore CANNOT execute: constructing a
                        calculator for it raises ``IncompleteFormulaError``
                        before any computation. R3 behaviour is never
                        substituted and no clipping is ever applied silently.

Being REGISTERED is deliberately distinct from being IMPLEMENTED: the enum
existing does not make R4 executable.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

PROJECT = Path(__file__).resolve().parents[3]
DEFAULT_REWARD_YAML = PROJECT / "configs" / "reward.yaml"

FORMULA_ID = "R3"

# Frozen weights (PLAN section 15). The calculator refuses a YAML that
# disagrees with these values.
FROZEN_WEIGHTS: dict[str, float] = {
    "w_time_improvement": 1.0,
    "w_task_imbalance": 0.2,
    "task_cv_reference": 0.5,
    "w_spill_waste": 0.2,
    "spill_ratio_reference": 0.10,
    "w_failure": 1.0,
    "clip_low": -1.0,
    "clip_high": 1.0,
}

# --- EXP-008 A3 variant registry (DEC-030 section 3; additive) ---------------
# DEC-030 section 3.1 registers exactly three A3 reward variants. No other
# reward variant exists in registered PLAN intent, and DEC-030 introduces none.
FORMULA_A3_TIME_ONLY = "A3-time-only"
FORMULA_A3_R4_LOG_RATIO = "A3-R4-log-ratio"

# Every variant DEC-030 names. Registration is a naming fact only.
REGISTERED_FORMULAS: tuple[str, ...] = (
    FORMULA_ID, FORMULA_A3_TIME_ONLY, FORMULA_A3_R4_LOG_RATIO)

# Variants whose complete semantics DEC-030 froze, and which are therefore
# implemented here. R4 is deliberately absent.
IMPLEMENTED_FORMULAS: tuple[str, ...] = (FORMULA_ID, FORMULA_A3_TIME_ONLY)

# DEC-030 section 3.2 (table row "Coefficients"): time-only = R3 with the
# task-imbalance term AND the spill-waste term removed simultaneously.
# Frozen values, never read from configs/reward.yaml (that file freezes the
# primary R3 formula only).
TIME_ONLY_WEIGHTS: dict[str, float] = {
    "w_time_improvement": 1.0,
    "w_task_imbalance": 0.0,
    "w_spill_waste": 0.0,
    "w_failure": 1.0,
    "clip_low": -1.0,
    "clip_high": 1.0,
}

# DEC-030 section 3.3 / section 12 field 15: the complete R4 specification is
# UNRESOLVED. Every one of these must be frozen by a separate decision before
# R4 may compute anything. This module invents none of them.
R4_UNRESOLVED_SEMANTICS: tuple[str, ...] = (
    "failure_rule",
    "coefficients",
    "clipping",
    "edge_T_le_0",
    "edge_T_ref_le_0",
    "edge_failures_timeouts",
    "edge_missing_execution_time",
    "term_structure_vs_time_only",
)


class TRefMissing(RuntimeError):
    """No T_ref for this workload instance (COMP-RL-08: hard error)."""


class IncompleteFormulaError(RuntimeError):
    """A REGISTERED-but-incomplete reward variant was asked to execute.

    DEC-030 left this variant's semantics unresolved, so no computation may
    occur and no default (R3 behaviour, clipping, failure transformation) may
    be silently substituted. Raised BEFORE any Spark execution.
    """


@dataclass(frozen=True)
class Reward:
    """One realized reward value with full term provenance (value object)."""

    value: float
    formula_id: str = FORMULA_ID
    t_ref_s: float | None = None
    failed: bool = False
    terms: dict[str, float | None] = field(default_factory=dict)
    missing: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "formula_id": self.formula_id,
            "value": self.value,
            "t_ref_s": self.t_ref_s,
            "failed": self.failed,
            "terms": dict(self.terms),
            "missing": list(self.missing),
        }


def load_reward_config(path: str | Path = DEFAULT_REWARD_YAML) -> dict[str, float]:
    """Load and FROZEN-validate the reward weights.

    Raises on any disagreement with PLAN section 15 - the weights are research
    constants, not tuning parameters.
    """
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    weights: dict[str, float] = {}
    for key, frozen in FROZEN_WEIGHTS.items():
        value = raw.get(key)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"reward config key {key!r} missing/invalid: {value!r}")
        if not math.isclose(float(value), frozen, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(
                f"reward config {key}={value} disagrees with the frozen "
                f"PLAN-section-15 value {frozen}")
        weights[key] = float(value)
    if raw.get("formula") != FORMULA_ID:
        raise ValueError(
            f"reward config formula={raw.get('formula')!r} != {FORMULA_ID!r}")
    return weights


class RewardCalculator:
    """Computes one registered reward variant from stored metrics. Stateless.

    ``formula`` defaults to the frozen primary ``R3``, so every existing
    caller (environment, training loop, EXP-002 Q0 builder, validators) is
    behaviourally unchanged. ``A3-time-only`` (DEC-030) selects the frozen
    multi-term-removal variant. ``A3-R4-log-ratio`` is registered but
    incomplete and is refused at construction.
    """

    def __init__(self, config_path: str | Path = DEFAULT_REWARD_YAML, *,
                 formula: str = FORMULA_ID) -> None:
        if formula not in REGISTERED_FORMULAS:
            raise ValueError(
                f"unknown reward formula {formula!r}; DEC-030 registers "
                f"{list(REGISTERED_FORMULAS)} and no other variant")
        if formula == FORMULA_A3_R4_LOG_RATIO:
            # Fail closed BEFORE any computation or Spark execution. R4 stays
            # non-executable until a separate decision freezes every one of
            # these semantics; nothing is defaulted, substituted or clipped.
            raise IncompleteFormulaError(
                "reward variant "
                f"{FORMULA_A3_R4_LOG_RATIO!r} (-ln(T / T_ref)) is REGISTERED "
                "but NOT executable: DEC-030 leaves its complete specification "
                "unresolved ("
                + ", ".join(R4_UNRESOLVED_SEMANTICS)
                + "). A separate decision must freeze every one of them "
                  "before any computation; R3 behaviour is never substituted "
                  "and no clipping is applied silently.")
        self.formula_id = formula
        if formula == FORMULA_A3_TIME_ONLY:
            self.weights = dict(TIME_ONLY_WEIGHTS)
        else:
            self.weights = load_reward_config(config_path)

    def compute(self, metrics: Mapping[str, Any], t_ref: float | None,
                input_bytes: int | None, *, failed: bool) -> Reward:
        """Apply the selected frozen formula.

        ``metrics`` is a RunMetrics-style mapping (``RunMetrics.to_dict()`` or
        equivalent). ``failed`` covers workload failure AND timeout.
        """
        if self.formula_id == FORMULA_A3_TIME_ONLY:
            return self._compute_time_only(metrics, t_ref, failed=failed)
        w = self.weights
        if failed:
            return Reward(value=-1.0 * w["w_failure"], t_ref_s=t_ref, failed=True,
                          terms={"failure": -w["w_failure"]})
        if t_ref is None or not isinstance(t_ref, (int, float)) or t_ref <= 0:
            raise TRefMissing(
                "T_ref missing or non-positive; reward cannot be normalized "
                "(COMP-RL-08 hard error)")
        t_ref_f = float(t_ref)
        t_exec = metrics.get("execution_time_s")
        if t_exec is None:
            # A usable run must carry the authoritative timing; if it is
            # absent the observation is unusable, not zero.
            raise TRefMissing("execution_time_s missing on a run marked usable")
        t_exec_f = float(t_exec)

        missing: list[str] = []
        terms: dict[str, float | None] = {}

        # 1. primary time term (clipped)
        delta = (t_ref_f - t_exec_f) / t_ref_f
        delta_clipped = max(w["clip_low"], min(w["clip_high"], delta))
        terms["time_delta"] = delta
        terms["time_term"] = w["w_time_improvement"] * delta_clipped

        # 2. task-imbalance term (None -> contributes 0, recorded as missing)
        cv = metrics.get("task_duration_cv")
        if cv is None:
            terms["task_term"] = 0.0
            missing.append("task_duration_cv")
        else:
            ratio = min(1.0, float(cv) / w["task_cv_reference"])
            terms["task_term"] = w["w_task_imbalance"] * (1.0 - ratio)

        # 3. spill-waste term (None -> contributes 0, recorded as missing)
        spill = metrics.get("disk_spill_bytes")
        if spill is None or input_bytes is None:
            terms["spill_term"] = 0.0
            if spill is None:
                missing.append("disk_spill_bytes")
            if input_bytes is None:
                missing.append("input_bytes")
        else:
            spill_ratio = float(spill) / float(input_bytes)
            terms["spill_ratio"] = spill_ratio
            terms["spill_term"] = -w["w_spill_waste"] * min(
                1.0, spill_ratio / w["spill_ratio_reference"])

        value = (terms["time_term"] + terms["task_term"]     # type: ignore[operator]
                 + terms["spill_term"])                       # type: ignore[operator]
        value_f = float(value)
        if not math.isfinite(value_f):
            raise ValueError(f"reward is not finite: {terms}")
        return Reward(value=value_f, t_ref_s=t_ref_f, failed=False,
                      terms=terms, missing=tuple(missing))

    # -- A3-time-only (DEC-030 section 3.2) ---------------------------------
    def _compute_time_only(self, metrics: Mapping[str, Any],
                           t_ref: float | None, *, failed: bool) -> Reward:
        """``R = 1.0 * clip((T_ref - T) / T_ref, -1, +1)``; failure ``-1.0``.

        MULTI-TERM REMOVAL: the task-imbalance term AND the spill-waste term
        are removed from R3 SIMULTANEOUSLY, so this is explicitly NOT a
        one-factor ablation (DEC-030 section 3.2 classification).

        Consequently ``task_duration_cv`` and ``disk_spill_bytes`` are removed
        INPUTS, not missing facts: they are never read and therefore never
        appear in ``Reward.missing``. Everything else is inherited verbatim
        from frozen R3: the failure rule (including timeout -> failure), the
        [-1, +1] clipping, the T_ref positive-check and the "a usable run must
        carry its timing" rule.
        """
        w = self.weights
        if failed:
            return Reward(value=-1.0 * w["w_failure"],
                          formula_id=FORMULA_A3_TIME_ONLY, t_ref_s=t_ref,
                          failed=True, terms={"failure": -w["w_failure"]})
        if t_ref is None or not isinstance(t_ref, (int, float)) or t_ref <= 0:
            raise TRefMissing(
                "T_ref missing or non-positive; reward cannot be normalized "
                "(COMP-RL-08 hard error)")
        t_ref_f = float(t_ref)
        t_exec = metrics.get("execution_time_s")
        if t_exec is None:
            # Same rule as R3: a usable run must carry the authoritative
            # timing; absent timing is unusable, never zero.
            raise TRefMissing("execution_time_s missing on a run marked usable")
        t_exec_f = float(t_exec)

        delta = (t_ref_f - t_exec_f) / t_ref_f
        delta_clipped = max(w["clip_low"], min(w["clip_high"], delta))
        terms: dict[str, float | None] = {
            "time_delta": delta,
            "time_term": w["w_time_improvement"] * delta_clipped,
        }
        value_f = float(terms["time_term"])          # type: ignore[arg-type]
        if not math.isfinite(value_f):
            raise ValueError(f"reward is not finite: {terms}")
        return Reward(value=value_f, formula_id=FORMULA_A3_TIME_ONLY,
                      t_ref_s=t_ref_f, failed=False, terms=terms)
