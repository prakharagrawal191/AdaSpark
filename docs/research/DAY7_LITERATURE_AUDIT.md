# Day 7 Literature Audit

*AdaSpark · Day 7 (2026-09-08) · scope: Literature A–C only (PLAN.md §31, Days 6–7 block)*

## Coverage

- **A — Spark performance behavior / execution lineage:** 6 rows (A1 Zaharia HotCloud '10; A2 Spark SQL SIGMOD '15; A3 Ousterhout et al. NSDI '15; A4 Salloum et al. IJDSA '16; A5 RDD NSDI '12; A6 Shark SIGMOD '13)
- **B — AQE / adaptive execution:** 3 rows (B1 AQE blog + Spark docs; B2 Deshpande/Ives/Raman, FnT Databases 2007; B3 SkewTune SIGMOD '12)
- **C — Spark configuration / automatic tuning / BO / search:** 7 rows (C1 Nguyen et al. IEEE CLOUD '18; C2 Cheng et al. JSS '21; C3 Yoon & Chung IEICE '25; C4 BestConfig SoCC '17; C5 Herodotou et al. ACM CSUR '20; C6 Islam et al. IEEE TPDS '21; C7 Lin et al. ICDE '22)
- **Total: 16 verified rows** (frozen Day-7 target: ≥15 — met)

## Verification status

- 16/16 rows marked `VERIFIED — <specific source>` with exact source links; 0 [TK]; 0 EXCLUDED.
- Claim scopes are explicit per row: full abstract verified for A1, A2, A3 (page abstract), A4, A5, B3 (demo abstract), C1, C4, C5, C7; title/venue-scoped for B2, C2, C3, C6; implementation-facts scope for B1 (blog + docs, non-peer-reviewed).
- A3 was corrected during this audit: canonical USENIX NSDI '15 page, pp. 293–307, and the abstract's exact wording "the causes of most stragglers can be identified".

## Replaced/excluded entries

- Day 6 replaced 10 unverifiable representative rows (A3-old shuffle paper [404 link], A4-old, A5-old, B2-old, B3-old, C1-old, C3-old "CherryPie" [no record found], C4-old, C5-old, and the C2-old ML/RL entry) — see `docs/research/LITERATURE_VERIFICATION_LOG.md`.
- Day 7 excluded nothing and replaced nothing; additions only (A6, C7) plus the A3 correction.

## Strongest evidence

1. **Measured tuning gains:** ML-based application-specific performance influence models reduce Spark execution time by **22.8–40.0%** across 9 applications (C1, verbatim abstract) — configuration selection is a real, measured lever.
2. **Sample-efficiency barrier stated in the literature itself:** the ICDE 2022 LITE paper states it is **infeasible for Bayesian optimization and reinforcement learning to collect sufficient training instances or repeatedly execute Spark applications** on big data (C7, verbatim abstract) — the premise for this project's cache-bounded, tabular design.
3. **Config/workload dependence:** "a good configuration can greatly improve the performance of a deployed system under certain workloads"; users applying one setting across workloads leave "untapped the performance potential of systems" (C4 abstract); improper settings cause "significant performance degradation and stability issues" (C5 abstract).
4. **AQE scope is documented and bounded:** runtime coalescing, join-strategy switching, and skew-join optimization within a single query (B1 blog + docs); runtime plan adaptation has deep DB lineage (B2) and even appears in the Spark lineage pre-AQE via Shark's dynamic mid-query replanning (A6).
5. **Performance characterization discipline:** blocked-time analysis shows CPU — not I/O — is often the bottleneck and network improvements buy at most a 2% median (A3), informing how configuration effects should be measured on a single machine.

## Current research gap

Unchanged from Day 6 (per the freeze discipline — no stronger claim than evidence supports): the reviewed literature predominantly addresses Spark adaptation either within a single query execution (AQE; B1, lineage in B2, runtime skew mitigation in B3) or through tuning approaches that construct models or search configurations for a fixed setting (C1–C4, C6–C7), with approach families catalogued by survey (C5). The remaining question investigated by this project is whether a sample-efficient, cross-execution learning formulation for Spark configuration selection can measurably improve execution time relative to defaults, static/rule heuristics, and equal-budget random search — with AQE-on as an explicit comparison condition — within a single 32 GB machine, and how far it generalizes to unseen workloads.

C7 sharpens (but does not change) this gap: it addresses the budget barrier via knowledge migration and model adaptation, not via a cross-workload decision policy evaluated on unseen workloads — full-text check queued for Days 8–10 before any stronger statement.

## Remaining limitations

- C2, C3, C4, C6, C7 claims are abstract/title-scoped; full texts not retrieved this session (IEEE Xplore/Elsevier paywalls). Queued for Days 8–10.
- C7 author-name discrepancy between Semantic Scholar ("Jia-geng Feng") and OpenAlex ("Jiadong Feng") — needs an IEEE Xplore check.
- B1 remains an industry/documentation source (explicitly non-peer-reviewed); no peer-reviewed Spark-AQE evaluation was locatable in OpenAlex/Semantic Scholar title searches this session (searched: "adaptive query execution" titles ×23, "spark adaptive" titles, "spark.sql.adaptive" fulltext — zero/full-text-unindexed).
- The B category is the thinnest (3 rows); one peer-reviewed AQE evaluation would materially strengthen it.

## Day-8 literature needs

Per the frozen plan (Days 8–9: "Literature D–J — RL-for-systems, MAPE-K, learned optimizers — 30 matrix rows"), Days 8–10 must add verified rows for:

- **Reinforcement learning for systems optimization** (RL for resource allocation, scheduling, and configuration in data systems) — C6 (Islam et al., TPDS '21) is currently the only adjacent RL row.
- **RL / resource allocation** specifically for cluster and big-data systems.
- **Self-adaptive systems** foundations (the MAPE-K loop that RESEARCH_PROBLEM.md §1 frames as the project's motivation).
- **MAPE-K / autonomic computing** literature (PLAN.md §5 search string "MAPE-K autonomic computing").
- **Learned query optimization** (PLAN.md §5 search string "learned query optimization") — DBMS-side learned optimizers that RESEARCH_PROBLEM.md §2 distinguishes from Spark-configuration tuning.
- **Learned execution optimization** (Spark/big-data execution planning).

Also queued: full-text inspections (C2, C3, C4, C6, C7) and the C7 author-name check on IEEE Xplore.