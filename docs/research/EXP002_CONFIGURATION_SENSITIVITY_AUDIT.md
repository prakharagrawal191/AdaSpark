# EXP-002 — Configuration-Sensitivity Study (Audit)

> **Day 22 · Status: EXECUTED · Type: calibration / feasibility gate (RQ0)**
> Authority: `docs/PLAN.md` §§7, 11, 14, 17, 18, 22, 23, 27, 33, 39; `DECISIONS.md`
> DEC-007; `docs/architecture/ARCHITECTURE_FREEZE.md` (COMP-EXP-12, COMP-RL-07 ordering
> cross-reference); `docs/BASELINE_B0.md` (Day-17 B0 calibration).
>
> **This experiment does not implement, evaluate, or claim anything about reinforcement
> learning.** It measures whether Spark configuration changes produce measurable,
> repeatable differences in workload execution time on this machine — the precondition
> the frozen plan requires before any adaptive/RL stage may begin.

---

## 1. Objective

Establish whether the frozen Spark configuration knobs are sufficiently **sensitive**,
**repeatable** and **measurable** on the selected workloads to justify the later
configuration-adaptation study. This is PLAN objective **O4** ("config-sensitivity grid
scan and statistical feasibility gate") and the mitigation for PLAN risk **R2**
("Configs barely affect runtime (existential)").

EXP-002 is a **gate**, not an optimisation. It selects no configuration, tunes nothing,
and produces no policy.

## 2. Research question

> **RQ0:** How sensitive is execution time of shuffle/join-heavy Spark workloads to
> shuffle-partition and parallelism settings on single-node local-mode Spark?
> *(PLAN §3, "Days 23–24; pivot path pre-agreed if insufficient.")*

Questions explicitly **not** answered here: whether RL works, whether a learned policy
beats B0, whether Q-learning converges, whether adaptation improves performance, whether
the approach is novel. Those are EXP-004 through EXP-010.

## 3. Hypothesis under test (frozen before measurement)

> **H1 (sensitivity gate):** on shuffle/join-heavy workloads, the action space spans
> **≥10% median execution-time difference** on this hardware. *(PLAN §2)*
>
> **SC1** = H1 gate passes. **EXP-002 acceptance** (PLAN §33): "≥10% spread on ≥2
> families". **R2 pivot trigger** (PLAN §38): "EXP-002 effect <10%".

## 4. Configuration parameters

Only the parameters the frozen plan designates for this study are varied. PLAN §14
("Action Space", v1) defines the set exactly, and explicitly **rejects** the alternatives:

| Parameter | Varied | Authority |
|---|---|---|
| `spark.sql.shuffle.partitions` | **yes** | PLAN §14 v1 |
| execution parallelism — `spark.master` = `local[N]` **and** `spark.default.parallelism` = N | **yes** (coupled, one factor) | PLAN §14 v1 |
| `spark.driver.memory` | no — frozen control at `6g` | PLAN §14: executor/driver memory rejected (OOM risk on fixed hardware) |
| `spark.sql.autoBroadcastJoinThreshold` | no | PLAN §14: v2 / ablation-only |
| caching strategy | no | PLAN §14: v2 / ablation-only |
| dynamic allocation | no | PLAN §14: off in local mode |
| `spark.sql.adaptive.enabled` (AQE) | no — frozen **OFF** | PLAN §7, §11; AQE-on is EXP-005b |

The varied set is asserted in code: `sparkrl.experiments.grid.VARIED_PARAMETERS`, and the
validator (check 05) proves every candidate differs from B0 **only** within that set.

## 5. Configuration levels and grid

PLAN §14: `shuffle.partitions ∈ {16, 32, 64, 128}` × `parallelism ∈ {2, 4, 8}` = **12
configurations**, plus **B0** as the reference = **13 grid points**.

Enumeration order is frozen as `grid_index = parallelism_index × 4 + shuffle_index`.
This is load-bearing: `ARCHITECTURE_FREEZE` (COMP-RL-07) states the pre-authorised Plan-B
4-configuration subset is "indices {0,3,6,9} of the same table"; under this ordering those
indices are `G-p2-sp16`, `G-p2-sp128`, `G-p4-sp64`, `G-p8-sp32` — a subset spanning both
dimensions. Recording the ordering is a cross-reference to that frozen contract; **no
action mapper, agent or policy is implemented.**

| idx | name | `local[N]` | `default.parallelism` | `shuffle.partitions` |
|---|---|---|---|---|
| ref | `B0` | `local[2]` | unset (Spark default) | 200 |
| 0 | `G-p2-sp16` | `local[2]` | 2 | 16 |
| 1 | `G-p2-sp32` | `local[2]` | 2 | 32 |
| 2 | `G-p2-sp64` | `local[2]` | 2 | 64 |
| 3 | `G-p2-sp128` | `local[2]` | 2 | 128 |
| 4 | `G-p4-sp16` | `local[4]` | 4 | 16 |
| 5 | `G-p4-sp32` | `local[4]` | 4 | 32 |
| 6 | `G-p4-sp64` | `local[4]` | 4 | 64 |
| 7 | `G-p4-sp128` | `local[4]` | 4 | 128 |
| 8 | `G-p8-sp16` | `local[8]` | 8 | 16 |
| 9 | `G-p8-sp32` | `local[8]` | 8 | 32 |
| 10 | `G-p8-sp64` | `local[8]` | 8 | 64 |
| 11 | `G-p8-sp128` | `local[8]` | 8 | 128 |

Every point carries a deterministic name, a SHA-256 **configuration fingerprint** over its
canonical knob dict, and an explicit `delta_from_b0`. Names and fingerprints are unique
(validator check 02). The grid is version-controlled in `experiments/exp002.yaml` and
constructed by `src/sparkrl/experiments/grid.py`; the whole ordered grid also has a
`grid_fingerprint` recorded in every run manifest.

**No random configuration generation, no automated optimisation, no adaptive search.**

## 6. B0 definition (immutable)

`configs/baseline_b0.yaml`, unchanged by this work:

```
master: local[2] · driver_memory: 6g · shuffle_partitions: 200
default_parallelism: null · aqe_enabled: false
warmup_runs: 2 · warmup_micro_job: true · timeout: 300 s
```

B0 is **not** one of the 12 candidates — `shuffle_partitions=200` is outside the level set
and `default_parallelism` is left to Spark — so there is no identity collision. It is
included as the 13th grid point purely as the measured reference. `assert_b0_unchanged()`
re-verifies the loaded configuration against the frozen definition at the start of every
run pass, and validator check 03 asserts it independently.

B0 medians also constitute the **T_ref calibration** that PLAN §§15/33 assign to
EXP-002/003. T_ref is emitted as data only; **no reward is computed anywhere.**

## 7. Workload scope

`F1_agg`, `F2_join`, `F3_rdd`, `F5_mixed` — exactly PLAN §33's "12-config grid ×
F1,F2,F3,F5 × S,M".

`F4_ski` is **deliberately excluded**: PLAN §18 reserves the skewed family as an *unseen
test family*. Running it here would leak the test set.

Workload SQL/transformations, the dataset generator, dataset schema, dataset fingerprints,
event-log semantics and parser semantics are **unmodified**. The workloads are used through
the existing registry (`sparkrl.workloads.registry.REGISTRY`) and resolver.

## 8. Scale scope

`small` and `medium`. `large` is **deliberately excluded** — PLAN §18 makes scale L part of
the frozen test set.

## 9. Seeds and repetitions

- **Seed 0** — a TRAIN seed (PLAN §18 train seeds = {0,1,2}).
- **2 measured repetitions** per (family, scale, configuration) cell.

PLAN §33 budgets EXP-002 at **192 runs**, which decomposes uniquely over the 12-config grid
as `12 × 4 families × 2 scales × 2`. The plan fixes the run count but not whether the
factor 2 is repetitions or seeds. This study reads it as **2 repetitions at one train
seed**, so that a configuration effect is never confounded with dataset-instance variation
— which is precisely what RQ0 asks. Cross-seed robustness is a different question and is
**not** claimed by EXP-002. Including the B0 reference adds `4 × 2 × 2 = 16` runs.

**Planned total: 208 runs** (192 grid + 16 reference).

Warm-up policy is identical to B0: `warmup_runs = 2` plus the session-start micro-job.
**Warm-up executions are run, discarded, and never measured**; only the timed execution
contributes to `execution_time_s`.

## 10. Run-order method

PLAN prescribes no run order for EXP-002, so a **randomized complete block design** is used
and documented:

- one block = `(family, scale, repetition)`;
- within a block every one of the 13 configurations appears **exactly once**, in an order
  drawn from `random.Random(f"{order_seed}|{block_id}")` with `order_seed = 20022`
  recorded in the spec;
- blocks run scale-major, so an interrupted queue still yields complete coverage at the
  smaller scale.

This prevents machine drift over a block from systematically favouring any configuration,
while remaining **exactly reproducible**: the full ordered plan is persisted in
`results/experiments/exp-002/spec.json`. Configuration identity never depends on execution
order (validator check 07).

## 11. Train / validation / test separation

PLAN §18, enforced in code by `sparkrl.experiments.spec.split_of()` /
`assert_train_only()`:

| Split | Definition | EXP-002 use |
|---|---|---|
| TRAIN | {F1,F2,F3,F5} × {small,medium} × seeds {0,1,2} | **the only cells used** |
| VALIDATION | same families/scales × seed {3} | untouched (belongs to EXP-003) |
| TEST | scale `large` (any family) **or** family `F4_ski` **or** seed {4} | **frozen, untouched** |

Test membership dominates: any cell touching the unseen family, unseen scale, or unseen
seed is TEST regardless of its other coordinates. `assert_train_only()` raises before a
non-train cell can execute, `ExperimentSpec.validate()` rejects a spec that declares one,
and validator checks 11–12 re-verify over every stored record.

**EXP-002 selects nothing**, so no model-selection stage is invented and the validation
split is not used. No test metric influences anything here.

## 12. Test-set freeze status

**FROZEN and untouched.** PLAN §7/§18 freeze the test set until Day 31. This study never
reads it; the freeze is enforced at three independent layers (spec validation, pre-run
guard, post-hoc validator scan) rather than by convention alone.

## 13. Measurement semantics

The authoritative metric is **`execution_time_s`**, the Day-3 runner clock measuring only
`workload.run()` — session startup and warm-up excluded. It is **unchanged and never
redefined**.

Explicitly **not** used as the performance metric: runner total time, warm-up time,
event-log wall clock, parser time, manifest-write time, orchestration overhead. The
event-log wall clock remains only a flagged fallback (`execution_time_source`) in the
frozen Day-16 contract and is not exercised as a primary measurement here.

## 14. Metrics

The existing Day-19 `RunMetrics` schema (`run_metrics/v1`) is used unchanged — identity,
execution, event-log metrics, optional psutil monitoring, provenance. No metric is invented
and **missing values remain `None`, never coerced to 0** (asserted by the frozen
`validate_run_metrics` invariants, re-checked by validator check 09).

Additionally recorded per run, as an EXP-002 orchestration concern: the **read-back applied
Spark settings** (`provenance.applied_settings`) and any `applied_mismatches`. This matters
scientifically — a configuration that silently failed to apply would be indistinguishable
from insensitivity — so a run whose settings did not take effect is forced invalid.

## 15. Valid-run definition

A measured observation is **VALID** iff the existing Day-19 `usable` rule holds:

```
success  AND  execution_time_s present  AND  event_log_status == COMPLETE
         AND  result_signature present
```

`event_log_status == COMPLETE` requires both `SparkListenerLogStart` and
`SparkListenerApplicationEnd` (Day-16 parser contract). A run is additionally forced
invalid if its configuration did not verifiably apply.

Everything else is recorded explicitly as `FAILED` (error/timeout) or `INCOMPLETE`
(ran, but provenance incomplete) and is **never counted as a normal measurement**. No
failure is dropped: each keeps its own immutable manifest, and every attempt — including
superseded ones — is appended to `results/experiments/exp-002/attempts.jsonl`.

## 16. Statistical analysis

Per `(family, scale, configuration)`: n, median, mean, sample SD (ddof=1), CV, min, max of
`execution_time_s`; and B0-relative absolute and relative differences.

Per `(family, scale)` panel: configuration spread with and without the reference; pooled
within-configuration CV (the run-to-run noise estimate); per-repetition spread; and the
Spearman rank agreement of the configuration ordering between repetitions.

**No significance test is run.** With 2 repetitions per cell the assumptions of a paired
rank test across configurations are not met, and a test run purely for decoration would
misrepresent the evidence. Repeatability is reported directly instead. PLAN §22's Wilcoxon
/ Cliff's δ / Holm apparatus belongs to EXP-005, where the design supports it.

The analysis is a pure function of the stored manifests
(`src/sparkrl/analysis/exp002.py`, `ANALYSIS_VERSION = exp002-analysis/v1`): re-running it
on unchanged inputs reproduces byte-identical output (validator check 14), and the stored
`gate.json` is re-derived and compared (validator check 13).

## 17. Sensitivity criterion

Taken from the frozen plan; **fixed before measurement** and recorded in
`experiments/exp002.yaml`:

```
spread_relative(panel) = (max_c median_c − min_c median_c) / min_c median_c
                          over c ∈ the 12 VARIED configurations
```

The scope is `varied_only` because H1 speaks about *"the action space"* — B0 is the
reference, not a candidate. The including-reference spread is computed and reported too.

```
panel SENSITIVE  iff  panel complete (every configuration has ≥1 valid observation)
                 AND  spread_relative ≥ 0.10           ← PLAN H1, verbatim
                 AND  spread_relative >  pooled within-configuration CV   ← noise guard

family SENSITIVE iff sensitive at ≥1 of its measured scales   (family_rule = any_scale)
```

The **10% threshold and the ≥2-family requirement are the plan's own numbers** (PLAN §2 H1,
§33 acceptance, §38 R2). They were not invented here and were not adjusted after seeing
results.

