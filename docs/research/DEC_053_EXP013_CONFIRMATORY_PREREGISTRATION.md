# DEC-053 (SIGNED) | 2026-10-02 | EXP-013 confirmatory re-evaluation on the full frozen TEST identity — interleaved, A/A-controlled, makes H2/H3 decidable; 0 charged to SC6

**Status:** **SIGNED 2026-10-02 — operator approval GRANTED for the full scope (stages A–D).** Provenance, recorded exactly: the operator approved this draft in-session on 2026-10-02 by selecting *"All stages A–D (Recommended)"* in answer to *"Approve DEC-053 (EXP-013 confirmatory runs on TEST, 0 charged to SC6)? Choosing a run option is recorded as your operator signature for exactly that scope."* The operator also approved milestone commits and asked for the EXP-014 overhead pre-registration to be prepared for a separate sign-off. Supervisor counter-signature: PENDING (never simulated).
**Supersedes nothing.** EXP-005 (DEC-014/018) stands exactly as recorded; EXP-013 is a separate confirmatory study reported beside it.

> **Writing this draft performed 0 Spark executions.** SC6 cap = 500, NOT raised. SC6 ledger = 483 / 17 (488 / 500 combined with the 5 disclosed demo runs), unchanged. TEST = AUTHORIZED only if this entry is signed, and only for the 900 queue entries below. A5 = DISABLED. `docs/PLAN.md` = UNCHANGED.

---

**0 — Identifier resolution.** The ledger ends at DEC-052; next free: **DEC-053**. The experiment register ends at EXP-012; next free: **EXP-013**.

**1 — Why (all facts below were established with 0 Spark executions).**

- **(a) H2/H3/SC2–SC4 are UNDECIDED.** EXP-005 left six common cells, and the frozen PLAN §22 tests were never run (`results/evaluation/exp005_analysis.json`: "inferential_tests: NOT RUN").
- **(b) The EXP-005 ordering is confounded with queue position.** EXP-005 executed instance-major, then arm, then rep. On `F1_agg|large|s3`, all six non-B0 arms ran the identical configuration `G-p8-sp16`, yet their medians range from 10.09 s (B1) to 21.78 s (RL-s2), a 2.16× spread between identical configurations. The descriptive ordering "B1 30.32 < RL-s0 38.15 ≈ B4 38.34" therefore cannot be read as a configuration effect.
- **(c) Configuration identity on TEST.** This was resolved with the EXP-005 driver's own frozen code (`resolve_static_arm`, `resolve_rl_arm`, `strategies.resolve`). Every configuration EXP-005 recorded (7 instances × 7 arms) is reproduced, with 0 mismatches.
  - On all 43 TEST cells, **B1 ≡ B3 ≡ B4 ≡ `G-p8-sp16`**, and **RL-s0 ≡ RL-s1 ≡ RL-s2**.
  - The reason for the RL identity: every TEST input is < 512 MiB, i.e. size bin S (recorded internally in `DAY32_CONVERGENCE_AND_STATE_COVERAGE.md`), and the evaluation feedback bin is `le0`. So on TEST the three frozen policies act as one per-family lookup: agg/join → `G-p8-sp16`, rdd_sort → `G-p4-sp128`, skew_join → `G-p2-sp16`, mixed → `G-p8-sp32`.
  - B2 resolves to `G-p8-sp16` on F1/F2, `G-p8-sp64` on F3 and `G-p8-sp32` on F5, and is undefined on F4 (DEC-019).
  - **Consequence:** on F1/F2 the RL arm *is* the tuned static configuration, so the RL-vs-static question is decided on F3, F4 and F5.
- **(d) Purpose.** To **affirm or refute the manuscript's stated conclusions**, not to obtain better numbers. No arm, configuration, policy or threshold is tuned. The predictions in §4 are the manuscript's own current sentences.

**2 — Scope (authorized only if signed).**

- **Cells (42).** The 43 frozen TEST cells (`test_freeze.json`, artifact_id `699e98df…`) minus `F3_rdd|large|s3`, which already has 40/40 structural failures across every arm including B0′ (AQE-independent).
- **Execution units per cell, 5 repetitions each:**
  - **B0.**
  - **B1**, which also stands for B3 (identity verified at plan time).
  - **B4**, executed separately even though it resolves to B1's configuration. This makes it the **A/A control**.
  - **RL**: the frozen RL-s0 artifact, greedy, ε = 0. RL-s1 and RL-s2 are identity-mapped by configuration fingerprint.
  - **B2**, only where its configuration differs from both B1 and RL (F3: `G-p8-sp64`).
  - **B0′** (AQE-on default) on the 6 executable EXP-005 instances only, compared with B0 only. No pooling with RL (DEC-047 rule).
