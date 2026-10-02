# 14. Evaluation Metrics

The primary metric throughout is median end-to-end execution time over exactly five usable repetitions (Figure 20; Table 10 defines every metric). Secondary indicators are task-duration CV (imbalance), spill-bytes ratio (waste), and reward convergence (episodes to epsilon floor, greedy-policy agreement). Optimization effectiveness is judged against frozen gates rather than vibes: ≥10% spread for sensitivity (SC1), whole-interval position vs the 5% budget for overhead (SC6 clause 2), cross-seed agreement ≥0.70 for policy promotion (M8), and ±5% median reproducibility (SC7: pilot 2/4, X10; full study unevaluated). Reliability metrics count usable/failed/incomplete runs and budget consumption; a failed run is a first-class observation (reward −1), never a dropped row.

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

Measurement definitions used throughout — the overhead of Equation (5), the interval half-width of Equation (6) and the repetition count implied by a target half-width, Equation (7):

O = 100·(med_full − med_base)/med_base   (5)

h = (CI_hi − CI_lo)/2   (6)

n_req = n·(h/h_target)², h_target = 2pp   (7)

Two additions make the main comparison decidable for the first time (EXP-013). First, the frozen test family of PLAN §22 — Wilcoxon signed-rank paired by workload instance, Mann–Whitney U within a cell, Cliff's δ and Holm correction — is computed exactly, without normal approximations, with the cell as the unit of analysis; Equation (11) gives the per-cell effect size for repetitions x (arm) and y (comparator). Second, an A/A control measures the metric's own noise: two units executing the identical configuration in the same randomized block should differ only by chance, and their observed gap calibrates every other comparison in the design. Aggregate effects are reported as the geometric-mean ratio of Equation (12), which weights every cell equally instead of letting the largest cells dominate as a sum of medians does. Monitoring overhead in any future measurement uses the paired statistic of Equation (13), fixed by DEC-044 before such data existed.

δ = (#{(i,j): x_i > y_j} − #{(i,j): x_i < y_j}) / (m·n)   (11)

GMR = exp( (1/N) Σ_c ln(med_arm,c / med_cmp,c) )   (12)

O_paired = median_r [ 100·(t_full,r − t_base,r) / t_base,r ]   (13)
