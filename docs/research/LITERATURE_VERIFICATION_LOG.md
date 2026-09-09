# Literature Verification Log — Day 6 (2026-09-08)

**Scope:** Source verification of `docs/LITERATURE_MATRIX.md` rows (categories A–C).

**Methods used (all via live web fetch this session):** USENIX proceedings pages (title/authors/year/venue/pages/BibTeX + abstract), CrossRef DOI records, OpenAlex records (including abstract-inverted-index reconstruction), Semantic Scholar records, Springer article pages, Databricks engineering blog, official Apache Spark documentation. dblp was attempted but is bot-blocked (Anubis); CrossRef was intermittently rate-limited (HTTP 429) and retried.

**Decision key:** VERIFIED = retained source, bibliographic + claim level checked. REPLACED = original row could not be verified and was substituted by a verified source. EXCLUDED = removed without replacement (none in this pass).

| ID | Source | Verification method | Bibliographic verified | Claim verified | Decision | Why / Notes |
|----|--------|----------------------|------------------------|----------------|----------|-------------|
| A1 | USENIX HotCloud '10 proceedings page | Web fetch of page (BibTeX + author list) + OpenAlex abstract | Yes — title, 5 authors, 2010, HotCloud '10, Boston, MA | Yes — abstract: "outperform Hadoop by 10x for iterative machine learning jobs"; 39 GB interactive query | VERIFIED (retained) | Corrected claimed "10–100× speedup" to 10x per the verified abstract; workload/metric fields re-scoped to the abstract. |
| A2 | ACM DL DOI 10.1145/2723372.2742797 | CrossRef record + OpenAlex abstract | Yes — SIGMOD/PODS '15, Melbourne, pp. 1383–1394, 11 authors, 985 citations | Partial — abstract only; the abstract makes no performance claims | VERIFIED (retained) | Removed unverifiable claims (TPC-DS/Facebook workloads, "speedup over Shark/Hive", "state-of-the-art performance") — none supported by the abstract. |
| A3 (orig.) | Claimed: "Optimizing Shuffle Performance in Apache Spark" (Davidson/Or), USENIX HotCloud 2013 | USENIX link fetch | No — link returned HTTP 404; no record found via OpenAlex/Semantic Scholar/CrossRef | No | REPLACED | Attribution unverifiable. Replaced with Ousterhout et al., "Making Sense of Performance in Data Analytics Frameworks" (USENIX NSDI '15) — verified abstract; supports the project's measurement/metric discipline. |
| A4 (orig.) | Claimed "Tuning Apache Spark: An Empirical Study of Parameter Sensitivity" (representative entry) | CrossRef/OpenAlex bibliographic searches | No — no matching specific publication located | No | REPLACED | Representative entry, not a real citable source. Replaced with Salloum et al., "Big data analytics on Apache Spark" (Springer IJDSA 2016) — full abstract read on Springer. Configuration-sensitivity evidence now rests on C1/C4/C5 (verified abstracts). |
| A5 (orig.) | Claimed "A Survey on Performance Optimization of Apache Spark" (representative entry) | CrossRef/OpenAlex searches | No — no matching specific publication found | No | REPLACED | Replaced with Zaharia et al., "Resilient Distributed Datasets" (USENIX NSDI '12, Best Paper) — full author list, pages 15–28, and abstract verified from the USENIX page. |
| B1 | Databricks Engineering Blog (May 29, 2020) + Apache Spark 4.2.0 performance-tuning docs | Web fetch of blog + docs | Yes — title, authors (Wenchen Fan, Herman van Hövell, MaryAnn Xue), date | Yes — AQE features and behaviors documented; TPC-DS figures not re-quoted | VERIFIED (retained with corrections) | Original attribution ("Andrew Or, Shiyan Yin, VLDB 2020") was wrong: the blog's actual authors differ, and this is not a VLDB paper. Corrected to blog + official docs, explicitly labeled non-peer-reviewed. |
| B2 (orig.) | Claimed "Runtime Adaptive Optimization for Spark SQL" (representative entry) | CrossRef/OpenAlex searches | No | No | REPLACED | Representative entry. Replaced with Deshpande, Ives, Raman, "Adaptive Query Processing" (Foundations and Trends in Databases, 2007, DOI verified) as the adaptive-QP lineage source; claims scoped to the publication record. |
| B3 (orig.) | Claimed "Data Skew Handling in Apache Spark: A Survey and Empirical Study" (representative entry) | CrossRef/OpenAlex searches | No | No | REPLACED | Representative entry. Replaced with Kwon, Balazinska, Howe, Rolia, "SkewTune: Mitigating Skew in MapReduce Applications" (SIGMOD 2012, pp. 25–36, DOI 10.1145/2213836.2213840, 289 citations) + companion PVLDB demonstration. Note: an initially recalled DOI (10.1145/2213836.2213856) resolved to a different paper (SCARAB) and was corrected via CrossRef — recorded here as evidence against trusting memory. |
| C1 (orig.) | Claimed "A Bayesian Optimization Approach for Automatic Tuning of Apache Spark Configuration" (representative entry) | CrossRef/OpenAlex searches | No | No | REPLACED | Representative entry. Replaced with Nguyen, Khan, Wang, "Towards Automatic Tuning of Apache Spark Configuration" (IEEE CLOUD 2018, DOI verified) with verbatim abstract (22.8–40.0% execution-time reductions, 9 applications, 6-node cluster). |
| C2 (orig.) | Claimed "Auto-Tuning Spark Configurations Using Machine Learning / Reinforcement Learning" (representative entry) | CrossRef/OpenAlex searches | No | No | REPLACED | Representative entry. Replaced with Cheng, Ying, Wang (JSS 2021, DOI verified); publisher elides the abstract, so all claims are scoped to the verified title. Full-text check scheduled Days 8–10. |
| C3 (orig.) | Claimed "CherryPie: Automatic Spark Configuration Tuning via Provenance-Based Optimization" | OpenAlex title search (0 results), Semantic Scholar, CrossRef | No — no record located in any authoritative source | No | REPLACED | The cited paper could not be located. Replaced with Yoon & Chung, "Empirical Evaluation of Acquisition Functions for Bayesian Optimization-Based Configuration Tuning of Apache Spark Applications" (IEICE Trans. Inf. & Syst., 2025, DOI verified; gold-OA PDF at J-Stage). |
| C4 (orig.) | Claimed "Towards Automatic Configuration of Apache Spark Using Bayesian Optimization" (representative entry) | CrossRef/OpenAlex searches | No | No | REPLACED | Representative entry. Replaced with Zhu et al., "BestConfig" (ACM SoCC '17, pp. 338–350, DOI verified, 204 citations); claims scoped to the verified abstract. |
| C5 (orig.) | Claimed "A Survey on Automatic Tuning of Big Data Processing Systems" (representative entry) | CrossRef/OpenAlex searches | No | No | REPLACED | Representative entry. Replaced with Herodotou, Chen, Lu, "A Survey on Automatic Parameter Tuning for Big Data Processing Systems" (ACM Computing Surveys, 2020, DOI verified) with verbatim abstract (six-category taxonomy). |
| C6 (new) | Islam, Karunasekera, Buyya — IEEE TPDS 2021 (DOI 10.1109/TPDS.2021.3124670) | OpenAlex + DOI record | Yes — title, 3 authors, 2021, IEEE TPDS | Title-scoped only (abstract not fetched) | VERIFIED (added) | Added as verified deep-RL-for-Spark (scheduling) evidence, strengthening RQ2/RQ5 coverage toward the Day-10 target (25–30 verified rows). |

## Totals

- Original rows: 13 — retained with corrections: 3 (A1, A2, B1); REPLACED: 10 (A3, A4, A5, B2, B3, C1, C2, C3, C4, C5); EXCLUDED: 0.
- Added verified rows: 1 (C6).
- Final matrix: **14 rows**, all VERIFIED with exact source links (A: 5, B: 3, C: 6).
- Remaining work (Days 8–10): full-text inspection for C2, C3, C4, C6 (abstract/title-scoped rows), and expansion toward 25–30 verified rows.

## Quality gate (manual inspection checklist)

For each retained source the following were checked this session against the fetched record: source opens (or DOI record resolves), title matches, authors match, year matches, venue matches, DOI/URL resolves, topic matches, method matches (at abstract/title scope), claimed result is supported (or explicitly scoped), limitation is supported (or explicitly scoped), project relevance is marked as OUR INTERPRETATION, and no information was fabricated. Items that could not be checked (paywalled full texts, unfetched abstracts) are explicitly flagged in the corresponding matrix rows and above.

---

# Day 7 additions and audit (2026-09-08)

## New rows

| ID | Previous status | Source | Verification method | Bibliographic verification | Claim verification | Decision | Notes |
|----|-----------------|--------|----------------------|----------------------------|--------------------|----------|-------|
| A6 (new) | did not exist | Xin, Rosen, Zaharia, Franklin, Shenker, Stoica — "Shark: SQL and Rich Analytics at Scale", ACM SIGMOD 2013, pp. 13–24, DOI 10.1145/2463676.2465288 (229 citations) | CrossRef DOI record + OpenAlex abstract reconstruction | Yes — title, 6 authors, venue, pages, year | Yes — abstract verbatim: "up to 100X faster than Apache Hive", "column-oriented in-memory storage", "dynamic mid-query replanning", MPP-comparable speedups with MapReduce-like fault tolerance | VERIFIED | Added to complete the SQL-on-Spark execution lineage (RDD → Shark → Spark SQL) and document that mid-query replanning predates AQE in the Spark lineage. |
| C7 (new) | did not exist | Lin, Zhuang, Feng, Li, Zhou, Li — "Adaptive Code Learning for Spark Configuration Tuning", IEEE ICDE 2022, DOI 10.1109/ICDE53745.2022.00195 | CrossRef/OpenAlex DOI record + Semantic Scholar abstract (verbatim) + DBLP key conf/icde/LinZFLZL22 | Yes — title, 6 authors, ICDE 2022 | Yes — abstract verbatim: LITE knob recommender; code features ↔ knob correlations; small→large dataset knowledge migration; adaptive model update via adversarial learning; "much better performance compared with state-of-the-art auto-tuning methods"; authors state it is infeasible for BO/RL to collect sufficient training instances for Spark | VERIFIED | The strongest peer-reviewed evidence for the project's sample-efficiency premise (RQ5) and cross-scale transfer (RQ3-adjacent). Fills the hole left by the Day-6 "CherryPie" exclusion with a located, verified ICDE paper. Author-name caveat: S2 gives "Jia-geng Feng", OpenAlex "Jiadong Feng" — IEEE Xplore check queued for Days 8–10. |

## Audit of existing rows (Step 4 re-verification)

| ID | Audit result | Action |
|----|--------------|--------|
| A1 | USENIX page re-fetched, live; BibTeX matches row | None |
| A2 | CrossRef record re-checked (Day 6 fetch retained as evidence) | None |
| A3 | USENIX NSDI '15 page fetched for the first time — verified; abstract wording is "the causes of **most** stragglers can be identified"; pages 293–307; canonical URL confirmed | CORRECTED — link upgraded from AMPLab PDF to USENIX page, pages added, "most" restored to the finding, venue completed (Oakland, CA) |
| A4 | Springer page verified Day 6 (full abstract) | None |
| A5 | USENIX NSDI '12 page verified Day 6 | None |
| B1 | Blog + Spark docs verified Day 6 | None |
| B2 | OpenAlex DOI record verified Day 6 | None |
| B3 | CrossRef record verified Day 6 | None |
| C1 | Semantic Scholar abstract verified Day 6 (verbatim) | None |
| C2 | Bibliographic record verified; abstract elided by publisher (claim scope unchanged) | None |
| C3 | Bibliographic record verified; title-scoped claim (unchanged) | None |
| C4 | CrossRef + OpenAlex abstract verified Day 6 | None |
| C5 | Semantic Scholar abstract verified Day 6 (verbatim) | None |
| C6 | OpenAlex record verified Day 6 (title-scoped claim) | None |

## Totals after Day 7

- Matrix: **16 rows** (A: 6, B: 3, C: 7), all VERIFIED with exact source links; no [TK]; no duplicates.
- Cumulative decisions across Days 6–7: 13 original rows → 3 retained with corrections, 10 REPLACED; 3 added verified rows (C6, A6, C7).
- Still queued for full-text inspection (Days 8–10): C2, C3, C4, C6, C7.

---

# Day 8 additions — Literature D–J (2026-09-08)

## New rows

| ID | Previous status | Source | Verification method | Bibliographic verification | Claim verification | Decision | Notes |
|----|-----------------|--------|----------------------|----------------------------|--------------------|----------|-------|
| D1 (new) | did not exist | Mao, Alizadeh, Menache, Kandula — "Resource Management with Deep Reinforcement Learning", ACM HotNets 2016, pp. 50–56, DOI 10.1145/3005745.3005750 (1059 citations) | CrossRef DOI record | Yes — title, 4 authors, venue, pages, year | Title/abstract-scope only (abstract not fetched) | VERIFIED | Establishes the RL-for-systems paradigm; motivates both the RL approach and the sample-efficiency concern. |
| E1 (new) | did not exist | Alipourfard, Liu, Chen, Venkataraman, Yu, Zhang — "CherryPick: Adaptively Unearthing the Best Cloud Configurations for Big Data Analytics", USENIX NSDI 2017 | OpenAlex bibliographic record + USENIX proceedings page URL | Yes — title, 6 authors, venue, year | Title/abstract-scope only (abstract not fetched) | VERIFIED | Closest published work to this project's config-selection problem; motivates sample-efficiency requirement and execution cache. |
| F1 (new) | did not exist | Salehie, Tahvildari — "Self-adaptive Software: Landscape and Research Challenges", ACM TRETS 4(2), Article 14, 2009, DOI 10.1145/1516533.1516538 | CrossRef DOI record | Yes — title, 2 authors, venue, year | Title/abstract-scope only (abstract not fetched) | VERIFIED | Foundational self-adaptive-systems taxonomy; establishes the conceptual vocabulary for the project's framing. |
| G1 (new) | did not exist | Kephart, Chess — "The Vision of Autonomic Computing", IEEE Computer 36(1), pp. 41–50, 2003, DOI 10.1109/MC.2003.1160055 (4677 citations) | CrossRef DOI record | Yes — title, 2 authors, venue, pages, year | Title/abstract-scope only (abstract not fetched) | VERIFIED | The canonical MAPE-K reference; conceptual backbone of the project's adaptation loop. |
| H1 (new) | did not exist | Marcus, Negi, Liu, Tatbul, Alizadeh, Kraska — "Bao: Making Learned Query Optimization Practical", ACM SIGMOD 2021, DOI 10.1145/3448016.3452838 | CrossRef DOI record + Semantic Scholar abstract (verbatim) | Yes — title, 6 authors, venue, year | Yes — abstract verbatim | VERIFIED | State-of-the-art learned query optimization; demonstrates viability and practical challenges of learned optimizers. |
| I1 (new) | did not exist | Kraska, Beutel, Chi, Dean, Polyzotis — "The Case for Learned Index Structures", ACM SIGMOD 2018, DOI 10.1145/3183713.3196909 | CrossRef DOI record | Yes — title, 5 authors, venue, year | Title/abstract-scope only (abstract not fetched) | VERIFIED | Seminal learned-systems paper; establishes that learned models can replace hand-crafted system components. |

## Totals after Day 8

- Matrix: **22 rows** (A: 6, B: 3, C: 7, D: 1, E: 1, F: 1, G: 1, H: 1, I: 1, J: 0), all VERIFIED with exact source links; no [TK]; no duplicates.
- Cumulative decisions across Days 6–8: 13 original rows → 3 retained with corrections, 10 REPLACED; 9 added verified rows (C6, A6, C7, D1, E1, F1, G1, H1, I1).
- Still queued for full-text inspection (Days 9–10): A2, C2, C3, C4, C6, D1, E1, F1, G1, H1, I1.
- J category not yet populated (target for Day 9).

---

# Day 9 additions — Literature D–J completion (2026-09-08)

**Scope:** Complete the D–J block to the ~30-row Day-9/Day-10 target. Eight rows added: E2, F2, G2, H2, I2, J1, J2, J3. No existing rows were renumbered or modified.

**Methods used (all via live web fetch this session):** CrossRef DOI records (full metadata: title, authors, venue, pages, citation counts), OpenAlex records (including abstract-inverted-index reconstruction and `select=authorships` roster queries), Semantic Scholar Graph API (roster + venue + external IDs), arXiv abstract pages (H2 Neo preprint metadata; J3 ICLR-2021 comment), and dblp was not used (bot-blocked/Anubis as on prior days). CrossRef/OpenAlex were intermittently rate-limited (HTTP 429); affected queries were retried via alternate providers.

**Decision key:** VERIFIED = retained source, bibliographic + claim level checked within the verified scope. No source was REPLACED or EXCLUDED in this pass; no [TK] rows exist.

| ID | Source | Verification route | Bibliographic verification | Claim verification | Decision | Notes |
|----|--------|--------------------|----------------------------|--------------------|----------|-------|
| E2 (new) | Mao, Schwarzkopf, Venkatakrishnan, Meng, Alizadeh — "Learning scheduling algorithms for data processing clusters", ACM SIGCOMM 2019, pp. 270–288, DOI 10.1145/3341302.3342080 (594 citations) | CrossRef DOI record + OpenAlex `select=authorships` | Yes — title, 5 authors, venue, pages, year | Abstract via OpenAlex inverted index (verbatim) | VERIFIED | Flagship deep-RL cluster-scheduling paper; establishes that learned policies can replace hand-crafted scheduling heuristics. |
| F2 (new) | de Lemos, Giese, Müller, Shaw, Andersson, Litoiu, Schmerl, Tamura, Villegas, Vogel, Weyns, et al. — "Software Engineering for Self-Adaptive Systems: A Second Research Roadmap", LNCS 7475 (Software Engineering for Self-Adaptive Systems II), Springer, 2013, pp. 1–32, DOI 10.1007/978-3-642-35813-5_1 (722 citations per OpenAlex; 291 per CrossRef) | CrossRef DOI record + Semantic Scholar paper record | Yes — title, venue/book, pages, year; 42-author roster via Semantic Scholar | Title/venue scope only (chapter full text not fetched) | VERIFIED | Authoritative follow-on roadmap to F1; consolidates the self-adaptive-systems research agenda. |
| G2 (new) | Huebscher, McCann — "A Survey of Autonomic Computing—Degrees, Models, and Applications", ACM Computing Surveys 40(3), 2008, pp. 1–28, DOI 10.1145/1380584.1380585 (591 citations) | CrossRef DOI record | Yes — title, 2 authors, venue, volume/issue, pages, year | Abstract verbatim via CrossRef | VERIFIED | Canonical autonomic-computing survey organized around the MAPE-K reference model; complements G1. |
| H2 (new) | Marcus, Negi, Mao, Zhang, Alizadeh, Kraska, Papaemmanouil, Tatbul — "Neo: A Learned Query Optimizer", PVLDB 12(11), 2019, pp. 1705–1718, DOI 10.14778/3342263.3342644 (321 citations) | CrossRef DOI record + arXiv:1904.03711 + Semantic Scholar | Yes — title, 8 authors, venue, pages, year | Abstract verbatim via CrossRef | VERIFIED | Deep-neural-network learned optimizer; bootstraps from existing optimizers and learns from incoming queries; complements H1 (Bao). |
| I2 (new) | Trummer, Wang, Wei, Maram, Moseley, Jo, Antonakakis, Rayabhari — "SkinnerDB: Regret-bounded Query Evaluation via Reinforcement Learning", ACM TODS 46(3), 2021, pp. 1–45, DOI 10.1145/3464389 | CrossRef DOI record + OpenAlex `select=authorships` | Yes — title, 8 authors, venue, pages, year | Abstract verbatim via CrossRef | VERIFIED | RL learns join orders from scratch during execution with an upper bound on expected execution-cost regret; complements I1. |
| J1 (new) | Van Aken, Pavlo, Gordon, Zhang — "Automatic Database Management System Tuning Through Large-scale Machine Learning" (OtterTune), ACM SIGMOD 2017, pp. 1009–1024, DOI 10.1145/3035918.3064029 (419 citations) | CrossRef DOI record | Yes — title, 4 authors, venue, pages, year | Title/abstract-scope only (abstract not fetched) | VERIFIED | Prototypical learned DBMS configuration tuning with workload/DBMS transfer; closest established analog to this project's learned Spark tuning. |
| J2 (new) | Hutter, Hoos, Leyton-Brown — "Sequential Model-Based Optimization for General Algorithm Configuration" (SMAC), LION 5, LNCS 6683, Springer, 2011, pp. 507–523, DOI 10.1007/978-3-642-25566-3_40 (1394 citations) | CrossRef DOI record | Yes — title, 3 authors, venue/book series, pages, year, ISBN | Title/venue scope only (full text not fetched) | VERIFIED | Foundational surrogate-model (random-forest BO) algorithm-configuration paper; sample-efficiency anchor for the non-RL baseline family. |
| J3 (new) | Wistuba, Grabocka — "Few-Shot Bayesian Optimization with Deep Kernel Surrogates", ICLR 2021, arXiv:2101.07667 | arXiv abstract page (comment: "Published as a conference paper at ICLR 2021") | Yes — title, 2 authors, year, arXiv id, acceptance comment | Abstract verbatim via arXiv | VERIFIED | Few-shot/deep-kernel surrogate meta-learning for sample-efficient black-box optimization across tasks. |

## Totals after Day 9

- Matrix: **30 rows** (A: 6, B: 3, C: 7, D: 1, E: 2, F: 2, G: 2, H: 2, I: 2, J: 3), all VERIFIED with exact source links; no [TK]; no duplicates (validated by `scripts/validate_literature_matrix.py`).
- Cumulative decisions across Days 6–9: 13 original rows → 3 retained with corrections, 10 REPLACED; 17 added verified rows (C6, A6, C7, D1, E1, F1, G1, H1, I1, E2, F2, G2, H2, I2, J1, J2, J3).
- Still queued for full-text inspection (Day 10): A2, C2, C3, C4, C6, D1, E1, F1, G1, H1, I1, E2, F2, G2, H2, I2, J1, J2 (all rows whose claims are scoped to title/abstract rather than fetched full text).
- D–J block complete; Day-10 task (gap note / novelty tiering) can proceed.