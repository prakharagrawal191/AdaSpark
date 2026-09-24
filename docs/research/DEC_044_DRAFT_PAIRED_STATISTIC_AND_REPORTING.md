# DEC-044 (DRAFT) | EXP-009 overhead statistic — how the paired analysis may be reported, and what is pre-registered for future overhead work

**Decision ID:** DEC-044
**Date drafted:** 2026-09-24 (Day 41)
**Status:** **DRAFT — NOT SIGNED. THIS DOCUMENT AUTHORIZES NOTHING.**
It is not appended to `DECISIONS.md` and confers no authorization until an operator signs it.
Drafted following the DEC-014 precedent for a PENDING decision artifact.
**Scope:** the reporting status of the paired diagnostic, and the pre-registration of a
statistic for *future* overhead measurement. **Nothing else.**

> **This entry performs 0 Spark executions, trains nothing, executes no TEST, and modifies no
> manifest, no result artifact and no prior decision entry.**
> **SC6 cap = 500, NOT raised. SC6 ledger = 483 / 17. TEST = NOT AUTHORIZED. `docs/PLAN.md` = UNCHANGED.**

---

## 0 — Why this draft exists

DEC-043 §3 is fully discharged: seven stages, 4842 executions, 0 charged to SC6
(`docs/research/DAY39_DEC043_EXP009_STAGES_1_7_EXECUTION.md`). Six of seven analysed cells are
decided, all PASS. One — `F1_agg|small` — is INCONCLUSIVE **at its full authorized n**, with a
half-width that ended *wider* than at n = 5.

That execution produced a measurement which, if acted on, would change a signed experiment's
acceptance quantity. It must not be acted on silently, and it must not be discarded either.
This draft exists so the choice is made explicitly, in the open, and **after** the confirmatory
result is already on the record at `7937db8`.

## 1 — The finding at issue

The DEC-040 §5 protocol interleaves FULL / NO-SYSMON / NEITHER **within each (cell, rep)**, so
repetitions are already matched. Every level shift measured in EXP-009 is **common-mode** — it
moves all three conditions at the same rep together. The DEC-040 §7 acceptance quantity is the
difference of *independent* medians, which discards that matching and carries the shift's full
variance.

Measured gap, same bootstrap seed and resample count (`analysis_ext.json`, `paired_diagnostic`):

| Cell | n | unpaired half-width (adjudicated) | paired half-width (diagnostic) | ratio |
|---|---|---|---|---|
| `F5_mixed\|medium` | 37 | 2.00 pp | 1.07 pp | 1.9× |
| `F3_rdd\|small` | 121 | 0.78 pp | 0.39 pp | 2.0× |
| `F2_join\|medium` | 146 | 0.51 pp | 0.43 pp | 1.2× |
| `F2_join\|small` | 170 | 0.48 pp | 0.36 pp | 1.3× |
| `F1_agg\|medium` | 207 | 0.34 pp | 0.25 pp | 1.4× |
| `F1_agg\|small` | 247 | **14.95 pp** | **0.42 pp** | **35.7×** |
| `F5_mixed\|small` | 721 | 0.86 pp | 0.18 pp | 4.8× |

Paired point estimates agree across all seven cells (−0.214% … +0.172%).

**The temptation this draft refuses.** Adopting the paired statistic retroactively would decide
`F1_agg|small`, complete coverage at 7 of 7, and make SC6 clause 2 evidenceable. That is exactly
why it must not be done retroactively: the statistic would have been selected *because* it
produces the preferred outcome, on data already seen.

## 2 — PROPOSED DECISIONS

**D1 — The EXP-009 acceptance quantity is NOT reopened.** DEC-040 §7 (difference of independent
medians) and DEC-042 §3 (interval rule) stand unchanged for EXP-009. `F1_agg|small` remains
**INCONCLUSIVE**. The six PASS verdicts stand as recorded. SC6 clause 2 remains **unevidenced as
a whole**, exactly as `DAY39…§5` states.

**D2 — The paired analysis MAY be reported, as a clearly-labelled secondary analysis.** It may
appear in write-ups provided it is labelled **exploratory / secondary**, presented alongside —
never instead of — the registered unpaired result, and never described as deciding
`F1_agg|small` or as satisfying SC6 clause 2. This is the standard confirmatory/exploratory
split; it is honest precisely because the confirmatory result was recorded first, at `7937db8`.

**D3 — For any FUTURE monitoring-overhead measurement, the PAIRED statistic is pre-registered
as the primary acceptance quantity**, fixed here *before* any such data exist: the median over
repetitions of the per-repetition relative difference, with the same 95% percentile bootstrap
(4000 resamples, seed 0) and the same DEC-042 interval rule against the unchanged 5% gate
(`docs/PLAN.md` line 45). No threshold is altered by this.

**D4 — A steady-state screen is pre-registered for future work, and is NOT applied
retroactively.** Future overhead experiments should report whether each series reaches a stable
regime before the acceptance quantity is computed, following the changepoint approach of
Barrett et al. (OOPSLA 2017). EXP-009's recorded observations are **not** re-analysed under it
and **no observation is excluded** from any existing statistic.

**D5 — Novelty obligations for any write-up.** Any paper or report drawing on EXP-009 must cite
**Kalibera & Jones, ISMM 2013** (`doi:10.1145/2464157.2464160`) and **Barrett et al., OOPSLA
2017** (`doi:10.1145/3133876`), and must **not** claim priority for the observation that
benchmark repetitions are non-independent or that benchmarks may fail to reach a steady state.
The contribution is to be stated narrowly, as in `DAY39…§3.8`. Publication-oriented language is
not to be introduced into research artifacts.

**D6 — `F1_agg|small` receives no further repetitions on this authorization.** Its interval is
non-convergent under the present statistic, so additional repetitions are not evidently the
remedy, and DEC-043 authorizes no count beyond the 242 already run.

## 3 — What this draft does NOT propose

It does not amend DEC-040, DEC-042 or DEC-043. It does not restate, relax or withdraw SC6
clause 2 or the 5% gate. It does not amend `docs/PLAN.md`. It does not authorize any Spark
execution, any TRAIN cell, any TEST cell or any AQE-on run. It does not repair
`F3_rdd|medium`. It decides no EXP-005b, EXP-008, EXP-010 or EXP-011 matter. It does not
re-analyse any recorded observation.

## 4 — Ledger

**0 charged to SC6.** SC6 ledger **483 / 500, remaining 17, unmoved.** This draft performs no
execution of any kind.

---

**Status.** **DRAFT. NOT SIGNED. AUTHORIZES NOTHING.** Operator signature: **ABSENT** — never
simulated. Until signed, the paired analysis remains a diagnostic only (`DAY39…§3.5`), and
every EXP-009 verdict rests on the frozen DEC-040 §7 statistic. Historical decisions
(DEC-001 … DEC-026, DEC-030 … DEC-043) = **UNCHANGED**.
