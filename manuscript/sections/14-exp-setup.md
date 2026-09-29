# 13. Experimental Setup

All experiments ran on one frozen backend: Windows 11, Python 3.11.9, Java 17, PySpark 3.5.9 in native local mode (`local[2]`, driver 6 GB, 24 logical cores) — the Day-2 smoke-matrix configuration (13/13 checks) frozen by decision, so hardware and software are constants, not variables (Figure 19). Datasets are seeded synthetics across five families (F1 aggregation, F2 join, F3 RDD sort/filter, F4 skew join, F5 mixed pipeline) at S/M/L scales with checksummed manifests; the RL configuration is tabular Q-learning (α = 0.2, γ = 0.0, ε 1.0 → 0.05, 3 training seeds, Q0-median init, ≤500-execution guard).

Evaluation scenarios span twelve experiments: EXP-001 noise calibration, EXP-002 sensitivity gate, EXP-003 baseline selection, EXP-004 training, EXP-005 main comparison (7 frozen test instances × 7 arms × 5 reps = 245 runs), EXP-006 generalization, EXP-007 state ablations, EXP-008 derived reward/action ablations, EXP-009 monitoring overhead (105 + 4,842 runs). The remaining three later ran as bounded pilots under signed decisions with their own register lines and 0 charged to SC6: EXP-010 (NYC-Taxi transfer, X9, 20 runs, DEC-050), EXP-011 (±5% reproducibility, X10, 20 runs, DEC-049), and EXP-012 (live demo rehearsal, 5 disclosed TRAIN-split runs, DEC-051) — alongside the validation-scoped confirmations X1–X3 (DEC-048), the AQE-on arm B0′ (X6, 35 runs, DEC-047) and the F2 rematch (X8), each reported at its pilot scope with any plan/execution substitution disclosed.

## Table 9: Experimental Configuration Details

| Item | Setting |
|---|---|
| Backend | PySpark 3.5.9 / Java 17 / Python 3.11.9 / Win 11, `local[2]`, driver 6 GB |
| Workloads | F1_agg, F2_join, F3_rdd, F4_ski, F5_mixed × S/M/L, dataset seed 0 |
| Action space | 12 actions (partitions {16,32,64,128} × local {2,4,8}) |
| Learner | Tabular Q, α=0.2, γ=0.0, ε 1.0→0.05, seeds {0,1,2}, Q0-median |
| Budget | SC6 ≤500 training executions — 483/500 SC6-counted (17 remain); 488/500 combined incl. the 5 disclosed demo TRAIN runs (12 remain) |
| Repetitions | Median of exactly 5 usable reps (evaluation); n=2 (EXP-002); n=1 (selection) |
| Test discipline | Frozen instances; sealed TEST; authorization guards |
