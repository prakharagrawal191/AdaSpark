# DEC-039 | 2026-09-21 | EXP-008 authorization decision — zero-charge derived ablation authorized (gate item 4); trained executions remain NOT AUTHORIZED (Day 38/39)

**Decision ID:** DEC-039
**Date:** 2026-09-21
**Scope:** The EXP-008 **authorization decision** only (DEC-030 §15 gate item 4: worst-case counts, ledger charge, and the clean preflight re-run), plus production of the zero-charge DERIVED ablation exactly as DEC-034 §5 defines it. Nothing else.
**Status:** DECIDED — **the zero-charge derived ablation is AUTHORIZED and PRODUCED (0 executions, 0 charge); trained EXP-008 execution authorization remains NO.**
**Standalone decision artifact.** The authoritative log entry is the appended `## DEC-039` section of `DECISIONS.md`; this companion document carries the same decision content, self-contained, following the DEC-037/DEC-038 convention. Companion machine artifacts: `results/evaluation/exp008_derived_ablation.json` (fingerprint `18b33979a38e82ef…`) and `results/evaluation/exp008_preflight_rerun.json` (fingerprint `16779a4a4970f8db…`).
**Supersedes nothing.** DEC-001…DEC-026, DEC-030…DEC-038 are unchanged; no historical decision entry is rewritten; no cited figure is edited.

> **This entry performs 0 Spark executions, trains nothing, executes no TEST, creates no run directory, and modifies no manifest, no prior result artifact, no budget counter and no configuration.**
> **EXP-008 trained-execution authorization = NO. Zero-charge derived ablation = AUTHORIZED (DEC-034 §5; this entry). A5 = DISABLED. TEST = NOT AUTHORIZED. SC6 cap = 500, NOT raised. `docs/PLAN.md` = UNCHANGED.**

---

## 0 — Identifier resolution

`DECISIONS.md` headings run DEC-001…DEC-026 and DEC-031…DEC-038 (DEC-030 is recorded outside the ledger per DEC-031 §0; DEC-033 likewise per DEC-034 §0). No DEC-039 artifact exists. The next sequential identifier is **DEC-039**.

## 1 — Scope

In scope: (a) the **authorization decision** — the fourth and final item of the DEC-030 §15 gate chain (`1. DEC-030 methodology freeze ✓ → 2. DEC-031 budget/B5 ✓ → 3. DEC-035 B6 implementation ✓ → 4. authorization ← this entry`), stated with **worst-case execution counts** and **worst-case ledger charge**, and supported by the **clean preflight re-run** the gate wording requires; (b) **building the derived ablation** as DEC-034 §5 defines it, and delivering the ablation table `docs/PLAN.md` line 315 names as EXP-008's acceptance, in that zero-charge form. Not in scope: the SC6 cap; `docs/PLAN.md`; the trained-study question after this entry; A5 (DEC-011: DISABLED); TEST (not authorized); the R4 specification (dropped by DEC-036 §8 — see §6).

## 2 — Canonical figures restated, not re-derived

