# DEC-042 | 2026-09-21 | EXP-009 result — SC6 clause 2 is INCONCLUSIVE, not failed; the measurement cannot adjudicate a 5% gate at n=5 (Day 38)

**Decision ID:** DEC-042
**Date:** 2026-09-21
**Scope:** The EXP-009 result and its consequences for SC6 clause 2. **Nothing else.**
**Status:** DECIDED.
**Standalone decision artifact.** On signature, the authoritative log entry is the appended DEC-042 section of `DECISIONS.md`; this document carries the same decision content, self-contained.
**Supersedes nothing.** DEC-040 is unchanged; its authorization, protocol and acceptance criterion stand exactly as signed.

> **This entry performs 0 Spark executions, trains nothing, executes no TEST, and modifies no manifest and no prior decision entry.**
> **EXP-008 execution authorization = NO. A5 = DISABLED. TEST = NOT AUTHORIZED. SC6 cap = 500, NOT raised. `docs/PLAN.md` = UNCHANGED.**

---

**0 — Identifier resolution.** Ledger headings run DEC-001…DEC-026 and DEC-031…DEC-041. Next free: **DEC-042**.

**1 — What was executed.** EXP-009 ran under DEC-040, scope-bound to §5. **105 usable observations**: 7 cells × 3 conditions (FULL / NO-SYSMON / NEITHER) × 5 repetitions, all complete. 12 further observations are error records, retained. **Charged to SC6: 0** — every cell is validation split, seed 3, exactly as DEC-040 §2 froze. The SC6 ledger is **483 / 500, remaining 17, unmoved by this experiment**, verified by `scripts/validate_day31.py` check 22.

**2 — Coverage: 7 of 8 authorized cells.** `F3_rdd|medium` is excluded under **DEC-040 §6**, which provides that acceptance is *"computed over whatever was actually run"*. It failed 9 of 9 attempts with a PySpark Python-worker exception in the RDD path. The exclusion rests on evidence predating this experiment: **EXP-002 recorded 18 FAILED / 8 COMPLETED for `F3_rdd|medium` against 25 COMPLETED / 1 FAILED for `F3_rdd|small`**, and `results/baseline/F3_rdd/` holds only `small`. The cell is **long-standing fragile, not an EXP-009 regression**. Its 9 failure records are **retained, not deleted**. Repairing the F3 RDD workload is separate work and is **not** undertaken here — debugging a workload inside an overhead experiment would confound it.

**3 — THE RESULT: INCONCLUSIVE. SC6 clause 2 remains unevidenced.**

The analysis first recorded **FAIL**, on one cell reading `sysmon = 6.715%` against the 5% gate. **That verdict is withdrawn as unsupportable**, on three findings from the run's own data:

| Finding | Evidence |
|---|---|
| The gate sits inside the noise | run-to-run CV of `execution_time_s` is **2.6 – 13.6%** across the seven cells; at n = 5 the sampling error of a difference of medians is the same order as the 5% being tested |
| Variance dominates the effect | **7 of 14** component measurements are **negative**, down to **−13.42%**. Instrumentation cannot make a job run faster; those are variance, not overhead |
| No cell can decide | computing the **95% bootstrap CI that `docs/PLAN.md` line 180 already prescribes**, **every** cell's interval straddles both 0 and 5%. The widest is **[−22.65, +25.21]** |

**FAIL was unsupportable — and PASS would have been equally unsupportable.** The honest outcome is that the measurement lacks the resolution to adjudicate the gate in either direction.

**Adjudication is therefore by INTERVAL, not point estimate:** a component verdict is returned only when the whole interval lies on one side of the gate; a straddling interval is **INCONCLUSIVE in both directions**. This is neither a softened FAIL nor a rescued PASS.

**Nothing is invented.** PLAN line 180 lists the 95% bootstrap CI among this project's statistics; the 5% threshold and its source (PLAN line 45) are untouched; no significance test, no correction procedure and no new threshold is introduced; DEC-030 §8's descriptive-only posture is undisturbed. Point estimates, medians and IQRs are unchanged — only the verdict logic and the reported uncertainty are added. The bootstrap is seeded (seed 0, 4000 resamples) so re-analysis reproduces byte-identically, as the Day-28/29 analysis-reproducibility norm requires.

