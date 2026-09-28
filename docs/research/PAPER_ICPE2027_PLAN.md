# ICPE 2027 submission plan — the monitoring-overhead paper

> **Status: PROPOSED — AUTHORIZES NOTHING.** This plans the submission of
> `docs/report/PAPER_DRAFT_monitoring_overhead.md` to the ACM/SPEC ICPE 2027
> Research Track. It creates no account, repository, preprint, deposit or
> submission, changes no result, and decides none of the §6 questions. It
> executes no Spark and charges nothing to SC6.

**Date:** 2026-09-26

## 1. The venue decision

On 2026-09-26 the operator was asked *"Which venue should the paper target?"*
and selected ***"ICPE 2027 (Recommended)"***. Under DEC-045 D7 a double-blind
submission is now scheduled first, so the public GitHub repository and the
Zenodo records stay **held** until ICPE notifies authors (2027-01-25). The
authoritative deposit (DEC-045 D9) is unaffected; only its publication waits.

## 2. What ICPE 2027 requires (read from its pages on 2026-09-26)

| Item | Requirement | Source |
|---|---|---|
| Abstract / paper | **Mon 2026-11-09 / Mon 2026-11-16**, AoE | icpe2027.spec.org/important-dates |
| Notification / camera-ready | 2027-01-25 / 2027-03-12 | same |
| System | HotCRP, `icpe2027.hotcrp.com` | research-paper-track |
| Format | ACM double-column conference format (no acmart option set is named) | same |
| Length | ≤ 10 pages incl. figures and tables; references and appendices extra. Appendices are **not published**, so the paper must be self-contained | same |
| Camera-ready | up to +2 pages, to de-anonymize and answer reviewers | same |
| Categories | Regular Research, or **EERCS** (Empirical, Experience, Reproduction, Case Study) | same |
| Anonymity | no author list; own work in the third person; **any associated code or repository anonymized**; no identifying links; **no acknowledgements** in the submitted PDF | icpe2027.spec.org/double-blind |
| Preprints | arXiv allowed, with a sufficiently different title | same |
| AI tools | may not be authors; follow the ACM Policy on Authorship for disclosure | call-for-contributions |
| ORCID | required from authors of accepted papers | same |
| Artifact track | "Details TBA"; ICPE 2026 required a DOI-archived artifact by camera-ready, GitHub not sufficient | artifact-evaluation-track (2027, 2026) |

## 3. The draft today

**Strengths a reviewer will see** (from a review of the draft on 2026-09-26):
a pre-registered prediction recorded before execution and falsified on all seven
cells; interval adjudication fixed in advance; the INCONCLUSIVE cell reported,
not rescued; the paired analysis confined to an exploratory appendix (DEC-044
D2); an i.i.d. estimator control; candid threats to validity; a checker that
traces all 73 headline figures to a committed artifact; a verified
fresh-clone reproduction (DEC-045, `SC8_DEC045_REHEARSAL.md`).

**Gaps, in the order to fix them:**

1. **Format and length.** Markdown today (~3,900 words, 5 wide tables, 2 SVG
   figures). Convert to ACM `acmart` (`sigconf`, anonymous review mode) and
   measure. The page count is unknown until compiled; the 10-page limit
   includes tables and figures. Appendix A may stay as an appendix, but nothing
   the argument needs may live only there.
2. **Related work is thin for the claim it makes.** §2 cites four works, then
   says no controlled study of Spark monitoring overhead was found. ICPE
   reviewers will expect the monitoring-overhead line (Kieker/MooBench), the
   repetition and cloud-variability literature, and ICPE's own interleaving
   and duet-benchmarking papers. Verified candidates are in §4.
3. **Data availability.** §10 still says the raw deposit "will be" made,
   with a bracketed TODO. For review it becomes an anonymized availability
   statement (§5); the DOI replaces it at camera-ready.
4. **Multiple looks.** Seven cells, two components and a grid of prefix k are
   reported without a multiplicity note. State that verdicts are per
   component, per cell, at one pre-registered n with no family-wise claim, and
   that the prefix grid is descriptive, not a sequence of tests.
