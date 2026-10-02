# Datasets folder

This folder is the submission's dataset package. The bulk data (seeded synthetic Parquet, about
5.1 GB in 30 dataset directories, two tables each) is regenerated deterministically rather than
shipped; what is shipped here is everything needed to regenerate it and to prove the bytes match.

| Content | Purpose |
|---|---|
| `manifests/<dataset>/<table>/manifest.json` (60 files) | Per-table row count, byte count, key cardinality, Zipf skew, seed, schema and generation fingerprints, file checksum |
| `index.json`, `summary.json` | The dataset index the workload resolver reads, and its summary |
| `SHA256SUMS.txt` | SHA-256 of every file in this folder |

**Regenerate the data.** From the repository root, with the canonical environment
(`sparkrl_env311`, Python 3.11.9, PySpark 3.5.9):
`python scripts/generate_dataset_matrix.py` (generator: `src/sparkrl/datagen/`, configuration:
`configs/datagen.yaml`). Each regenerated table must reproduce its manifest's
`generation_fingerprint`, `schema_fingerprint` and `checksum`; the workload resolver refuses
data whose manifest does not match the index.

**Splits.** The train / validation / test assignment of every (family, scale, seed) cell is fixed
in code (`sparkrl.experiments.spec.split_of`) and frozen for evaluation in
`results/evaluation/test_freeze.json` (43 TEST cells, verified by `scripts/validate_day31.py`).

**External data.** The NYC-Taxi pilot (X9) used one public month,
`yellow_tripdata_2023-01.parquet` (47,673,370 bytes) from the NYC TLC trip-record site; it is
not redistributed here.

**Raw observations.** Experiment observation records (`results/experiments/*`) are covered by the
Data Availability statement and the DEC-045 deposit plan.
