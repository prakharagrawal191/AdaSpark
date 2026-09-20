# DEC-036 | 2026-09-20 | EXP-008 A3/A4 methodological field resolution - all eighteen DEC-030 s12 fields; A3-R4 DROPPED as unspecifiable; execution authorization remains NO (Day 38, C3)

**Decision ID:** DEC-036
**Date:** 2026-09-20
**Scope:** The eighteen methodological fields that `docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md` §12 marks *"UNFROZEN — SEPARATE DECISION REQUIRED"*. **Nothing else.**
**Status:** DECIDED — sixteen fields resolved unconditionally; the two count-driving fields (6 seeds, 8 horizon) resolved as a frozen RULE plus three fully specified branches, one of which a separate decision selects. **`EXP-008 execution authorization = NO`.**
**Standalone decision artifact.** The authoritative log entry is the appended DEC-036 section of `DECISIONS.md`; this document carries the same decision content, self-contained, so the decision also exists as an addressable artifact (the DEC-031/DEC-032 convention).
**Supersedes nothing.** DEC-030, DEC-031, DEC-032 and DEC-033 are unchanged; no historical decision entry is rewritten. `docs/PLAN.md` is **UNCHANGED**.

> **This entry performs 0 Spark executions, trains nothing, executes no TEST, creates no run directory, and modifies no manifest, no result artifact, no configuration, no implementation file and no prior decision entry.**
> **EXP-008 execution authorization remains NO. A5 remains DISABLED. TEST remains NOT AUTHORIZED.**

---

## 0 — Identifier resolution and batch context

`DECISIONS.md` headings run DEC-001…DEC-026, DEC-031, DEC-032. DEC-030 is formally recorded outside `DECISIONS.md` (`docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md`, `Decision ID: DEC-030`). **DEC-033 is likewise recorded as a standalone artifact only** (`docs/research/DEC_033_GOVERNANCE_RECONCILIATION.md`, *"STATUS: DECIDED — Option A selected by the operator"*) and has **no section in `DECISIONS.md`** — recorded here as an observation, **not corrected by this entry**. DEC-034 and DEC-035 are the identifiers assigned to the sibling budget and B6 entries of the same Day-38 governance batch; **DEC-036 claims neither of them, cites neither as signed, and takes no effect on either.**

## 1 — Scope

DEC-030 §15: *"Any methodological field marked 'UNFROZEN — SEPARATE DECISION REQUIRED' must be resolved by such a DEC before authorization."* This entry is that DEC for all eighteen §12 fields. It resolves methodology only. It is **not** the B6 implementation decision, **not** a budget decision and **not** an authorization decision.

## 2 — Method, and the rule this entry obeys

Each field is placed in exactly one class:

* **INHERIT** — the project already holds a frozen value that applies unchanged. The frozen value and its authority (file:line, decision id) are given. **Inheriting is not inventing**; a field is only inherited where the value demonstrably already exists.
* **CHOOSE** — a real choice with no frozen default. Options and reasoning are given.
* **ALREADY RESOLVED** — by DEC-031/DEC-033 (field 17) or by the separate B6 decision (field 18).
* **DROP** — the element cannot be specified without invention, so it is removed from the executable set rather than guessed.

**No threshold, statistic, formula, weight or policy absent from the record is created by this entry.** Where a field could only be settled by invention, it is dropped and the cost is stated. CITED historical figures are not edited anywhere (the DEC-032 §3 discriminator); every figure below is either restated from a signed decision or re-derived from the live tree and labelled as such.

## 3 — Canonical figures restated (not re-derived, not changed)

| Quantity | Value | Authority |
|---|---|---|
| SC6 cap | **500**, **not raised** | `docs/PLAN.md` line 45; `configs/rl.yaml` line 17 |
| Cumulative charge | **468** | DEC-033 Option A: `232 + 84 + 20 + 126 + 6 = 468` |
| Remaining headroom | **32** | `500 − 468` (DEC-033) |
| PLAN EXP-008 envelope | **~300** | `docs/PLAN.md` line 315 — an internal-PLAN tension DEC-011 and DEC-031 §10 record and do **not** resolve |

**This entry adds no accounting and changes no figure.**

## 4 — The unit of account (evidence, not assumption)

Every execution count below rests on three facts already in the repository:

