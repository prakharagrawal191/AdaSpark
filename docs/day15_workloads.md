# Day 15 Workloads

Implementation of the five frozen Spark workload families (PLAN §11) as the
experimental instruments for later configuration-sensitivity (EXP-002) and
RL (EXP-004/005) studies. Day 15 delivers **correctness, interface
compatibility, and manifest generation** — no performance claims.

## 1. Common Workload Contract

All families implement the frozen COMP-SPARK-03 interface via
`sparkrl.workloads.base`:

- `BaseWorkload(scale, seed)` — constructs a workload bound to one
  (family, scale, seed) point.
- `run(spark, config=None) -> WorkloadResult` — resolves the dataset,
  executes the frozen operator pattern, computes a deterministic
  `result_signature`, returns a structured result.
- `validate(result) -> bool` — per-family logical invariant check.

`WorkloadResult` fields: `workload_id, family, scale, seed, dataset_id,
dataset_fingerprint, schema_fingerprint, workload_version, success,
result_signature, rows_processed, columns, measurements, error`.

Timing, warm-up, timeout, and session creation are **not** reimplemented —
they come from the Day-3 foundation (`sparkrl.spark.session/runner/config`).

## 2. Dataset Resolution

`sparkrl.workloads.resolver.resolve_dataset(family, scale, seed)` maps the
logical request through `data/generated/index.json` (the Day-14 inventory)
to the physical dataset:

- F1/F2/F3/F5 → skew-1.0 physical dataset for (scale, seed)
- F4 → dedicated skew-1.5 physical dataset for (scale, seed)

The resolver verifies: index entry exists, both table manifests exist and
parse, manifest scale/seed match the request, paths exist. Resolution
failure raises `DatasetResolutionError` — **no silent substitution** of
dataset, seed, or scale.

## 3. F1 Aggregation

`F1_agg_v1` — reads lineitem ⨝ orders, `groupBy(cust_key, order_day)`
with `sum(extended_price)`, `count(*)`, then a window sum
(`cum_revenue` partitioned by cust_key ordered by order_day), ordered
output, collected. Stresses shuffle partitions. No broadcast, no cache,
no repartition tuning.

## 4. F2 Join

`F2_join_v1` — lineitem ⨝ orders on `order_key` (inner), then
`groupBy(order_day)` with `sum(extended_price)`, `count(*)`, ordered,
collected. Stresses broadcast threshold/partitions. Plain join — **no

## 6. F4 Skewed Join

`F4_ski_v1` — identical join shape to F2 but executed on the **skew-1.5
substrate** (Zipf(1.5) keys baked into the Day-14 data, never generated at
execution time), grouped by the skewed key (`cust_key`), with skew
metadata (`skew`, `zipf_parameter`, `top_key_revenue`) recorded in the
manifest. Skew comes from the data only: no salting, no skew hints.
AQE is not touched inside F4 — it is an experimental control.

## 7. F5 Mixed 3-Phase

`F5_mixed_v1` — frozen pipeline "ingest-clean → join → aggregate-write;
intermediate consumed twice — makes caching meaningful":

