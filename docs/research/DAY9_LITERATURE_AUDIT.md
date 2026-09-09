# Day 9 Literature Audit

*AdaSpark · Day 9 (2026-09-08) · scope: completion of Literature D–J to the ~30-row target (PLAN.md §31, Days 8–9 block)*

## Final Counts

- A: 6 (A1–A6)
- B: 3 (B1–B3)
- C: 7 (C1–C7)
- D: 1 (D1)
- E: 2 (E1, E2)
- F: 2 (F1, F2)
- G: 2 (G1, G2)
- H: 2 (H1, H2)
- I: 2 (I1, I2)
- J: 3 (J1, J2, J3)
- **Total: 30 verified rows** (Day-10 target: 25–30 — met)

## New Sources Added (Day 9)

- **E2** — Mao, Schwarzkopf, Venkatakrishnan, Meng, Alizadeh. "Learning scheduling algorithms for data processing clusters" (Decima), ACM SIGCOMM 2019, pp. 270–288. DOI 10.1145/3341302.3342080. *RL-derived scheduling policies for data-processing clusters.*
- **F2** — de Lemos, Giese, Müller, Shaw, Andersson, Litoiu, Schmerl, Tamura, Villegas, Vogel, Weyns, et al. (42 authors). "Software Engineering for Self-Adaptive Systems: A Second Research Roadmap", LNCS 7475, Springer, 2013, pp. 1–32. DOI 10.1007/978-3-642-35813-5_1. *Authoritative follow-on roadmap to F1.*
- **G2** — Huebscher & McCann. "A Survey of Autonomic Computing—Degrees, Models, and Applications", ACM Computing Surveys 40(3), 2008, pp. 1–28. DOI 10.1145/1380584.1380585. *Canonical survey organized around the MAPE-K reference model.*
- **H2** — Marcus, Negi, Mao, Zhang, Alizadeh, Kraska, Papaemmanouil, Tatbul. "Neo: A Learned Query Optimizer", PVLDB 12(11), 2019, pp. 1705–1718. DOI 10.14778/3342263.3342644. *Deep-neural-network learned optimizer that bootstraps from existing optimizers.*
- **I2** — Trummer, Wang, Wei, Maram, Moseley, Jo, Antonakakis, Rayabhari. "SkinnerDB: Regret-bounded Query Evaluation via Reinforcement Learning", ACM TODS 46(3), 2021, pp. 1–45. DOI 10.1145/3464389. *RL learns join orders during execution with an execution-cost regret bound.*
- **J1** — Van Aken, Pavlo, Gordon, Zhang. "Automatic Database Management System Tuning Through Large-scale Machine Learning" (OtterTune), ACM SIGMOD 2017, pp. 1009–1024. DOI 10.1145/3035918.3064029. *Learned DBMS config tuning with workload/DBMS transfer.*
- **J2** — Hutter, Hoos, Leyton-Brown. "Sequential Model-Based Optimization for General Algorithm Configuration" (SMAC), LION 5, LNCS 6683, Springer, 2011, pp. 507–523. DOI 10.1007/978-3-642-25566-3_40. *Foundational surrogate-model configuration optimization.*
- **J3** — Wistuba & Grabocka. "Few-Shot Bayesian Optimization with Deep Kernel Surrogates", ICLR 2021. arXiv:2101.07667. *Meta-learned deep-kernel surrogate for few-shot black-box optimization.*

## Verification Summary

- 30/30 rows marked `VERIFIED — <source>` with exact source links; 0 [TK]; 0 EXCLUDED; 0 REPLACED in this pass; no duplicate titles or DOIs (validator-enforced).
- Full abstract verified this session for: E2 (OpenAlex inverted index), G2 (CrossRef), H2 (CrossRef), I2 (CrossRef), J3 (arXiv).
- Title/venue-scoped (abstract not fetched): J1, J2, F2 (book chapter); plus pre-existing rows A2, C2, C3, C4, C6, D1, E1, F1, G1, H1, I1.
- Verification routes: CrossRef DOI records (E2, F2, G2, H2, I2, J1, J2), OpenAlex (E2 author roster, I2 author roster, F2 citation count), Semantic Scholar (F2 42-author roster, H2 roster), arXiv (H2 preprint metadata, J3 acceptance comment).

## RL Evidence (state / action / reward / algorithm extraction)

- **D1 (Mao et al., HotNets 2016)**: cluster resource management as a deep-RL problem; neural-network policy over resource-allocation decisions; abstract-level scope.
- **E2 (Decima, SIGCOMM 2019)**: state = workload/job characteristics on the cluster; action = scheduling decisions; reward/learning signal = scheduling efficiency (job completion); algorithm = deep-RL policy network; evaluation = efficiency vs heuristic schedulers; abstract-level scope — quantitative results deferred to full text.
- **I2 (SkinnerDB, TODS 2021)**: state = query-execution progress per time slice; action = join-order choice per slice; reward/learning signal = measured execution progress; algorithm = RL with regret-bounded execution strategies; evaluation = Join Order Benchmark, TPC-H, JCC-H vs MonetDB/Postgres/adaptive baselines; abstract verified verbatim.
- **C6 (Islam et al., TPDS 2021)** — pre-existing: deep RL for Spark job scheduling in clouds (title-verified scope).
- None of these RL papers addresses Spark *configuration selection* with a bounded execution budget; none is claimed to validate this project's design.

## Self-Adaptive / MAPE-K Evidence

