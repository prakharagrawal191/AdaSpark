"""EXP-005 strategy resolution (DEC-016 Decision F, Day 32).

The `BaselineStrategy` contract of ARCHITECTURE_FREEZE line 66 -
``select(state) + id + describe`` - realized for the strategies whose
specifications are settled. Every strategy resolves a cell identity to ONE
frozen `SparkConfig` BEFORE execution, which is the pre-execution selection
problem PLAN section 7 defines; none of them measures anything, and none
touches Spark.

Settled and implemented here:
    B0        Spark default, out-of-box pinned              configs/baseline_b0.yaml
    B0'       Spark factory default with AQE ENABLED        configs/baseline_b0_prime.yaml
    B1        one global validation-selected configuration  baseline_selection.json
    B2        per-family validation-selected configuration  baseline_selection.json

Deliberately NOT implemented, because their specifications are open:
    B3        DEC-016 Decision B is OPEN - `k`, the clamp target, the
              parallelism rule and the core-count definition are all UNDEFINED
              in PLAN. Implementing it would invent a research constant after
              the RL results already exist.
    B4        DEC-016 Decision C is OPEN - the budget referent, the selection
              rule and the freeze point are UNDEFINED, and DEC-015 made "same
              budget as RL" ambiguous across arms of 84, 49 and 42 episodes.
Both raise `StrategyUnspecified` naming the decision that would settle them.

The RL arms are NOT resolved here: they select per state from a frozen Q-table
through `sparkrl.agent.policy_store`, published under DEC-015 to
``models/policies/``. This module owns configuration-selecting baselines only.

EXECUTION IS SEPARATELY GATED. B0' is specified but the frozen runner refuses
AQE-on (`runner.py` raises "AQE became enabled after config application"), so
resolving a B0' configuration here does NOT authorize running it. See DEC-016
(signed) and DEC-014 (pending).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sparkrl.experiments.grid import build_grid
from sparkrl.spark.config import SparkConfig

PROJECT = Path(__file__).resolve().parents[3]
B0_CONFIG = PROJECT / "configs" / "baseline_b0.yaml"
B0_PRIME_CONFIG = PROJECT / "configs" / "baseline_b0_prime.yaml"
SELECTION_ARTIFACT = PROJECT / "results" / "evaluation" / "baseline_selection.json"

STRATEGY_VERSION = "exp005-strategies/v1"

#: Strategies this module resolves. B3/B4 are absent by decision, not oversight.
IMPLEMENTED: tuple[str, ...] = ("B0", "B0'", "B1", "B2")

#: Open specification decisions, keyed by the strategy they block.
OPEN_SPECIFICATIONS: dict[str, str] = {
    "B3": ("DEC-016 Decision B is OPEN: PLAN:155 gives "
           "'partitions = clamp(input_GB x k, 16, 128); core-count rule for "
           "parallelism' but never defines k, its provenance or scope, the "
           "input_GB measurement, the clamp target, or the core-count rule. "
           "Choosing any of them now would be a research constant invented "
           "after the RL results exist."),
    "B4": ("DEC-016 Decision C is OPEN: PLAN:156 gives 'uniform over the same "
           "12 actions, same budget as RL' but never defines the budget "
           "referent, the selection rule, or the freeze point. DEC-015 made "
           "'same budget as RL' ambiguous - the arms are 84, 49 and 42 "
           "episodes."),
}


class StrategyUnspecified(RuntimeError):
    """The strategy's specification is not settled; nothing was invented."""


class StrategyResolutionError(ValueError):
    """A settled strategy could not be resolved from its frozen artifacts."""


@dataclass(frozen=True)
class ResolvedStrategy:
    """One strategy's pre-execution configuration choice, with provenance."""

    strategy_id: str
    config: SparkConfig
    config_name: str
    describe: str
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def config_fingerprint(self) -> str:
        return self.config.fingerprint()


def _grid_point(config_name: str):
    for point in build_grid(include_b0=False):
        if point.name == config_name:
            return point
    raise StrategyResolutionError(
        f"configuration {config_name!r} is not in the frozen 12-action grid")


