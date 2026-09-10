# Workload Inventory

The five frozen workload families (PLAN §11), implemented Day 15.
All families read the Day-14 Parquet substrate via
`sparkrl.workloads.resolver` and run through `scripts/run_workload.py`.

| Family | Version | Input | Core Operators | Scale Support | Deterministic Signature | Status |
|--------|---------|-------|----------------|---------------|--------------------------|--------|
| F1_agg | F1_agg_v1 | lineitem + orders (skew 1.0) | inner join → groupBy(cust_key, order_day) sum/count → window cumsum | small / medium / large | yes (FNV-1a over sorted rows) | implemented, smoke-verified |
| F2_join | F2_join_v1 | lineitem + orders (skew 1.0) | inner join on order_key → groupBy(order_day) sum/count | small / medium / large | yes | implemented, smoke-verified |
| F3_rdd | F3_rdd_v1 | lineitem (skew 1.0) | RDD: map → sortByKey(part_key) → filter(qty ≥ 10) → reduceByKey(sum) | small / medium / large | yes | implemented, smoke-verified |
| F4_ski | F4_ski_v1 | lineitem + orders (**skew 1.5**) | inner join on order_key → groupBy(cust_key) sum/count + skew metadata | small / medium / large | yes | implemented, smoke-verified |
| F5_mixed | F5_mixed_v1 | lineitem + orders (skew 1.0) | 3-phase: ingest-clean → join (cached intermediate) → aggregate-write (intermediate consumed twice) | small / medium / large | yes (binds aggregate rows + intermediate size) | implemented, smoke-verified |

## Verified small-scale signatures (seed 0)

| Family | Result signature | Rows out | Source |
|--------|------------------|----------|--------|
| F1_agg | `7f21df5d3daba03e` | 195,373 | results/workloads/F1_agg/small/seed0/manifest.json |
| F2_join | `8d7c822ef7e22db0` | 365 | results/workloads/F2_join/small/seed0/manifest.json |
| F3_rdd | `08e48f2bef07520c` | 2,000 | results/workloads/F3_rdd/small/seed0/manifest.json |
| F4_ski | `319b5c2b718ee080` | 1,091 | results/workloads/F4_ski/small/seed0/manifest.json |
| F5_mixed | `565ca8e84f975493` | 365 + intermediate | results/workloads/F5_mixed/small/seed0/manifest.json |

Signatures are stable across repeated runs of the same (family, scale,
seed) and differ across seeds. F5's aggregate arm logically equals F2's
(cross-family consistency check); F5's overall signature is distinct
because it also binds the materialized intermediate size.

## Notes

- F3 is intentionally RDD-API to preserve a distinct execution pattern.
- F4 consumes the dedicated Zipf(1.5) physical datasets; skew is in the
  data, never synthesized at execution time.
- The only cache in the family set is F5's join-output cache, mandated by
  the frozen double-consumption pipeline definition.
- AQE is recorded per manifest (`aqe_mode`) and never modified inside a
  workload; AQE on/off is an experimental control (EXP-005b).
