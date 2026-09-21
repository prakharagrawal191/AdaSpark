# DEC-041 | 2026-09-21 | EXP-005b AQE-complementarity — scope frozen at B0' alone (35 runs, separate AQE-on ledger, 0 to SC6); execution authorization CONDITIONAL on a driver that does not yet exist (Day 38)

**Decision ID:** DEC-041
**Date:** 2026-09-21
**Scope:** EXP-005b only — its arm set, its ledger, its protocol, the no-pooling rule that governs its output, and the conditions under which its execution may be authorized. **Nothing else.**
**Status:** DECIDED — scope frozen; **execution authorization CONDITIONAL and therefore NOT YET GRANTED** (§6). TEST remains sealed until the condition is met.
**Standalone decision artifact.** The authoritative log entry is this appended DEC-041 section of `DECISIONS.md`; `docs/research/DEC_041_EXP005B_AQE_AUTHORIZATION.md` carries the same decision content, self-contained.
**Supersedes nothing.** DEC-016, DEC-017, DEC-018, DEC-020 and DEC-034 are unchanged; no historical decision entry is rewritten. Two **stale figures** carried in earlier prose are corrected below **as to current scope only**, with the originals preserved and cited (§2).

> **This entry performs 0 Spark executions, trains nothing, executes no TEST, creates no run directory, and modifies no manifest, no result artifact and no prior decision entry.**
> **EXP-008 execution authorization = NO. A5 = DISABLED. SC6 cap = 500, NOT raised. `docs/PLAN.md` = UNCHANGED.**

---

**0 — Identifier resolution.** Next free identifier after DEC-040 is **DEC-041**.

**1 — The gap this entry closes.** DEC-018 Decision B (`DECISIONS.md:1014-1020`) opened TEST *"solely and strictly"* for EXP-005 and ruled: *"TEST remains sealed for every other purpose, **including EXP-005b and EXP-006, each of which requires its own decision**."* EXP-006 duly received DEC-022. **EXP-005b never received its equivalent**, and `DECISIONS.md:1394` states it in terms: **`EXP-005b EXECUTION = NOT YET AUTHORIZED`**. PLAN line 284 schedules EXP-005b for Day 38 — today — so the omission is now load-bearing.

**2 — Two stale figures corrected as to CURRENT scope (originals preserved, not edited).**

**(a) The arm set is B0' ALONE, not two arms.** DEC-016's cost passage (`DECISIONS.md:710-713`) reads *"Two additional arms over EXP-005's planned seven: 7 instances x 2 x 5 repetitions = **+70 runs**"*. That was written while **B3** was still expected to execute. **DEC-017 then made B3 ANALYTIC**, and its Status (`DECISIONS.md:967`) records the resolved position verbatim: *"EXP-005 is seven arms; **B3 analytic, B0' in EXP-005b**"*. Only B0' remains. DEC-016's sentence is **historically correct for its date and is not edited**; it is superseded as to scope by DEC-017, exactly as the DEC-032 §3 cited-versus-re-derived discriminator prescribes.

**(b) The ledger is EXP-005b's OWN, not EXP-005's register line.** DEC-016 wrote *"charged to EXP-005's own register line (PLAN line 312, ~245)"*. DEC-020 later fixed the resolved position twice: `DECISIONS.md:1220` — *"EXP-005b execution (still sealed, separate decision, **separate AQE-on ledger**…)"* — and `:1399` — *"**H — EXP-005b unchanged.** Separate AQE-on experiment, **separate ledger**…"*. EXP-005b therefore has its own AQE-on ledger.

