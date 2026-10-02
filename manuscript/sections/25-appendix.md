# Appendix

## A. RL algorithm (tabular Q-learning, bandit mode)

Q(s,a) ← Q(s,a) + 0.2·[r − Q(s,a)]; ε-greedy with ε 1.0 → 0.05 (×0.95/episode); optimistic Q0 = 0.5 for evidence-free pairs; Q0-median init from EXP-002 TRAIN records; checkpoints every 25 episodes; early stop after 2 stable epochs.

## B. Reward-function configurations

R3: Equation (1) with weights (1.0, 0.2, 0.2, 1.0), references CV 0.5 / spill 0.10, clip [−1, +1], failure −1 exactly (`configs/reward.yaml`). A3-time-only: time term alone. A3-R4-log-ratio: registered, not implementable (incomplete specification).

## C. Spark tuning parameters (action grid)

`shuffle.partitions ∈ {16, 32, 64, 128}` × `local[N], default.parallelism ∈ {2, 4, 8}` → 12 actions; mode-4 subset {0,3,6,9}; parallelism changes restart the session; AQE-off main study.

## D. Benchmark workloads

F1_agg (aggregation), F2_join (join), F3_rdd (sort/filter), F4_ski (skew join), F5_mixed (pipeline, twice-consumed cached intermediate) × S(<512 MiB)/M(<2 GiB)/L(≥2 GiB), dataset seed 0, checksummed manifests.

## E. Experimental scripts and supplementary results

Runners/analyzers: `scripts/run_exp00{1,2,5,6,9}.py`, `run_exp009_ext.py`, `run_training.py`, `analyze_exp00{2,6,7,9}.py`, `analyze_exp009_ext.py`, `analyze_exp009_robustness.py`; confirmatory studies: `run_exp013.py` / `analyze_exp013.py` and `run_exp014.py` / `analyze_exp014.py` with the exact-test module `src/sparkrl/analysis/inference.py` (frozen by sha256 in each study's spec before its first run); verifiers: `verify_paper_claims.py`, `verify_reproducibility.py`, `validate_day31.py`; paper build: `docs/paper/icpe2027/build.py`. Supplementary: `results/evaluation/exp009_robustness.json` (R1–R8), `exp009_ext_analysis.json` (55 traced figures), training analyses (Day-28/29).

## F. Decision log index (methodological decisions cited)

DEC-007 backend freeze; DEC-010 failure semantics; DEC-011 mode gate (multi-step NO); DEC-012/013 EXP-003 reconciliation and validation gate; DEC-015 three replicate arms; DEC-016 baseline specifications; DEC-018 test-seal conversion; DEC-030 EXP-008 methodology; DEC-037 record integrity; DEC-040/042/043 EXP-009 authorization, adjudication, and extension; DEC-044 paired-statistic reporting; DEC-045 deposit plan; DEC-046 paper hardening; DEC-047/048 Track-E (B0′ arm X6; validation confirmations X1–X3); DEC-049/050 (SC7 pilot X10; Taxi pilot X9); DEC-051 demo rehearsal; DEC-052 X-family provenance close-out; DEC-053 EXP-013 confirmatory re-evaluation (pre-registered, signed 2026-10-02); DEC-054 EXP-014 overhead confirmation (pre-registered, signed 2026-10-02). Full texts in `DECISIONS.md`.

## G. Data and artifact availability

Committed and tracked in the repository: source (`src/`), scripts, the frozen decision log (`DECISIONS.md`), the test suite and the reproducibility harness (16/16 checks pass from committed artifacts alone), `results/evaluation/*.json` (including the five X-family / Track-R analysis JSONs), the EXP-002/005/009 raw base records (the 4.8 MB extension records included), figures, and this manuscript. Held in the working tree and **deposit-pending under DEC-045 D1–D11**: the raw X-family observations (`results/experiments/x*`, excluded by the `results/**` ignore rule) — held, not yet archived. No URL and no DOI is invented. Full provenance notes: `docs/research/CLAIM_EXPERIMENT_MAP.md` §Provenance notes (DEC-052 D2).
