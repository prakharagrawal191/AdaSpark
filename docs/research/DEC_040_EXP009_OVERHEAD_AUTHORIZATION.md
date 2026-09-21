# DEC-040 | 2026-09-21 | EXP-009 monitoring-overhead register line and execution authorization — VALIDATION-split protocol, 0 charged to SC6; SC6 clause 2 becomes evidenceable (Day 38)

**Decision ID:** DEC-040
**Date:** 2026-09-21
**Scope:** The EXP-009 monitoring-overhead experiment only: which register line it charges, its frozen protocol, and its execution authorization. **Nothing else.**
**Status:** DECIDED — **EXP-009 execution AUTHORIZED**, scope-bound to §5. EXP-008 execution authorization is unchanged and remains NO.
**Standalone decision artifact.** The authoritative log entry is this appended DEC-040 section of `DECISIONS.md`; `docs/research/DEC_040_EXP009_OVERHEAD_AUTHORIZATION.md` carries the same decision content, self-contained (the DEC-031/DEC-032 convention).
**Supersedes nothing.** DEC-011, DEC-012, DEC-026, DEC-030 … DEC-039 are unchanged.

> **This entry performs 0 Spark executions, trains nothing, executes no TEST, creates no run directory, and modifies no manifest, no result artifact and no prior decision entry.**
> **EXP-008 execution authorization = NO. A5 = DISABLED. TEST = NOT AUTHORIZED. SC6 cap = 500, NOT raised. `docs/PLAN.md` = UNCHANGED.**

---

**0 — Identifier resolution.** `DECISIONS.md` headings run DEC-001…DEC-026 and DEC-031…DEC-039 (DEC-030 recorded outside the ledger per DEC-031 §0). Next free identifier: **DEC-040**.

**1 — Why this entry exists: SC6 is half unevidenced.** `docs/PLAN.md` line 45 states SC6 with **two** clauses: *"SC6 = training ≤500 executions, **monitoring overhead ≤5% of job time**"*. Clause 1 is satisfied and reconciled at **483/500, remaining 17** (DEC-038). **Clause 2 has no measurement anywhere in the repository.** `monitor_overhead_s` is named in the frozen metrics schema (`docs/PLAN.md` line 172) but appears in **zero** recorded result files; the only "overhead" in `docs/day03_timing_harness.md:39` is *cold-start* overhead, a different quantity. PLAN line 266 scheduled an EXP-009 "first" pass on Day 21 and line 284 the "final" on Day 38; neither produced a stored measurement. **A success criterion of this project currently has no supporting evidence, and unlike EXP-008's derived ablation it cannot be obtained by recomputation** — monitoring overhead is the difference between monitored and unmonitored execution and must be measured.

**2 — Register line: EXP-009 charges SC6 ZERO, by protocol construction.** DEC-034 §3 established the discriminator: *the exemption turns on the **SPLIT**, never on an experiment having its own register line*, and SC6 caps **TRAINING**. Applying it:

`docs/PLAN.md` line 163 defines the splits: **Train** = {F1,F2,F3,F5} × {S,M} × seeds{0,1,2}; **Validation** = same families × seed{3}; **Test** = all families × {L} × seeds{3,4} + F4 + public + F5 unseen.

| EXP-009 component | Split | Charge to SC6 |
|---|---|---|
| **micro** (5 MB; `docs/PLAN.md` lines 167, 196) | **none** — the splits are defined over scales S ≈ 0.3 GB / M ≈ 1 GB / L ≈ 3 GB; a 5 MB micro instance is in no split | **0** |
| **real** — FROZEN HERE to the **VALIDATION** split, seed 3 | validation | **0**, on the same footing as EXP-003 (DEC-012: *"EXP-003 is a separate register line and is NOT charged to SC6's ≤500 **TRAINING** cap"*) |

