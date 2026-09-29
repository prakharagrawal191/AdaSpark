# 19. Business Impact Assessment

The business case rests on converting recurring tuning labour and wasted compute into a one-time governed loop (Figure 28, Table 15). Operational efficiency comes from fewer manual interventions: each workload family carries one policy instead of one expert-maintained configuration per scale. Infrastructure savings follow the measured tuning gap — tuned configurations beat defaults 3–5× on the studied cells, so jobs that must run daily consume proportionally fewer executor-hours once tuned. Performance improvement is therefore not a promise but a measured range on the studied backend, with the honest bound that the learner matched but did not beat the best static tuning. Productivity gains accrue to platform teams: every decision ships with its evidence (policy checkpoint, manifest, interval), cutting diagnosis time when performance regresses.

ROI framing must stay inside the evidence. Measured costs: one full adjudication study ≈ 57 wall-clock hours on a single commodity node plus analyst time, against which ~3,000 unnecessary runs (≈60% of the study) are avoidable with dependence-aware stopping — a direct saving for any team running repetition studies. Unmeasured and therefore excluded from ROI: cluster-scale savings, multi-tenant effects, and any AQE-on interaction. The cost–benefit table below labels each line as measured or projected.

## Table 15: Cost–Benefit Analysis

| Line | Basis | Value |
|---|---|---|
| Tuning gap (default → tuned) | Measured (6 cells) | 3–5× faster |
| Learner vs static best | Measured | −21% (static wins; open) |
| Adjudication study cost | Measured (4,842 runs) | ~57 node-hours, 4.8 MB record |
| Avoidable runs (dependence-aware stopping) | Measured retrospectively | ~3,000 runs (~60%) |
| Expert-tuning labour displaced | Projected | Per-family policy replaces per-scale configs |
| Cluster/multi-tenant savings | Not measured | Excluded from ROI |
