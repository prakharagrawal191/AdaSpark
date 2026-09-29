# Presentation outline (Days 46–47 draft) — 16 slides, each mapped to claims + figures

1. Title — AdaSpark: sample-efficient RL configuration selection for single-node Spark.
2. Motivation — ~200 knobs, defaults stale under drift (MAPE-K setting).
3. Research gap — offline BO tuners (static), deep RL (1000s of runs), DB optimizers (not Spark);
   gap: tabular/bandit online adaptation + cache + unseen-workload evidence (matrix: 30 rows A1–J3).
4. Problem + RQs — RQ0 gate … RQ6 AQE; H1–H4; SC1–SC8 (RESEARCH_PROBLEM.md).
5. System architecture — monitor→state→decide→configure→measure→learn (ARCHITECTURE_FREEZE).
6. RL formulation — v1.5 state, 12 actions, R3 reward equation, γ=0 bandit (DEC-011: no multi-step).
7. Spark integration + monitoring — event-log primary, psutil secondary, ≤5% overhead (EXP-009 synthesis).
8. Experimental setup — splits, 5 reps, medians, noise band 11.89% (EXP-001), own-ledger pilots.
9. Baselines — B0/B0′/B1/B2/B3/B4 + 3 RL replicates; B3≡B1 finding (X1); no-pooling rule.
10. Sensitivity gate — EXP-002 PASS 4/4 families (fig exp002_configuration_sensitivity.svg).
11. Main results — descriptive sums; F4 pattern; X8 drift falsification (figs exp005_arm_comparison, x8_rematch).
12. AQE complementarity — X6 B0' mixed: F2 L −14.2% only above-noise signal (fig x6_b0prime_vs_b0).
13. Generalization + transfer — EXP-006 partial; X9 Taxi −78%/−70% (fig x9_taxi); SC5 honestly unevaluable.
14. Ablations + overhead — A1/A2 divergence, A5 not run; block-bootstrap warning (fig x_robustness_block_vs_iid).
15. Limitations — single node/synthetic-first; small-cell ±5% miss (X10 2/4); F3 structural; drift across days.
16. Conclusion + future work — bandit-matched-heuristic + reproducible harness; deep RL/clusters/multi-objective.

# Viva Q&A notes (Day 49 draft)

- Q: Does RL beat the heuristic? A: No superiority established — B1 lowest descriptive sum; X8
  falsified the single RL lead (drift); honest contribution is the harness + evidence, Plan-B framing.
- Q: Why no deep RL? A: sample cost ≫500 budget (PLAN §38, DEC-008); tabular fits 12 actions.
- Q: AQE interaction? A: X6 measured — one above-noise cell (F2 L −14.2%), rest inside noise; no pooling.
- Q: Novelty? A: tiered honestly (§6): applied techniques + engineering + experimental; hybrid-cache
  claim verified Day 10 against 30-row matrix; 3 candidates still to add (P3).
- Q: Reproducibility? A: X10 2/4 within ±5%; small cells drift-sensitive; seeds/manifests/checksums frozen.
- Q: Why did F3 fail? A: Windows sort/spill file-lock (WinError32), AQE-independent (X6 confirms), all arms.
- Q: Overhead honesty? A: small points but i.i.d. CIs overstated — block intervals flip 2/7; reported both.
- Q: Single machine threat? A: within-machine paired design; absolute times machine-relative (PLAN §27);
  Taxi pilot extends beyond synthetic (one month, one shape — feasibility only).
