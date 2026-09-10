# Day 17 Baseline Audit

Milestone M5 — B0 default baseline working.

## Planned Runs

- 5 families × small × seed 0 × 3 reps = 15 runs
- scale spot-check: F2_join × {medium, large} × seed 0 × 1 rep = 2 runs
- **Total planned: 17.**

## Completed Runs

All 17 executed via `scripts/run_baseline.py` under
`configs/baseline_b0.yaml` (B0, AQE off), one fresh Spark session per run,
2 warm-ups discarded each.

## Valid Runs

**17 / 17 usable** — every run `usable=True`, `success=True`,
`event_log_status=COMPLETE`, `validate()` passed, result signature present.

## Invalid Runs

None. (One single-run harness smoke earlier checked the runner; excluded
from the summary by design, not by outlier rule.)

## B0 Configuration

Pinned in `configs/baseline_b0.yaml`: `baseline_id: B0`, AQE off,
`local[2]`, `shuffle_partitions: 200` (Spark out-of-box), `driver_memory:
6g`, warm-up 2, timeout 300 s. All runs shared the identical
`configuration_fingerprint` (validator-enforced).

## AQE Configuration

`aqe_enabled: false` in config; every manifest `aqe_mode: off`; event-log
`spark.sql.adaptive.enabled=false` concurred. AQE-on is a separate
condition (B0′, EXP-005b), not part of B0.

## Timing Statistics

Authoritative timing = runner `execution_time_s` (warm-up excluded):

| Family | Scale | n | mean (s) | median (s) | std (s) | CV |
|--------|-------|---|----------|------------|---------|-----|
| F1_agg | small | 3 | 16.57 | 16.68 | 0.25 | 1.5% |
| F2_join | small | 3 | 1.89 | 1.90 | 0.08 | 4.0% |
| F3_rdd | small | 3 | 13.74 | 13.64 | 0.36 | 2.6% |
| F4_ski | small | 3 | 1.90 | 1.90 | 0.04 | 2.1% |
| F5_mixed | small | 3 | 3.08 | 3.07 | 0.02 | 0.6% |
| F2_join | medium | 1 | 13.13 | — | — | — |
| F2_join | large | 1 | 17.97 | — | — | — |

## Workload Results

Result signatures identical across reps per family (F1 `7f21…d03e`,
F2 `8d7c…db0`, F3 `08e4…20c`, F4 `319b…080`, F5 `565c…493`) — logical
determinism confirmed and unchanged from Day 15. Dataset fingerprints,
schema fingerprints, and workload versions recorded in every manifest.

## Noise Assessment

Timing CV across 3 reps: 0.6–4.0%. This is calibration noise, not the
formal EXP-001 CV gate (which is run after Day 21/22). Median is retained
as the robust measure for later median-based analysis (PLAN §23).

## Event-Log Completeness

17/17 event logs `COMPLETE` (LogStart + ApplicationEnd present), 0
malformed, 0 unknown-event warnings beyond tolerated types. Parsed metrics
(pipeline from Day 16) reconcile to the manifests.

## Monitoring Metrics Availability

Every manifest carries the full frozen RuntimeMetrics set: stage/task
counts, shuffle read/write bytes, memory/disk spill, task-duration
mean/median/std/CV, event-log status, AQE flag. Spill == 0 across all B0
runs (dataset fits in memory at these scales).

## Reproducibility

- Result signatures identical across 3 reps per family ✓
- Dataset fingerprints identical per (family, scale, seed) ✓
- Config fingerprint identical across all 17 runs ✓
- Median-based timing is stable within-family (CV ≤ 4%) ✓

## Issues

- None blocking. F1's window workload drives the highest task count
  (2421) and shuffle (62 MB) at small scale; F5's task-duration CV ≈ 9 is a
  diagnostic of heterogeneous stage mix, not a validity issue.
- Startup/variability: batch ran on Windows local mode with no machine
  quieting protocol; a plugged-in high-performance profile and sync-paused
  protocol are planned for formal experiments (PLAN §23).

## Readiness for EXP-002

**Yes** — the B0 measurement foundation is reliable enough to proceed to
the sensitivity grid:

- all five workloads execute and validate under the frozen B0 config;
- runtime metrics (execution time, shuffle, spill, task CV, stage/task
  counts) are extracted from complete event logs for every run;
- result/dataset/config fingerprints are reproducible; timing noise is low
  (CV ≤ 4% over 3 reps).

This says nothing about whether configuration sensitivity itself is
sufficient — that is EXP-002's question. The sensitivity grid (EXP-002,
Day 23–24) will exercise the 12-config action space on F1/F2/F3/F5 × S/M,
using B0 as the default reference.