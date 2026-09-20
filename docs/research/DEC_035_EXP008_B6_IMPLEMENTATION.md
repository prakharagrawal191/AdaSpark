# DEC-035 | 2026-09-20 | EXP-008 A3/A4 implementation decision (B6; DEC-030 s15 gate item 3) - ADOPTED with fields 1/13/14 deferred; execution authorization remains NO (Day 38, C2)

**Decision ID:** DEC-035
**Date:** 2026-09-20
**Scope:** DEC-030 §15 gate-chain item (3) only — the implementation decision resolving B6, with green zero-Spark tests. **Nothing else.**
**Status:** DECIDED — the EXP-008 A3/A4 implementation at HEAD `c2e980a` is ADOPTED as the B6 resolution, with DEC-030 §12 fields **1, 13 and 14** explicitly DEFERRED to the methodology/authorization decisions. **`EXP-008 execution authorization = NO`.**
**Standalone decision artifact.** The authoritative log entry is the appended DEC-035 section of `DECISIONS.md`; this document carries the same decision content, self-contained, so the decision also exists as an addressable artifact (the DEC-031/DEC-032 convention).
**Supersedes nothing.** DEC-030, DEC-031, DEC-032 and DEC-033 are unchanged; no historical decision entry is rewritten. `docs/research/DAY37_EXP008_B6_IMPLEMENTATION_REPORT.md` and `results/evaluation/exp008_b6_implementation.json` are **adopted as evidence and retained byte-identical** — they are B6-time records and are not regenerated.

> **This entry performs 0 Spark executions, trains nothing, executes no TEST, creates no run directory, and modifies no manifest, result, budget, ledger, configuration or implementation file.**
> **EXP-008 execution authorization remains NO. A5 remains DISABLED. TEST remains NOT AUTHORIZED. `docs/PLAN.md` is UNCHANGED. The SC6 cap remains 500 and is NOT raised.**

---

## 0 — Identifier resolution

`DECISIONS.md` headings run **DEC-001 … DEC-026**, plus **DEC-031** (`DECISIONS.md:2113`) and **DEC-032** (`DECISIONS.md:2241`). Two further decisions are formally recorded **outside** `DECISIONS.md`, by the convention DEC-031 §0 established for DEC-030: **DEC-030** (`docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md`) and **DEC-033** (`docs/research/DEC_033_GOVERNANCE_RECONCILIATION.md`; `grep -n "DEC-033" DECISIONS.md` returns **zero** lines). A repository-wide search for `DEC-034` and `DEC-035` returns **nothing**: neither identifier is occupied by any artifact, heading or code reference.

**DEC-035 is the identifier assigned to this entry by the operator's decision-drafting pass.** This entry does **not** claim, reserve, describe or depend on DEC-034; if DEC-034 is recorded by a sibling entry, its content is not read into this one. That DEC-033 currently has no `DECISIONS.md` section is **recorded, not corrected here** — DEC-030 is in the same position and DEC-031 §0 preserved its identity rather than renumbering it.

## 1 — Scope

DEC-030 §15 (`docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md:372`) sets the gate chain: *"(1) this DEC-030; (2) a separate budget DEC resolving B5; (3) a separate implementation DEC resolving B6 with green zero-Spark tests; (4) a separate authorization DEC … with worst-case counts and ledger charge, plus a clean preflight re-run."*

Item (1) is DONE (DEC-030). Item (2) is DONE (DEC-031, as the ledger was later moved by DEC-033). **This entry is item (3), and only item (3).** Item (4) is untouched and remains open.

In scope: (a) what the EXP-008 A3/A4 implementation actually is today; (b) whether its zero-Spark tests are green; (c) which DEC-030 §12 fields the implementation enforces fail-closed and which it does not; (d) whether anything implemented exceeds what DEC-030 froze, and whether A5 is inert; (e) the disposition of the one owed item the B6 report left open. Nothing else.

## 2 — Why a decision is required, and what the existing evidence is

The B6 evidence exists and disclaims decision status in terms. `docs/research/DAY37_EXP008_B6_IMPLEMENTATION_REPORT.md:12`:

> *"This report is **not a decision**. DEC-030 §15 gate-chain item (3) expects a separate decision entry to record B6; this document and its JSON supply the evidence that item needs, nothing more. No DEC number is claimed, no authorization is granted, and no methodological field is frozen here."*

Its §10 row 1 restates the same gap: *"The B6 implementation decision itself (DEC-030 §15 gate item 3) … This report and its JSON are evidence, not a decision entry."* **DEC-035 is that decision entry.** It adds no implementation, changes no code, and invents no methodology.

