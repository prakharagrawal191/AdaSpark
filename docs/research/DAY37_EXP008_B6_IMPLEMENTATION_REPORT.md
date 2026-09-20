# DAY37 — B6: EXP-008 A3/A4 IMPLEMENTATION REPORT

**Task:** B6 — implementation of the already-governed EXP-008 A3/A4 methodology.
**Date:** 2026-09-18
**Repository HEAD:** `5cf0cf850f022750fa7df734328f6807e3546ee9`
**Scope:** implementation support only. **No experiment was executed, specified, scheduled or authorized.**
**Machine artifact:** `results/evaluation/exp008_b6_implementation.json` (regenerated deterministically by `scripts/generate_b6_implementation.py`).

> **Spark executions = 0. Training executions = 0. TEST executions = 0.**
> **EXP-008 execution authorization = NO** — unchanged by this task, and no code path added here can change it.

This report is **not a decision**. DEC-030 §15 gate-chain item (3) expects a separate decision entry to record B6; this document and its JSON supply the evidence that item needs, nothing more. No DEC number is claimed, no authorization is granted, and no methodological field is frozen here.

---

## 1. Authority and precedence

Applied in this order, with the current decisions overriding any older audit text:

1. `docs/PLAN.md`
2. `DECISIONS.md` through DEC-031
3. `docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md` (DEC-030 — methodology freeze)
4. `docs/research/DEC_031_EXP008_SC6_BUDGET_RECONCILIATION.md` (DEC-031 — SC6 budget)
5. EXP-008 preflight/budget artifacts
6. `experiments/registry.csv`
7. existing source implementation
8. tests

Where the Day-37 preflight audit disagrees with DEC-030/DEC-031 — notably its "illustrative parity shape" of 2 seeds × 35 episodes × 7 cells, and its `379` / `121` / `−89` budget bases — the decisions win and the audit figures were treated as non-authoritative evidence. Nothing from that audit entered the implementation as a default.

**Governing budget facts (DEC-031 §§3–4, 8), used read-only:** SC6 cap 500; cumulative charge 462; remaining headroom 38. B6 charges **0**.

---

## 2. Phase 1 — repository audit findings

| Component | Pre-B6 state | Consequence for B6 |
|---|---|---|
| `src/sparkrl/rl/reward.py` | One frozen formula (`R3`), weights validated against `configs/reward.yaml` | Needed an **additive** variant registry; R3 must stay byte-behaviour identical |
| `src/sparkrl/rl/action.py` | `MODE12`, `MODE4`, `MODE4_SUBSET = {0,3,6,9}`, `ActionMapper` with pre-execution rejection | **Already complete.** A4 reuses it verbatim; not one line was changed |
| `src/sparkrl/agent/q_learning.py` | 12-wide Q rows always; `mode4` restricts *selection* only; ties break to lowest index | **Already complete.** No Q-table change needed for A4 |
| `src/sparkrl/agent/q0.py` | `q0-exp002/v1` (primary) and `q0-neutral/v1` (EXP-007 A1/A2) | No new Q0 builder may be added (DEC-030 §5); B6 added none |
| `src/sparkrl/rl/state.py`, `env.py` | `state-v1`/`v1.5`/`v2`; env already accepts `action_mode` and `state_schema` | No change needed |
| `src/sparkrl/training/loop.py` | Main study + EXP-007 A1/A2 variants | **Deliberately not touched** — see §7 |
| `src/sparkrl/training/ablation.py` | EXP-007 scope/budget layer (DEC-023/025) | Pattern reused for the EXP-008 scope layer |
| `configs/rl.yaml`, `configs/reward.yaml` | Frozen hyperparameters and R3 weights | **Unchanged**, both verified byte-identical |

**Conclusion:** the only genuine implementation gaps were (a) the A3 reward variants and (b) a fail-closed representation of the DEC-030 arm scope. A4's action machinery already existed as pre-authorized Plan-B support, so B6 reuses it rather than duplicating it.