The **noise guard** is the one addition, and it makes the gate *harder*, never easier: a
spread smaller than ordinary run-to-run variation is not evidence of a configuration
effect. PLAN risk R3 / EXP-001 set the project's noise criterion at CV ≤ 10%, but EXP-001
was never executed (§23 below), so the noise band is estimated from EXP-002's own
within-configuration repetitions and reported explicitly rather than assumed.

## 18. Gate definition

```
GATE PASSES iff n_families_sensitive ≥ 2        ← PLAN §33 acceptance
```

The gate is a deterministic function of the stored results: identical manifests always
produce an identical verdict, and the verdict is written machine-readably to
`results/experiments/exp-002/analysis/gate.json` (`exp002-gate/v1`) alongside the
human-readable `summary.md`. `scripts/analyze_exp002.py` refuses to silently overwrite an
existing gate result whose verdict differs.

<!-- GENERATED-RESULTS-BEGIN -->

## 19. Raw results summary

Generated from `results/experiments/exp-002/analysis/gate.json` (`exp002-gate/v1`, analysis `exp002-analysis/v1`, code `d8e02f7-dirty`).

| quantity | value |
|---|---|
| planned runs | 208 |
| run manifests found | 208 |
| **valid** observations | **189** |
| invalid / failed observations | 19 |
| planned but not executed | 0 |
| unexpected (not in plan) | 0 |
| spec fingerprint | `9fb5cb51f74fe37f` |
| grid fingerprint | `97d70dc18a1d5369` |
| AQE | OFF |
| metric | `execution_time_s` |

