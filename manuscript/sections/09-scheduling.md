# 8. Adaptive Resource Allocation and Scheduling Framework

Decisions become performance in the scheduling layer (Figures 11–12): the chosen action resolves to a concrete Spark configuration (shuffle partitions + `local[N]` parallelism, restarting the session when parallelism changes), tasks are allocated to executors, and the monitoring layer records the outcome that becomes the next state's feedback. Around the learned policy sit the static strategies that double as evaluation baselines and as deployable fallback policies: B0 (Spark defaults, AQE-off), B0′ (AQE-on reference), B1 (one globally tuned config), B2 (per-family tuned configs), B3 (rule-based: partitions from input size, parallelism from core count), and B4 (equal-budget random search) [9].

Two honest findings shape this layer's presentation. First, the rule heuristic B3 collapsed analytically onto B1 at the studied data volumes (clamp yields 16 partitions at every scale; confirmed byte-identical on 7/7 executed validation cells, X1), so the "heuristics" bar in any comparison is effectively the static tuning — recorded as a finding, not engineered around. Second, the AQE-on arm B0′ was executed as the X6 pilot (DEC-047, 35 runs) and came back mixed — one above-noise cell (`F2_join|large`, −14.24% favoring B0′), the rest inside noise or reversed, no pooling with RL arms — so complementarity with built-in adaptivity is bounded, one-cell evidence, still short of a general claim. Job prioritization and cluster tuning beyond the 12-action grid (broadcast thresholds, caching, memory fractions) are designed extension points, exercised only in the derived A4 ablation.

## Table 6: Resource Management Policies

| Policy | Rule | Status |
|---|---|---|
| B0 default | Factory settings, AQE-off | Executed (baseline) |
| B0′ AQE-on | B0 + `aqe_enabled=true`, nothing else | Executed as X6 pilot (DEC-047): mixed, side-by-side only |
| B1 static-global | `G-p8-sp16` (validation-frozen) | Executed; best 6-cell sum |
| B2 static-per-family | Best validation config per family | Executed (3 eligible cells) |
| B3 size rule | `clamp(input_GB × 7.45, 16, 128)` + cores→parallelism | Analytic + confirmed 7/7 (X1); ≡ B1 here |
| B4 random search | 84 TRAIN-calibrated draws, co-executed | Executed; ≈ RL-s0 |
| RL-s0/s1/s2 | Frozen greedy Q policies (3 seeds) | Executed as separate arms |

Resolution mechanics are deliberately explicit. The winning action's shuffle level and parallelism level are written into a static configuration object validated against the frozen schema; parallelism changes trigger a session restart (Spark requires it), while partition-only changes apply in-session. The twice-consumed F5 cache is preserved across same-parallelism decisions and rebuilt after restarts, with rebuild cost landing inside the measured execution time rather than hidden beside it. Prioritization across queued decisions follows registration order with per-run provenance (queue index recorded), which is also how the F1_agg|large|s3 queue-order confound was detected and disclosed instead of averaged away. Cluster tuning beyond the grid — executor memory, serializer, spill thresholds — stays fixed precisely so the 12-action comparison measures configuration selection rather than platform drift.
