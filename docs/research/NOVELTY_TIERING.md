# Novelty Tiering

*AdaSpark · Day 10 (2026-09-09) · grounded in `docs/research/RESEARCH_GAP.md` (§6 claim-to-evidence trace) and `docs/LITERATURE_MATRIX.md` v1.0 (30 VERIFIED rows) · frozen problem: `docs/RESEARCH_PROBLEM.md`*

> **Reading rule.** Tier 1 = established in the reviewed literature (not a contribution). Tier 2 = the proposed combination/adaptation under test (not a proven contribution). Tier 3 = what would count as an empirical contribution **only if** the frozen experiments support it. **No Tier-3 item is claimed as fact in Week 2.**

## Tier 1 — Established in Existing Literature

These are NOT proposed contributions. Each is supported by the cited matrix rows at the stated evidence strength.

| Concept | Supporting Literature | Status |
|---|---|---|
| Spark in-memory execution model and its performance basis | A1, A5, A4 | Established (abstracts read) |
| Shark → Spark SQL → AQE engine lineage; runtime plan adaptation within a query | A6, A2, B1, B2, B3 | Established; B1 scope is industry/official-docs, non-peer-reviewed |
| Configuration sensitivity + workload dependence of performance | C1, C4, C5 | Established (abstracts read) |
| Automatic configuration tuning in multiple families (rule/cost-model/simulation/experiment-driven/ML/adaptive) | C5 taxonomy; instances C1, C2, C3, C4, C7 | Established as families; C2/C3 at title scope |
| Few-trial BO config search; surrogate-model configuration search | E1 (BO), J2 (SMAC) | Established as techniques (title/venue scope) |
| RL for sequential systems decisions (resource management, cluster scheduling, Spark job scheduling, join ordering) | D1, E2, C6, I2 | Established as paradigm in adjacent domains; D1/C6 title-scope |
| Self-adaptive systems vocabulary (feedback loops, goals/utilities) + research roadmap | F1, F2 | Established as framing (title/venue scope) |
| MAPE-K reference model + autonomic-computing survey organization | G1, G2 | Established as reference model (G2 abstract; G1 title scope) |
| Learned query optimization / learned execution components with robustness costs | H1, H2, I1 | Established with caveats (H2 abstract; H1 abstract; I1 title scope) |
| Transfer / cross-scale / few-shot techniques in adjacent tuning domains | J1, J3, C7 | Established in adjacent domains (J3/C7 abstracts; J1 title scope) |
| Experimentation cost barrier (tuning is costly; Spark BO/RL instance collection infeasible at scale) | C4, C7, E1 | Established as problem framing (C4/C7 abstracts) |
## Tier 2 — Proposed Combination / Adaptation

The proposed study combines established ideas into the configuration tested by EXP-001…EXP-012. Wording is deliberate: "proposed", "under test", "adapted" — **not** "proven" and **not** "first".

1. **Applying a small tabular/bandit RL policy to Spark configuration selection.** Adapts the RL-for-systems paradigm (D1, E2) from scheduling/allocation to launch-configuration choice over the frozen 12-action space. *The proposed study combines D-domain RL decision-making with C-domain Spark tuning scope.*
2. **Using workload-context + runtime-feedback state (v1.5) as the decision input.** Adapts workload-aware tuning (C1, C7 code/workload features; B1 runtime statistics) into the frozen state design tested by ablations A1/A2 (EXP-007). *This project adapts established workload-aware signals into a cross-execution policy state.*
3. **Initializing policy information from controlled sensitivity data (EXP-002 grid).** Adapts surrogate/offline-knowledge practice (J2, J1, C7 migration) into T_ref calibration + Q-initialization. *This configuration of established ideas is the proposed design.*
4. **Bounding learning with a fixed execution budget + execution cache (≤500).** Adapts few-trial (E1), surrogate-efficiency (J2, J3), and regret-budgeted (I2) practice into the frozen training protocol (EXP-004). *A proposed adaptation to single-machine constraints, not an established result.*
5. **Combining adaptive learning with an explicit AQE-on comparison (EXP-005b).** Positions cross-execution learning relative to within-query adaptation (B1 lineage B2/B3) inside the MAPE-K loop (G1/G2). *The proposed study tests complementarity rather than assuming substitution.*
6. **Evaluating transfer across unseen Spark workload conditions (EXP-006/EXP-010).** Adapts adjacent transfer practice (J1, J3, C7) into the frozen unseen-test protocol for H4/SC5. *Whether transfer occurs for this policy is the empirical question.*

No priority is claimed for any Tier-2 item. If the experiments fail, Tier 2 remains "a tested combination that did not pay off" — still reportable under Plan B (benchmark framing).
## Tier 3 — Potential Empirical Contributions (Require Positive Results)

**Requires positive experimental results.** Nothing below is asserted. Each item states the frozen experiment that would have to support it and the frozen success criterion it maps to.

1. **A workload-aware policy that statistically beats default/static/rule/equal-budget-random on the frozen test set.** Would constitute an empirical contribution **if** supported by EXP-005 with Wilcoxon + Cliff's δ + Holm (H2/H3, SC2–SC4). *The project will test whether this holds.*
2. **Median execution-time improvement with task-balance and bounded spill.** Would constitute an empirical contribution **if** EXP-005/EXP-009 show time gains without violating SC7 (spill) and SC8 (overhead ≤5%). *If supported by the measurements.*
3. **Generalization of the frozen policy to unseen scales/families/seeds and the public dataset.** Would constitute an empirical contribution **if** EXP-006/EXP-010 support H4/SC5. *The project will test how far the advantage, if any, transfers.*
4. **Convergence within the bounded budget (≤500 cached executions, zero failed submits).** Would constitute an empirical contribution **if** EXP-004 supports SC6. *If supported by the training trace.*
5. **Measured value of runtime feedback in the state (A1/A2) and of reward/action design choices (A3–A5).** Would constitute an empirical contribution **if** EXP-007/EXP-008 isolate the effect. *The project will test whether state design matters.*
6. **Measured AQE complementarity.** Would constitute an empirical contribution **if** EXP-005b shows the policy adds value with AQE on (RQ6). *If supported by the AQE-on condition.*

## Safety review (Day 10)

Searched these documents for: first, novel, unique, unprecedented, only, no prior work, state-of-the-art (as a self-claim), superior, outperforms, improves, proves. Disposition:

- "state-of-the-art" appears only inside C7's SOURCE-REPORTED abstract finding ("better performance compared with state-of-the-art auto-tuning methods") — retained as a source report, not our claim.
- Tier-3 verbs are conditional ("would constitute … if", "will test whether", "if supported by") — legitimate forward references to frozen experiments, labeled as hypotheses/expected outcomes, not results.
- No sentence asserts gains for the proposed method as fact. The gap note's "remaining question … is whether … can measurably improve" is a question, not a claim.
- No "first/only/no prior work" sentence exists; the gap is scoped ("within the literature corpus examined", "at verified scope", "predominantly").