Invalid breakdown by status: `{'FAILED': 19}`

### Invalid / failed observations (recorded, never dropped)

| run id | status | event log | reason |
|---|---|---|---|
| `exp002-f3-rdd-medium-s0-b0-r1` | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: Job aborted due to... |
| `exp002-f3-rdd-medium-s0-b0-r2` | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: Job aborted due to... |
| `exp002-f3-rdd-medium-s0-g-p2-sp128-r1` | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: Job aborted due to... |
| `exp002-f3-rdd-medium-s0-g-p2-sp128-r2` | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: Job aborted due to... |
| `exp002-f3-rdd-medium-s0-g-p2-sp16-r1` | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: Job aborted due to... |
| `exp002-f3-rdd-medium-s0-g-p2-sp16-r2` | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: Job aborted due to... |
| `exp002-f3-rdd-medium-s0-g-p2-sp32-r1` | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: Job aborted due to... |
| `exp002-f3-rdd-medium-s0-g-p2-sp32-r2` | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: Job aborted due to... |
| `exp002-f3-rdd-medium-s0-g-p2-sp64-r1` | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: Job aborted due to... |
| `exp002-f3-rdd-medium-s0-g-p2-sp64-r2` | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: Job aborted due to... |
| `exp002-f3-rdd-medium-s0-g-p4-sp128-r1` | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: Job aborted due to... |
| `exp002-f3-rdd-medium-s0-g-p4-sp128-r2` | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: Job aborted due to... |
| `exp002-f3-rdd-medium-s0-g-p4-sp16-r1` | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: Job aborted due to... |
| `exp002-f3-rdd-medium-s0-g-p4-sp16-r2` | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: Job aborted due to... |
| `exp002-f3-rdd-medium-s0-g-p4-sp32-r1` | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: Job aborted due to... |
| `exp002-f3-rdd-medium-s0-g-p4-sp32-r2` | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: Job aborted due to... |
| `exp002-f3-rdd-medium-s0-g-p4-sp64-r1` | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: Job aborted due to... |
| `exp002-f3-rdd-medium-s0-g-p4-sp64-r2` | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: Job aborted due to... |
| `exp002-f3-rdd-small-s0-g-p4-sp16-r1` | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: Job aborted due to... |

### T_ref calibration (B0 medians, PLAN §§15/33)

Emitted as calibration data only. **No reward is computed anywhere in this work.**

| family \| scale | T_ref (s) |
|---|---|
| F1_agg|medium | 36.670 |
| F1_agg|small | 22.347 |
| F2_join|medium | 16.127 |
| F2_join|small | 2.215 |
| F3_rdd|medium | n/a |
| F3_rdd|small | 25.109 |
| F5_mixed|medium | 32.759 |
| F5_mixed|small | 3.904 |

## 20. Aggregate results

Per-panel summary. *Spread* is the relative range of per-configuration median `execution_time_s` across the 12 varied configurations; *noise* is the pooled within-configuration CV; *ρ* is the Spearman rank agreement of the configuration ordering between the two repetitions.

| family | scale | complete | valid | invalid | spread (varied) | spread (incl. B0) | noise CV | ρ | sensitive |
|---|---|---|---|---|---|---|---|---|---|
| F1_agg | small | yes | 26 | 0 | 497.9% | 966.5% | 16.45% | +0.97 | **YES** |
| F1_agg | medium | yes | 26 | 0 | 366.9% | 685.3% | 26.53% | +0.97 | **YES** |
| F2_join | small | yes | 26 | 0 | 210.0% | 310.7% | 10.70% | +0.95 | **YES** |
| F2_join | medium | yes | 26 | 0 | 583.1% | 1010.0% | 18.29% | +0.98 | **YES** |
| F3_rdd | small | yes | 25 | 1 | 158.7% | 158.7% | 30.07% | +0.55 | **YES** |
| F3_rdd | medium | **NO** | 8 | 18 | 49.9% | 49.9% | 40.69% | +0.40 | no |
| F5_mixed | small | yes | 26 | 0 | 183.9% | 237.5% | 25.24% | +0.98 | **YES** |
| F5_mixed | medium | yes | 26 | 0 | 424.7% | 693.8% | 28.92% | +0.90 | **YES** |