def _selection(artifact_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(artifact_path) if artifact_path is not None else SELECTION_ARTIFACT
    if not path.exists():
        raise StrategyResolutionError(
            f"{path} not found; B1/B2 are frozen by the Day-31 validation "
            f"selection and cannot be resolved without it")
    art = json.loads(path.read_text(encoding="utf-8"))
    if art.get("contains_test_data"):
        raise StrategyResolutionError(
            "selection artifact reports contains_test_data=true; refusing to "
            "resolve a baseline from an artifact touched by TEST")
    return art


def resolve(strategy_id: str, *, family: str | None = None,
            base_config: SparkConfig | None = None,
            artifact_path: str | Path | None = None) -> ResolvedStrategy:
    """Resolve one strategy to its frozen pre-execution configuration.

    ``family`` is required only by B2, whose configuration is per-family.
    Raises ``StrategyUnspecified`` for B3/B4 rather than guessing.
    """
    sid = strategy_id.strip()
    if sid in OPEN_SPECIFICATIONS:
        raise StrategyUnspecified(f"{sid}: {OPEN_SPECIFICATIONS[sid]}")

    if sid == "B0":
        cfg = SparkConfig.from_yaml(B0_CONFIG)
        return ResolvedStrategy(
            sid, cfg, "B0",
            "Spark default, out-of-box settings pinned (AQE off, main study)",
            {"source": str(B0_CONFIG.relative_to(PROJECT)).replace("\\", "/"),
             "aqe_enabled": cfg.aqe_enabled, "strategy_version": STRATEGY_VERSION})

    if sid in ("B0'", "B0p", "B0-prime"):
        cfg = SparkConfig.from_yaml(B0_PRIME_CONFIG)
        if not cfg.aqe_enabled:
            raise StrategyResolutionError(
                "B0' must carry aqe_enabled=true (PLAN:152, DEC-016 Decision A)")
        return ResolvedStrategy(
            "B0'", cfg, "B0-prime",
            "Spark factory default with AQE ENABLED (modern default, RQ6)",
            {"source": str(B0_PRIME_CONFIG.relative_to(PROJECT)).replace("\\", "/"),
             "aqe_enabled": cfg.aqe_enabled,
             "decision": "DEC-016 Decision A",
             "execution_gate": (
                 "NOT AUTHORIZED: sparkrl.experiments.runner.execute_run refuses "
                 "aqe_enabled=true (PLAN section 7). Resolving this configuration "
                 "does not authorize running it; see DEC-016 and DEC-014."),
             "strategy_version": STRATEGY_VERSION})

    art = _selection(artifact_path)
    base = base_config if base_config is not None else SparkConfig.from_yaml(B0_CONFIG)

    if sid == "B1":
        name = art["B1"]["selected_config"]
        cfg, _point, _fp = _apply(name, base)
        return ResolvedStrategy(
            sid, cfg, name,
            "one globally-selected static configuration, used everywhere",
            {"selected_from": "validation split only",
             "selection_artifact_id": art.get("artifact_id"),
             "metric": art.get("metric"), "statistic": art.get("statistic"),
             "strategy_version": STRATEGY_VERSION})

    if sid == "B2":
        if family is None:
            raise StrategyResolutionError(
                "B2 is per-family (PLAN:154); a family is required")
        by_family = art["B2"]["selected_config_by_family"]
        if family not in by_family:
            raise StrategyResolutionError(
                f"B2 has no frozen configuration for family {family!r}; "
                f"available: {sorted(by_family)}")
        name = by_family[family]
        cfg, _point, _fp = _apply(name, base)
        return ResolvedStrategy(
            sid, cfg, name,
            f"per-family static configuration selected on validation ({family})",
            {"family": family, "selected_from": "validation split only",
             "selection_artifact_id": art.get("artifact_id"),
             "metric": art.get("metric"), "statistic": art.get("statistic"),
             "strategy_version": STRATEGY_VERSION})

    raise StrategyResolutionError(
        f"unknown strategy {strategy_id!r}; implemented: {list(IMPLEMENTED)}; "
        f"open by decision: {sorted(OPEN_SPECIFICATIONS)}; RL arms resolve "
        f"through sparkrl.agent.policy_store, not here")


def _apply(config_name: str, base: SparkConfig):
    """Apply a frozen grid point to the base configuration."""
    point = _grid_point(config_name)
    cfg = point.apply_to(base)
    return cfg, point, cfg.fingerprint()


def describe_all() -> dict[str, str]:
    """Strategy inventory, including what is deliberately unresolved."""
    out = {s: "implemented" for s in IMPLEMENTED}
    out.update({s: "OPEN - " + r.split(":")[0] for s, r in OPEN_SPECIFICATIONS.items()})
    out["RL-s0/RL-s1/RL-s2"] = "frozen policies (DEC-015), resolved by policy_store"
    return out