A partial B6 implementation (`src/sparkrl/rl/reward.py`, `src/sparkrl/training/exp008.py`, `configs/exp008.yaml` and the two `__init__.py` re-export blocks) was already present, uncommitted, in the working tree when this task began. It was audited line-by-line against DEC-030/DEC-031 rather than assumed correct; §§3–7 state the verification. This session additionally closed one error-taxonomy gap (§6), added the entire zero-Spark test suite, and produced this report and its JSON.

---

## 3. Phase 2 — A3 reward support

Implemented additively in `src/sparkrl/rl/reward.py`. `RewardCalculator.__init__` gained a **keyword-only** `formula` parameter defaulting to `R3`, so every existing caller is unchanged.

### 3.1 `R3` — frozen comparator, unchanged

- Default construction, default weights (`FROZEN_WEIGHTS`, validator-enforced against `configs/reward.yaml`), default `formula_id`, and every computed term are identical to the pre-B6 code.
- `configs/reward.yaml` is byte-identical (`a52131d5…db1b`).
- `RewardCalculator()` and `RewardCalculator(formula="R3")` produce identical `Reward.to_dict()` payloads.
- All 14 pre-existing `tests/unit/test_rl_reward.py` cases still pass unmodified.

### 3.2 `A3-time-only` — implemented exactly

```
R = 1.0 * clip((T_ref - T) / T_ref, -1, +1)        failure: R = -1.0 exactly
```

Frozen coefficients (`TIME_ONLY_WEIGHTS`): `w_time=1.0, w_task=0.0, w_spill=0.0, w_failure=1.0, clip=[-1,+1]`. They are module constants, never read from `configs/reward.yaml` — that file freezes the primary R3 formula and must not acquire EXP-008 keys.

**Classification, documented in the code and asserted by tests:** time-only is a **MULTI-TERM REMOVAL** from R3. The task-imbalance term **and** the spill-waste term are removed **simultaneously**. It is explicitly **not** a one-factor ablation, and no future analysis may attribute a difference against R3 to a single removed term.

The two removed inputs (`task_duration_cv`, `disk_spill_bytes`) are **removed inputs, not missing facts**: they are never read, so they never appear in `Reward.terms` and never appear in `Reward.missing`. Everything else is inherited verbatim from frozen R3 — the failure rule (timeout counts as failure), the `[-1,+1]` clipping, the `T_ref > 0` hard error and the "a usable run must carry its timing" rule.

### 3.3 `A3-R4-log-ratio` — registered, deliberately not executable

`R4 = -ln(T / T_ref)` is registered in `REGISTERED_FORMULAS` and **absent** from `IMPLEMENTED_FORMULAS`. Constructing a calculator for it raises `IncompleteFormulaError` **before any computation and before any Spark execution**. The refusal message names every unresolved semantic DEC-030 §3.4 left open:

`failure_rule`, `coefficients`, `clipping`, `edge_T_le_0`, `edge_T_ref_le_0`, `edge_failures_timeouts`, `edge_missing_execution_time`, `term_structure_vs_time_only`.

Guarantees asserted by test: R3 behaviour is **never** substituted; clipping is **never** silently applied; no failure transformation is invented; and **the enum existing does not make R4 executable**. The `A3-R4-log-ratio` arm can never become configuration-complete.

---

## 4. Phase 3 — A4 mode4

**No new action logic was written.** `sparkrl.training.exp008` binds `A4_ACTION_SUBSET is MODE4_SUBSET` and derives every description from the frozen `ActionMapper`. `src/sparkrl/rl/action.py` is byte-identical (`580cf010…c0528`).

Verified against DEC-030 §4.3 (test constants transcribed from the decision table, not from the code):

| Index | Parallelism | Shuffle partitions | Config name |
|---|---|---|---|
| 0 | 2 (`local[2]`) | 16 | `G-p2-sp16` |
| 3 | 2 (`local[2]`) | 128 | `G-p2-sp128` |
| 6 | 4 (`local[4]`) | 64 | `G-p4-sp64` |
| 9 | 8 (`local[8]`) | 32 | `G-p8-sp32` |