- **Design.** Randomized complete blocks, one block per (cell, rep). The order is stage-major, then rep-major. Cells are shuffled per (stage, rep) and units per block, with seed 20261001.
- **Frozen queue.** **900 entries, fingerprint `fe159085330569d577d34285609a6fc3ef232dfa2d81c4e6be175084a16c8d1a`**, pinned by a unit test.
- **Probe rule (F3_rdd large).** The rep-1 block of each `F3_rdd|large` cell (seeds 0, 1, 2, 4) starts with B0 and RL. If both fail, the cell is STRUCTURAL-INCOMPLETE and all its later entries are recorded NOT_EXECUTED with 0 Spark. If the cell continues, any unit that fails in two consecutive repetitions there is skipped for its remaining repetitions, also at 0 Spark.

| Stage | Cells | Queue entries | Est. Spark runs | Est. wall-clock |
|---|---|---|---|---|
| A | the 6 executable EXP-005 instances (+ B0′) | 150 | 150 | ~1.7 h |
| B | the other 12 `F4_ski` cells | 240 | 240 | ~1.2 h |
| C | 8 small/medium F1/F2/F3/F5 cells (seed 4) | 170 | 170 | ~1.9 h |
| D | 16 large F1/F2/F3/F5 cells at seeds 0, 1, 2, 4 (incl. 4 F3 probe cells) | 340 | ~248 | ~4.0 h |
| **Total** | **42** | **900** | **~808** | **~8.6 h** |

- **How the estimate was made.** Wall time ≈ 4.1 s + 2.75 × execution time, fitted on 56 X-family rows. Execution times come from the EXP-005 and EXP-002 medians. A failed F3 large run costs ~330 s.
- **Stopping and partial runs.** The campaign may be stopped after any complete stage. **Only complete stages enter the decisions.**

**3 — Frozen analysis.** The analysis lives in `scripts/analyze_exp013.py` and `src/sparkrl/analysis/inference.py`. Both were written and unit-tested on synthetic data before any EXP-013 data existed. Their sha256 is frozen into `spec.json` at the first execution, and any later edit is a disclosed deviation reported with both outputs.

- **Unit of analysis:** the cell. This is PLAN §22's "paired by workload instance". Per (cell, unit), the statistic is the median of exactly 5 usable repetitions; fewer means INCOMPLETE, never imputed.
- **T1 (H2), per distinct RL arm.**
  - Test: one-sided exact Wilcoxon signed-rank across cells on ln(med_RL / med_B0) − ln 0.9.
  - Per-cell count: cells with a ≥ 10% gain and a per-cell exact one-sided Mann-Whitney p ≤ 0.05.
- **T2 and T3 (H3 vs B3 and vs B4).**
  - Test: one-sided exact Wilcoxon on ln(med_RL / med_k).
  - A cell counts as **better** if ratio ≤ 1 − τ with Mann-Whitney p ≤ 0.05, and as **worse** if ratio ≥ 1 + τ with Mann-Whitney p ≤ 0.05.
  - τ = 0.1189: the EXP-001 worst-cell CV, already the project's noise rule (DEC-018 Decision F).
- **Multiplicity:** Holm across {T1, T2, T3} × distinct RL arms, α = 0.05. A test is decidable iff (family size) × 2^−n < α.
- **Decision rules.**
  - **H2 ACCEPTED** iff Holm p(T1) < α and the ≥ 10% gain cells number at least ⌈n/2⌉.
  - **H3 ACCEPTED** iff, for both comparators, Holm p < α, the better cells number at least ⌈n/2⌉, and there are zero worse cells.
- **Effect sizes.** Per-cell Cliff's δ. Across cells, the geometric-mean ratio with a 95% percentile bootstrap CI (4,000 resamples, seed 0), the same convention as `analyze_exp009.py`.
- **A/A calibration.**
  - B4 vs B1 per cell, which run identical configurations: median, 95th-percentile and maximum |gap|, the fraction within τ, and a two-sided Wilcoxon.
  - The same summary for RL vs B1 on cells where they share a configuration.
- **Secondary results (descriptive, never deciding):**
  - SC7: fresh vs EXP-005 medians (±5%);
  - AQE: B0′ vs B0 per cell;
  - F3 probe outcomes;
  - drift: lag-1 autocorrelation of log deviations in queue order;
  - per-run resource metrics (CPU, RSS, shuffle, spill) recorded for every execution, which supply the measured data that a resource-utilization figure needs.

**4 — Pre-registered predictions.** Each is the manuscript's current conclusion, and each can fail. Results are published as observed. A REFUTED prediction is reported as a refutation, and the manuscript sentence it tested is corrected. EXP-005's record is not edited (DEC-037 §5).