**Resolved scope: 7 frozen TEST instances × 1 arm (B0') × 5 repetitions = 35 runs.**

**3 — Register line and SC6 effect.** B0' executes on the **TEST** split. Under DEC-034 §3 the exemption turns on the split, and SC6 caps **TRAINING**; DEC-031 §5 records *"EXP-005 TEST = 0 charge. EXP-006 TEST = 0 charge."* **EXP-005b charges SC6 exactly 0.** The SC6 ledger stays **483 / 500, remaining 17, untouched**. The 35 runs are recorded on EXP-005b's own AQE-on ledger (§2b), which this entry establishes as beginning at **0 / 35**.

**4 — The no-pooling rule is the scientific heart of this entry, and it is binding.** `docs/architecture/ARCHITECTURE_FREEZE.md:69` is frozen and states: *"Main study: OFF (PLAN section 7). EXP-005b: ON … Every manifest records `aqe_mode`; **analysis never pools across modes**."* DEC-017 Decision 2 (`DECISIONS.md:893-900`) applies it: *"Pooling an AQE-on arm into a Wilcoxon / Cliff / Holm comparison against AQE-off arms is prohibited by that frozen rule."*

**Independently of the rule, DEC-017 records a FAIRNESS DEFECT:** *"B0' **ADAPTS AT RUNTIME** while every other arm is static."* AQE re-plans during execution; B0, B1, B2, B4 and the frozen RL policies do not. A head-to-head "RL vs B0'" improvement number would therefore compare a runtime-adaptive system against non-adaptive ones and attribute the difference to the wrong cause.

**What is admissible:** a **descriptive, within-mode** report of B0' against the AQE-on reference point, and a **stated-limitation** discussion of AQE complementarity. **What is INADMISSIBLE and is forbidden by this entry:** any pooled statistic across `aqe_mode`; any Wilcoxon, Cliff's δ or Holm-corrected comparison spanning AQE-on and AQE-off arms; any headline claim of the form "RL beats B0'" or "B0' beats RL"; and any substitution of B0' for B0 in the EXP-005 main comparison. **An EXP-005b that produced a pooled number would produce a number nobody may legitimately use, which is worse than not running it.**

**5 — Implementation readiness: NO DRIVER EXISTS.** `scripts/run_exp005.py:54` declares `ARMS = ("B0", "B1", "B2", "B4", "RL-s0", "RL-s1", "RL-s2")` — **seven arms, no B0'** — and its own header at `:19` states the reason: *"B3 is analytical only; **B0' belongs to EXP-005b**"*. The exclusion is deliberate, and the DEC-018B content contract that three validators enforce is written against that seven-arm set. **There is today no code path that executes a B0' TEST arm.**

`configs/baseline_b0_prime.yaml` **does** exist and freezes the configuration mechanically — its header records that it is `configs/baseline_b0.yaml` *"with exactly ONE value changed: `aqe_enabled` false -> true"*, introducing no tuning value. The **configuration** is ready; the **driver** is not.

**6 — THEREFORE THE EXECUTION AUTHORIZATION IS CONDITIONAL, AND IS NOT GRANTED BY THIS ENTRY.** Authorizing the execution of code that has not been written is precisely the defect DEC-030 §15's gate chain exists to prevent. Following that chain's shape, **EXP-005b execution may be authorized by a separate later decision once, and only once, ALL of the following hold:**

1. an EXP-005b driver exists that executes **B0' only** over the **7 frozen TEST instances** at **5 repetitions**, opening **no new TEST cell**;
2. it carries a content contract in the DEC-018B shape, so that filename alone never authorizes, and it refuses to run without an explicit Spark gate;
3. it writes `aqe_mode` into **every** manifest and refuses to emit any pooled statistic (§4);
4. its zero-Spark tests are green and the full validator chain still passes;
5. that later decision records worst-case counts (**35**), the ledger charge (**0** to SC6; 35 to EXP-005b's own ledger) and a clean preflight.

Until then: **`EXP-005b EXECUTION = NOT AUTHORIZED`** and **TEST remains SEALED**, exactly as DEC-018 Decision B left it.

**7 — TEST-seal discipline for the eventual execution.** The opened cells are the **same 7 frozen EXP-005 TEST instances** whose identity is pinned by `results/evaluation/exp005_instances.json` and `test_freeze.json`. **No new TEST cell is unsealed by EXP-005b, ever.** TEST re-seals on completion. No TEST metric may influence training or tuning (`docs/PLAN.md` line 163).

**8 — Exhaustively NOT permitted by this entry.** No execution of any kind. No TEST cell is opened now. No new TEST instance is ever added. No B0' substitution into EXP-005's pooled comparison. No pooled cross-mode statistic. No retraining, no Q update, no policy write. No amendment of `docs/PLAN.md`, SC6, `configs/baseline_b0.yaml` or `configs/baseline_b0_prime.yaml`. No edit to DEC-016's or DEC-017's recorded text. No EXP-008 execution.

**9 — What this entry does NOT decide.** Whether the EXP-005b driver should extend `run_exp005.py` or be a separate script (an implementation decision). Whether B3's analytic treatment should be revisited. Whether EXP-005b's 35 runs should appear in `docs/PLAN.md`'s register (PLAN is unchanged). Any EXP-009 matter — DEC-040 covers it. Whether AQE complementarity warrants a thesis chapter section of its own.

**Status.** **DECIDED.** EXP-005b scope is frozen at **B0' alone, 7 instances × 5 repetitions = 35 runs**, on a **separate AQE-on ledger**, **0 charged to SC6**. The **no-pooling rule and the runtime-adaptivity fairness defect are binding on any analysis**. **`EXP-005b EXECUTION = NOT AUTHORIZED`** — the authorization is **CONDITIONAL** on §6's five conditions, chief among them a driver that does not exist (`scripts/run_exp005.py:54` excludes B0' deliberately). `TEST = SEALED`. `SC6 cap = 500, NOT raised`. `SC6 ledger = 483 / 17, unchanged`. `EXP-008 execution authorization = NO`. `A5 = DISABLED`. `docs/PLAN.md = UNCHANGED`. Historical decisions (DEC-001 … DEC-026, DEC-030 … DEC-040) = **UNCHANGED**. Supervisor counter-signature: **PENDING** (conventional expectation only; never simulated; not a prerequisite under DEC-018 Decision A). **NO SUPERVISOR HAS REVIEWED THIS ENTRY.** A future review is a new entry; this one is never rewritten. **This entry performs 0 Spark executions and trains nothing.**

---

*Standalone companion artifact. The authoritative log entry is the appended DEC-041 section of DECISIONS.md; this document carries the same decision content, self-contained (the DEC-031/DEC-032 convention).*
