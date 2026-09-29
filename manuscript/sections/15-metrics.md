# 14. Evaluation Metrics

The primary metric throughout is median end-to-end execution time over exactly five usable repetitions (Figure 20). Secondary indicators are task-duration CV (imbalance), spill-bytes ratio (waste), and reward convergence (episodes to epsilon floor, greedy-policy agreement). Optimization effectiveness is judged against frozen gates rather than vibes: ≥10% spread for sensitivity (SC1), whole-interval position vs the 5% budget for overhead (SC6 clause 2), cross-seed agreement ≥0.70 for policy promotion (M8), and ±5% median reproducibility (SC7: pilot 2/4, X10; full study unevaluated). Reliability metrics count usable/failed/incomplete runs and budget consumption; a failed run is a first-class observation (reward −1), never a dropped row.

## Table 10: Metrics Definition Matrix

| Metric | Definition | Gate / use |
|---|---|---|
| Median execution time | Median of 5 usable reps, runner clock | Primary; all RQs |
| Spread across configs | (max − min)/min of medians | ≥10% on ≥2 families (SC1/H1) |
| Overhead % | 100·(med_full − med_base)/med_base | 95% CI wholly below 5% (SC6c2) |
| Task CV / spill ratio | CV of task durations; spill/input | R3 terms (refs 0.5 / 0.10) |
| Policy agreement | Cross-seed greedy match fraction | ≥0.70 (M8; measured 0.20) |
| Reproducibility | Fresh-median within ±5% | SC7 pilot 2/4 (X10); full 60-run study not executed |
| Budget consumed | Ledger sum over manifests | ≤500 (483 spent) |
| Usable/failed/incomplete | Per-record validity | Reliability reporting |

Measurement definitions used throughout:

O = 100·(med_full − med_base)/med_base   (5)

h = (CI_hi − CI_lo)/2   (6)

n_req = n·(h/h_target)², h_target = 2pp   (7)