### F1_agg / small

B0 median (= T_ref) = **22.347 s**. Fastest varied configuration: `G-p8-sp16` at 2.095 s; slowest: `G-p2-sp128` at 12.528 s.

| configuration | idx | n | median (s) | mean (s) | SD (s) | CV | Δ vs B0 (s) | Δ vs B0 (%) |
|---|---|---|---|---|---|---|---|---|
| `B0` | ref | 2 | 22.347 | 22.347 | 1.830 | 0.082 | +0.000 | +0.0% |
| `G-p2-sp16` | 0 | 2 | 2.587 | 2.587 | 0.056 | 0.022 | -19.760 | -88.4% |
| `G-p2-sp32` | 1 | 2 | 3.439 | 3.439 | 0.396 | 0.115 | -18.908 | -84.6% |
| `G-p2-sp64` | 2 | 2 | 6.042 | 6.042 | 1.110 | 0.184 | -16.305 | -73.0% |
| `G-p2-sp128` | 3 | 2 | 12.528 | 12.528 | 0.932 | 0.074 | -9.819 | -43.9% |
| `G-p4-sp16` | 4 | 2 | 2.146 | 2.146 | 0.175 | 0.082 | -20.202 | -90.4% |
| `G-p4-sp32` | 5 | 2 | 2.712 | 2.712 | 0.328 | 0.121 | -19.636 | -87.9% |
| `G-p4-sp64` | 6 | 2 | 4.003 | 4.003 | 0.222 | 0.055 | -18.345 | -82.1% |
| `G-p4-sp128` | 7 | 2 | 8.860 | 8.860 | 0.446 | 0.050 | -13.487 | -60.4% |
| `G-p8-sp16` | 8 | 2 | 2.095 | 2.095 | 0.257 | 0.122 | -20.252 | -90.6% |
| `G-p8-sp32` | 9 | 2 | 2.310 | 2.310 | 0.078 | 0.034 | -20.037 | -89.7% |
| `G-p8-sp64` | 10 | 2 | 3.853 | 3.853 | 0.478 | 0.124 | -18.494 | -82.8% |
| `G-p8-sp128` | 11 | 2 | 8.926 | 8.926 | 2.245 | 0.251 | -13.422 | -60.1% |

Per-repetition spread — rep 1: 481.1%; rep 2: 520.2%.

- spread 4.9790 >= 0.10 and exceeds pooled within-configuration noise 0.1645

### F1_agg / medium

B0 median (= T_ref) = **36.670 s**. Fastest varied configuration: `G-p8-sp32` at 4.669 s; slowest: `G-p2-sp128` at 21.800 s.

| configuration | idx | n | median (s) | mean (s) | SD (s) | CV | Δ vs B0 (s) | Δ vs B0 (%) |
|---|---|---|---|---|---|---|---|---|
| `B0` | ref | 2 | 36.670 | 36.670 | 9.969 | 0.272 | +0.000 | +0.0% |
| `G-p2-sp16` | 0 | 2 | 6.325 | 6.325 | 0.643 | 0.102 | -30.345 | -82.8% |
| `G-p2-sp32` | 1 | 2 | 8.325 | 8.325 | 2.361 | 0.284 | -28.345 | -77.3% |
| `G-p2-sp64` | 2 | 2 | 10.112 | 10.112 | 2.198 | 0.217 | -26.558 | -72.4% |
| `G-p2-sp128` | 3 | 2 | 21.800 | 21.800 | 6.350 | 0.291 | -14.870 | -40.6% |
| `G-p4-sp16` | 4 | 2 | 5.777 | 5.777 | 1.390 | 0.241 | -30.893 | -84.2% |
| `G-p4-sp32` | 5 | 2 | 5.297 | 5.297 | 0.679 | 0.128 | -31.372 | -85.6% |
| `G-p4-sp64` | 6 | 2 | 7.453 | 7.453 | 1.202 | 0.161 | -29.216 | -79.7% |
| `G-p4-sp128` | 7 | 2 | 13.633 | 13.633 | 2.430 | 0.178 | -23.037 | -62.8% |
| `G-p8-sp16` | 8 | 2 | 4.692 | 4.692 | 1.084 | 0.231 | -31.978 | -87.2% |
| `G-p8-sp32` | 9 | 2 | 4.669 | 4.669 | 0.255 | 0.055 | -32.000 | -87.3% |
| `G-p8-sp64` | 10 | 2 | 5.893 | 5.893 | 0.756 | 0.128 | -30.776 | -83.9% |
| `G-p8-sp128` | 11 | 2 | 11.340 | 11.340 | 1.537 | 0.136 | -25.330 | -69.1% |

Per-repetition spread — rep 1: 340.9%; rep 2: 442.1%.

- spread 3.6687 >= 0.10 and exceeds pooled within-configuration noise 0.2653

### F2_join / small

B0 median (= T_ref) = **2.215 s**. Fastest varied configuration: `G-p8-sp16` at 0.539 s; slowest: `G-p2-sp128` at 1.672 s.

| configuration | idx | n | median (s) | mean (s) | SD (s) | CV | Δ vs B0 (s) | Δ vs B0 (%) |
|---|---|---|---|---|---|---|---|---|
| `B0` | ref | 2 | 2.215 | 2.215 | 0.161 | 0.073 | +0.000 | +0.0% |
| `G-p2-sp16` | 0 | 2 | 0.748 | 0.748 | 0.026 | 0.034 | -1.467 | -66.2% |
| `G-p2-sp32` | 1 | 2 | 0.899 | 0.899 | 0.065 | 0.072 | -1.316 | -59.4% |
| `G-p2-sp64` | 2 | 2 | 1.186 | 1.186 | 0.118 | 0.099 | -1.028 | -46.4% |
| `G-p2-sp128` | 3 | 2 | 1.672 | 1.672 | 0.165 | 0.099 | -0.543 | -24.5% |
| `G-p4-sp16` | 4 | 2 | 0.598 | 0.598 | 0.011 | 0.019 | -1.616 | -73.0% |
| `G-p4-sp32` | 5 | 2 | 0.743 | 0.743 | 0.013 | 0.018 | -1.471 | -66.4% |
| `G-p4-sp64` | 6 | 2 | 0.871 | 0.871 | 0.026 | 0.030 | -1.344 | -60.7% |
| `G-p4-sp128` | 7 | 2 | 1.173 | 1.173 | 0.055 | 0.047 | -1.041 | -47.0% |
| `G-p8-sp16` | 8 | 2 | 0.539 | 0.539 | 0.031 | 0.057 | -1.675 | -75.7% |
| `G-p8-sp32` | 9 | 2 | 0.586 | 0.586 | 0.018 | 0.031 | -1.629 | -73.6% |
| `G-p8-sp64` | 10 | 2 | 0.791 | 0.791 | 0.069 | 0.087 | -1.424 | -64.3% |
| `G-p8-sp128` | 11 | 2 | 1.143 | 1.143 | 0.242 | 0.212 | -1.071 | -48.4% |

