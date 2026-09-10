"""The five frozen workload families (Day 15, PLAN §11).

Each family reads the Day-14 Parquet substrate via ``resolver`` and
executes its frozen operator pattern with NO performance tuning:

- F1_agg (v1): multi-key groupBy (cust_key, order_day) + window sums over
  lineitem+orders — stresses shuffle partitions. No broadcast, no cache.
- F2_join (v1): lineitem ⨝ orders on order_key — stresses broadcast
  threshold/partitions. Plain join, NO broadcast hint.
- F3_rdd (v1): RDD API sort + filter + reduceByKey — stresses
  default.parallelism. Deliberately RDD (not DataFrame) to preserve a
  distinct execution pattern; no repartition/coalesce tuning.
- F4_ski (v1): lineitem ⨝ orders on the skew-1.5 substrate, grouped by
  the skewed key — stresses partitioning under skew. Skew comes from the
  data, never generated at execution time; no salting/skew hints.
- F5_mixed (v1): 3-phase ingest-clean → join → aggregate-write pipeline
  where the join output is consumed twice (aggregate + write) — makes
  caching meaningful. Phase 1 result is cached because the frozen
  definition requires double consumption (correctness, not benchmark
  advantage); nothing else is cached.

Signatures: FNV-1a over canonical logical content (collect in key order;
floats rounded to 6 dp before encoding so Spark float noise cannot leak
into the signature).
"""
from __future__ import annotations

from typing import Any

from sparkrl.workloads.base import (BaseWorkload, WorkloadResult,
                                    result_signature,)
from sparkrl.workloads.resolver import ResolvedDataset, resolve_dataset


def _sig(rows: list[tuple]) -> str:
    norm: list[tuple] = []
    for row in rows:
        norm.append(tuple(round(v, 6) if isinstance(v, float) else v
                          for v in row))
    return result_signature(norm)


def _validate_not_none(result: WorkloadResult) -> bool:
    return (result.success and result.error is None
            and len(result.result_signature) == 16
            and result.rows_processed > 0)


class F1Aggregation(BaseWorkload):
    """F1_agg_v1: multi-key groupBy + window sums (shuffle-partition stress)."""

    family = "F1_agg"
    workload_version = "F1_agg_v1"
    workload_id = "F1_agg_v1"

    def run(self, spark, config=None) -> WorkloadResult:
        ds = resolve_dataset(self.family, self.scale, self.seed)
        li = spark.read.parquet(str(ds.lineitem_path))
        orders = spark.read.parquet(str(ds.orders_path))
        joined = li.join(orders, on="order_key", how="inner")
        from pyspark.sql import functions as F
        from pyspark.sql.window import Window
        agg = (joined.groupBy("cust_key", "order_day")
               .agg(F.sum("extended_price").alias("revenue"),
                    F.count("*").alias("n_lines")))
        w = Window.partitionBy("cust_key").orderBy("order_day")
        out = (agg.withColumn("cum_revenue",
                              F.sum("revenue").over(w)).orderBy("cust_key", "order_day"))
        rows = out.collect()
        parts = [(r["cust_key"], r["order_day"], float(r["revenue"]),
                  int(r["n_lines"]), float(r["cum_revenue"])) for r in rows]
        parts.sort()
        sig = _sig(parts)
        total_rev = round(float(sum(p[2] for p in parts)), 6)
        return WorkloadResult(
            workload_id=self.workload_id, family=self.family,
            scale=self.scale, seed=self.seed, dataset_id=ds.dataset_id,
            dataset_fingerprint=ds.dataset_fingerprint,
            schema_fingerprint=ds.schema_fingerprint,
            workload_version=self.workload_version, success=True,
            result_signature=sig, rows_processed=len(parts),
            columns=("cust_key", "order_day", "revenue", "n_lines",
                     "cum_revenue"),
            measurements={"groups": len(parts), "total_revenue": total_rev,
                          "orders_rows": ds.orders_manifest.get("row_count"),
                          "lineitem_rows": ds.lineitem_manifest.get("row_count"),
                          "skew": ds.skew})

    def validate(self, result: WorkloadResult) -> bool:
        return _validate_not_none(result)


