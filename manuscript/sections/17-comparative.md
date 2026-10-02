# 16. Comparative Analysis

Figure 24 summarizes the comparison per workload family as geometric-mean speed relative to the tuned static configuration B1 (outward is faster), from the drift-controlled EXP-013 study. Against the four comparison classes the picture is now decided rather than descriptive. **Static scheduling:** the validation-tuned static configuration (B1) is the strongest measured arm; the learned policy is 1.22× slower overall (95% CI 1.13–1.32) — identical on the aggregation and join families, 1.60× slower on skew joins and within noise on mixed pipelines — so superiority over static tuning is rejected (H3). **Heuristic optimization:** the size rule B3 resolves to B1's configuration on every TEST cell (and was byte-identical on 7/7 executed validation cells, X1), so "RL versus heuristics" is the same comparison as RL versus B1. **Equal-budget random search:** B4 also resolves to B1's configuration on every TEST cell, and EXP-013's A/A control shows the two agree within a 2.0% median gap (maximum 9.7%); EXP-005's apparent tie between RL and random search was a queue-order artifact, and RL trails random search by the same 1.21× it trails static tuning. **Adaptive query execution:** executed side by side with B0 in the same randomized blocks, AQE-on (B0′) was faster beyond noise on none of six cells (`F2_join|large` +1.8%; two skew-join cells 18–21% slower but not significantly), so X6's single-cell lead is retracted and no complementarity claim is made; pooling AQE-on with RL arms remains forbidden (gap G-04). **AutoML-style systems:** offline tuners in the OtterTune/CDBTune lineage [7][8] and recent DRL tuners [15] trade larger tuning budgets for potentially stronger optima; AdaSpark's counter-position is sample efficiency (≤500 runs, single machine) with governed adaptation — a different point on the cost–adaptivity frontier, not a domination claim. What the learner did deliver is a large, significant improvement over Spark defaults (4.0×, H2 accepted): the gain a competent tuning delivers, reached within the budget but not exceeded.

Table 12 states each comparison class with its measured result.

## Table 12: Comparative Benchmark Analysis

| Comparison class | Rival | Result (EXP-013 unless noted) |
|---|---|---|
| Spark defaults | B0 | RL needs 0.249× the default's time (CI 0.212–0.295); ≥10% faster on 36/37 cells; H2 accepted |
| Static scheduling | B1 global / B2 per-family | RL/B1 1.218 (CI 1.128–1.319); worse on 16 cells, better on 1; H3 rejected. B2 equals B1 or RL's configuration except on F3 (sp64), where it is within 1% of B1 |
| Heuristic | B3 size rule | Same configuration as B1 on every TEST cell; byte-identical on 7/7 validation cells (X1) |
| Equal-budget search | B4 random (84 TRAIN runs) | Same configuration as B1; A/A gap median 2.0%, maximum 9.7% (38/38 within noise); RL/B4 1.206 (CI 1.115–1.309) |
| Built-in adaptivity | B0′ AQE-on | Faster than B0 beyond noise on 0/6 cells (interleaved); X6's −14.24% not replicated |
| Offline AutoML-style | OtterTune/CDBTune class [7][8] | Different budget regime; no head-to-head |
