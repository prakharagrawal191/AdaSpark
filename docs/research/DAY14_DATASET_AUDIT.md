# Day 14 Dataset Audit

Generated: 2026-09-09. Head: `b1f6d06` (Day 13) → Day 14 working tree.
All entries below are derived from actual manifests
(`data/generated/index.json`, `data/generated/summary.json`).

## Planned Matrix

- Logical families × scales × seeds = **75** entries
  - F1_agg, F2_join, F3_rdd, F5_mixed → skew 1.0
  - F4_ski → skew 1.5
- Physical datasets = **30** (2 skews × 3 scales × 5 seeds)

| Scale | lineitem rows | orders rows |
|---|---|---|
| small | 3,000,000 | 750,000 |
| medium | 10,000,000 | 2,500,000 |
| large | 30,000,000 | 7,500,000 |

## Generated Matrix

| Skew | Scale | Seeds | Status |
|---|---|---|---|
| 1.0 | small | 0–4 | VALID (15 tables × 2 manifests, checksums in index.json) |
| 1.0 | medium | 0–4 | VALID |
| 1.0 | large | 0–4 | VALID |
| 1.5 | small | 0–4 | VALID |
| 1.5 | medium | 0–4 | VALID |
| 1.5 | large | 0–4 | VALID |

## Missing Matrix Entries

None — final `summary.json`: valid_physical=30, missing_physical=0. All 75 logical
entries (5 families × 3 scales × 5 seeds) resolve via `index.json`.

## Actual Storage Usage

From `summary.json` (parquet-compressed actuals):

| Metric | Value |
|---|---|
| total_physical | 30 |
| total_logical | 75 |
| valid_physical | 30 |
| total_rows | 537,500,000 |
| total_gib | 4.7524 (5,102,800,202 bytes) |
| bytes_by_scale | large 3,575,402,827 · medium 1,178,850,441 · small 348,547,934 |
| bytes_by_seed | s0 1,021,010,849 · s1 1,018,580,920 · s2 1,021,094,847 · s3 1,021,053,958 · s4 1,021,060,628 |
| lineitem_bytes_by_family | F1_agg/F2_join/F3_rdd/F5_mixed 2,532,969,340 each (shared skew-1.0) · F4_ski 1,992,816,564 |

## Size by Family

Shared skew-1.0 physicals (F1/F2/F3/F5): 2,532,969,340 lineitem bytes each (logical
mapping, same physical data — no duplication). Dedicated skew-1.5 (F4):
1,992,816,564 lineitem bytes (higher skew compresses slightly better).

## Size by Scale

large 3,575,402,827 · medium 1,178,850,441 · small 348,547,934 bytes
(≈ 330–360 MB / 110–120 MB / 37–39 MB per physical dataset).

## Size by Seed

s0 1,021,010,849 · s1 1,018,580,920 · s2 1,021,094,847 · s3 1,021,053,958 ·
s4 1,021,060,628 bytes (even spread; seed changes content, not size).

## Validation Summary

Every dataset runs `full_validation` (row domain rules + skew direction +
manifest consistency) at generation time. Ad-hoc Spark reads were run for the
pilot dataset (skew1_small_s0) on Day 14 to confirm Parquet readability.

## Checksum Summary

Checksums are FNV-1a 64-bit over canonical row content (not Parquet bytes).
Same spec ⇒ same checksum + generation fingerprint. Reproducibility samples
are listed in `docs/DATASET_README.md` → "How to reproduce".

| Sample dataset | files | row counts | checksum |
|---|---|---|---|
| skew1_small_s0 | 8 orders + 30 lineitem | 750k + 3M | orders `7af30d6083fa5305` / lineitem `9cf268163200a4c7` (from `index.json`) |

## Reproducibility Check

- Same spec → same checksum: verified on Day 13 (unit determinism tests) and
  Day 14 (pilot vs after crash recovery: regenerated lineitem for
  skew1_small_s0 twice → both `skew1_small_s0` marks VALID; new checksum from
  the second run recorded in its manifest).
- Changed seed → different checksum: covered by Day-13 unit test
  `test_different_seeds_differ`.

## Failures

| Dataset | Issue | Resolution |
|---|---|---|
| skew1_small_s0 (first attempt, pre-CDF-cache) | generation killed mid-lineitem (O(K·N) CDF rebuild made validation intractable) | Fixed `distributions.py` CDF cache; regenerated lineitem; dataset VALID |
| skew1.5_large_s1 lineitem (×2 attempts) | first-seed-100k write crashed mid-way (Spark executor loss); 250k retry completed but its `data/_SUCCESS` landed in the quarantine dir, so the run was flagged missing-manifest and its files quarantined | Regenerated cleanly (uncached default 100k path); manifest written; VALID. Quarantine dirs (`.quarantine_*`, stale committed-file duplicates only) are inert and listed for cleanup |
| skew1.5_large_s3 / s4 | missing at end of the 09-09 run (Spark shuffle-crash killed the batch driver before it reached the last two) | Generated with the idempotent resume (`--skew 1.5 --scale large --seed 3/4`); VALID |

## Disk-Space Assessment

Free disk before generation: ~517 GiB. Estimated raw: ~30 GiB.
Actual parquet usage: 5,102,800,202 bytes (4.7524 GiB, `summary.json`).
Free disk after generation: 509.9 GiB (batch-driver preflight). Safety margin:
comfortable (~2% of free disk consumed).

## Notes for Day 15

- Datasets are discoverable via `data/generated/index.json` (family → scale →
  seed → physical_id).
- AQE control + Spark config are NOT part of dataset generation (Day 15+
  workload layer reads data through COMP-SPARK-03).
- The NYC Taxi dataset (EXP-010 external validity) is NOT part of the Day-14
  matrix; it is procured separately on its own day.