SC6 cap **500**, unchanged, **not raised** (`docs/PLAN.md` line 45; `configs/rl.yaml` line 17). Canonical ledger **483 charged / 17 remaining** (`232 + 84 + 20 + 126 + 6 + 15 = 483`; DEC-038 §3–§4; reconciled by the Day-31 validator's named smoke terms). `500 − 483 = 17`. This entry **adds no execution and no charge**: worst-case live TRAIN executions **0**; worst-case ledger charge **0**. Ledger after this entry: **483 / 17 — unchanged.**

## 3 — The authorization (gate item 4)

| Question | Decision |
|---|---|
| DEC-030 §15 gate items 1–3 | **SATISFIED** — DEC-030 (methodology freeze), DEC-031 (budget/B5), DEC-035 (B6 implementation) |
| **Worst-case live TRAIN executions of the authorized work** | **0** |
| **Worst-case ledger charge of the authorized work** | **0** |
| **Zero-charge derived ablation (DEC-034 §5 scope)** | **AUTHORIZED and PRODUCED** (§5–§6 below) |
| **Trained EXP-008 execution** | **NOT AUTHORIZED** — unchanged from DEC-034/DEC-036 |
| DEC-036 §10 branches **P (210) / R (140) / M (21)** | **NONE SELECTED** — each exceeds the 17-execution envelope (`210 > 17`, `140 > 17`, `21 > 17`); the branch rule stays frozen and revives under R8 |
| A5 | **DISABLED** (DEC-011; re-affirmed DEC-030 §9, DEC-031 §14, DEC-036) |
| TEST | **NOT AUTHORIZED** — nothing here opens TEST for anything |
| R8 scope-ladder rungs 2–4 | **UNCONSUMED** |
| `docs/PLAN.md` | **UNCHANGED** — line 315 stays planned (`A3, A4, A5`, ~300 trained runs, Train/Test); the ~300 trained runs are **not consumed** by the zero-charge form |

The arithmetic that makes this the only admissible shape is recorded, not invented: any trained comparison needs a DEC-036 branch, and no branch fits 17; the derived form needs **0**, which fits any envelope. This is DEC-034 §5's scope, resolved and exercised — DEC-034 explicitly deferred the authorization (its §9) and DEC-036 deferred the branch selection (§10); both deferrals are resolved here.


## 4 — The clean preflight re-run (gate wording, second clause)

## 6 — The ablation table (PLAN line 315 acceptance, zero-charge form)

State rows are the `state-v1.5` rows of the derived Q0 tables (4 rows × 12 actions = 48 evidence pairs, 4 observations per pair). Descriptive only — **no threshold, no inferential statistic** (DEC-030 §8; DEC-036 field 14).

| State row | greedy mode12 (R3) | greedy mode12 (time-only) | greedy action agreement | greedy mode4 (from R3) |
|---|---|---|---|---|
| `agg` | 8 = G-p8-sp16 | 8 = G-p8-sp16 | **agree** | 9 = G-p8-sp32 |
| `join` | 8 = G-p8-sp16 | 8 = G-p8-sp16 | **agree** | 9 = G-p8-sp32 |
| `mixed` | 9 = G-p8-sp32 | 9 = G-p8-sp32 | **agree** | 9 = G-p8-sp32 |
| `rdd_sort` | 7 = G-p4-sp128 | 7 = G-p4-sp128 | **agree** | 0 = G-p2-sp16 |

Q-value pair comparison: **8 of 48** evidence pairs differ between the two reward shapes; **all eight are in the `rdd_sort` row (actions 4–11)**. The greedy action is unchanged on every state row. These are descriptions of recorded data, not claims about training.

**Structural reachability (DEC-034 §8 — previously *available, not asserted*; now verified and recorded).** Under the frozen grid mapping (`grid_index = parallelism_index·4 + shuffle_index`), mode4 = {G-p2-sp16, G-p2-sp128, G-p4-sp64, G-p8-sp32}. Therefore:

* **B1 is unreachable**: the frozen B1 selection `G-p8-sp16` is grid index **8** ∉ mode4.
* **Two of the three distinct frozen B2 definitions are unreachable**: `G-p8-sp16` (F1_agg, F2_join) = index **8** ∉ mode4, and `G-p8-sp64` (F3_rdd) = index **10** ∉ mode4. The third, `G-p8-sp32` (F5_mixed) = index **9**, **is** reachable.

## 7 — Stated limitations (verbatim, binding on any use of this table)

1. **"A3 here ablates the OFFLINE INITIALIZATION, not ONLINE LEARNING."**
2. **"RQ4 asks about learning stability and final policy quality; the learning-stability half is UNANSWERED by this decision and is reported as a stated limitation, with no claim about what a trained comparison would have shown."**

## 8 — What this decision deliberately does NOT decide

Whether EXP-008's trained study (PLAN line 315, ~300 runs) is ever executed, and under which DEC-036 branch if so (the branch rule and R8 rungs remain available and unconsumed); any change to `docs/PLAN.md` or the register line (the PLAN tension recorded by DEC-031 §10 stays open; this entry does not amend the PLAN); the R4 specification (dropped from the executable set by DEC-036 §8 — it stays registered and may not be revived by this entry); any statistical treatment beyond descriptive reporting; EXP-009/EXP-010; `scripts/validate_day30.py` maintenance; the classification of the zero-live manifests (DEC-032 §7.3, still UNRESOLVED). DEC-030 §12 fields 6–12 and 16 remain **inapplicable by construction** under the zero-execution scope and **revive in full** if any later decision restores a trained scope.

## 9 — Non-authorization firewall (explicit)

| Item | State recorded by this entry |
|---|---|
| **EXP-008 trained-execution authorization** | **NO — UNCHANGED** |
| **Zero-charge derived ablation (DEC-034 §5 scope)** | **AUTHORIZED — and PRODUCED (§5–§6)** |
| **Worst-case live TRAIN executions / worst-case ledger charge** | **0 / 0** |
| **SC6 cap** | **500 — UNCHANGED, NOT RAISED** |
| **SC6 ledger** | **483 charged / 17 remaining — UNCHANGED** |
| **A5** | **DISABLED** (DEC-011); `configs/rl.yaml` `gamma` stays 0.0 |
| **TEST** | **NOT AUTHORIZED** — nothing here opens TEST for anything |
| **R8 scope-ladder rungs 2–4** | **UNCONSUMED** |
| **`docs/PLAN.md`** | **UNCHANGED — no line edited; line 315 stays planned** |
| **`configs/rl.yaml`** | **UNCHANGED** |
| **Historical decisions** | **UNCHANGED** — DEC-001…DEC-026, DEC-030…DEC-038 are not rewritten; this entry is appended, never substituted |
| **Spark / training / TEST executions performed by this entry** | **0 / 0 / 0** |

## 10 — Evidence and fingerprints (read-only; nothing listed was modified)

| Source | Role | SHA256 (first 16) |
|---|---|---|
| `docs/PLAN.md` | SC6 line 45; EXP-008 line 315 | `db5e82102833efe6` (**unchanged** — identical to the value DEC-031/DEC-032/DEC-034 record) |
| `configs/rl.yaml` | cap 500; epsilon schedule | `8ca70d6dd7df6884` (**unchanged**) |
| `docs/research/DEC_034_EXP008_SCOPE_RESOLUTION.md` | §5 derived scope; §8 available-not-asserted | `73433b569f4086cb` |
| `docs/research/DEC_035_EXP008_B6_IMPLEMENTATION.md` | B6 implementation | `a24df0d9cfa959ee` |
| `docs/research/DEC_036_EXP008_METHODOLOGICAL_FIELDS.md` | all eighteen fields | `7ec988bd40f794f6` |
| `src/sparkrl/agent/q0.py` | reused Q0 machinery | `7d2ffb0c33fc4349` |
| `src/sparkrl/rl/reward.py` | frozen reward semantics | `e98a1351c42fc230` |
| `src/sparkrl/training/exp008.py` | TRAIN-only guard | `0a2252b378dda0a6` (**unchanged** from DEC-034's record) |
| `results/experiments/exp-002/analysis/gate.json` | T_ref source | `e30a7b0c953d9965` |
| `results/evaluation/baseline_selection.json` | frozen B1/B2 | `b452197abb32a77c` |
| `results/evaluation/exp008_b6_implementation.json` | DEC-035 artifact | `b6cf45148fcb8d45` |
| `results/evaluation/exp008_preflight_audit.json` | DEC-030 audit (re-run by §4) | `6f49f9b81156f8f6` |
| **NEW** `results/evaluation/exp008_derived_ablation.json` | the ablation table + limitations | fingerprint `18b33979a38e82ef…` |
| **NEW** `results/evaluation/exp008_preflight_rerun.json` | the clean preflight re-run | fingerprint `16779a4a4970f8db…` |

## 11 — Validation of this entry (read-only, zero Spark)

The generator (`scripts/generate_exp008_derived_ablation.py`) is deterministic and opens no Spark session; re-running it is a fingerprint-verified no-op (freeze write-once discipline). The unit suite pins: the greedy tie-break to the lowest index; the structural subset-argmax property of A4; that `A3-R4-log-ratio` refuses construction (not retained, not executable); and that both stored artifacts are sealed (`artifact_id` = content fingerprint), carry `executed: false` and `spark_executions: 0`, record the three stated limitations verbatim, and record worst-case 0/0. All seven read-only validators are re-run after this entry; none executes Spark and the ledger is untouched.

---

**Status.** **DECIDED.** The DEC-030 §15 gate chain is complete: **1** methodology freeze (DEC-030) ✓, **2** budget/B5 (DEC-031, ledger 483/17) ✓, **3** B6 implementation (DEC-035) ✓, **4** authorization (**this entry**) ✓ — with **worst-case live TRAIN executions 0, worst-case ledger charge 0**, and a **clean preflight re-run** recorded (`exp008_preflight_rerun.json`; all six blockers `B1–B6` RESOLVED by cited decisions). The **zero-charge derived ablation is AUTHORIZED and PRODUCED**: A3 recomputed (`A3-time-only` vs `A3-R3-frozen`, 48 evidence pairs, 8 differing — all in the `rdd_sort` row — greedy actions agreeing on every state row), A4 derived structurally (mode4 subset argmax; per-state greedy 9, 9, 9, 0), the DEC-034 §8 reachability facts verified and recorded (B1 unreachable; two of three distinct B2 definitions unreachable; F5_mixed's reachable), the ablation table delivered as PLAN line 315's acceptance in its zero-charge form, and **A3-R4 not retained**. **No DEC-036 branch is selected (P 210 / R 140 / M 21 all exceed the 17-execution envelope).** `SC6 cap = 500, NOT raised`. `EXP-008 trained-execution authorization = NO`. `A5 = DISABLED`. `TEST = NOT AUTHORIZED`. `docs/PLAN.md = UNCHANGED`. Historical decisions (DEC-001 … DEC-026, DEC-030 … DEC-038) = **UNCHANGED**. Supervisor counter-signature: **PENDING** (conventional expectation only; never simulated; not a prerequisite under DEC-018 Decision A). **NO SUPERVISOR HAS REVIEWED THIS ENTRY.** A future review is a new entry; this one is never rewritten. **This entry performs 0 Spark executions and trains nothing.**

3. **"Descriptive only — no threshold and no inferential statistic is computed or asserted (DEC-030 §8)."**

These three sentences are recorded verbatim in `exp008_derived_ablation.json` under `stated_limitations` and are part of the deliverable, not commentary on it. The final-policy-quality half of RQ4 is likewise **not answered by this table**: the derived policies are initializations, not trained policies, and no quality claim is made.


The 2026-09-17 preflight audit (`results/evaluation/exp008_preflight_audit.json`, DEC-030) recorded recommendation **"NO-GO // B1-B6 block execution authorization"** with six blocking findings. This entry re-runs that audit **clean** (zero Spark, read-only) as `results/evaluation/exp008_preflight_rerun.json`; every blocker is resolved by a recorded decision, cited verbatim:

| Blocking finding (audit-verbatim) | Resolved by |
|---|---|
| `B1-A3-UNFROZEN` | DEC-030 (variant-structure freeze); **DEC-036 §5/§8** — executable arm set `A3-R3-frozen` + `A3-time-only`; **A3-R4 DROPPED** |
| `B2-A4-UNFROZEN` | DEC-030 §5 (structural compatibility); **DEC-036 §5** — mode12; A4 subset `{0, 3, 6, 9}` |
| `B3-Q0-UNFROZEN` | **DEC-036 §5** — Q0 = `q0-exp002/v1` uniformly, rows wide 12, no projection, no invented pooling |
| `B4-CONTROLS-UNFROZEN` | **DEC-036 §5/§6** — eleven INHERIT fields; seeds/horizon frozen as a rule with branches P/R/M |
| `B5-BUDGET-EXHAUSTED` | **DEC-031** §3/§4/§5/§8 + **DEC-033/DEC-038** — ledger 483/17 of 500 |
| `B6-IMPLEMENTATION-GAP` | **DEC-035** — B6 implementation adopted, semantics registered and validator-enforced |

Non-blocking findings `N1…N6` are dispositioned in the artifact exactly as the record supports (N3–N6 resolved by DEC-034/DEC-036; N1/N2 non-blocking by the audit's own classification, N2's failure transformation registered exactly by DEC-035). The re-run's recommendation is **"GO // zero-charge derived ablation only (DEC-034 §5); trained-execution authorization remains NO"** — the GO is scoped to the 0-execution form and must not be read wider.

## 5 — The derived ablation, built exactly as DEC-034 §5 defines it

**A3 (reward-shape ablation).** `A3-time-only` (`R = 1.0 · clip((T_ref − T)/T_ref, −1, +1)`, failure `R = −1.0`) is recomputed against `A3-R3-frozen` over the already-recorded EXP-002 TRAIN observation store (`results/experiments/exp-002`, 208 records scanned / 167 valid used / 16 B0 references / 8 T_ref-missing skipped / 17 invalid skipped), reusing the `src/sparkrl/agent/q0.py` machinery with T_ref from the EXP-002 gate artifact (`exp002-gate:gate.json`), TRAIN cells only. Charged live TRAIN executions: **0** — the observations already existed; nothing was run.

**A4 (action-space ablation).** `MODE4_SUBSET = {0, 3, 6, 9}` is a strict subset of the frozen 12-action grid, so the mode4 greedy policy is derived **structurally**: greedy action = argmax over the subset of the same mode12 Q-table (frozen tie-break: lowest index), derived from the `A3-R3-frozen` table per DEC-036's control pairing (field 5). No execution of any kind.

**A3-R4 is not retained.** DEC-036 §8 dropped it from the executable arm set; no Q0 under R4 ever existed, none is constructed here, and the registered formula remains not-executable (proved by construction: `RewardCalculator(formula="A3-R4-log-ratio")` refuses at construction — pinned by the unit suite).