**The validation choice is deliberate and costs nothing scientifically.** Monitoring overhead is a property of the **instrumentation**, not of workload semantics: the sampler thread and the event-log writer impose the same cost whichever cell the workload reads. Measuring on validation cells therefore yields the same quantity as measuring on TRAIN cells while charging the TRAIN cap nothing. **This entry does NOT create a new exemption category** — it selects, within an experiment whose cells were never frozen, cells that the existing DEC-012 exemption already covers.

**Had the real arm been put on TRAIN cells** it would have charged SC6 and ~20 required executions against **17** remaining would have forced the DEC-034 §9 cap-amendment conversation **for a success criterion satisfiable no other way**. That collision is avoided by protocol, not by reinterpretation. It is recorded here because it was real.

**3 — Feasibility: the protocol is implementable TODAY with no new code.** Both monitoring components already have off-switches, verified by reading the source:

| Component | Switch | Evidence |
|---|---|---|
| psutil system sampler | `sysmon_enabled: bool = True` | `src/sparkrl/experiments/runner.py:265`, threaded to `SystemSampler(SamplerConfig(enabled=sysmon_enabled)).start()` at `:303`. Disabled, `start()` returns immediately with `_error = "disabled by config"` (`src/sparkrl/monitoring/sysmon.py:106-110`) — no thread is created and no sample is taken. |
| Spark event log | `SparkConfig.event_log_enabled: bool = True` | `src/sparkrl/spark/config.py:31`; applied at `src/sparkrl/spark/session.py:57-64`, which sets `spark.eventLog.enabled` true or false on the builder. |

**No implementation decision is required and this authorization is therefore NOT conditional** (contrast DEC-041, which is).

**4 — The confound this protocol must not hide, and how it is handled.** The two components are **not** symmetric controls:

* Disabling the **psutil sampler** removes an *external* observer thread. The Spark job is byte-for-byte the same job. This is a clean paired control.
* Disabling the **event log** changes `spark.eventLog.enabled`, i.e. **Spark's own configuration**. The unmonitored arm is then not the same Spark execution with an observer removed; it is a differently configured Spark execution. Treating the two as one lump would report a number that is part observer cost and part configuration difference.

**Therefore the two components are measured and reported SEPARATELY**, never summed into a single "monitoring overhead" figure without also reporting the split. The event-log arm's configuration difference is disclosed in the overhead report as a stated limitation, not silently absorbed.

**5 — FROZEN PROTOCOL (this is the authorized scope; nothing outside it is authorized).**

* **Cells.** micro (5 MB) and the **validation** split only: {F1,F2,F3,F5} × {S,M} × **seed 3**. **No TRAIN cell. No TEST cell. No F4. No L scale.**
* **Conditions,** per cell, in this order: (a) **FULL** — `sysmon_enabled=True`, `event_log_enabled=True`; (b) **NO-SYSMON** — `sysmon_enabled=False`, `event_log_enabled=True`; (c) **NEITHER** — `sysmon_enabled=False`, `event_log_enabled=False`.
* **Repetitions.** 5 per (cell, condition), matching the frozen `EVALUATION_REPETITIONS = 5`.
* **Timing.** The authoritative Day-3 semantics, unchanged: `execution_time_s`, source `runner`, warm-up executed and discarded (`docs/PLAN.md` §22). No wall-clock and no driver clock is substituted.
* **AQE OFF** (`docs/PLAN.md` §7), as for every main-study measurement.
* **Every run writes an immutable manifest** recording its `sysmon_enabled` and `event_log_enabled` values, so each observation is attributable to its condition after the fact.

**6 — Worst-case count and ledger effect.** Cells = micro (1) + validation (4 families × 2 scales = 8) = **9**. Conditions = 3. Repetitions = 5. **Worst case = 9 × 3 × 5 = 135 executions**, of which **0 are charged to SC6** (§2). The SC6 ledger stays **483 / 500, remaining 17, unchanged by this experiment**. EXP-009 executions are recorded on **EXP-009's own register line** (`docs/PLAN.md` line 316, ~20 — a planning **estimate**, not a cap; no decision in this ledger calls a register line a cap, and every use of "cap" is reserved for SC6). **The worst case exceeds that estimate and that is disclosed here, not hidden.** An operator who prefers to stay near the estimate may run the micro cell plus a single validation family (1 + 2 = 3 cells → 45 executions) and record the reduced coverage; the acceptance in §7 is computed over whatever was actually run.