- `mode12` unchanged: all 12 configurations, frozen order `grid_index = parallelism_index * 4 + shuffle_index`, unchanged identities.
- `mode4` exposes exactly `(0, 3, 6, 9)`; `allowed_actions()` is **not** `(0,1,2,3)` — nothing is compacted.
- Original indices preserved: for every subset action, `name`, `grid_index`, parallelism and shuffle partitions are identical under mode4 and mode12, so an action means the same thing in a mode4 log, manifest or policy artifact as in a mode12 one.
- `{1,2,4,5,7,8,10,11}` are rejected with `InvalidAction` **before** any Spark execution; each remains valid under mode12.
- Malformed actions (`-1`, `12`, `True`, `1.5`, `"0"`, `None`) are rejected in both modes.
- Tie-breaking semantics preserved: greedy selection over the subset still breaks ties to the **lowest** frozen index (verified at 3 vs 6 vs 9 → 3).
- Selection restriction, not projection: with a Q row whose global maximum sits at index 1, a mode4 agent selects 6 and the stored row remains 12 values wide.
- `guard_action_mode_for_arm` locks the `A4-mode4` arm to `mode4` — the arm *is* the action-availability change, so `mode12` is refused for it.

---

## 5. Phase 4 — Q0 handling

DEC-030 §5 did **not** freeze the per-arm Q0 source. B6 therefore implements **provenance and refusal**, never construction.

**Nothing was invented.** B6 adds no Q0 builder of any kind — `sparkrl.training.exp008` contains no `build_*q0*` function, and `src/sparkrl/agent/q0.py` is byte-identical (`7d2ffb0c…de195`). No projection, no pooling, no row collapsing, no invented mode4 mapping, no new learned Q0, and no TEST-derived Q0 exists anywhere in the change.

| Arm | Admissible Q0 sources | Behaviour |
|---|---|---|
| `A3-R3-frozen` | `q0-exp002/v1`, `q0-neutral/v1` | source **must be declared explicitly**; unset → `Exp008IncompleteError` |
| `A3-time-only` | `q0-exp002/v1`, `q0-neutral/v1` | same |
| `A3-R4-log-ratio` | *(none)* | **no Q0 is admissible** — none was ever computed under R4, so constructing one would be post-hoc construction |
| `A4-mode4` | `q0-exp002/v1`, `q0-neutral/v1` | same; rows stay **12-wide**, `{0,3,6,9}` address the same columns of the same row |

- `guard_q0_projection(True)` always raises `Exp008Q0Error`; `q0_projection` is `false` in every shipped config block and in every provenance record.
- `guard_q0_rows` / `guard_q0_for_mode` reject any table whose rows are not 12 wide — a 4-wide "projected" mode4 table is precisely what must never exist, and it is refused.
- `guard_q0_source` refuses any source outside the two existing frozen ones, and refuses `None` as *required-but-unset* rather than defaulting.
- The primary-study Q0 (`q0-exp002/v1`) and the EXP-007 neutral Q0 (`q0-neutral/v1`) are untouched in code and in behaviour.

**A4's structural compatibility with the existing 12-wide Q0 follows DEC-030 §5.4's "EXISTING FROZEN MAPPING" verdict.** It is implementation support only; it is **not** an authorized experimental configuration, and the choice of which frozen Q0 source A4 uses remains an open decision (DEC-030 §12 field 2).

---

## 6. Phases 5–6 — configuration schema and guards

`configs/exp008.yaml` (new, inert — nothing in the primary study, the baselines, EXP-005/006/007 or the training loop loads it) represents the four DEC-030 arms. Frozen values are stated: `experiment_id`, `schema_version`, `dataset_seed: 0`, `split: train`, `q0_projection: false`, each A3 arm's own reward formula, and `action_mode: mode4` for A4. **Every DEC-030 §12 unresolved field is an explicit `null`.**

`Exp008ArmConfig` mirrors that: frozen fields carry frozen values, unresolved fields are `None` and **required-but-unset**. `validate_configuration()` fails closed with `Exp008IncompleteError` while any of them is unset, and the test suite proves this field by field — dropping any single required field makes the configuration refuse.