5. **Cluster-mode portability.** §8 asserts the methodological finding "is
   more portable" than the single-host `local[2]` magnitudes. Keep the claim
   narrow, or argue it (event-log shipping and multi-executor listener
   contention are not measured).
6. **The excluded cell.** `F3_rdd|medium`'s fragility (18 failed / 8
   completed) is asserted; point to the record in the anonymized artifact.
7. **AI-use disclosure.** ACM policy asks for it, normally in the
   Acknowledgements, which ICPE forbids in the submitted PDF. See §6 P4.
8. **Front matter.** CCS concepts and keywords now; authors, ORCID and
   acknowledgements only at camera-ready.
9. **Reference hygiene.** Cite ASPLOS by its proceedings DOI
   `10.1145/1508244.1508275` (the draft's `1508284.1508275` is the valid SIGPLAN
   Notices twin); Chen & Revels stays an arXiv citation.

**Tooling.** No TeX is installed on the recording machine. Either compile on
Overleaf, or install a user-level TeX (for example TinyTeX) so that the page
count and `verify_paper_claims.py` can run locally (§6 P6). The checker should
then also scan the LaTeX source — an additive change to its `DOCS` list.

## 4. Related work to add (each verified at the publisher or dblp on 2026-09-26)

| Reference | Why it matters here |
|---|---|
| Georges, Buytaert, Eeckhout. *Statistically Rigorous Java Performance Evaluation.* OOPSLA 2007. doi:10.1145/1297027.1297033 | the i.i.d. repetition statistics our √n test inherits |
| Abedi, Brecht. *Conducting Repeatable Experiments in Highly Variable Cloud Computing Environments.* ICPE 2017. doi:10.1145/3030207.3030229 | interleaving conditions, as §3 does |
| Bulej, Horký, Tůma, Farquet, Prokopec. *Duet Benchmarking: Improving Measurement Accuracy in the Cloud.* ICPE 2020. doi:10.1145/3358960.3379132 | paired execution against common-mode noise — context for Appendix A |
| Laaber, Scheuner, Leitner. *Software Microbenchmarking in the Cloud. How Bad Is It Really?* EMSE 24, 2019. doi:10.1007/s10664-019-09681-1 | repetitions needed under real noise |
| Leitner, Cito. *Patterns in the Chaos.* ACM TOIT 16, 2016. doi:10.1145/2885497 | structured, non-random performance variation |
| Uta et al. *Is Big Data Performance Reproducible in Modern Cloud Networks?* NSDI 2020 | big-data variability; why a single fixed host |
| Maricq et al. *Taming Performance Variability.* OSDI 2018 | non-i.i.d. host variability |
| Ousterhout et al. *Making Sense of Performance in Data Analytics Frameworks.* NSDI 2015 | Spark instrumentation as a measurement substrate |
| Papadopoulos et al. *Methodological Principles for Reproducible Performance Evaluation in Cloud Computing.* IEEE TSE 47(8), 2021. doi:10.1109/TSE.2019.2927908 | reporting-principles checklist |
| Traini, Cortellessa, Di Pompeo, Tucci. *Towards Effective Assessment of Steady State Performance in Java Software: Are We There Yet?* EMSE 28, 2023. doi:10.1007/s10664-022-10247-x | steady-state detection fails in practice |
| Costa et al. *What's Wrong with My Benchmark Results? Studying Bad Practices in JMH Benchmarks.* IEEE TSE, 2019. doi:10.1109/TSE.2019.2925345 | measurement pitfalls |
| Mytkowicz et al. *Evaluating the Accuracy of Java Profilers.* PLDI 2010. doi:10.1145/1806596.1806618 | what a sampling profiler's output can be trusted for |
| Burchell, Larose, Kaleba, Marr. *Don't Trust Your Profiler.* MPLR 2023. doi:10.1145/3617651.3622985 | same, recent |
| van Hoorn, Waller, Hasselbring. *Kieker.* ICPE 2012. doi:10.1145/2188286.2188326 | monitoring framework whose overhead ICPE has long measured |
| Reichelt, Kühne, Hasselbring. *Towards Solving the Challenge of Minimal Overhead Monitoring.* ICPE 2023 Companion. doi:10.1145/3578245.3584851 | monitoring-overhead measurement at ICPE |
| Reichelt, Bulej, Jung, van Hoorn. *Overhead Comparison of Instrumentation Frameworks.* ICPE 2024 Companion. doi:10.1145/3629527.3652269 | same |
| Ren et al. *Google-Wide Profiling.* IEEE Micro 30(4), 2010. doi:10.1109/MM.2010.68 | always-on profiling cost at scale |

