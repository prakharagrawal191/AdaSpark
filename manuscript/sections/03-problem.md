# 2. Problem Statement

Spark workloads are executed under a fixed configuration — a default or a statically tuned one — even though the best configuration depends on conditions that change: operator mix (joins vs aggregations vs sorts), data scale, and skew [1]. Manual tuning does not generalize across workloads and does not respond to drift, and it consumes expert labour each time performance visibly degrades. This is the problem AdaSpark addresses: static configuration selection leaves performance on the table and adaptation to the engineer.

Five concrete challenges define the problem landscape (Figure 3); Table 2 maps each problem element to its status in this project. **Workload variability**: the same pipeline exhibits different bottlenecks as data grows or skew shifts, so no single configuration stays optimal. **Resource utilization**: executors sit idle during skewed stages while others spill, wasting capacity that a better configuration would reclaim. **Scheduling inefficiencies**: partition counts and parallelism levels chosen once interact poorly with stage boundaries discovered only at runtime. **Dynamic cluster environments**: shared hosts, thermal effects, and background load move runtimes by tens of percent between sessions — our own measurements show ~22% session-to-session level shifts and contention episodes reaching 75% dispersion within one series. **Performance bottlenecks**: shuffle-heavy stages amplify every one of the above, making configuration choice load-bearing rather than cosmetic. Each challenge is documented beyond this project: co-located Spark applications interfere with one another in ways that require dedicated diagnosis [44], partition imbalance from data skew prolongs reduce stages and idles resources [45], splitting jobs into many small tasks trades lower load variance against per-task overhead [46], and learned systems degrade when the workload they were trained on shifts [47].

The feasibility of treating this as a learning problem was established empirically: varying only shuffle partitions {16, 32, 64, 128} × parallelism {local-2, local-4, local-8} moves median execution time by ≥10% on all four tested workload families (EXP-002 gate, PASS). A decision problem with no measurable effect would not be worth learning; this one clears the bar on every family.

## Table 2: Problem Definition and Research Gaps

| # | Problem element | Status in this project |
|---|---|---|
| P1 | Static/default configs ignore workload + drift | Confirmed; motivates RL loop (RQ0 gate PASS 4/4) |
| P2 | Rule heuristics break silently | Observed: B3 ≡ B1 byte-identical at studied volumes (analytic; confirmed 7/7 executed validation cells, X1) |
| P3 | Learned policies must beat strong baselines | Decided (EXP-013): 4.0× faster than defaults (H2 accepted); 1.22× slower than static tuning and random search (H3 rejected) |
| P4 | Policies must generalize (scale, skew, new data) | Partial: unseen-cell failures high; SC5 not evaluable |
| P5 | Learning must fit a practical budget | Met: 483/500 executions; 0 failed submitted configs |
| P6 | Monitoring must be cheap enough to leave on | Met on 6/7 cells vs 5% budget (interval-adjudicated) |
| P7 | Repetition statistics must handle dependence | Failed honestly: √n model falsified 7/7; block-CI widens 2 verdicts |
| P8 | Interaction with built-in AQE | Interleaved re-test (EXP-013): AQE-on faster on 0/6 cells, X6's one-cell lead not replicated; pooled interaction unevaluated |
