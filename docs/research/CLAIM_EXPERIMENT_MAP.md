# Claim ↔ experiment map (M11) — every claim carries its EXP ID

**Date:** 2026-09-29 · **Rule:** no claim without a pre-registered experiment + artifact; null/negative
claims listed, never hidden. Frozen inferential tests (Wilcoxon + Cliff's δ + Holm) were NOT runnable
at n=6/3 with no frozen mapping (DAY34 §5) — comparisons below are descriptive + noise-adjudicated
(EXP-001 worst-cell CV 0.1189) unless stated as bootstrapped CIs.

## Sensitivity / feasibility (RQ0)

| Claim | EXP | Evidence | Status |
|---|---|---|---|
| Action space spans ≥10% on ≥2 families | EXP-002 | gate.json: 4/4 families sensitive, spreads 1.59–5.83 vs noise 0.11–0.41 | PASS (SC1) |
| T_ref calibrated per cell | EXP-002 | t_ref_calibration, 7/8 cells (F3_rdd\|medium null) | DONE with exclusion |
| B3 collapses onto B1 at this data volume | X1 + DEC-016B | 7/7 executed validation cells byte-identical (runtime fp `f857d8de…` on all rows; SparkConfig fp `285ad990e5bc`; 7/7 usable) — the earlier 8/8 phrasing named no 8-cell artifact, narrowed to 7/7 (G-08 / DEC-052 D2) | CONFIRMED empirically 7/7 |

## Main comparison (RQ2: H2/H3, SC2–SC4)

| Claim | EXP | Evidence | Status |
|---|---|---|---|
| B1 lowest 6-cell descriptive sum | EXP-005 | 30.32 vs RL-s0 38.15 ≈ B4 38.34 | DESCRIPTIVE |
| Only above-noise RL-vs-static pattern: F4 p2-vs-p8 | EXP-005 | F4 L/M/S outside noise; rest inside 11.89% | DESCRIPTIVE |
| F2 L RL-s1 lead replicates | X8 | fresh same-day rematch B1 2.964 vs RL-s1 2.947 s = **−0.57%** (recomputed −0.565%); EXP-005's −8.6% lead (RL-s1 vs B4, in-noise, different baseline) NOT replicated; the −24.7% implied cross-day (B1 4.888 vs 3.678) is an unsourced figure description → dropped (audit §9A) | FALSIFIED (drift) |
| H2/H3/SC2–SC4 decided | — | frozen tests not runnable at n=6/3 | UNDECIDED (stated) |
| AQE-on beats AQE-off ≥5% on shuffle-heavy | X6 | F2_join\|large **−14.24%** outside noise (favors B0′); 5/6 other decidable cells inside noise or reversed; F3\|large INCOMPLETE 0/5 (WinError32) | MIXED (1/6), no pooling — side-by-side only; pooled estimator gated (G-04) |

## Generalization (RQ3: H4, SC5)

| Claim | EXP | Evidence | Status |
|---|---|---|---|
| SC5 evaluated | EXP-006 (+X9) | seen baseline never frozen; X9 is one-month feasibility, not a second frozen family | NOT EVALUABLE (stated) |
| F1/F4-large descriptive generalization | EXP-006 | complete 5-rep medians on 3 cells; 2 F4 cells unevaluable (0/5) | PARTIAL descriptive |
| Transfers to real data | X9 | Taxi tuned −78.05% / −69.82% vs B0 (far outside noise); RL-s0 greedy action 8 ≡ tuned `G-p8-sp16`, identity verified from artifact; plan 30 runs → 20 executed + identity substitution, disclosed (DEC-050 §2) | FEASIBILITY established (pilot) |

## Ablations (RQ1/RQ4: EXP-007/008)

| Claim | EXP | Evidence | Status |
|---|---|---|---|
| State representation effect isolated | EXP-007 | 126 execs; Q0-confound disclosed; 0/4 + 0/2 cross-seed agreement | OBSERVED, not causal |
| Reward/action design | EXP-008 | derived ablation (A5 disabled, DEC-011) | DERIVED-ONLY (stated) |
| Multi-step helps | A5 | gate NO (DEC-011) | NOT RUN (stated) |

## Cost/overhead (RQ5: SC6)

| Claim | EXP | Evidence | Status |
|---|---|---|---|
| Training ≤500 | ledger | SC6 483/500 (17 remain) + 5 demo-disclosed = **488/500 combined TRAIN-split** (12 remain); new work on own lines, 0 SC6 | HOLDS |
| Overhead ≤5% | EXP-009+X2+X3 | 6/7 PASS pooled; block-bootstrap flips 2; pilots in-noise | QUALIFIED PASS |
| Sampler scales sub-linearly | X2 | sign flips at n=1, no monotonic trend | DESCRIPTIVE |
| Elog confound <1pp | X3 | pair −3.9% inside noise; bounded not removed | DESCRIPTIVE |

## Reproducibility (SC7)

| Claim | EXP | Evidence | Status |
|---|---|---|---|
| Re-runs within ±5% | X10 | 2/4: F4 medium +2.71% / +4.74% PASS; F4 small +6.82% / +11.73% FAIL; full 60-run EXP-011 still empty (G-01) | PARTIAL 2/4 (pilot) |
| Same-config drift bounds | EXP-005+X8 | B1-vs-B4 ≤84% F1L; X8 same-day ≈0% | DISCLOSED |

## Failures (structural, never rankings)

| Claim | EXP | Evidence |
|---|---|---|
| F3\|large\|s3 WinError32 all arms + B0' | EXP-005+X6 | 35+5 identical sort/spill lock failures, AQE-independent |
| F3_rdd\|medium T_ref null | EXP-002+X5 | missing B0 reference; backfill needs TRAIN DEC |

## Demo rehearsal (EXP-012)

| Claim | EXP | Evidence | Status |
|---|---|---|---|
| Live demo runs end-to-end with logged manifests | EXP-012 | 5/5 usable on its own demo line; B0 4.699 s slowest; B3 1.424 s; RL-s0 ep1 1.417 s (`G-p8-sp32`), ep2/3 1.73/1.77 s (`G-p4-sp16`); the pre-registered parenthetical (ep1 ≡ `G-p8-sp16`) did not hold on F5_mixed — disclosed, no claim rests on it | HOLDS (DEC-051) |
| Ledger honesty for demo spend | DEC-051 | 5 TRAIN-split runs disclosed on the demo line; 483 SC6-counted + 5 = 488 combined | DISCLOSED |

## Provenance notes (DEC-052 D2)

- **Ledger.** DEC-047–052 were transcribed into `DECISIONS.md` on 2026-09-29 (DEC-047–051 from operator-signed drafts; DEC-052 as the governance cover). Until committed at HEAD, gap register G-00 applies: X rows cite signed-but-uncommitted drafts, so X evidence is cited as working-tree pilots with the ledger commit as the authorization record.
- **X6 spec is partial, not the record.** `results/experiments/x6-b0prime/spec.json` lists 1 instance (`F4_ski|small|s4`) while the observations and register line cover all 7 frozen TEST cells (35 runs, 30 usable) — STALE/PARTIAL spec; `observations.jsonl` + `results/evaluation/x6_b0prime_analysis.json` are the record. No rows or specs are rewritten (DEC-037 §5).
- **X8 authorization-scope mismatch (disclosed, not cured).** X8 rows record `authorized_by: DEC-048`, but DEC-048's signed scope is validation-scoped E1/E5/E6 and its guard voids on TEST-cell runs; X8 ran 10 runs on the frozen TEST cell `F2_join|large|s3`. Evidence retained as observed; X8 is cited with this caveat pending supervisor counter-signature; DEC-052 does not retroactively authorize TEST crossings.
- **Track-R output path.** `scripts/analyze_exp009_robustness.py` writes to a hard-coded local `OUT_DIR` (`…\AppData\Local\Temp\opencode\robustness`); `results/evaluation/exp009_robustness.json` was hand-copied from there into the repository — the copy step is recorded here (G-08); the script itself ships untracked with the manuscript bundle.
- **Observation-only pilots.** X2, X3, X10 and X8 carry `observations.jsonl` without specs; X1, X6, X9 and EXP-012 carry specs; row-level `authorized_by` fields are the per-run citation.
- **Availability (honest wording).** Committed + tracked: the reproducibility harness (16/16 verified from committed artifacts), `results/evaluation/*.json` (including the five X/Track-R analysis JSONs), the EXP-002/005/009 raw base (4.8 MB extension records included), figures, the decision log, manuscript sources and research drafts. HELD in the working tree and **deposit-pending under DEC-045 D1–D11**: raw X-family observations (`results/experiments/x*`, excluded by the `results/**` ignore rule). No URL or DOI invented; the ICPE paper's `\ArtifactURL`/`\TODO` markers are kept (G-08).
- **Ledger quoting.** SC6 ledger = 483/500 (17 remain); combined TRAIN-split incl. the 5 disclosed demo runs = 488/500 (12 remain) — both quoted wherever the budget is summarized (DEC-051, DEC-052 D2g).
