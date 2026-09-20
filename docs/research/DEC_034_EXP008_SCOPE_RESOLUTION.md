# DEC-034 | 2026-09-20 | EXP-008 A3/A4 scope resolution — zero-charge derived ablation; SC6 cap NOT amended; register-line exemption held inapplicable to TRAIN-only work (Day 37/38)

**Decision ID:** DEC-034
**Date:** 2026-09-20
**Scope:** The EXP-008 scope/envelope question only — what shape EXP-008 A3/A4 may take given the SC6 headroom recorded by DEC-033. Nothing else.
**Status:** DECIDED — **EXP-008 execution authorization remains NO.**
**Standalone decision artifact.** The authoritative log entry is this appended DEC-034 section of `DECISIONS.md`; a companion document `docs/research/DEC_034_EXP008_SCOPE_RESOLUTION.md` carries the same decision content, self-contained, following the DEC-031/DEC-032 convention.
**Supersedes nothing.** DEC-010, DEC-011, DEC-012, DEC-017, DEC-018, DEC-020, DEC-026, DEC-030, DEC-031, DEC-032 and DEC-033 are unchanged; no historical decision entry is rewritten.

> **This entry performs 0 Spark executions, trains nothing, executes no TEST, creates no run directory, modifies no result artifact, no manifest, no budget, no ledger, no implementation file and no configuration.**
> **EXP-008 execution authorization = NO. A5 = DISABLED. TEST = NOT AUTHORIZED. `docs/PLAN.md` = UNCHANGED.**

---

**0 — Identifier resolution.** `DECISIONS.md` headings run DEC-001…DEC-026, DEC-031, DEC-032. DEC-030 is formally recorded outside `DECISIONS.md` (`docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md`, sha256 `ec487bf2a84a9c1a6f506bdd83c71b7c7bb7ae2cceaf7e761f000c7201912a5a`). DEC-033 is likewise recorded outside `DECISIONS.md` (`docs/research/DEC_033_GOVERNANCE_RECONCILIATION.md`, sha256 `3e6d0d7c4b5359990ea6ac6766e226d860c5fea2fb0e8639cc73fff645932b21`, committed `c2e980a`); `grep -c "DEC-033" DECISIONS.md` returns **0**. That out-of-ledger recording is the DEC-030 pattern DEC-031 §0 accepted and is **recorded here, not corrected** — DEC-033's identity is preserved unchanged and this entry does not renumber, fold or edit it. The next sequential identifier is therefore **DEC-034**.

**1 — Scope.** (a) whether the register-line exemption reaches EXP-008 A3/A4; (b) what EXP-008 scope is admissible under the SC6 headroom recorded by DEC-033; (c) the charged live TRAIN execution requirement of that scope. Nothing else is in scope. This entry is **not** the B6 implementation decision and **not** an authorization decision.

**2 — Ledger restated, not re-derived.** SC6 cap **500**, unchanged and **not raised** (`docs/PLAN.md` line 45; `configs/rl.yaml` line 17). Cumulative charge **468**; remaining **32**; `232 + 84 + 20 + 126 + 6 = 468`; `500 − 468 = 32` (DEC-033, Option A selected by the operator). This entry **adds no new accounting and changes no figure**.

**3 — The register-line exemption does NOT reach EXP-008 A3/A4. The discriminator is the SPLIT, not the register line.** DEC-031 §10 left this open; DEC-011 held the pot question unarbitrable. Both stand. What this entry establishes is narrower and is fully supported by the existing record: *what made EXP-003, EXP-005, EXP-005b and EXP-006 exempt was never the existence of a register line.* Every exemption in the ledger is stated as an exemption from the **TRAIN** cap for **non-TRAIN** work:

| Exempt line | Split | The sentence that exempts it |
|---|---|---|
| EXP-003 | validation | DEC-012: *"EXP-003 is a separate register line and is NOT charged to SC6's ≤500 **TRAINING** cap (PLAN line 45)"* |
| EXP-005 | TEST | DEC-018 Decision B: *"245 TEST executions, charged to EXP-005's own register line and **outside** the SC6 **TRAIN** cap"* |
| EXP-005b | TEST | DEC-017: *"+70 runs, charged to EXP-005's own register line (PLAN line 312, ~245), NOT to SC6's 500-execution **training** cap"* |
| EXP-006 | TEST | DEC-031 §5: *"EXP-006 TEST — 125/125 **TEST** observations, charged **0**"* |

Against which DEC-031 §5 charged-category 1 reads: *"**TRAIN live executions** — every real environment transition consumed by a training run's budget counter … charged to the training register lines."*