The adopted evidence is: `docs/research/DAY37_EXP008_B6_IMPLEMENTATION_REPORT.md`, `results/evaluation/exp008_b6_implementation.json`, `src/sparkrl/training/exp008.py`, the additive change to `src/sparkrl/rl/reward.py`, `configs/exp008.yaml`, and the three zero-Spark test files `tests/unit/test_exp008_{scope,action,reward}.py` — all tracked at HEAD `c2e980a` (`git log --oneline -1 -- src/sparkrl/training/exp008.py` → `2c00236 feat(gov): commit the EXP-006/007/008 implementation and repair the validator chain`), working tree clean.

## 3 — What is actually implemented today (established by reading the code, not the report)

**3.1 The arm set — exactly the DEC-030 four, and no A5.**

```python
A3_ARMS  = (ARM_A3_R3, ARM_A3_TIME_ONLY, ARM_A3_R4_LOG_RATIO)   # exp008.py:92
A4_ARMS  = (ARM_A4_MODE4,)                                       # exp008.py:93
ALL_ARMS = A3_ARMS + A4_ARMS                                     # exp008.py:94
```

`ARM_REWARD_FORMULA` (`exp008.py:99-103`) binds each A3 arm to its own reward by arm identity; A4's reward is deliberately absent from that map because DEC-030 §12 field 5 leaves the A4 control pairing unfrozen.

**3.2 The reward handling.**

* `R3` — unchanged. `RewardCalculator.__init__` takes `formula` as **keyword-only**, defaulting to the frozen `R3` (`src/sparkrl/rl/reward.py:191-192`), so no existing call site changes behaviour. `configs/reward.yaml` is byte-identical at `a52131d5…db1b`.
* `A3-time-only` — implemented exactly as DEC-030 §3.2 froze it: `TIME_ONLY_WEIGHTS` (`reward.py:99`) gives `w_time=1.0, w_task=0.0, w_spill=0.0, w_failure=1.0`, clip `[-1,+1]`, failure `-1.0`, module constants never read from `configs/reward.yaml`. **DEC-030 §3.2's mandatory classification is carried through unchanged and is restated here: time-only is a MULTI-TERM REMOVAL from R3 — the task-imbalance term AND the spill-waste term are removed simultaneously — and no future analysis may attribute an A3-time-only-versus-R3 difference to a single removed term.**
* `A3-R4-log-ratio` — registered, not executable. `REGISTERED_FORMULAS` contains it; `IMPLEMENTED_FORMULAS` (`reward.py:93`) does not. `build_reward_calculator` (`exp008.py:284-301`) raises `IncompleteFormulaError` naming all eight DEC-030 §3.4 unresolved semantics before any computation and before any Spark execution.

**3.3 The action subset — reused, never redefined.**

```python
A4_ACTION_MODE   = MODE4
A4_ACTION_SUBSET = MODE4_SUBSET          # frozenset({0, 3, 6, 9})   exp008.py:108-109
```

`A4_ACTION_SUBSET` **is** the frozen `MODE4_SUBSET` object from `src/sparkrl/rl/action.py`, which is byte-identical at `580cf010…c0528` — the value DEC-030's freeze JSON recorded. `a4_action_configurations()` (`exp008.py:320-339`) derives all four configurations from the frozen `ActionMapper`, preserving original indices and config names. No action is renumbered and no 4-wide table is produced.

**3.4 The guards (all firing before any Spark execution).**

| Guard | Location | Refuses |
|---|---|---|
| `guard_arm` | `exp008.py:177-183` | any arm outside `ALL_ARMS`; routes `A5` to its own error first |
| `guard_a5` | `exp008.py:186-204` | `arm == "A5"`; `multi_step=True`; any `gamma != 0.0` |
| `guard_split` | `exp008.py:207-214` | any split != `TRAIN` |
| `guard_cell` / `guard_train_cells` | `exp008.py:217-243` | cells outside the frozen domain (re-raised as `Exp008ConfigError`) and any non-TRAIN cell |
| `guard_metrics` | `exp008.py:246-257` | metrics carrying `split`/`test_family`/`test_scale`/`test_seed` |
| `guard_agent_seeds` | `exp008.py:260-281` | unset seeds (`Exp008IncompleteError`), non-int, duplicate, empty — **never invents a seed set** |
| `build_reward_calculator` / `guard_reward_variant` | `exp008.py:284-311` | unregistered variants; R4 |
| `guard_action_mode_for_arm` | `exp008.py:342-357` | unset mode; unknown mode; any non-`mode4` mode for the A4 arm |
| `guard_q0_projection` / `guard_q0_source` / `guard_q0_rows` / `guard_q0_for_mode` | `exp008.py:384-438` | every projection; any source outside `q0-exp002/v1` and `q0-neutral/v1`; any Q0 row not 12 wide; any Q0 at all for A3-R4 |
| `arm_config_from_mapping` | `exp008.py:673-721` | unknown configuration keys (closed schema) and wrong value types |