Per-repetition spread — rep 1: 218.9%; rep 2: 200.5%.

- spread 2.1004 >= 0.10 and exceeds pooled within-configuration noise 0.1070

### F2_join / medium

B0 median (= T_ref) = **16.127 s**. Fastest varied configuration: `G-p8-sp16` at 1.453 s; slowest: `G-p2-sp128` at 9.926 s.

| configuration | idx | n | median (s) | mean (s) | SD (s) | CV | Δ vs B0 (s) | Δ vs B0 (%) |
|---|---|---|---|---|---|---|---|---|
| `B0` | ref | 2 | 16.127 | 16.127 | 1.928 | 0.120 | +0.000 | +0.0% |
| `G-p2-sp16` | 0 | 2 | 3.511 | 3.511 | 0.488 | 0.139 | -12.616 | -78.2% |
| `G-p2-sp32` | 1 | 2 | 3.594 | 3.594 | 0.292 | 0.081 | -12.533 | -77.7% |
| `G-p2-sp64` | 2 | 2 | 4.977 | 4.977 | 0.157 | 0.032 | -11.149 | -69.1% |
| `G-p2-sp128` | 3 | 2 | 9.926 | 9.926 | 0.686 | 0.069 | -6.201 | -38.5% |
| `G-p4-sp16` | 4 | 2 | 2.026 | 2.026 | 0.419 | 0.207 | -14.101 | -87.4% |
| `G-p4-sp32` | 5 | 2 | 2.244 | 2.244 | 0.137 | 0.061 | -13.883 | -86.1% |
| `G-p4-sp64` | 6 | 2 | 2.909 | 2.909 | 0.290 | 0.100 | -13.218 | -82.0% |
| `G-p4-sp128` | 7 | 2 | 6.083 | 6.083 | 0.990 | 0.163 | -10.044 | -62.3% |
| `G-p8-sp16` | 8 | 2 | 1.453 | 1.453 | 0.170 | 0.117 | -14.674 | -91.0% |
| `G-p8-sp32` | 9 | 2 | 1.626 | 1.626 | 0.314 | 0.193 | -14.501 | -89.9% |
| `G-p8-sp64` | 10 | 2 | 2.443 | 2.443 | 0.526 | 0.215 | -13.684 | -84.9% |
| `G-p8-sp128` | 11 | 2 | 5.150 | 5.150 | 1.844 | 0.358 | -10.977 | -68.1% |

Per-repetition spread — rep 1: 608.3%; rep 2: 561.8%.

- spread 5.8315 >= 0.10 and exceeds pooled within-configuration noise 0.1829

### F3_rdd / small

B0 median (= T_ref) = **25.109 s**. Fastest varied configuration: `G-p4-sp128` at 12.404 s; slowest: `G-p8-sp32` at 32.093 s.

| configuration | idx | n | median (s) | mean (s) | SD (s) | CV | Δ vs B0 (s) | Δ vs B0 (%) |
|---|---|---|---|---|---|---|---|---|
| `B0` | ref | 2 | 25.109 | 25.109 | 16.876 | 0.672 | +0.000 | +0.0% |
| `G-p2-sp16` | 0 | 2 | 13.489 | 13.489 | 0.954 | 0.071 | -11.620 | -46.3% |
| `G-p2-sp32` | 1 | 2 | 16.217 | 16.217 | 3.014 | 0.186 | -8.892 | -35.4% |
| `G-p2-sp64` | 2 | 2 | 14.299 | 14.299 | 1.669 | 0.117 | -10.811 | -43.1% |
| `G-p2-sp128` | 3 | 2 | 15.461 | 15.461 | 1.600 | 0.103 | -9.648 | -38.4% |
| `G-p4-sp16` | 4 | 1 | 12.645 | 12.645 | n/a | n/a | -12.465 | -49.6% |
| `G-p4-sp32` | 5 | 2 | 12.616 | 12.616 | 2.022 | 0.160 | -12.493 | -49.8% |
| `G-p4-sp64` | 6 | 2 | 13.926 | 13.926 | 1.875 | 0.135 | -11.184 | -44.5% |
| `G-p4-sp128` | 7 | 2 | 12.404 | 12.404 | 0.547 | 0.044 | -12.705 | -50.6% |
| `G-p8-sp16` | 8 | 2 | 16.411 | 16.411 | 0.754 | 0.046 | -8.698 | -34.6% |
| `G-p8-sp32` | 9 | 2 | 32.093 | 32.093 | 15.407 | 0.480 | +6.984 | +27.8% |
| `G-p8-sp64` | 10 | 2 | 17.178 | 17.178 | 2.451 | 0.143 | -7.931 | -31.6% |
| `G-p8-sp128` | 11 | 2 | 16.571 | 16.571 | 1.011 | 0.061 | -8.538 | -34.0% |

Per-repetition spread — rep 1: 241.2%; rep 2: 89.5%.

- spread 1.5873 >= 0.10 and exceeds pooled within-configuration noise 0.3007

### F3_rdd / medium

B0 median (= T_ref) = **n/a s**. Fastest varied configuration: `G-p8-sp128` at 25.450 s; slowest: `G-p8-sp32` at 38.157 s.

| configuration | idx | n | median (s) | mean (s) | SD (s) | CV | Δ vs B0 (s) | Δ vs B0 (%) |
|---|---|---|---|---|---|---|---|---|
| `B0` | ref | 0 | n/a | n/a | n/a | n/a | n/a | n/a |
| `G-p2-sp16` | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a |
| `G-p2-sp32` | 1 | 0 | n/a | n/a | n/a | n/a | n/a | n/a |
| `G-p2-sp64` | 2 | 0 | n/a | n/a | n/a | n/a | n/a | n/a |
| `G-p2-sp128` | 3 | 0 | n/a | n/a | n/a | n/a | n/a | n/a |
| `G-p4-sp16` | 4 | 0 | n/a | n/a | n/a | n/a | n/a | n/a |
| `G-p4-sp32` | 5 | 0 | n/a | n/a | n/a | n/a | n/a | n/a |
| `G-p4-sp64` | 6 | 0 | n/a | n/a | n/a | n/a | n/a | n/a |
| `G-p4-sp128` | 7 | 0 | n/a | n/a | n/a | n/a | n/a | n/a |
| `G-p8-sp16` | 8 | 2 | 37.225 | 37.225 | 15.777 | 0.424 | n/a | n/a |
| `G-p8-sp32` | 9 | 2 | 38.157 | 38.157 | 19.960 | 0.523 | n/a | n/a |
| `G-p8-sp64` | 10 | 2 | 29.194 | 29.194 | 6.111 | 0.209 | n/a | n/a |
| `G-p8-sp128` | 11 | 2 | 25.450 | 25.450 | 3.876 | 0.152 | n/a | n/a |

