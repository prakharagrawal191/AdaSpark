# Paper follow-up tasks — strengthen the ICPE 2027 paper without spinning results

**Date:** 2026-09-28 · **Status:** BACKLOG (not authorized, not started)
**Parent paper:** `docs/paper/icpe2027/main.tex` (533 lines, 6pp, body ends p.5/10)
**Hardening report:** `docs/research/DAY45_ICPE2027_PAPER_HARDENING.md` · **Decision baseline:** DEC-046 (APPROVED 2026-09-28)
**Budget reality:** SC6 ledger **483/500, 17 remain**; TRAIN effectively closed; TEST sealed (crossing needs its own DEC, DEC-014 pattern).
**Register note:** `experiments/registry.csv` is stale (all rows `planned`) — see H1.

## Integrity guardrails (bind every task below)

1. **Pre-register before touching live Spark.** Prediction + analysis frozen in writing first (DEC-043 pattern). No exceptions.
2. **Reuse frozen analysis code** for any re-adjudication (the `analyze_exp009_ext.py` precedent) — never reimplement the estimator under test.
3. **Report negatives.** A task that falsifies its own motivation is DONE, not failed. Null/negative outcomes go in the paper, not in a drawer.
4. **No TEST without authorization.** Anything crossing the TEST seal needs a DEC-014-pattern entry first.
5. **Budget honesty.** New live work is either charged to SC6 (≤17 left — TRAIN only) or authorized on its own SC6-exempt register line with the DEC-043/EXP-009-extension justification (VALIDATION-only, zero charge to the training cap). Never both, never neither.
6. **Touch nothing recorded.** No edits to artifacts, ledgers, manifests, hashes, or prior DEC entries (DEC-037 §5). New outputs are NEW files; modified tracked files need DEC cover (check 27).

## Audit headline (evidence, 2026-09-28)

- Paper's core: pre-registered √n falsification on 7/7 cells (4,842 runs), interval-adjudicated overhead vs 5% budget (6/7 PASS, 1 INCONCLUSIVE), lag-1 autocorrelation +0.584…+0.886 in 21/21 series, worse-with-more-data cell, retrospective 2.9–4.5× over-provisioning cost.
- Strongest reviewer-facing gaps: (a) bootstrap CIs assume independence the paper itself disproves (§7 vs §5.1); (b) AQE-on condition scoped but 0 measurements (005b); (c) heuristics baseline B3 analytic-only so SC3 ≈ RL-vs-B1; (d) single host / synthetic-only / no external dataset (EXP-010 empty); (e) reproducibility ±5% unevidenced (EXP-011 empty); (f) threats-to-validity 6 short paragraphs, no validity structure; (g) 3 related-work candidates missing + no search method; (h) methods detail thin (interleaving order, session map, clock, host telemetry).
- Per-experiment truth: EXP-001/002/004/005/006/007/009(+ext) executed; EXP-003 selection-only; EXP-008 derived-only (A5 DISABLED, DEC-011); EXP-005b/010/011/012 not executed. TRAIN missing `F3_rdd|medium` everywhere (T_ref null); TEST `F3|large|s3` structurally failed (WinError32); B2 undefined on F4 by design.

---

## Track R — zero-execution re-analyses (no budget, no authorization needed)

| ID | Task | Why (paper gap) | Acceptance |
|---|---|---|---|
| R1 | Block bootstrap + seed sensitivity for EXP-009 CIs; BCa vs percentile comparison on committed observations, reusing frozen estimator code | Paper's CIs assume i.i.d. resamples while proving serial dependence (`main.tex:208-209` vs `324-325`) — the sharpest self-critique available | New `results/evaluation/exp009_robustness_*.json` (NEW files); verdicts reported whether they move or not; method paragraph for §7 |
| R2 | Full ACF (lag>1), per-series lag-1 table, stationarity/changepoint tests on all 21 condition-series | Autocorrelation evidence is currently a range only (`main.tex:324`); no ACF, no per-series table | Per-series table + ACF figure candidate; method defined (estimator, lags, test, α) before running |
| R3 | Overhead resource breakdown from retained monitoring data (sampler CPU%, log bytes, GC/spill where logged) | Overhead table is job-time deltas only; no mechanism attribution | Table or explicit "not logged, listed as limitation" — either closes the gap |
| R4 | Cost accounting: wall-clock hours, CPU-hours, storage/energy for the 4,842 runs from manifests/logs | Cost section counts runs only (`main.tex:408-411`) | Cost paragraph with real units; energy via TDP-bounded estimate, labelled as such |
| R5 | Per-cell duration/scale table (median runtime, n, scale) | No basis to judge overhead-vs-runtime or scale trend | Table for §3 or appendix |
| R6 | Bimodality diagnostics for `F1_agg\|small` (density/histogram, mixture or changepoint at run ~146) | Worse-with-more-data claim rests on p25/p75 of two modes (`main.tex:379-383`) | Figure + test statistic, or downgrade to descriptive |
| R7 | Define monotonicity + slope CIs for the trajectory table; adjudicate eventlog half-widths in prose (e.g. 15.41pp on `F1_agg\|small`, `main.tex:270`) | `monotone` column undefined; eventlog widths never discussed | Definitions frozen first; prose covers both arms |
| R8 | Pre-register a stabilization rule for earliest-stable-PASS, or reframe Table `main.tex:391-405` as post-hoc/descriptive with selection-bias disclosure | Prefix grid is dependent (`main.tex:440-441`) yet mined for "earliest stable" — selection bias unlisted | Rule + re-analysis, or rewritten caption + §7 bullet |

## Track E — confirmatory live experiments (each needs its own DEC + budget line)

