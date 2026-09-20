"""EXP-008 A3/A4 frozen-scope layer (DEC-030 methodology; DEC-031 budget).

NON-EXECUTING BY CONSTRUCTION. This module encodes the DEC-030 A3/A4
methodology as data plus pure validators. It NEVER launches Spark, never
trains, never executes TEST, and never authorizes anything: EXP-008 execution
authorization is an EXTERNAL governance decision (DEC-030 section 15 gate
chain; DEC-031 records ``EXP-008 execution authorization = NO``). No code path
here can grant it.

WHAT DEC-030 FROZE (implemented or represented below)
-----------------------------------------------------
* ``A3-R3-frozen``   - the frozen primary R3 reward, unchanged
                       (``sparkrl.rl.reward.RewardCalculator()`` default).
* ``A3-time-only``   - ``R = 1.0 * clip((T_ref - T) / T_ref, -1, +1)``,
                       failure ``R = -1.0``. A MULTI-TERM REMOVAL from R3
                       (task-imbalance AND spill-waste removed
                       simultaneously): explicitly NOT a one-factor ablation.
* ``A3-R4-log-ratio``- ``R4 = -ln(T / T_ref)`` is REGISTERED but INCOMPLETE.
                       Its failure/domain/clipping/edge semantics are
                       unresolved, so it is refused BEFORE any computation or
                       Spark execution (``IncompleteFormulaError``). The enum
                       existing does not make R4 executable.
* ``A4-mode4``       - action subset ``{0, 3, 6, 9}`` of the frozen 12-action
                       grid, reused verbatim from the existing Plan-B
                       definition: original action indices preserved, never
                       renumbered, no projection, selection restriction only.

WHAT DEC-030 DID NOT FREEZE (section 12)
----------------------------------------
Q0 source, state schema, the A3 action schema, the A4 control-pairing reward,
seeds, TRAIN cells, episode horizon, early-stop rule, AQE confirmation,
warm-up behaviour, cache behaviour, alpha/gamma/epsilon deviations and the
live-execution charging rule are all UNRESOLVED. This module therefore
represents every such field as ``None``, records it in every provenance
payload as unseen, and FAILS CLOSED (``Exp008IncompleteError``) whenever an
arm is asked to become configuration-complete. It never chooses a hidden
default that would change the frozen research design.

Q0 POLICY (DEC-030 section 5)
-----------------------------
No projection, no pooling, no row collapsing, no invented state or action
mapping, no new learned Q0, no TEST-derived Q0, and no change to the primary
EXP-002 Q0. A4 may use the existing 12-wide frozen Q0 with ``{0, 3, 6, 9}``
applied as a SELECTION restriction (DEC-030: "EXISTING FROZEN MAPPING"); the
Q0 SOURCE per arm still requires an explicit decision. A3-R4 admits no Q0 at
all, because none was ever computed under R4 and constructing one now would
be post-hoc construction.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from sparkrl.agent.q0 import Q0_NEUTRAL_VERSION, Q0_VERSION
from sparkrl.experiments.spec import TRAIN, split_of
from sparkrl.rl.action import (MODE4, MODE12, MODE4_SUBSET, ActionMapper,
                               InvalidAction)
from sparkrl.rl.reward import (FORMULA_A3_R4_LOG_RATIO, FORMULA_A3_TIME_ONLY,
                               FORMULA_ID, IMPLEMENTED_FORMULAS,
                               REGISTERED_FORMULAS, R4_UNRESOLVED_SEMANTICS,
                               IncompleteFormulaError, RewardCalculator)

PROJECT = Path(__file__).resolve().parents[3]
DEFAULT_EXP008_YAML = PROJECT / "configs" / "exp008.yaml"

EXP008_ID = "EXP-008"
CONFIG_SCHEMA = "exp008-config/v1"

# --- AUTHORIZATION / EXECUTION DECLARATIONS (never mutated by this module) ----
# DEC-031: "EXP-008 execution authorization = NO". Authorization is an
# external governance decision, so this implementation can only record that
# fact - it offers no automatic or self-granting path.
EXECUTION_AUTHORIZATION = "NO"
EXECUTION_AUTHORIZED = False
SPARK_EXECUTIONS = 0
TRAINING_EXECUTIONS = 0
TEST_EXECUTIONS = 0
A5_ARM_ID = "A5"
A5_STATUS = ("DISABLED (DEC-011; re-affirmed DEC-016 s7, DEC-023 s2, "
             "DEC-024 A5 row, DEC-025 s7, DEC-030 s9)")
FROZEN_GAMMA_BANDIT = 0.0

# --- arms (DEC-030 sections 3.1 and 4) ---------------------------------------
ARM_A3_R3 = "A3-R3-frozen"
ARM_A3_TIME_ONLY = "A3-time-only"
ARM_A3_R4_LOG_RATIO = "A3-R4-log-ratio"
ARM_A4_MODE4 = "A4-mode4"
A3_ARMS: tuple[str, ...] = (ARM_A3_R3, ARM_A3_TIME_ONLY, ARM_A3_R4_LOG_RATIO)
A4_ARMS: tuple[str, ...] = (ARM_A4_MODE4,)
ALL_ARMS: tuple[str, ...] = A3_ARMS + A4_ARMS

# A3 reward variant per arm: FIXED by the arm identity (DEC-030 section 3).
# A4's reward variant is the control-pairing field and is deliberately NOT
# set here (DEC-030 section 12 field 5 - UNFROZEN).
ARM_REWARD_FORMULA: dict[str, str] = {
    ARM_A3_R3: FORMULA_ID,
    ARM_A3_TIME_ONLY: FORMULA_A3_TIME_ONLY,
    ARM_A3_R4_LOG_RATIO: FORMULA_A3_R4_LOG_RATIO,
}

# --- A4 action space (DEC-030 section 4) -------------------------------------
# REUSED from the frozen Plan-B definition in sparkrl.rl.action. Never
# redefined here, never renumbered, never re-derived.
A4_ACTION_MODE = MODE4
A4_ACTION_SUBSET = MODE4_SUBSET                       # frozenset({0, 3, 6, 9})
NON_A4_ACTIONS: tuple[int, ...] = tuple(a for a in range(12)
                                        if a not in MODE4_SUBSET)

# Frozen dataset seed (DEC-030: "0 (frozen: T_ref calibrated for dataset seed
# 0 only)"). This is a measured fact, not a tuning choice, and is therefore
# the only seed-valued field this module fills in.
FROZEN_DATASET_SEED = 0

Q0_PROJECTION_FORBIDDEN = True
Q0_ROWS_WIDE = 12                # frozen action-grid width; unchanged by A4

# --- errors ------------------------------------------------------------------
class Exp008Error(RuntimeError):
    """Base class for every EXP-008 configuration/scope refusal."""


class Exp008ConfigError(Exp008Error, ValueError):
    """The EXP-008 configuration artifact is malformed or inconsistent."""


class Exp008IncompleteError(Exp008Error):
    """A required-but-unset DEC-030 field was not supplied: fail closed."""


class Exp008ScopeError(Exp008Error):
    """Out-of-scope request (TEST/VALIDATION, unknown arm, A5, ...)."""


class Exp008Q0Error(Exp008Error):
    """Unsupported Q0 provenance, or a forbidden Q0 projection."""


class A5DisabledError(Exp008ScopeError):
    """A5 (multi-step RL, gamma=0.9) is DISABLED and must stay blocked."""


# --- required-but-unset fields (DEC-030 section 12) --------------------------
# Attribute names of ``Exp008ArmConfig`` that MUST be explicitly supplied by a
# later decision before the arm is configuration-complete. The A4 control
# pairing adds its reward variant.
A3_REQUIRED_FIELDS: tuple[str, ...] = (
    "action_mode",
    "state_schema",
    "q0_source",
    "agent_seeds",
    "train_cells",
    "episode_horizon",
    "early_stop_rule",
    "aqe_condition",
    "warm_up_behavior",
    "cache_behavior",
    "alpha",
    "gamma",
    "epsilon_schedule",
    "live_execution_charging_rule",
    "t_ref_source",
)
A4_REQUIRED_FIELDS: tuple[str, ...] = A3_REQUIRED_FIELDS + ("reward_variant",)


def required_fields(arm: str) -> tuple[str, ...]:
    """The required-but-unset field names for one frozen arm."""
    guard_arm(arm)
    return A4_REQUIRED_FIELDS if arm == ARM_A4_MODE4 else A3_REQUIRED_FIELDS


# --- scope guards ------------------------------------------------------------
def guard_arm(arm: str) -> None:
    """Accept exactly the DEC-030 arms; A5 is refused with its own error."""
    guard_a5(arm=arm)
    if arm not in ALL_ARMS:
        raise Exp008ScopeError(
            f"unknown EXP-008 arm {arm!r}; DEC-030 freezes exactly "
            f"{list(ALL_ARMS)} (A3/A4 only - A5 is out of scope)")


def guard_a5(*, arm: str | None = None, gamma: float | None = None,
             multi_step: bool = False) -> None:
    """A5 stays blocked: no A5 arm, no multi-step mode, no gamma != 0.0.

    DEC-030 section 9 / DEC-011: multi-step RL (gamma = 0.9) is FORBIDDEN.
    """
    if arm == A5_ARM_ID:
        raise A5DisabledError(
            f"arm {A5_ARM_ID!r} is DISABLED ({A5_STATUS}); DEC-030 section 9 "
            "forbids opening multi-step RL or implementing/executing A5")
    if multi_step:
        raise A5DisabledError(
            f"multi-step RL is FORBIDDEN ({A5_STATUS}); the frozen bandit "
            f"lock is gamma={FROZEN_GAMMA_BANDIT}")
    if gamma is not None and float(gamma) != FROZEN_GAMMA_BANDIT:
        raise A5DisabledError(
            f"gamma={gamma!r} is FORBIDDEN: A5 / multi-step RL is DISABLED "
            f"({A5_STATUS}); only the frozen bandit value "
            f"gamma={FROZEN_GAMMA_BANDIT} is admissible")


def guard_split(split: str) -> None:
    """EXP-008 A3/A4 is TRAIN-only: TEST and VALIDATION never enter."""
    if split != TRAIN:
        raise Exp008ScopeError(
            f"EXP-008 A3/A4 is TRAIN-only: split={split!r} refused. TEST "
            "(F4_ski / large / seed 4) and VALIDATION (seed 3) cells and "
            "metrics may never enter an A3/A4 configuration (PLAN section 18; "
            "DEC-030 section 6)")


def guard_cell(family: str, scale: str, seed: int = FROZEN_DATASET_SEED) -> None:
    """One (family, scale, seed) cell must resolve to the TRAIN split.

    A cell outside the frozen family/scale/seed domain is a configuration
    error, not a split decision: it is re-raised inside the EXP-008 error
    taxonomy so every refusal on this path is catchable as ``Exp008Error``.
    """
    try:
        split = split_of(family, scale, seed)
    except ValueError as exc:
        raise Exp008ConfigError(
            f"cell ({family!r}, {scale!r}, seed {seed}) is outside the frozen "
            f"experiment domain: {exc}") from exc
    guard_split(split)


def guard_train_cells(cells: Sequence[str]) -> None:
    """Every declared TRAIN cell must be a real TRAIN cell at dataset seed 0."""
    if (isinstance(cells, (str, bytes)) or not isinstance(cells, Sequence)
            or not cells):
        raise Exp008ConfigError("train_cells must be a non-empty list")
    for cell in cells:
        family, sep, scale = str(cell).partition("|")
        if not sep or not family or not scale:
            raise Exp008ConfigError(
                f"train_cells entry {cell!r} is not 'family|scale'")
        guard_cell(family, scale, FROZEN_DATASET_SEED)


def guard_metrics(metrics: Mapping[str, Any]) -> None:
    """Refuse any metrics mapping that carries TEST/VALIDATION provenance."""
    if not isinstance(metrics, Mapping):
        raise Exp008ConfigError("metrics must be a mapping")
    tag = metrics.get("split")
    if tag is not None:
        guard_split(str(tag))
    for key in ("test_family", "test_scale", "test_seed"):
        if metrics.get(key) is not None:
            raise Exp008ScopeError(
                f"metrics carry {key!r}: TEST information may never enter an "
                "EXP-008 A3/A4 path (DEC-030 section 6)")


def guard_agent_seeds(seeds: Sequence[int] | None) -> None:
    """Structural validation only - DEC-030 leaves the seed SET unfrozen.

    No seed identity or count is invented or defaulted here: the frozen
    PLAN-section-16 set {0, 1, 2} is NOT silently imposed on A3/A4.
    """
    if seeds is None:
        raise Exp008IncompleteError(
            "agent_seeds is required-but-unset (DEC-030 section 12 field 6: "
            "seed count and identities are UNFROZEN)")
    if isinstance(seeds, (str, bytes)) or not isinstance(seeds, Sequence):
        raise Exp008ConfigError(f"agent_seeds must be a sequence, got {seeds!r}")
    if not seeds:
        raise Exp008ConfigError("agent_seeds must not be empty")
    seen: list[int] = []
    for seed in seeds:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise Exp008ConfigError(f"agent seed {seed!r} is not an int")
        if seed in seen:
            raise Exp008ConfigError(f"duplicate agent seed {seed!r}")
        seen.append(seed)


# --- reward-variant guards (DEC-030 section 3) -------------------------------
def build_reward_calculator(formula: str) -> RewardCalculator:
    """Build the calculator for one REGISTERED variant; refuse R4.

    R4 is registered but incomplete, so it can never reach computation - the
    refusal happens here, before any Spark execution.
    """
    if formula not in REGISTERED_FORMULAS:
        raise Exp008ScopeError(
            f"unsupported reward variant {formula!r}; DEC-030 registers "
            f"{list(REGISTERED_FORMULAS)} and introduces none")
    if formula not in IMPLEMENTED_FORMULAS:
        raise IncompleteFormulaError(
            f"reward variant {formula!r} is REGISTERED but NOT executable: "
            "DEC-030 leaves its complete specification unresolved ("
            + ", ".join(R4_UNRESOLVED_SEMANTICS)
            + "). A separate decision must freeze every one of them first; "
              "R3 behaviour is never substituted")
    return RewardCalculator(formula=formula)


def guard_reward_variant(variant: str | None, *, arm: str) -> None:
    """Validate a declared reward variant against the DEC-030 registry."""
    guard_arm(arm)
    if variant is None:
        raise Exp008IncompleteError(
            f"{arm}: reward_variant is required-but-unset (DEC-030 section 12 "
            "field 5: the A4 control-pairing reward is UNFROZEN)")
    build_reward_calculator(variant)          # raises for R4 / unknown


# --- A4 action-space support (DEC-030 section 4) -----------------------------
def guard_action(action: int, *, mode: str = A4_ACTION_MODE) -> int:
    """Validate one action index against the frozen grid/mode (pre-Spark)."""
    return int(ActionMapper(mode=mode).describe(action).grid_index)  # type: ignore[arg-type]


def a4_action_configurations() -> tuple[dict[str, Any], ...]:
    """The four frozen mode4 configurations, derived from the frozen grid.

    Derived from ``ActionMapper`` (never duplicated): each entry keeps the
    ORIGINAL action index and the original config identity, so nothing is
    renumbered and logs/manifests can name the same action as mode12.
    """
    mapper = ActionMapper(mode=A4_ACTION_MODE)
    out: list[dict[str, Any]] = []
    for action in sorted(A4_ACTION_SUBSET):
        point = mapper.describe(action)
        out.append({
            "action_index": int(action),
            "grid_index": int(point.grid_index),   # type: ignore[arg-type]
            "name": point.name,
            "parallelism": int(point.parallelism),
            "shuffle_partitions": int(point.shuffle_partitions),
            "is_reference": bool(point.is_reference),
        })
    return tuple(out)


def guard_action_mode_for_arm(arm: str, mode: str | None) -> None:
    """A4 is FROZEN to mode4; the A3 action schema is UNFROZEN."""
    guard_arm(arm)
    if mode is None:
        raise Exp008IncompleteError(
            f"{arm}: action_mode is required-but-unset (DEC-030 section 12 "
            "field 4: the A3 action schema is UNFROZEN)")
    if mode not in (MODE12, MODE4):
        raise Exp008ScopeError(
            f"unsupported action mode {mode!r}; only {MODE12!r} / {MODE4!r} "
            "exist in the frozen action domain")
    if arm == ARM_A4_MODE4 and mode != MODE4:
        raise Exp008ScopeError(
            f"{arm} is FROZEN to {MODE4!r} (DEC-030 section 4); {mode!r} is "
            "refused - the A4 arm IS the action-availability change")



# --- Q0 policy (DEC-030 section 5) -------------------------------------------
def q0_policy(arm: str) -> dict[str, Any]:
    """The Q0 policy record for one arm (provenance; no invention)."""
    guard_arm(arm)
    if arm == ARM_A3_R4_LOG_RATIO:
        allowed: tuple[str, ...] = ()
        status = ("NO Q0 ADMISSIBLE - no Q0 was ever computed under R4; "
                  "constructing one now would be post-hoc construction")
    else:
        allowed = (Q0_VERSION, Q0_NEUTRAL_VERSION)
        status = ("SOURCE REQUIRES EXPLICIT DECISION (DEC-030 section 5); "
                  "existing frozen sources only")
    return {
        "arm": arm,
        "allowed_sources": list(allowed),
        "required_explicit": True,
        "projection": False,
        "rows_wide": Q0_ROWS_WIDE,
        "action_indices": (sorted(A4_ACTION_SUBSET) if arm == ARM_A4_MODE4
                           else list(range(12))),
        "status": status,
    }


def guard_q0_projection(projection: bool) -> None:
    """No Q0 projection may ever be invented (DEC-030 section 5)."""
    if projection:
        raise Exp008Q0Error(
            "Q0 projection is FORBIDDEN (DEC-030 section 5): no state-to-state "
            "mapping, no row collapsing, no median pooling across keys, no "
            "invented mode4 Q0 mapping and no new learned Q0 may be "
            "constructed for EXP-008")


def guard_q0_source(arm: str, source: str | None) -> None:
    """A declared Q0 source must be admissible for that arm."""
    policy = q0_policy(arm)
    if not policy["allowed_sources"]:
        raise Exp008Q0Error(
            f"{arm}: no Q0 source is admissible ({policy['status']})")
    if source is None:
        raise Exp008IncompleteError(
            f"{arm}: q0_source is required-but-unset (DEC-030 section 12 "
            "field 2: Q0 provenance per arm is UNFROZEN)")
    if source not in policy["allowed_sources"]:
        raise Exp008Q0Error(
            f"{arm}: unsupported q0_source {source!r}; DEC-030 section 5 "
            f"admits only {policy['allowed_sources']} - no new Q0 may be "
            "invented and the primary-study Q0 is never silently changed")


def guard_q0_rows(q_table: Mapping[str, Sequence[float]]) -> None:
    """Q0 rows must stay 12-wide: A4 restricts selection, never the row.

    This is what preserves the existing frozen mapping: indices {0, 3, 6, 9}
    address the SAME 12-wide row used by mode12, so no action is renumbered
    and no value is remapped.
    """
    if not isinstance(q_table, Mapping) or not q_table:
        raise Exp008ConfigError("q_table must be a non-empty mapping")
    for key, row in q_table.items():
        if len(row) != Q0_ROWS_WIDE:
            raise Exp008Q0Error(
                f"Q0 row {key!r} is {len(row)}-wide; EXP-008 requires the "
                f"unchanged {Q0_ROWS_WIDE}-wide frozen action grid (A4 is a "
                "selection restriction only - no projection, no collapsing)")


def guard_q0_for_mode(q_table: Mapping[str, Sequence[float]],
                      mode: str) -> None:
    """Combine the row-width and subset-preservation checks."""
    guard_q0_rows(q_table)
    if mode == MODE4:
        for action in A4_ACTION_SUBSET:
            if action >= Q0_ROWS_WIDE:
                raise Exp008Q0Error(
                    f"mode4 index {action} is outside the frozen "
                    f"{Q0_ROWS_WIDE}-wide Q0 row")


def guard_q0_action_indices(mode: str) -> tuple[int, ...]:
    """The selectable action indices for a mode, taken from ActionMapper.

    A4 SELECTS {0, 3, 6, 9} out of the unchanged 12-wide table; it never
    produces a compacted or renumbered 4-wide table. The consumer (the frozen
    agent) already restricts selection through ``allowed_actions()``.
    """
    return tuple(ActionMapper(mode=mode).allowed_actions())

# --- configuration schema (Phase 5): fail-closed, default-preserving ----------
def _opt_str(value: Any, *, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise Exp008ConfigError(f"{field} must be a non-empty string, got {value!r}")
    return value


def _opt_float(value: Any, *, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise Exp008ConfigError(f"{field} must be a number, got {value!r}")
    return float(value)


def _opt_int(value: Any, *, field: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise Exp008ConfigError(f"{field} must be an int, got {value!r}")
    return int(value)


def _opt_mapping(value: Any, *, field: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise Exp008ConfigError(f"{field} must be a mapping, got {value!r}")
    return {str(k): v for k, v in value.items()}


def _opt_str_tuple(value: Any, *, field: str) -> tuple[str, ...] | None:
    if value is None:
        return None
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise Exp008ConfigError(f"{field} must be a sequence, got {value!r}")
    return tuple(_opt_str(v, field=field) for v in value)   # type: ignore[misc]


def _opt_seeds(value: Any, *, field: str) -> tuple[int, ...] | None:
    if value is None:
        return None
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise Exp008ConfigError(f"{field} must be a sequence, got {value!r}")
    out: list[int] = []
    for v in value:
        if isinstance(v, bool) or not isinstance(v, int):
            raise Exp008ConfigError(f"{field} entry {v!r} is not an int")
        out.append(int(v))
    return tuple(out)
@dataclass(frozen=True)
class Exp008ArmConfig:
    """One EXP-008 arm configuration.

    Fields DEC-030 froze carry their frozen value; fields DEC-030 left
    unresolved default to ``None`` and are REQUIRED-BUT-UNSET: they must be
    supplied explicitly by a later decision before the arm is
    configuration-complete. ``validate_configuration()`` fails closed.
    """

    arm: str
    # -- frozen by DEC-030 ---------------------------------------------------
    dataset_seed: int = FROZEN_DATASET_SEED
    split: str = TRAIN
    q0_projection: bool = False
    action_mode: str | None = None          # A4 frozen to mode4; A3 UNFROZEN
    # -- DEC-030 required-but-unset -----------------------------------------
    reward_variant: str | None = None       # A3: fixed by arm; A4: UNFROZEN
    state_schema: str | None = None
    q0_source: str | None = None
    q0_variant: str | None = None
    agent_seeds: tuple[int, ...] | None = None
    train_cells: tuple[str, ...] | None = None
    t_ref_source: str | None = None
    t_ref_fingerprint: str | None = None
    alpha: float | None = None
    gamma: float | None = None
    epsilon_schedule: Mapping[str, Any] | None = None
    episode_horizon: int | None = None
    early_stop_rule: Mapping[str, Any] | None = None
    execution_budget: Mapping[str, Any] | None = None
    aqe_condition: str | None = None
    warm_up_behavior: str | None = None
    cache_behavior: str | None = None
    live_execution_charging_rule: str | None = None
    statistical_governance: Mapping[str, Any] | None = None
    code_fingerprint: str | None = None

    # -- derived -------------------------------------------------------------
    def effective_reward_variant(self) -> str | None:
        """The arm's reward variant (A3 arms fix it; A4 declares it)."""
        return ARM_REWARD_FORMULA.get(self.arm, self.reward_variant)

    def unresolved_fields(self) -> tuple[str, ...]:
        """Required fields still ``None`` for this arm (deterministic order)."""
        return tuple(f for f in required_fields(self.arm)
                     if getattr(self, f) is None)

    def to_provenance(self) -> dict[str, Any]:
        """The full run-manifest provenance record (no fabricated value).

        Unresolved fields are recorded as ``None`` and additionally listed in
        ``unresolved_fields``. ``execution_authorized`` is a constant False:
        authorization is an external governance decision.
        """
        return {
            "experiment": EXP008_ID,
            "config_schema": CONFIG_SCHEMA,
            "arm": self.arm,
            "reward_variant": self.effective_reward_variant(),
            "action_mode": self.action_mode,
            "action_subset": (sorted(A4_ACTION_SUBSET)
                              if self.action_mode == MODE4 else None),
            "state_schema": self.state_schema,
            "q0_source": self.q0_source,
            "q0_variant": self.q0_variant,
            "q0_projection": bool(self.q0_projection),
            "q0_rows_wide": Q0_ROWS_WIDE,
            "agent_seeds": list(self.agent_seeds) if self.agent_seeds else None,
            "dataset_seed": self.dataset_seed,
            "split": self.split,
            "train_cells": list(self.train_cells) if self.train_cells else None,
            "t_ref_source": self.t_ref_source,
            "t_ref_fingerprint": self.t_ref_fingerprint,
            "alpha": self.alpha,
            "gamma": self.gamma,
            "epsilon_schedule": (dict(self.epsilon_schedule)
                                 if self.epsilon_schedule else None),
            "episode_horizon": self.episode_horizon,
            "early_stop": (dict(self.early_stop_rule)
                           if self.early_stop_rule else None),
            "execution_budget": (dict(self.execution_budget)
                                 if self.execution_budget else None),
            "aqe_condition": self.aqe_condition,
            "warm_up_behavior": self.warm_up_behavior,
            "cache_behavior": self.cache_behavior,
            "live_execution_charging_rule": self.live_execution_charging_rule,
            "statistical_governance": (dict(self.statistical_governance)
                                       if self.statistical_governance else None),
            "implementation_fingerprint": self.code_fingerprint,
            "unresolved_fields": list(self.unresolved_fields()),
            "execution_authorized": EXECUTION_AUTHORIZED,
            "execution_authorization": EXECUTION_AUTHORIZATION,
        }

    # -- validation ----------------------------------------------------------
    def validate_configuration(self) -> None:
        """Fail-closed validation. NO Spark, NO TEST, NO authorization.

        Raises ``Exp008IncompleteError`` while any DEC-030 field is unset,
        ``IncompleteFormulaError`` for R4, ``A5DisabledError`` for A5/gamma,
        ``Exp008ScopeError`` for TEST/VALIDATION or wrong action modes and
        ``Exp008Q0Error`` for unsupported/forbidden Q0 provenance.
        """
        guard_arm(self.arm)
        guard_split(self.split)
        expected_variant = ARM_REWARD_FORMULA.get(self.arm)
        if expected_variant is not None and self.reward_variant not in (
                None, expected_variant):
            raise Exp008ScopeError(
                f"{self.arm}: reward_variant={self.reward_variant!r} "
                f"contradicts the arm identity; DEC-030 section 3 fixes this "
                f"arm's reward to {expected_variant!r}")
        if self.dataset_seed != FROZEN_DATASET_SEED:
            raise Exp008ScopeError(
                f"dataset_seed={self.dataset_seed!r} refused: T_ref is "
                f"calibrated for dataset seed {FROZEN_DATASET_SEED} only "
                "(measured fact, not a tuning choice)")
        guard_q0_projection(self.q0_projection)

        formula = self.effective_reward_variant()
        if formula is not None:
            guard_reward_variant(formula, arm=self.arm)   # R4 raises here

        missing = list(self.unresolved_fields())
        if missing:
            raise Exp008IncompleteError(
                f"{self.arm}: EXP-008 configuration is INCOMPLETE - "
                f"{len(missing)} DEC-030 method field(s) are required-but-unset "
                f"and may not be defaulted: {missing}. A3/A4 must not execute "
                "until every one of them is explicitly supplied by a later "
                "decision (DEC-030 section 12).")

        guard_a5(gamma=self.gamma)
        guard_action_mode_for_arm(self.arm, self.action_mode)
        guard_agent_seeds(self.agent_seeds)
        guard_train_cells(self.train_cells)
        guard_q0_source(self.arm, self.q0_source)
        if self.action_mode == MODE4:
            # A4 selection is exactly the frozen subset, taken from the frozen
            # mapper; the Q0 table itself stays 12-wide (checked by callers via
            # guard_q0_for_mode / guard_q0_rows).
            guard_q0_action_indices(MODE4)

    def arm_runtime_kwargs(self) -> dict[str, Any]:
        """Component-level kwargs for the EXISTING abstractions (no Spark).

        Returns only after ``validate_configuration()`` passes. Nothing is
        planned, built or launched: the caller still needs an EXTERNAL
        governance authorization to execute EXP-008.
        """
        self.validate_configuration()
        formula = self.effective_reward_variant()
        assert formula is not None                      # guaranteed above
        return {
            "action_mode": self.action_mode,
            "state_schema": self.state_schema,
            "reward_formula": formula,
            "reward_calculator": build_reward_calculator(formula),
            "action_subset": guard_q0_action_indices(str(self.action_mode)),
            "q0_source": self.q0_source,
            "q0_variant": self.q0_variant,
            "q0_projection": bool(self.q0_projection),
            "agent_seeds": tuple(self.agent_seeds or ()),
            "dataset_seed": self.dataset_seed,
            "split": self.split,
        }
