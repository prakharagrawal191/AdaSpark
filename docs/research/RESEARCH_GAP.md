# Research Gap

*AdaSpark · Day 10 (2026-09-09) · source of truth: `docs/LITERATURE_MATRIX.md` v1.0 (30 VERIFIED rows, A–J) · verification routes in `docs/research/LITERATURE_VERIFICATION_LOG.md`*

> **Boundary.** This note synthesizes only what the 30-row corpus supports. It motivates and positions the study; it does not claim the proposed method works. That is decided by EXP-001…EXP-012. No Tier-3 claim is made as fact.

## 1. Established Knowledge

Within the literature corpus examined in this study, the following is established at abstract/record level (claim-to-row trace in §6):

1. **Spark's in-memory execution model is the performance foundation.** Spark outperforms Hadoop by 10x on iterative ML jobs and interactive queries over tens of GB (A1); keeping data in memory improves performance by an order of magnitude for iterative/interactive workloads (A5). Spark is documented as the de-facto analytics framework with in-memory, SQL, ML, graph, and streaming libraries (A4).
2. **The SQL engine lineage runs Shark → Spark SQL → AQE.** Shark added column-oriented in-memory storage and dynamic mid-query replanning on Spark (A6); Spark SQL added tight procedural/declarative integration and the extensible Catalyst optimizer (A2); AQE (Spark 3.0+) re-optimizes plans at runtime — dynamic partition coalescing, runtime join-strategy switching, skew splitting (B1, industry/official-docs scope, explicitly non-peer-reviewed).
3. **Spark performance is configuration-sensitive and workload-dependent.** A good configuration can greatly improve deployed-system performance; systems expose tens to hundreds of parameters (C4). Improper settings cause significant degradation and stability issues in Spark-class systems (C5).
4. **Automatic configuration optimization exists, in several families.** The survey taxonomy lists rule-based, cost-modeling, simulation-based, experiment-driven, ML, and adaptive tuning (C5). Verified instances: ML influence models cutting execution time 22.8–40.0% across 9 applications, with influence varying across applications (C1); multi-objective + prediction models (C2, title scope); BO acquisition-function studies for Spark (C3, title scope); BestConfig-style automatic tuning framed as costly/expertise-requiring (C4); code-learning knob recommendation with small→large knowledge migration and adaptive updates (C7).
5. **RL is an established paradigm for systems/resource decisions.** Deep RL formulates cluster resource management as sequential decision-making (D1); learned scheduling policies for data-processing clusters are generated automatically (E2); deep RL is applied to Spark job scheduling in clouds (C6, title scope); RL learns join orders during execution with a bounded execution-cost regret criterion (I2).
6. **Sample-efficient / transfer-based optimization is an established response to expensive trials.** CherryPick frames cloud-config selection as needing few expensive full-run evaluations and uses BO (E1). Surrogate-model configuration search (SMAC, J2) and workload/DBMS knowledge transfer (OtterTune, J1) are established techniques; few-shot deep-kernel BO transfers surrogate knowledge across tasks for very few evaluations (J3). LITE migrates small-scale knowledge to large-scale datasets (C7).
7. **Self-adaptive / autonomic framing is established.** Foundational taxonomy of self-adaptive engineering (F1) and the community research roadmap (F2) establish feedback-loop, goal/utility, and monitoring vocabulary. The MAPE-K reference model (Monitor–Analyze–Plan–Execute over Knowledge) is the organizing construct for self-managing systems (G1) and for the autonomic-computing survey literature (G2).
8. **Learned data-system components are viable but face robustness costs.** Bao combines learned models with traditional optimization for practicality (H1); Neo bootstraps a DNN optimizer from an existing optimizer and keeps learning from incoming queries (H2); learned index structures replace/augment hand-crafted structures for specific distributions (I1).
9. **System experimentation is expensive.** Deciding the best configuration across tens/hundreds of parameters is highly costly and expertise-requiring (C4); collecting sufficient training instances or repeatedly executing Spark applications is stated to be infeasible for BO/RL on big data (C7); config selection needs few expensive trials (E1).

## 2. Limitations Observed Across the Reviewed Literature

Each limitation is traceable to matrix rows (IDs in parentheses):