Guards added, all firing **before** any Spark execution:

| Guard | Refuses |
|---|---|
| `guard_split` / `guard_cell` / `guard_train_cells` | any TEST or VALIDATION cell (`F4_ski`, scale `large`, seed 4, seed 3) and any non-TRAIN split |
| `guard_metrics` | any metrics mapping carrying TEST provenance (`split`, `test_family`, `test_scale`, `test_seed`) |
| `guard_a5` | the `A5` arm, `multi_step=True`, and any `gamma != 0.0` |
| `build_reward_calculator` | unregistered variants; R4 via `IncompleteFormulaError` |
| `guard_q0_source` / `guard_q0_projection` / `guard_q0_rows` | unsupported Q0 provenance and every forbidden projection |
| `ActionMapper._validate` / `guard_action` / `guard_action_mode_for_arm` | non-mode4 actions; a non-mode4 mode for the A4 arm |
| `arm_config_from_mapping` | unknown configuration keys (closed schema) and wrong value types |

One gap was closed in this session: `guard_cell` previously let a cell outside the frozen family/scale/seed domain surface a bare `ValueError` from `split_of`. It now re-raises as `Exp008ConfigError` (itself a `ValueError`, so strictly backward compatible), which closes the error taxonomy — every refusal on an EXP-008 path is now catchable as `Exp008Error`.

**No authorization mechanism exists.** `EXECUTION_AUTHORIZED` is a module constant `False`, `EXECUTION_AUTHORIZATION` is `"NO"`, and `SPARK_EXECUTIONS = TRAINING_EXECUTIONS = TEST_EXECUTIONS = 0`. Nothing writes them. Passing validation is explicitly **not** authorization — a test asserts exactly that. Authorization remains an external governance decision.

**Defaults preserved.** No existing default value changed: reward default `R3`; `action_mode` default `mode12`; `gamma` 0.0; `live_execution_cap` 500. Main training, A1, A2, baselines, EXP-005, EXP-006, the Plan-B guards and the A5-disabled guard all behave exactly as before.

---

## 7. Phase 7 — manifest / provenance

`Exp008ArmConfig.to_provenance()` emits a record covering every field the task requires: experiment id, arm/variant, reward variant, action mode, action subset, state schema, Q0 source, Q0 variant, Q0 projection status, Q0 row width, agent seeds, dataset seed, TRAIN/validation/TEST split, T_ref source and fingerprint, alpha, gamma, epsilon schedule, episode horizon, early-stop configuration, execution-budget configuration, AQE condition, live-execution charging rule, statistical governance and implementation/code fingerprint.

**No unresolved value is fabricated.** Each is emitted as an explicit `null` *and* listed in `unresolved_fields`, following the project's existing convention (the EXP-007 neutral-Q0 provenance uses the same `None`-plus-explicit-note shape). Every record also carries `execution_authorized: false` and `execution_authorization: "NO"`.

**Deliberately not done:** EXP-008 is **not** wired into `src/sparkrl/training/loop.py`. Doing so would require choosing a seed set, a cell set, a horizon and an early-stop rule — every one of which DEC-030 §12 leaves unresolved — so any wiring would have had to invent methodology. The provenance record is instead produced by the configuration layer, and `loop.py` is byte-identical (`b513238d…83611`). This is why B6 delivers no EXP-008 runner: a runner cannot exist without the decisions DEC-030 deferred.

---

## 8. Phase 8 — tests (zero Spark)

103 new tests across three files, all passing. No test launches Spark; no integration test was run.