# --- loading (existing project YAML convention) ------------------------------
_CONFIG_KEYS: frozenset[str] = frozenset(
    f.name for f in dataclasses.fields(Exp008ArmConfig))


def arm_config_from_mapping(arm: str, raw: Mapping[str, Any]) -> Exp008ArmConfig:
    """Build one arm config from a mapping; unknown keys are a hard error."""
    guard_arm(arm)
    if not isinstance(raw, Mapping):
        raise Exp008ConfigError(f"{arm}: arm configuration must be a mapping")
    unknown = sorted(set(str(k) for k in raw) - _CONFIG_KEYS)
    if unknown:
        raise Exp008ConfigError(
            f"{arm}: unknown configuration key(s) {unknown}; the EXP-008 schema "
            f"is closed (allowed: {sorted(_CONFIG_KEYS)})")
    return Exp008ArmConfig(
        arm=arm,
        dataset_seed=int(raw.get("dataset_seed", FROZEN_DATASET_SEED)),
        split=str(raw.get("split", TRAIN)),
        q0_projection=bool(raw.get("q0_projection", False)),
        action_mode=_opt_str(raw.get("action_mode"), field="action_mode"),
        reward_variant=_opt_str(raw.get("reward_variant"),
                                field="reward_variant"),
        state_schema=_opt_str(raw.get("state_schema"), field="state_schema"),
        q0_source=_opt_str(raw.get("q0_source"), field="q0_source"),
        q0_variant=_opt_str(raw.get("q0_variant"), field="q0_variant"),
        agent_seeds=_opt_seeds(raw.get("agent_seeds"), field="agent_seeds"),
        train_cells=_opt_str_tuple(raw.get("train_cells"), field="train_cells"),
        t_ref_source=_opt_str(raw.get("t_ref_source"), field="t_ref_source"),
        t_ref_fingerprint=_opt_str(raw.get("t_ref_fingerprint"),
                                   field="t_ref_fingerprint"),
        alpha=_opt_float(raw.get("alpha"), field="alpha"),
        gamma=_opt_float(raw.get("gamma"), field="gamma"),
        epsilon_schedule=_opt_mapping(raw.get("epsilon_schedule"),
                                      field="epsilon_schedule"),
        episode_horizon=_opt_int(raw.get("episode_horizon"),
                                 field="episode_horizon"),
        early_stop_rule=_opt_mapping(raw.get("early_stop_rule"),
                                     field="early_stop_rule"),
        execution_budget=_opt_mapping(raw.get("execution_budget"),
                                      field="execution_budget"),
        aqe_condition=_opt_str(raw.get("aqe_condition"), field="aqe_condition"),
        warm_up_behavior=_opt_str(raw.get("warm_up_behavior"),
                                  field="warm_up_behavior"),
        cache_behavior=_opt_str(raw.get("cache_behavior"),
                                field="cache_behavior"),
        live_execution_charging_rule=_opt_str(
            raw.get("live_execution_charging_rule"),
            field="live_execution_charging_rule"),
        statistical_governance=_opt_mapping(raw.get("statistical_governance"),
                                           field="statistical_governance"),
        code_fingerprint=_opt_str(raw.get("code_fingerprint"),
                                  field="code_fingerprint"),
    )
