"""EXP-005 strategy resolution (DEC-016, Day 32).

The `BaselineStrategy` contract of ARCHITECTURE_FREEZE line 66 -
``select(state) + id + describe`` - for the six configuration-selecting
baselines. Every strategy resolves a cell identity to ONE frozen `SparkConfig`
BEFORE execution, which is the pre-execution selection problem PLAN section 7
defines. Nothing here measures anything and nothing here touches Spark.

    B0    Spark default, out-of-box pinned              configs/baseline_b0.yaml
    B0'   Spark factory default with AQE ENABLED        configs/baseline_b0_prime.yaml
    B1    one global validation-selected configuration  baseline_selection.json
    B2    per-family validation-selected configuration  baseline_selection.json
    B3    rule-based adaptive (DEC-016 Decision B)      computed from manifests
    B4    equal-budget random search (Decision C)       b4_selection.json

The RL arms are NOT resolved here: they select per state from frozen Q-tables
published under DEC-015 to ``models/policies/``. This module owns
configuration-selecting baselines only.

EXECUTION IS SEPARATELY GATED. B0' is fully specified but the frozen runner
refuses AQE-on (``runner.py`` raises "AQE became enabled after config
application"), so resolving a B0' configuration does NOT authorize running it.
See DEC-016 and DEC-014.
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
B4_SELECTION_ARTIFACT = PROJECT / "results" / "evaluation" / "b4_selection.json"

STRATEGY_VERSION = "exp005-strategies/v1"

#: All six baselines are settled by DEC-016 (A-F, 2026-09-14).
IMPLEMENTED: tuple[str, ...] = ("B0", "B0'", "B1", "B2", "B3", "B4")

# --- B3, frozen by DEC-016 Decision B ----------------------------------------
#: partitions = clamp(input_GB * B3_K, 16, 128). k = 1e9 / 134217728 - one
#: partition per 128 MB, Spark's own spark.sql.files.maxPartitionBytes default.
#: The ONLY candidate derivable from outside this project; a larger k would have
#: been a constant chosen after the RL results already existed.
B3_K: float = 1e9 / 134217728                 # 7.450580596923828
B3_MIN_PARTITIONS: int = 16
B3_MAX_PARTITIONS: int = 128
B3_NOTE = (
    "DEC-016 Decision B. At the measured data volumes (0.0386 / 0.1320 / 0.4042 "
    "GB) this rule yields 16 partitions at EVERY scale, so B3 resolves to "
    "parallelism 8 / shuffle 16 = G-p8-sp16, identical to the frozen B1. The "
    "collapse is a recorded finding about the data scale, not a defect to "
    "engineer around, and it means SC3 reduces in practice to RL vs B1.")

# --- B4, frozen by DEC-016 Decision C ----------------------------------------
#: Equal-budget random search on TRAIN: 84 uniform draws over the frozen grid,
#: best by median execution_time_s, frozen before TEST. 84 = RL-s0's training
#: budget, the only arm that completed the full schedule and reached the floor.
B4_BUDGET: int = 84

#: Historical record: B3 and B4 were UNSPECIFIED until DEC-016 settled them.
#: Retained so the original refusal reasons stay auditable.
RESOLVED_SPECIFICATIONS: dict[str, str] = {
    "B3": "was OPEN (k, clamp target, parallelism rule) - settled by DEC-016 Decision B",
    "B4": "was OPEN (budget, selection rule, freeze point) - settled by DEC-016 Decision C",
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


# --- helpers -----------------------------------------------------------------
def _physical_cores() -> int:
    """Physical cores; used only by B3's core-count rule."""
    try:
        import psutil
        n = psutil.cpu_count(logical=False)
        if n:
            return int(n)
    except Exception:                                       # noqa: BLE001
        pass
    import os
    return int(os.cpu_count() or 1)


def input_gb(family: str, scale: str, dataset_seed: int) -> float:
    """B3's input size: manifest ``total_bytes / 1e9`` (DEC-016 Decision B).

    Read pre-execution from the frozen checksummed dataset manifests - the same
    sum the state encoder uses. Never measured at runtime.
    """
    from sparkrl.workloads.resolver import resolve_dataset
    r = resolve_dataset(family, scale, dataset_seed)
    total = (int(r.orders_manifest.get("total_bytes") or 0)
             + int(r.lineitem_manifest.get("total_bytes") or 0))
    return total / 1e9


def b3_partitions(gb: float) -> int:
    """clamp(input_GB * k, 16, 128), snapped to the frozen shuffle levels."""
    clamped = max(B3_MIN_PARTITIONS, min(B3_MAX_PARTITIONS, gb * B3_K))
    return min((16, 32, 64, 128), key=lambda level: (abs(level - clamped), level))


def b3_parallelism() -> int:
    """Core-count rule, clamped to the frozen parallelism levels {2, 4, 8}."""
    cores = _physical_cores()
    eligible = [level for level in (2, 4, 8) if level <= cores]
    return max(eligible) if eligible else 2


def _grid_point(config_name: str):
    for point in build_grid(include_b0=False):
        if point.name == config_name:
            return point
    raise StrategyResolutionError(
        f"configuration {config_name!r} is not in the frozen 12-action grid")


