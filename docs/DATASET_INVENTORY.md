# Dataset Inventory

## Generator Version

`datagen-v1` (schema + generator code frozen on Day 13; batch driver
`scripts/generate_dataset_matrix.py` added Day 14).

## Schema Version

`datagen-v1` — canonical two-table schema (`orders`, `lineitem`), see
`docs/day13_data_generation.md` for field-by-field details and fingerprints.

## Families

| Family | Description (PLAN §11) | Physical skew |
|---|---|---|
| F1_agg | Aggregation | 1.0 |
| F2_join | Join | 1.0 |
| F3_rdd | RDD sort + filter + reduceByKey | 1.0 |
| F4_ski | Skewed join | 1.5 |
| F5_mixed | Mixed 3-phase | 1.0 |

## Scales

| Scale | lineitem rows | orders rows |
|---|---|---|
| small | 3,000,000 | 750,000 |
| medium | 10,000,000 | 2,500,000 |
| large | 30,000,000 | 7,500,000 |

## Seeds

{0, 1, 2, 3, 4} — {0,1,2} train, {3} validation, {3,4} test (PLAN §16/§18).

## Generation Matrix

30 physical datasets (2 skews × 3 scales × 5 seeds); 75 logical entries.
Physical ID: `skew{skew}_{scale}_s{seed}`, e.g. `skew1_large_s3`, `skew1.5_small_s0`.

## Actual Sizes

| Metric | Parquet actual |
|---|---|
| total_rows | 537,500,000 |
| total_bytes / GiB | 5,102,800,202 / 4.7524 |
| bytes_by_scale | large: 3,575,402,827 · medium: 1,178,850,441 · small: 348,547,934 |
| bytes_by_seed | s0: 1,021,010,849 · s1: 1,018,580,920 · s2: 1,021,094,847 · s3: 1,021,053,958 · s4: 1,021,060,628 |
| lineitem_bytes_by_family | F1_agg/F2_join/F3_rdd/F5_mixed: 2,532,969,340 each (shared skew-1.0 physicals) · F4_ski: 1,992,816,564 |

Per-dataset sizes are in `data/generated/index.json` under each `physical` → `tables`.
Measured guide: small ≈ 37–39 MB, medium ≈ 110–120 MB, large ≈ 330–360 MB per physical dataset.

## Checksums

FNV-1a 64-bit over canonical row content, stored per table in each
`manifest.json` (`checksum` field), plus `generation_fingerprint`
(SHA-256 over the spec identity). Same spec ⇒ same checksum.

## Generation Status

| Status | Count |
|---|---|
| VALID | 30 |
| MISSING | 0 |
| CORRUPT | 0 |

30/30 physical datasets VALID, 75/75 logical entries resolvable (`data/generated/index.json`).

## Reproduction Command

```bash
python scripts/generate_dataset_matrix.py                     # full matrix
python scripts/generate_dataset_matrix.py --plan-only         # print plan
python scripts/generate_dataset_matrix.py --scale small --seed 0 --skew 1.0
```

Idempotent: valid datasets are skipped; missing/corrupt tables are regenerated.

## Data Location

`<SPARKRL_DATA_ROOT>/generated/datasets/<physical_id>/{orders,lineitem}/`
(`SPARKRL_DATA_ROOT` defaults to `./data`; excluded from Git).
Index: `<SPARKRL_DATA_ROOT>/generated/index.json`.
Summary: `<SPARKRL_DATA_ROOT>/generated/summary.json`.

## Validation Status

Every table is validated at generation time via
`sparkrl.datagen.validate.full_validation` (row rules, skew direction,
manifest/spec/checksum consistency). Machine-readable status lives in
`index.json` / `summary.json`. Full-text check procedure:
`docs/DATASET_README.md` → "How to validate".

---

TOTALS (from actual manifests at end of Day-14 run, `data/generated/summary.json`):

- TOTAL EXPECTED: 30 physical / 75 logical
- TOTAL GENERATED: 30 physical / 75 logical
- TOTAL VALID: 30
- TOTAL FAILED: 0
- TOTAL MISSING: 0