| File | Tests | Covers |
|---|---|---|
| `tests/unit/test_exp008_reward.py` | 21 | R3 unchanged (default construction, weights, explicit-vs-default equality, all four terms, failure −1.0); time-only exact formula over 6 timings; time-only failure exactly −1.0; time-only carries **no** task-imbalance term and **no** spill term and reports them in neither `terms` nor `missing`; time-only is provably insensitive to CV/spill while R3 is provably sensitive; T_ref and missing-timing rules retained; R4 registered; R4 construction refused naming every unresolved semantic; R4 never falls back to R3 or time-only |
| `tests/unit/test_exp008_action.py` | 32 | mode12 unchanged (12 configurations, frozen grid order); mode4 subset exactly `{0,3,6,9}`; all four mappings against the DEC-030 table; original indices preserved and never renumbered; stable config names for logs/manifests; each of the 8 non-mode4 actions rejected while still valid under mode12; malformed actions rejected in both modes; A4 locked to mode4; 12-wide rows with restricted selection; exploration confined to the subset; lowest-index tie-breaking; mode12 agent unaffected |
| `tests/unit/test_exp008_scope.py` | 50 | arm set; per-arm reward binding; R4 arm can never complete; contradicting reward refused; shipped config incomplete for every arm; **each** required field individually fails closed; Q0 projection forbidden; admissible Q0 sources; R4 admits no Q0; 12-wide row enforcement; same-column addressing; primary Q0 untouched and no new builder; TRAIN-only split; TEST/VALIDATION cells and metrics refused; malformed cells; A5 arm/multi-step/gamma refused and absent from the scope summary; seed validation without inventing a seed set; closed config schema; deterministic loading; provenance completeness; no fabricated unresolved value; frozen dataclass; zero-execution declarations; no Spark/runner/subprocess import in the module |

### Regression

| Suite | Before B6 | After B6 |
|---|---|---|
| `tests/unit` (full) | 559 passed, 1 failed, 1 skipped | **662 passed, 1 failed, 1 skipped** |

Specifically re-verified green: `test_rl_reward.py` (14), `test_rl_action.py` (8), `test_rl_agent.py` (11), `test_rl_q0.py` (8), `test_rl_state.py` (18), `test_rl_training.py` (49), and the EXP-007 A1/A2 suites `test_exp007_parity.py` (16), `test_exp007_q0.py` (10), `test_exp007_scope.py` (17), `test_exp007_state.py` (32).

### The one failing test — pre-existing, not B6

`tests/unit/test_exp001_maintenance.py::test_exp003_or_exp005_are_never_charged_to_sc6` fails **identically before and after B6**. It asserts the SC6 ledger reads `336` live / `164` remaining; the real ledger now reads `462` / `38` because EXP-007 executed 126 charged live TRAIN executions (`336 + 126 = 462`) — exactly the figure DEC-031 §§3–4 record as authoritative.

Evidence that it is unrelated to B6: the test reads only `scripts/validate_day31.py` and `results/training/**/manifest.json`; `validate_day31.py` imports nothing from `sparkrl`; and neither path is in the B6 changed-file set.

**Not repaired here.** Re-pinning a governance ledger constant to `462`/`38` is a DEC-031 follow-up, not an implementation-only change, and silently editing a governance assertion inside B6 would be exactly the kind of drift this task forbids. It is reported as an open item in §10.

---

## 9. Phase 9 — research-drift audit

### 9.1 Files changed by B6

| File | Change | Frozen rule it implements |
|---|---|---|
| `src/sparkrl/rl/reward.py` | modified | DEC-030 §3 — additive A3 registry; R3 unchanged; time-only exact; R4 registered-but-refused |
| `src/sparkrl/rl/__init__.py` | modified | re-exports only; no behaviour |
| `src/sparkrl/training/__init__.py` | modified | re-exports only; no behaviour |
| `src/sparkrl/training/exp008.py` | created | DEC-030 §§3–6, 9, 12 — arm registry, fail-closed schema, Q0 policy, TRAIN-only and A5 guards, provenance |
| `configs/exp008.yaml` | created | DEC-030 §12 — every unresolved field as an explicit `null` |
| `tests/unit/test_exp008_reward.py` | created | zero-Spark proof of §3 |
| `tests/unit/test_exp008_action.py` | created | zero-Spark proof of §4 |
| `tests/unit/test_exp008_scope.py` | created | zero-Spark proof of §§5, 6, 9, 12 |
| `scripts/generate_b6_implementation.py` | created | deterministic generator for the B6 artifact |
| `docs/research/DAY37_EXP008_B6_IMPLEMENTATION_REPORT.md` | created | this report |
| `results/evaluation/exp008_b6_implementation.json` | created | the B6 machine artifact |