**3.5 The scope constants that ARE fixed, and their DEC-030 authority.**

| Constant | Value | Frozen by |
|---|---|---|
| `FROZEN_DATASET_SEED` (`exp008.py:116`) | `0`, and any other value is refused | DEC-030 §3.2 *"Dataset seed \| 0 (frozen: T_ref calibrated for seed 0 only)"* — a measured fact |
| `q0_projection` | `False`, unconditionally | DEC-030 §5.1 rules 2–4 |
| `Q0_ROWS_WIDE` (`exp008.py:119`) | `12` | DEC-030 §5.4 *"EXISTING FROZEN MAPPING"* |
| A4 action mode | `mode4`, locked | DEC-030 §4.2 / §4.3 |
| A3 arm→reward binding | by arm identity | DEC-030 §3 |
| `EXECUTION_AUTHORIZED` (`exp008.py:78`) | `False`; `SPARK_EXECUTIONS = TRAINING_EXECUTIONS = TEST_EXECUTIONS = 0` | DEC-030 §11; DEC-031 §14 |

## 4 — Zero-Spark tests: GREEN (re-run for this entry)

```
$ python -m pytest tests/unit/test_exp008_scope.py tests/unit/test_exp008_action.py tests/unit/test_exp008_reward.py
103 passed in 0.24s        (exit 0)
```

The 0.24 s wall time is itself evidence that no Spark session was started. The per-file split recorded by the B6 artifact is `test_exp008_scope.py` **50**, `test_exp008_action.py` **32**, `test_exp008_reward.py` **21** = **103**, which matches the re-run total exactly.

**What this entry did NOT run, and does not assert:** the full `tests/unit` suite, any validator in `scripts/` (several regenerate tracked artifacts), any integration test, any training, any TEST, and any Spark. The *"full unit suite green, seven validators PASS"* state reported to this drafting pass is **not re-verified here** and must be re-verified at gate item (4)'s clean preflight re-run, as DEC-030:372 already requires.

**Gate item (3)'s "with green zero-Spark tests" condition is therefore SATISFIED on the evidence this entry itself produced.**

## 5 — What the implementation presumes: NOTHING that DEC-030 left unfrozen (one named consequence)

This was the specific risk B6 exists to surface: a presumption baked into code while the field is marked *"UNFROZEN — SEPARATE DECISION REQUIRED"*. DEC-030 §3.2 does record presumed values for state schema (state-v1.5), action schema (mode12), alpha (0.2), gamma (0.0), epsilon (1.0→0.05 @0.95), AQE (off) and T_ref (EXP-002 TRAIN B0 median). **The implementation inherits none of them.** Every one is a required-but-unset field (`exp008.py:150-166`) and an explicit `null` in the shipped artifact (`configs/exp008.yaml`: `action_mode: null`, `state_schema: null`, `q0_source: null`, `alpha: null`, `gamma: null`, `epsilon_schedule: null`, `aqe_condition: null`, `t_ref_source: null` on all four arms). `validate_configuration()` raises `Exp008IncompleteError` listing them (`exp008.py:625-633`), and `tests/unit/test_exp008_scope.py:138` proves it field by field.

**One named consequence, recorded not hidden.** DEC-030 §12 field 16 covers *"Epsilon schedule / alpha / gamma if deviating from frozen values"*. `gamma` is required-but-unset, but `guard_a5` (`exp008.py:200-204`) then refuses every value except `0.0`. The admissible set for `gamma` is therefore `{0.0}`. That is **not** a new freeze: it is DEC-030 §9's A5 lock (*"`configs/rl.yaml` gamma remains 0.0; DEC-030 makes no change and permits none"*) expressed in code. DEC-035 adopts it as a restatement of the A5 lock and freezes nothing new.

## 6 — DEC-030 §12 coverage: fail-closed on 15 of 18 (16 for A4) — CORRECTION OF RECORD

`A3_REQUIRED_FIELDS` (`exp008.py:150-166`) contains exactly **fifteen** names; `A4_REQUIRED_FIELDS` adds `reward_variant` (`exp008.py:167`), giving **sixteen** for A4. DEC-030 §12 (`…METHODOLOGY_FREEZE.md:333-354`) lists **eighteen** fields.