- **G1** (Kephart & Chess, IEEE Computer 2003): MAPE-K reference model — the structural template for the project's adaptation loop.
- **G2** (Huebscher & McCann, ACM CSUR 2008): survey organized around the MAPE-K reference-model components, hierarchical autonomic architectures, and degrees of autonomicity — confirms MAPE-K as the field's organizing construct.
- **F1** (Salehie & Tahvildari, ACM TRETS 2009): foundational taxonomy of engineering approaches.
- **F2** (de Lemos et al., LNCS 7475, 2013): second community roadmap consolidating the self-adaptive-systems research agenda.
- MAPE-K is documented as a reference model, **not** an RL algorithm; the RL agent would implement its "Plan" component.

## Learned Optimizer Evidence

- **H1** (Bao, SIGMOD 2021): learned query optimization made practical by combining learned models with traditional optimization.
- **H2** (Neo, PVLDB 2019): deep-neural-network query optimizer bootstrapped from existing optimizers, learning continuously from incoming queries.
- **I1** (Kraska et al., SIGMOD 2018): learned index structures — learned models replacing hand-crafted components.
- **I2** (SkinnerDB, TODS 2021): learned execution decisions at runtime (RL join ordering with regret bound).

## Sample-Efficiency Evidence

- **C7 (LITE, ICDE 2022)**: authors state it is infeasible for BO/RL to collect sufficient training instances for Spark on big data.
- **E1 (CherryPick, NSDI 2017)**: config selection framed as requiring few expensive trials; BO for sample efficiency.
- **J2 (SMAC, LION 5 2011)**: surrogate-model optimization finds good configurations with few evaluations — the canonical non-RL sample-efficiency anchor.
- **J3 (few-shot deep-kernel BO, ICLR 2021)**: cross-task transfer makes black-box optimization sample-efficient.
- **I2 (SkinnerDB)**: regret-bounded learning bounds the cost of bad decisions — budgeted learning inside execution.
- This evidence directly motivates the project's ≤500-execution budget (SC6), execution cache, and offline initialization from the EXP-002 sensitivity grid.

## Generalization Evidence (RQ3)

- **C1**: performance influence is application-specific — motivates explicit unseen-workload testing.
- **C7**: knowledge migration small→large datasets — transfer across workload conditions is a recognized Spark-tuning challenge.
- **J1 (OtterTune)**: knowledge transfer across DBMS workloads/instances is an established technique.
- **J3**: few-shot cross-task transfer is the modern sample-efficiency direction.
- **E1/H1**: point-estimate/robustness limitations of BO and learned optimizers across workloads.
- Distinguish: generalization *demonstrated by these sources* (within their domains) vs generalization *proposed for evaluation in this project* (EXP-006/EXP-010, H4/SC5). The latter remains an empirical question.

## Strongest Sources (most important to the thesis)

1. **E1 (CherryPick, NSDI 2017)** — closest published formulation of the project's configuration-selection problem; motivates sample-efficiency and the random-search baseline.
2. **E2 (Decima, SIGCOMM 2019)** — flagship evidence that learned policies beat hand-crafted heuristics for cluster resource decisions.
3. **C7 (LITE, ICDE 2022)** — peer-reviewed Spark tuning that itself states the BO/RL sample-cost barrier on Spark.
4. **G1 + G2 (MAPE-K vision + CSUR survey)** — the adaptation-loop conceptual backbone; RL is one possible "Plan".
5. **J2 (SMAC, 2011)** — surrogate-model sample efficiency; conceptual support for offline initialization and the equal-budget baseline framing.
6. **J1 (OtterTune, SIGMOD 2017)** — learned configuration tuning with workload transfer; the closest DB-domain analog.
7. **I2 (SkinnerDB, TODS 2021)** — regret-bounded RL for execution decisions; budgeted-learning precedent.
8. **H1/H2 (Bao + Neo)** — viability and robustness/deployability challenges of learned optimizers in data systems.

## Current Research Gap

The reviewed literature supports a sample-efficient, cross-execution learning formulation for Spark configuration selection. The surveyed sources cover: Spark sensitivity and tuning (A, C), AQE within-query adaptation (B), RL for cluster scheduling/resource management (D1, E2, C6), BO for few-trial config selection (E1, J2), self-adaptive/MAPE-K framing (F1, F2, G1, G2), learned optimizers and execution (H1, H2, I1, I2), and sample-efficient/transfer learning-based tuning (J1, J3). The literature does **not** contain a study combining: (a) tabular/bandit RL for sample efficiency, (b) offline initialization from a sensitivity grid, (c) an execution cache bounding the budget at ≤500 executions, (d) explicit generalization testing on unseen workloads, (e) comparison against static/rule/random-search baselines, and (f) AQE-on as an explicit comparison condition. This project is designed to investigate that combination. (Scoping statement, not a novelty claim.)

## Full-Text Items Outstanding

A2, C2, C3, C4, C6, D1, E1, F1, G1, H1, I1, E2, F2, G2, H2, I2, J1, J2 (claims scoped to verified title/abstract records; E2, G2, H2, I2, J3 abstracts verified verbatim this session).

## Day-10 Priorities

1. Gap note: finalize `LITERATURE_MATRIX.md` v1 with the cross-checked research-gap statement (matrix §G + Cross-Domain Synthesis).
2. Novelty tiering: flag each contribution concept as Tier 1 (established) / Tier 2 (combination of established methods) / Tier 3 (requires empirical validation) — Spark-configuration RL, cross-execution adaptation, bounded/sample-efficient learning, AQE-aware comparison, unseen-workload evaluation. Do **not** freeze Tier-3 claims as established fact.
3. Cross-check the gap statement against the full-text queue where paywalls permit.
