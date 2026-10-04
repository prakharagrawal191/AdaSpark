# 17. Explainability, Reliability, and Trustworthiness Assessment

Trust is assessed claim by claim, each paired with its evidence and verdict (Figure 25, Table 13). Recommendation transparency holds: every acting policy is inspectable down to per-state Q-values with published episode counts — which is how the confirmatory study could establish, before running anything, that on test inputs the three replicate policies collapse to one per-family rule. Robustness is mixed and reported so: replicates disagree on training states (M8 0.20), `F3_rdd` fails structurally on large data under every configuration tried and on medium data under the default and the policy's own choice, and two overhead verdicts fall under dependence-honest intervals. Decision trustworthiness improved where it mattered most: the main hypotheses are now decided by pre-registered, drift-controlled tests (H2 accepted, H3 rejected), and an A/A control measured the noise floor those decisions rest on. Reproducibility of analysis is strong (16/16 zero-execution corroboration; seed-stable intervals), while reproducibility of measurement is partial: 18 of 39 cell-arms re-measured in EXP-013 fell within ±5% of EXP-005, and the X10 pilot's size pattern did not recur. Governance readiness is the strongest pillar: sealed test discipline, counted budget, immutable record, and a decision log that preserves failures — including the halt and amendment of the confirmatory study itself.

## Table 13: Trustworthiness Evaluation Matrix

| Claim | Evidence | Verdict |
|---|---|---|
| Config choice matters | EXP-002: ≥10% on 4/4 families | Supported |
| Learning fits budget | Ledger 483/500 SC6-counted (+5 demo disclosed = 488 combined); 0 failed configs | Supported |
| RL beats defaults | EXP-013: 0.249× (CI 0.212–0.295), 36/37 cells, Holm p = 4.4×10⁻¹¹ | Supported (H2 accepted) |
| RL beats static/random | EXP-013: RL/B1 1.218 (CI 1.128–1.319); worse on 16 cells, better on 1 | Rejected (H3) |
| Identical configs agree | EXP-013 A/A: 38/38 cells within 11.89%; median gap 2.0% | Supported |
| Policies generalize | EXP-006 heavy failures | NOT evaluable |
| Monitoring is cheap | Sampler 6/7 PASS in EXP-009 and EXP-014 (paired); event log 3/7 PASS, 0 FAIL in EXP-014 | Supported (sampler); not established (event log) |
| Analysis reproduces | 16/16 (EXP-002/005/009); seeds/BCa stable | Supported |
| Measurements reproduce | EXP-013 vs EXP-005: 18/39 cell-arms within ±5%; X10 pilot 2/4 | PARTIAL |
| Process is auditable | 36/36 gate; decision log DEC-001–DEC-055 | Supported |