def load_exp008_config(path: str | Path = DEFAULT_EXP008_YAML) -> dict[str, Any]:
    """Load and structurally validate the EXP-008 configuration artifact."""
    p = Path(path)
    if not p.exists():
        raise Exp008ConfigError(f"EXP-008 configuration not found: {p}")
    raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise Exp008ConfigError(f"{p}: top level must be a mapping")
    if raw.get("experiment_id") != EXP008_ID:
        raise Exp008ConfigError(
            f"{p}: experiment_id={raw.get('experiment_id')!r} != {EXP008_ID!r}")
    if raw.get("schema_version") != CONFIG_SCHEMA:
        raise Exp008ConfigError(
            f"{p}: schema_version={raw.get('schema_version')!r} != "
            f"{CONFIG_SCHEMA!r}")
    arms = raw.get("arms")
    if not isinstance(arms, dict) or not arms:
        raise Exp008ConfigError(f"{p}: 'arms' must be a non-empty mapping")
    unknown = sorted(set(arms) - set(ALL_ARMS))
    if unknown:
        raise Exp008ConfigError(
            f"{p}: unknown arm(s) {unknown}; DEC-030 freezes {list(ALL_ARMS)}")
    return raw


def arm_config_from_yaml(arm: str,
                         path: str | Path = DEFAULT_EXP008_YAML
                         ) -> Exp008ArmConfig:
    """Load one arm block from the EXP-008 configuration artifact."""
    guard_arm(arm)
    raw = load_exp008_config(path)
    arms = raw["arms"]
    if arm not in arms:
        raise Exp008ConfigError(f"{Path(path)}: no configuration block for {arm}")
    return arm_config_from_mapping(arm, arms[arm])


