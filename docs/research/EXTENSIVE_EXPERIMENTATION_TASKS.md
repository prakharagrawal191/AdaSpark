# Extensive experimentation program — make the project and paper better

**Date:** 2026-09-28 · **Status:** TASK BACKLOG (nothing authorized, nothing started)
**Companion:** `docs/research/PAPER_FOLLOWUP_TASKS.md` (audit + Tracks R/E/P/H) · **Manuscript:** `manuscript/` (v1 complete: ~10,100 words, 32 figs, 15 tables, 10 equations, 39 refs)
**Budget:** SC6 483/500 (17 remain, TRAIN only) · TEST sealed · rule: pre-register → authorize → run → report (negatives included).

## Phase 1 — Validation-scoped confirmations (no TEST, own register lines, DEC-043 pattern)

| ID | Task | Pre-registered prediction slot | Cost | Paper payoff |
|---|---|---|---|---|
| X1 | E1: execute B3 heuristic on validation cells | "B3 ≡ B1 byte-identical (DEC-016B analytic claim)" | ~8–16 runs | Closes SC3 honesty gap empirically |
| X2 | E5: sampler sweep (0.5/1/2 Hz × payload) on 1–2 validation cells | "Overhead scales sub-linearly with rate; verdicts unchanged" | ~30–60 runs | Answers single-point critique (§11) |
| X3 | E6: eventlog confound quantification (paired elog-off-config vs nearest clean removal) | "Confound < 1pp on decided cells" | ~20–40 runs | Quantifies admitted confound |
| X4 | E7-diagnosis: `F3\|large\|s3` WinError32 root-cause (zero-execution first) | "Sort/spill file-lock under parallelism 8" | 0 runs | Converts structural failure to evidence |
| X5 | E8-analysis: `F3_rdd\|medium` T_ref-null remediation (zero-execution first) | "Missing calibration record, recoverable" | 0 runs | Unlocks coverage everywhere |

## Phase 2 — TEST-crossing studies (needs DEC-014-pattern authorization)

| ID | Task | Design | Cost | Paper payoff |
|---|---|---|---|---|
| X6 | E2: EXP-005b B0' AQE-on arm | Implement B0' driver; 7 TEST × 5 reps; own AQE-on ledger; no-pooling rule stands | 35 runs | Biggest claim upgrade (PLAN:72 AQE conditions) |
| X7 | E8-runs: backfilled F3_rdd\|medium TRAIN + eligibility refresh | Only if X5 finds recoverable cause; calibration first | TBD by DEC | Removes train-wide exclusion |
| X8 | H2 retest: winning-cell rematch (B1 vs RL-s0 on F2_join\|large\|s3 only) | "RL-s1's −8.6% replicates within noise band" | 2×5 runs | Tests the single RL lead honestly |

## Phase 3 — External validity (new register lines, supervisor-visible decisions)

| ID | Task | Design | Cost | Paper payoff |
|---|---|---|---|---|
| X9 | E3 pilot: public-dataset family (1 family × 2 scales × 3 arms) | New data manifest + datagen extension; frozen analysis code reused | ~60–120 runs | Generalization beyond synthetic (EXP-010) |
| X10 | E4 pilot: SC7 reproducibility subset (2 cells × 2 arms, fresh) | ±5% median rule; reconciliation vs 17-remaining SC6 first | ~20 runs + budget DEC | First SC7 evidence (EXP-011) |
| X11 | Dependence-aware stopping prototype: CUSUM/ACF-triggered stop on validation cells | "Stops at ≤50% of √n prescription without verdict loss" | ~100 runs | Converts retrospective cost finding to method |

## Phase 4 — Project fine-tuning (zero-execution unless noted)

| ID | Task | Note |
|---|---|---|
| X12 | H1: repair or deprecate stale `experiments/registry.csv` | Needs DEC cover (tracked file) — bundle with next DEC |
| X13 | H2: resolve empty `src/sparkrl/env/`, `runner/` placeholders | Needs DEC cover — bundle |
| X14 | H3: check-27 message still cites DEC-012/013 instead of DEC-046 | Message-only fix in `validate_day31.py` — bundle |
| X15 | Commit robustness outputs + manuscript scaffold (new files) | `results/evaluation/exp009_robustness.json`, `scripts/analyze_exp009_robustness.py`, `manuscript/`, backlog files — clean commit, no gate impact |
| X16 | R3 follow-up: per-sample telemetry schema for future studies | Design-only; makes next overhead study attributable |
| X17 | Video deliverables: record training/eval/build runs | `manuscript/videos/` placeholder ready |

## Sequencing rule

X4, X5 (zero cost) → X1–X3 (cheap validation) → X6 DEC draft (long lead) → X8/X7 → X9–X11 (expensive, decide late) → X12–X14 bundled with the next DEC that touches those files. If resources run out, unfinished items stay listed as future work — never silently weakened evidence.
