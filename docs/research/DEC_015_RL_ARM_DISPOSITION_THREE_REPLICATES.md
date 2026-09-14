# DEC-015 — RL-Arm Disposition for EXP-005 After the M8 Gate Failure

> **Status.** **SIGNED AND ADOPTED 2026-09-14.** The AUTHORITATIVE text is
> **DEC-015** in `DECISIONS.md`, approved by the operator after the Day-32
> readiness audit presented the four options. This file is retained as the
> working record of how the decision was reached; where it and `DECISIONS.md`
> differ, `DECISIONS.md` governs. Supervisor counter-signature follows the
> same pending path as the M2 freeze.
>
> The decision authorizes NO execution: TEST remains sealed, DEC-014 is still
> pending, and B0'/B3/B4 remain unimplemented.

## Question

EXP-005 (PLAN line 312) mandates an RL arm — "RL vs B0,B0′,B1,B2,B3,B4" — and
PLAN lines 159/192 require "**the** frozen policy (never retrained)" — singular.
Day-29's M8 replicate-agreement gate FAILED at 0.20 (1/5) against the frozen
≥0.70 criterion, so the three replicate greedy policies demonstrably do NOT
agree closely enough to speak of one policy. PLAN, ARCHITECTURE_FREEZE and
COMPONENT_CONTRACTS define **no rule for selecting among seeds {0,1,2}**, and
no existing DEC provides a fallback. How is the EXP-005 RL arm constituted?

## Facts

1. Three real training replicates exist (Day-28/29, TRAIN split only, budget
   84 live executions each, gamma=0.0, mode12, Q0-init from EXP-002):

   | Replicate | Seed | Final policy ID | Episodes | Note |
   |-----------|------|-----------------|----------|------|
   | RL-s0 | 0 | `b801f4a7df200b04c630978f0476c29245da9a93368002f26bff4c2e5b8a7d033` | 84 | planned_episodes |
   | RL-s1 | 1 | `af41d8ae7a21d81f5c570f3d96246e26c393bc32018f3b82126a7a0600a9566c` | 49 | early-stopped epoch 7 |
   | RL-s2 | 2 | `d8fd7b9859d2feeab753d9a40f89f07fb7559a481accdf9d86bb1d578d54bc16b` | 42 | planned_episodes |

   Evidence: `results/training/analysis/day29_policy_agreement.json`,
   `results/training/train-a*/checkpoints/`.
2. No checkpoint has been promoted to the frozen policy store
   (`models/policies/` contains only `.gitkeep`). No selection rule exists.
3. M8 = 0.20 measures replicate **consistency**, not learning quality. It
   does not by itself disqualify any replicate, and it does not justify
   silently picking one.
4. Promoting one replicate by any post-hoc criterion (best validation reward,
   largest Q-table, lowest seed) would be **selection after the fact** —
   precisely the bias the M8 gate existed to exclude.

## Decision (operator directive, 2026-09-13)

**Evaluate ALL THREE replicate final policies as separate, pre-declared RL
arms in EXP-005** — RL-s0, RL-s1, RL-s2 — instead of one aggregated RL arm.

Rationale: with M8 failed, no single "frozen policy" is defensible. Evaluating
all three is the only disposition that adds no selection bias: it preserves
PLAN:192's "never retrained" guarantee (each replicate IS frozen — unchanged,
fingerprint-verified against its Day-28/29 checkpoint before TEST opens), and
it converts the M8 failure from a hidden assumption into a measured result
(between-replicate variance on unseen data becomes reportable evidence).

## Consequences

1. **Strategy count:** EXP-005 goes from 7 to 9 arms
   (B0, B0′, B1, B2, B3, B4, RL-s0, RL-s1, RL-s2).
2. **Projected cost:** ~245 → **~315** TEST executions at 5 repetitions
   (9/7 × 245), still OUTSIDE the SC6 RL-training cap (ledger 232/500
   untouched). Exact count pending the "7 instances vs 43 frozen TEST cells"
   clarification already recorded in DEC-014.
3. **Policy promotion:** each replicate's checkpoint is copied to the frozen
   policy store UNCHANGED, with fingerprint equality asserted against the
   training artifact. No retraining, no Q-value edits, no gamma change.
4. **Statistics:** per-arm reporting; if aggregate RL claims are made, the
   multiplicity of three arms must be handled by a pre-declared rule
   (e.g. per-arm Wilcoxon with Holm correction across arms, or
   median-of-replicates as primary) — this is an analysis-planning choice
   that MUST be frozen BEFORE TEST execution and is NOT decided here.
5. **PLAN register:** PLAN line 312 lists 7 strategies; this disposition
   supersedes it as a governance amendment and is recorded here rather than
   by editing PLAN.md (PLAN is not modified by this draft).

## Safeguards

- All three arms derive from TRAIN-only training; no TEST data influenced any
  of them (verified by the Day-28/29 leakage guards).
- TEST remains SEALED; this decision does not authorize execution — that is
  DEC-014's question and remains PENDING.
- B0/B0′/B1/B2/B3/B4 definitions are untouched.
- No checkpoint is deleted or modified; the frozen store gains verified copies.

## Required approval statement

`EXP-005's RL arm is constituted as three frozen replicate arms (RL-s0/s1/s2)
pending supervisor counter-signature of this record and of DEC-014. TEST
remains sealed until DEC-014 is approved.`

**Status.** **APPROVED (OPERATOR) — DEC-018 Decision C, 2026-09-14.**
**NO SUPERVISOR COUNTER-SIGNED THIS RECORD.** DEC-018 Decision A converted the
self-imposed supervisor gate into an operator decision and recorded the absence
of supervisor review permanently. The three-replicate disposition stands and the
EXP-005 arm count is 7, not 9.
