"""GenerationSpec + chunked deterministic row generation (Day 13).

Row rule (chunking-independent): row i is fully determined by (i, spec) —
its Zipf draws are re-derived by replaying the seeded RNG stream from draw
0 to the row's draw offset. Chunks only slice the index range.

Day-13 conventions (NOT frozen research decisions):
- scales: micro (fixture-only, 5_000 lineitem rows) + small/medium/large
  ladder targets 0.3/1/3 GB with lineitem:orders = 4:1.
- default skew s=1.0, customer cardinality 10_000, part cardinality 2_000.
"""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass

from sparkrl.datagen.distributions import ZipfSampler
from sparkrl.datagen.schema import GENERATOR_VERSION, SCHEMA_VERSION

SCALE_ROWS_LINEITEM: dict[str, int] = {
    "micro": 5_000,        # fixture-only scale, NOT part of the research ladder
    "small": 3_000_000,    # ~0.3 GB target
    "medium": 10_000_000,  # ~1 GB target
    "large": 30_000_000,   # ~3 GB target
}
LINEITEM_TO_ORDERS = 4
RESEARCH_SCALES = ("small", "medium", "large")

DEFAULT_SKEW = 1.0
DEFAULT_CUST_CARDINALITY = 10_000
DEFAULT_PART_CARDINALITY = 2_000
DEFAULT_CHUNK_ROWS = 100_000


@dataclass(frozen=True)
class GenerationSpec:
    """Complete deterministic identity of one generated table."""

    table: str  # "orders" | "lineitem"
    scale: str  # micro | small | medium | large
    rows: int
    seed: int
    skew: float
    key_cardinality: int  # cust domain (orders) or orders domain (lineitem FK)
    part_cardinality: int = DEFAULT_PART_CARDINALITY  # lineitem only
    chunk_rows: int = DEFAULT_CHUNK_ROWS

    def __post_init__(self) -> None:
        if self.table not in ("orders", "lineitem"):
            raise ValueError(f"table must be orders|lineitem, got {self.table!r}")
        if self.scale not in SCALE_ROWS_LINEITEM:
            raise ValueError(
                f"scale must be one of {sorted(SCALE_ROWS_LINEITEM)}, got {self.scale!r}")
        if self.rows < 1:
            raise ValueError(f"rows must be >= 1, got {self.rows!r}")
        if self.seed < 0:
            raise ValueError(f"seed must be >= 0, got {self.seed!r}")
        if not 0 <= self.skew <= 5.0:
            raise ValueError(f"skew must be in [0, 5], got {self.skew!r}")
        if self.key_cardinality < 1:
            raise ValueError("key_cardinality must be >= 1")
        if self.chunk_rows < 1:
            raise ValueError("chunk_rows must be >= 1")

    def fingerprint(self) -> str:
        """Stable identity: schema + scale + seed + distribution + versions."""
        payload = {
            "generator_version": GENERATOR_VERSION,
            "schema_version": SCHEMA_VERSION,
            "table": self.table,
            "scale": self.scale,
            "rows": self.rows,
            "seed": self.seed,
            "skew": self.skew,
            "key_cardinality": self.key_cardinality,
            "part_cardinality": self.part_cardinality,
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
