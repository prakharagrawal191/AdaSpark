# 19. Business Impact Assessment

The business case rests on converting recurring tuning labour and wasted compute into a one-time governed loop (Figure 28, Table 15). Operational efficiency comes from fewer manual interventions: each workload family carries one policy instead of one expert-maintained configuration per scale. Infrastructure savings follow the measured tuning gap — the learned policy beats defaults about 4× across 37 test cells (EXP-013), so jobs that must run daily consume proportionally fewer executor-hours once tuned. Performance improvement is therefore not a promise but a measured range on the studied backend, with the honest bound that the learner is 1.22× slower than the best static tuning. Productivity gains accrue to platform teams: every decision ships with its evidence (policy checkpoint, manifest, interval), cutting diagnosis time when performance regresses.

ROI framing must stay inside the evidence. Measured costs: one full adjudication study ≈ 57 wall-clock hours on a single commodity node plus analyst time, against which ~3,000 unnecessary runs (≈60% of the study) are avoidable with dependence-aware stopping — a direct saving for any team running repetition studies. Unmeasured and therefore excluded from ROI: cluster-scale savings, multi-tenant effects, and the pooled AQE-on interaction. The cost–benefit table below labels each line as measured or projected.

Two external reference points bound the projection. A study of ML-based configuration tuning on an enterprise Oracle deployment with a real workload trace measured a 45% improvement over enterprise-grade configurations [64] — evidence that tuning gains can survive production conditions, but for a different system class and a far larger tuning budget than AdaSpark's. Reinforcement learning is also being reviewed as a route to data-centre energy efficiency [133]; this report measures execution time only, so no energy saving is claimed.

## Table 15: Cost-Benefit Analysis

| Line | Basis | Value |
|---|---|---|
| Tuning gap (default → learned policy) | Measured (EXP-013, 37 cells) | 4.0× faster (GMR 0.249) |
| Learner vs static best | Measured (EXP-013) | 1.22× slower (H3 rejected) |
| Adjudication study cost | Measured (4,842 runs) | ~57 wall-clock hours on one node, 4.8 MB record |
| Avoidable runs (dependence-aware stopping) | Measured retrospectively | ~3,000 runs (~60%) |
| Expert-tuning labour displaced | Projected | Per-family policy replaces per-scale configs |
| Cluster/multi-tenant savings | Not measured | Excluded from ROI |
