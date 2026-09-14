# DEC-013 — Validation Execution Gate + B1/B2 Selection Repetition Rule

> **Status.** **SIGNED AND ADOPTED 2026-09-13.** The AUTHORITATIVE text is
> **DEC-013** in `DECISIONS.md`, recorded by the operator: selection at 1
> repetition, and the validation execution gate via Model B. This file is retained
> as the working record of how the decision was reached; where it and
> `DECISIONS.md` differ, `DECISIONS.md` governs. Supervisor counter-signature
> follows the same pending path as the M2 freeze.
>
> Only this status banner was reconciled; no rationale, evidence, option text,
> scope, budget figure, requirement, signature or date below it was altered.

**Date drafted.** 2026-09-13 (Day 31, second governance gate)

**Supersedes.** Nothing. Refines the *pending* DEC-012: DEC-012's 96-run
selection arithmetic embeds an unresolved repetition-rule assumption
(see Fact 4 and Question 2). If this DEC is approved, DEC-012's Option
costing must be read through the repetition rule chosen here. Nothing
in DEC-012 is altered by this document.

**Type.** Governance / specification. **Not** an implementation task,
**not** an execution task, **not** an authorization.

---

## Facts (repository evidence, verified 2026-09-13 at HEAD `e0ebbb8`)

1. **Day 31 harness/freeze infrastructure is complete** and committed
   (`e0ebbb8`): evaluation harness (`src/sparkrl/evaluation/`), TEST
   identity freeze (`results/evaluation/test_freeze.json`, 43 cells,
   identity-only), evaluation specification, validator, unit tests.
   Zero Spark executions.

2. **The runner guard currently rejects VALIDATION cells.**
   `execute_run` (`src/sparkrl/experiments/runner.py:272`) calls
   `assert_train_only(...)` as its **first statement**, before any
   Spark session construction (`build_session` is only reached at
   line 298). `assert_train_only`
   (`src/sparkrl/experiments/spec.py:81-91`) raises `ValueError` for
   every cell whose `split_of(...) != "train"`. The same guard also
   validates the whole EXP-002 declared scope
   (`experiments/spec.py:219`). Control flow:

   ```text
   caller (EXP-003 validation plan / any experiment)
     ↓
   execute_run                     runner.py:264
     ↓
   assert_train_only               runner.py:272 (first statement)
     ↓
   split_of(...) != "train"  →  ValueError   spec.py:81-91
     ↓
   Spark never starts              build_session (runner.py:298) unreached
   ```

   The guard's own error message anticipates this state: *"EXP-002
   runs on TRAIN cells only; the TEST split is frozen until Day 31
   (PLAN section 18) and VALIDATION belongs to EXP-003."*

3. **Budget authorization does NOT imply execution authorization.**
   Even if a supervisor approves a run count (DEC-012 Options), the
   runner would still refuse every seed=3 cell. Budget and code path
   are **separate** authorizations.

4. **No existing decision authorizes widening the runner guard.**
   `DECISIONS.md` ends at DEC-011 (multi-step NOT enabled). DEC-012
   (pending) addresses budget only; it does not mention the runner
   guard, `assert_train_only`, or any code-path change.
   **NO EXISTING AUTHORIZATION.**

5. **Validation measurements for seed=3 are ABSENT.** No valid
   seed=3 observation exists anywhere in the repository (EXP-002 is
   seed=0; training manifests are seeds {0,1,2}; baseline data is
   seed=0). B1/B2 empirical selection remains pending.

6. **B1/B2 are NOT frozen.** `evaluation_spec.json` records
   `"selected": false`; no `baseline_selection.json` exists (validator
   check 13 SKIP). TEST remains sealed (`TestSplitSealed` verified by
   validator check 09).

7. **The repetition rule for candidate selection is AMBIGUOUS.** The
   PLAN states the 5-repetition rule for *evaluation* only:

   - PLAN line 141: *"evaluation uses median-of-5 repetitions only"*
   - PLAN line 184: *"all evaluation = 5 repetitions × fixed seeds,
     medians analyzed"*

   but describes the selection split as **tuning**, not evaluation:

   - PLAN line 163: *"Validation = same families × seed{3}
     (B1/B2 tuning + hyperparameters)"*

   and never states which repetition rule governs candidate-grid
   selection measurements. The repository artifacts expose **both**
   shapes simultaneously:

   - Validator check 24: **480 planned runs** (8 cells × 12 candidates
     × 5 reps queue shape, all validation, planned only)
   - Validator check 23 / evaluation-spec projection: **minimum 216**
     (1-rep selection 96 + 120 comparison)
   - DEC-012 (pending): assumes 1-rep selection = 96

   Whether "all evaluation = 5 repetitions" binds candidate selection
   is **not decidable from the PLAN text alone**.

8. **Cost under each interpretation** (EXP-003 unchanged at 5 reps:
   3 strategies × 8 cells × 5 = 120):

   | Interpretation | Selection | EXP-003 | Combined |
   |---|---:|---:|---:|
   | 1-rep selection | 12 × 8 × 1 = **96** | 120 | **216** |
   | 5-rep selection | 12 × 8 × 5 = **480** | 120 | **600** |

   Neither scenario is authorized.

9. **Budget scope.** The 500-execution cap is **RL-training-only**:
   PLAN line 45 ("SC6 = training ≤500 executions"); PLAN line 145
   ("3 training seeds {0,1,2}; cap 500 executions"); PLAN line 311
   (EXP-004 register row: "≤500 (cached)"). EXP-003 carries its own
   register estimate (line 310, "~30") and is not stated to draw on
   SC6. Current training ledger: **232/500 live executions**
   (Day-29 figure; unchanged by Day 31 and by this task). No separate
   evaluation-budget line exists; the register's per-experiment
   estimates are the only evaluation budget recorded. The exact
   treatment of the 96/480/120 runs against SC6 is **not explicitly
   stated** by the repository and is recorded here as a scoping note
   for the supervisor; this DEC does not assign them to SC6.

10. **TEST boundary.** `TestSplitSealed` +
    `assert_test_execution_permitted()` always refuse; `execute_test_run`
    refuses regardless of inputs. Any authorization made under this DEC
    must preserve: TRAIN → existing permitted paths; VALIDATION →
    separately authorized calibration path only; TEST → sealed until
    EXP-005/006.