**7 — Acceptance criterion. No new threshold is invented.** The 5% comes from `docs/PLAN.md` line 45 and from nowhere else. Overhead for a component is computed **per (cell, condition-pair)** as the paired relative difference of the **median** `execution_time_s` over the 5 repetitions:

`overhead_sysmon% = 100 × (median(FULL) − median(NO-SYSMON)) / median(NO-SYSMON)`
`overhead_eventlog% = 100 × (median(NO-SYSMON) − median(NEITHER)) / median(NEITHER)`

Reported with median ± IQR per `docs/PLAN.md` line 180. **Acceptance: each reported component overhead ≤ 5%.** The two components are reported separately (§4) and, if a combined figure is also reported, it is reported **as a sum of separately measured parts with the event-log configuration caveat attached**. **No inferential test, no significance threshold and no correction procedure is introduced by this entry** — PLAN line 180's statistics are available for the report, and DEC-030 §8's descriptive-only posture is not disturbed.

**8 — STOP rule.** Execution halts immediately and the partial result is recorded, unanalysed, if any of: a run fails or times out (`timeout = 5× default-config median`, PLAN §7) twice on the same cell; any manifest records a cell outside §5; any manifest records `aqe_enabled: true`; the SC6 ledger moves by even one execution (it must not — §2); or any TRAIN or TEST cell appears in any EXP-009 manifest. A STOP is a recorded outcome, never a silent retry.

**9 — Exhaustively NOT permitted by this entry.** No TRAIN cell. No TEST cell (TEST stays sealed; DEC-018 Decision B is untouched). No F4 and no L scale. No AQE-on run (that is EXP-005b's, sealed separately). No training, no Q update, no policy write, no checkpoint. No EXP-008 execution of any kind. No amendment of `docs/PLAN.md`, of SC6's cap, or of any frozen configuration. No editing of any recorded manifest or hash. No re-run of any prior experiment.

**10 — What this entry does NOT decide.** Whether EXP-009's own register-line estimate should be amended to match §6's worst case. Whether a combined single-figure overhead may be quoted in the thesis (the report must carry §4's caveat either way). Any EXP-008 matter. EXP-005b, which DEC-041 addresses. Whether `monitor_overhead_s` should be back-filled into the metrics schema for future runs — it is **not** required by this protocol, which derives overhead from paired `execution_time_s` medians rather than from a self-reported field.

**Status.** **DECIDED. `EXP-009 execution authorization = APPROVED`**, scope-bound to §5, worst case **135** executions, **0 charged to SC6**. Sealed state until execution: `EXP-009 — EXECUTION AUTHORIZED (scope-bound, DEC-040) — NOT YET EXECUTED`. `SC6 cap = 500, NOT raised`. `SC6 ledger = 483 / 17, unchanged by this experiment`. `EXP-008 execution authorization = NO`. `A5 = DISABLED`. `TEST = NOT AUTHORIZED`. `docs/PLAN.md = UNCHANGED`. Historical decisions (DEC-001 … DEC-026, DEC-030 … DEC-039) = **UNCHANGED**. Supervisor counter-signature: **PENDING** (conventional expectation only; never simulated; not a prerequisite under DEC-018 Decision A). **NO SUPERVISOR HAS REVIEWED THIS ENTRY.** A future review is a new entry; this one is never rewritten. **This entry performs 0 Spark executions and trains nothing.**

---

*Standalone companion artifact. The authoritative log entry is the appended DEC-040 section of DECISIONS.md; this document carries the same decision content, self-contained (the DEC-031/DEC-032 convention).*