| §12 # | Field | Representation in code | Fail-closed? |
|---|---|---|---|
| 1 | Final arm set to execute | none — all four arms always present | **NO** |
| 2 | Q0 source per arm | `q0_source` + `guard_q0_source` | YES |
| 3 | State schema per arm | `state_schema` | YES |
| 4 | Action schema for A3 | `action_mode` + `guard_action_mode_for_arm` | YES |
| 5 | Reward arm for A4 control pairing | `reward_variant` (A4 only) | YES (A4) |
| 6 | Seeds | `agent_seeds` + `guard_agent_seeds` | YES |
| 7 | TRAIN cells | `train_cells` + `guard_train_cells` | YES |
| 8 | Episode horizon | `episode_horizon` | YES |
| 9 | Early-stop rule | `early_stop_rule` | YES |
| 10 | AQE condition | `aqe_condition` | YES |
| 11 | Warm-up behavior | `warm_up_behavior` | YES |
| 12 | Cache behavior | `cache_behavior` | YES |
| 13 | Whether A3 and A4 share seeds/cells/horizon | none — a cross-arm field with no per-arm slot | **NO** |
| 14 | Statistical governance | `statistical_governance` field EXISTS but is **not required** | **NO** |
| 15 | R4 complete specification | `IncompleteFormulaError` — strongest enforcement in the module | YES |
| 16 | Epsilon / alpha / gamma deviations | `epsilon_schedule`, `alpha`, `gamma` (see §5) | YES |
| 17 | Live-execution charging rule | `live_execution_charging_rule` | YES |
| 18 | Implementation authorization (B6) | `EXECUTION_AUTHORIZED = False`; this entry | n/a |

**Proved by direct read-only construction, not inferred.** An `A3-time-only` configuration supplying all fifteen required fields, with `statistical_governance`, `execution_budget`, `code_fingerprint`, `t_ref_fingerprint` and `q0_variant` left `None`, makes `validate_configuration()` return normally, `unresolved_fields()` return `()`, and `arm_runtime_kwargs()` return component kwargs including a constructed `RewardCalculator`. The repository's own test records the same behaviour by name: `tests/unit/test_exp008_scope.py:144` — `test_a_fixture_complete_config_validates_without_authorizing_anything`.

> **Correction of record (following the DEC-032 §4 precedent for correcting a work-stream statement without rewriting the artifact).** The B6 report §9.4 states that the implementation *"gives the 18 fields of DEC-030 §12 an explicit, schema-safe, fail-closed representation."* The **explicit** and **schema-safe** halves are accurate — every one of the eighteen appears, and unresolved values are emitted as `null` and listed under `unresolved_fields`. The **fail-closed** half is accurate for fifteen of them (sixteen for A4) and **not** for fields 1, 13 and 14. The B6 report is **not edited**; it is a B6-time record and stands as written. This decision carries the corrected statement.

**Consequence, binding on gate item (4):** `validate_configuration()` passing is **not** methodological completeness and **not** authorization. The authorization DEC must check DEC-030 §12 fields **1, 13 and 14** by hand; the configuration layer will not stop it.

## 7 — Scope-creep audit: nothing implemented exceeds what DEC-030 froze

