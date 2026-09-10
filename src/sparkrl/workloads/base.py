"""Common workload contract for the five frozen families (Day 15).

Implements COMP-SPARK-03 (ARCHITECTURE_FREEZE §5, COMPONENT_CONTRACTS §1):
deterministic workloads + reference values + validation. Every family
exposes ``WorkloadSpec`` in and ``WorkloadResult`` out via a shared base
class; the CLI dispatches through the registry in ``__init__`` (never a
monolithic if/elif block).

Frozen family semantics come from PLAN §11; per-family operator logic
lives in ``families.py``. This module owns only the shared contract:

- ``WorkloadSpec``: family / scale / seed (validated pre-run).
- ``WorkloadResult``: logical result payload + deterministic signature.
- ``BaseWorkload``: run/validate/reference_check/manifest plumbing hooks.
- ``result_signature``: FNV-1a 64-bit over canonical logical content only
  (never timestamps, app IDs, paths, or hostnames).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from sparkrl.datagen.checksums import _fnv1a_64, _FNV_OFFSET, encode_row

FAMILIES: tuple[str, ...] = ("F1_agg", "F2_join", "F3_rdd", "F4_ski", "F5_mixed")
SCALES: tuple[str, ...] = ("small", "medium", "large")
SEEDS: tuple[int, ...] = (0, 1, 2, 3, 4)

# PLAN §11: F4 consumes skew-1.5; F1/F2/F3/F5 share skew-1.0 physicals.
FAMILY_SKEW: dict[str, float] = {
    "F1_agg": 1.0,
    "F2_join": 1.0,
    "F3_rdd": 1.0,
    "F4_ski": 1.5,
    "F5_mixed": 1.0,
}


@dataclass(frozen=True)
class WorkloadSpec:
    """Validated (family, scale, seed); raises ValueError pre-run on bad params."""

    family: str
    scale: str
    seed: int

    def __post_init__(self) -> None:
        if self.family not in FAMILIES:
            raise ValueError(
                f"unknown family {self.family!r}; expected one of {list(FAMILIES)}")
        if self.scale not in SCALES:
            raise ValueError(
                f"unknown scale {self.scale!r}; expected one of {list(SCALES)}")
        if self.seed not in SEEDS:
            raise ValueError(
                f"unknown seed {self.seed!r}; expected one of {list(SEEDS)}")


@dataclass
class WorkloadResult:
    """Logical result of one workload execution (correctness data, not timing)."""

    workload_id: str
    family: str
    scale: str
    seed: int
    dataset_id: str
    dataset_fingerprint: str
    schema_fingerprint: str
    workload_version: str
    success: bool
    result_signature: str
    rows_processed: int
    columns: tuple[str, ...] = ()
    measurements: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "workload_id": self.workload_id,
            "family": self.family,
            "scale": self.scale,
            "seed": self.seed,
            "dataset_id": self.dataset_id,
            "dataset_fingerprint": self.dataset_fingerprint,
            "schema_fingerprint": self.schema_fingerprint,
            "workload_version": self.workload_version,
            "success": self.success,
            "result_signature": self.result_signature,
            "rows_processed": self.rows_processed,
            "columns": list(self.columns),
            "measurements": dict(self.measurements),
            "error": self.error,
        }


def result_signature(parts: list[tuple]) -> str:
    """Deterministic FNV-1a 64-bit hex over canonical logical row content.

    ``parts`` are tuples in a caller-fixed order; encoding reuses the
    Day-13 canonical ``encode_row`` (floats repr'd, ints/str str'd, ``|``
    separators) folded in order with ``\\n`` separators. Same logical
    result -> same signature on any machine, any run, any Spark app ID.
    """
    state = _FNV_OFFSET
    for part in parts:
        state = _fnv1a_64(encode_row(tuple(part)), state)
        state = _fnv1a_64(b"\n", state)
    return format(state, "016x")


class BaseWorkload:
    """Shared plumbing for the five frozen families.

    Subclasses set ``family``, ``workload_version``, and ``workload_id``,
    and implement ``run``, ``reference_check`` (small-scale pure-Python
    expectation where practical), and ``validate``.
    """

    family: ClassVar[str] = ""
    workload_version: ClassVar[str] = ""
    workload_id: ClassVar[str] = ""

    def __init__(self, scale: str, seed: int) -> None:
        self.spec = WorkloadSpec(family=self.family, scale=scale, seed=seed)
        self.scale = scale
        self.seed = seed

    def run(self, spark, config=None):  # pragma: no cover - overridden per family
        raise NotImplementedError

    @classmethod
    def reference_check(cls, rows: int):  # pragma: no cover - overridden per family
        raise NotImplementedError

    def validate(self, result: WorkloadResult) -> bool:  # pragma: no cover
        raise NotImplementedError
