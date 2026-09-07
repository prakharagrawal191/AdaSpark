# M2 Research Freeze — Consistency Audit

**Audit date:** 2026-09-07
**Auditor:** AdaSpark project engineer (automated + manual cross-check)
**Sources checked:** `docs/PLAN.md` (frozen), `docs/RESEARCH_PROBLEM.md` (Day-4 draft), `DECISIONS.md`, `experiments/registry.csv`

---

## 1. Problem Statement Check

| Item | PLAN.md §2 | RESEARCH_PROBLEM.md §2 | Consistent? |
|---|---|---|---|
| Core problem | Static/default Spark config doesn't adapt to workload/runtime conditions | Same wording, expanded into current/problem/limitation/proposal/evaluation | ✅ |
| Self-adaptive framing (MAPE-K) | §2 motivation + §8 concept | §1 context + §9 boundary | ✅ |
| Policy π: s → a | §2 problem statement | §2 + §12 | ✅ |
| Single-node scope | §7 scope decisions | §8.1 in-scope | ✅ |
| Bounded training budget | §2 + §31 | §11 constraints | ✅ |

**Verdict:** PASS

---

## 2. Research Aim Check

| Item | PLAN.md §2 | RESEARCH_PROBLEM.md §3 |
|---|---|---|
| Aim text | "Determine whether RL can make a Spark big-data workload self-adaptive..." | Verbatim match |

**Verdict:** PASS

---

## 3. Research Question Check

| RQ | PLAN.md §3 | RESEARCH_PROBLEM.md §5/§6 | Consistent? |
|---|---|---|---|
| RQ0 (gate) | "How sensitive is execution time..." | Same | ✅ |
| RQ1 (state) | "Which state representation..." | Same | ✅ |
| RQ2 (main) | "Does the learned RL policy outperform..." | Same | ✅ |
| RQ3 (generalization) | "Does the policy generalize..." | Same | ✅ |
| RQ4 (reward/action) | "How do reward-function variants..." | Same | ✅ |
| RQ5 (cost/overhead) | "What are the training cost..." | Same | ✅ |
| RQ6 (AQE) | "How does the agent interact with AQE..." | Same | ✅ |

**Verdict:** PASS — all 7 RQs (RQ0–RQ6) match verbatim.

---

## 4. Objective Check

| Obj | PLAN.md §4 | RESEARCH_PROBLEM.md §4 | Consistent? |
|---|---|---|---|
| O1 environment | Assemble pinned Spark environment | Same | ✅ |
| O2 workload suite | Implement parameterized workload suite | Same | ✅ |
| O3 monitoring | Build monitoring pipeline | Same | ✅ |
| O4 sensitivity gate | Run config-sensitivity grid scan | Same | ✅ |
| O5 RL formulation | Formulate and implement RL env + agent | Same | ✅ |
| O6 experiments | Execute main comparison, generalization, ablation, AQE, overhead | Same | ✅ |
| O7 thesis | Produce thesis, matrix, viz, repo, presentation, demo | Same | ✅ |

**Verdict:** PASS

---

## 5. Hypothesis Check

| Hyp | PLAN.md §2 | RESEARCH_PROBLEM.md §7 | Consistent? |
|---|---|---|---|
| H1 (sensitivity) | ≥10% spread on ≥2 families | Same | ✅ |
| H2 (RL vs default) | ≥10% reduction on ≥half of test workloads | Same | ✅ |
| H3 (RL vs heuristics) | Never worse; better on ≥half | Same | ✅ |
| H4 (generalization) | Retains ≥half advantage unseen; never below default | Same | ✅ |

**Verdict:** PASS

---

## 6. Scope Check