def _apply(config_name: str, base: SparkConfig):
    point = _grid_point(config_name)
    cfg = point.apply_to(base)
    return cfg, point, cfg.fingerprint()


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


# --- resolution ---------------------------------------------------------------
def resolve(strategy_id: str, *, family: str | None = None,
            scale: str | None = None, dataset_seed: int | None = None,
            base_config: SparkConfig | None = None,
            artifact_path: str | Path | None = None) -> ResolvedStrategy:
    """Resolve one strategy to its frozen pre-execution configuration.

    ``family`` is required by B2 and B3; ``scale``/``dataset_seed`` by B3, whose
    rule reads the dataset manifests.
    """
    sid = strategy_id.strip()

    if sid == "B0":
        cfg = SparkConfig.from_yaml(B0_CONFIG)
        return ResolvedStrategy(
            sid, cfg, "B0",
            "Spark default, out-of-box settings pinned (AQE off, main study)",
            {"source": "configs/baseline_b0.yaml", "aqe_enabled": cfg.aqe_enabled,
             "strategy_version": STRATEGY_VERSION})

    if sid in ("B0'", "B0p", "B0-prime"):
        cfg = SparkConfig.from_yaml(B0_PRIME_CONFIG)
        if not cfg.aqe_enabled:
            raise StrategyResolutionError(
                "B0' must carry aqe_enabled=true (PLAN:152, DEC-016 Decision A)")
        return ResolvedStrategy(
            "B0'", cfg, "B0-prime",
            "Spark factory default with AQE ENABLED (modern default, RQ6)",
            {"source": "configs/baseline_b0_prime.yaml",
             "aqe_enabled": cfg.aqe_enabled, "decision": "DEC-016 Decision A",
             "execution_gate": (
                 "NOT AUTHORIZED: sparkrl.experiments.runner.execute_run refuses "
                 "aqe_enabled=true (PLAN section 7). Resolving this configuration "
                 "does not authorize running it; see DEC-016 and DEC-014."),
             "strategy_version": STRATEGY_VERSION})

    base = base_config if base_config is not None else SparkConfig.from_yaml(B0_CONFIG)

    if sid == "B3":
        if family is None or scale is None or dataset_seed is None:
            raise StrategyResolutionError(
                "B3 is input-size dependent (PLAN:155); family, scale and "
                "dataset_seed are required to read the frozen manifests")
        gb = input_gb(family, scale, dataset_seed)
        parts, par = b3_partitions(gb), b3_parallelism()
        name = f"G-p{par}-sp{parts}"
        cfg, _point, _fp = _apply(name, base)
        return ResolvedStrategy(
            sid, cfg, name,
            "rule-based adaptive: clamp(input_GB * k, 16, 128) partitions, "
            "core-count rule for parallelism",
            {"rule": "clamp(input_GB * %.6f, %d, %d)" % (
                B3_K, B3_MIN_PARTITIONS, B3_MAX_PARTITIONS),
             "k": B3_K,
             "k_basis": "1e9 / 134217728 = one partition per 128 MB "
                        "(spark.sql.files.maxPartitionBytes default)",
             "input_gb": gb,
             "input_gb_basis": "manifest total_bytes / 1e9 (compressed Parquet)",
             "partitions": parts, "parallelism": par,
             "physical_cores": _physical_cores(),
             "decision": "DEC-016 Decision B", "note": B3_NOTE,
             "strategy_version": STRATEGY_VERSION})

    if sid == "B4":
        if not B4_SELECTION_ARTIFACT.exists():
            raise StrategyResolutionError(
                f"B4 is frozen by an equal-budget random search on TRAIN "
                f"({B4_BUDGET} draws, DEC-016 Decision C) that has not been run; "
                f"{B4_SELECTION_ARTIFACT.name} does not exist. Nothing is guessed.")
        b4 = json.loads(B4_SELECTION_ARTIFACT.read_text(encoding="utf-8"))
        if b4.get("split") != "train":
            raise StrategyResolutionError(
                "B4 search artifact does not report split='train'; refusing")
        name = b4["selected_config"]
        cfg, _point, _fp = _apply(name, base)
        return ResolvedStrategy(
            sid, cfg, name,
            f"equal-budget random search ({B4_BUDGET} draws on TRAIN), frozen",
            {"budget": B4_BUDGET,
             "budget_basis": "RL-s0 training episodes - the only arm that "
                             "completed the full 84-episode schedule",
             "searched_on": "train", "metric": b4.get("metric"),
             "artifact_id": b4.get("artifact_id"),
             "decision": "DEC-016 Decision C",
             "strategy_version": STRATEGY_VERSION})

    art = _selection(artifact_path)

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
        f"RL arms resolve through sparkrl.agent.policy_store, not here")


def describe_all() -> dict[str, str]:
    """Strategy inventory."""
    out = {s: "implemented" for s in IMPLEMENTED}
    out["B3"] = "implemented (DEC-016 Decision B; collapses onto B1 at this data scale)"
    out["B4"] = "implemented (DEC-016 Decision C; requires the TRAIN search artifact)"
    out["RL-s0/RL-s1/RL-s2"] = "frozen policies (DEC-015), resolved by policy_store"
    return out
