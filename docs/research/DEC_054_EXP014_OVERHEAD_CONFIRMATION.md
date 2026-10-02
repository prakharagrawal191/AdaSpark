# DEC-054 (SIGNED) | 2026-10-02 | EXP-014 monitoring-overhead confirmation under DEC-044 D3's pre-registered paired statistic; VALIDATION split, 0 charged to SC6

**Status:** **SIGNED 2026-10-02 — operator approval GRANTED.** Provenance, recorded exactly: the operator approved this draft in-session on 2026-10-02 by selecting *"Sign; run after EXP-013 (Recommended)"* in answer to a question stating that the choice is recorded as the operator signature for exactly this scope. Execution starts only after EXP-013 has finished. Supervisor counter-signature: PENDING (never simulated).
**Supersedes nothing.** DEC-040, DEC-042, DEC-043 and DEC-044 stand unchanged. EXP-009's recorded verdicts are not reopened (DEC-044 D1). EXP-014 is a fresh measurement reported beside them.

> **Writing this draft performed 0 Spark executions.** SC6 cap = 500, NOT raised. SC6 ledger = 483 / 17, unchanged. TEST = untouched (VALIDATION only). A5 = DISABLED. `docs/PLAN.md` = UNCHANGED.

---

**0 — Identifier resolution.** Next free decision after DEC-053: **DEC-054**. Next free experiment: **EXP-014**.

**1 — Why.**
- **The conclusion under test.** The manuscript concludes that monitoring overhead "sits below the 5% budget on six of seven tested cells" (executive summary (iv)), with `F1_agg|small` INCONCLUSIVE at its full authorized n. DEC-044 found the cause: the DEC-040 §7 statistic, a difference of independent medians, discards the within-(cell, rep) matching. On that same cell the paired half-width is 0.42 pp against 14.95 pp unpaired.
- **What DEC-044 D3 fixed in advance.** For every **future** overhead measurement, the paired statistic is the **primary** acceptance quantity. It was fixed on 2026-09-24, before any such data existed.
- **What EXP-014 does.** It is that future measurement. It can affirm or refute the overhead conclusion under the statistic the project committed to before seeing data. It is not a re-analysis of EXP-009 (D1 and D6 are respected).

**2 — Scope (authorized only if signed).**
- **Cells (7).** The 7 EXP-009 analysed cells on the VALIDATION split, seed 3. `F3_rdd|medium` stays excluded (DEC-040 §6).
- **Conditions.** FULL, NO-SYSMON and NEITHER, configuration B0, AQE OFF. All of these are taken from `scripts/run_exp009.py` itself (`CONDITIONS`, `config_for`, `exp009_guard`, the per-cell timeouts).
- **Repetitions per cell, fixed from precision alone before any EXP-014 data.** The rule: the smallest n in {10, 15, 20, 30} whose mean windowed paired half-width, for both components, is ≤ 2.5 pp in the committed EXP-009 extension data. The resulting values:

  | Cell | n |
  |---|---|
  | `F1_agg\|medium` | 10 |
  | `F1_agg\|small` | 15 |
  | `F2_join\|medium` | 10 |
  | `F2_join\|small` | 10 |
  | `F3_rdd\|small` | 10 |
  | `F5_mixed\|medium` | 15 |
  | `F5_mixed\|small` | 20 |

  That is 90 blocks and **270 runs**; queue fingerprint `709d2024a62599466d297c77a6b52178a0f6b238ed787c64852f73d541c13ed9`, pinned by a unit test. Half-width depends on dispersion, not on where the estimate falls relative to the gate, so this choice cannot steer the outcome.
- **Order.** Rep-major. Cells are shuffled per rep, and the three conditions are shuffled per (cell, rep) block (seed 20261002). Randomizing the within-block order removes the position effect that EXP-009's fixed FULL → NO-SYSMON → NEITHER sequence could carry into a paired statistic.
- **Estimated cost.** About 3.6 h at September execution speeds, and up to about 6.5 h if the ~1.8× slowdown observed at the start of EXP-013 persists.

**3 — Frozen analysis (`scripts/analyze_exp014.py`, written and unit-tested before any data; sha256 frozen into `spec.json` at the first run).**
- **Primary (DEC-044 D3), per cell and component.** The statistic is the median over repetitions of the per-repetition relative difference:
  - sysmon component: 100·(FULL − NO-SYSMON)/NO-SYSMON;
  - eventlog component: 100·(NO-SYSMON − NEITHER)/NEITHER.

  The interval is a 95% percentile bootstrap over repetitions (4,000 resamples, seed 0, `analyze_exp009.py`'s indexing). The verdict uses DEC-042's whole-interval rule against the 5% gate: PASS iff the whole CI is ≤ 5; FAIL iff the whole CI is > 5; INCONCLUSIVE otherwise. A repetition counts only when all three of its conditions are timing-valid. The components are reported separately (DEC-040 §4).
- **Secondary (never deciding).**
  - The DEC-040 §7 unpaired statistic, for continuity with EXP-009.
  - The DEC-044 D4 steady-state screen: exact optimal partitioning for a change in mean on the log-time series (the optimum PELT computes), robust σ, penalty 15·ln n, following Barrett et al. (OOPSLA 2017). Each (cell, condition) series is classified flat / steady / no-steady-state. Nothing is excluded.
  - Whether EXP-009's recorded paired estimates fall inside the fresh intervals.

**4 — Pre-registered predictions (the manuscript's current statements; each can fail).**
- **Q1, sysmon component** (executive summary (iv)): PASS on ≥ 6 of 7 cells with 0 FAIL → AFFIRMED; any FAIL or ≤ 4 PASS → REFUTED; otherwise INCONCLUSIVE.
- **Q2, eventlog component** (same sentence, reported separately per DEC-040 §4): same rule.
- **Q3, "point estimates within ±0.2%" and DEC-044's paired diagnostics (−0.214% … +0.172%).** EXP-009's recorded paired median lies inside the fresh 95% CI for ≥ 12 of the 14 cell-components → AFFIRMED; ≤ 8 → REFUTED; otherwise INCONCLUSIVE.

**5 — Stop rules** (DEC-040 §8 as corrected by DEC-042). Halt on any of:
- the 2nd timing-invalid run of a cell (across conditions);
- `aqe_enabled` true;
- less than 5 GiB free on the data root;
- any guard refusal;
- the SC6 ledger moving (check 22 before and after).

No interim testing; stopping is for time only.

**6 — Ledger.** **0 charged to SC6**: VALIDATION split, the DEC-040 §2 basis. Own register line `results/experiments/exp-014/`. The quiet-machine protocol (PLAN §23) applies as in DEC-053 §7. EXP-014 runs only after EXP-013 has finished, never concurrently.

**7 — What this entry does NOT decide.** It does not reopen any EXP-009 verdict or statistic (DEC-044 D1). It does not change the 5% gate. It authorizes no TRAIN or TEST cell and no AQE-on run. It does not decide whether SC6 clause 2 is evidenced "as a whole": that is for the close-out entry to state from the recorded verdicts.

**Status.** **SIGNED.** `Operator approval = GRANTED 2026-10-02 (in-session)`. `SC6 cap = 500, NOT raised`. `SC6 ledger = 483 / 17`. `VALIDATION only; TEST untouched`. Supervisor counter-signature: PENDING (never simulated).
