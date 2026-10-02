# 17. Explainability, Reliability, and Trustworthiness Assessment

Trust is assessed claim by claim, each paired with its evidence and verdict (Figure 25, Table 13). Recommendation transparency holds: every acting policy is inspectable down to per-state Q-values with published episode counts. Robustness is mixed and reported so: three replicates diverge (M8 0.20), unseen-cell failures are heavy, and two overhead verdicts fall under dependence-honest intervals. Reproducibility of analysis is strong (16/16 zero-execution corroboration; seed-stable intervals) while reproducibility of measurement is partial and pilot-scoped — X10 reproduced 2 of 4 cell-arms within ±5% (medium arms pass, small arms drift), and the full 60-run EXP-011 remains empty. Governance readiness is the strongest pillar: sealed test discipline, counted budget, immutable record, and a decision log that preserves failures.

## Table 13: Trustworthiness Evaluation Matrix

| Claim | Evidence | Verdict |
|---|---|---|
| Config choice matters | EXP-002: ≥10% on 4/4 families | Supported |
| Learning fits budget | Ledger 483/500 SC6-counted (+5 demo disclosed = 488 combined); 0 failed configs | Supported |
| RL beats defaults | B0 142.38 vs RL-s0 38.15 (6-cell) | Supported |
| RL beats static/random | B1 30.32 best; RL≈B4; no inference | NOT supported (open) |
| Policies generalize | EXP-006 heavy failures | NOT evaluable |
| Monitoring is cheap | 6/7 PASS (i.i.d.); 4/7 under blocks | Qualified support |
| Analysis reproduces | 16/16; seeds/BCa stable | Supported |
| Measurements reproduce | X10 pilot 2/4 (medium +2.7/+4.7% pass, small +6.8/+11.7% fail); full EXP-011 empty | PARTIAL (pilot) |
| Process is auditable | 36/36 gate; 54 decisions | Supported |
