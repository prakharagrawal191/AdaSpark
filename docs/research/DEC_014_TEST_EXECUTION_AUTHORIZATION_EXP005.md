# DEC-014 Draft — TEST Execution Authorization for EXP-005

> **Status.** **PENDING SUPERVISOR APPROVAL**
> Prepared: Day 32 readiness audit (post Day-31 closure, HEAD `ba287a6`).
> This is a DRAFT decision record. It is NOT approval. It does not unseal
> TEST, modify any guard, or authorize any execution until the supervisor
> signs it in `DECISIONS.md`.
>
> **AMENDMENT 1 (2026-09-13).** The RL-arm prerequisite referenced in Fact 5
> is now the subject of its own draft decision: **DEC-015**
> (`DEC_015_RL_ARM_DISPOSITION_THREE_REPLICATES.md` — operator directive
> recorded, PENDING SUPERVISOR COUNTER-SIGNATURE). DEC-015 constitutes the
> RL arm as **three frozen replicate arms (RL-s0/s1/s2)** instead of one
> aggregated "RL" strategy. Under that disposition EXP-005 becomes a
> **9-arm** comparison (B0, B0′, B1, B2, B3, B4, RL-s0, RL-s1, RL-s2) with a
> projected cost of **~315 TEST executions** (9/7 × 245) rather than ~245.
> The affected passages below are marked `[amended by DEC-015]`. PLAN.md is
> not modified; the 9-arm scope is a governance amendment recorded in
> DEC-015 §Consequences.5.

## Question

May the repository open the TEST split for execution, solely and strictly
for the frozen EXP-005 protocol (PLAN line 312), given that:

1. Day 31 is complete and the harness/selection/identity artifacts are frozen
   (`baseline_selection.json` artifact_id `0a0ecbe5151c81ed`,
   `test_freeze.json`, `evaluation_spec.json` fingerprint
   `e9c4777047cf4454...`).
2. B1 (`G-p8-sp16`) and B2 (per-family) are frozen from the authorized
   96-run validation grid (DEC-012 Option B + DEC-013).
3. `assert_test_execution_permitted()` currently raises `TestSplitSealed`
   unconditionally (`src/sparkrl/evaluation/spec.py`), and
   `execute_test_run()` is unreachable (`orchestration.py` line 134).
4. DEC-013 explicitly scoped its authorization to VALIDATION calibration
   only and stated the TEST boundary "requires its own decision" — this is
   that decision.

## Facts

1. TEST identity is frozen: `test_freeze.json`, `executed: false`, 43 cells,
   identity-only (no measurements).
2. B1/B2 selection used VALIDATION only: `contains_test_data: false`;
   no TEST metric influenced any selection.
3. EXP-005 per PLAN line 312: TEST split, 7 strategies × 5 repetitions,
   queue completes; strategies = B0, B0′, B1, B2, B3, B4, RL (PLAN
   lines 151-157).
   `[amended by DEC-015: the single RL strategy is constituted as three
   frozen replicate arms RL-s0/RL-s1/RL-s2 — 9 arms total; the PLAN
   line-312 "7 strategies" wording is superseded by DEC-015
   §Consequences.5, not by a PLAN edit.]`
4. Projected EXP-005 cost: ~245 TEST executions, OUTSIDE the SC6
   RL-training cap (which `configs/rl.yaml:17` scopes to RL training; the
   ledger stands at 232/500 and is untouched by evaluation runs).
   `[amended by DEC-015: under the 9-arm scope the projection is
   ~315 TEST executions (9/7 × 245), outside SC6.]`
5. **OPEN PREREQUISITE:** the RL strategy requires "trained Q-policy,
   frozen before test evaluation" (PLAN line 157/158). No frozen policy
   artifact exists yet (`models/policies/` contains only `.gitkeep`;
   Day-29 M8 gate FAILED at greedy-agreement 0.2000; only transition
   records and `day29_policy_agreement.json` exist under
   `results/training/`).
   `[amended by DEC-015: this prerequisite is now resolved at the
   governance level by DEC-015 — the three replicate final policies
   (seed 0: 84 episodes, seed 1: 49, seed 2: 42, all gamma=0.0, TRAIN
   split) are constituted as three separate frozen arms rather than
   requiring one M8-consistent aggregate policy. Technical freeze of the
   three artifacts into `models/policies/` is still pending and remains
   a precondition of any EXP-005 execution. DEC-015 is
   PENDING SUPERVISOR COUNTER-SIGNATURE.]`
6. Failure protocol is PARTIALLY specified: statuses, unusable-run
   accounting, timeout (300 s) and the per-cell usability rule exist;
   retry/attempt policy, partial-cell median representation and the exact
   "queue completes" semantics are unspecified for EXP-005.
7. No Spark executions were performed during the audits that produced
   this draft.

## Proposed authorization model (if approved)

- A dedicated, explicit EXP-005 test-execution authorization
  (Model A in the readiness audit): `authorize_test_cell` gains an
  experiment-scoped assertion, and the seal function becomes
  approval-gated (raises `TestSplitSealed` until an operator-set,
  environment-owned EXP-005 authorization flag is present). TEST remains
  impossible for every other caller; TRAIN/VALIDATION paths unchanged;
  split guards otherwise untouched.

## Options

- **Option A — Authorize EXP-005 TEST execution now**, with the Model A
   guard above, 43 frozen TEST cells, 7 strategies, 5 repetitions, ~245
   runs, outside SC6, after the RL policy is frozen.
   `[amended by DEC-015: "7 strategies, ~245 runs" reads as
   "9 arms, ~315 runs" under the DEC-015 disposition; "after the RL
   policy is frozen" reads as "after the three replicate arm artifacts
   are frozen into models/policies/".]`
- **Option B — Authorize EXP-005 TEST execution only after the frozen RL
  policy artifact exists** and the failure protocol is completed (a
  prerequisite-completing amendment first). RECOMMENDED: PLAN lines
  157-158 require the policy frozen before the test set is opened.
- **Option C — Defer TEST authorization** until EXP-003 (120-run
  B0/B1/B2 validation comparison) is executed, preserving full
  calibration-before-evaluation ordering.

## Required approval statement

`Day 32 / EXP-005 remains BLOCKED until: (a) TEST execution is explicitly
authorized by this decision, (b) the RL policy is frozen per PLAN lines
157-158, and (c) the EXP-005 failure protocol is completed.`