class F2Join(BaseWorkload):
    """F2_join_v1: lineitem x orders (broadcast-threshold stress, no hint)."""

    family = "F2_join"
    workload_version = "F2_join_v1"
    workload_id = "F2_join_v1"

    def run(self, spark, config=None) -> WorkloadResult:
        ds = resolve_dataset(self.family, self.scale, self.seed)
        li = spark.read.parquet(str(ds.lineitem_path))
        orders = spark.read.parquet(str(ds.orders_path))
        joined = li.join(orders, on="order_key", how="inner")
        from pyspark.sql import functions as F
        out = (joined.groupBy("order_day")
               .agg(F.sum("extended_price").alias("revenue"),
                    F.count("*").alias("n_lines")).orderBy("order_day"))
        rows = out.collect()
        parts = [(r["order_day"], float(r["revenue"]), int(r["n_lines"]))
                 for r in rows]
        parts.sort()
        sig = _sig(parts)
        total = round(float(sum(p[1] for p in parts)), 6)
        return WorkloadResult(
            workload_id=self.workload_id, family=self.family,
            scale=self.scale, seed=self.seed, dataset_id=ds.dataset_id,
            dataset_fingerprint=ds.dataset_fingerprint,
            schema_fingerprint=ds.schema_fingerprint,
            workload_version=self.workload_version, success=True,
            result_signature=sig, rows_processed=len(parts),
            columns=("order_day", "revenue", "n_lines"),
            measurements={"groups": len(parts), "total_revenue": total,
                          "skew": ds.skew})

    def validate(self, result: WorkloadResult) -> bool:
        return _validate_not_none(result)

    @classmethod
    def reference_check(cls, rows: int) -> dict[str, Any]:
        raise NotImplementedError("F2 reference lives in unit fixtures")


class F3Rdd(BaseWorkload):
    """F3_rdd_v1: RDD sort + filter + reduceByKey (default.parallelism).

    Intentionally RDD (not DataFrame/SQL): the frozen definition needs a
    distinct RDD execution pattern so EXP-002 sensitivity covers the RDD
    engine path. Pipeline: key by part_key -> sortByKey -> filter
    quantity >= 10 -> reduceByKey(sum of extended_price). No
    repartition/coalesce tuning.
    """

    family = "F3_rdd"
    workload_version = "F3_rdd_v1"
    workload_id = "F3_rdd_v1"

    def run(self, spark, config=None) -> WorkloadResult:
        ds = resolve_dataset(self.family, self.scale, self.seed)
        li = spark.read.parquet(str(ds.lineitem_path))
        rdd = li.rdd.map(
            lambda r: (int(r["part_key"]),
                       (float(r["extended_price"]), int(r["quantity"]))))
        reduced = (rdd.sortByKey()
                   .filter(lambda kv: kv[1][1] >= 10)
                   .mapValues(lambda v: v[0])
                   .reduceByKey(lambda a, b: a + b))
        parts = sorted(reduced.collect())
        sig = _sig([(k, float(v)) for k, v in parts])
        return WorkloadResult(
            workload_id=self.workload_id, family=self.family,
            scale=self.scale, seed=self.seed, dataset_id=ds.dataset_id,
            dataset_fingerprint=ds.dataset_fingerprint,
            schema_fingerprint=ds.schema_fingerprint,
            workload_version=self.workload_version, success=True,
            result_signature=sig, rows_processed=len(parts),
            columns=("part_key", "revenue_qty_ge_10"),
            measurements={"groups": len(parts), "skew": ds.skew})

    def validate(self, result: WorkloadResult) -> bool:
        return _validate_not_none(result)

    @classmethod
    def reference_check(cls, rows: int) -> dict[str, Any]:
        raise NotImplementedError("F3 reference lives in unit fixtures")


class F4SkewJoin(BaseWorkload):
    """F4_ski_v1: skewed join on Zipf(1.5) data (no skew tricks at runtime)."""

    family = "F4_ski"
    workload_version = "F4_ski_v1"
    workload_id = "F4_ski_v1"

    def run(self, spark, config=None) -> WorkloadResult:
        ds = resolve_dataset(self.family, self.scale, self.seed)
        if abs(ds.skew - 1.5) > 1e-12:
            raise ValueError(
                f"F4_ski requires skew-1.5 data, resolved skew={ds.skew}")
        li = spark.read.parquet(str(ds.lineitem_path))
        orders = spark.read.parquet(str(ds.orders_path))
        joined = li.join(orders, on="order_key", how="inner")
        from pyspark.sql import functions as F
        out = (joined.groupBy("cust_key")
               .agg(F.sum("extended_price").alias("revenue"),
                    F.count("*").alias("n_lines")).orderBy("cust_key"))
        rows = out.collect()
        parts = [(r["cust_key"], float(r["revenue"]), int(r["n_lines"]))
                 for r in rows]
        parts.sort()
        sig = _sig(parts)
        top1 = round(float(parts[0][1]) if parts else 0.0, 6)
        return WorkloadResult(
            workload_id=self.workload_id, family=self.family,
            scale=self.scale, seed=self.seed, dataset_id=ds.dataset_id,
            dataset_fingerprint=ds.dataset_fingerprint,
            schema_fingerprint=ds.schema_fingerprint,
            workload_version=self.workload_version, success=True,
            result_signature=sig, rows_processed=len(parts),
            columns=("cust_key", "revenue", "n_lines"),
            measurements={"groups": len(parts), "skew": ds.skew,
                          "zipf_parameter": ds.orders_manifest.get("zipf_parameter"),
                          "top_key_revenue": top1})

    def validate(self, result: WorkloadResult) -> bool:
        return _validate_not_none(result)

    @classmethod
    def reference_check(cls, rows: int) -> dict[str, Any]:
        raise NotImplementedError("F4 reference lives in unit fixtures")