Per-repetition spread — rep 1: 14.8%; rep 2: 85.4%.

- panel incomplete: 9 configuration(s) without 1 valid observation(s): ['B0', 'G-p2-sp16', 'G-p2-sp32', 'G-p2-sp64', 'G-p2-sp128', 'G-p4-sp16', 'G-p4-sp32', 'G-p4-sp64', 'G-p4-sp128']

### F5_mixed / small

B0 median (= T_ref) = **3.904 s**. Fastest varied configuration: `G-p8-sp16` at 1.157 s; slowest: `G-p2-sp128` at 3.284 s.

| configuration | idx | n | median (s) | mean (s) | SD (s) | CV | Δ vs B0 (s) | Δ vs B0 (%) |
|---|---|---|---|---|---|---|---|---|
| `B0` | ref | 2 | 3.904 | 3.904 | 1.099 | 0.281 | +0.000 | +0.0% |
| `G-p2-sp16` | 0 | 2 | 2.298 | 2.298 | 0.414 | 0.180 | -1.605 | -41.1% |
| `G-p2-sp32` | 1 | 2 | 2.458 | 2.458 | 0.598 | 0.243 | -1.446 | -37.0% |
| `G-p2-sp64` | 2 | 2 | 2.607 | 2.607 | 0.544 | 0.209 | -1.297 | -33.2% |
| `G-p2-sp128` | 3 | 2 | 3.284 | 3.284 | 0.895 | 0.273 | -0.620 | -15.9% |
| `G-p4-sp16` | 4 | 2 | 1.522 | 1.522 | 0.350 | 0.230 | -2.381 | -61.0% |
| `G-p4-sp32` | 5 | 2 | 1.683 | 1.683 | 0.346 | 0.206 | -2.221 | -56.9% |
| `G-p4-sp64` | 6 | 2 | 1.774 | 1.774 | 0.447 | 0.252 | -2.130 | -54.6% |
| `G-p4-sp128` | 7 | 2 | 2.081 | 2.081 | 0.532 | 0.255 | -1.823 | -46.7% |
| `G-p8-sp16` | 8 | 2 | 1.157 | 1.157 | 0.267 | 0.231 | -2.747 | -70.4% |
| `G-p8-sp32` | 9 | 2 | 1.238 | 1.238 | 0.398 | 0.321 | -2.665 | -68.3% |
| `G-p8-sp64` | 10 | 2 | 1.220 | 1.220 | 0.273 | 0.224 | -2.683 | -68.7% |
| `G-p8-sp128` | 11 | 2 | 1.488 | 1.488 | 0.327 | 0.220 | -2.416 | -61.9% |

Per-repetition spread — rep 1: 191.1%; rep 2: 177.0%.

- spread 1.8391 >= 0.10 and exceeds pooled within-configuration noise 0.2524

### F5_mixed / medium

B0 median (= T_ref) = **32.759 s**. Fastest varied configuration: `G-p8-sp32` at 4.127 s; slowest: `G-p2-sp128` at 21.654 s.

| configuration | idx | n | median (s) | mean (s) | SD (s) | CV | Δ vs B0 (s) | Δ vs B0 (%) |
|---|---|---|---|---|---|---|---|---|
| `B0` | ref | 2 | 32.759 | 32.759 | 10.876 | 0.332 | +0.000 | +0.0% |
| `G-p2-sp16` | 0 | 2 | 11.400 | 11.400 | 4.335 | 0.380 | -21.360 | -65.2% |
| `G-p2-sp32` | 1 | 2 | 11.216 | 11.216 | 3.183 | 0.284 | -21.543 | -65.8% |
| `G-p2-sp64` | 2 | 2 | 10.648 | 10.648 | 0.725 | 0.068 | -22.111 | -67.5% |
| `G-p2-sp128` | 3 | 2 | 21.654 | 21.654 | 6.265 | 0.289 | -11.105 | -33.9% |
| `G-p4-sp16` | 4 | 2 | 5.297 | 5.297 | 0.248 | 0.047 | -27.463 | -83.8% |
| `G-p4-sp32` | 5 | 2 | 6.310 | 6.310 | 0.917 | 0.145 | -26.450 | -80.7% |
| `G-p4-sp64` | 6 | 2 | 6.252 | 6.252 | 0.056 | 0.009 | -26.507 | -80.9% |
| `G-p4-sp128` | 7 | 2 | 10.786 | 10.786 | 1.186 | 0.110 | -21.973 | -67.1% |
| `G-p8-sp16` | 8 | 2 | 4.833 | 4.833 | 1.620 | 0.335 | -27.927 | -85.2% |
| `G-p8-sp32` | 9 | 2 | 4.127 | 4.127 | 0.662 | 0.160 | -28.632 | -87.4% |
| `G-p8-sp64` | 10 | 2 | 4.475 | 4.475 | 0.869 | 0.194 | -28.284 | -86.3% |
| `G-p8-sp128` | 11 | 2 | 7.896 | 7.896 | 1.357 | 0.172 | -24.863 | -75.9% |

Per-repetition spread — rep 1: 370.7%; rep 2: 467.7%.

- spread 4.2469 >= 0.10 and exceeds pooled within-configuration noise 0.2892

## 21. PASS / FAIL determination

Criterion, fixed before measurement (PLAN H1 / SC1 / §33 / R2):

```
metric                : execution_time_s (median)
scope                 : varied_only
min relative spread   : 0.10
noise rule            : spread_must_exceed_pooled_within_config_cv
family rule           : any_scale
min families          : 2
complete panel needed : True
```

| family | sensitive | sensitive scales | spread by scale |
|---|---|---|---|
| F1_agg | **YES** | small, medium | medium: 366.9%; small: 497.9% |
| F2_join | **YES** | small, medium | medium: 583.1%; small: 210.0% |
| F3_rdd | **YES** | small | medium: 49.9%; small: 158.7% |
| F5_mixed | **YES** | small, medium | medium: 424.7%; small: 183.9% |

Families meeting the criterion: **4** (required: 2).

### EXP-002 SENSITIVITY GATE: **PASS**