1. **One episode = one charged live execution.** `docs/architecture/ARCHITECTURE_FREEZE.md`: *"Episode: one cached-or-live execution + update"*; `src/sparkrl/rl/env.py:284` increments the counter once per step; `:300` *"bandit mode: episode terminates"*. EXP-007's four manifests read `35 / 35 / 35 / 21` live against 35 planned episodes per seed.
2. **One epoch = one full pass over the planned cells.** `configs/rl.yaml:27` `epoch_definition: "one_full_pass_over_the_planned_cell_cycle"`; `src/sparkrl/training/loop.py:232-233`, `episodes_per_epoch` is DERIVED `== len(cells)`.
3. **No cache exists.** `src/sparkrl/rl/env.py:29-30`: *"the cache itself is COMP-EXP-11 (deferred, Day 26+), so every … step is a live execution and `info[\"cached\"]` is always False."* The frozen *"cache hits free"* rule therefore has no live content and reduces no count.

Therefore **charged live TRAIN executions = arms × seeds × epochs × cells**, with `cells = 7` (§6, field 7).

## 5 — Resolution of all eighteen fields

| # | Field (DEC-030 §12) | Class | Resolution | Authority |
|---|---|---|---|---|
| 1 | Final arm set; whether A3-R4 is retained | **CHOOSE** | **Three executable arms: `A3-R3-frozen`, `A3-time-only`, `A4-mode4`. `A3-R4-log-ratio` is DROPPED from the executable arm set** and retained as REGISTERED-BUT-UNEXECUTABLE | §8 |
| 2 | Q0 source per arm | **CHOOSE** | **`q0-exp002/v1` for all three arms**, uniformly; A4 uses 12-wide rows with selection restricted to {0,3,6,9}, no projection | §7.2 |
| 3 | State schema per arm | **INHERIT** | **`state-v1.5`** (30 states) for all arms | `src/sparkrl/rl/state.py:73` `STATE_VERSION = "state-v1.5"`; every Day-29 manifest `contract_versions.state_schema = state-v1.5`; DEC-030 §6.1 primary row |
| 4 | Action schema for A3 | **INHERIT** | **`mode12`** (all 12 frozen actions) for both A3 arms | `src/sparkrl/rl/action.py:30`; `docs/architecture/ARCHITECTURE_FREEZE.md` COMP-RL-07; DEC-030 §4.1 |
| 5 | Reward arm for A4 control pairing | **CHOOSE** | **R3**, and A4-mode4's control **is** the `A3-R3-frozen` arm (same run set, same seeds, same cells, same horizon) | §7.3 |
| 6 | Seeds (count + identities) | **CHOOSE — conditional** | **Rule frozen:** seeds are an ascending **prefix of the frozen PLAN §16 set {0,1,2}**; no seed outside it, no re-ordering, no invented seed. **Value: branch-selected (§10).** | `configs/rl.yaml:16` `training_seeds: [0, 1, 2]`; DEC-023/DEC-025 used the prefix {0,1} |
| 7 | TRAIN cells | **INHERIT (forced)** | **The seven T_ref-calibrated TRAIN cells at dataset seed 0**: `F1_agg|small`, `F1_agg|medium`, `F2_join|small`, `F2_join|medium`, `F3_rdd|small`, `F5_mixed|small`, `F5_mixed|medium`; `F3_rdd|medium` excluded (`t_ref_null`). **No subset is admissible** (§7.5) | `src/sparkrl/training/loop.py:392-396`; DEC-025 §3; the same seven appear in `results/training/train-a0-d0-20260912T112906Z/episodes.jsonl` |
| 8 | Episode horizon | **CHOOSE — conditional** | **Rule frozen:** the horizon is an **integer number of complete 7-cell epochs**; a non-integer horizon is inadmissible because it truncates the round-robin cycle. **Value: branch-selected (§10).** | DEC-025 §4 (*"40 is rejected because 40 is not an integer number of complete 7-cell epochs"*) |
| 9 | Early-stop rule | **INHERIT** | **`stable_epochs_required = 2`; greedy snapshot identical at 3 consecutive epoch boundaries.** Inert below 3 epochs (§10 note) | `configs/rl.yaml:29`; `src/sparkrl/training/loop.py:60,100`; PLAN §16 |
| 10 | AQE condition | **INHERIT** | **`aqe_enabled = false`** for every arm; AQE-on is EXP-005b and is never pooled with this study | `configs/spark.yaml:14`; `src/sparkrl/rl/action.py:97-99` (post-application guard raises); `ARCHITECTURE_FREEZE` §13 |
| 11 | Warm-up behaviour | **INHERIT** | **`warmup_runs: 2`, `warmup_micro_job: true`, warm-up excluded from the timed region**; unchanged from the frozen runner | `configs/spark.yaml:19-20`; `src/sparkrl/experiments/runner.py:422-429` (a spec disagreeing with the base config is refused); `ARCHITECTURE_FREEZE` COMP-SPARK-04 |
| 12 | Cache behaviour | **INHERIT** | **No execution cache (COMP-EXP-11 deferred).** Every step is a live execution; `cached` is always False; the "cache hits free" rule is retained verbatim and reduces nothing | `src/sparkrl/rl/env.py:29-30,123,284`; DEC-025 §3 |
| 13 | Whether A3 and A4 share seeds/cells/horizon | **CHOOSE** | **YES — A3 and A4 share the seed set, the seven cells, the horizon, the early-stop rule and the R3 control arm.** The shared control is what makes A4's isolation claim exact | §7.3 |
| 14 | Statistical governance | **CHOOSE (forced by norm)** | **DESCRIPTIVE-ONLY. No p-value threshold, no effect-size cutoff, no Holm family, no minimum-n, no superiority threshold, no inferential test.** Any future formal testing requires a separate pre-use methodology amendment | §9; DEC-020 A and F; DEC-026 §13; DEC-030 §8 |
| 15 | R4 complete specification | **DROP** | **Not specifiable without invention → A3-R4 is dropped from the executable arm set** (see field 1). R4 stays REGISTERED in PLAN §24 and refused pre-computation in code | §8 |
| 16 | Epsilon / alpha / gamma | **INHERIT** | **alpha = 0.2; gamma = 0.0; epsilon 1.0 → 0.05, decay 0.95 per episode. NO deviation for any arm.** gamma is additionally locked | `configs/rl.yaml:7-11`; PLAN §16; DEC-011; DEC-030 §9; `src/sparkrl/training/exp008.py` `guard_a5` refuses any gamma ≠ 0.0 |
| 17 | Live-execution charging rule and headroom (B5) | **ALREADY RESOLVED** | By **DEC-031 §5** (charging categories) and **§8** (headroom), re-based by **DEC-033** to **468 charged / 32 remaining** of the unchanged cap 500 | DEC-031; DEC-033 |
| 18 | Implementation authorization (B6) | **ALREADY RESOLVED — by the separate B6 decision, when signed** | **Not resolved as of this entry's date.** The evidence exists (`docs/research/DAY37_EXP008_B6_IMPLEMENTATION_REPORT.md`; `results/evaluation/exp008_b6_implementation.json`) and states of itself *"This report is **not a decision**"*. **DEC-036 grants no implementation authorization** | DEC-030 §15 gate item (3) |

