# 11. Monitoring, Feedback, and Learning Layer

Monitoring is the MAPE-K sensor and the project's measurement instrument in one (Figure 17; Table 7). Two arms instrument every run: a system-metrics sampler (host + process CPU/memory, retained at ≈3.0 samples per job-second with no starvation across 1,614 monitored runs) and Spark's own event log (COMPLETE status required for validity) [10][27]. A fixed metrics schema (execution time, task-duration CV, spill bytes, log status) is merged and validated per record; timing-validity is a per-record property checked against the runner clock, which is how the 4,842-run extension study holds zero deviations.

Feedback closes the loop in two timescales. Online, each episode's reward updates the Q-table under the budget guard; offline, the monitoring record supports the adjudication studies of Section 15 — including the finding that repetitions are regime-structured episodes (lag-1 autocorrelation +0.58…+0.89; contention windows to 75% dispersion; CUSUM level shifts common across interleaved arms), which reframes "noise" as measurable host dynamics. Policy refinement is thus evidence-limited by design: when the record shows instability (M8 0.20), the layer reports replicates rather than refining toward a mirage.

Observability research on container-based and edge microservices faces the same trade-offs at larger scale — which signals to collect (metrics, logs, traces), at what granularity and at what cost [107][108] — and anomaly detection over high-dimensional operational data is a field of its own, with accuracy that degrades as volume and velocity grow [109]. In Spark, co-located applications interfere in ways only dedicated diagnosis reveals [44]. Learned components add two monitoring duties: catching the performance regressions a model introduces on some inputs while improving the average [62], and noticing workload shifts that invalidate a learned model [47]. AdaSpark covers the first through per-run validity and EXP-013's A/A control, which measures how far two executions of an identical configuration disagree under the evaluation design. It covers the second only in part: drift is measured (lag-1 autocorrelation, CUSUM shifts) but no online drift detector gates the policy — a limitation recorded in Section 20.

## Table 7: Monitoring Metrics and Indicators

| Metric | Source | Used for |
|---|---|---|
| `execution_time_s` (runner clock) | Harness | Primary outcome; reward time term |
| `task_duration_cv` | Spark tasks | R3 imbalance term (ref 0.5) |
| `spill_disk_bytes` / input | Spark + manifest | R3 waste term (ref 0.10) |
| System CPU/memory samples (~3/s) | Sampler daemon | Overhead arm; regime context |
| Event-log status/bytes | Spark listener bus | Overhead arm; validity gate |
| Lag-1..10 ACF, CUSUM shifts | Re-analysis (R2) | Dependence evidence; §15/§20 |
| Config/latency provenance | Manifests | Audit trail; reproducibility |
