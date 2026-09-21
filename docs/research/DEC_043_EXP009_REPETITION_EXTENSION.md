# DEC-043 | 2026-09-21 | EXP-009 repetition extension — per-cell n derived from the measured CI, staged by resolution efficiency; 0 charged to SC6 (Day 38)

**Decision ID:** DEC-043
**Date:** 2026-09-21
**Scope:** The number of repetitions in EXP-009 only. **Nothing else** — cells, conditions, timing semantics, acceptance criterion and register line are all unchanged from DEC-040.
**Status:** DECIDED — **extension AUTHORIZED**, scope-bound to §3.
**Standalone decision artifact.** `docs/research/DEC_043_EXP009_REPETITION_EXTENSION.md` carries the same content.
**Supersedes nothing.** DEC-040 stands; this amends **only** its §5 repetition count, and records the amendment rather than rewriting it. DEC-042 stands.

> **This entry performs 0 Spark executions and modifies no manifest, no result artifact and no prior decision entry.**
> **EXP-008 execution authorization = NO. A5 = DISABLED. TEST = NOT AUTHORIZED. SC6 cap = 500, NOT raised.**

---

**0 — Identifier resolution.** Ledger headings run DEC-001…DEC-026 and DEC-031…DEC-042. Next free: **DEC-043**.

**1 — Why.** DEC-042 recorded SC6 clause 2 as **INCONCLUSIVE**: at n = 5 every cell's 95% bootstrap CI straddles both 0 and the 5% gate, so the measurement decides nothing in either direction. DEC-042 §5 quantified the remedy per cell. This entry authorizes it. **The purpose is to make the gate decidable — NOT to obtain a particular verdict.** If the additional repetitions show overhead above 5%, that is the result and it will be recorded as such.

**2 — No new threshold is invented, and no duration floor is imposed.** A tempting design would exclude "short" cells by a wall-clock cut-off, but any such cut-off would be an invented parameter. It is also unnecessary: the per-cell `reps_needed_for_2pp_halfwidth` already derives from each cell's own measured dispersion and therefore **prices duration automatically**. The evidence that a floor would have been wrong: `F2_join|small` (2.1 s) needs **165** repetitions while `F1_agg|small` (21.7 s) needs **242** — the shorter job is the *cheaper* one to resolve. Cells are therefore ordered by **resolution efficiency**, lowest required n first, and nothing is excluded by duration.

**3 — AUTHORIZED SCOPE.** For each cell, repetitions per condition = **that cell's own `reps_needed_for_2pp_halfwidth` (sysmon component)**, as recorded in `results/evaluation/exp009_analysis.json`, executed in this order:

| Stage | Cell | n per condition | executions (×3) | cumulative | est. wall-clock |
|---|---|---|---|---|---|
| 1 | F5_mixed\|medium | 32 | 96 | 96 | ~36 min |
| 2 | F3_rdd\|small | 116 | 348 | 444 | ~79 min |
| 3 | F2_join\|medium | 141 | 423 | 867 | ~121 min |
| 4 | F2_join\|small | 165 | 495 | 1362 | ~17 min |
| 5 | F1_agg\|medium | 202 | 606 | 1968 | ~398 min |
| 6 | F1_agg\|small | 242 | 726 | 2694 | ~263 min |
| 7 | F5_mixed\|small | 716 | 2148 | 4842 | ~147 min |

**Stages may be stopped after any completed stage.** Each completed stage is independently analysable and independently reportable, and the acceptance in DEC-040 §7 is computed over whatever was actually run — the same reduced-coverage provision DEC-040 §6 already carries. **Stages 1–4 (1362 executions, ≈4.2 h) are the recommended target**: they adjudicate four of the seven cells at the lowest cost per decided cell.

Already-recorded observations are **retained and pooled** with the new ones; nothing is discarded and no prior observation is re-run or overwritten.

**4 — Ledger: 0 charged to SC6.** Unchanged from DEC-040 §2 and unchanged by volume: every cell is **validation split, seed 3**, and SC6 caps **training**. The SC6 ledger stays **483 / 500, remaining 17**. Executions are recorded on EXP-009's own register line (`docs/PLAN.md` line 316, a planning estimate, not a cap — DEC-040 §6). **At the full seven stages the register-line estimate is exceeded roughly 240-fold; that is disclosed here, not hidden.** The cost of this decision is **wall-clock, not budget**.

**5 — Everything else is unchanged.** Cells, the three conditions (FULL / NO-SYSMON / NEITHER), interleaving within (cell, rep), AQE OFF, the authoritative Day-3 timing semantics, the per-run manifest recording `sysmon_enabled` and `event_log_enabled`, the separate reporting of the two components and the DEC-040 §4 event-log configuration caveat, the 5% acceptance from `docs/PLAN.md` line 45, and DEC-042's interval rule — a verdict only when the whole CI lies on one side of the gate. **`F3_rdd|medium` remains excluded** (DEC-040 §6, DEC-042 §2).

**6 — STOP rule,** as DEC-040 §8 and corrected by DEC-042 §7 — keyed on the **cell**, not the (cell, condition). Execution halts and the partial result is recorded if a cell fails twice, any manifest shows a cell outside scope or `aqe_enabled: true`, or **the SC6 ledger moves by even one execution**.

**7 — A prediction this entry records in advance, so it can be wrong.** The power model behind §3 says the CI half-width shrinks as 1/√n. At the authorized n each completed cell should reach a half-width of about **2 percentage points**. **If the observed half-widths do not shrink as predicted, the noise is not independent between repetitions** — drift, thermal or host contention — and the model is wrong. Recording the prediction now makes that falsifiable rather than something rationalised afterwards.

**8 — What this entry does NOT decide.** Whether SC6 clause 2 passes or fails — that is the measurement's to answer. Whether `docs/PLAN.md`'s EXP-009 register estimate should be amended. Whether to repair `F3_rdd|medium`. Any EXP-005b, EXP-008, EXP-010 or EXP-011 matter. It authorizes **no TRAIN cell, no TEST cell and no AQE-on run**.

**Status.** **DECIDED. `EXP-009 repetition extension = AUTHORIZED`**, scope-bound to §3, stoppable after any completed stage, **0 charged to SC6**. `SC6 cap = 500, NOT raised`. `SC6 ledger = 483 / 17, unchanged`. `EXP-008 execution authorization = NO`. `A5 = DISABLED`. `TEST = NOT AUTHORIZED`. `docs/PLAN.md = UNCHANGED`. Historical decisions (DEC-001 … DEC-026, DEC-030 … DEC-042) = **UNCHANGED**. Supervisor counter-signature: **PENDING** (conventional expectation only; never simulated; not a prerequisite under DEC-018 Decision A). **This entry performs 0 Spark executions and trains nothing.**

---

*Standalone companion artifact. The authoritative log entry is the appended DEC-043 section of DECISIONS.md; this document carries the same decision content, self-contained.*
