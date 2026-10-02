# 16. Comparative Analysis

Figure 24 places B1, B4, and RL-s0 on six axes (one per cell, best-normalized so outward is better): no arm dominates — B1 leads on three cells, B4 on two, RL-s0 never leads outright but never collapses, trailing B4 by 0.5% overall. Against the four comparison classes the picture is differentiated rather than triumphal. **Static scheduling:** the frozen static tuning (B1) is the strongest arm measured (30.32 vs 38.15), so any claim of beating static methods is withheld. **Heuristic optimization:** the size rule (B3) is analytically identical to B1 here and was confirmed byte-identical on 7/7 executed validation cells (X1), making "RL vs heuristics" effectively "RL vs B1" — a limitation stated, not hidden. **Adaptive query execution:** the AQE-on arm (B0′, X6, 35 runs under DEC-047) is now measured side-by-side and is mixed — one above-noise cell (`F2_join|large`, −14.24% favoring B0′), the other decidable cells inside noise or reversed — so complementarity with built-in adaptivity is bounded, one-cell evidence; pooling with RL arms remains forbidden (no-pooling rule, gap G-04). **AutoML-style systems:** offline tuners in the OtterTune/CDBTune lineage [7][8] trade larger tuning budgets for potentially stronger optima; AdaSpark's counter-position is sample efficiency (≤500 runs, single machine) with governed online adaptation — a different point on the cost–adaptivity frontier, not a domination claim.

Table 12 states each comparison class with its measured result.

## Table 12: Comparative Benchmark Analysis

| Comparison class | Rival | Result (measured) |
|---|---|---|
| Static scheduling | B1 global / B2 per-family | B1 wins 6-cell sum by ~21%; B2 eligible on 3 cells only |
| Heuristic | B3 size rule | Collapses onto B1 — analytic, and byte-identical on 7/7 executed validation cells (X1); comparison ≡ RL vs B1 |
| Equal-budget search | B4 random (84 TRAIN runs) | RL-s0 ≈ B4 (38.15 vs 38.34, 0.5%) |
| Spark defaults | B0 | All tuned arms beat B0 by 3–5× |
| Built-in adaptivity | B0′ AQE-on (X6, DEC-047) | Mixed: `F2_join\|large` −14.24% outside noise favoring B0′; 5/6 decidable cells inside noise or reversed; `F3_rdd\|large` incomplete; side-by-side only, no pooling |
| Offline AutoML-style | OtterTune/CDBTune class [7][8] | Different budget regime; no head-to-head |