| ID | Task | Design sketch | Budget / gate |
|---|---|---|---|
| E1 | B3 heuristic baseline execution (SC3 honesty) | `k=7.45` already frozen (DEC-016B); B3 ≡ B1 byte-identical at current volumes — run to confirm the collapse empirically rather than assert it | Small; VALIDATION-scoped DEC; cheap because config identical to B1 |
| E2 | EXP-005b B0' AQE-on arm (biggest claim upgrade) | Implement B0' driver (`run_exp005.py:54` has no B0' path), run 7 TEST × 5 = 35 on own AQE-on ledger; no-pooling rule stands (RL-vs-B0' never pooled) | 35 runs, own ledger, 0 to SC6; needs TEST-crossing DEC (DEC-014 pattern) |
| E3 | EXP-010 external-dataset pilot (Taxi) | 1 family × 2 scales × subset of arms; new data manifest + datagen extension; generalization beyond synthetic | New register line + dataset DEC; medium cost — pilot scope only |
| E4 | EXP-011 SC7 reproducibility | Fresh live subset vs ±5% median rule; 60 planned vs 17 SC6 remaining → reconciliation first | Budget DEC before any run; possibly reduced pilot scope by decision |
| E5 | Sampler sweep (frequency/payload) on 1–2 validation cells | 0.5/1/2 Hz × payload levels; quantifies overhead scaling, answers single-point critique (`main.tex:169-171`) | VALIDATION-scoped, SC6-exempt line (DEC-043 pattern) |
| E6 | Eventlog confound quantification | elog-off changes Spark config (DEC-040§4) — measure the confound's magnitude/direction | Small paired VALIDATION design; pre-register |
| E7 | `F3\|large\|s3` WinError32 root-cause | Diagnose sort/spill file-lock failure; convert structural failure into evidenced limitation (or fix + re-run by decision) | Zero-execution diagnosis first; runs only if fix authorized |
| E8 | `F3_rdd\|medium` T_ref-null remediation | Investigate null, backfill calibration; unlocks TRAIN coverage + B1/B2 eligibility everywhere downstream | Analysis first; backfill needs DEC cover |

## Track P — paper revision (after R; no live runs)

| ID | Task | Source gap |
|---|---|---|
| P1 | Artifact readiness: anonymized URL (P1 TODO), DOI deposit per DEC-045/SC8 plan, Anonymous-GitHub-vs-supplement decision, CCSXML, reference hygiene (ASPLOS DOI twin, Chen-Revels arXiv), AI-use placement | DAY45 §5; `PAPER_ICPE2027_PLAN.md:75-77,110-134` |
| P2 | Threats-to-validity rewrite: construct/internal/conclusion structure + bootstrap-independence, post-hoc-selection, eventlog-confound, coverage-exclusion, drift-gap, uncontrolled-host bullets | `main.tex:420-445` (6 short paragraphs) |
| P3 | Related-work completion: Costa'19 JMH, Mytkowicz'10 profiler accuracy, Burchell'23 + search-method paragraph + Kieker/MooBench quantitative comparison | `PAPER_ICPE2027_PLAN.md:98-100`; `main.tex:102-148` |
| P4 | Methods detail: interleaving order (fixed vs randomized), per-session batching, session-length/count/wall-span per cell, clock boundaries + Spark-timer cross-check, run-date/session map, host-telemetry log | `main.tex:152-201,253-254` |
| P5 | Results presentation: ACF figure (from R2), duration table (R5), eventlog-half-width prose (R7), bimodality figure (R6), stabilization-rule framing (R8) | Track R outputs |
| P6 | Page-budget check: body currently ends p.5/10 — allocate new material without breaching the limit; rebuild + in-page check must stay green | `build.py` gate |

## Track H — project hygiene / fine-tuning (no research claims affected)

| ID | Task | Note |
|---|---|---|
| H1 | Fix stale `experiments/registry.csv` (all `planned`) or mark it deprecated in favor of the DEC log + DAY AV audits | Source of confusion; zero claim impact |
| H2 | Resolve placeholder dirs `src/sparkrl/env/`, `src/sparkrl/runner/` (empty `__init__.py`) — implement or delete with DEC note | Dead surface in the package |
| H3 | `validate_day31.py` check-27 message still says "authorized by DEC-012/013" while the allow-list cites DEC-046 | Cosmetic; gate passes — fix message only |
| H4 | Build fragility: Edge hard dependency for figure PDFs; `pdftotext` "not checked" fallback; decide figure-PDF commit policy (currently committed) | Gates pass; robustness only |
| H5 | Confirm `CCSXML` + review-vs-camera-ready AI-disclosure placement per venue guidance | P1-adjacent; editorial |

## Suggested order

1. **R1 → R2 → R4** (zero cost; answer the two sharpest statistical critiques + real cost units).
2. **P2 + P3 + P4 scaffolding** in parallel (text work that R outputs will fill).
3. **E2 DEC draft** (longest lead time: TEST-crossing authorization; 35-run AQE-on is the largest single claim upgrade).
4. **E1 + E5** (cheap VALIDATION-scoped confirmations).
5. **E3/E4 pilots** only after explicit budget decisions (they don't fit in SC6's 17).
6. **E7/E8** diagnosis first (zero-execution), runs only by decision.
7. **P5 + P6** last (presentation once numbers are final; page budget enforced by `build.py`).

## What this backlog does NOT authorize

No Spark execution, no TRAIN/TEST cell, no budget spend, no artifact/ledger/manifest/hash edit, no threshold change, no venue submission. Each Track-E item needs its own pre-registered DEC before any run. A re-analysis that moves a verdict is reported, never hidden; a live run that returns null is published, never rerun until significant.
