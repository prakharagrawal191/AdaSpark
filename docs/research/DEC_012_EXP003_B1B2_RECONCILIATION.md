# DEC-012 | 2026-09-13 | EXP-003 / B1-B2 Validation Selection Scheduling and Budget Reconciliation

> **Status.** **SIGNED AND ADOPTED 2026-09-13.** The AUTHORITATIVE text is
> **DEC-012** in `DECISIONS.md`, recorded by the operator as Option B. This file
> is retained as the working record of how the decision was reached; where it and
> `DECISIONS.md` differ, `DECISIONS.md` governs. Supervisor counter-signature
> follows the same pending path as the M2 freeze.
>
> Only this status banner was reconciled; no rationale, evidence, option text,
> scope, budget figure, requirement, signature or date below it was altered.

**Context.** Day 31 (PLAN line 277) is complete as an infrastructure/plan-freeze milestone: the evaluation harness is built, the TEST-split identity is frozen, the candidate grid is fingerprinted, and the B1/B2 selection machinery is proved to accept validation observations and structurally reject all others. Day 31 actual Spark executions: **0**.

Day 32 (PLAN line 278) is EXP-005 main comparison on the TEST split, which requires B1/B2 to be frozen as strategies. B1/B2 are defined (PLAN lines 153-154) as validation-selected static baselines. ARCHITECTURE_FREEZE §14 assigns "baseline calibration (EXP-003)" to the VALIDATION split.

---

## Facts

1. Day 31 harness/freeze infrastructure is complete (validator: 35 PASS, 1 expected SKIP, 0 FAIL).
2. Validation measurements required to empirically freeze B1/B2 are **absent**. Exhaustive search confirms no seed=3 data exists in EXP-002 (seed=0), training (seeds 0/1/2), or baseline (seed=0) artifacts.
3. B1/B2 selection requires **96** validation runs under the currently defined grid (12 configs × 8 cells × 1 rep).
4. EXP-003 requires **120** comparison runs under the current five-repetition policy (PLAN line 141: "evaluation uses median-of-5 repetitions only"; 3 strategies × 8 cells × 5 reps).
5. Combined cost is **216** executions.
6. PLAN line 310 currently states **~30** for EXP-003.
7. The ~30 estimate is compatible with a one-repetition B0/B1/B2 comparison (3 × 8 = 24) but does not cover the separately required 96-run B1/B2 selection grid and does not match the fixed five-repetition EXP-003 policy.
8. Day 32 requires frozen B1/B2 before EXP-005 can begin.
9. TEST must remain sealed until EXP-005/EXP-006 (PLAN lines 312-313; ARCHITECTURE_FREEZE §14).
10. No Spark executions were performed during this reconciliation.
11. The 500-execution training cap (SC6, PLAN line 45) applies to RL training only; EXP-003 is a separate register line (PLAN line 310) and is NOT charged to the training budget.

---

## Validation Evidence

| Evidence source | Seed | Split | Valid measurement? |
|----------------|------|-------|-------------------|
| EXP-002 | 0 | TRAIN | NO for validation |
| Training data | 0/1/2 | TRAIN | NO |
| Baseline data | 0 | TRAIN | NO |
| Validation measurements | 3 | VALIDATION | **NONE FOUND** |

**Conclusion:** `NO VALID VALIDATION DATA`

The validation split requires seed=3 for families {F1_agg, F2_join, F3_rdd, F5_mixed} × scales {small, medium} (8 cells). No such data exists in any repository artifact.

---

## Cost Reconciliation

| Phase | Computation | Runs |
|-------|------------|------|
| B1/B2 selection | 12 configs × 8 cells × 1 rep | **96** |
| EXP-003 comparison | 3 strategies × 8 cells × 5 reps | **120** |
| **Combined** | 96 + 120 (no reuse: different rep counts) | **216** |
| PLAN estimate | | **~30** |
| **Difference** | 216 − 30 | **186** |
| **Multiplicative** | 216 / 30 | **7.2×** |

## Run Reuse Finding

**No authorized cross-purpose reuse rule was found.**

- Selection uses 1 repetition per cell
- EXP-003 uses 5 repetitions per cell (PLAN line 141: "evaluation uses median-of-5 repetitions only")
- At different repetition counts on the same cells, the selection grid **cannot** be reused for the comparison
- The plan does NOT explicitly permit reuse across different repetition counts
- Every comparison run is additional to the selection runs

---

## TEST Boundary

**TEST remains sealed.**

- `assert_test_execution_permitted()` always raises `TestSplitSealed`
- `execute_test_run()` raises `TestSplitSealed` regardless of inputs
- Day 31 did not execute TEST
- TEST execution belongs to EXP-005 (Day 32-33) and EXP-006 (Day 34) — PLAN lines 312-313
- No split guard was weakened

---

## Budget Scope

**Training budget (SC6):** 232 / 500 live executions (Day-29 validator figure)

The 500-execution cap (PLAN line 45, SC6) applies to **RL training only**. EXP-003 is a separate register line (PLAN line 310) and is **NOT charged** to the training budget.

**Projected evaluation costs (separate from training cap):**
- B1/B2 selection: 96 runs
- EXP-003 comparison: 120 runs
- EXP-005 TEST: ~245 runs
- EXP-006 unseen: ~100 runs

---

## Governance Decision

### Option A
Authorize:
- 96-run validation selection (12 configs × 8 cells × 1 rep)
- 120-run EXP-003 comparison (3 strategies × 8 cells × 5 reps)
- 216 total executions

and explicitly reconcile the budget discrepancy (~30 → 216).

### Option B
Interpret ~30 as the comparison-only estimate at one repetition (3 × 8 = 24), while authorizing the 96-run B1/B2 selection as a separate required phase. This interpretation is **not** already approved and requires explicit authorization.

### Option C
Amend PLAN scheduling to allocate a dedicated execution phase/day for the validation selection grid before Day 32.

---

## Required Approval

**Day 32 / EXP-005 remains BLOCKED** until B1/B2 are empirically frozen and the required execution phase is authorized by the supervisor.

---

## Spark Executions

**Spark executions during this task: 0**

---

## References

- PLAN line 277: Day 31 = "Eval harness + B1/B2 | frozen test set; static baselines tuned on validation | configs frozen"
- PLAN line 278: Day 32 = "EXP-005 main comparison | 7 instances × 7 strategies × 5 reps | queue completes"
- PLAN line 310: EXP-003 register = "support RQ2 | B1/B2 beat B0 | validation split | B0,B1,B2 | ~30 | frozen B1/B2"
- PLAN line 141: "evaluation uses median-of-5 repetitions only"
- PLAN line 153: B1 = "Static global | one config tuned on validation, used everywhere"
- PLAN line 154: B2 = "Static per-family | best validation-grid config per family"
- PLAN line 163: Validation = same families × seed{3}
- PLAN line 45: SC6 = training ≤500 executions
- ARCHITECTURE_FREEZE §14: VALIDATION = baseline calibration (EXP-003)
- ARCHITECTURE_FREEZE §12: B1/B2 family/scale-tuned
- DEC-011: multi-step NOT enabled; gamma = 0.0