**The decisive counter-example is EXP-007.** `docs/PLAN.md` line 314 registers it on its own line with the **identical** `~300` envelope and the **identical** `ablation table` acceptance column as EXP-008 at line 315. It was charged **126 to SC6** anyway — DEC-031 §6: *"EXP-007 = 126 charge (35+35+35+21 live, **TRAIN-split**, 0 failures, 0 smoke, 14 unexecuted planned rows charging nothing)"*, authorized against SC6 by DEC-026 §10: *"maximum 140 live Spark executions charged to SC6 (remaining 164, headroom 24)."* EXP-008 A3/A4 possesses no property EXP-007 lacked.

**EXP-008 A3/A4 is TRAIN-only, enforced in code.** `src/sparkrl/training/exp008.py` lines 207–214:

```
def guard_split(split: str) -> None:
    """EXP-008 A3/A4 is TRAIN-only: TEST and VALIDATION never enter."""
    if split != TRAIN:
        raise Exp008ScopeError(...)
```

**Recorded finding.** Any charged live TRAIN execution performed under EXP-008 A3/A4 falls inside SC6's subject ("training ≤500", PLAN line 45) and is charged. Routing it to PLAN line 315 instead would require writing a new exclusion reason into DEC-031 §5's exhaustively stated NOT-CHARGED list — the move DEC-032 §6's anti-pattern clause forbids and which DEC-033 §12 already refused on identical grounds. **That route is closed.**

**4 — The PLAN-internal conflict is MOOTED for EXP-008, not arbitrated.** DEC-011 recorded that whether EXP-008's envelope is charged to SC6's ≤500 or to its own ~300 line is *"internal to PLAN; DEC-010's precedence rule cannot arbitrate it."* **This entry does not arbitrate it and claims no authority to.** It does not need to: §5 fixes EXP-008 A3/A4's charged requirement at **0**, and a zero-charge experiment charges the same amount — nothing — under either reading of PLAN. The conflict is therefore **inert for EXP-008 and remains OPEN** for any future experiment that would charge live TRAIN executions. No arbitration is enacted, implied or available to be cited from this entry.

**5 — Decision: EXP-008 A3/A4 is scoped as a ZERO-CHARGE DERIVED ABLATION. Charged live TRAIN executions = 0.**

* **A3 (reward variants)** is produced by recomputation over the already-recorded EXP-002 TRAIN observation store, using the machinery the repository already runs for exactly this purpose: `src/sparkrl/agent/q0.py` builds the offline Q-function from *"the EXP-002 stored run records (`results/experiments/exp-002`), and only TRAIN cells"*, valuing each observation by *"the per-observation FROZEN R3 reward (`sparkrl.rl.reward`), using T_ref from the EXP-002 gate artifact (B0 median, seed 0)"*. The registered A3 comparator — `A3-time-only`, `R = 1.0 · clip((T_ref − T)/T_ref, −1, +1)`, failure `R = −1.0` (DEC-030 §3.2; `src/sparkrl/training/exp008.py` header) — is a function of the same stored fields. Recomputing it consumes **no live Spark execution**.
* **A4 (action-space granularity)** is produced as a structural restriction. `mode4 = {0, 3, 6, 9}` is a strict subset of the frozen 12-action grid (DEC-030 §4.3; `src/sparkrl/rl/action.py` `MODE4_SUBSET`), so a mode4 greedy policy is derivable from any mode12 Q-table by argmax over the subset. No execution is required to derive it.
* **A3-R4-log-ratio is NOT retained under this scope.** It remains INCOMPLETE in the eight respects DEC-030 §3.4 enumerates and is refused before any computation by `IncompleteFormulaError`. Whether R4 is ever retained is DEC-030 §12 field 1 and is **not decided here**.
* **Charged requirement: 0.** This satisfies DEC-031 §11 by the **scope-reduction** route — *"an explicit scope reduction to ≤ [32] charged live TRAIN executions, enacted by its own decision"* — and requires **no cap amendment**. `cap_amendment_required` = **false**.

**6 — Cache hits are not the basis of this decision.** DEC-031 §5 non-charged category 2 (*"Cache hits — a replayed/cached transition consumes no live Spark execution"*) is **not** invoked here and is **not** extended. §5's zero charge rests on the fact that **nothing is executed at all** — no environment step, cached or live, is taken. No policy about cache accounting is created, relaxed or implied.

**7 — What this costs scientifically. Stated plainly, not minimised.**