1. **Static / point-estimate tuning, not cross-execution policies.** C1 builds application-specific influence models; C4 produces one tuned configuration per setting; E1's BO returns a single best cloud configuration; C7 recommends knob values per application. None, at verified scope, describes a reusable cross-workload decision policy evaluated on unseen workloads. (C1, C4, E1, C7)
2. **Within-query rather than cross-execution adaptation.** AQE re-optimizes a single query execution (B1); adaptive-query-processing lineage (B2) and skew mitigation (B3) operate within a run. None describes learning a configuration policy from past executions. (B1, B2, B3)
3. **Workload-specific models with limited demonstrated transfer.** Influence varies across applications (C1); BO config selection does not generalize across workloads (E1); learned-optimizer robustness across queries is an open deployability concern (H1). Cross-scale migration (C7) and cross-workload DBMS transfer (J1) show transfer is possible in adjacent settings, not that a Spark configuration policy transfers. (C1, C5, C7, E1, H1, J1, J3)
4. **Search / training cost vs. single-machine budgets.** Exponential search spaces are computationally infeasible (C1); tuning is highly costly (C4); BO/RL instance collection on Spark is infeasible at big-data scale (C7); deep RL implies many trials (D1). The corpus does not demonstrate tabular/bandit-scale learning within a ≤500-execution cache on a single 32 GB node. (C1, C4, C7, D1, E1, J2, J3, I2)
5. **RL evidence is adjacent, not on Spark configuration selection.** D1/E2/C6 address cluster resource management, cluster scheduling, and Spark job scheduling — not Spark configuration-knob selection with a bounded discrete action space and workload-context state. I2's RL addresses join orders, not configuration. (D1, E2, C6, I2)
6. **Learned optimizers operate inside the query, not on launch configuration.** Bao/Neo learn plan choices (H1, H2); learned indexes learn data-structure layout (I1). Neither selects executor sizing, static parallelism, or caching strategy across executions.
7. **MAPE-K prescribes the loop, not the learner.** G1/G2 and F1/F2 establish Monitor→Analyze→Plan→Execute→Knowledge and adaptation vocabulary but say nothing about how "Plan" should learn under a trial budget. RL is one candidate Plan implementation, not a consequence of MAPE-K.

## 3. Cross-Domain Synthesis

The surveyed work tells one connected story. Spark's in-memory model made iterative analytics fast but exposed a large configuration surface whose best settings shift with workload, scale, and skew (A1–A6, C4, C5, C1). The field responded along two tracks: *within-query* runtime adaptation — mid-query replanning (A6), adaptive query processing (B2), skew handling (B3), culminating in AQE (B1) — and *across-run* automatic tuning — influence models (C1), multi-objective/prediction tuning (C2), BO studies (C3), BestConfig-style search (C4), code-learning recommenders (C7), surveyed as six families (C5).
In parallel, systems research showed RL can drive sequential resource/scheduling/execution decisions (D1, E2, C6, I2) and that learned components can beat hand-crafted ones if robustness is managed (H1, H2, I1). Because each full-system trial is expensive, a companion literature grew around doing more with fewer trials: BO for few-trial config search (E1), surrogate-model search (J2), workload/DBMS transfer (J1), cross-scale migration (C7), few-shot cross-task surrogates (J3). Self-adaptive systems (F1, F2) and MAPE-K/autonomic computing (G1, G2) supply the unifying loop — monitor workload and runtime signals, decide, act, retain knowledge — inside which AQE is one within-query instance and a learned configuration policy would be a cross-execution instance. The remaining question is whether the cross-execution, budgeted, workload-aware policy instance works for Spark configuration selection under single-machine constraints and generalizes to unseen workloads. That is the empirical question this project is designed to test — not a result the literature already supplies.

## 4. Research Gap Addressed by This Study

The reviewed literature indicates the following, scoped strictly to the 30-row corpus examined in this study. The surveyed work predominantly covers (i) Spark foundations and within-query adaptation (A, B), (ii) per-application or per-setting configuration tuning (C), (iii) RL for adjacent resource/scheduling/execution decisions (D, E2, C6, I2), (iv) BO/surrogate few-trial search (E1, J2, J3) and transfer in adjacent domains (J1, C7), (v) self-adaptive/MAPE-K framing (F, G), and (vi) learned query/execution components (H, I).
The remaining question investigated by this project is whether a **sample-efficient, cross-execution learning formulation for Spark configuration selection** — a compact workload-context + runtime-feedback state mapped to a small discrete configuration action space, learned within a bounded execution budget via an execution cache, compared against default/static/rule-based/equal-budget-random strategies with an explicit AQE-on comparison condition, and evaluated for generalization on unseen workloads — can measurably improve median execution time on a single-node deployment without failed submitted configurations.