No peer-reviewed measurement of Spark's own event-log or metrics-system
overhead was found; practitioner material (e.g. sparkMeasure) is not a citable
precedent. The novelty claim should stay as narrow as §1 already makes it.

## 5. Anonymity for review

The paper text contains none of `AdaSpark`, `sparkrl`, `Prakhar`, `OneDrive` or
the local path. The repository contains all of them, plus the commit author on
every commit, so no raw link can be given. Options for reviewer access:

| Option | What reviewers get | Cost and risk |
|---|---|---|
| A. No link | an availability statement only | none; weakest evidence for a reproducibility-centred paper |
| B. Anonymous GitHub mirror of a **private** GitHub repository | read-only browsing of code and committed artifacts, identifying terms replaced by `XXX` | needs a GitHub account and a private repo, and a token with full `repo` scope; every identifying term must be listed (`AdaSpark`, `Prakhar`, `prakh`, `OneDrive`); replacing `sparkrl` would break imports, so it stays; large files are streamed, and whole-repo download is capped at 10 MB |
| C. Anonymized supplementary archive | a zip of code, committed artifacts and a **separately labelled redacted derivative** of the raw records, with its own manifest (plan §5) | depends on HotCRP supplementary upload being enabled (unknown); the derivative is never presented as the raw record |

Zenodo restricted records do not help: their metadata, including creator
names, is always public, and requesting access reveals the reviewer.

## 6. Operator decisions (answered 2026-09-26)

Each was put to the operator as a question with options; the selected answer is
quoted.

| # | Question | Answer |
|---|---|---|
| P1 | Reviewer access to the artifact (§5) | ***"Anonymous GitHub (Recommended)"*** — option B: a private GitHub repo mirrored by Anonymous GitHub; it becomes the DEC-045 D1 public repo after notification |
| P2 | Post an arXiv preprint before the decision? | **No** (defaults accepted: ***"Accept all three"***) |
| P3 | Authors | ***"Just me"*** — sole author |
| P4 | AI-use disclosure at submission | one non-identifying sentence in the paper body, moved to the Acknowledgements at camera-ready (defaults accepted) |
| P5 | Category | **EERCS** (defaults accepted) |
| P6 | TeX environment | ***"Install TeX locally (Recommended)"*** — a user-level TinyTeX, so page count and the claims checker run locally |

## 7. Schedule

| Week | Work |
|---|---|
| Sep 28 – Oct 4 | P1–P6 decided; LaTeX conversion; related work (§4); reference fixes |
| Oct 5 – 11 | gaps 3–8; figures to PDF; `verify_paper_claims.py` extended to the LaTeX |
| Oct 12 – 18 | cut to 10 pages; adversarial internal review |
| Oct 19 – 25 | anonymized artifact (P1) built and checked from its mirror |
| Oct 26 – Nov 1 | supervisor / peer read; revision |
| Nov 2 – 8 | final checks; HotCRP abstract registration and conflicts by **Nov 9** |
| by Nov 16 | submit |
| Jan 25, 2027 | if accepted: DEC-045 public release (repo, three Zenodo records, tag `v1.0.0`); clean-machine §8 run (SC8); artifact track; camera-ready with DOIs, ORCID and acknowledgements by Mar 12 |

## 8. What this plan does not do

It submits nothing, creates no account, repository or preprint, reserves no DOI,
publishes nothing, and edits no result or decision entry. P1–P6 were answered
by the operator (§6); this plan only records them. It does not change SC6 (483/500), SC7 (not started), SC8 (not yet
demonstrated) or TEST (sealed).
