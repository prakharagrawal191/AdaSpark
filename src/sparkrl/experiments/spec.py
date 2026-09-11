"""EXP-002 experiment specification: scope, split guards, run plan, run identity.

Everything in this module is *pre-registered design*: it is fixed before the first
measured observation and is reconstructible from the version-controlled YAML spec
(``experiments/exp002.yaml``) plus the frozen configuration grid (``grid.py``).
Nothing here depends on observed results.

Split authority (PLAN section 18, leakage-guarded)
-------------------------------------------------
    TRAIN      = {F1,F2,F3,F5} x {small,medium} x seeds {0,1,2}
    VALIDATION = {F1,F2,F3,F5} x {small,medium} x seed  {3}
    TEST       = scale large (any family) OR family F4_ski (unseen family)
                 OR seed 4; frozen until Day 31.

EXP-002 runs on TRAIN cells only. PLAN section 33 scopes it to
"12-config grid x F1,F2,F3,F5 x S,M", and ARCHITECTURE_FREEZE states
"Safe-for-init subset: TRAIN-split cells only; validation cells calibrate baselines
(EXP-003); test cells never touched". EXP-002 selects nothing and tunes nothing, so
no validation stage is invented here.

Run order (PLAN does not prescribe one for EXP-002)
---------------------------------------------------
Randomized complete block design. One block = (family, scale, rep); within a block
every configuration appears exactly once, in an order drawn from a seeded RNG whose
seed is recorded in the spec. Blocks run scale-major so an interrupted queue still
yields complete coverage at the smaller scale. Configuration *identity* never
depends on execution order.
"""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from sparkrl.experiments.grid import (ConfigPoint, GRID_VERSION, build_grid,
                                      grid_fingerprint, validate_grid,)
from sparkrl.workloads.base import FAMILIES, SCALES, SEEDS

SPEC_VERSION = "exp002-spec/v1"
EXPERIMENT_ID = "EXP-002"

# PLAN section 18 split constants.
TRAIN_FAMILIES: tuple[str, ...] = ("F1_agg", "F2_join", "F3_rdd", "F5_mixed")
TRAIN_SCALES: tuple[str, ...] = ("small", "medium")
TRAIN_SEEDS: tuple[int, ...] = (0, 1, 2)
VALIDATION_SEEDS: tuple[int, ...] = (3,)
TEST_FAMILY = "F4_ski"          # unseen family, frozen
TEST_SCALE = "large"            # unseen scale, frozen
TEST_SEEDS: tuple[int, ...] = (4,)

TRAIN, VALIDATION, TEST = "train", "validation", "test"


def split_of(family: str, scale: str, seed: int) -> str:
    """Classify one (family, scale, seed) cell into the PLAN-18 split.

    Test membership is checked first and dominates: any cell touching the unseen
    family, the unseen scale, or an unseen seed is TEST regardless of the others.
    """
    if family not in FAMILIES:
        raise ValueError(f"unknown family {family!r}; expected one of {list(FAMILIES)}")
    if scale not in SCALES:
        raise ValueError(f"unknown scale {scale!r}; expected one of {list(SCALES)}")
    if seed not in SEEDS:
        raise ValueError(f"unknown seed {seed!r}; expected one of {list(SEEDS)}")
    if family == TEST_FAMILY or scale == TEST_SCALE or seed in TEST_SEEDS:
        return TEST
    if seed in VALIDATION_SEEDS:
        return VALIDATION
    # TRAIN is granted by MEMBERSHIP, never by failing to match TEST/VALIDATION.
    # Classifying by exclusion would silently admit any future family/scale/seed
    # added to the frozen sets as training data.
    if (family in TRAIN_FAMILIES and scale in TRAIN_SCALES and seed in TRAIN_SEEDS):
        return TRAIN
    return TEST