1. **ingest-clean** — domain-validity filter on lineitem
   (`quantity >= 1 AND extended_price > 0`). No-op by construction (the

## 9. Manifest Schema

One `manifest.json` per run at
`results/workloads/<family>/<scale>/seed<seed>/manifest.json`:

| Field | Meaning |
|---|---|
| workload_id / family / workload_version | e.g. `F5_mixed_v1` / `F5_mixed` / `F5_mixed_v1` |
| scale / seed | requested and executed point |
| dataset_id / dataset_fingerprint / schema_fingerprint | from the resolved dataset manifests |
| spark_version / configuration_fingerprint / aqe_mode | from the Spark config layer (AQE recorded, never secretly changed) |
| success / error | logical validation outcome |
| **correctness** | `result_signature`, `rows_processed`, columns, per-family invariants (e.g. F5 phases, F4 skew metadata) |
| **performance** | `execution_time_s`, `warmup_time_s`, `total_time_s`, `timeout` — Day-3 runner timing |
| timestamp / code_version / spark_app_id | metadata only, excluded from signatures |

`correctness` and `performance` are separated at the top level; RL
state/action/reward are deliberately absent (later phases).

## 10. CLI

```
python scripts/run_workload.py --family F1_agg --scale small --seed 0
python scripts/run_workload.py --family F4_ski --scale medium --seed 2
```

Flags: `--family {F1_agg,F2_join,F3_rdd,F4_ski,F5_mixed}`,
`--scale {small,medium,large}`, `--seed {0..4}`, `--config`,
`--out` (results root), `--code-version`, `--print-manifest`.
Dispatch goes through the central registry
(`sparkrl.workloads.registry.REGISTRY`) — no per-family if-chains in the
CLI. Exit code is non-zero on any failure; `success=true` is never emitted
when logical validation fails.

## 11. Validation

- Per-family `validate()`: success + 16-hex signature + rows_processed > 0
  (+ F5 phases match the frozen three, + F4 skew metadata present).
- Unit tests (`tests/unit/test_workloads.py`): registry completeness,
  family lookup, invalid family/scale/seed, resolver failure modes,
  workload versions, result schema, signature determinism/distinctness,
  manifest serialization/validation — on tiny fixtures, never the
  multi-million-row substrate.
- Integration test (`tests/integration/test_workloads.py`): runs all five
  families at small/seed 0 through the CLI path and checks the Step-21
  manifest checklist.
- `scripts/validate_workloads.py`: structural validator (registry, docs,
  manifest fields).

## 12. Reproducibility

Each family run twice at (small, seed 0) produces the **same
result_signature**; execution time may vary and is never compared.
Verified signatures are recorded in `docs/WORKLOAD_INVENTORY.md`.

## 13. Deliberately Excluded Optimizations

Day 15 does **not** introduce: broadcast hints, manual repartition/coalesce
tuning, AQE-specific optimization (AQE stays at the project default and is
only *recorded*), caching for benchmark advantage (the single F5 cache is
mandated by the frozen double-consumption pipeline), RL, reward/state
logic, or baseline strategy logic. The workloads are experimental
instruments; execution-time optimization is the subject of the later
experiments, not of their implementation.

   generator emits in-domain rows) but a real scan+filter stage.
2. **join** — cleaned ⨝ orders on `order_key`; the join **output** is the
   intermediate and is cached.
3. **aggregate-write** — the cached intermediate is consumed **twice**:
   (a) aggregate arm: `groupBy(order_day)` sum/count, collected;
   (b) write arm: full materialization (`count()`). The `cache()` here is
   required by the frozen double-consumption pipeline shape — correctness,
   not benchmark advantage. The CLI/manifest layer owns persistence; the
   workload writes no output Parquet.

The aggregate arm's logical output equals F2's (same embedded computation
over the same input) — a deliberate cross-family consistency property;
F5's signature additionally binds the materialized intermediate size.

## 8. Result Signatures

Signature = FNV-1a 64-bit over the canonical encoding of the collected
logical result rows (sorted; floats rounded to 6 dp so Spark float noise
cannot leak in). F5 appends `("n_written", n)` to the row list before
signing. The signature depends only on logical content — never on
timestamp, Spark app ID, paths, or hostname. Same (family, scale, seed)
⇒ same signature; different seed ⇒ different signature.

broadcast hint**.

## 5. F3 RDD Sort/Filter/ReduceByKey

`F3_rdd_v1` — **deliberately RDD API** (not DataFrame/SQL) to preserve a
distinct execution pattern so EXP-002 sensitivity covers the RDD engine
path. Pipeline: `map` → key by `part_key` → `sortByKey` → `filter(quantity
>= 10)` → `mapValues(extended_price)` → `reduceByKey(sum)`, collected and
sorted. No repartition/coalesce tuning.
