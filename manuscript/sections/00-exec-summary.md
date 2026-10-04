# Executive Summary

Big-data programming on Spark remains dominated by static decisions: a workload is submitted under a default or hand-tuned configuration that stays fixed while data volumes, skew and operator mixes change. With about two hundred parameters, manual tuning goes stale as workloads drift, and built-in Adaptive Query Execution (AQE) covers only some runtime decisions.

**AdaSpark** closes the loop around Spark execution with reinforcement learning (RL): an agent observes a compact workload-context and runtime-feedback state, selects shuffle partitions × execution parallelism before each run, and learns from the measured outcome within ≤500 training executions. It follows the Monitor–Analyze–Plan–Execute–Knowledge (MAPE-K) pattern, with a governance layer that never rewards failed configurations.

On a frozen single-node backend (five workload families, three data scales, plus a 4,842-run overhead study) the findings are: (i) configuration choice moves median execution time by ≥10% on all four tested families (EXP-002 gate, PASS); (ii) training used 483 of the 500 executions with zero failed submitted configurations; (iii) the pre-registered, drift-controlled confirmatory evaluation on 42 frozen test cells (EXP-013) accepted H2 — 4.0× faster than Spark defaults across 37 decidable cells and ≥10% faster on 36 of them — and rejected H3: 1.22× slower than a well-chosen static tuning, to which equal-budget random search also converged; (iv) cross-seed agreement failed on training states (0.20 vs 0.70), yet on test inputs the three replicates collapse to one per-family rule, and generalization (EXP-006) is not evaluable; (v) the 1 Hz sampler stays below the 5% overhead budget on six of seven cells in both EXP-009 and the paired re-measurement EXP-014, whereas the event log's earlier six-of-seven pass was not re-established (three pass, four inconclusive, none fail); and (vi) the pre-registered prediction that interval width shrinks as 1/√n failed on all seven cells because repetitions are serially correlated (lag-1 autocorrelation +0.58…+0.89), so roughly 3,000 of the 4,842 runs were unnecessary.

Organizationally, AdaSpark turns tuning into a governed, auditable control loop: every decision traces to a policy checkpoint, every measurement carries provenance, and every limitation — including the failed agreement gate and three earlier conclusions the two confirmatory studies refuted — is recorded in the decision log and the claim–experiment map. Table 1 summarizes the contributions and outcomes.

## Table 1: Executive Summary of Contributions and Outcomes

| # | Contribution | Outcome (measured) |
|---|---|---|
| C1 | RL-driven self-adaptive Spark configuration loop (MAPE-K) | Implemented; 12-action space; tabular Q-learning + Q0 offline init |
| C2 | Bounded-budget learning (≤500 executions) | 483 SC6-counted spent, 17 remaining (488/500 combined incl. 5 disclosed demo runs); 0 failed submitted configs |
| C3 | Sensitivity feasibility gate (EXP-002) | PASS — ≥10% spread on 4/4 families |
| C4 | Main comparison vs baselines incl. random search (EXP-005 → EXP-013) | 245 + 900 queue entries; H2 ACCEPTED (4.0× vs defaults); H3 REJECTED (1.22× slower than static tuning) |
| C5 | Generalization study (EXP-006) | Partial (high failure on unseen cells); SC5 not evaluable |
| C6 | Monitoring-overhead measurement (EXP-009 → EXP-014) | Sampler 6/7 PASS in both; event log 6/7 → 3/7 PASS (0 FAIL) under the paired statistic |
| C7 | Pre-registered √n falsification (4,842 runs) | Failed 7/7 — serial dependence measured, cost quantified |
| C8 | Governance: decision log, provenance, sealed test discipline | Decision log DEC-001–DEC-055; immutable manifests; reproducible artifact |