## 6 — The INHERIT fields: proof that each frozen value exists and applies

Each value below is already in force for the main study and for EXP-007; EXP-008 A3/A4 adopt it **unchanged**, so no control differs between the treatment arms and the frozen design except the factor each arm is testing.

* **state-v1.5 / mode12 (fields 3, 4).** Both are the primary-study values (`state.py:73`; `action.py:30`) and are recorded in every Day-28/29 manifest (`contract_versions.state_schema = state-v1.5`, `contract_versions.action_mode = mode12`). Pinning A3 to mode12 is load-bearing: if A3 varied the action space, A3 and A4 would confound each other, contrary to DEC-030 §6.
* **The seven cells (field 7).** `loop.py:392-396` refuses any TRAIN cell without a calibrated T_ref at dataset seed 0 and names `F3_rdd|medium` as the null one; `env.step` would raise `TRefMissing`. The set is therefore forced by calibration, not chosen for convenience.
* **Early-stop (field 9).** `configs/rl.yaml:29` is frozen-validated `== 2` by `loop.py:164-167`; the rule text is `loop.py:100`.
* **AQE off (field 10).** `configs/spark.yaml:14`; `action.py:97-99` raises `"AQE became enabled after action application (PLAN section 7)"` — the control is enforced in code, not merely declared.
* **Warm-up (field 11).** `configs/spark.yaml:19-20`; `runner.py:422-429` refuses to run a design whose declared warm-up policy differs from the executed one. SC6 charges **env-level live executions**, exactly as every one of the 468 already-charged executions was counted; this entry changes no charging rule.
* **Cache (field 12).** `env.py:29-30`. Recorded so that no future reader mistakes the inherited *"cache hits free"* clause for a budget reduction.
* **alpha / gamma / epsilon (field 16).** `configs/rl.yaml:7-11`, matching PLAN §16 verbatim. gamma = 0.0 is the A5 lock and is re-affirmed, not re-decided.