class F5Mixed(BaseWorkload):
    """F5_mixed_v1: 3-phase ingest-clean -> join -> aggregate-write.

    Frozen definition (PLAN §11): "ingest-clean → join → aggregate-write;
    intermediate consumed twice — makes caching meaningful".

    - Phase 1 (ingest-clean): domain-validity filter on lineitem
      (quantity >= 1 AND extended_price > 0). No-op by construction — the
      generator emits in-domain rows — but it is a real scan+filter stage;
      the data substrate is intentionally clean.
    - Phase 2 (join): cleaned x orders on order_key. The join OUTPUT is the
      intermediate and is cached.
    - Phase 3 (aggregate-write): the cached intermediate is consumed TWICE —
      (a) aggregate arm: group by order_day (sum revenue, count lines),
      collected for the signature; (b) write arm: full materialization of
      the intermediate (count). This is the frozen "consumed twice"
      property: caching here is required for correctness of the pipeline
      shape, not a benchmark advantage. The CLI/manifest layer owns any
      persistence; the workload itself writes no output Parquet.

    Note: the aggregate arm's logical output equals F2_join's (same embedded
    computation over the same no-op-cleaned input) — a deliberate
    cross-family consistency property. F5's identity is the pipeline shape,
    and its signature differs from F2's because it also binds the
    materialized intermediate size.
    """

    family = "F5_mixed"
    workload_version = "F5_mixed_v1"
    workload_id = "F5_mixed_v1"
    PHASES: tuple[str, ...] = ("ingest-clean", "join", "aggregate-write")

    def run(self, spark, config=None) -> WorkloadResult:
        ds = resolve_dataset(self.family, self.scale, self.seed)
        li = spark.read.parquet(str(ds.lineitem_path))
        orders = spark.read.parquet(str(ds.orders_path))
        from pyspark.sql import functions as F
        cleaned = li.filter("quantity >= 1 AND extended_price > 0")
        n_clean = cleaned.count()
        joined = cleaned.join(orders, on="order_key", how="inner").cache()
        out = (joined.groupBy("order_day")
               .agg(F.sum("extended_price").alias("revenue"),
                    F.count("*").alias("n_lines")).orderBy("order_day"))
        rows = out.collect()
        n_written = joined.count()  # write arm: full materialization
        joined.unpersist()
        parts = [(r["order_day"], float(r["revenue"]), int(r["n_lines"]))
                 for r in rows]
        parts.sort()
        parts.append(("n_written", int(n_written)))
        sig = _sig(parts)
        return WorkloadResult(
            workload_id=self.workload_id, family=self.family,
            scale=self.scale, seed=self.seed, dataset_id=ds.dataset_id,
            dataset_fingerprint=ds.dataset_fingerprint,
            schema_fingerprint=ds.schema_fingerprint,
            workload_version=self.workload_version, success=True,
            result_signature=sig, rows_processed=len(rows),
            columns=("order_day", "revenue", "n_lines"),
            measurements={"phases": list(self.PHASES),
                          "phase1_clean_rows": int(n_clean),
                          "phase2_intermediate_rows": int(n_written),
                          "intermediate_cached": True,
                          "groups": len(rows), "skew": ds.skew})

    def validate(self, result: WorkloadResult) -> bool:
        ok = _validate_not_none(result)
        phases = (result.measurements or {}).get("phases", [])
        return ok and list(phases) == list(self.PHASES)

    @classmethod
    def reference_check(cls, rows: int) -> dict[str, Any]:
        raise NotImplementedError("F5 reference lives in unit fixtures")


__all__ = ["F1Aggregation", "F2Join", "F3Rdd", "F4SkewJoin", "F5Mixed"]