Other files carrying uncommitted modifications (`agent/q0.py`, `agent/q_learning.py`, `rl/state.py`, `training/loop.py`, `training/ablation.py`, `scripts/run_exp005.py`, `scripts/run_training.py`, `DECISIONS.md`, `docs/architecture/ARCHITECTURE_FREEZE.md` …) are **pre-B6 EXP-005/EXP-007/DEC-031 work**, not touched by this task.

### 9.2 Nothing frozen was altered — verified by fingerprint

| File | SHA256 | Expectation recorded in |
|---|---|---|
| `docs/PLAN.md` | `db5e8210…ee63` **unchanged** | DEC-031 §15 |
| `configs/rl.yaml` | `8ca70d6d…8b80` **unchanged** | DEC-031 §15 |
| `configs/reward.yaml` | `a52131d5…db1b` **unchanged** | DEC-030 freeze JSON |
| DEC-030 artifact | `ec487bf2…12a5a` **unchanged** | its own `dec030_fingerprint` |
| DEC-031 artifact | `af5c1821…852c` **unchanged** | not modified by this task |
| `results/evaluation/exp008_budget_reconciliation.json` | `bd67da17…96c5` **unchanged, byte-identical** | DEC-031 §15 |
| `results/evaluation/exp007_analysis.json` | `e010072f…3b68` **unchanged** | EXP-007 output |
| `src/sparkrl/rl/action.py` | `580cf010…c0528` **unchanged** | DEC-030 freeze JSON |
| `src/sparkrl/agent/q0.py` | `7d2ffb0c…de195` **unchanged** | DEC-030 freeze JSON |
| `src/sparkrl/agent/q_learning.py` | `1c5fab89…bb31` **unchanged** | DEC-030 freeze JSON |
| `src/sparkrl/rl/state.py` | `3ce6ee04…bda0` **unchanged** | DEC-030 freeze JSON |
| `src/sparkrl/rl/env.py` | `66ff0497…1975` **unchanged** | DEC-030 freeze JSON |
| `src/sparkrl/training/loop.py` | `b513238d…83611` **unchanged** | DEC-030 freeze JSON |
| `src/sparkrl/training/ablation.py` | `69ab9c40…b5216a` **unchanged** | DEC-030 freeze JSON |

`src/sparkrl/rl/reward.py` is the **only** DEC-030-fingerprinted source file B6 changed. Its DEC-030 fingerprint `0c5e67f4…9798` describes the pre-B6 state and remains a correct historical record; the current file is `e98a1351…fd95`. **`results/evaluation/exp008_methodology_freeze.json` was deliberately not regenerated** — regenerating it would rewrite a recorded decision artifact.

### 9.3 Could anything change primary-study behaviour?

Reviewed and answered **no**, on these grounds:

- `RewardCalculator`'s new `formula` parameter is keyword-only and defaults to `R3`; no existing call site passes it.
- `Reward.formula_id` already existed with default `R3`; the R3 code path is unchanged.
- `TIME_ONLY_WEIGHTS` is a separate constant; `FROZEN_WEIGHTS` and `configs/reward.yaml` are untouched.
- `sparkrl.training.__init__` now imports `exp008` eagerly. That module reads no file at import time, starts no session and imports neither `pyspark` nor `sparkrl.rl.env` — asserted by test.
- `configs/exp008.yaml` is loaded by nothing except the EXP-008 layer and its tests.
- The env/agent/loop/Q0/state code is byte-identical, so every primary, A1/A2, baseline, EXP-005 and EXP-006 path is untouched.

### 9.4 New unresolved fields introduced by B6

**None.** B6 introduces no new methodological field. It gives the 18 fields of DEC-030 §12 an explicit, schema-safe, fail-closed representation and adds nothing to the list.

---

## 10. Blockers and required decisions (not invented here)