def assert_train_only(family: str, scale: str, seed: int) -> None:
    """Hard guard: refuse anything that is not a TRAIN cell.

    This is the test-set freeze enforced in code, not only in documentation.
    """
    split = split_of(family, scale, seed)
    if split != TRAIN:
        raise ValueError(
            f"EXP-002 refuses {family}/{scale}/seed{seed}: split={split}. "
            f"EXP-002 runs on TRAIN cells only; the TEST split is frozen until "
            f"Day 31 (PLAN section 18) and VALIDATION belongs to EXP-003.")


def run_id_for(family: str, scale: str, seed: int, config_name: str,
               rep: int) -> str:
    """Deterministic run identity. Same inputs -> same id, on any machine."""
    if rep < 1:
        raise ValueError(f"rep must be >= 1, got {rep}")
    raw = f"exp002-{family}-{scale}-s{seed}-{config_name}-r{rep}"
    return raw.replace("_", "-").lower()


@dataclass(frozen=True)
class RunSpec:
    """One planned measured observation (never a warm-up)."""

    run_id: str
    family: str
    scale: str
    seed: int
    rep: int
    config: ConfigPoint
    split: str
    timeout_seconds: float
    order_index: int
    block_id: str

    def relative_path(self) -> Path:
        """Deterministic on-disk location under the experiment result root."""
        return (Path(self.family) / self.scale / f"seed{self.seed}"
                / self.config.name / f"rep{self.rep}.json")

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "experiment_id": EXPERIMENT_ID,
            "family": self.family,
            "scale": self.scale,
            "seed": self.seed,
            "rep": self.rep,
            "config_name": self.config.name,
            "config_grid_index": self.config.grid_index,
            "config_fingerprint": self.config.fingerprint(),
            "config_is_reference": self.config.is_reference,
            "split": self.split,
            "aqe_enabled": self.config.aqe_enabled,
            "timeout_seconds": self.timeout_seconds,
            "order_index": self.order_index,
            "block_id": self.block_id,
            "relative_path": self.relative_path().as_posix(),
        }