This is the research question, not a result. The surveyed approaches do not, at verified scope, jointly demonstrate that combination for Spark configuration selection; whether it succeeds is determined by EXP-002 (sensitivity gate), EXP-004/EXP-005 (bounded learning and comparison), EXP-006/EXP-010 (generalization), and EXP-005b (AQE complementarity). No priority ("first"/"only") is claimed.

## 5. Why the Gap Matters

1. **Performance variability is workload-dependent.** Because influence varies across applications (C1) and one setting across workloads leaves performance untapped (C4), static defaults risk systematic waste — the premise tested at the EXP-002 gate (H1/SC1).
2. **Tuning effort does not scale by hand.** Tuning is highly costly and expertise-requiring (C4); improper settings cause degradation and instability (C5). An automated, workload-aware policy would reduce per-workload expert labor — if it works.
3. **Experiment cost dominates single-machine research.** BO/RL instance collection on Spark is itself reported infeasible at scale (C7); each evaluation costs a full run (E1). A bounded (≤500), cached, offline-initialized design is therefore a practical necessity, not an embellishment (SC6).
4. **Workload change is the norm.** Application-specific models (C1), non-generalizing BO selection (E1), and learned-optimizer robustness concerns (H1) jointly imply that a policy untested on unseen workloads is an incomplete answer — hence the frozen unseen-test evaluation (H4/SC5).
5. **Within-query adaptation does not close the loop.** AQE improves single executions (B1) but does not learn across them; measuring complementarity rather than assuming substitution (RQ6/EXP-005b) is the practically useful question for Spark users who will run with AQE on.
## 6. Claim-to-Evidence Trace

| Claim (§1–§2) | Supporting Rows | Evidence Strength |
|---|---|---|
| In-memory model / order-of-magnitude gains | A1, A5, A4 | STRONG (abstracts read) |
| Shark → Spark SQL → AQE lineage | A6, A2, B1 | MODERATE (A6/A2 abstracts; B1 industry/docs, non-peer-reviewed) |
| Configuration sensitivity + workload dependence | C4, C5, C1 | STRONG (abstracts read) |
| Six-family tuning taxonomy + verified instances | C5, C1, C7 | STRONG (abstracts); C2/C3 title-scope → LIMITED for those two |
| RL for systems/scheduling/execution decisions | D1, E2, C6, I2 | MODERATE (E2/I2 abstracts verbatim; D1/C6 title-scope → LIMITED) |
| Few-trial / surrogate / transfer sample efficiency | E1, J2, J1, J3, C7 | MODERATE (J3/C7 abstracts; E1/J1/J2 title-scope → LIMITED) |
| Self-adaptive taxonomy + roadmap | F1, F2 | LIMITED (title/venue-scoped; F2 chapter not fetched) |
| MAPE-K reference model + survey | G1, G2 | MODERATE (G2 abstract verbatim; G1 title-scope → LIMITED) |
| Learned optimizers / indexes viability + robustness | H1, H2, I1 | MODERATE (H2 abstract verbatim; H1 abstract; I1 title-scope → LIMITED) |
| Experimentation cost barrier | C4, C7, E1 | STRONG for C4/C7 (abstracts); LIMITED for E1 scope |
| Gap-combination not jointly demonstrated (scoped) | All 30 (absence at verified scope) | MODERATE — bounded by abstract-level evidence; full texts may qualify it (see LITERATURE_EVIDENCE_LIMITATIONS.md) |

*Strength key: STRONG = peer-reviewed abstract read verbatim; MODERATE = abstract read for key rows, siblings title-scoped; LIMITED / ABSTRACT-LEVEL = title/venue or un-fetched-abstract scope. No claim rests on full-text inspection; see `docs/research/LITERATURE_EVIDENCE_LIMITATIONS.md`.*
