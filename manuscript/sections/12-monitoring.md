# 11. Monitoring, Feedback, and Learning Layer

Monitoring is the MAPE-K sensor and theInstitution's measurement instrument in one (Figure 17). Two arms instrument every run: a system-metrics sampler (host + process CPU/memory, retained at ≈3.0 samples per job-second with no starvation across 1,614 monitored runs) and Spark's own event log (COMPLETE status required for validity) [10][27]. A fixed metrics schema (execution time, task-duration CV, spill bytes, log status) is merged and validated per record; timing-validity is a per-record property checked against the runner clock, which is how the 4,842-run extension study holds zero deviations.

Feedback closes the loop in two timescales. Online, each episode's reward updates the Q-table under the budget guard; offline, the monitoring record supports the adjudication studies of Section 15 — including the finding that repetitions are regime-structured episodes (lag-1 autocorrelation +0.58…+0.89; contention windows to 75% dispersion; CUSUM level shifts common across interleaved arms), which reframes "noise" as measurable host dynamics. Policy refinement is thus evidence-limited by design: when the record shows instability (M8 0.20), the layer reports replicates rather than refining toward a mirage.

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