@dataclass(frozen=True)
class ExperimentSpec:
    """Validated, pre-registered EXP-002 design."""

    experiment_id: str
    spec_version: str
    families: tuple[str, ...]
    scales: tuple[str, ...]
    seeds: tuple[int, ...]
    repetitions: int
    warmup_runs: int
    aqe_enabled: bool
    order_seed: int
    timeouts_by_scale: dict[str, float]
    grid: tuple[ConfigPoint, ...]
    base_config_path: str
    result_root: str
    gate: dict[str, Any]
    notes: dict[str, Any] = field(default_factory=dict)

    # -- validation ----------------------------------------------------
    def validate(self) -> None:
        """Structural + scientific-scope invariants. Raises ValueError."""
        if self.experiment_id != EXPERIMENT_ID:
            raise ValueError(
                f"experiment_id must be {EXPERIMENT_ID}, got {self.experiment_id!r}")
        if self.spec_version != SPEC_VERSION:
            raise ValueError(
                f"spec_version must be {SPEC_VERSION}, got {self.spec_version!r}")
        if self.aqe_enabled:
            raise ValueError(
                "EXP-002 requires aqe_enabled=false (PLAN section 7; AQE-on is EXP-005b)")
        if not self.families:
            raise ValueError("no workload families specified")
        if not self.scales:
            raise ValueError("no scales specified (the design would plan zero runs)")
        if not self.seeds:
            raise ValueError("no seeds specified (the design would plan zero runs)")
        if len(self.seeds) != 1:
            # The PLAN-33 budget for EXP-002 is a single TRAIN seed; a multi-seed
            # design would need the seed folded into the block key and a different
            # run count, so it is rejected at validation rather than inside plan().
            raise ValueError(
                f"this spec version plans exactly one seed per experiment; "
                f"got {list(self.seeds)}")
        for fam in self.families:
            if fam not in FAMILIES:
                raise ValueError(
                    f"unknown workload family {fam!r}; frozen set is {list(FAMILIES)}")
        for scale in self.scales:
            if scale not in SCALES:
                raise ValueError(f"unknown scale {scale!r}; frozen set is {list(SCALES)}")
        for seed in self.seeds:
            if seed not in SEEDS:
                raise ValueError(f"unknown seed {seed!r}; frozen set is {list(SEEDS)}")
        if self.repetitions < 1:
            raise ValueError(f"repetitions must be >= 1, got {self.repetitions}")
        if self.warmup_runs < 0:
            raise ValueError(f"warmup_runs must be >= 0, got {self.warmup_runs}")

        validate_grid(self.grid)
        if not any(p.is_reference for p in self.grid):
            raise ValueError("configuration grid must include the B0 reference point")

        missing = [s for s in self.scales if s not in self.timeouts_by_scale]
        if missing:
            raise ValueError(f"no timeout declared for scale(s) {missing}")
        for scale, value in self.timeouts_by_scale.items():
            if value <= 0:
                raise ValueError(f"timeout for scale {scale!r} must be > 0, got {value}")

        # Test-set freeze, enforced over the whole declared scope.
        for fam in self.families:
            for scale in self.scales:
                for seed in self.seeds:
                    assert_train_only(fam, scale, seed)

        self._validate_gate()

    def _validate_gate(self) -> None:
        # Every key that can change the verdict must be declared explicitly. A key
        # left to a code-side default would be an undeclared degree of freedom in a
        # pre-registered criterion.
        required = ("criterion_id", "metric", "statistic", "min_relative_spread",
                    "min_families", "scope", "family_rule", "noise_rule",
                    "min_valid_runs_per_config", "require_complete_panel")
        missing = [k for k in required if k not in self.gate]
        if missing:
            raise ValueError(f"gate specification missing key(s): {missing}")
        if self.gate["statistic"] != "median":
            raise ValueError(
                "gate statistic must be 'median' (PLAN section 22 primary statistic), "
                f"got {self.gate['statistic']!r}")
        if self.gate["family_rule"] not in ("any_scale", "all_scales"):
            raise ValueError(
                "gate family_rule must be 'any_scale' or 'all_scales', got "
                f"{self.gate['family_rule']!r}")
        if self.gate["noise_rule"] != "spread_must_exceed_pooled_within_config_cv":
            raise ValueError(
                "gate noise_rule must be "
                "'spread_must_exceed_pooled_within_config_cv', got "
                f"{self.gate['noise_rule']!r}")
        if int(self.gate["min_valid_runs_per_config"]) < 1:
            raise ValueError("min_valid_runs_per_config must be >= 1")
        if not isinstance(self.gate["require_complete_panel"], bool):
            raise ValueError("require_complete_panel must be a boolean")
        if self.gate["metric"] != "execution_time_s":
            raise ValueError(
                "gate metric must be execution_time_s (the frozen Day-3 authoritative "
                f"timing), got {self.gate['metric']!r}")
        if not 0 < float(self.gate["min_relative_spread"]) < 1:
            raise ValueError("min_relative_spread must be a fraction in (0, 1)")
        if int(self.gate["min_families"]) < 1:
            raise ValueError("min_families must be >= 1")
        if self.gate["scope"] not in ("varied_only", "including_reference"):
            raise ValueError(
                "gate scope must be 'varied_only' or 'including_reference', got "
                f"{self.gate['scope']!r}")

    # -- planning ------------------------------------------------------
    def blocks(self) -> list[tuple[str, str, int]]:
        """Ordered (family, scale, rep) blocks. Scale-major, then rep, then family."""
        return [(fam, scale, rep)
                for scale in self.scales
                for rep in range(1, self.repetitions + 1)
                for fam in self.families]

    def plan(self) -> tuple[RunSpec, ...]:
        """The full, deterministic, order-fixed run plan (measured runs only)."""
        self.validate()          # also pins the design to exactly one seed
        seed = self.seeds[0]
        runs: list[RunSpec] = []
        order = 0
        for family, scale, rep in self.blocks():
            block_id = f"{family}|{scale}|rep{rep}"
            rng = random.Random(f"{self.order_seed}|{block_id}")
            points = list(self.grid)
            rng.shuffle(points)
            for point in points:
                runs.append(RunSpec(
                    run_id=run_id_for(family, scale, seed, point.name, rep),
                    family=family, scale=scale, seed=seed, rep=rep,
                    config=point, split=split_of(family, scale, seed),
                    timeout_seconds=float(self.timeouts_by_scale[scale]),
                    order_index=order, block_id=block_id))
                order += 1

        ids = [r.run_id for r in runs]
        if len(set(ids)) != len(ids):
            raise ValueError("run plan contains duplicate run ids")
        return tuple(runs)

    def planned_run_count(self) -> int:
        return len(self.families) * len(self.scales) * self.repetitions * len(self.grid)

    def fingerprint(self) -> str:
        """Stable SHA-256 over the whole pre-registered design."""
        payload = json.dumps(self.to_dict(include_plan=False), sort_keys=True,
                             separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def to_dict(self, include_plan: bool = False) -> dict[str, Any]:
        out: dict[str, Any] = {
            "experiment_id": self.experiment_id,
            "spec_version": self.spec_version,
            "grid_version": GRID_VERSION,
            "families": list(self.families),
            "scales": list(self.scales),
            "seeds": list(self.seeds),
            "repetitions": self.repetitions,
            "warmup_runs": self.warmup_runs,
            "aqe_enabled": self.aqe_enabled,
            "order_seed": self.order_seed,
            "timeouts_by_scale": dict(sorted(self.timeouts_by_scale.items())),
            "base_config_path": self.base_config_path,
            "result_root": self.result_root,
            "grid_fingerprint": grid_fingerprint(self.grid),
            "grid": [p.to_dict() for p in self.grid],
            "gate": dict(sorted(self.gate.items())),
            "split": {
                "train_families": list(TRAIN_FAMILIES),
                "train_scales": list(TRAIN_SCALES),
                "train_seeds": list(TRAIN_SEEDS),
                "validation_seeds": list(VALIDATION_SEEDS),
                "test_family": TEST_FAMILY,
                "test_scale": TEST_SCALE,
                "test_seeds": list(TEST_SEEDS),
                "exp002_uses": TRAIN,
            },
            "planned_run_count": self.planned_run_count(),
            "notes": dict(sorted(self.notes.items())),
        }
        if include_plan:
            out["plan"] = [r.to_dict() for r in self.plan()]
        return out

    # -- loading -------------------------------------------------------
    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ExperimentSpec":
        try:
            spec = cls(
                experiment_id=str(raw["experiment_id"]),
                spec_version=str(raw["spec_version"]),
                families=tuple(raw["families"]),
                scales=tuple(raw["scales"]),
                seeds=tuple(int(s) for s in raw["seeds"]),
                repetitions=int(raw["repetitions"]),
                warmup_runs=int(raw["warmup_runs"]),
                aqe_enabled=bool(raw["aqe_enabled"]),
                order_seed=int(raw["order_seed"]),
                timeouts_by_scale={str(k): float(v)
                                   for k, v in raw["timeouts_by_scale"].items()},
                grid=build_grid(include_b0=bool(raw.get("include_b0", True))),
                base_config_path=str(raw["base_config_path"]),
                result_root=str(raw["result_root"]),
                gate=dict(raw["gate"]),
                notes=dict(raw.get("notes", {})),
            )
        except KeyError as exc:
            raise ValueError(f"EXP-002 spec missing required key: {exc}") from None
        spec.validate()
        return spec

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ExperimentSpec":
        import yaml

        with open(path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        return cls.from_dict(raw)


def summarize_plan(runs: Sequence[RunSpec]) -> dict[str, Any]:
    """Counts by scale / family / configuration - a pre-run sanity view."""
    def _count(key) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in runs:
            out[str(key(r))] = out.get(str(key(r)), 0) + 1
        return dict(sorted(out.items()))

    return {
        "total": len(runs),
        "by_scale": _count(lambda r: r.scale),
        "by_family": _count(lambda r: r.family),
        "by_config": _count(lambda r: r.config.name),
        "by_split": _count(lambda r: r.split),
    }