## 7 — The CHOOSE fields

**7.1 — Field 1, the arm set.** Three executable arms: `A3-R3-frozen` (R3, mode12), `A3-time-only` (the DEC-030 §3.2 multi-term removal, mode12), `A4-mode4` (R3, mode4 = {0,3,6,9}). `A3-R4-log-ratio` is dropped (§8). DEC-030 §3.2's mandatory classification is carried forward verbatim: **time-only is a MULTI-TERM REMOVAL from R3, not a one-factor ablation** — the task-imbalance and spill-waste terms are removed simultaneously, so no observed difference is attributable to either term alone. This statement must appear in any analysis of that arm.

**7.2 — Field 2, Q0 source: `q0-exp002/v1` for every arm.**

* It exists at the right shape: `src/sparkrl/agent/q0.py:64-78` builds it with a `state-v1.5` encoder and 12-wide rows; `configs/rl.yaml:13` `q0_source: "exp002"`.
* It is admissible for every retained arm under the already-implemented policy (`src/sparkrl/training/exp008.py` `q0_policy`, `allowed_sources = (q0-exp002/v1, q0-neutral/v1)`).
* For A4 it is DEC-030 §5.4's **"EXISTING FROZEN MAPPING"**: rows stay 12 wide, columns {0,3,6,9} are used as-is, **no projection, no pooling, no construction**.
* **One source across all arms holds Q0 constant**, which removes DEC-030 §6.1 confound 2 (*"differing Q0 sources across arms would confound reward effects with initialization"*) by construction.