**This decision does not execute EXP-008 as `docs/PLAN.md` line 315 registered it. It substitutes a derived ablation for a trained one, and it weakens a scientific claim.** A3 under this scope is an ablation of the **offline initialization**, not of **online learning**. RQ4 asks *"How do reward-function variants and action-space granularity affect **learning stability** and final policy quality?"* — the **learning-stability half of RQ4 is UNANSWERED and is left unanswered by this decision.**

Following DEC-011's template verbatim in form: the write-up **must state that A3/A4 were not executed as trained arms and why, making no claim about what they would have shown**, and the learning-dynamics dimension of RQ4 is left unexamined **by decision, and that limitation must be stated as such in the report — it is not a measured result.** No inferential claim, no threshold and no statistic is created by this entry (DEC-030 §8 stands: any EXP-008 analysis *"remains descriptive-only with no thresholds invented"*).

**8 — What survives, and one result available at zero cost.** PLAN line 315's stated acceptance is *"ablation table"*, and a derived ablation table discharges that column. Beyond it, the following is derivable today from signed evidence, with **0** executions, and is recorded as available — **not asserted as a finding, which requires the analysis the B6 and authorization decisions still gate**:

Under the frozen grid mapping `grid_index = parallelism_index × 4 + shuffle_index` (`src/sparkrl/experiments/grid.py` lines 177–188; DEC-030 §4.3), `G-p8-sp16` = index **8** and `G-p8-sp64` = index **10**, and **neither is in `mode4 = {0, 3, 6, 9}`**. Index 8 is byte-identical to the frozen B1 (DEC-016/DEC-017: *"parallelism 8 this is `G-p8-sp16`, byte-identical to the frozen B1"*), is B2 for F1/F2, and is the configuration DEC-020 §A records the statics as having converged on. Index 10 is B2 for F3 (DEC-020 §C). **Two of the three frozen B2 definitions, and B1 itself, are unreachable under the reduced action space.** That is a structural statement about action-space granularity, derived from already-signed artifacts.

**9 — Alternative considered and NOT adopted, recorded so the choice is on the record.** The other route DEC-031 §11 admits is an **explicit cap/PLAN amendment**: raising SC6's cap at `docs/PLAN.md` line 45 under the PLAN header's change-control rule (*"Any change requires a new `DEC-xxx` entry in `DECISIONS.md` and explicit user/supervisor approval"*), and executing EXP-008 at EXP-007 parity (70 charged executions per arm; 3 shared-control arms = 210, 4 arms = 280). **It is the only route that answers RQ4 as registered, and it is defensible.** It is not adopted because **it amends a SUCCESS CRITERION that is currently SATISFIED** (468 ≤ 500) — SC6 would then pass only because the bar moved — and because it erodes the claim `docs/PLAN.md` line 35 identifies as the project's research gap (*"sample-efficient online adaptation (tabular/bandit RL) for Spark config selection"*), line 27 (*"within ≤500 cached executions"*) and line 101 (Candidate C at *"~600–900 total, cache-bounded"* against *"B: Pure online RL — 1000s (infeasible)"*). It would additionally change a load-validated frozen research constant (`configs/rl.yaml` line 17, under the file's own rule that *"these are research constants, NOT tuning parameters. Any disagreement is a hard error"*) and every validator and test pinning 500. **No DEC has ever amended `docs/PLAN.md`**; DEC-031 §15 and DEC-032 §11 both record its sha256 `db5e8210…ee63` as unchanged, re-verified current at this entry's recording. **This entry forecloses nothing: §5's zero-charge scope leaves the amendment route fully open, and a later decision may take it.** Choosing it is the operator's call.

**10 — Also considered, and FORECLOSED by arithmetic and by signed decisions.**

