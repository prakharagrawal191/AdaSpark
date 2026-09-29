# 6. Big Data Programming and Execution Layer

The execution layer runs ordinary Spark programs and is intentionally the least novel part of the system: five workload families (F1 aggregation, F2 join, F3 RDD sort/filter, F4 skew join, F5 mixed pipeline) execute as parameterized jobs over seeded synthetic datasets at three scales (S/M/L), with DAG generation, stage scheduling, shuffle, spill, and memory management handled by unmodified Spark (Figure 8) [1][2]. Deterministic data generation with checksummed manifests guarantees that a "workload instance" means the same bytes on every run, and the frozen dataset seed (0) anchors all calibrations.

Each job passes through session creation (fixed Spark configuration surface), timed execution under the runner's clock with two discarded warmups, and metric extraction (execution time, task-duration CV, spill bytes, event-log status). A run is timing-valid only if the harness clock sourced it; anything else is recorded but never adjudicated. This strictness is why the extension study can claim zero deviations across 4,842 runs: validity is a property checked per record, not assumed per batch.

## Table 5: Spark Components and Responsibilities

| Component | Responsibility in AdaSpark |
|---|---|
| Driver / SparkSession | Fixed-config session lifecycle; parallelism changes via session restart |
| DAG scheduler / stages | Unmodified stage graph; observed, never steered mid-job |
| Shuffle service | Partition-count target of actions (16/32/64/128) |
| Executors (local[N], N ∈ {2,4,8}) | Parallelism target of actions; task CV + spill telemetry source |
| Event log / listener bus | Overhead-measured monitoring arm; COMPLETE status required |
| DataGen + manifests | Seeded datasets; checksums; size-bin ground truth (never live-measured) |
| Runner clock | Sole timing authority; 2 warmups discarded per session |

Scale behavior confirms the workloads exercise distinct regimes: pooled median runtimes span 1.6s (small join) to 30.6s (medium aggregation), so the action grid is tested against both sub-second overhead-sensitive jobs and long shuffle-dominated ones. The twice-consumed cached intermediate in F5_mixed is the one structural feature that interacts with session restarts — changing parallelism destroys the JVM cache the pipeline depends on — which is why per-phase action changes were ruled out as a frozen-vs-frozen conflict rather than attempted. Determinism is enforced below the jobs as well: the smoke matrix (session creation, DataFrame operations, Parquet round-trip with exact checksums, event-log shape, clean shutdown across 13 checks) re-verifies the backend contract, so a regression in the platform surfaces as a failed gate rather than a mysterious result shift.
