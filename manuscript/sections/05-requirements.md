# 4. Requirements Analysis for Self-Adaptive Big Data Systems

Requirements were derived from the research objectives (O1–O7) and frozen in the architecture contracts before implementation, so that every component traces to a requirement and every requirement to an evaluation question (Figure 5; Table 4). Functional requirements define what the loop must do: ingest parameterized workloads across five families and three scales; monitor every execution with a fixed metrics schema; map workload context plus runtime feedback to a configuration decision; learn within a hard execution budget; and compare against baselines with statistical validity. Non-functional requirements constrain how: reproducibility (seeded, config-driven, immutable manifests), safety (no failed submitted configurations; failures score exactly −1 and train the agent to avoid them), determinism of analysis (seeded resampling, byte-reproducible artifacts), and auditability (a decision log in which scope changes, budget reconciliations, and negative outcomes are recorded rather than edited away).

Two requirements deserve emphasis because they shaped the engineering. First, the budget requirement (≤500 training executions, SC6) is enforced structurally by the environment's execution guard and counted across manifests — not estimated. Second, the test-discipline requirement (frozen train/validation/test split, TEST sealed until evaluation) is enforced by authorization guards in code, so an engineer cannot accidentally train on the test set. Both convert good intentions into properties the test suite can verify.

The requirement set mirrors what the self-adaptive-systems literature identifies as the hard parts of placing learning inside a feedback loop: knowing when a learned component is wrong, keeping adaptation decisions analyzable, and preserving evidence for later audit [85][87]. Trustworthiness requirements follow general trustworthy-ML practice, where robustness, transparency and accountability are properties to be demonstrated rather than asserted [92]. The lineage requirement (every decision traceable to code, data and policy versions) corresponds to ML lineage frameworks for production systems [91]. Reproducibility is specified at the strongest level a single-host study can support: re-running the analysis code over the frozen record reproduces every reported number, while re-running executions is a separately measured property (SC7), in line with graded definitions of computational reproducibility [93].

## Table 4: Functional and Non-Functional Requirements Matrix

| ID | Requirement | Type | Verified by |
|---|---|---|---|
| FR1 | Parameterized workloads (5 families × 3 scales, seeded) | Functional | EXP-002, EXP-006, dataset manifests |
| FR2 | Per-run monitoring (system metrics + event logs) | Functional | EXP-009 (4,842 runs, 0 deviations) |
| FR3 | State → configuration policy with offline init | Functional | EXP-004 training; policy store |
| FR4 | Baseline comparison (default, static, heuristic, random) | Functional | EXP-005 (245/245 runs) |
| FR5 | Generalization + ablation + overhead studies | Functional | EXP-006/007/008/009 |
| NFR1 | Bounded training budget (≤500, counted) | Non-functional | SC6 ledger 483/500 |
| NFR2 | Sealed test discipline (authorization guards) | Non-functional | Day-31 gate 36/36 |
| NFR3 | Byte-reproducible analysis (seeded, frozen code) | Non-functional | 16/16 corroboration |
| NFR4 | No failed submitted configurations | Non-functional | 0 failures in training; F-FAIL invariant |
| NFR5 | Full audit trail (decisions, provenance, manifests) | Non-functional | 55 DEC entries; immutable artifacts |