* **Re-scope to fit 32 by consuming R8 scope-ladder rung 3** (`docs/PLAN.md` line 361, *"shrink ablations to A1+A3"*; rungs 2–4 recorded as available by DEC-011). The mechanism is real and rung 3 is genuinely unconsumed. The arithmetic is not favourable: 2 arms × 1 seed × 2 epochs = **28**, or 2 arms × 2 seeds × 1 epoch = **28**, both ≤ 32, but at one epoch each of the 7 T_ref-calibrated TRAIN cells is visited once — **7 of 7 × 12 = 84 (cell, action) pairs, 8.3% coverage**; epsilon under the frozen schedule (1.0 → 0.05, decay 0.95/episode) stands at **0.698** after 7 episodes and **0.488** after 14, against **0.166** for EXP-007's arms and **0.050 / 0.081 / 0.116** for the three main-study policies; the frozen early-stop rule (2 consecutive stable epochs) cannot meaningfully fire; and DEC-011's measured reference is that **175 executions covered only 68.3% of the 5-state footprint**. At one seed there is no cross-seed variance estimate; at two seeds it is n = 1 per cell against the measured noise band (median CV **0.045485**, worst cell **0.118864**, DEC-018 Decision F — the 11.89% band DEC-020 §A used to bound every EXP-005 finding). DEC-020 §A closed **245** TEST executions as descriptive-only with SC2/SC3/SC4 **UNDECIDED**; 28 cannot do better. **It would spend the entire remaining SC6 headroom for a result no stronger than §5's, and leave 4 executions forever.** Rung 3 is therefore **NOT consumed by this entry and remains available under R8.**
* **Charging EXP-008 to its own PLAN line 315 envelope** — **foreclosed by §3.**
* **Not executing EXP-008 at all and recording RQ4 unanswered** (the DEC-011/A5 shape) — viable and honest, but strictly dominated: it costs the same 0 executions as §5 while producing neither the register's ablation-table deliverable nor §8's derivable result.

**11 — What this decision deliberately does NOT decide.** The **B6 implementation decision** (DEC-030 §15 gate item 3); the **authorization decision** (gate item 4); the **final arm set** (DEC-030 §12 field 1), including whether A3-R4 is ever retained; the **Q0 source per arm** (field 2); the **state schema** (field 3); the **A3 action schema** (field 4); the **A4 control-pairing reward** (field 5); whether A3 and A4 share a basis (field 13); the **statistical governance** of EXP-008 (field 14; DEC-030 §8 stands unchanged); the **R4 complete specification** (field 15); the **amendment mechanism** for the PLAN tension of DEC-031 §10; the classification of the 2026-09-16 and 2026-09-19 **zero-live manifests** (DEC-032 §7.3, still UNRESOLVED); and **`scripts/validate_day30.py` / `validate_day31.py`** maintenance. DEC-030 §12 fields **6–12 and 16** (seeds, TRAIN cells, episode horizon, early-stop rule, AQE confirmation, warm-up, cache behaviour, hyperparameter deviations) are **INAPPLICABLE BY CONSTRUCTION** under §5's zero-execution scope — they are **not** silently resolved, and they **revive in full** if any later decision restores a trained scope. Field **17 (B5 charging rule)** is resolved by §3 and §5 for EXP-008 only.

**12 — Non-authorization firewall (explicit).**

| Item | State recorded by this entry |
|---|---|
| **EXP-008 execution authorization** | **FALSE / NO** |
| **Implementation authorization (A3/A4, B6)** | **FALSE / NO** |
| **EXP-008 charged live TRAIN executions** | **0** |
| **SC6 cap** | **500 — UNCHANGED, NOT RAISED** |
| **SC6 ledger** | **468 charged / 32 remaining — UNCHANGED** |
| **A5** | **DISABLED** (DEC-011; re-affirmed DEC-030 §9, DEC-031 §14); `configs/rl.yaml` `gamma` stays 0.0 |
| **TEST** | **NOT AUTHORIZED** — nothing here opens TEST for anything |
| **R8 scope-ladder rungs 2–4** | **UNCONSUMED — all remain available** |
| **`docs/PLAN.md`** | **UNCHANGED — no line edited** |
| **`configs/rl.yaml`** | **UNCHANGED** |
| **Historical decisions** | **UNCHANGED** — DEC-001 … DEC-026, DEC-030 … DEC-033 are not rewritten; this entry is appended, never substituted |
| **Spark / training / TEST executions performed by this entry** | **0 / 0 / 0** |

**13 — Evidence and fingerprints (read-only; nothing listed here was modified).**