- **P1.** *"Tuned configurations — including the learner's — beat Spark defaults"* (executive summary (i)/(iii); Table 1 C3/C4). Prediction: H2 is ACCEPTED for every RL arm.
- **P2.** *"The learned policies … did not beat a well-chosen static tuning"* (executive summary (iii)). Prediction: RL shows no H3 superiority over B3 ≡ B1.
- **P3.** *"The only above-noise RL-vs-static pattern is F4 `G-p2-sp16` vs `G-p8-sp16`"* (DAY34 §5, finding 4). Prediction, two parts:
  - RL is slower than B1 by more than τ, with Mann-Whitney p ≤ 0.05, on at least half of the F4 cells;
  - RL is within τ of B1 on at least 90% of the cells where both run the same configuration.
- **P4.** *"Competitive with equal-budget random search"* / *"RL ≈ random search"* (executive summary (iii); Table 1 C4). Prediction, read on the 95% CI of GMR(RL / B4):
  - entirely inside [1 − τ, 1 + τ] → AFFIRMED;
  - entirely outside → REFUTED;
  - straddling → INCONCLUSIVE.

  **Competing explanation, recorded in advance:** because B4 ≡ B1 on every TEST cell, if P3 and P5 hold then RL/B4 ≈ RL/B1. In that case the EXP-005 ordering "RL ≈ B4 < B1" reflected queue position, not search quality.
- **P5.** Implicit in the DEC-018 noise rule. Prediction: identical configurations executed in the same block differ by ≤ τ on at least 90% of cells, and the A/A Wilcoxon is non-significant.
- **P6.** *"F3|large WinError 32 is structural, AQE-independent"* (EXP-005, X6). Prediction: all four probed `F3_rdd|large` cells are STRUCTURAL-INCOMPLETE.
- **P7.** *"AQE mixed — only F2_join|large benefits"* (X6, DEC-047 §3). Prediction: B0′ is faster than B0 by more than τ, with Mann-Whitney p ≤ 0.05, on `F2_join|large|s3` and on no other EXP-005 cell.
- **P8.** *"Medium reproduces within ±5%, short cells drift"* (X10, DEC-049 §2). Prediction: B0 and B1 on `F4_ski|medium|s4` are within ±5% of their EXP-005 medians, and at least one of B0/B1 on `F4_ski|small|s4` is outside.

**5 — Stop and halt rules.**

- **Halt** if a non-probe (cell, unit) fails in two consecutive repetitions.
- **Halt** if less than 5 GiB is free on the data root.
- **Halt** on any guard refusal.
- **Halt** if the SC6 ledger moves. `validate_day31.py` check 22 is run before and after every stage and must stay at 483.
- **No interim significance testing.** Stages may be stopped for time only, never "until significant", and never at the first PASS.

**6 — Ledger.** **0 charged to SC6**: these are TEST-split evaluations, and SC6 caps training.

- TEST is crossed under the DEC-014 pattern: a purpose-scoped guard admits exactly the 42 cells, and `assert_test_execution_permitted` stays sealed.
- B0′ is the only AQE-on unit (the `allow_aqe` gate, DEC-047 pattern).
- Own register line: `results/experiments/exp-013/`.

**7 — Quiet-machine protocol (PLAN §23).** For the duration of the runs:

- the machine is on mains power, with the high-performance power plan;
- OneDrive sync is paused;
- no other heavy workloads run.

Per-run host CPU is recorded by sysmon so that contention can be diagnosed.

**8 — Artifacts.** These are new files only; no tracked file is modified before the close-out:

- `scripts/run_exp013.py`
- `scripts/analyze_exp013.py`
- `src/sparkrl/analysis/inference.py`
- `tests/unit/test_exp013.py`
- `tests/unit/test_inference.py`

At the separate close-out step:

- this entry is transcribed into `DECISIONS.md`;
- `exp013_analysis.json` is added to check 26's allow-list against DEC-053 (the DEC-052 D1 pattern, effective only once DEC-053 is committed at HEAD).

**9 — What this entry does NOT decide.**

- No threshold, baseline, policy or arm is changed.
- No retraining: 0 TRAIN executions.
- No pooling of B0′ with RL.
- No SC5 verdict, because the seen-advantage baseline was never frozen.
- EXP-005's recorded result stands as recorded.

**Status.** **SIGNED.** `Operator approval = GRANTED 2026-10-02 (in-session, full scope A–D)`. `SC6 cap = 500, NOT raised`. `SC6 ledger = 483 / 17`. `TEST = AUTHORIZED for exactly the 900 frozen queue entries (fingerprint fe159085…)`. Supervisor counter-signature: PENDING (never simulated).

---

**Amendment 1 (DEC-055, signed 2026-10-02).** The §5 two-consecutive-failure halt fired on `F3_rdd|medium|s4` (B0 failed reps 1–2, RL rep 1; all `WinError 32`, the documented Windows Spark file-lock failure; B1/B4/B2 succeeded). The halt is waived for that cell only: its remaining entries run exactly as frozen and failures are recorded; INCOMPLETE units are excluded from comparisons as §3 pre-registered; the halt stays in force for every other cell. The RL policy's failure on this cell is reported as a structural finding. Frozen code unchanged.