- 4 workload families (F1_agg, F2_join, F3_rdd, F5_mixed) show a configuration spread of at least 10% in median execution_time_s that also exceeds pooled within-configuration noise; the criterion requires 2.
- incomplete panels (not evaluable as sensitive): F3_rdd/medium

This verdict is a deterministic function of the stored run manifests: re-running `scripts/analyze_exp002.py` on unchanged inputs reproduces it byte-for-byte, and `scripts/validate_exp002.py` re-derives and compares it independently.

<!-- GENERATED-RESULTS-END -->

## 22. Threats and limitations

### 22.1 Measurement defects found during execution, and corrected

Two defects were found **while the first execution pass was collecting data**. Both were
detected by an adversarial review of the runner against the stored manifests, and both
invalidate measurements rather than merely being code smells. The entire first pass
(37 manifests) was therefore **discarded before any analysis**, the defects were fixed,
and the complete design was re-run from scratch. The discarded manifests are retained
with their explanation in `results/experiments/exp-002-discarded-pass1/`; **no number in
this document comes from them.**

**Defect 1 — B0 was not actually B0.** `spark.default.parallelism` is a static SparkConf
entry that survives `SparkContext.stop()` inside one JVM, and PySpark reuses a single JVM
for the lifetime of the Python process. B0 is the *only* configuration that leaves the key
unset (`default_parallelism: null` — "leave it to Spark"), so every B0 session silently
inherited the value set by whichever configuration preceded it in the randomized block.
Stored evidence from the discarded pass:

```
exp002-f1-agg-small-s0-b0-r1    master=local[2]   default.parallelism=8
exp002-f2-join-small-s0-b0-r1   master=local[2]   default.parallelism=8
```

B0 requires `local[2]` with Spark's own local-mode default of 2. `verify_applied()` missed
it because it skipped the check whenever the configuration declared `None` — precisely the
one case that needed checking.

*Scope of the damage:* the 12 varied configurations always set the key explicitly, so only
B0 was affected. The gate statistic uses `scope = varied_only`, so the **verdict** would
not have changed — but every B0-relative difference and the whole T_ref calibration would
have been wrong, which is reason enough to discard and re-run.

