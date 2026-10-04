# AdaSpark Case-Study Manuscript — Build Outline

**Target:** 10,000–15,000 words · 25–35 figures · 12–15 tables · 8–15 equations · references: planning table 80–140, guideline 30–50 (≥80% journals IEEE/ACM/Springer/Elsevier, 2020–2025) — the two sources conflict; 140 used.
**Source:** `C:\Users\prakh\OneDrive\Desktop\PDS PROJECT` (frozen plan `docs/PLAN.md`, decision log `DECISIONS.md`, evidence in `results/`).
**Integrity rule:** every measured number traces to a committed artifact; null/negative findings reported, never hidden; prospective material labelled as such.

**Build status 2026-10-03: COMPLETE v3 (compliance pass)** — 14,957 words excl. references and figure captions (abstract, keywords, executive summary with Table 1, data availability and appendix included; band 10,000–15,000; markdown table syntax not counted) · 32 figures (band 25–35) · 15 tables (band 12–15) · 13 equations, editable OMML (band 8–15) · 140 references (128 with DOI), every one cited · `.docx` built into `template/official_template.docx` · results include the confirmatory EXP-013 (DEC-053/055) and EXP-014 (DEC-054) · all sections DONE · student names, registration numbers, e-mails, Team ID, GitHub URL and video location remain highlighted `[to be entered]` flags.
Per-section bands sum to ≈19,400 words at their minimums, above the 15,000 total cap, so sections are scaled proportionally and the total band governs.

## Section files (`sections/`) and status

| File | Section | Target words | Status |
|---|---|---|---|
| `00-abstract.md`, `00-exec-summary.md` | Abstract (150–250, one paragraph) + Executive Summary | 450–750 combined | DONE |
| `01-keywords.md` | Keywords | 20–40 | DONE |
| `02-introduction.md` | 1. Introduction (Fig 1, 2) | 800–1200 | DONE |
| `03-problem.md` | 2. Problem Statement (Fig 3, Table 2) | 400–700 | DONE |
| `04-background.md` | 3. Background & Literature (Fig 4, Table 3) | 1500–2500 | DONE |
| `05-requirements.md` | 4. Requirements Analysis (Fig 5, Table 4) | 600–1000 | DONE |
| `06-architecture.md` | 5. RL-Driven Spark Architecture (Fig 6 CORE, Fig 7) | 1000–1500 | DONE |
| `07-execution-layer.md` | 6. Programming & Execution Layer (Fig 8, Table 5) | 1000–1500 | DONE |
| `08-rl-layer.md` | 7. RL Optimization Layer (Fig 9, 10, Eq reward) | 1200–1800 | DONE |
| `09-scheduling.md` | 8. Resource Allocation & Scheduling (Fig 11, 12, Table 6) | 1200–1800 | DONE |
| `10-self-tuning.md` | 9. Self-Tuning Optimization (Fig 13, 14) | 1000–1500 | DONE |
| `11-explainability.md` | 10. Explainability & Decision Intelligence (Fig 15, 16, Eq confidence) | 1000–1500 | DONE |
| `12-monitoring.md` | 11. Monitoring, Feedback & Learning (Fig 17, Table 7) | 1000–1500 | DONE |
| `13-governance.md` | 12. Security, Reliability & Governance (Fig 18, Table 8) | 800–1200 | DONE |
| `14-exp-setup.md` | 13. Experimental Setup (Fig 19, Table 9) | 700–1200 | DONE |
| `15-metrics.md` | 14. Evaluation Metrics (Fig 20, Table 10) | 500–800 | DONE |
| `16-results.md` | 15. Results & Findings (Fig 21, 22, 23, Table 11) | 1200–2000 | DONE |
| `17-comparative.md` | 16. Comparative Analysis (Fig 24, Table 12) | 800–1200 | DONE |
| `18-trust.md` | 17. Explainability/Reliability/Trust Assessment (Fig 25, Table 13) | 700–1000 | DONE |
| `19-usecases.md` | 18. Industry Use Cases (Fig 26, 27, Table 14) | 800–1500 | DONE (prospective) |
| `20-business.md` | 19. Business Impact (Fig 28, Table 15) | 500–1000 | DONE (prospective) |
| `21-limitations.md` | 20. Challenges & Limitations (Fig 29) | 600–1000 | DONE |
| `22-future.md` | 21. Future Research (Fig 30, 31) | 600–1200 | DONE |
| `23-conclusion.md` | 22. Conclusion (Fig 32) | 500–800 | DONE |
| `24-references.md` | References (30–50) | variable | DONE |
| `25-appendix.md` | Appendix (algorithms, configs, scripts) | 500–2000 | DONE |

## Diagrams (`diagrams/`, 600 DPI PNG, `Fig NN <Title>.png`)

Conceptual figures by `diagrams/make_diagrams.py`; Figs 21–24 by `diagrams/make_result_figures.py` from committed results (no hand-typed values; matched cell sets). Matplotlib, re-drawn originals; no third-party figures reused.

## Assembly

`build_docx.py` (python-docx) assembles `AdaSpark_CaseStudy_Report.docx` from `sections/` in order (with `data_availability.md` before the references), into the official course template; figure-caption significance sentences come from `figure_captions.json`, and Index/LoF/LoT page numbers are computed by Word at build time.
Equations (1)–(13) are converted from MathML (`equations.json`) to editable Word equations (OMML) via Office's `MML2OMML.XSL`.
Citations are numeric `[n]` per the guideline format, one per sentence.