**4 — The central estimate, reported as an observation and not as a finding.** Across the seven cells the clean component — the psutil sampler, measured against an identical Spark job with no configuration difference — has a **median of 1.21% and a mean of 1.63%**. That is well inside the 5% gate. **It is recorded here as an observation, not asserted as a result**, because the intervals above do not support asserting it. The event-log component carries the additional DEC-040 §4 confound: disabling it changes Spark's own configuration, so its arm is not a clean control.

**5 — What would settle it, per cell.** `reps_needed_for_2pp_halfwidth`, now recorded in the artifact:

| Cell | median duration | reps needed |
|---|---|---|
| F5_mixed\|medium | 22.5 s | **32** |
| F3_rdd\|small | 13.8 s | 116 |
| F2_join\|medium | 16.1 s | 141 |
| F2_join\|small | 2.1 s | 165 |
| F1_agg\|medium | 39.9 s | 202 |
| F1_agg\|small | 21.7 s | 242 |
| F5_mixed\|small | 3.9 s | **716** |

**The spread is the design signal: short jobs cannot resolve a 5% effect.** `F5_mixed|small` (3.9 s, CV 13.6%) needs 716 repetitions; `F5_mixed|medium` (22.5 s) needs 32. A future decision that wants a decisive answer should concentrate repetitions on the longer-duration cells and state the duration floor it adopts. **These are validation cells, so additional repetitions charge SC6 nothing** — the cost is wall-clock, not budget.

**6 — Consequence for SC6, stated plainly.** SC6 has two clauses. **Clause 1 (`training ≤500 executions`) is SATISFIED** at 483/500. **Clause 2 (`monitoring overhead ≤5% of job time`) is NOT satisfied and NOT refuted — it is unevidenced.** Therefore **SC6 as a whole is not yet met**, and no write-up may claim it is. Equally, **no write-up may claim monitoring overhead exceeds the budget** — the data does not support that either. The honest statement is that the overhead is *not yet measured to the resolution the criterion requires*.

**7 — Implementation correction adopted retrospectively.** `scripts/run_exp009.py` keyed its STOP counter on `family|scale|condition`, so it halted after two failures *within a condition*; DEC-040 §8 says *"twice on the same **cell**"*. The implementation was **laxer than the authorization** — under the written rule `F3_rdd|medium` would have halted at 2 failures, not 9. The driver is corrected to key on `family|scale`, and the correction is **adopted here retrospectively**, in the amend-and-ratify-concurrently shape of `9e83742` and DEC-018 Decision E.

**8 — What this entry does NOT decide.** Whether to run the additional repetitions §5 quantifies, and at what duration floor. Whether to repair the F3 RDD workload at medium scale. Whether SC6 clause 2 should be restated, relaxed or withdrawn in `docs/PLAN.md` (PLAN is unchanged, and no decision has ever amended it). Whether a combined single-figure overhead may be quoted anywhere. Any EXP-008 or EXP-005b matter. It makes **no** claim about what a better-resolved measurement would have shown.

**Status.** **DECIDED.** EXP-009 executed **105 usable observations over 7 of 8 authorized cells, 0 charged to SC6**; ledger **483 / 17, unmoved**. **SC6 clause 2 = INCONCLUSIVE** — unevidenced, neither satisfied nor refuted; **SC6 as a whole is therefore NOT met**. The prior FAIL verdict is **withdrawn as unsupportable**. `SC6 cap = 500, NOT raised`. `EXP-008 execution authorization = NO`. `A5 = DISABLED`. `TEST = NOT AUTHORIZED`. `docs/PLAN.md = UNCHANGED`. Historical decisions (DEC-001 … DEC-026, DEC-030 … DEC-041) = **UNCHANGED**. Supervisor counter-signature: **PENDING** (conventional expectation only; never simulated; not a prerequisite under DEC-018 Decision A). **This entry performs 0 Spark executions and trains nothing.**