Rejected alternatives, with reasons: **`q0-neutral/v1`** — `build_neutral_q0` accepts only `"A1"` or `"A2"` (`q0.py:239-250`), so no neutral table exists for `state-v1.5`; creating one is new implementation work outside the B6 scope, which recorded *"No new Q0 builder may be added (DEC-030 §5); B6 added none."* The EXP-007 neutral-Q0 precedent does **not** transfer: `q0.py:190-196` records that A1/A2 went neutral because the EXP-002 table could not be mapped onto their 15- and 2-state spaces — a dimensional problem that does not arise here. **Per-arm reward-matched Q0** (rebuilding from the same EXP-002 TRAIN records under each arm's own reward) — refused: it is post-hoc Q0 construction (DEC-030 §5.1 rule 2), and it would make Q0 differ across arms, reinstating exactly the confound the uniform choice removes.

> **Limitation, recorded and binding on any future analysis.** `q0-exp002/v1` was derived from EXP-002 TRAIN records scored under the frozen **R3** reward. For `A3-time-only` this is initialization computed under a different reward from the one the arm optimizes — DEC-030 §5.3 calls that *"methodologically defensible IF frozen"*. This entry freezes it and requires the limitation to be disclosed wherever that arm is reported.

**7.3 — Fields 5 and 13, the A4 control and sharing.** A4-mode4's control reward is **R3**, and its control arm **is** `A3-R3-frozen`. A3 and A4 share the seed set, the seven cells, the horizon and the early-stop rule. This makes DEC-030 §6.2's requirement — *"All other factors must equal the control arm"* — exactly true rather than approximately true, and it removes one arm's worth of executions from every branch in §10. DEC-030 §6.2 confound 3 is carried forward unrepaired and **must be reported, not corrected**: ε-greedy over 4 actions versus 12 yields different exploration coverage under the same schedule; that is inherent to the factor.

**7.4 — Field 14.** See §9.

**7.5 — Why no cell subset is admissible.** A smaller cell set would cut every count proportionally, and is refused: no artifact, decision or criterion selects a subset of the seven, so choosing one would be an invented selection rule; and a subset would break comparability with the main study, with EXP-007 and with the R3 control. The cell count stays 7.

## 8 — Field 15: A3-R4 is DROPPED from the executable arm set

**What the record supplies for R4:** the name and the formula, and nothing else — `docs/PLAN.md` §24 (*"R4 log-ratio"*) and `docs/architecture/ARCHITECTURE_FREEZE.md` (*"R4 = −ln(T/T_ref) ablation-only"*).

**What the record does not supply** — the eight semantics enumerated by DEC-030 §3.4 and pinned in code at `src/sparkrl/rl/reward.py:111-120`: `failure_rule`, `coefficients`, `clipping`, `edge_T_le_0`, `edge_T_ref_le_0`, `edge_failures_timeouts`, `edge_missing_execution_time`, `term_structure_vs_time_only`. `configs/reward.yaml` holds R3 weights only. No DEC supplies any of them.

**Why none can be derived.** The failure rule is the clearest case: R3's `−1.0` failure constant is commensurate with a reward clipped to `[−1, +1]`, whereas `−ln(T/T_ref)` is unbounded in both directions. Carrying `−1.0` across is a **scale decision with no authority behind it**, not a derivation. The same applies to clipping (R4 has none), to `T ≤ 0` (undefined), and to whether R4 is a functional-form change of the time term or also a multi-term removal — DEC-030 §3.4 lists that last question as unresolved, and it changes what the arm even measures.

**Decision.** `A3-R4-log-ratio` is **DROPPED from the EXP-008 executable arm set**. It remains **REGISTERED** — `docs/PLAN.md` §24 is **not amended**, the enum stays in `src/sparkrl/rl/reward.py:85`, and the code keeps failing closed before any computation (`reward.py:197-206`, `IncompleteFormulaError`). A later decision may freeze all eight semantics from a real authority and reinstate the arm; this entry does not.

> **This weakens the scientific claim, and the entry says so in those words.** A3 as executed becomes a **two-way** reward comparison (time-only vs frozen R3), not the **three-way** comparison PLAN §24 registers. RQ4's reward-design question is answered for coefficient/term removal only, and **not at all for functional form**. Any A3 report must state that the R4 log-ratio variant was never executed and why. **No success criterion is amended by this**: PLAN line 45 (SC6) and PLAN line 315 stand verbatim, and SC1–SC8 are untouched.

## 9 — Field 14: statistical governance — DESCRIPTIVE-ONLY

**Frozen:** EXP-008 A3/A4 analysis is **descriptive**. Per-arm and per-cell medians and the registered ablation table; coverage and failures reported as first-class; no inferential test and **no threshold of any kind**.

**Explicitly NOT created by this entry:** p-value threshold, alpha, effect-size cutoff, Cliff's δ decision rule, Holm family definition, multiple-testing scope, minimum successful cells, superiority threshold, hypothesis-to-comparison mapping.

**Authority for following this rather than inventing a procedure.** DEC-020 A closed EXP-005 with *"H2, H3, SC2, SC3, SC4 are **UNDECIDED** — not failed. No Wilcoxon, no Cliff's δ decision, no Holm decision, no alpha, no minimum-n, no effect threshold … No generic defaults are retrofitted."* DEC-020 F: *"Any future formal testing needs a separate pre-use methodology amendment."* DEC-026 §13 applied the same rule to the most recent ablation: *"No numerical pass/fail threshold and no inferential statistic is introduced."* DEC-030 §8 records that the Day-37 audit's proposed Wilcoxon/Holm procedure is *"EVIDENCE, not authority; it is not adopted here."* This entry adopts none of it either.

**Consequence, stated plainly.** RQ4 receives a **descriptive** answer, not a tested one. That matches what `docs/PLAN.md` line 315 registers as EXP-008's deliverable (*"ablation table"*), so no registered deliverable is lost; but no claim of statistical significance may ever be attached to EXP-008 A3/A4 under this entry.

## 10 — Fields 6 and 8: the count-driving fields, the arithmetic, and the conditional freeze

**Frozen unconditionally (the rule):** horizon = an integer number of complete 7-cell epochs (DEC-025 §4); seeds = an ascending prefix of the frozen `{0, 1, 2}` (`configs/rl.yaml:16`); the same seeds and horizon for every arm (field 13).

**The arithmetic** (`arms × seeds × epochs × 7`, per §4; worst case = planned, since early stop can only reduce):

| Shape (per arm) | 2 arms | 3 arms | 4 arms | Fits inside 32? |
|---|---|---|---|---|
| 1 seed × 1 epoch = **7** | 14 | **21** | 28 | **yes** (all three) |
| 1 seed × 2 epochs = **14** | **28** | 42 | 56 | only 2 arms |
| 2 seeds × 1 epoch = **14** | **28** | 42 | 56 | only 2 arms |
| 1 seed × 3 epochs = **21** | 42 | 63 | 84 | no |
| 2 seeds × 2 epochs = **28** | 56 | 84 | 112 | no |
| 1 seed × 5 epochs = **35** | 70 | 105 | 140 | no |
| **2 seeds × 5 epochs = 70** (EXP-007 parity, DEC-025 §5) | 140 | **210** | 280 | no |

**Two facts the operator should read off this table.** First, **the complete list of shapes that fit inside the 32 remaining executions is: 14, 21 and 28** — nothing else. Second, the EXP-007-parity shape for the three-arm set is **210**, and PLAN line 315's registered envelope is **~300**; neither is within a factor of six of what exists.

**Early-stop note.** The frozen rule needs three consecutive epoch boundaries (`loop.py:100`). At 1 or 2 epochs it **cannot fire**, so worst case equals actual. At 5 epochs it can (EXP-007's A2 seed 1 stopped at 21 of 35).

**The three branches. The authorization decision selects exactly one; DEC-036 selects none.**

* **Branch P — PARITY (210 worst case).** 3 arms × seeds {0,1} × 5 epochs × 7 cells. Requires a separate scope/cap governance action making ≥210 charged live TRAIN executions available, exactly as DEC-031 §11 requires. **This is the only branch DEC-036 endorses methodologically**: it is the EXP-007 shape, and it is the only branch in which each arm has a replicate and a learning phase.
* **Branch R — REUSE-PARITY (140 worst case).** 2 new arms (`A3-time-only`, `A4-mode4`) × seeds {0,1} × 5 epochs × 7 cells; the `A3-R3-frozen` control is **read from the already-charged 2026-09-12 training records, truncated episode-for-episode to 35 episodes**, at **0 additional charge**. Those records match on everything: `results/training/train-a0-d0-20260912T112906Z/manifest.json` and `train-a1-d0-20260912T115123Z/manifest.json` carry `reward_formula = R3`, `state_schema = state-v1.5`, `action_mode = mode12`, `q0_version = q0-exp002/v1`, `dataset_seed = 0`, `t_ref_gate_sha256 = e30a7b0c953d…`, the same seven cells in the same round-robin order and the same epsilon trajectory (`episodes.jsonl` episode 1 ε = 1.0, episode 8 ε = 0.6983). **Cost, which must be stated if this branch is taken:** the control was measured on 2026-09-12 under `code_version 8a9ca54-dirty`, the treatment arms would run later under the post-B6 tree, so every A3/A4 difference confounds the intended factor with cross-session timing drift against the 11.89% noise band DEC-018 F recorded. **Admissible; not recommended as the default.**
* **Branch M — MINIMUM (21 worst case), the only branch that fits today.** 3 arms × seed {0} × 1 epoch × 7 cells = 21, leaving 11. **ARITHMETICALLY ADMISSIBLE, METHODOLOGICALLY NOT RECOMMENDED.** With one seed and one epoch: each arm sees each cell exactly once; ε never falls below `0.95^7 = 0.6983` (`configs/rl.yaml:9-11`), so most actions are random; there is no replicate; and the early-stop rule cannot fire. **This weakens the scientific claim to the point of removing it**: the result would be a 21-execution random-policy probe, not an ablation of a trained policy, and it cannot support RQ4. It would also consume 21 of the 32 executions the project has left. (`docs/PLAN.md` lines 316-320 register EXP-009/010/011/012 with envelopes ~20/~25/~60/~10; **no decision states whether any of them charges SC6**, and this entry asserts nothing about them.)

**DEC-036 selects no branch.** Selection belongs to the authorization decision (DEC-030 §15 gate item 4), because it depends on capacity this entry has no power to create.

## 11 — What this decision deliberately does NOT decide

The branch selection (§10); the execution schedule; the authorization itself; any budget figure, charging rule or cap amendment; the amendment mechanism for the PLAN line 45 vs line 315 tension (DEC-031 §10, DEC-011); the B6 implementation authorization; R4's semantics (dropped, not specified); A5 in any form; TEST for anything; any statistical threshold; and the counting rule for zero-live manifests (DEC-032 §7.3, still open). It also does not decide whether Branch R's reuse is acceptable — it records the option and its confound.

## 12 — Gate-chain status after this entry

| Gate (DEC-030 §15) | State |
|---|---|
| (1) DEC-030 methodology freeze | **DONE** |
| (2) separate budget DEC resolving B5 | **DONE** — DEC-031, re-based by DEC-033 to 468/32 |
| (3) separate implementation DEC resolving B6 with green zero-Spark tests | **NOT DONE** — evidence exists; **DEC-036 does not supply it** |
| (4) separate authorization DEC with worst-case counts, ledger charge and a clean preflight re-run | **NOT DONE** — and blocked by capacity, not by methodology, once this entry is signed |
| §12's eighteen fields | **RESOLVED by this entry**, with fields 6 and 8 frozen as a rule plus three branches |

**Implementation consequence (NOT implemented here; DEC-025 §11 template).** The B6 report §7 refused to wire EXP-008 into `src/sparkrl/training/loop.py` because *"Doing so would require choosing a seed set, a cell set, a horizon and an early-stop rule — every one of which DEC-030 §12 leaves unresolved."* This entry removes that cause for the cell set, the early-stop rule and the horizon rule, and supplies the seed rule. A **separate later task** may therefore wire an EXP-008 runner **without inventing methodology** — under the B6 decision's authorization, not this one, and it must remain incapable of granting execution authorization.

## 13 — Non-authorization firewall (explicit)

| Item | State recorded by this entry |
|---|---|
| **EXP-008 execution authorization** | **FALSE / NO** |
| **Implementation authorization (A3/A4, B6)** | **FALSE / NO** — not granted here |
| **A5** | **DISABLED** (DEC-011; re-affirmed DEC-016 §7, DEC-023 §2, DEC-024, DEC-025 §7, DEC-030 §9); `configs/rl.yaml` `gamma` stays 0.0 |
| **TEST** | **NOT AUTHORIZED** — no TEST queue, specification or ledger is created |
| **SC6 cap** | **500 — not raised, not amended** |
| **Ledger** | **468 charged / 32 remaining — restated, not re-derived, not changed** |
| **`docs/PLAN.md`** | **UNCHANGED** — no line edited; R4 remains registered in §24 |
| **`configs/*.yaml`, `src/**`, `scripts/**`** | **UNCHANGED** — no file modified by this entry |
| **Historical decisions** | **UNCHANGED** — DEC-001 … DEC-026, DEC-030, DEC-031, DEC-032, DEC-033 are not rewritten; this entry is appended |
| **Spark / training / TEST executions performed by this entry** | **0 / 0 / 0** |

## 14 — Evidence (read-only; nothing listed was modified)

| Source | Role |
|---|---|
| `docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md` §12 (lines 337-354), §15 (line 372) | the eighteen fields and the gate chain |
| `docs/PLAN.md` line 45 (SC6), line 143 (§16 hyperparameters), line 188 (§24 ablations), line 315 (EXP-008 envelope) | registered intent; **unchanged** |
| `configs/rl.yaml` lines 7-11, 13, 16, 17, 27, 29 | alpha/gamma/epsilon, q0 source, seeds, cap, epoch definition, early stop |
| `configs/reward.yaml`, `configs/spark.yaml` lines 14, 19-20 | R3 weights; AQE off; warm-up policy |
| `src/sparkrl/rl/state.py:73`; `action.py:30,35,97-99`; `env.py:29-30,284,300`; `reward.py:85,111-120,197-206` | state schema, action grid, AQE guard, cache/step/budget semantics, R4 refusal |
| `src/sparkrl/agent/q0.py:47,64-78,190-196,239-250` | `q0-exp002/v1`; why the neutral builder is A1/A2-only |
| `src/sparkrl/training/loop.py:60,100,232-233,392-396` | early stop, epoch/cell derivation, the seven-cell refusal |
| `src/sparkrl/training/exp008.py` | the B6 scope layer; required-but-unset fields; Q0 policy; A5 guard |
| `results/training/train-a0-d0-20260912T{083120,112906}Z`, `train-a1-d0-20260912T115123Z`, `train-a2-d0-20260912T120648Z` (manifests + `episodes.jsonl`) | the existing charged R3/mode12/state-v1.5/q0-exp002 runs cited by Branch R |
| `docs/research/DEC_031_…md`; `DEC_032_…md`; `DEC_033_GOVERNANCE_RECONCILIATION.md`; `DAY37_EXP008_B6_IMPLEMENTATION_REPORT.md` | budget, validator, ledger re-base, B6 evidence |
| `DECISIONS.md` DEC-011, DEC-018 A/F, DEC-020 A/F, DEC-023, DEC-025 §§1-6, DEC-026 §13 | gamma lock, operator gate, descriptive-closure norm, EXP-007 scope and arithmetic |

**Working-tree disclosure.** DEC-033 exists as a standalone artifact with no `DECISIONS.md` section (§0). Any future entry citing DEC-033's 468/32 cites an authority in that form. Disclosed, not hidden, matching DEC-031 §15 / DEC-032 §11.

## 15 — Validation of this entry (read-only, zero Spark)

| Check | Result |
|---|---|
| DEC-036 is the identifier assigned to this cluster; no DEC-036 exists elsewhere | PASS (§0) |
| All eighteen DEC-030 §12 fields appear exactly once in the §5 table | PASS |
| Every INHERIT field cites a frozen value with a file:line | PASS (§5, §6) |
| No threshold, statistic, weight, formula or policy invented | PASS (§2, §8, §9) |
| No CITED historical figure edited | PASS (DEC-032 §3 discriminator) |
| Canonical figures restated, none re-derived | PASS (500 / 468 / 32) |
| Execution arithmetic derived from cited mechanics | PASS (§4, §10) |
| No execution authorized; no branch selected | PASS (§10, §13) |
| `docs/PLAN.md`, `configs/**`, `src/**`, `scripts/**`, all manifests and results unmodified | PASS |
| EXP-008 = NO; A5 = DISABLED; TEST = NOT AUTHORIZED | PASS (§13) |
| Spark / training / TEST executions performed | **0 / 0 / 0** |

**Status.** **DECIDED.** All eighteen DEC-030 §12 fields are resolved: **eleven INHERIT** (state-v1.5; mode12; the seven T_ref-calibrated cells; early stop at 2 stable epochs; AQE off; warm-up 2 + micro-job; no cache; alpha 0.2; gamma 0.0; epsilon 1.0 → 0.05 @ 0.95 — all with cited frozen authority), **five CHOOSE** (arm set = `A3-R3-frozen` + `A3-time-only` + `A4-mode4`; Q0 = `q0-exp002/v1` uniformly; A4 control reward = R3 paired to the `A3-R3-frozen` arm; A3/A4 share seeds, cells, horizon and control; statistics = descriptive-only with no threshold), **one DROP** (`A3-R4-log-ratio` removed from the executable arm set — **this weakens the scientific claim**, turning A3 from the registered three-way reward comparison into a two-way one; PLAN §24 is **not** amended and R4 stays registered), and **two ALREADY RESOLVED** (field 17 by DEC-031/DEC-033 at 468/32; field 18 by the separate B6 decision, **which is not signed as of this entry**). Fields **6 (seeds)** and **8 (horizon)** are frozen as a **rule** — integer 7-cell epochs; seeds an ascending prefix of {0,1,2} — with three fully specified branches (**P** 210, **R** 140, **M** 21) of which a separate authorization decision selects exactly one; **DEC-036 selects none, because the shapes that fit the current 32-execution envelope are 14, 21 and 28, and none of them is a training comparison.** `SC6 cap = 500, not raised`. `EXP-008 execution authorization = NO`. `A3/A4 implementation = NOT AUTHORIZED`. `A5 = DISABLED`. `TEST = NOT AUTHORIZED`. `docs/PLAN.md = UNCHANGED`. Historical decisions (DEC-001 … DEC-026, DEC-030, DEC-031, DEC-032, DEC-033) = **UNCHANGED**. Supervisor counter-signature: **PENDING** (conventional expectation only; never simulated; not a prerequisite under DEC-018 Decision A). **This entry performs 0 Spark executions and trains nothing.**

*End of DEC-036.*

---

*Standalone companion artifact. The authoritative log entry is the appended DEC-036 section of DECISIONS.md; this document carries the same decision content, self-contained (the DEC-031/DEC-032 convention).*

**Ledger supersession note (appended 2026-09-20, before signature).** This entry was drafted against the then-current ledger **468 / 32** (DEC-033). Five completed smoke TRAIN executions dated 2026-09-20 07:37-07:56Z were discovered afterwards and classified by **DEC-038**, making the canonical ledger **483 / 17** at signature. The figure is corrected here rather than in the body, so the drafting chronology stays visible. One consequence: the count-driving branches for fields 6 (seeds) and 8 (horizon) must be selected against **17**, not 32, by the separate authorization decision. Every field resolution in the body is unchanged, and this entry still charges nothing.