def all_arm_configs(path: str | Path = DEFAULT_EXP008_YAML
                    ) -> dict[str, Exp008ArmConfig]:
    """All four arm configs, deterministically ordered (read-only)."""
    return {arm: arm_config_from_yaml(arm, path) for arm in ALL_ARMS}


def arm_scope_summary() -> dict[str, Any]:
    """The DEC-030 frozen-vs-unresolved scope as a plain dict (tests/reports)."""
    return {
        "experiment": EXP008_ID,
        "arms": {
            arm: {
                "arm": arm,
                "reward_formula": ARM_REWARD_FORMULA.get(arm),
                "action_mode_frozen": (MODE4 if arm == ARM_A4_MODE4 else None),
                "required_but_unset": list(required_fields(arm)),
                "q0_policy": q0_policy(arm),
                "executable": arm != ARM_A3_R4_LOG_RATIO,
                "incomplete_reason": (
                    None if arm != ARM_A3_R4_LOG_RATIO else
                    "R4 semantics unresolved ("
                    + ", ".join(R4_UNRESOLVED_SEMANTICS) + ")"),
            }
            for arm in ALL_ARMS
        },
        "a4_action_subset": sorted(A4_ACTION_SUBSET),
        "a4_exact_configurations": [dict(c) for c in a4_action_configurations()],
        "a5_status": A5_STATUS,
        "execution_authorized": EXECUTION_AUTHORIZED,
        "spark_executions": SPARK_EXECUTIONS,
        "training_executions": TRAINING_EXECUTIONS,
        "test_executions": TEST_EXECUTIONS,
    }