**7.1 Exactly one governed source file changed.** `src/sparkrl/rl/reward.py` (now `e98a1351…fd95`; DEC-030's recorded pre-B6 fingerprint `0c5e67f4…9798` remains a correct historical record of the earlier state). DEC-030 §13 anticipated precisely this: *"Current `sparkrl.rl.reward` implements exactly one frozen formula (R3) and refuses any other — an additive, default-preserving extension would be required."* Every other DEC-030-fingerprinted file is byte-identical to its recorded value: `action.py` `580cf010…c0528`, `q0.py` `7d2ffb0c…de195`, `q_learning.py` `1c5fab89…bb31`, `loop.py` `b513238d…83611`, `ablation.py` `69ab9c40…b5216a`. `docs/PLAN.md` `db5e8210…ee63`, `configs/rl.yaml` `8ca70d6d…8b80`, `configs/reward.yaml` `a52131d5…db1b` — all unchanged.

**7.2 No runner exists, by design.** `loop.py` is untouched; B6 report §7 states why: *"Doing so would require choosing a seed set, a cell set, a horizon and an early-stop rule — every one of which DEC-030 §12 leaves unresolved — so any wiring would have had to invent methodology."* `tests/unit/test_exp008_scope.py:393` (`test_module_never_imports_spark_or_a_runner`) passes; the module's imports are `yaml`, `sparkrl.agent.q0`, `sparkrl.experiments.spec`, `sparkrl.rl.action`, `sparkrl.rl.reward` — no `pyspark`, no `sparkrl.rl.env`, no `subprocess`.

**7.3 Two surfaces recorded, neither a creep, both disclosed.**

* `arm_runtime_kwargs()` (`exp008.py:645-667`) returns a live `RewardCalculator` and component kwargs for a validated configuration. It is the closest thing in the change to executable machinery. It builds nothing, launches nothing and grants nothing; it is recorded so the authorization gate knows what surface it is fingerprinting.
* `arm_scope_summary()` (`exp008.py:776`) emits `"executable": arm != ARM_A3_R4_LOG_RATIO`, i.e. `true` for three arms. In that dict the word means **"this arm's reward formula can be constructed"**, nothing more; the same dict carries `execution_authorized: False`, `spark_executions: 0`, `training_executions: 0`, `test_executions: 0` (`exp008.py:787-790`). **No consumer may read that key as an authorization signal.**

**7.4 A narrowing relative to PLAN, stated so it is never mistaken for a de-scoping.** `docs/PLAN.md:315` registers EXP-008 with split *"Train/Test"* and arms *"A3, A4, A5"*. The implementation is TRAIN-only by hard guard and contains no A5. **This decision does NOT amend PLAN and does NOT de-scope EXP-008.** `docs/PLAN.md` is unchanged. The TRAIN-only guard binds the A3/A4 implementation layer only; any TEST component of EXP-008 would require its own decision and its own treatment of the TEST seal (PLAN §18: *"no test metric influences training or tuning"*; DEC-018 Decision B). Refusing TEST is the conservative direction and is left in place.

## 8 — A5 is genuinely inert

Four independent facts, each checked: (a) `A5` is absent from `ALL_ARMS` (`exp008.py:92-94`); (b) `guard_a5` (`exp008.py:186-204`) raises `A5DisabledError` for the `A5` arm, for `multi_step=True`, and for any `gamma != 0.0`; (c) `configs/exp008.yaml:26-27` states *"A5 is DISABLED … and is not representable here at all"*, and `load_exp008_config` refuses unknown arms (`exp008.py:181-184`); (d) `configs/rl.yaml:8` still reads `gamma: 0.0` and the file is byte-identical at `8ca70d6d…8b80`. Three tests assert it: `test_a5_arm_is_refused`, `test_multi_step_and_non_zero_gamma_are_refused`, `test_a5_is_absent_from_the_scope_summary_arms`. **A5 remains DISABLED** (DEC-011; re-affirmed DEC-016 §7, DEC-023 §2, DEC-024 A5 row, DEC-025 §7, DEC-030 §9). Nothing here opens multi-step RL.

## 9 — The B6 report's one owed item is DISCHARGED (§8 / §10 row 5)

The B6 report classified the stale SC6 pin in `tests/unit/test_exp001_maintenance.py::test_exp003_or_exp005_are_never_charged_to_sc6` as owed work needing a decision: *"Re-pinning a governance ledger constant to `462`/`38` is a DEC-031 follow-up, not an implementation-only change"* (§8), repeated as §10 row 5. Two later decisions discharged it, in sequence:

1. **DEC-032 §8** adopted the `336/164 → 462/38` re-pin as operator-authorized Day-37 work, *"on the same reasoning as §3 (the assertion re-derives from the live tree; it does not cite a historical figure) and subject to the same invariant as §6 (the pin was not weakened — it remains an exact equality)"*, and named the B6 report as the reason for recording it: *"the B6 implementation report (§8, §10 row 5) had classified that repair as 'a DEC-031 follow-up' … **DEC-032 is that decision.**"*
2. **DEC-033** then charged the six completed 2026-09-19 smoke TRAIN executions under DEC-031 §5 categories 1 and 3, moving the canonical ledger to `232 + 84 + 20 + 126 + 6 = 468`, remaining `500 − 468 = 32`, with follow-up (ii) *"correcting the test pin from 462/38 to 468/32, keeping it an exact equality so an unauthorized execution still breaks it."*

The pin now reads `tests/unit/test_exp001_maintenance.py:161` — `assert live == 468 and CAP - live == 32` — an exact equality, unweakened, with the hermetic fixture-tree assertions correctly left at 336. **B6 §10 row 5 is closed. DEC-035 re-opens nothing and re-decides nothing about the ledger.**

## 10 — CITED versus RE-DERIVED: the B6 artifacts are frozen as evidence

Applying the DEC-032 §3 discriminator: `docs/research/DAY37_EXP008_B6_IMPLEMENTATION_REPORT.md` and `results/evaluation/exp008_b6_implementation.json` **CITE** figures as of 2026-09-18 — `cumulative_charge: 462`, `remaining_headroom: 38`, `decisions_md_fingerprint: 7579e551…`, and a `pre_existing_failures` entry for the ledger test that has since been repaired. They do not re-derive anything from the live tree.

**They are therefore CITED historical records and are NOT edited, NOT regenerated and NOT corrected.** This restates DEC-032 §8's ruling verbatim in effect: *"The B6 report and `results/evaluation/exp008_b6_implementation.json` are **not** regenerated: they are correct as B6-time records and their historical status is preserved."*

**The current canonical ledger is DEC-033's: charged 468 of 500, remaining 32.** No reader may take the B6 JSON's `462/38` as current headroom. This entry changes no ledger figure and charges 0.

## 11 — WHAT IS DECIDED

1. **B6 is RESOLVED.** The EXP-008 A3/A4 implementation at HEAD `c2e980a` — `src/sparkrl/training/exp008.py`, the additive `src/sparkrl/rl/reward.py` extension, `configs/exp008.yaml`, the two `__init__` re-export blocks, and the three zero-Spark test files — is **ADOPTED** as the implementation DEC-030 §15 gate item (3) requires. DEC-030 §15's *"with green zero-Spark tests"* condition is **satisfied**: 103/103 passed, exit 0, 0.24 s, re-run for this entry (§4).
2. **Adoption is retrospective**, following DEC-018 Decision E and DEC-032 §8: the code was written and committed before any decision covered it. It is adopted as operator-authorized Day-37 work, on the evidence of §§3–8, not ratified blindly.
3. **DEC-030 §12 fields 1, 13 and 14 are explicitly DEFERRED** to the methodology/authorization decisions and are recorded as **NOT** enforced by the configuration layer (§6). Fields 2–12 and 15–17 are enforced fail-closed per arm.
4. **`validate_configuration()` passing is not authorization and not methodological completeness.** Recorded as binding on gate item (4).
5. **The DEC-030 §3.2 multi-term-removal classification stands** and is restated: A3-time-only removes the task-imbalance AND spill-waste terms simultaneously; no analysis may attribute a difference to a single removed term.
6. **B6 report §10 row 5 is discharged** by DEC-032 §8 as amended by DEC-033 (§9).
7. **The B6 report and JSON are frozen as CITED evidence** and are not regenerated (§10).

## 12 — Authorized but NOT performed here (following DEC-025 §11 / DEC-032 §6)

A **validator-only, minimal, local** repair is AUTHORIZED for a **separate later task**: `scripts/validate_day31.py:1015` currently reads `"exp008_b6_implementation.json": "DEC-031",` inside `AUTHORIZED_ARTIFACTS`, while DEC-031 §13 states *"It is **not** the B6 implementation decision."* Once DEC-035 is at HEAD, the correct attribution for that artifact is **DEC-035**.

**The repair MUST:** change only the attribution string for that one artifact key; leave `exp008_methodology_freeze.json` → `DEC-030`, `exp008_preflight_audit.json` → `DEC-030` and `exp008_budget_reconciliation.json` → `DEC-031` untouched; and preserve `_authorized()`'s requirement that the named decision be present at HEAD.

**The repair MUST NOT:** weaken, delete, skip or bypass any check; add any artifact to the allowlist; change any ledger, manifest, result or budget artifact; or alter authorization state. **It is NOT performed by this entry**, and this entry does not modify `scripts/validate_day31.py`.

## 13 — What this decision deliberately does NOT decide

* **EXP-008 execution authorization** — gate item (4). Not granted, not prepared, not implied.
* **DEC-030 §12 fields 1–14 and 16–17** — every one remains UNFROZEN and REQUIRES A SEPARATE DECISION. Naming fields 1, 13 and 14 in §6 **resolves none of them**; it records that the code will not catch them.
* **Field 15 / the A3-R4-log-ratio arm** — its eight unresolved semantics are not frozen here. The arm can never become configuration-complete as the code stands; either a decision freezes all eight, or field 1 drops it from the executed arm set. DEC-035 does neither.
* **The PLAN-internal scope/envelope tension.** `docs/PLAN.md:315` registers EXP-008 at **~300** executions; the canonical remaining headroom is **32** (DEC-033). DEC-031 §10 recorded this as an unresolved governance dependency and DEC-011 held it to be an internal-PLAN conflict DEC-010's precedence rule cannot arbitrate. **DEC-035 does not resolve it, does not raise the cap, does not amend PLAN and does not de-scope EXP-008.** No amount of implementation creates executions that do not exist.
* **Statistical governance** (§12 field 14) — DEC-030 §8's position stands: until a governing DEC exists, any EXP-008 analysis that ever runs is descriptive-only with no invented thresholds.
* **The zero-live manifest counting rule** (DEC-032 §7.3) — still UNRESOLVED; untouched here.
* **`scripts/validate_day30.py`** and every other validator beyond the one attribution line in §12.
* **DEC-034**, whatever it may be. Not read, not assumed, not depended on.

## 14 — Non-authorization firewall (explicit)

| Item | State recorded by this entry |
|---|---|
| **EXP-008 execution authorization** | **FALSE / NO** |
| **A5** | **DISABLED / excluded** (DEC-011; re-affirmed DEC-016 §7, DEC-023 §2, DEC-024 A5 row, DEC-025 §7, DEC-030 §9); `configs/rl.yaml` `gamma` stays `0.0` |
| **TEST** | **NOT AUTHORIZED** — no TEST queue, specification or ledger is created; the TRAIN-only guards are strengthened by adoption, never relaxed |
| **Implementation authorization (B6)** | **GRANTED by this entry, for implementation only** — A3/A4 are IMPLEMENTED-AND-ADOPTED, and remain **UNAUTHORIZED IN EXECUTION** |
| **SC6 cap** | **500 — unchanged, not raised** (`docs/PLAN.md:45`; `configs/rl.yaml:17`) |
| **Canonical ledger** | **468 charged / 32 remaining** (DEC-033) — restated, not re-derived, not changed |
| **`docs/PLAN.md`** | **UNCHANGED** — no line edited |
| **Historical decisions** | **UNCHANGED** — DEC-001 … DEC-026, DEC-030, DEC-031, DEC-032, DEC-033 are not rewritten; this entry is appended, never substituted |
| **Spark / training / TEST executions performed by this entry** | **0 / 0 / 0** |

## 15 — Evidence and fingerprints (read-only; nothing listed was modified by this entry)

| Source | Role | SHA256 |
|---|---|---|
| `src/sparkrl/training/exp008.py` | the adopted scope layer (36 504 bytes) | `0a2252b378dda0a630106795ef13287eda86d3a50c0e294ef26f3768bc54ceba` |
| `configs/exp008.yaml` | the inert fail-closed configuration artifact | `7b0f3999c08398df2cb956dceed312b32706fc3dca1f33815663bbedbb4cd2d4` |
| `src/sparkrl/rl/reward.py` | the one changed governed source; additive A3 registry | `e98a1351c42fc2303a4590afc62ed7d485754c43176b8f1b86b57fd77b67fd95` |
| `tests/unit/test_exp008_scope.py` | 50 zero-Spark tests | `815192962246cbfbb3bd8a1e9676fb09193e2c5419f137701bf7e6b703167d8c` |
| `tests/unit/test_exp008_action.py` | 32 zero-Spark tests | `e781ca7d10c92121c081f078ca90a81b8150d52c683b05641c71485178535443` |
| `tests/unit/test_exp008_reward.py` | 21 zero-Spark tests | `20c2d45f5144fe709808bde2e626b9d217110975f83faa5662eb575f13e75a35` |
| `docs/research/DAY37_EXP008_B6_IMPLEMENTATION_REPORT.md` | adopted evidence — **retained, not regenerated** | `65cbe165fd05e1475f3d66bdd3d9ea971b6366bf85c644a4510c4277e87f0541` |
| `results/evaluation/exp008_b6_implementation.json` | adopted evidence — **retained byte-identical** | `b6cf45148fcb8d45902b9b81fef86efe5a484886e5dab3cc13cbe7c4f93871b2` |
| `src/sparkrl/rl/action.py` | reused verbatim | `580cf010f17b2cb0f7c3b7967d4fb560b7f973028e8a1909123e7d337f4c0528` (**unchanged**) |
| `src/sparkrl/agent/q0.py` | no Q0 builder added | `7d2ffb0c33fc4349a71d3e064781927425092ff86be2eeed595705b3111de195` (**unchanged**) |
| `src/sparkrl/agent/q_learning.py` | 12-wide rows unchanged | `1c5fab897f8f652b90cd9011b1d84846459f041d31565c9652c4edd578d9bb31` (**unchanged**) |
| `src/sparkrl/training/loop.py` | **no EXP-008 wiring** | `b513238d5148a16cc8e39283526082b0c199fee5ad7a00326d95f4ad3983a611` (**unchanged**) |
| `src/sparkrl/training/ablation.py` | EXP-007 layer, pattern reused only | `69ab9c40e1688405b8b6f795783ada7fbf26c753bacb76d0aba215b7fb5b216a` (**unchanged**) |
| `docs/PLAN.md` | SC6 line 45; EXP-008 envelope line 315 | `db5e82102833efe6bab8db1adaf1b35ad195faf385e63ab296d50562e349ee63` (**unchanged**) |
| `configs/rl.yaml` | `gamma: 0.0`; `live_execution_cap: 500` | `8ca70d6dd7df68841c409a4441dc538616206bccea7877b28c73df20e6428b80` (**unchanged**) |
| `configs/reward.yaml` | frozen R3 weights | `a52131d5a0de63ef06d3dd5b181f1bbeda326df3ffffbd2ae1c69ed96571db1b` (**unchanged**) |
| `docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md` | DEC-030 identity preserved | `ec487bf2a84a9c1a6f506bdd83c71b7c7bb7ae2cceaf7e761f000c7201912a5a` (**unchanged**) |
| `docs/research/DEC_031_EXP008_SC6_BUDGET_RECONCILIATION.md` | DEC-031 | `af5c18216c6fdbcba86c891934a4b2d1026a32c4e2ada91eee91f7c8ab12852c` (**unchanged**) |
| `docs/research/DEC_032_DAY31_VALIDATOR_LEDGER_RECONCILIATION.md` | DEC-032 | `142bcd86b54ad7c369e8f10c7914c07372e63b93520e8e2780e2a68c25ad506d` (**unchanged**) |
| `docs/research/DEC_033_GOVERNANCE_RECONCILIATION.md` | DEC-033 — canonical 468/32 | `3e6d0d7c4b5359990ea6ac6766e226d860c5fea2fb0e8639cc73fff645932b21` (**unchanged**) |
| `scripts/validate_day31.py` | the §12 attribution line — **NOT MODIFIED by this entry** | out of scope; repair authorized for a later task |
| `DECISIONS.md` | this entry appended; every prior byte intact | `849197ed5b9d2ca192db68e14bef80916d2ef55af48b5105a3f39301e919953e` **before** this append |

Repository state at recording: branch `main`, HEAD `c2e980a` (*"gov(DEC-033): Option A — the six 2026-09-19 smoke executions are charged; ledger 468/32"*), working tree **clean** (`git status --porcelain` empty).

## 16 — Validation of this entry (read-only, zero Spark)

| Check | Method | Result |
|---|---|---|
| DEC-035 identifier free | heading scan of `DECISIONS.md` + repository-wide search for `DEC-034`/`DEC-035` | PASS (both unoccupied) |
| `DECISIONS.md` appended only | prior bytes intact; append-only | PASS |
| DEC-030 / DEC-031 / DEC-032 / DEC-033 artifacts unchanged | SHA256 re-checked (§15) | PASS |
| `docs/PLAN.md`, `configs/rl.yaml`, `configs/reward.yaml` unchanged | SHA256 re-checked | PASS |
| Zero-Spark EXP-008 tests green | `python -m pytest tests/unit/test_exp008_{scope,action,reward}.py` | **PASS — 103 passed, 0.24 s, exit 0** |
| Only `reward.py` changed among DEC-030-fingerprinted sources | SHA256 of action/q0/q_learning/loop/ablation vs recorded values | PASS |
| No EXP-008 runner exists | `loop.py` byte-identical; module imports no `pyspark`/`env`/`subprocess` | PASS |
| §12 field coverage measured, not assumed | read-only construction of a 15-field-complete config; `unresolved_fields()` → `()` with `statistical_governance=None` | PASS (15/18; 16/18 for A4) |
| A5 inert | four independent refusals + unchanged `gamma: 0.0` | PASS |
| No execution authorized | §13, §14 | PASS |
| Ledger unchanged | 468/32 restated from DEC-033; charged by this entry: **0** | PASS |
| Full unit suite / validator chain | **NOT RE-RUN by this entry** — deferred to gate item (4)'s clean preflight | NOT ASSERTED |
| Spark / training / TEST executions performed | — | **0 / 0 / 0** |

**Status.** **DECIDED.** DEC-030 §15 gate-chain item **(3) is SATISFIED**: the EXP-008 A3/A4 implementation is **ADOPTED** as the B6 resolution on green zero-Spark tests (**103/103, exit 0**), with DEC-030 §12 fields **1, 13 and 14** recorded as **NOT** fail-closed in the configuration layer and **explicitly deferred**, and with fifteen fields (sixteen for A4) enforced required-but-unset. One validator-only attribution repair is **AUTHORIZED for a separate later task and NOT performed here**. `EXP-008 execution authorization = NO`. `A5 = DISABLED`. `TEST = NOT AUTHORIZED`. `SC6 cap = 500, not raised`. `Canonical ledger = 468 charged / 32 remaining (DEC-033)`. `docs/PLAN.md = UNCHANGED`. Historical decisions (DEC-001 … DEC-026, DEC-030, DEC-031, DEC-032, DEC-033) = **UNCHANGED**. Supervisor counter-signature: **PENDING** (conventional expectation only; never simulated; not a prerequisite under DEC-018 Decision A). **NO SUPERVISOR HAS REVIEWED THIS ENTRY.** **This entry performs 0 Spark executions and trains nothing.**

*End of DEC-035.*

---

*Standalone companion artifact. The authoritative log entry is the appended DEC-035 section of DECISIONS.md; this document carries the same decision content, self-contained (the DEC-031/DEC-032 convention).*

**Ledger supersession note (appended 2026-09-20, before signature).** This entry was drafted against the then-current ledger **468 / 32** (DEC-033). Five completed smoke TRAIN executions dated 2026-09-20 07:37-07:56Z were discovered afterwards and classified by **DEC-038**, making the canonical ledger **483 / 17** at signature. The figure is corrected here rather than in the body, so the drafting chronology stays visible. No conclusion in this entry depends on the difference: it adopts an implementation and charges nothing; EXP-008 execution authorization remains NO either way.
