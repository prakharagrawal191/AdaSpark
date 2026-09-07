"""Deterministic baseline workload for the Day-3 timing harness.

Design (plan §19 / Dec-3 baseline, NOT the research workload suite yet):
- ``spark.range(N)`` gives deterministic ids 0..N-1; every derived column is a pure
  function of ``id``, so the resulting DataFrame and its checksum are fully reproducible
  for a given row count — no RNG state involved.
- Pipeline: derive columns → filter → group-by aggregation → materialize via ``collect()``
  (a real execution is forced; a small checksum + group count are returned).
- The action/result "materializes an output" and returns a small validation value, per the
  Day-3 requirements. No output Parquet is written (that belongs to later workload
  families); this baseline isolates pure compute timing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BaselineResult:
    """Small validation payload returned by the baseline workload."""

    group_count: int
    checksum_value: float
    row_count_filtered: int

    @property
    def checksum(self) -> Any:
        return {
            "group_count": self.group_count,
            "checksum_value": round(self.checksum_value, 6),
            "rows_after_filter": self.row_count_filtered,
        }


class BaselineWorkload:
    """Deterministic filter + groupBy-sum baseline (workload id ``baseline_agg_v1``)."""

    workload_id = "baseline_agg_v1"

    def __init__(self, rows: int = 1_000_000, seed: int = 42) -> None:
        if rows < 1:
            raise ValueError(f"rows must be >= 1, got {rows}")
        self.rows = int(rows)
        self.seed = int(seed)
        self._columns = ("id", "k", "v")

    # pure-Python reference implementation for tests / determinism checks ---------
    @classmethod
    def reference_check(cls, rows: int) -> BaselineResult:
        """Compute the expected result without Spark (used by unit tests)."""
        group_sums: dict[int, float] = {}
        count = 0
        for i in range(rows):
            if i % 11 == 0:      # mirrors the SQL filter below
                continue
            k = i % 1000
            v = (i % 100_000) / 7.0
            group_sums[k] = group_sums.get(k, 0.0) + v
            count += 1
        total = sum(group_sums.values())
        return BaselineResult(
            group_count=len(group_sums), checksum_value=total, row_count_filtered=count)

    # Spark implementation ---------------------------------------------------------
    def run(self, spark, config=None):
        """Execute the deterministic filter + aggregation, materialize, return result."""
        src = (spark.range(self.rows)
               .selectExpr("id", "id % 1000 as k", "(id % 100000) / 7.0 as v"))
        filtered = src.filter("id % 11 != 0")
        aggregates = (filtered.groupBy("k")
                      .agg({"v": "sum"})
                      .orderBy("k"))
        collected = aggregates.collect()          # force execution (materialization)
        group_count = len(collected)
        checksum = round(float(sum(row[1] for row in collected)), 6)
        rows_after_filter = filtered.count()
        return BaselineResult(
            group_count=group_count,
            checksum_value=checksum,
            row_count_filtered=rows_after_filter)

    # -- completion check (used by validation scripts) ----------------------------
    @staticmethod
    def _filtered_count(rows: int) -> int:
        """Number of ids in [0, rows) that are NOT multiples of 11."""
        excluded = (rows - 1) // 11 + 1   # multiples of 11 in 0..rows-1
        return rows - excluded

    def validate(self, result: BaselineResult, expect_same_as_ref: bool = True) -> bool:
        ok = (result.group_count == 1000
              and result.row_count_filtered == self._filtered_count(self.rows))
        if expect_same_as_ref:
            ref = self.reference_check(self.rows)
            ok = ok and abs(result.checksum_value - ref.checksum_value) < 1e-6
        return ok