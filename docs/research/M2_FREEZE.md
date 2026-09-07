# M2 Research Problem Freeze

**Project:** Self-Adaptive Big Data Programming Using Reinforcement Learning and Spark
**Freeze date:** 2026-09-07
**Milestone:** M2 — Research Problem Frozen (PLAN.md §32)

---

## Frozen Documents

These documents are frozen as the authoritative research definition. Any substantive change requires a new `DEC-xxx` entry in `DECISIONS.md` and supervisor approval (see Change Control below).

| Document | Role | Status |
|---|---|---|
| `docs/PLAN.md` | Frozen 50-day execution plan | Frozen (Day 1) |
| `docs/RESEARCH_PROBLEM.md` | Research problem, RQs, hypotheses, scope, SC1–SC8 | **Draft for supervisor sign-off** |
| `DECISIONS.md` | Decision log (DEC-001…DEC-007) | Frozen (Day 1–2) |
| `experiments/registry.csv` | Experiment register (EXP-001…EXP-012) | Frozen (Day 1) |

---

## Frozen Components

| Component | Location | Status |
|---|---|---|
| Research problem | RESEARCH_PROBLEM.md §2 | Draft for sign-off |
| Research aim | RESEARCH_PROBLEM.md §3 | Draft for sign-off |
| Main RQ (RQ2) | RESEARCH_PROBLEM.md §5 | Draft for sign-off |
| Supporting RQs (RQ0, RQ1, RQ3–RQ6) | RESEARCH_PROBLEM.md §6 | Draft for sign-off |
| Objectives (O1–O7) | RESEARCH_PROBLEM.md §4 | Draft for sign-off |
| Hypotheses (H1–H4) | RESEARCH_PROBLEM.md §7 | Draft for sign-off |
| Scope (in/out) | RESEARCH_PROBLEM.md §8 | Draft for sign-off |
| System boundary | RESEARCH_PROBLEM.md §9 | Draft for sign-off |
| Assumptions | RESEARCH_PROBLEM.md §10 | Draft for sign-off |
| Constraints | RESEARCH_PROBLEM.md §11 | Draft for sign-off |
| Success criteria (SC1–SC8) | RESEARCH_PROBLEM.md §13 | Draft for sign-off |
| Experimental traceability | RESEARCH_PROBLEM.md §14 | Draft for sign-off |
| Minimum viable contribution | RESEARCH_PROBLEM.md §15 | Draft for sign-off |
| Ideal final contribution | RESEARCH_PROBLEM.md §16 | Draft for sign-off |
| Threats to validity | RESEARCH_PROBLEM.md §17 | Draft for sign-off |

---

## Freeze Status

### PROVISIONALLY FROZEN — awaiting supervisor signature/approval

**Reason:** The research definition is internally consistent (M2_RESEARCH_FREEZE_AUDIT.md verdict: PASS) and all documents are complete. However, actual supervisor approval has not been recorded within this repository. The freeze becomes fully `FROZEN` only when the supervisor sign-off section below is completed.

**M2 exit criterion (PLAN.md §32):** "RESEARCH_PROBLEM.md approved; SC1–SC8 written"
- SC1–SC8 written: ✅ (RESEARCH_PROBLEM.md §13)
- RESEARCH_PROBLEM.md approved: ⏳ awaiting supervisor signature

---

## Supervisor Sign-Off

| Status | Item |
|--------|------|
| [ ] | Research problem approved (§2) |
| [ ] | Main RQ approved (§5) |
| [ ] | Supporting RQs approved (§6) |
| [ ] | Objectives approved (§4) |
| [ ] | Hypotheses approved (§7) |
| [ ] | Scope approved (§8) |
| [ ] | System boundary approved (§9) |
| [ ] | SC1–SC8 approved (§13) |
| [ ] | Minimum contribution approved (§15) |
| [ ] | Ideal contribution approved (§16) |
| [ ] | Threats to validity reviewed (§17) |

**Supervisor:**
Name: __________________
Signature: ______________
Date: ___________________

---

## Items Requiring Confirmation

Per RESEARCH_PROBLEM.md §18, three interpretation items are flagged for supervisor confirmation (none are plan changes):

1. **Hypotheses for RQ1/RQ4/RQ5/RQ6:** PLAN.md defines H1–H4 for RQ0/RQ2/RQ3 only; RQ1/RQ4/RQ5/RQ6 have evaluation criteria but no explicit Hx. *Interpretation to confirm.*
2. **SC2–SC4 grouping:** PLAN.md groups SC2–SC4 as "H2–H3 accepted statistically"; RESEARCH_PROBLEM.md maps SC3/SC4 to H3 sub-claims. *Interpretation to confirm.*
3. **EXP-005b:** AQE condition referenced as EXP-005b but no dedicated register row. *Confirmed as sub-experiment of EXP-005, not a new ID.*

---

## Change Control

After M2 freeze, changes to the research problem, RQs, hypotheses, scope, or SC1–SC8 require:

1. An explicit decision entry in `DECISIONS.md` (`DEC-xxx`)
2. Supervisor approval
3. Documentation of:
   - The old definition
   - The new definition
   - Rationale for the change
   - Affected experiments (by EXP-id)
   - Affected report sections

**Minor editorial corrections** (typos, formatting, clarifications that do not change meaning) may be made without a decision entry, but must be noted in the Git commit message.

This rule prevents research drift during the 45 remaining implementation days.

---

## Audit Trail

| Date | Event | Commit |
|---|---|---|
| 2026-09-07 | M2 consistency audit performed; all 11 sections PASS | (this commit) |
| 2026-09-07 | M2 freeze record created; status = PROVISIONALLY FROZEN | (this commit) |

---

*M2 freeze record — Self-Adaptive Big Data Programming Using Reinforcement Learning and Spark*