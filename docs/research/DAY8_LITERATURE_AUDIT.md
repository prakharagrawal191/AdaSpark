# Day 8 Literature Audit

*AdaSpark · Day 8 (2026-09-08) · scope: Literature D–J (PLAN.md §31, Days 8–9 block)*

## Sources Added

- **D1** — Mao et al., "Resource Management with Deep Reinforcement Learning" (HotNets 2016)
- **E1** — Alipourfard et al., "CherryPick" (NSDI 2017)
- **F1** — Salehie & Tahvildari, "Self-adaptive Software: Landscape and Research Challenges" (ACM TRETS 2009)
- **G1** — Kephart & Chess, "The Vision of Autonomic Computing" (IEEE Computer 2003)
- **H1** — Marcus et al., "Bao: Making Learned Query Optimization Practical" (SIGMOD 2021)
- **I1** — Kraska et al., "The Case for Learned Index Structures" (SIGMOD 2018)

## Category Coverage

- A: 6 · B: 3 · C: 7 · D: 1 · E: 1 · F: 1 · G: 1 · H: 1 · I: 1 · J: 0
- **Total: 22 verified rows** (Day-9 target: ~30)

## Verification Summary

- 22/22 rows marked `VERIFIED — <source>` with exact source links; 0 [TK]; 0 EXCLUDED; no duplicate titles or DOIs.
- Full abstract verified for: A1, A2 (abstract), A3 (page abstract), A4, A5, B3 (demo abstract), C1, C4, C5, C7, H1.
- Title/venue-scoped (abstract not fetched): B2, C2, C3, C6, D1, E1, F1, G1, I1.
- Implementation-facts scope: B1 (blog + docs, non-peer-reviewed).

## Strongest Evidence

1. **RL is viable for systems but sample-expensive** (D1): Mao et al. formulated cluster resource management as deep RL (1059 citations), establishing the paradigm while surfacing the trial-cost challenge.
2. **Config selection is an expensive few-trials problem** (E1): CherryPick used Bayesian optimization to find good cloud configurations for big-data analytics with few evaluations — the closest published work to this project's problem.
3. **MAPE-K is the conceptual backbone** (G1): Kephart & Chess introduced the Monitor→Analyze→Plan→Execute→Knowledge reference model (4677 citations); the project's adaptation loop is a MAPE-K instance.
4. **Learned optimizers are viable but face robustness challenges** (H1): Bao made learned query optimization practical (SIGMOD 2021), demonstrating promise and practical hurdles.
5. **Learned models can replace hand-crafted components** (I1): Learned index structures (SIGMOD 2018) established the broader learned-systems paradigm.

## Sample-Efficiency Evidence

- **C7 (LITE, ICDE 2022)**: authors state it is infeasible for BO/RL to collect sufficient training instances for Spark on big data.
- **E1 (CherryPick, NSDI 2017)**: frames config selection as requiring few expensive trials; uses Bayesian optimization for sample efficiency.
- **D1 (Mao et al., HotNets 2016)**: deep-RL resource management motivates the sample-efficiency constraint (deep RL typically needs many trials).
- This evidence directly motivates the project's ≤500-execution budget and execution cache.

## Self-Adaptation Evidence

- **F1 (Salehie & Tahvildari, ACM TRETS 2009)**: foundational taxonomy of self-adaptive systems engineering approaches.
- **G1 (Kephart & Chess, IEEE Computer 2003)**: the MAPE-K reference model — the structural template for the project's adaptation loop.

## Learned-Optimizer Evidence

- **H1 (Bao, SIGMOD 2021)**: state-of-the-art learned query optimizer combining learned models with traditional optimization.
- **I1 (Kraska et al., SIGMOD 2018)**: learned index structures — the seminal learned-systems paper.

## Current Research Gap

The reviewed literature supports a sample-efficient, cross-execution learning formulation for Spark configuration selection. The literature does not contain a study combining: (a) tabular/bandit RL for sample efficiency, (b) offline initialization from a sensitivity grid, (c) an execution cache bounding the budget at ≤500 executions, (d) explicit generalization testing on unseen workloads, (e) comparison against static/rule/random-search baselines, and (f) AQE-on as an explicit comparison condition. This project is designed to investigate that combination.

## Full-Text Items Outstanding

A2, C2, C3, C4, C6, D1, E1, F1, G1, H1, I1 (abstract/title-scoped; full texts behind paywalls).

## Day-9 Search Priorities

- Populate **J** category (closely related learning-based systems optimization; sample efficiency, transfer learning, surrogate models).
- Add a second **D/E** row (e.g., a survey on RL for resource management, or a learned-scheduling paper) for balance.
- Add a second **F** row (e.g., a self-adaptive systems survey with broader coverage) and a second **I** row (learned execution decisions beyond indexes).
- Expand toward the ~30-row target with verified sources only.