| Source | Role | SHA256 |
|---|---|---|
| `docs/PLAN.md` | SC6 line 45; EXP-007 line 314; EXP-008 line 315; R8 scope tier line 361; header change-control lines 3–7 | `db5e82102833efe6bab8db1adaf1b35ad195faf385e63ab296d50562e349ee63` (**unchanged**; identical to the value DEC-031 §15 and DEC-032 §11 record) |
| `configs/rl.yaml` | `live_execution_cap: 500` (line 17); epsilon schedule (lines 9–11); `early_stop_stable_epochs: 2` | `8ca70d6dd7df68841c409a4441dc538616206bccea7877b28c73df20e6428b80` (**unchanged**) |
| `src/sparkrl/training/exp008.py` | `guard_split` TRAIN-only enforcement (lines 207–214); frozen A3/A4 arm layer | `0a2252b378dda0a630106795ef13287eda86d3a50c0e294ef26f3768bc54ceba` (**unchanged**) |
| `docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md` | DEC-030 identity preserved; §12 fields; §15 gate chain | `ec487bf2a84a9c1a6f506bdd83c71b7c7bb7ae2cceaf7e761f000c7201912a5a` (**unchanged**) |
| `docs/research/DEC_033_GOVERNANCE_RECONCILIATION.md` | canonical 468/32 ledger | `3e6d0d7c4b5359990ea6ac6766e226d860c5fea2fb0e8639cc73fff645932b21` (**unchanged**; committed `c2e980a`) |
| `src/sparkrl/agent/q0.py`, `src/sparkrl/experiments/grid.py`, `src/sparkrl/rl/action.py`, `src/sparkrl/training/ablation.py` | cited for §5 and §8 mechanics | **NOT MODIFIED** |
| `results/training/**/manifest.json` | 22 manifests | **NOT MODIFIED** |

**14 — Validation of this entry (read-only, zero Spark).**

| Check | Result |
|---|---|
| DEC-034 is the next free identifier (`grep` for DEC-033/DEC-034 headings in `DECISIONS.md`) | PASS |
| `DECISIONS.md` appended only; every prior byte intact | PASS |
| DEC-030 / DEC-031 / DEC-032 / DEC-033 artifacts unchanged (SHA256 re-checked) | PASS |
| `docs/PLAN.md`, `configs/rl.yaml` unchanged (SHA256 re-checked) | PASS |
| SC6 cap = 500; charge = 468; remaining = 32; `232+84+20+126+6 = 468` | PASS |
| EXP-008 charged requirement under §5 = 0 ≤ 32; DEC-031 §11 satisfied by scope reduction | PASS |
| No cap amendment enacted | PASS |
| No R8 scope-ladder rung consumed | PASS |
| TRAIN-only enforcement quoted verbatim from `exp008.py:207–214` | PASS |
| No execution, implementation or TEST authorized | PASS |
| A5 remains DISABLED | PASS |
| Spark / training / TEST executions performed | **0 / 0 / 0** |

**Status.** **DECIDED.** The register-line exemption is recorded as turning on the **SPLIT**, not on the existence of a register line, and is therefore **inapplicable** to TRAIN-only EXP-008 A3/A4 — with EXP-007 (own ~300 register line, charged 126 to SC6) as the controlling counter-example. EXP-008 A3/A4 is scoped as a **ZERO-CHARGE DERIVED ABLATION**: charged live TRAIN executions = **0**, satisfying DEC-031 §11 by scope reduction with **no cap amendment**. The DEC-011 PLAN-internal pot conflict is **MOOTED for EXP-008, not arbitrated, and remains OPEN**. The **learning-stability half of RQ4 is UNANSWERED by decision** and must be reported as a stated limitation with no claim about what it would have shown. The cap-amendment alternative (§9) is recorded, **not foreclosed**. `SC6 cap = 500, NOT RAISED`. `Ledger = 468 / 32, unchanged`. `EXP-008 execution authorization = NO`. `A3/A4 implementation = NOT AUTHORIZED`. `A5 = DISABLED`. `TEST = NOT AUTHORIZED`. `PLAN.md = UNCHANGED`. Historical decisions DEC-001 … DEC-026, DEC-030 … DEC-033 = **UNCHANGED**. Supervisor counter-signature: **PENDING** (conventional expectation only; never simulated; not a prerequisite under DEC-018 Decision A). **NO SUPERVISOR HAS REVIEWED THIS ENTRY.** A future review is a new entry; this one is never rewritten. **This entry performs 0 Spark executions and trains nothing.**

*End of DEC-034.*

---

*Standalone companion artifact. The authoritative log entry is the appended DEC-034 section of DECISIONS.md; this document carries the same decision content, self-contained (the DEC-031/DEC-032 convention).*

**Ledger supersession note (appended 2026-09-20, before signature).** This entry was drafted against the then-current ledger **468 / 32** (DEC-033). Five completed smoke TRAIN executions dated 2026-09-20 07:37-07:56Z were discovered afterwards and classified by **DEC-038**, making the canonical ledger **483 / 17** at signature. The figure is corrected here rather than in the body, so the drafting chronology stays visible. No conclusion in this entry depends on the difference: the scope resolved here has a charged requirement of **0**, which satisfies any headroom. The change strengthens it - the 28-execution single-epoch alternative rejected in the body no longer fits at all (28 > 17), so that option is now foreclosed by arithmetic as well as by design.