*Fix:* `ConfigPoint.effective_default_parallelism()` materialises the value explicitly for
every point (B0 → 2, i.e. Spark's own local-mode default for `local[2]`), and
`verify_applied()` now checks it for **every** point, including B0, against both
`spark.default.parallelism` and `sc.defaultParallelism`. B0's *declared* identity still
records `None` — that is what B0 specifies; the fix makes the session honour the
specification instead of inheriting a stale value. Verified against live Spark: after a
`local[8]` run, B0 now reports `default.parallelism=2`.

**Defect 2 — a concurrent runner.** A second process executed against the same result root
while the queue was live (`exp002-f1-agg-small-s0-g-p8-sp32-r1` appears twice in the
discarded `attempts.jsonl`). Two Spark sessions on one 8-core machine contend for cores, so
an unknown subset of those timings was measured under contention. Because the affected
window could not be bounded reliably, partial salvage was not defensible.

*Fix:* `QueueLock` takes an exclusive `O_CREAT|O_EXCL` lock on the result root, so a second
concurrent runner now fails loudly instead of silently contaminating timings.

**Honest reading:** these were found by adversarial review, not by the test suite. A
configuration that silently fails to apply is indistinguishable from insensitivity, which
is the most dangerous failure mode this experiment has. The read-back verification that
caught it is now mandatory for every knob on every run.

### 22.2 Design limitations

- **Two repetitions per cell.** This is the PLAN §33 budget (192 runs over the 12-config
  grid), not a choice made here. It supports medians, a pooled noise estimate and a
  rank-agreement check, but it does **not** support confidence intervals or a paired
  significance test over configurations. None is claimed.
- **One training seed (seed 0).** Holding the dataset instance fixed isolates the
  configuration effect, but EXP-002 therefore says nothing about cross-seed robustness.
- **EXP-001 was never run**, so the project's independent run-to-run noise profile does not
  exist. The noise band used by the gate is estimated from EXP-002's own within-configuration
  repetitions. This is a documented substitute, not an equivalent (see §23).
- **Single machine, single node, AQE off.** All results are machine-relative. Nothing here
  generalises to a cluster, to AQE-on execution, or to other hardware.
- **`require_complete_panel: true`** means one configuration failing at a (family, scale)
  discards that whole panel from the sensitivity judgement. This is conservative — it can
  only make the gate harder to pass — but it does discard evidence.
- **Monitoring overhead is unmeasured.** EXP-009 was not run, so SC6's overhead half is
  unverified. `provenance.queue_wall_s` is recorded as raw infrastructure data only; no
  overhead claim is made.
- **Process-level psutil only.** In single-node local mode the sampled process is the
  driver; this is not executor-level CPU/RSS coverage and is never presented as such.
- **Spill-path limitation of the frozen backend.** PySpark's external-sort spill path calls
  `os.unlink()` on a still-open file handle (`pyspark/shuffle.py`), which is legal on POSIX
  and raises `PermissionError [WinError 32]` on Windows. Any configuration whose partitions
  are large enough to spill in a Python-side sort fails for this environmental reason, not
  for a configuration-quality reason. Such runs are recorded as invalid observations with
  their traceback and are reported, never silently dropped — see the generated §19.

## 23. Dependency deviation — Days 19–21 were never completed

Recorded because it materially affects how this study was built.

`git log` at the start of Day 22 had **HEAD = `d8e02f7` "test(monitoring): harden
event-log parser and hand-checked fixtures"** — the **Day-18** deliverable. The working
tree additionally held **uncommitted Day-19** work
(`src/sparkrl/monitoring/{run_metrics,merge,sysmon}.py`, `tests/unit/test_metrics_merge.py`,
and a modification to `src/sparkrl/monitoring/__init__.py`).

Consequently the following planned prerequisites **did not exist**:

| Plan item | Expected artefact | Actual state |
|---|---|---|
| Day 19 — metrics merge + schema | committed `RunMetrics` / merge layer | present but **uncommitted** |
| Day 20 — experiment runner v1 | `YAML runner; cache; resume` | **absent** (no `src/sparkrl/experiments/`) |
| Day 21 — runner hardening + overhead | runner v1.0, EXP-009 first pass | **absent** (no overhead audit, no `DAY20/DAY21` docs) |
| Day 22 — EXP-001 noise calibration | 20-run noise profile, median CV ≤ 10% | **absent** (and out of scope for this task) |

The task instruction to "reuse the Day-21 hardened experiment runner" and "not duplicate
runner logic" therefore could not be followed literally. Resolution taken:

- **Nothing frozen was re-implemented.** Session creation, warm-up, timed execution and
  timeout remain `sparkrl.spark.{session,runner}` (Day 3); event-log parsing remains
  Day 18; metric merging and the `usable` rule remain Day 19.
- A **minimal** experiment layer (`src/sparkrl/experiments/`) supplies only what Day 20
  would have: queue order, resume/skip, atomic immutable manifests, and an attempt log.
  It is ~3 modules of orchestration with no measurement semantics of its own.
- The **execution cache** (COMP-EXP-11) and the **≤500-execution budget guard** were
  *not* built: they are RL-episode machinery, out of scope for a gate experiment, and
  building them would have drifted toward the blocked RL stage.
- **EXP-009 (monitoring-overhead ≤5%) was not run**, so SC6's overhead half remains
  unverified. EXP-002 records `provenance.queue_wall_s` per run as raw infrastructure
  data only; no overhead claim is made.
- **EXP-001 was not run.** Its absence is why the noise band in §17 is estimated
  internally. This is a documented substitute, not an equivalent.

**Result-layout note.** PLAN §27 suggests `results/EXP-XXX/<timestamp>/`. A per-invocation
timestamp is incompatible with the resumability this study requires (a new timestamp each
pass would prevent skip-completed). The deterministic path
`results/experiments/exp-002/runs/<family>/<scale>/seed<N>/<config>/rep<N>.json` is used
instead; the plan's "never overwritten" intent is satisfied more strongly, by immutable
completed manifests that the runner refuses to rewrite.

## 24. Reproducibility notes

EXP-002 is reproducible from version-controlled inputs alone:

| Input | Artefact |
|---|---|
| pre-registered design | `experiments/exp002.yaml` (+ snapshot `results/experiments/exp-002/spec.json`, which embeds the full ordered run plan) |
| design identity | `spec_fingerprint` — recorded in every run manifest and in `gate.json` |
| configuration grid | `src/sparkrl/experiments/grid.py`; `grid_fingerprint` + a per-point SHA-256 knob fingerprint |
| execution order | `order_seed: 20022` — the randomized complete block order is regenerated exactly |
| dataset identity | `dataset_id` / `dataset_fingerprint` / `schema_fingerprint` per manifest, resolved through the frozen Day-14 index |
| workload identity | `workload_version` per manifest, via the frozen registry |
| runner/schema versions | `exp002-run/v1` manifests, `run_metrics/v1` metrics, `exp002-analysis/v1` analysis, `exp002-gate/v1` gate |
| code version | `code_version` (git SHA + dirty flag) per manifest and in `gate.json` |

Commands:

```
python scripts/run_exp002.py            # resumable; completed runs are SKIPPED, never redone
python scripts/analyze_exp002.py        # stored manifests -> analysis/gate.json + summary.md
python scripts/render_exp002_audit.py   # gate.json -> sections 19-21 of this document
python scripts/validate_exp002.py       # 22 structural / integrity checks
```

The analysis is a pure function of `(stored manifests, spec)`. It was re-run on the same
stored set, and on the same set in reversed input order, producing **byte-identical** JSON
and an identical verdict, qualifying-family set, per-panel spreads, noise values and run
counts. `scripts/render_exp002_audit.py --check` fails if this document drifts from
`gate.json`, so the numbers above cannot silently diverge from the data.

Raw per-run manifests, the attempt log, the spec snapshot and the gate result are kept under
version control (a narrow `.gitignore` exception, ~2 MB of JSON); Spark event logs and
datasets remain outside the repository per DEC-002.

## 25. Conclusion — strictly what EXP-002 establishes

**The pre-registered configuration-sensitivity calibration gate (PLAN H1 / SC1) was
satisfied by the measured EXP-002 data.**

That is the entire claim. Concretely, and only this:

- On this machine, under the frozen backend, with AQE off, on the TRAIN split, varying only
  `spark.sql.shuffle.partitions` and execution parallelism produces differences in median
  `execution_time_s` that are far larger than 10% and larger than the observed run-to-run
  noise, on all four calibration families at at least one scale.
- The differences are repeatable: configuration orderings agree strongly between the two
  independent repetitions.
- B0 medians are recorded as the T_ref calibration the plan assigns to EXP-002/003.

EXP-002 does **not** establish, and nothing here should be read as claiming, any of the
following: that reinforcement learning works; that RL or any adaptive policy improves Spark
performance; that Q-learning converges; that adaptation is beneficial; that Candidate C is
superior; that any configuration is optimal or should be selected; empirical novelty;
production readiness; or generalisation to unseen workloads, scales, skew profiles, seeds,
hardware, or cluster deployments. A passing gate means only that the precondition the frozen
plan set for *considering* the later adaptive stage has been met — it is a calibration
result, not a performance result.

The strongest measured effects are also partly explained by an obvious confound worth
stating plainly: B0's `shuffle.partitions = 200` is badly oversized for these data volumes
on a 2-core local master, so a large part of the B0-relative gain is the removal of
per-partition overhead rather than evidence that a *learned* policy would add value over a
simple static rule. PLAN's B1/B2/B3 baselines (EXP-003/005) exist precisely to test that,
and they have not been run.

## 26. Exact next task

The EXP-002 gate (PLAN Day 24, SC1) is satisfied, which per the frozen plan removes the
R2 pivot trigger. It does **not** authorise starting RL work in this task, and earlier plan
items remain outstanding.

Reading `docs/PLAN.md` §31 in day order, the earliest incomplete items are:

1. **Day 21 — "Runner hardening + overhead"**: deliver runner v1.0 and the first EXP-009
   pass, validated by *monitoring overhead ≤ 5%* — this is milestone **M6**, still unmet.
   EXP-002 built only the thin orchestration it needed; the execution cache (COMP-EXP-11)
   and the ≤500-execution budget guard were deliberately not built (§23).
2. **Day 22 — "EXP-001 noise calibration"**: the 20-run noise profile with acceptance
   *median CV ≤ 10%*. It was never executed, which is why EXP-002's noise band had to be
   estimated internally (§17, §22.2).

**The exact next task is therefore Day 21: runner hardening + the first EXP-009 overhead
measurement (M6)**, followed by Day 22's EXP-001 noise calibration. Day 25 ("RL environment")
must not begin before those are closed.

Governance note: PLAN §31 marks the Day-24 deliverable as a recorded decision (`GO/pivot
(DEC)`). `DECISIONS.md` states that any entry requires explicit user/supervisor approval, so
no `DEC-xxx` entry was written here. Recording the GO decision in `DECISIONS.md` is a
supervisor action, not an automated one.