| Boundary | PLAN.md §7 | RESEARCH_PROBLEM.md §8 | Consistent? |
|---|---|---|---|
| Single-node local Spark | In scope | In scope | ✅ |
| 5 discrete config actions max | In scope | In scope | ✅ |
| Tabular Q / bandit | In scope | In scope | ✅ |
| DQN/PPO | Out of scope | Out of scope | ✅ |
| Multi-node / K8s | Out of scope | Out of scope | ✅ |
| TB-scale | Out of scope | Out of scope | ✅ |

**Verdict:** PASS

---

## 7. Success Criteria Check

| SC | PLAN.md §2 | RESEARCH_PROBLEM.md §13 | Consistent? |
|---|---|---|---|
| SC1 | H1 gate passes | Same | ✅ |
| SC2–SC4 | H2–H3 accepted statistically | Same | ✅ |
| SC5 | H4 accepted | Same | ✅ |
| SC6 | ≤500 executions + ≤5% overhead | Same | ✅ |
| SC7 | ±5% reproducibility | Same | ✅ |
| SC8 | Tests green + repo reproducible | Same | ✅ |

**Verdict:** PASS

---

## 8. Experiment Traceability Check

| Mapping | PLAN.md source | RESEARCH_PROBLEM.md §14 | Consistent? |
|---|---|---|---|
| RQ0 → H1 → EXP-002 → SC1 | §3 + §33 | §14 matrix | ✅ |
| RQ2 → H2/H3 → EXP-005 → SC2–SC4 | §3 + §33 | §14 matrix | ✅ |
| RQ3 → H4 → EXP-006 → SC5 | §3 + §33 | §14 matrix | ✅ |
| RQ1 → EXP-007 (state ablations) | §24 | §14 matrix | ✅ |
| RQ4 → EXP-008 (reward/action ablations) | §24 | §14 matrix | ✅ |
| RQ5 → EXP-004/EXP-009 | §33 | §14 matrix | ✅ |
| RQ6 → EXP-005b (AQE) | §3 + §33 | §14 matrix | ✅ |

**Verdict:** PASS

---

## 9. Feasibility Check

| Item | PLAN.md §38 | Status |
|---|---|---|
| All selected components GREEN/YELLOW | Yes (no RED selected) | ✅ |
| Backend validated (DEC-007) | Day-2 smoke 13/13 PASS | ✅ |
| Timing harness CV < 10% | Day-3 warm CV = 3.36% | ✅ |
| 50-day budget | Schedule fits; buffers on D38/40/48–50 | ✅ |

**Verdict:** PASS

---

## 10. Open Decisions

Per RESEARCH_PROBLEM.md §18, three items flagged for supervisor confirmation:

1. **Hypotheses for RQ1/RQ4/RQ5/RQ6:** PLAN.md defines H1–H4 for RQ0/RQ2/RQ3 only. RQ1/RQ4/RQ5/RQ6 have evaluation criteria but no explicit Hx. *Not a plan change — an interpretation to confirm.*
2. **SC2–SC4 grouping:** PLAN.md groups SC2–SC4 as "H2–H3 accepted statistically"; RESEARCH_PROBLEM.md maps SC3/SC4 to H3 sub-claims. *Interpretation to confirm.*
3. **EXP-005b:** AQE condition referenced as EXP-005b but no dedicated register row (register lists EXP-005 only). *Confirmed as sub-experiment, not a new ID.*

**No unresolved academic decisions** beyond the three interpretation confirmations above.

---

## 11. Final Freeze Decision

| Dimension | Status |
|---|---|
| Problem statement | ✅ Consistent across PLAN + RESEARCH_PROBLEM |
| Research aim | ✅ Consistent |
| RQs (RQ0–RQ6) | ✅ Consistent |
| Objectives (O1–O7) | ✅ Consistent |
| Hypotheses (H1–H4) | ✅ Consistent |
| Scope | ✅ Consistent |
| Success criteria (SC1–SC8) | ✅ Consistent |
| Experiment traceability | ✅ Consistent |
| Feasibility | ✅ Validated (backend + timing) |

**Overall audit verdict: PASS — research definition is internally consistent and ready for supervisor sign-off.**