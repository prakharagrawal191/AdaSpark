# RQ → Literature Traceability

*AdaSpark · Day 10 (2026-09-09) · maps frozen RQs (`docs/RESEARCH_PROBLEM.md` §5–§6) to `docs/LITERATURE_MATRIX.md` v1.0 rows · evidence strengths per `docs/research/RESEARCH_GAP.md` §6 · limitations per `docs/research/LITERATURE_EVIDENCE_LIMITATIONS.md`*

| RQ | Relevant Literature | What Literature Establishes | What Remains Open |
|---|---|---|---|
| RQ0 (sensitivity gate) | C4, C5, C1, C2, C3 | Config sensitivity is real and workload-dependent (C4/C5/C1 abstracts); Spark-tuning studies exist (C2/C3 title scope) | Whether THIS action space moves time ≥10% on ≥2 families on THIS machine — EXP-002/H1/SC1 decides |
| RQ1 (workload characterization) | C1, C7, B1, A3 | Influence varies across applications (C1); code/workload features drive knob choice (C7); runtime stats enable adaptation (B1); straggler causes identifiable (A3) | Whether v1.5 state features suffice — EXP-007 (A1/A2) decides |
| RQ2 (main: adaptive vs baselines) | C1–C5, C7, E1, J2, J1, H1, D1, E2, C6 | Baseline families exist (ML/C5 taxonomy; BO E1/J2/C3; transfer J1; learned H1; RL-adjacent D1/E2/C6) and tuning gains are measurable (C1, C7 abstracts) | Whether the proposed policy beats default/static/rule/random — EXP-005/H2/H3/SC2–SC4 decides |
| RQ3 (generalization) | C1, C5, C7, E1, H1, J1, J3 | App-specificity (C1), open tuning problems (C5), cross-scale migration (C7), BO non-transfer (E1), optimizer robustness (H1), DBMS transfer (J1), few-shot transfer (J3) | Whether THIS policy transfers to unseen workloads — EXP-006/EXP-010/H4/SC5 decides |
| RQ4 (state/reward/action) | C1, C4, B1, C7, D1, G1, G2, I2 | Time as objective (C1); knob framing (C4); AQE knob boundary (B1); workload features (C7); sequential RL framing (D1); MAPE-K loop template (G1/G2); progress-as-signal (I2) | Which state/reward/action design works — EXP-007/EXP-008 decide |
| RQ5 (training cost) | C1, C4, C3, C7, D1, E1, I2, J2, J3 | Search is infeasible/costly (C1/C4 abstracts); BO-efficiency is studied (C3); Spark BO/RL collection infeasible at scale (C7); few-trial/surrogate/regret-budgeted practice (E1/J2/J3/I2) | Whether ≤500 cached executions suffice — EXP-004/SC6 decides |
| RQ6 (AQE complementarity) | B1, B2, B3, G1, G2 | AQE = within-query adaptation (B1 docs scope); lineage B2/B3; MAPE-K frames AQE as one loop instance (G1/G2) | Whether cross-execution learning adds value with AQE on — EXP-005b decides |

*No RQ is closed by literature. Coverage is thinnest where it should be: RQ3/RQ5/RQ6 rest on adjacent-domain transfer/cost evidence (J1/J3/C7/E1) and docs-scope AQE material (B1) — hence the frozen experiments carry the weight. RQ1/RQ4/RQ6 have no standalone Hx by frozen design (see M2_FREEZE.md confirmation items); their rows above inform design/evaluation, not hypothesis tests.*
