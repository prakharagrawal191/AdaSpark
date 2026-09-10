# B0 Default Baseline

## Purpose

Establish the frozen Day-17 control condition: the Spark **default /
out-of-box** configuration (PLAN §17, B0 = "Spark default, out-of-box
settings, pinned, vendor reality"), measured across all five workload
families through the shared session/runner/monitoring/manifest pipeline. B0
is the *reference condition* for every later comparison. This document does
**not** interpret B0 as optimal and does not answer whether configuration
sensitivity or RL benefit exists — those belong to EXP-002 and later
experiments. This is M5: *Spark Baseline Working*.

## Configuration

Pinned in `configs/baseline_b0.yaml` (`baseline_id: B0`):

- `master: local[2]`, `driver_memory: 6g` — unchanged Day-3 frozen defaults
- `shuffle_partitions: 200` — Spark SQL out-of-box default (**not tuned**)
- `default_parallelism: null` — left to Spark (out-of-box)
- `event_log_enabled: true` — observability, not performance
- `warmup_runs: 2`, `warmup_micro_job: true`, `timeout_seconds: 300`

Distinction (Step 2): the only values reported are either **observability /
execution metadata** (app name, event-log location, warm-up policy, timeout)
or **Spark's own out-of-box settings**. No performance-tuning value is
introduced.

Configuration fingerprint (sanity anchor, from the shared config layer):
recorded in every manifest via `run_result.config_fingerprint`; all 17 runs
share the identical fingerprint (validator-enforced consistency).

## AQE Mode

**AQE OFF** — the main study uses AQE off (PLAN §7, §11) so that
pre-execution configuration selection is a well-defined problem. AQE-on
defaults are a separate comparison condition (B0′, RQ6, EXP-005b), never
part of B0. Every manifest records `aqe_mode: off` (also verified by
`scripts/validate_baseline.py`); `metrics.aqe_enabled` from the event log
concurs.

## Workload Matrix

| Family | Scale | Seeds | Reps | Runs |
|--------|-------|-------|------|------|
| F1_agg | small | {0} | 3 | 3 |
## Results

Authoritative timing = `execution_time_s` (runner, warm-up excluded).
Values below are from `results/baseline/b0_summary.json`.

| Family | Scale | n | mean (s) | median (s) | std (s) | CV | shuffle R/W (MB) | spill (MB) | task CV | stages/tasks |
|--------|-------|---|----------|------------|---------|-----|------------------|------------|---------|--------------|
| F1_agg | small | 3 | 16.57 | 16.68 | 0.25 | 0.0152 | 62.2 / 43.4 | 0 | 1.01 | 26 / 2421 |
| F2_join | small | 3 | 1.89 | 1.90 | 0.08 | 0.0397 | 0.27 / 0.18 | 0 | 2.90 | 23 / 1821 |
| F3_rdd | small | 3 | 13.74 | 13.64 | 0.36 | 0.0264 | 87.0 / 87.0 | 0 | 0.69 | 20 / 36 |
| F4_ski | small | 3 | 1.90 | 1.90 | 0.04 | 0.0214 | 0.53 / 0.38 | 0 | 2.00 | 23 / 1821 |
| F5_mixed | small | 3 | 3.08 | 3.07 | 0.02 | 0.0065 | 0.27 / 0.18 | 0 | 9.00 | 35 / 1839 |
| F2_join | medium | 1 | 13.13 | — | — | — | 316.7 / 307.2 | 0 | 1.57 | 26 / 2427 |
| F2_join | large | 1 | 17.97 | — | — | — | 931.6 / 922.0 | 0 | 1.83 | 26 / 2454 |

Notes:
- F1 aggregations show the largest shuffle (62 MB read) and the highest
  task count (2421) — expected for the multi-key aggregation.
- F3 RDD workload: shuffle read == write (~87 MB) because a single shuffle
  boundary is crossed on the 3M-lineitem dataset; only 36 tasks on a single
  stage (RDD pipeline of 1 reduceByKey).
- F5 task-duration CV ≈ 9.0 is high because one pipeline has 35 stages with
  a broad mix of short/long tasks; this is a diagnostic, not a validity
  issue.
- The medium/large spot checks confirm the pipeline scales (runtime rises
  with input size and shuffle volume grows) — calibration sanity, not a
  claim.

## Noise / Repeatability

- Per-family timing CV over 3 reps: F1 1.5% · F2 4.0% · F3 2.6% · F4 2.1% ·
  F5 0.6% — tight enough for later median-based analysis (EXP-001's formal
  CV criterion is run after Day 21/22, not claimed today).
- Result signatures: **identical across all reps** for every family
  (F1 `7f21df5d3daba03e`, F2 `8d7c822ef7e22db0`, F3 `08e48f2bef07520c`,
  F4 `319b5c2b718ee080`, F5 `565ca8e84f975493`), confirming logical
  reproducibility.
- The medium spot run used the same signature structure as the Day-15
  medium smoke (identical logical result).

## Invalid Runs

None. All 17 runs were `usable=True` with `event_log_status=COMPLETE`,
`success=True`, and validated result signatures. No outliers were removed;
no run was tuned between measurements. (The single-run smoke F2_join run
earlier in Day 17 was a harness check and is not part of this summary.)

## Interpretation

- The pipeline reliably executes **and measures** all five workloads under
  B0 with complete event logs and consistent config.
- The numbers are the **B0 control condition**, not a claim about optimal
  or RL behavior. EXP-002 will determine whether any non-default
  configuration can beat B0; later experiments compare strategies against
  this control.

## Limitations

- Sample size: only 3 reps at small plus single-spot-medium/large; this is
  calibration, not the full experimental design (5 seeds × 5 reps).
- Single machine (Windows local, 32 GB, 24 cores) with potential background
  variance; no CPU/RAM metering was captured during the batch, so exact
  system state is not reported beyond the pinned environment.
- Warm-up is per-session; cross-session variability is included in the CV.
- Spill was 0 for all runs — if later tuning increases data/executor
  memory pressure, spill metrics will become informative.
| F2_join | small | {0} | 3 | 3 |
| F3_rdd | small | {0} | 3 | 3 |
| F4_ski | small | {0} | 3 | 3 |
| F5_mixed | small | {0} | 3 | 3 |
| F2_join (scale spot) | medium, large | {0} | 1 | 2 |

**Total: 17 runs.** This is the smallest reproducible calibration set that
covers all five families plus a medium/large scale spot-check, matching the
frozen calibration intent without consuming the EXP-002 budget. The Day-3
warm-up policy (2 discarded warm-ups) is retained.

## Timing Method

- Timing from the Day-3 runner: `execution_time_s` = timed workload
  execution only (warm-up runs and session start are excluded).
- Warm-up time and total (session) time are recorded separately and never
  pooled into B0 performance statistics.
- All runs use a fresh Spark session per run; event logs are complete for
  every run (`event_log_status: COMPLETE`); `execution_time_source` =
  `runner` (authoritative) with the event-log wall clock as a diagnostic.

## Monitoring Metrics

Every manifest splits: **correctness** (validated, result signature,
columns, per-family measurements) from **performance** (execution time,
warm-up) from **monitoring** (stage/task counts, shuffle read/write bytes,
memory/disk spill, task-duration statistics/CV, event-log status, AQE
flag). Metrics come from the Day-16 parser over real complete event logs.