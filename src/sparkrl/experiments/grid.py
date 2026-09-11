"""EXP-002 configuration grid: the frozen sensitivity-study configuration set.

Authority
---------
PLAN section 14 ("Action Space") defines the v1 configuration set exactly:

    spark.sql.shuffle.partitions in {16, 32, 64, 128}
        x execution parallelism (local[N] + spark.default.parallelism=N) in {2, 4, 8}

= 12 configurations. PLAN section 33 registers EXP-002 as
"12-config grid x F1,F2,F3,F5 x S,M". No other knob is varied: PLAN section 14
explicitly rejects executor memory (OOM risk on fixed hardware) and dynamic
allocation (off in local mode); broadcast threshold and caching are v2 /
ablation-only and are NOT part of EXP-002.

B0 (configs/baseline_b0.yaml) is the immutable reference condition and is included
as a 13th grid point so every candidate has an explicit, measured relationship to
the default. B0 is NOT one of the 12 varied configurations (shuffle_partitions=200
is outside the level set and default_parallelism is left to Spark), so no identity
collision exists.

Enumeration order (frozen)
--------------------------
``grid_index = parallelism_index * 4 + shuffle_index`` over parallelism (2,4,8)
and shuffle partitions (16,32,64,128). This ordering is load-bearing:
ARCHITECTURE_FREEZE (COMP-RL-07) states the pre-authorized Plan-B 4-configuration
subset is "indices {0,3,6,9} of the same table"; under this ordering those indices
are (2,16), (2,128), (4,64), (8,32) - a subset spanning both dimensions. Recording
the order here is a cross-reference to that frozen contract; no agent, policy or
index->action mapper is implemented (that is Day 26+, out of scope for EXP-002).

Frozen controls (identical for every grid point, never varied by EXP-002)
------------------------------------------------------------------------
AQE OFF (PLAN sections 7/11 - main study), driver memory 6g, event logging on,
warm-up policy, workload definitions, dataset identity.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterator

# PLAN section 14 v1 level sets. Order is frozen (see module docstring).
PARALLELISM_LEVELS: tuple[int, ...] = (2, 4, 8)
SHUFFLE_PARTITION_LEVELS: tuple[int, ...] = (16, 32, 64, 128)

# PLAN section 17 / configs/baseline_b0.yaml - the immutable reference condition.
B0_NAME = "B0"
B0_MASTER = "local[2]"
B0_SHUFFLE_PARTITIONS = 200
B0_DEFAULT_PARALLELISM: int | None = None
B0_DRIVER_MEMORY = "6g"

# EXP-002 varies only these knobs; everything else is a frozen control.
VARIED_PARAMETERS: tuple[str, ...] = (
    "spark.master",
    "spark.default.parallelism",
    "spark.sql.shuffle.partitions",
)

GRID_VERSION = "exp002-grid/v1"


@dataclass(frozen=True)
class ConfigPoint:
    """One configuration in the EXP-002 grid: identity + knobs + relation to B0."""

    name: str
    grid_index: int | None          # 0..11 for varied points; None for B0 (reference)
    is_reference: bool
    master: str
    shuffle_partitions: int
    default_parallelism: int | None
    driver_memory: str = B0_DRIVER_MEMORY
    aqe_enabled: bool = False       # frozen control: AQE OFF throughout EXP-002

    @property
    def parallelism(self) -> int:
        """N from ``local[N]`` - the execution parallelism actually requested."""
        return int(self.master[len("local["):-1])

    def effective_default_parallelism(self) -> int:
        """The value ``spark.default.parallelism`` must actually hold for this point.

        B0 declares ``default_parallelism = None`` ("leave it to Spark"). In local
        mode Spark's own out-of-box value for that setting is the core count, i.e. the
        N of ``local[N]`` - so B0's intended effective value is 2.

        This must be applied EXPLICITLY rather than left unset. ``spark.default.
        parallelism`` is a static SparkConf entry that survives ``SparkContext.stop()``
        inside one JVM, and PySpark reuses a single JVM for the lifetime of the Python
        process. A point that leaves the key unset therefore inherits whatever the
        PREVIOUS run in the same process set, which silently turned B0 into
        ``local[2]`` + ``default.parallelism=8`` during the first EXP-002 pass
        (see the audit document, "Measurement defect found and corrected").

        The declared identity in :meth:`knobs` deliberately keeps ``None`` - that is
        what B0 *specifies*. This method reports what the session must *hold* so the
        specification is honoured.
        """
        return (self.default_parallelism if self.default_parallelism is not None
                else self.parallelism)

    def knobs(self) -> dict[str, Any]:
        """Canonical knob dict - the scientific identity of this configuration."""
        return {
            "spark.master": self.master,
            "spark.driver.memory": self.driver_memory,
            "spark.sql.shuffle.partitions": self.shuffle_partitions,
            "spark.default.parallelism": self.default_parallelism,
            "spark.sql.adaptive.enabled": self.aqe_enabled,
        }

    def fingerprint(self) -> str:
        """Stable SHA-256 over the canonical knob dict (configuration identity).

        Deliberately narrower than ``SparkConfig.fingerprint()``, which also covers
        app name, timeouts and warm-up policy. Two grid points differ here if and
        only if they differ in an actual Spark knob.
        """
        payload = json.dumps(self.knobs(), sort_keys=True,
                             separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def delta_from_b0(self) -> dict[str, dict[str, Any]]:
        """Explicit parameter differences from B0 ({} for B0 itself)."""
        b0 = b0_point()
        if self.name == b0.name:
            return {}
        mine, theirs = self.knobs(), b0.knobs()
        return {key: {"b0": theirs[key], "candidate": mine[key]}
                for key in sorted(mine) if mine[key] != theirs[key]}

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "grid_index": self.grid_index,
            "is_reference": self.is_reference,
            "parallelism": self.parallelism,
            "shuffle_partitions": self.shuffle_partitions,
            "default_parallelism": self.default_parallelism,
            "master": self.master,
            "driver_memory": self.driver_memory,
            "aqe_enabled": self.aqe_enabled,
            "fingerprint": self.fingerprint(),
            "delta_from_b0": self.delta_from_b0(),
        }

    def apply_to(self, base_config):
        """Return a SparkConfig with this grid point's knobs applied.

        Frozen controls (AQE off, driver memory, warm-up policy, event logging) come
        from ``base_config`` (configs/baseline_b0.yaml) and are never rewritten here,
        except that AQE is re-asserted OFF as a defensive invariant.
        """
        return base_config.with_overrides(
            master=self.master,
            shuffle_partitions=self.shuffle_partitions,
            # always explicit - see effective_default_parallelism() for why leaving
            # this unset lets a previous run's value leak in through the shared JVM
            default_parallelism=self.effective_default_parallelism(),
            driver_memory=self.driver_memory,
            aqe_enabled=False,
        )


def b0_point() -> ConfigPoint:
    """The immutable B0 reference configuration (PLAN section 17)."""
    return ConfigPoint(
        name=B0_NAME, grid_index=None, is_reference=True,
        master=B0_MASTER, shuffle_partitions=B0_SHUFFLE_PARTITIONS,
        default_parallelism=B0_DEFAULT_PARALLELISM,
        driver_memory=B0_DRIVER_MEMORY, aqe_enabled=False)


def _varied_points() -> Iterator[ConfigPoint]:
    for p_idx, parallelism in enumerate(PARALLELISM_LEVELS):
        for s_idx, partitions in enumerate(SHUFFLE_PARTITION_LEVELS):
            yield ConfigPoint(
                name=f"G-p{parallelism}-sp{partitions}",
                grid_index=p_idx * len(SHUFFLE_PARTITION_LEVELS) + s_idx,
                is_reference=False,
                master=f"local[{parallelism}]",
                shuffle_partitions=partitions,
                default_parallelism=parallelism,
                driver_memory=B0_DRIVER_MEMORY,
                aqe_enabled=False)


def build_grid(include_b0: bool = True) -> tuple[ConfigPoint, ...]:
    """Full EXP-002 grid: B0 reference first, then the 12 PLAN-14 points in order."""
    points = list(_varied_points())
    if include_b0:
        points.insert(0, b0_point())
    validate_grid(points)
    return tuple(points)


def validate_grid(points) -> None:
    """Structural invariants. Raises ValueError on any violation."""
    points = list(points)
    if not points:
        raise ValueError("configuration grid is empty")

    names = [p.name for p in points]
    if len(set(names)) != len(names):
        raise ValueError(f"duplicate configuration names: {sorted(names)}")

    prints = [p.fingerprint() for p in points]
    if len(set(prints)) != len(prints):
        raise ValueError("duplicate configuration fingerprints: grid points collide")

    varied = [p for p in points if not p.is_reference]
    indices = sorted(p.grid_index for p in varied)
    if indices != list(range(len(varied))):
        raise ValueError(
            f"varied grid indices must be contiguous from 0, got {indices}")

    refs = [p for p in points if p.is_reference]
    if len(refs) > 1:
        raise ValueError("more than one reference configuration in the grid")

    for p in points:
        if p.aqe_enabled:
            raise ValueError(
                f"{p.name}: AQE must be OFF throughout EXP-002 (PLAN section 7)")
        if p.driver_memory != B0_DRIVER_MEMORY:
            raise ValueError(
                f"{p.name}: driver memory is a frozen control ({B0_DRIVER_MEMORY}), "
                f"got {p.driver_memory}")
        if not p.master.startswith("local[") or not p.master.endswith("]"):
            raise ValueError(f"{p.name}: master must be local[N], got {p.master!r}")
        if p.shuffle_partitions < 1:
            raise ValueError(f"{p.name}: shuffle_partitions must be >= 1")
        if p.is_reference:
            continue
        if p.parallelism not in PARALLELISM_LEVELS:
            raise ValueError(
                f"{p.name}: parallelism {p.parallelism} outside PLAN-14 levels "
                f"{PARALLELISM_LEVELS}")
        if p.shuffle_partitions not in SHUFFLE_PARTITION_LEVELS:
            raise ValueError(
                f"{p.name}: shuffle_partitions {p.shuffle_partitions} outside "
                f"PLAN-14 levels {SHUFFLE_PARTITION_LEVELS}")
        if p.default_parallelism != p.parallelism:
            raise ValueError(
                f"{p.name}: default_parallelism {p.default_parallelism} must equal "
                f"local[N] N={p.parallelism} (PLAN section 14 couples the two)")


def assert_b0_unchanged(base_config) -> None:
    """Verify a loaded SparkConfig still matches the frozen B0 definition."""
    b0 = b0_point()
    drift = []
    if base_config.master != b0.master:
        drift.append(f"master {base_config.master!r} != {b0.master!r}")
    if base_config.shuffle_partitions != b0.shuffle_partitions:
        drift.append(f"shuffle_partitions {base_config.shuffle_partitions} "
                     f"!= {b0.shuffle_partitions}")
    if base_config.default_parallelism != b0.default_parallelism:
        drift.append(f"default_parallelism {base_config.default_parallelism!r} "
                     f"!= {b0.default_parallelism!r}")
    if base_config.driver_memory != b0.driver_memory:
        drift.append(f"driver_memory {base_config.driver_memory!r} "
                     f"!= {b0.driver_memory!r}")
    if base_config.aqe_enabled:
        drift.append("aqe_enabled is True; B0 and EXP-002 require AQE OFF")
    if drift:
        raise ValueError("B0 configuration drift detected: " + "; ".join(drift))


def grid_fingerprint(points=None) -> str:
    """Stable SHA-256 over the whole ordered grid (spec-level identity)."""
    points = list(points) if points is not None else list(build_grid())
    payload = json.dumps(
        {"version": GRID_VERSION,
         "points": [{"name": p.name, "index": p.grid_index,
                     "fingerprint": p.fingerprint()} for p in points]},
        sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