| # | Required decision | Why it blocks |
|---|---|---|
| 1 | **The B6 implementation decision itself** (DEC-030 §15 gate item 3) | This report and its JSON are evidence, not a decision entry. No DEC number is claimed by B6. |
| 2 | **R4 complete specification** (DEC-030 §12 field 15) | Until failure rule, coefficients, clipping, `T ≤ 0`, `T_ref ≤ 0`, missing timing, timeout semantics and term structure are frozen, `A3-R4-log-ratio` cannot be constructed, let alone executed. |
| 3 | **Every DEC-030 §12 field (1–18)** | Q0 source per arm, state schema, A3 action schema, A4 control-pairing reward, seeds, TRAIN cells, horizon, early-stop, AQE confirmation, warm-up, cache, alpha/gamma/epsilon deviations, statistical governance, charging rule. Each is required-but-unset; the configuration refuses until each is supplied. |
| 4 | **EXP-008 execution authorization** | Remains **NO** (DEC-030 §11; DEC-031 §14). It is external to the code and cannot be granted by it. |
| 5 | **Stale ledger assertion in `test_exp001_maintenance.py`** | Pre-existing failure (§8). Repairing it means re-pinning a governance constant from `336`/`164` to DEC-031's `462`/`38` — a DEC-031 follow-up, outside implementation-only scope. |

No decision was invented in code. Where a value was needed but unfrozen, the code refuses rather than choosing.

---

## 11. Phase 11 — validation performed

| Check | Method | Result |
|---|---|---|
| New EXP-008 tests | `python -m pytest tests/unit/test_exp008_*.py` | **103/103 pass** |
| Full unit suite | `python -m pytest tests/unit` | **662 passed, 1 pre-existing failure, 1 skipped** |
| Frozen-file integrity | SHA256 of 14 governed files vs their recorded expectations | **all unchanged** |
| DEC-030 identity | SHA256 vs its own `dec030_fingerprint` | **match** |
| Budget JSON identity | SHA256 vs DEC-031 §15 | **byte-identical** |
| Artifact determinism | `python scripts/generate_b6_implementation.py --check` | **DETERMINISTIC** (re-run reproduces identical bytes) |
| Diff inspection | `git status` / `git diff` reviewed file by file | B6 changes isolated as listed in §9.1 |
| Spark / training / TEST | not invoked | **0 / 0 / 0** |

Not run, by instruction: Spark, integration tests, training, any EXP-008 runner, TEST, any benchmark.

---

## 12. Acceptance gates

| Gate | Result |
|---|---|
| A3-time-only implemented exactly | **PASS** |
| A3-R3 comparator preserves frozen R3 | **PASS** |
| R4 represented but cannot execute with unresolved semantics | **PASS** |
| A4 mode4 = {0, 3, 6, 9} | **PASS** |
| Action indices preserved | **PASS** |
| mode12 unchanged | **PASS** |
| Q0 provenance explicit | **PASS** |
| No Q0 projection invented | **PASS** |
| TEST guards intact | **PASS** |
| A5 remains disabled | **PASS** |
| Primary-study defaults unchanged | **PASS** |
| All relevant zero-Spark tests pass | **PASS** (103/103 new; 1 pre-existing unrelated failure, §8) |
| Deterministic B6 JSON | **PASS** |
| No training artifacts modified | **PASS** |
| No experiment results modified | **PASS** |
| PLAN unchanged | **PASS** |
| DEC-030 unchanged | **PASS** |
| DEC-031 unchanged | **PASS** |
| Execution authorization remains NO | **PASS** |
| Spark execution count = 0 | **PASS** |

---

## 13. Status

**B6 implementation COMPLETE.** The frozen parts of the DEC-030 A3/A4 methodology are implemented additively, default-preservingly and testably; the unfrozen parts are represented explicitly and fail closed. A3/A4 remain **frozen in intent, unfrozen in detail, unauthorized in execution**.

**Spark executions = 0. Training executions = 0. TEST executions = 0. EXP-008 execution authorization = NO. A5 = DISABLED. PLAN.md, DEC-030 and DEC-031 = UNCHANGED.**

*End of B6 implementation report.*
