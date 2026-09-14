# DEC-014 Draft — TEST Execution Authorization for EXP-005

> **Status.** **APPROVED (OPERATOR) — DEC-018 Decision B, 2026-09-14.**
> **NO SUPERVISOR REVIEWED THIS DOCUMENT.** DEC-018 Decision A converted the
> supervisor gate — a control this project imposed on itself, not an
> institutional requirement — into an operator decision, and recorded the
> absence of supervisor review permanently. Read every approval here as an
> operator decision and nothing more.
> Prepared: Day 32 readiness audit (post Day-31 closure, HEAD `ba287a6`).
> Authorizes EXP-005 ONLY, at 7 instances x 7 arms x 5 repetitions = 245 TEST
> executions. TEST remains sealed for EXP-005b and EXP-006.
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
   `[SUPERSEDED 2026-09-14 — the two open items in the amendment above are
   both now closed. The technical freeze is DONE: `models/policies/` holds
   `policy-af41d8ae7a21d81f`, `policy-b801f4a7df200b04`,
   `policy-d8fd7b9859d2feea` and `exp005_rl_arms.json`. DEC-015 is APPROVED
   (operator) under DEC-018 Decision C. The amendment text is retained as
   history and deliberately not rewritten.]`
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
   `[SUPERSEDED by DEC-016 D and DEC-017: read "43 frozen TEST cells"
   as "the 7 frozen EXP-005 INSTANCES", and "9 arms, ~315 runs" as
   "7 arms, 245 runs". See the Amendment section below - the earlier
   figures combined an instance-count cost model with a cell-count
   scope and were never mutually consistent.]`
- **Option B — Authorize EXP-005 TEST execution only after the frozen RL
  policy artifact exists** and the failure protocol is completed (a
  prerequisite-completing amendment first). RECOMMENDED: PLAN lines
  157-158 require the policy frozen before the test set is opened.
- **Option C — Defer TEST authorization** until EXP-003 (120-run
  B0/B1/B2 validation comparison) is executed, preserving full
  calibration-before-evaluation ordering.

## Amendment — resolved scope (DEC-016 D, DEC-017)

Everything this draft listed as outstanding, except its own authorization, is now
resolved. The scope it should authorize is:

| Item | Resolved value | Authority |
|---|---|---|
| TEST scope | the **7 frozen EXP-005 instances**, not 43 cells | DEC-016 D, `exp005_instances.json` |
| Arms | **7** — B0, B1, B2, B4, RL-s0, RL-s1, RL-s2 | DEC-017 amendment 3 |
| Repetitions | **5** | PLAN:141 / :184 |
| Projected TEST executions | **7 x 7 x 5 = 245** | matches the PLAN:312 register estimate |
| Budget line | EXP-005's own line, NOT SC6's 500 training cap | PLAN:310/312 |

**The 43-vs-7 inconsistency is closed.** This draft previously paired "43 frozen
TEST cells" with a "~245 runs" cost model, which required 7 instances and was
never mutually consistent (43 x 7 x 5 = 1505). The 43 cells remain the TEST
IDENTITY; the 7 are the EXP-005 INSTANCES drawn from it.

**B3 and B0' are no longer EXP-005 arms.** B3 is provably byte-identical to B1 on
every cell that exists (it would need a dataset 5.3x larger than any in the frozen
universe before diverging) and is reported analytically. B0' moves to EXP-005b
because `ARCHITECTURE_FREEZE:69` forbids pooling AQE-on with AQE-off analysis, and
because B0' adapts at runtime while every other arm is configuration-frozen.

**Consequence for this decision: the AQE-on runner authorization is NO LONGER on
EXP-005's critical path.** It remains a separate clause for EXP-005b, and must not
be bundled with the TEST authorization - different purpose, different scope.

### Prerequisites this draft named

- (a) **TEST execution explicitly authorized** — **STILL OPEN.** This is the only
  remaining item, and it is the supervisor's to grant.
- (b) **RL policy frozen per PLAN:157-158** — **SATISFIED.** DEC-015 published
  RL-s0/s1/s2 to `models/policies/`, each fingerprint-verified
  (manifest `58fac8b02e6e4635`).
- (c) **EXP-005 failure protocol completed** — **SATISFIED.** DEC-017 item 5:
  deterministic and NO-RETRY; failures are first-class recorded observations;
  medians over usable repetitions only; a cell with fewer than 5 usable
  repetitions is INCOMPLETE and excluded from pooled statistics with its count
  reported; a failed strategy-cell does not block queue completion.

### Authorization model, as refined

DEC-013 established the pattern: a caller supplies its own split authorization
rather than widening a frozen guard. Applied here, a dedicated EXP-005 entry point
supplies an `authorize_test_cell` restricted to the **seven frozen instances**,
leaving `assert_train_only` and `TestSplitSealed` untouched as defaults for every
other caller. This is narrower than the "Model A" sketch above, which proposed
making the seal itself approval-gated: scoping the authorization to one entry
point and seven named cells cannot leak to any other path.

### Every other EXP-005 input is frozen

B0 (`configs/baseline_b0.yaml`), B1/B2 (`baseline_selection.json`,
`0a0ecbe5151c81ed`), B4 (`b4_selection.json`, `0f87744727d1e12d`), the three RL
policies, the 7 instances (`exp005_instances.json`), the failure protocol and the
authorization design. Training ledger 316/500 with 184 remaining; EXP-005's 245
does not touch it.

## Required approval statement

`Day 32 / EXP-005 remains BLOCKED until (a) TEST execution is explicitly
authorized by this decision. Prerequisites (b) the frozen RL policy and
(c) the EXP-005 failure protocol are both SATISFIED (DEC-015, DEC-017).
Authorizing (a) would release EXP-005 at 7 instances x 7 arms x 5
repetitions = 245 TEST executions, on EXP-005's own register line.`
