# Literature Matrix A–C

**Project:** Self-Adaptive Big Data Programming Using Reinforcement Learning and Spark
**Phase:** Days 6–10 (PLAN.md §5) — Categories A–C populated on Day 6; sources verified on Day 6 (2026-09-08)

**Verification policy:**
- **VERIFIED — <source>** = bibliographic details and claims checked against an authoritative record on 2026-09-08 via USENIX proceedings pages, CrossRef/DOI records, OpenAlex, Semantic Scholar, Springer article pages, or the official Apache Spark documentation. The exact source link is included in every row.
- Every row distinguishes **SOURCE-REPORTED** claims (directly supported by the fetched abstract/record) from **OUR INTERPRETATION** (this project's reading).
- Full texts behind paywalls were not fetched; claims for those rows are scoped to verified abstracts/titles and flagged for full-text inspection on Days 8–10.

> **Honesty note (Day 6, updated):** All 14 rows were verified against real, authoritative publication records this session; no [TK] rows remain. Three rows retained in place with corrections (A1, A2, B1 — B1's authors corrected from an unverifiable attribution to the blog's actual authors); nine unverifiable "representative" entries were REPLACED with verified papers (decisions and reasons in docs/research/LITERATURE_VERIFICATION_LOG.md); one verified row was added (C6). Claims not supported by the fetched record were corrected or removed, including the A1 speedup figure (10–100× → 10x per the abstract) and B1's venue (a Databricks blog + Spark docs, not VLDB).

---

## Matrix Schema

| ID | Category | Paper | Authors | Year | Venue | DOI / Stable Link | Research Problem | Method | Context | Optimization Target | Parameters / Knobs | Dataset / Workload | Evaluation Metrics | Main Verified Finding | Limitation | Relevance | Research Gap | Verification |
|----|----------|-------|---------|------|-------|-------------------|------------------|--------|---------|---------------------|--------------------|--------------------|--------------------|-----------------------|------------|------------|--------------|--------------|

---

## Category A — Spark Performance Optimization

### A1
| Field | Content |
|-------|---------|
| ID | A1 |
| Category | A |
| Paper | Spark: Cluster Computing with Working Sets |
| Authors | Matei Zaharia, Mosharaf Chowdhury, Michael J. Franklin, Scott Shenker, Ion Stoica |
| Year | 2010 |
| Venue | 2nd USENIX Workshop on Hot Topics in Cloud Computing (HotCloud '10), Boston, MA |
| DOI / Stable Link | https://www.usenix.org/conference/hotcloud-10/spark-cluster-computing-working-sets |
| Research Problem | Efficiently support iterative and interactive data analytics workloads that MapReduce handles poorly due to repeated disk I/O. |
| Method | SOURCE-REPORTED (abstract): Proposes resilient distributed datasets (RDDs) — read-only, partitioned collections of objects partitioned across machines that can be rebuilt if a partition is lost — retaining the scalability and fault tolerance of MapReduce. |
| Context | Foundational Spark paper; establishes the RDD abstraction and core execution model. |
| Optimization Target | Execution time for iterative machine-learning and interactive analysis workloads. |
| Parameters / Knobs | Not a tuning paper; establishes the platform. |
| Dataset / Workload | Iterative machine-learning jobs; interactive analysis over a 39 GB dataset (per the verified abstract). |
| Evaluation Metrics | Execution time relative to Hadoop MapReduce; interactive-query response time. |
| Main Verified Finding | SOURCE-REPORTED (abstract): Spark can outperform Hadoop by 10x for iterative machine-learning jobs, and was used to interactively query a 39 GB dataset with sub-second response time. |
| Limitation | Focuses on the programming model and memory abstraction, not on automatic configuration or adaptive execution. |
| Relevance | OUR INTERPRETATION: establishes the Spark execution model and the performance motivation (memory, partitioning, iterative workloads) that this project's RL agent later optimizes. |
| Research Gap | Does not address automatic configuration selection or runtime adaptation. |
| Verification | VERIFIED — USENIX HotCloud '10 proceedings page (https://www.usenix.org/conference/hotcloud-10/spark-cluster-computing-working-sets); BibTeX and author list checked; abstract cross-checked via OpenAlex. |

### A2
| Field | Content |
|-------|---------|
| ID | A2 |
| Category | A |
| Paper | Spark SQL: Relational Data Processing in Spark |
| Authors | Michael Armbrust, Reynold S. Xin, Cheng Lian, Yin Huai, Davies Liu, Joseph K. Bradley, Xiangrui Meng, Tomer Kaftan, Michael J. Franklin, Ali Ghodsi, Matei Zaharia |
| Year | 2015 |
| Venue | Proceedings of the 2015 ACM SIGMOD International Conference on Management of Data (SIGMOD/PODS '15), Melbourne, pp. 1383–1394 |
| DOI / Stable Link | https://doi.org/10.1145/2723372.2742797 |
| Research Problem | Integrate relational (SQL) processing into Spark's functional programming API, building on the authors' experience with Shark. |
| Method | SOURCE-REPORTED (abstract): Two main additions — tight integration between procedural (RDD) and declarative (SQL/DataFrame) processing, and the highly extensible Catalyst optimizer built using Scala language features. |
| Context | Core Spark SQL paper; the static Catalyst optimizer is the substrate that AQE later extends at runtime. |
| Optimization Target | Query execution time for SQL workloads. |
| Parameters / Knobs | Catalyst optimization rules and join strategies (per abstract's framing of the optimizer). |
| Dataset / Workload | Per the abstract: use cases include schema inference for JSON data, ML data types, and query federation to external databases; detailed evaluations are in the paywalled full text. |
| Evaluation Metrics | Not verifiable from accessible metadata (the abstract makes no performance claims); full text is paywalled. |
| Main Verified Finding | SOURCE-REPORTED (abstract): Spark SQL integrates relational processing with Spark's functional API; the authors position it as an evolution of both SQL-on-Spark and Spark itself. The abstract makes no specific performance claims. |
| Limitation | Catalyst is a static optimizer; nothing in the verified abstract addresses runtime adaptation of configuration or learning from past executions. |
| Relevance | OUR INTERPRETATION: establishes the SQL execution path and the static optimizer that this project's RL agent complements by selecting execution configuration. |
| Research Gap | Static optimization; no runtime adaptation of shuffle partitions, parallelism, or resource configuration. |
| Verification | VERIFIED — ACM/CrossRef DOI record (https://doi.org/10.1145/2723372.2742797), pp. 1383–1394, SIGMOD/PODS '15, Melbourne; abstract cross-checked via OpenAlex. |

### A3
| Field | Content |
|-------|---------|
| ID | A3 |
| Category | A |
| Paper | Making Sense of Performance in Data Analytics Frameworks |
| Authors | Kay Ousterhout, Ryan Rasti, Sylvia Ratnasamy, Scott Shenker, Byung-Gon Chun |
| Year | 2015 |
| Venue | 12th USENIX Symposium on Networked Systems Design and Implementation (NSDI '15) |
| DOI / Stable Link | https://amplab.cs.berkeley.edu/wp-content/uploads/2015/04/nsdi15-final147.pdf |
| Research Problem | SOURCE-REPORTED (abstract): Much research is devoted to improving the performance of data analytics frameworks, but comparatively little effort has been spent systematically identifying the bottlenecks in these systems. |
| Method | SOURCE-REPORTED (abstract): Develops "blocked time analysis", a methodology for quantifying bottlenecks in distributed computation, and uses it to analyze the Spark framework's performance on two SQL benchmarks and a production workload. |
| Context | Performance characterization of Spark; complements tuning studies by explaining where execution time goes. |
| Optimization Target | Understanding and reducing job completion time (bottleneck identification). |
| Parameters / Knobs | Not a tuning paper; provides bottleneck analysis (CPU, I/O, network, stragglers). |
| Dataset / Workload | Two SQL benchmarks and a production workload on Spark (per the verified abstract). |
| Evaluation Metrics | Blocked time (bottleneck quantification), job completion time. |
| Main Verified Finding | SOURCE-REPORTED (abstract): Contrary to expectations, the study finds that (i) CPU — and not I/O — is often the bottleneck, (ii) network improvements can improve job completion time by a median of at most 2%, and (iii) the causes of stragglers can be identified. |
| Limitation | Analyzes bottlenecks and stragglers; it does not propose automated configuration selection or an adaptive policy. |
| Relevance | OUR INTERPRETATION: supports the project's measurement discipline (task-duration distributions, bottleneck reporting) and cautions that CPU-side costs matter when interpreting configuration effects on a single machine. |
| Research Gap | Identifies bottlenecks but does not address configuration selection or adaptation. |
| Verification | VERIFIED — OpenAlex record with verified abstract (NSDI '15, UC Berkeley/ICSI); PDF link above. |

### A4
| Field | Content |
|-------|---------|
| ID | A4 |
| Category | A |
| Paper | Big data analytics on Apache Spark |
| Authors | Salman Salloum, Ruslan Dautov, Xiaojun Chen, Patrick Xiaogang Peng, Joshua Zhexue Huang |
| Year | 2016 |
| Venue | International Journal of Data Science and Analytics (Springer), Vol. 1, pp. 145–164 |
| DOI / Stable Link | https://doi.org/10.1007/s41060-016-0027-9 |
| Research Problem | SOURCE-REPORTED (abstract): As a rapidly evolving open-source project with contributors from academia and industry, it is difficult for researchers to comprehend the full body of development and research behind Apache Spark. |
| Method | SOURCE-REPORTED (abstract): A technical review of big data analytics using Apache Spark, focusing on key components, abstractions and features, and what Spark offers for machine learning, graph analysis and stream processing pipelines. |
| Context | Peer-reviewed Spark review (Springer page shows 404 citations and 71k accesses at verification time). |
| Optimization Target | Multiple (survey); performance is discussed via Spark's in-memory programming model and upper-level libraries. |
| Parameters / Knobs | Not a tuning paper. |
| Dataset / Workload | Surveys Spark's capabilities across MLlib, GraphX, Spark Streaming, and Spark SQL. |
| Evaluation Metrics | N/A (review article). |
| Main Verified Finding | SOURCE-REPORTED (abstract): Apache Spark has emerged as the de facto framework for big data analytics with its advanced in-memory programming model and upper-level libraries for scalable machine learning, graph analysis, streaming and structured data processing. |
| Limitation | Review article; does not study configuration tuning or adaptation. |
| Relevance | OUR INTERPRETATION: establishes Spark as the platform and contextualizes the workload families this project uses. |
| Research Gap | Does not address automatic configuration selection. |
| Verification | VERIFIED — Springer article page (https://link.springer.com/article/10.1007/s41060-016-0027-9); title, authors, venue, pages, and abstract read in full. |

### A5
| Field | Content |
|-------|---------|
| ID | A5 |
| Category | A |
| Paper | Resilient Distributed Datasets: A Fault-Tolerant Abstraction for In-Memory Cluster Computing |
| Authors | Matei Zaharia, Mosharaf Chowdhury, Tathagata Das, Ankur Dave, Justin Ma, Murphy McCauly, Michael J. Franklin, Scott Shenker, Ion Stoica |
| Year | 2012 |
| Venue | 9th USENIX Symposium on Networked Systems Design and Implementation (NSDI '12), San Jose, CA, pp. 15–28 (Best Paper Award) |
| DOI / Stable Link | https://www.usenix.org/conference/nsdi12/technical-sessions/presentation/zaharia |
| Research Problem | SOURCE-REPORTED (abstract): Current computing frameworks handle two classes of applications inefficiently — iterative algorithms and interactive data mining tools. |
| Method | SOURCE-REPORTED (abstract): Presents RDDs, a distributed memory abstraction for fault-tolerant in-memory computation, providing a restricted form of shared memory based on coarse-grained transformations rather than fine-grained updates; implemented in Spark and evaluated through user applications and benchmarks. |
| Context | The full NSDI '12 RDD paper; the scholarly version of the Spark foundation (companion to A1's HotCloud '10 workshop paper). |
| Optimization Target | Execution time for iterative and interactive workloads. |
| Parameters / Knobs | Not a tuning paper; establishes the platform. |
| Dataset / Workload | A variety of user applications and benchmarks (per the verified abstract). |
| Evaluation Metrics | Performance relative to disk-based execution; expressiveness of the abstraction. |
| Main Verified Finding | SOURCE-REPORTED (abstract): In both application classes, keeping data in memory can improve performance by an order of magnitude; RDDs are expressive enough to capture a wide class of computations, including specialized iterative models such as Pregel. |
| Limitation | Focuses on the programming model and fault-tolerance abstraction, not on automatic configuration or runtime adaptation. |
| Relevance | OUR INTERPRETATION: establishes the in-memory execution model whose costs (memory pressure, spill, shuffle) motivate this project's configuration actions. |
| Research Gap | Does not address automatic configuration selection or runtime adaptation. |
| Verification | VERIFIED — USENIX NSDI '12 proceedings page (https://www.usenix.org/conference/nsdi12/technical-sessions/presentation/zaharia); full author list, pages, and abstract read from the page; cross-checked via OpenAlex. |

---

## Category B — Spark Adaptive Query Execution / Adaptive Execution

### B1
| Field | Content |
|-------|---------|
| ID | B1 |
| Category | B |
| Paper | Adaptive Query Execution: Speeding Up Spark SQL at Runtime |
| Authors | Wenchen Fan, Herman van Hövell, MaryAnn Xue (Databricks) |
| Year | 2020 (blog published May 29, 2020; AQE shipped in Apache Spark 3.0) |
| Venue | Databricks Engineering Blog + official Apache Spark performance-tuning documentation (industry/official docs — explicitly NOT peer-reviewed) |
| DOI / Stable Link | https://www.databricks.com/blog/2020/05/29/adaptive-query-execution-speeding-up-spark-sql-at-runtime.html |
| Research Problem | SOURCE-REPORTED: Static query plans cannot account for runtime data characteristics (e.g., actual partition sizes after a shuffle), so plans can be suboptimal with respect to join strategies, partition counts, and skew. |
| Method | SOURCE-REPORTED: The Adaptive Query Execution (AQE) framework re-optimizes the query plan at runtime using runtime statistics. Documented features: dynamic coalescing of post-shuffle partitions; runtime join-strategy switching (sort-merge join to broadcast or shuffled-hash join); splitting skewed shuffle partitions and optimizing skew joins. |
| Context | Built into Spark 3.0+ and on by default in current Spark; the implementation-level reference for Spark's built-in adaptive execution. |
| Optimization Target | Query execution time, shuffle efficiency, join strategy selection, skew handling. |
| Parameters / Knobs | AQE is controlled via `spark.sql.adaptive.*` configuration properties (see Spark performance-tuning documentation, Adaptive Query Execution section). |
| Dataset / Workload | The blog includes a TPC-DS section reporting performance gains from enabling AQE (specific figures not re-quoted here; Spark docs describe the behaviors). |
| Evaluation Metrics | Query execution time, post-coalescing shuffle partition counts, join strategy switches, skew task handling. |
| Main Verified Finding | SOURCE-REPORTED: The blog states that AQE "will figure out the data and improve the query plan as the query runs, increasing query performance", documenting the three runtime optimizations above. The Apache Spark documentation specifies the same AQE capabilities. |
| Limitation | All documented adaptation happens within a single query execution; neither source describes cross-execution learning, job-level configuration selection (executor sizing, static parallelism, caching), or policy generalization. |
| Relevance | OUR INTERPRETATION: AQE is the project's key AQE-on comparison condition (RQ6). It adapts within-query; the reviewed sources do not document cross-execution learning or job-level configuration selection, which is the level at which this project's RL agent operates. |
| Research Gap | The documented AQE scope leaves open cross-execution, job-level configuration learning. |
| Verification | VERIFIED — Databricks engineering blog by Wenchen Fan, Herman van Hövell, MaryAnn Xue (May 29, 2020, URL above) + official Apache Spark 4.2.0 performance-tuning documentation (https://spark.apache.org/docs/latest/sql-performance-tuning.html). Industry/official-documentation source, explicitly non-peer-reviewed. |

### B2
| Field | Content |
|-------|---------|
| ID | B2 |
| Category | B |
| Paper | Adaptive Query Processing |
| Authors | Amol Deshpande, Zachary G. Ives, Vijayshankar Raman |
| Year | 2007 |
| Venue | Foundations and Trends in Databases (Now Publishers) |
| DOI / Stable Link | https://doi.org/10.1561/9781601980359 |
| Research Problem | SOURCE-REPORTED (title/venue only): How query processing can adapt at runtime, beyond static plan selection made before execution. |
| Method | Published monograph-length synthesis of adaptive query processing in database systems (bibliographic record verified; full text not fetched in this session). |
| Context | Foundational database-literature treatment of runtime plan adaptation; predates Spark. |
| Optimization Target | Query performance under uncertain or variable data statistics. |
| Parameters / Knobs | Not Spark-specific. |
| Dataset / Workload | N/A (survey monograph). |
| Evaluation Metrics | N/A (survey monograph). |
| Main Verified Finding | Claim limited to what is verifiable from the publication record: the work is a published synthesis of adaptive query processing (title, authors, year, venue, and DOI verified). Detailed claims require the full text, which was not fetched. |
| Limitation | Pre-Spark, general-purpose database context; does not address Spark configuration or cross-execution configuration learning. |
| Relevance | OUR INTERPRETATION: establishes the conceptual lineage (runtime plan adaptation) that AQE instantiates in Spark SQL, supporting the framing of AQE as within-query adaptation. |
| Research Gap | Does not cover cross-execution configuration learning. |
| Verification | VERIFIED — OpenAlex/CrossRef DOI record (https://doi.org/10.1561/9781601980359); bibliographic details verified. |

### B3
| Field | Content |
|-------|---------|
| ID | B3 |
| Category | B |
| Paper | SkewTune: Mitigating Skew in MapReduce Applications |
| Authors | YongChul Kwon, Magdalena Balazinska, Bill Howe, Jerome Rolia |
| Year | 2012 |
| Venue | Proceedings of the 2012 ACM SIGMOD International Conference on Management of Data (SIGMOD/PODS '12), Scottsdale, AZ, pp. 25–36 |
| DOI / Stable Link | https://doi.org/10.1145/2213836.2213840 |
| Research Problem | SOURCE-REPORTED (companion VLDB demonstration abstract): Stragglers caused by skew degrade the performance of data-parallel jobs; how to mitigate skew automatically. |
| Method | SOURCE-REPORTED (companion demonstration abstract): SkewTune is a system that automatically mitigates skew in user-defined MapReduce programs at runtime and acts as a drop-in replacement for Hadoop; demonstrated on real applications running on a public cloud. |
| Context | MapReduce-era runtime skew mitigation (289 citations per CrossRef record at verification time); closely related big-data skew literature. |
| Optimization Target | Job completion time under skew; task-duration balance. |
| Parameters / Knobs | Not a Spark-configuration paper; a runtime re-partitioning mechanism. |
| Dataset / Workload | Real applications with skew on a public cloud (per the demonstration abstract). |
| Evaluation Metrics | Job completion time; skew mitigation at runtime. |
| Main Verified Finding | SOURCE-REPORTED (demonstration abstract): SkewTune automatically mitigates skew in real applications at runtime as a drop-in Hadoop replacement. |
| Limitation | Reactive, within-job mitigation for MapReduce; no learned policy and no Spark-configuration selection. |
| Relevance | OUR INTERPRETATION: supports the F4 skewed-join workload and the task-duration-imbalance metric; skew is a recognized performance problem addressed by runtime mechanisms rather than static configuration. |
| Research Gap | No proactive, learned policy that anticipates skew from workload context. |
| Verification | VERIFIED — ACM/CrossRef DOI record (https://doi.org/10.1145/2213836.2213840), SIGMOD/PODS '12, pp. 25–36, 289 citations; companion demonstration verified at https://doi.org/10.14778/2367502.2367541. |

---

## Category C — Spark Auto-Tuning / Configuration Optimization / Bayesian Optimization / Big-Data Tuning

### C1
| Field | Content |
|-------|---------|
| ID | C1 |
| Category | C |
| Paper | Towards Automatic Tuning of Apache Spark Configuration |
| Authors | Nhan Nguyen, Mohammad Maifi Hasan Khan, Kewen Wang |
| Year | 2018 |
| Venue | 2018 IEEE 11th International Conference on Cloud Computing (IEEE CLOUD) |
| DOI / Stable Link | https://doi.org/10.1109/CLOUD.2018.00059 |
| Research Problem | SOURCE-REPORTED (abstract): It is non-trivial to identify the combination of Spark settings that improves a specific application's performance, because the influence of each setting may vary across applications, and the exponential search space makes identifying the optimal combination computationally infeasible. |
| Method | SOURCE-REPORTED (abstract): Machine-learning-based approaches to construct application-specific performance influence models, used to tune the performance of specific applications running on Apache Spark. |
| Context | Directly addresses the Spark configuration optimization problem this project tackles; the closest published non-RL approach family. |
| Optimization Target | Execution time. |
| Parameters / Knobs | Spark configuration settings generally (per the abstract: "a large number of configuration settings"); specific knobs are enumerated in the paywalled full text. |
| Dataset / Workload | SOURCE-REPORTED (abstract): 9 different applications on a 6-node cluster. |
| Evaluation Metrics | Execution-time reduction (per the abstract). |
| Main Verified Finding | SOURCE-REPORTED (abstract): The authors demonstrate that their framework can reduce execution time by 22.8% to 40.0% depending on the application. |
| Limitation | Models are application-specific; the evaluation used a single 6-node cluster; the abstract does not describe cross-workload policy generalization or online adaptation. |
| Relevance | OUR INTERPRETATION: establishes ML-based Spark configuration tuning as a measured win over defaults, and is the closest non-RL point of comparison for this project's RL approach. |
| Research Gap | Application-specific models; the abstract does not report an online adaptive policy or cross-workload transfer. |
| Verification | VERIFIED — IEEE/CrossRef DOI record (https://doi.org/10.1109/CLOUD.2018.00059) + Semantic Scholar abstract (verbatim). |

### C2
| Field | Content |
|-------|---------|
| ID | C2 |
| Category | C |
| Paper | Tuning configuration of Apache Spark on public clouds by combining multi-objective optimization and performance prediction model |
| Authors | Guoli Cheng, Shi Ying, Bingming Wang |
| Year | 2021 |
| Venue | Journal of Systems and Software (Elsevier) |
| DOI / Stable Link | https://doi.org/10.1016/j.jss.2021.111028 |
| Research Problem | SOURCE-REPORTED (title-verified; publisher elides the abstract): How to tune Apache Spark configurations on public clouds. |
| Method | SOURCE-REPORTED (title-verified): Combines multi-objective optimization with a performance prediction model. |
| Context | Spark configuration tuning via prediction + optimization on public clouds. |
| Optimization Target | Execution time and additional objectives (multi-objective, per title). |
| Parameters / Knobs | Spark configuration parameters (title-verified scope; specifics in paywalled full text). |
| Dataset / Workload | Public clouds (title-verified scope). |
| Evaluation Metrics | Not verifiable from accessible metadata; full text is paywalled. |
| Main Verified Finding | Claim limited to verified scope: the study presents an approach combining multi-objective optimization and a performance prediction model for tuning Spark configurations on public clouds. No quantitative result is claimed here because the abstract is not openly accessible. |
| Limitation | Detailed method and results could not be verified from accessible metadata in this session (abstract elided by publisher). |
| Relevance | OUR INTERPRETATION: exemplifies prediction-model-based tuning, relevant to RQ1 (state/feature representation for performance prediction) and RQ2 (non-RL baseline family). |
| Research Gap | Title-verified scope does not include online policy learning or cross-workload generalization; this must be checked against the full text on Days 8–10. |
| Verification | VERIFIED — Elsevier/CrossRef DOI record (https://doi.org/10.1016/j.jss.2021.111028) via Semantic Scholar (title, authors, venue, year confirmed; abstract elided by publisher). |

### C3
| Field | Content |
|-------|---------|
| ID | C3 |
| Category | C |
| Paper | Empirical Evaluation of Acquisition Functions for Bayesian Optimization-Based Configuration Tuning of Apache Spark Applications |
| Authors | Hyunsik Yoon, Yon Dohn Chung (Korea University) |
| Year | 2025 |
| Venue | IEICE Transactions on Information and Systems (advance publication) |
| DOI / Stable Link | https://doi.org/10.1587/transinf.2024edl8071 |
| Research Problem | SOURCE-REPORTED (title-verified): How to choose acquisition functions for Bayesian-optimization-based configuration tuning of Apache Spark applications. |
| Method | SOURCE-REPORTED (title-verified): Empirical evaluation of acquisition functions for BO-based configuration tuning of Spark applications. |
| Context | In-scope BO-for-Spark tuning study; directly relevant to the project's non-RL baseline family. |
| Optimization Target | Execution time / configuration quality (title-verified scope). |
| Parameters / Knobs | Spark configuration parameters (title-verified scope; specifics in the full text). |
| Dataset / Workload | Apache Spark applications (title-verified scope). |
| Evaluation Metrics | Not verifiable from accessible metadata in this session; gold open-access PDF available at J-Stage for full-text inspection. |
| Main Verified Finding | Claim limited to verified scope: the study empirically evaluates acquisition functions for Bayesian-optimization-based configuration tuning of Apache Spark applications. No quantitative result is claimed here because the abstract was not accessible via Semantic Scholar. |
| Limitation | Journal letter; abstract not accessible in this session; full-text inspection (J-Stage OA PDF) recommended on Days 8–10 before citing specific results. |
| Relevance | OUR INTERPRETATION: evidence that BO-based Spark tuning is an active research line with design choices (acquisition functions) that affect sample efficiency — relevant to RQ2 and RQ5. |
| Research Gap | Title-verified scope covers BO internals, not cross-workload policy learning; check full text on Days 8–10. |
| Verification | VERIFIED — IEICE/CrossRef DOI record (https://doi.org/10.1587/transinf.2024edl8071); gold-OA PDF: https://www.jstage.jst.go.jp/article/transinf/advpub/0/advpub_2024EDL8071/_pdf |

### C4
| Field | Content |
|-------|---------|
| ID | C4 |
| Category | C |
| Paper | BestConfig: Tapping the Performance Potential of Systems via Automatic Configuration Tuning |
| Authors | Yuqing Zhu, Jianxun Liu, Mengying Guo, Yungang Bao, Wenlong Ma, Zhuoyue Liu, Kunpeng Song, Yingchun Yang |
| Year | 2017 |
| Venue | Proceedings of the 2017 ACM Symposium on Cloud Computing (SoCC '17), Santa Clara, CA, pp. 338–350 |
| DOI / Stable Link | https://doi.org/10.1145/3127479.3128605 |
| Research Problem | SOURCE-REPORTED (abstract): An ever-increasing number of configuration parameters are provided to system users; many users apply one setting across different workloads, leaving the performance potential of deployed systems untapped. |
| Method | SOURCE-REPORTED (abstract scope): Automatic configuration tuning for deployed systems (BestConfig). Technique details beyond the abstract were not verified in this session. |
| Context | General system configuration tuning (204 citations per CrossRef record at verification time); configuration search framing for data systems. |
| Optimization Target | Performance of deployed systems under given workloads. |
| Parameters / Knobs | Tens to hundreds of configuration parameters per system (per the verified abstract). |
| Dataset / Workload | Deployed systems under certain workloads (per the verified abstract); system specifics are in the full paper. |
| Evaluation Metrics | Performance improvement from tuned configurations (abstract scope). |
| Main Verified Finding | SOURCE-REPORTED (abstract): A good configuration can greatly improve the performance of a deployed system under certain workloads, and deciding the best configuration with tens or hundreds of parameters is a highly costly task requiring expertise that users commonly lack. |
| Limitation | Abstract-only verification in this session: which systems (and whether Spark specifically) were evaluated could not be confirmed here; treat beyond-abstract specifics as unverified until the full text is inspected. |
| Relevance | OUR INTERPRETATION: directly supports RQ0 (configuration sensitivity) and the workload-dependence motivation; the abstract's workload-dependence framing ("one setting across different workloads") is the RQ0 gate's premise. |
| Research Gap | Abstract scope frames tuning as costly and expertise-requiring; it does not describe cross-workload policy learning. |
| Verification | VERIFIED — ACM/CrossRef DOI record (https://doi.org/10.1145/3127479.3128605), SoCC '17, pp. 338–350, 204 citations; abstract verified via OpenAlex. |

### C5
| Field | Content |
|-------|---------|
| ID | C5 |
| Category | C |
| Paper | A Survey on Automatic Parameter Tuning for Big Data Processing Systems |
| Authors | Herodotos Herodotou, Yuxing Chen, Jiaheng Lu |
| Year | 2020 |
| Venue | ACM Computing Surveys |
| DOI / Stable Link | https://doi.org/10.1145/3381027 |
| Research Problem | SOURCE-REPORTED (abstract): Big data processing systems (e.g., Hadoop, Spark, Storm) contain a vast number of configuration parameters controlling parallelism, I/O behavior, memory settings, and compression; improper parameter settings can cause significant performance degradation and stability issues. |
| Method | SOURCE-REPORTED (abstract): Investigates existing parameter-tuning approaches for batch and stream processing systems and classifies them into six categories: rule-based, cost modeling, simulation-based, experiment-driven, machine learning, and adaptive tuning. |
| Context | Authoritative survey (ACM Computing Surveys) covering the tuning-approach taxonomy for Spark-class systems. |
| Optimization Target | Multiple: performance and stability across batch and stream systems. |
| Parameters / Knobs | Configuration parameters controlling parallelism, I/O behavior, memory settings, and compression (per the verified abstract). |
| Dataset / Workload | Surveys approaches across Hadoop, Spark, Storm (per the verified abstract). |
| Evaluation Metrics | N/A (survey); summarizes pros and cons of each approach category. |
| Main Verified Finding | SOURCE-REPORTED (abstract): The survey classifies tuning approaches into the six categories above, summarizes the pros and cons of each, and raises open research problems for automatic parameter tuning. |
| Limitation | Survey; it identifies open problems rather than providing an adaptive solution. |
| Relevance | OUR INTERPRETATION: supplies the baseline taxonomy for RQ2 (rule-based, cost-model, experiment-driven, ML, adaptive) and directly evidences RQ0's premise that improper settings cause significant degradation. |
| Research Gap | The survey raises open research problems in automatic parameter tuning; our interpretation is that sample-efficient online adaptation remains an open direction. |
| Verification | VERIFIED — ACM/CrossRef DOI record (https://doi.org/10.1145/3381027) + Semantic Scholar abstract (verbatim); bronze-OA PDF at ACM DL. |

### C6
| Field | Content |
|-------|---------|
| ID | C6 |
| Category | C |
| Paper | Performance and Cost-Efficient Spark Job Scheduling Based on Deep Reinforcement Learning in Cloud Computing Environments |
| Authors | Muhammed Tawfiqul Islam, Shanika Karunasekera, Rajkumar Buyya |
| Year | 2021 |
| Venue | IEEE Transactions on Parallel and Distributed Systems |
| DOI / Stable Link | https://doi.org/10.1109/TPDS.2021.3124670 |
| Research Problem | SOURCE-REPORTED (title/venue-verified): Spark job scheduling in cloud computing environments, targeting performance and cost efficiency. |
| Method | SOURCE-REPORTED (title-verified): Deep-reinforcement-learning-based Spark job scheduling in cloud environments. |
| Context | Adjacent RL-for-Spark work: addresses job scheduling rather than configuration selection; published in a top parallel/distributed systems journal. |
| Optimization Target | Performance and cost efficiency of Spark job scheduling in clouds. |
| Parameters / Knobs | Scheduling decisions (title-verified scope; not configuration tuning). |
| Dataset / Workload | Cloud computing environments (title-verified scope). |
| Evaluation Metrics | Not verifiable from accessible metadata in this session; no quantitative claim is made here. |
| Main Verified Finding | Claim limited to verified scope: the study applies deep reinforcement learning to Spark job scheduling for performance and cost efficiency in cloud environments. |
| Limitation | Scheduling rather than configuration selection; abstract was not fetched in this session, so no quantitative claims are made. |
| Relevance | OUR INTERPRETATION: evidence that reinforcement learning is actively applied to Spark optimization problems in strong venues; adjacent to this project's configuration-selection problem and relevant to RQ2 positioning. |
| Research Gap | Scheduling-level, not configuration-level; does not cover cross-workload configuration policies. |
| Verification | VERIFIED — IEEE/CrossRef DOI record (https://doi.org/10.1109/TPDS.2021.3124670), IEEE TPDS, 2021; bibliographic details verified via OpenAlex. |

---

# Synthesis of Literature A–C

## A. What the literature establishes

From the verified sources only:

1. **Spark's in-memory execution model is the performance foundation.** The HotCloud '10 paper reports that Spark can outperform Hadoop by 10x for iterative machine-learning jobs (A1), and the NSDI '12 RDD paper reports that keeping data in memory can improve performance by an order of magnitude for iterative and interactive workloads (A5).

2. **Spark SQL's Catalyst optimizer is a static substrate.** The SIGMOD '15 paper presents Catalyst as a highly extensible optimizer built using Scala features (A2); it is the substrate that AQE later extends at runtime.

3. **Bottlenecks are often not where intuition suggests.** Blocked-time analysis of Spark on SQL benchmarks and a production workload found that CPU — not I/O — is often the bottleneck, that network improvements improve job completion time by a median of at most 2%, and that the causes of stragglers can be identified (A3).

4. **Spark is a general-purpose analytics platform.** A peer-reviewed technical review describes Spark as the de facto framework for big data analytics, with in-memory processing and libraries for ML, graph analysis, streaming and structured data processing (A4).

## B. Why configuration matters

- "A good configuration can greatly improve the performance of a deployed system under certain workloads", and systems expose tens or hundreds of parameters (SOURCE-REPORTED, BestConfig abstract, C4).
- "Improper parameter settings can cause significant performance degradation and stability issues" in big data systems including Spark (SOURCE-REPORTED, Herodotou et al. survey abstract, C5).
- ML-based application-specific performance influence models reduced execution time by 22.8% to 40.0% across 9 applications on a 6-node cluster (SOURCE-REPORTED, Nguyen et al. abstract, C1).

## C. Why optimal configurations are workload-dependent

- Users commonly apply one setting across different workloads, "leaving untapped the performance potential of systems" (SOURCE-REPORTED, C4 abstract).
- "The influence of each setting on performance may vary across applications" (SOURCE-REPORTED, C1 abstract).
- Cloud deployment contexts motivate workload- and environment-specific tuning (title-verified scope, C2).

OUR INTERPRETATION: together, these verified findings make the RQ0 feasibility gate — that configuration sensitivity is real and measurable on this project's single 32 GB machine — a defensible premise to test empirically (EXP-002).

## D. Role of AQE

AQE (B1) is the most important comparison point for this project. What the verified sources document:

- AQE re-optimizes the query plan at runtime: it dynamically coalesces post-shuffle partitions, splits skewed shuffle partitions, converts sort-merge joins to broadcast or shuffled-hash joins at runtime, and optimizes skew joins (SOURCE-REPORTED: Databricks blog + Apache Spark documentation, B1).
- AQE is controlled via `spark.sql.adaptive.*` properties and is built into Spark 3.0+ (B1).

What the verified sources do NOT document (OUR INTERPRETATION):

- Cross-execution learning: AQE re-optimizes within a single query execution; the sources do not describe learning from past executions.
- Job-level configuration selection: executor sizing, static parallelism, or caching strategy are not part of the documented AQE feature set.
- Policy generalization: the sources do not describe a policy that transfers across workloads.

This project therefore treats AQE-on as a dedicated comparison condition (RQ6) to measure complementarity, not as a substitute for a learned configuration policy. Database-literature precedent for runtime plan adaptation is documented in B2; runtime skew mitigation in the MapReduce era in B3.

## E. Role of automated configuration tuning

From the verified sources:

- A survey classifies automatic parameter tuning for big-data systems into six categories — rule-based, cost modeling, simulation-based, experiment-driven, machine learning, and adaptive tuning — and raises open research problems (SOURCE-REPORTED, C5).
- Application-specific ML performance influence models reduce execution time by 22.8–40.0% (SOURCE-REPORTED, C1 abstract).
- Multi-objective optimization combined with performance prediction models is applied to Spark tuning on public clouds (title-verified, C2).
- Bayesian-optimization-based tuning of Spark applications is an active research line, with empirical work evaluating acquisition-function choices (title-verified, C3).
- Automated configuration tuning for deployed systems is framed as highly costly and expertise-requiring in its problem statement (SOURCE-REPORTED, C4 abstract).
- Deep RL has been applied to Spark job scheduling in clouds (title-verified, C6).

OUR INTERPRETATION: the published evidence supports that automated tuning yields measurable gains (C1) and that the field is active (C3, C6), but the verified material does not establish that existing approaches deliver cross-workload, online, sample-efficient configuration policies — this must be checked against full texts on Days 8–10.

## F. Where Bayesian / black-box optimization fits

Bayesian-optimization-based tuning is the strongest non-RL baseline family for this project (C3 documents its study for Spark applications; C4 frames the configuration-decision problem as costly). Key distinctions (OUR INTERPRETATION):

- BO-based tuning produces configurations for a given optimization run; this project's RL formulation produces a policy mapping workload state to configuration.
- The verified material does not yet quantify BO-for-Spark trial counts or comparisons against random/grid search (C3's full text has not been inspected); the previous draft's claims of "fewer trials than random/grid search" were unverified and have been removed.
- The project's random-search baseline (equal budget) controls for whether any observed gain is attributable to exploration alone.

## G. Remaining gap relevant to this research

The reviewed literature predominantly addresses Spark adaptation either within a single query execution (AQE; B1, with conceptual lineage in B2 and runtime skew mitigation in B3) or through tuning approaches that construct models or search configurations for a fixed setting (C1–C4, C6), with the approach families catalogued in a survey (C5).

The remaining question investigated by this study is whether a sample-efficient, cross-execution learning formulation for Spark configuration selection can measurably improve execution time relative to Spark defaults, static/rule heuristics, and equal-budget random search — evaluated with AQE as an explicit comparison condition (RQ6) — within the compute budget of a single 32 GB machine, and how far such a policy generalizes to unseen workloads (RQ3, H4).

This is a scoping statement, not a novelty claim: the survey literature (C5) treats adaptive tuning as one of several open-ended directions, and full-text inspection of C2/C3/C4/C6 on Days 8–10 is required before making any claim about what prior work has or has not combined.

---

# Relevance to Frozen Research Problem

| RQ | Supporting Literature | How It Supports the RQ |
|----|----------------------|------------------------|
| RQ0 (config sensitivity gate) | C1, C4, C5, A3 | C5 (verified abstract): improper settings cause significant degradation; C4 (verified abstract): a good configuration greatly improves performance for certain workloads; C1 (verified abstract): 22.8–40.0% execution-time reductions across 9 applications; A3 (verified abstract): bottleneck structure is measurable. Together these justify EXP-002. |
| RQ1 (state representation) | C1, C2, B1 | C1: application-specific performance influence models (features → performance); C2: performance prediction model (title-verified); B1: AQE's use of runtime statistics shows runtime signals carry adaptation-relevant information. |
| RQ2 (RL vs baselines) | C1, C2, C3, C4, C6 | Non-RL baseline families: ML influence models (C1), multi-objective + prediction (C2), BO with acquisition functions (C3), automated configuration tuning (C4); RL applied to adjacent Spark scheduling (C6). Supports the baseline taxonomy and the RL-vs-non-RL comparison. |
| RQ3 (generalization) | C1, C5 | C1's verified abstract describes application-specific models (influence varies across applications), motivating explicit generalization testing; C5 raises open research problems in automatic parameter tuning. |
| RQ4 (reward/action design) | C1, C4, B1 | C1: execution-time as the tuning objective with measurable reductions; C4: configuration-parameter framing (tens to hundreds of knobs); B1: AQE's knob families (`spark.sql.adaptive.*`) inform the action-space boundary. |
| RQ5 (training cost/overhead) | C1, C4, C3 | C1 (verified abstract): the exponential search space is computationally infeasible — motivating sample efficiency; C4 (verified abstract): deciding the best configuration is highly costly; C3: acquisition-function evaluation is explicitly about BO efficiency for Spark tuning. |
| RQ6 (AQE complementarity) | B1, B2, B3 | B1 (documented AQE scope: within-query adaptation only); B2 (adaptive query processing lineage); B3 (skew handled by runtime mechanisms) — together motivate the AQE-on comparison condition rather than treating AQE as a substitute. |

---

# Verification Notes

**Verification status (Day 6, 2026-09-08):** All 14 rows are marked **VERIFIED — <source>** with the exact source link in the row. No `[TK]` rows remain.

**How verification was performed (this session, via web fetch):**

- **USENIX** (A1, A5): proceedings pages read directly, including BibTeX (title, authors, year, venue, pages) and abstract text.
- **CrossRef DOI registry** (A2, B3, C1, C2, C3, C4, C5, C6): DOI metadata records read directly (title, subtitle, authors, venue, pages, year, citation counts).
- **OpenAlex** (A1, A2, A3, A4, A5, B2, B3, C4, C6, and discovery searches): abstract-inverted-index abstracts reconstructed and checked.
- **Semantic Scholar** (C1, C2, C3, C5): bibliographic records and abstracts (C2's abstract is elided by the publisher).
- **Springer** (A4): article page read in full (title, authors, venue, pages, abstract).
- **Databricks + Apache Spark docs** (B1): blog post and official performance-tuning documentation read; explicitly labeled industry/official-documentation, non-peer-reviewed.

**Verification method limitations (recorded honestly):**

- Paywalled full texts were not fetched. Claims for A2, C2, C3, C4, C6 are therefore scoped to verified abstracts/titles, and each row's Limitation field flags what still needs full-text inspection on Days 8–10.
- No claim in this matrix goes beyond what the fetched record supports. Where the earlier [TK] draft asserted specifics that the fetched record does not support (e.g., "10–100× speedup" for A1; "BO outperforms grid search"; "AQE significantly improves TPC-DS performance" as a paper claim), those claims were corrected or removed.
- Two originally-cited works could not be located in any authoritative record and were replaced: the HotCloud 2013 "Optimizing Shuffle Performance in Apache Spark" attribution (link returned HTTP 404) and "CherryPie: Automatic Spark Configuration Tuning via Provenance-Based Optimization" (no record in OpenAlex/Semantic Scholar/CrossRef searches). See docs/research/LITERATURE_VERIFICATION_LOG.md.
- Per the project's no-fabrication policy: no title, author, year, venue, DOI, method, dataset, metric, finding, or limitation is asserted beyond the fetched source. Rows distinguish SOURCE-REPORTED claims from OUR INTERPRETATION.

**Structural validation:** `scripts/validate_literature_matrix.py` checks structure only (fields, verification status, URLs, duplicates, sections). A "VERIFIED" string is not proof of authenticity; human/source inspection — the checks above — is the verification step.

---

# References

[1] Zaharia, Chowdhury, Franklin, Shenker, Stoica. "Spark: Cluster Computing with Working Sets." 2nd USENIX Workshop on Hot Topics in Cloud Computing (HotCloud '10), 2010. https://www.usenix.org/conference/hotcloud-10/spark-cluster-computing-working-sets (A1)
[2] Armbrust, Xin, Lian, Huai, Liu, Bradley, Meng, Kaftan, Franklin, Ghodsi, Zaharia. "Spark SQL: Relational Data Processing in Spark." ACM SIGMOD 2015, pp. 1383–1394. https://doi.org/10.1145/2723372.2742797 (A2)
[3] Ousterhout, Rasti, Ratnasamy, Shenker, Chun. "Making Sense of Performance in Data Analytics Frameworks." USENIX NSDI '15. https://amplab.cs.berkeley.edu/wp-content/uploads/2015/04/nsdi15-final147.pdf (A3)
[4] Salloum, Dautov, Chen, Peng, Huang. "Big data analytics on Apache Spark." International Journal of Data Science and Analytics 1, 145–164 (2016). https://doi.org/10.1007/s41060-016-0027-9 (A4)
[5] Zaharia, Chowdhury, Das, Dave, Ma, McCauly, Franklin, Shenker, Stoica. "Resilient Distributed Datasets: A Fault-Tolerant Abstraction for In-Memory Cluster Computing." USENIX NSDI '12, pp. 15–28 (Best Paper). https://www.usenix.org/conference/nsdi12/technical-sessions/presentation/zaharia (A5)
[6] Fan, van Hövell, Xue. "Adaptive Query Execution: Speeding Up Spark SQL at Runtime." Databricks Engineering Blog, May 29, 2020 (industry, non-peer-reviewed) + Apache Spark performance-tuning documentation. https://www.databricks.com/blog/2020/05/29/adaptive-query-execution-speeding-up-spark-sql-at-runtime.html (B1)
[7] Deshpande, Ives, Raman. "Adaptive Query Processing." Foundations and Trends in Databases, 2007. https://doi.org/10.1561/9781601980359 (B2)
[8] Kwon, Balazinska, Howe, Rolia. "SkewTune: Mitigating Skew in MapReduce Applications." ACM SIGMOD 2012, pp. 25–36. https://doi.org/10.1145/2213836.2213840 (B3)
[9] Nguyen, Khan, Wang. "Towards Automatic Tuning of Apache Spark Configuration." IEEE CLOUD 2018. https://doi.org/10.1109/CLOUD.2018.00059 (C1)
[10] Cheng, Ying, Wang. "Tuning configuration of Apache Spark on public clouds by combining multi-objective optimization and performance prediction model." Journal of Systems and Software, 2021. https://doi.org/10.1016/j.jss.2021.111028 (C2)
[11] Yoon, Chung. "Empirical Evaluation of Acquisition Functions for Bayesian Optimization-Based Configuration Tuning of Apache Spark Applications." IEICE Transactions on Information and Systems, 2025. https://doi.org/10.1587/transinf.2024edl8071 (C3)
[12] Zhu, Liu, Guo, Bao, Ma, Liu, Song, Yang. "BestConfig: Tapping the Performance Potential of Systems via Automatic Configuration Tuning." ACM SoCC '17, pp. 338–350. https://doi.org/10.1145/3127479.3128605 (C4)
[13] Herodotou, Chen, Lu. "A Survey on Automatic Parameter Tuning for Big Data Processing Systems." ACM Computing Surveys, 2020. https://doi.org/10.1145/3381027 (C5)
[14] Islam, Karunasekera, Buyya. "Performance and Cost-Efficient Spark Job Scheduling Based on Deep Reinforcement Learning in Cloud Computing Environments." IEEE TPDS, 2021. https://doi.org/10.1109/TPDS.2021.3124670 (C6)
