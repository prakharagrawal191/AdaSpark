# AdaSpark — Self-Adaptive Big Data Programming Using Reinforcement Learning and Spark

AdaSpark is an M.Tech case study in self-adaptive big data programming. A reinforcement learning (RL)
agent chooses the Spark execution configuration — execution parallelism and shuffle partitions — before
each run, measures the outcome, and learns from it inside a hard budget of 500 training executions. The
learned policy is then compared with Spark defaults, tuned static configurations, a rule heuristic and
random search, under pre-registered statistics on a sealed test split.

The study ran from **2026-09-07 to 2026-10-04** on one Windows machine, following a 50-day plan
(`docs/PLAN.md`), and is governed by a numbered decision log (`DECISIONS.md`, DEC-001 to DEC-055). The
case-study report is [`manuscript/AdaSpark_CaseStudy_Report.docx`](manuscript/AdaSpark_CaseStudy_Report.docx).

## At a glance

- **Configuration matters:** choosing a configuration moved median execution time by ≥10% on all four
  tested workload families (EXP-002, gate **PASS**).
- **Bounded learning:** training used 483 of the 500 budgeted executions, with no failed submitted
  configuration.
- **Against Spark defaults:** in the pre-registered confirmatory evaluation (EXP-013, 42 frozen test
  cells) the learned policy was **4.0× faster** than Spark defaults, and at least 10% faster on 36 of 37
  decidable cells — hypothesis H2 **accepted**.
- **Against competent tuning:** the policy was **1.22× slower** than a tuned static configuration, to
  which the rule heuristic and equal-budget random search also resolved — hypothesis H3 **rejected**.
- **Limits stated, not hidden:** the three training seeds disagreed (agreement 0.20 against a 0.70
  target), generalization was not evaluable, the event-log overhead pass was not re-established, and
  the pre-registered √n prediction failed on all seven cells.

## Contents

1. [What the project is about](#what-the-project-is-about)
2. [Key results](#key-results)
3. [Day-wise progress](#day-wise-progress)
4. [Decisions and why they were taken](#decisions-and-why-they-were-taken)
5. [Experiments, runs and hours](#experiments-runs-and-hours)
6. [How the study was governed](#how-the-study-was-governed)
7. [Repository layout](#repository-layout)
8. [Setup, tests and the report](#setup-tests-and-the-report)
9. [Contributors](#contributors)

## What the project is about

**Problem.** Spark jobs usually run under one fixed configuration, although the best setting shifts with
the operator mix, data scale and skew. Manual tuning goes stale as workloads drift, and Adaptive Query
Execution (AQE) covers only some runtime decisions.

**Approach.** AdaSpark closes a monitor–analyze–plan–execute loop (MAPE-K) around Spark:

| Element | What AdaSpark uses |
|---|---|
| Actions | 12 configurations: execution parallelism {2, 4, 8} × shuffle partitions {16, 32, 64, 128} (`local[p]`, AQE off) |
| State | Compact workload context (family, scale) plus runtime feedback |
| Learner | Tabular Q-learning in bandit mode (γ = 0, DEC-011), α = 0.2, ε from 1.0 decaying ×0.95 per episode to 0.05 |
| Initialization | Offline Q₀ derived from the EXP-002 sensitivity grid |
| Reward | R3, a runtime reward against a per-cell reference time; a failed or timed-out run is an observation with reward −1 (DEC-010) |
| Budget | At most 500 training executions (success criterion SC6) |

**Workloads and data.** Five synthetic workload families — F1 aggregation (`F1_agg`), F2 join
(`F2_join`), F3 RDD sort/filter (`F3_rdd`), F4 skew join (`F4_ski`) and F5 three-phase mixed
(`F5_mixed`) — at three scales (S/M/L: 0.0386 / 0.1320 / 0.4042 GB) and several seeds, plus a pilot on
one public NYC Taxi month. Training, validation and test cells are kept apart; the test split is sealed
and opened only by a recorded decision.

**Baselines.**

| ID | Baseline |
|---|---|
| B0 | Spark defaults (`local[2]`, 200 shuffle partitions, AQE off) |
| B0′ | Spark defaults with AQE on (separate comparison, never pooled) |
| B1 | Best single static configuration, tuned on the validation split |
| B2 | Best static configuration per workload family (validation split) |
| B3 | Rule heuristic — collapses onto B1 at these data volumes (DEC-016, confirmed 7/7 by X1) |
| B4 | Random search with an equal budget |
| RL | The frozen learned policy (three training seeds, RL-s0/s1/s2) |

**Scope.** Single-node local-mode Spark on Windows. Deep RL, multi-node clusters and Kubernetes are
excluded by the approved plan.

## Key results

Verdicts are the project's own recorded verdicts (`docs/research/CLAIM_EXPERIMENT_MAP.md`).

| Question | Evidence | Result | Verdict |
|---|---|---|---|
| Does configuration move runtime ≥10%? | EXP-002 | 4/4 tested families sensitive | **PASS** (SC1) |
| Can training stay within 500 executions? | Budget ledger | 483/500 used; 488/500 including 5 disclosed demo runs | **HOLDS** |
| Do the three training seeds agree (M8 ≥ 0.70)? | EXP-004 | Agreement 0.20 on training states; on test inputs the three policies act as one per-family rule | **FAILED** |
| RL faster than Spark defaults (H2)? | EXP-013 | RL/B0 geometric-mean ratio 0.249 (95% CI 0.212–0.295), i.e. 4.0× faster; ≥10% faster on 36/37 cells; Holm-adjusted p = 4.4×10⁻¹¹ | **ACCEPTED** |
| RL faster than the heuristic and random search (H3)? | EXP-013 | RL/B1 1.218 (CI 1.128–1.319); RL/B4 1.206 (CI 1.115–1.309); worse beyond noise on 16 cells, better on 1 | **REJECTED** |
| Identical configurations agree (A/A control)? | EXP-013 | B4 vs B1: median gap 2.0%, 38/38 cells within the ±11.89% noise band | **AFFIRMED** |
| Does the policy generalize to unseen cells (SC5)? | EXP-006 | 61 of 125 runs usable; heavy structural failures on unseen cells | **NOT EVALUABLE** |
| Does AQE-on beat AQE-off on shuffle-heavy jobs? | X6 → EXP-013 | X6 lead (−14.24% on `F2_join` large) not replicated: 0/6 cells faster beyond noise | **NOT REPLICATED** |
| Does the state representation matter (A1/A2)? | EXP-007 | 126 executions; cross-seed agreement 0/4 and 0/2 | **OBSERVED, not causal** |
| Reward and action-space design (A3/A4) | EXP-008 | Derived from existing data only; multi-step A5 not run (DEC-011) | **DERIVED ONLY** |
| Monitoring overhead ≤5% (SC6 clause 2)? | EXP-009, EXP-014 | 1 Hz sampler: 6/7 cells PASS in both studies; event log: 3/7 PASS, 4 inconclusive, 0 fail in the paired re-measurement | Sampler **AFFIRMED**; event log **not re-established** |
| Does interval width shrink with √n? | EXP-009 | Failed on 7/7 cells: repetitions are serially correlated (lag-1 autocorrelation +0.58 to +0.89); about 3,000 of 4,842 runs were unnecessary | **FAILED** |
| Do re-runs reproduce within ±5% (SC7)? | X10, EXP-013 | X10 2/4 cell-arms; EXP-013 vs EXP-005 medians 18/39 | **PARTIAL** |
| Does tuning transfer to real data? | X9 | NYC Taxi month: tuned arms −78.05% / −69.82% vs B0 | **FEASIBILITY** (pilot) |
| Does the live demo run end to end? | EXP-012 | 5/5 runs usable with logged manifests | **HOLDS** |

`F3_rdd` at large scale fails structurally for every arm, from a Windows sort/spill file lock
(`WinError 32`); these cells are recorded as structural failures, not as results.

## Day-wise progress

"Day" is the task day of the approved 50-day plan; several plan days were often completed on the same
calendar date.

| Plan day | Date | Work done | Decisions | Results |
|---|---|---|---|---|
| 1–3 | 2026-09-07 | Repository scaffold and environment audit; PySpark 4.0.4 failed on Windows native I/O; backend frozen on PySpark 3.5.9; timing harness with warm-up, timeouts and a baseline job | DEC-001–007 | Smoke matrix and benchmark validated on the frozen backend |
| 4–5 | 2026-09-07 | Research problem, aims, research questions, hypotheses and success criteria SC1–SC8 written and frozen (milestone M2) | — | M2 consistency audit: 11/11 sections pass |
| 6–10 | 2026-09-08 – 09-09 | Literature review (sources A–J) verified; literature matrix v1 and the evidence-based research gap frozen | — | Literature v1 frozen |
| 11–12 | 2026-09-09 | Architecture candidates A/B/C compared; candidate C frozen: 12 components, 14 interfaces, 12 data contracts, 6 diagrams | DEC-008, 009 | Architecture frozen |
| 13–14 | 2026-09-09 – 09-10 | Deterministic dataset generators with checksums; approved dataset matrix generated and inventoried | — | Measured dataset sizes 0.0386 / 0.1320 / 0.4042 GB (S/M/L) |
| 15–20 | 2026-09-10 – 09-11 | Five workload families; Spark event-log parser and runtime metrics; B0 baseline calibration; parser hardened with hand-checked fixtures | — | B0 baseline established (`docs/BASELINE_B0.md`) |
| 21–24 | 2026-09-11 | EXP-002 configuration-sensitivity grid (208 attempts) and its gate | — | SC1 gate PASS on 4/4 families |
| 25–27 | 2026-09-11 – 09-12 | RL environment with a frozen state, action and reward contract; tabular Q-learning agent with offline Q₀; training loop with ε schedule, checkpoints and budget guard | — | Smoke training runs completed |
| 28–29 | 2026-09-12 – 09-13 | First full training run (seed 0), then replicates on seeds 0/1/2 (84, 49 and 42 episodes) | DEC-010 | Cross-seed agreement M8 FAILED (0.20) |
| 30–31 | 2026-09-13 | Mode gate; evaluation harness and test-identity freeze; B1/B2 tuned on a 96-run validation grid (EXP-003) | DEC-011–013 | Multi-step mode not enabled; B1/B2 frozen |
| 32–33 | 2026-09-14 – 09-15 | Training replicates kept as separate arms; baselines specified; B4 random-search calibration (84/84); EXP-001 noise calibration (20 runs); EXP-005 main comparison (245 queue entries) | DEC-014–019 | B1, B3 and B4 converge on `G-p8-sp16`; noise band ±11.89% |
| 34–35 | 2026-09-16 | EXP-005 closed as descriptive; EXP-006 generalization on a pre-registered subset (125 queue entries) | DEC-020–022 | 61/125 usable; SC5 not evaluable |
| 35–36 | 2026-09-17 | EXP-007 state ablation (A1/A2): method frozen, first authorization refused for budget, scope amended, then approved; 126 training executions | DEC-023–026 | Effect observed, not causal |
| 37–38 | 2026-09-17 – 09-21 | EXP-008 frozen and scoped to a zero-charge derived ablation; budget reconciled; accidental test-suite runs charged; EXP-009 authorized and EXP-005b scoped; EXP-009 first pass (117 runs) | DEC-030–043 | Budget 483/500; first overhead pass INCONCLUSIVE at n = 5 |
| 39–41 | 2026-09-21 – 09-24 | EXP-009 repetition extension, stages 1–7: 4,842 runs over 57.4 hours | DEC-043, 044 | Sampler <5% on 6/7 cells; √n prediction failed |
| 42–43 | 2026-09-24 – 09-26 | Archival deposit plan, its amendment, deposit decisions and tooling | DEC-045 | Deposit tooling in place |
| 44–45 | 2026-09-28 | ICPE 2027 paper hardened: claim verifier rewritten, reproducibility check scoped | DEC-046 | — |
| 46 | 2026-09-29 | Extension studies X1–X3, X6 (EXP-005b), X8, X9 (EXP-010), X10 (EXP-011); EXP-012 demo rehearsal; provenance close-out | DEC-047–052 | AQE-on lead −14.24% (later not replicated); NYC Taxi feasibility; reproducibility 2/4 |
| 47 | 2026-10-02 | EXP-013 confirmatory re-evaluation and EXP-014 overhead confirmation pre-registered and run; report built into the course template | DEC-053–055 | H2 accepted; H3 rejected; AQE-on lead not replicated |
| 48 | 2026-10-04 | Report compliance pass; EXP-014 analysis recorded; repository prepared for publication | — | Sampler affirmed; event-log pass not re-established |

## Decisions and why they were taken

Every scope change, authorization and verdict is a numbered entry in [`DECISIONS.md`](DECISIONS.md).
DEC-027 to DEC-029 were never used (recorded in DEC-031); DEC-030 lives in
`docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md`.

| ID | Date | Decision | Why |
|---|---|---|---|
| DEC-001 | 2026-09-07 | Keep the Python virtual environment outside the repository | The repository sits in a OneDrive-synced folder; thousands of venv files cause sync churn and file locks |
| DEC-002 | 2026-09-07 | Keep bulk data in `%USERPROFILE%\sparkrl_data` (override with `SPARKRL_DATA_ROOT`) | Avoids OneDrive interference with bulk I/O and keeps the repository light |
| DEC-003 | 2026-09-07 | Start on PySpark 4.0.4, with 3.5.x or WSL2 as fallback | 4.0 supports the installed Python 3.12 and Java 17 (superseded by DEC-007) |
| DEC-004 | 2026-09-07 | One `src/sparkrl/` package mapped onto the planned architecture | Gives every planned component one importable home |
| DEC-005 | 2026-09-07 | Run Spark natively on Windows (local mode), provisionally | Java 17 and the PySpark wheel were already present; to be confirmed by the Day-2 smoke matrix |
| DEC-006 | 2026-09-07 | Record why PySpark 4.0.4 fails on Windows native I/O | Startup fails without a Hadoop shim; the evidence ruled 4.0.4 out on this machine |
| DEC-007 | 2026-09-07 | Freeze the backend: Python 3.11.9, PySpark 3.5.9, Java 17, winutils 3.3.6 shim | PySpark 3.5.9's Hadoop 3.3.4 client matches the shim: a reproducible backend over newer features |
| DEC-008 | 2026-09-09 | Select architecture candidate C (offline initialization + bounded online adaptation + cache) | Chosen against eight design criteria; explicitly not a performance claim |
| DEC-009 | 2026-09-09 | Freeze candidate C's contracts and interfaces | Settles the open design questions before any implementation |
| DEC-010 | 2026-09-12 | A failed run is an observation: reward −1, and the update is applied | Two frozen documents disagreed on failed runs; training was blocked until this was settled |
| DEC-011 | 2026-09-13 | Keep bandit mode (γ = 0); do not run the multi-step ablation A5 | The plan allows multi-step only if training is stable; the gate resolved no, so the plan's first scope fallback applied |
| DEC-012 | 2026-09-13 | Run the B1/B2 selection (96 validation runs) as a separate authorized phase | No validation observation existed, so the register's ~30-run estimate could not select B2 |
| DEC-013 | 2026-09-13 | Open a validation-only execution path; use one repetition for B1/B2 selection | Approving a budget does not open an execution path: the runner refused every validation cell |
| DEC-014 | 2026-09-14 | Authorize test-split execution for EXP-005 (approved through DEC-018) | The test split is sealed; the main comparison needed a scoped opening |
| DEC-015 | 2026-09-14 | Evaluate the three training seeds as separate arms RL-s0/s1/s2 | M8 failed (0.20), so there is no single policy to evaluate |
| DEC-016 | 2026-09-14 | Specify B0′, B3 and B4; record that B3 collapses onto B1 | At these data volumes the heuristic yields 16 partitions at every scale, identical to B1 |
| DEC-017 | 2026-09-14 | Adopt the EXP-005 methodology review, amending DEC-015/016 | Evidence found in review; e.g. B4's calibration is normalized because cell runtimes span 2.21–36.67 s (16.6×) and raw medians would favour fast cells |
| DEC-018 | 2026-09-14 | Resolve every open decision; the self-imposed supervisor gate becomes an author decision; EXP-005 unblocked (245 runs) | The gate was the project's own control, not an institutional rule; the plan requires decisions to be recorded |
| DEC-019 | 2026-09-15 | Record 15 B2 × unseen-family entries as incomplete instead of improvising a configuration | B2 has no tuned configuration for an unseen family, and tuning on the test split is forbidden |
| DEC-020 | 2026-09-16 | Close EXP-005 as descriptive; H2, H3 and SC2–SC4 left undecided, not failed | The protocol named the tests but froze no parameters, so no confirmatory verdict was possible |
| DEC-021 | 2026-09-16 | Correct DEC-020's cell list; run EXP-006 as a pre-registered 5-cell subset | One cell was already used by EXP-005; the full 36-cell universe would need about 840 runs |
| DEC-022 | 2026-09-16 | Authorize EXP-006, bound to its sealed specification | The test split stays sealed for every study without its own decision |
| DEC-023 | 2026-09-17 | Freeze the EXP-007 state ablation: training only, two seeds, 168 planned executions | Only 184 training executions remained, so two seeds instead of three |
| DEC-024 | 2026-09-17 | Refuse EXP-007's training authorization | The planned maximum (168) exceeded the remaining budget (164) |
| DEC-025 | 2026-09-17 | Reconcile the budget and shorten EXP-007's horizon | Fits the ablation inside the authoritative remaining budget |
| DEC-026 | 2026-09-17 | Approve EXP-007, bound to the amended code fingerprints | Approval is tied to fingerprints of exactly the code that runs |
| DEC-030 | 2026-09-17 | Freeze the EXP-008 method (A3 reward variants, A4 action space); execution not authorized | Settles the method; budget and implementation each need their own decision |
| DEC-031 | 2026-09-18 | Reconcile the training budget: 462/500 charged, 38 remaining, no cap change | EXP-008 needed an authoritative remaining figure before it could be sized |
| DEC-032 | 2026-09-18 | Mark a validator assumption obsolete; authorize a later validator-only repair | The check assumed a frozen ledger that authorized spending had already changed |
| DEC-033 | 2026-09-19 | Charge six accidental test-suite training executions (468/500) | A full `pytest tests` run started live Spark; execution records are disclosed and counted, never deleted |
| DEC-034 | 2026-09-20 | Scope EXP-008 as a zero-charge derived ablation; cap not amended | Too little budget remained for trained arms; the report must say they were not trained |
| DEC-035 | 2026-09-20 | Adopt the EXP-008 implementation with three fields deferred | The method freeze required an implementation decision backed by Spark-free tests |
| DEC-036 | 2026-09-20 | Resolve all eighteen EXP-008 method fields; drop the A3-R4 variant | Those fields were left open by DEC-030; A3-R4 could not be specified |
| DEC-037 | 2026-09-20 | Record-integrity closure: missing log entry supplied, live-Spark tests gated, hashes made line-ending independent | Validators read decision headings from the log, so a missing entry is a functional failure |
| DEC-038 | 2026-09-20 | Charge the 2026-09-20 accidental test-suite runs (15 executions): 483/500 | Same rule as DEC-033 |
| DEC-039 | 2026-09-21 | Produce the zero-charge derived EXP-008 ablation; trained arms stay unauthorized | Worst-case charge 0; trained arms would need method choices left open |
| DEC-040 | 2026-09-21 | Authorize EXP-009 (monitoring overhead) on the validation split, outside the training budget | SC6's overhead clause had no measurement at all |
| DEC-041 | 2026-09-21 | Freeze EXP-005b at B0′ alone (35 runs, own ledger) | AQE-on results may not be pooled with AQE-off, and no B0′ driver existed yet |
| DEC-042 | 2026-09-21 | Record EXP-009's first result as INCONCLUSIVE, not failed | At n = 5 every cell's 95% interval straddled both 0 and the 5% gate |
| DEC-043 | 2026-09-21 | Extend EXP-009 repetitions per cell from the measured interval widths | To make the gate decidable, not to obtain a particular verdict |
| DEC-044 | 2026-09-24 | Report the paired overhead analysis only as a labelled secondary result; pre-register it for future work | Adopting it retroactively would pick a statistic for its outcome on data already seen |
| DEC-045 | 2026-09-26 | Settle the archival deposit choices and tooling | Reproducibility from a fresh clone (SC8) could not be shown until those choices were made |
| DEC-046 | 2026-09-28 | Harden the ICPE 2027 paper's verification machinery | Brings the paper and its claim checks to submission quality |
| DEC-047 | 2026-09-29 | Run EXP-005b: B0′ (AQE on) on 7 frozen test instances × 5 repetitions | Settles the planned AQE-on/off comparison |
| DEC-048 | 2026-09-29 | Run validation-only confirmations X1, X2, X3 | Closes three cheap open gaps without touching the test split or the training budget |
| DEC-049 | 2026-09-29 | Run the EXP-011 reproducibility pilot (20 test re-runs) | EXP-011 had no evidence; drift seen in X8 called for a small pilot first |
| DEC-050 | 2026-09-29 | Run the EXP-010 external-data pilot on one NYC Taxi month | EXP-010 was empty; synthetic-only data was the sharpest external-validity gap |
| DEC-051 | 2026-09-29 | Rehearse the EXP-012 live demo (5 training-split runs on its own ledger line) | The live demo is a planned deliverable; only its rehearsal is authorized |
| DEC-052 | 2026-09-29 | Close out extension-study provenance and sync the claim map and report (an author draft, not signed) | A gate check failed on five new analysis files; the remaining gap was record-keeping |
| DEC-053 | 2026-10-02 | Pre-register and run EXP-013: frozen arms on 42 frozen test cells, randomized interleaved blocks with an A/A control | Makes H2 and H3 decidable, which EXP-005 had left open |
| DEC-054 | 2026-10-02 | Pre-register and run EXP-014: overhead re-measured with the paired statistic | DEC-044 had pre-registered that statistic for future measurement |
| DEC-055 | 2026-10-02 | Waive EXP-013's two-failure halt for `F3_rdd` medium seed 4 only | The halt was triggered by the documented Windows file-lock failure, while the static arms completed on the same cell |

## Experiments, runs and hours

Counts and times come from each study's run ledger under `results/experiments/` and the training
manifests under `results/training/` (raw ledgers are kept outside Git; DEC-002, DEC-045). **Spark time**
is the sum of recorded job execution times; **elapsed** is first-to-last run timestamp, including
warm-ups and pauses.

| Study | Date | Runs (usable) | Spark time | Elapsed | Outcome |
|---|---|---|---|---|---|
| EXP-001 noise calibration | 2026-09-14 | 20 (20) | 0.1 h | — | Noise band ±11.89% |
| EXP-002 sensitivity grid | 2026-09-11 | 208 (189 completed, 19 failed) + 39 in a discarded first pass | 1.1 h | 2.7 h | SC1 PASS, 4/4 families |
| EXP-003 B1/B2 selection | 2026-09-13 | 96 validation runs | — | — | B1/B2 frozen |
| B4 random-search calibration | 2026-09-14 | 84 (84) | — | — | Selects `G-p8-sp16` |
| EXP-004 training | 2026-09-12 | 42 episodes (first run) + 175 (seeds 0/1/2: 84, 49, 42) | — | 0.2 h + 0.8 h | M8 failed (0.20) |
| EXP-005 main comparison | 2026-09-14 – 09-15 | 245 queue entries (195 usable) | 1.1 h | — | Descriptive; superseded by EXP-013 |
| EXP-006 generalization | 2026-09-16 | 125 (61) + 7-run dry slice | 0.3 h | — | SC5 not evaluable |
| EXP-007 state ablation | 2026-09-17 | 126 training executions (2 variants × 2 seeds) | — | 0.6 h | Observed, not causal |
| EXP-008 reward/action ablation | 2026-09-21 | 0 (derived from existing data) | — | — | Derived only |
| EXP-009 monitoring overhead | 2026-09-21 – 09-24 | 117 (70) + 4,842 timing-valid (3,228 with event log) | 0.6 h + 14.7 h | 57.4 h | Sampler 6/7 PASS; √n refuted |
| X1–X3 validation confirmations | 2026-09-29 | 19 (16) | <0.1 h | — | B3 ≡ B1 7/7; sampler and event-log checks descriptive |
| X6 = EXP-005b AQE on | 2026-09-29 | 35 (30) | 0.4 h | — | Lead later not replicated |
| X8 `F2_join` rematch | 2026-09-29 | 10 (10) | <0.1 h | — | Earlier lead not replicated (−0.57%); ran outside DEC-048's scope, disclosed in DEC-052 |
| X9 = EXP-010 NYC Taxi pilot | 2026-09-29 | 20 (20) | <0.1 h | — | Feasibility established |
| X10 = EXP-011 reproducibility pilot | 2026-09-29 | 20 (20) | <0.1 h | — | 2/4 within ±5% |
| EXP-012 demo rehearsal | 2026-09-29 | 5 (5) | <0.1 h | — | Holds |
| EXP-013 confirmatory evaluation | 2026-10-02 | 900 queue entries (790 usable) | 2.4 h | 10.3 h | H2 accepted; H3 rejected |
| EXP-014 overhead confirmation | 2026-10-02 | 270 timing-valid (180 with event log) | 1.5 h | 4.8 h | Sampler affirmed; event log not re-established |
| Smoke training runs | 2026-09-12 – 09-20 | 36 executions | — | 0.1 h | 21 of them charged as accidental (DEC-033, DEC-038) |

**Totals.** About 22.2 hours of recorded Spark job time across the experiment ledgers, plus about
1.7 hours of training and smoke episodes. The four long campaigns (EXP-002, EXP-009, EXP-013, EXP-014)
took about 75 hours elapsed. The training budget ended at 483/500 (488/500 including the 5 disclosed
demo runs); validation and test studies run on their own ledger lines outside that cap.

**Machine.** Windows 11 (build 10.0.26200), Intel CPU with 24 logical cores, 31.4 GB RAM, Python 3.11.9,
Java 17.0.20.1, PySpark 3.5.9 in local mode.

## How the study was governed

- **Decision log.** Every scope change, authorization and verdict is a numbered entry in
  `DECISIONS.md`. The log is append-only: later entries record the file's SHA-256 before each append.
- **Pre-registration.** EXP-013 and EXP-014 froze their hypotheses, analysis code (SHA-256-bound) and
  stop rules before the first run (DEC-053, DEC-054).
- **Sealed test split.** Test cells are opened only by a recorded decision (DEC-018, DEC-022, DEC-047,
  DEC-049, DEC-053).
- **Budget ledger.** Training is capped at 500 executions; accidental runs are charged and disclosed,
  never deleted (DEC-033, DEC-038).
- **Validators.** `scripts/validate_*.py` check the committed record against Git `HEAD`.
- **Commit IDs.** IDs quoted in the records predate publication;
  [`docs/COMMIT_ID_MAP.md`](docs/COMMIT_ID_MAP.md) maps each one to its published commit.
- **Negative results kept.** Failed gates, refuted predictions and unreplicated leads stay in the record
  and the report.

## Repository layout

```
src/sparkrl/        package: spark/ datagen/ workloads/ monitoring/ agent/ rl/ training/ evaluation/ experiments/ analysis/ runner/ utils/
scripts/            experiment drivers, analyses, validators and environment checks
configs/            Spark, RL, reward and baseline configuration (YAML)
experiments/        experiment registry (registry.csv) + per-experiment YAML configs
data/ results/ logs/ plots/   generated artifacts (bulk data lives OUTSIDE the repo — see below)
tests/              unit/ integration/ fixtures/
docs/               PLAN.md, ENVIRONMENT_REPORT.md, research/ (decision and audit records), architecture/, report/, paper/, figures/
manuscript/         case-study report (AdaSpark_CaseStudy_Report.docx) with its sections, figures and build script
DECISIONS.md        decision log (DEC-001 to DEC-055)
models/policies/    trained policy checkpoints (small JSONs, committed)
notebooks/          analysis/EDA only — core logic always lives in src/
```

## Setup, tests and the report

**Environment** (Windows 11 · Python 3.11.9 · Java 17 · PySpark 3.5.9, frozen by DEC-007). The virtual
environment lives **outside** the repository because the repository sits in a OneDrive-synced folder
(DEC-001/DEC-002).

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe" -m venv "$env:USERPROFILE\sparkrl_env311"
& "$env:USERPROFILE\sparkrl_env311\Scripts\Activate.ps1"
pip install -r requirements.txt
pip install -e . --no-deps
python scripts/env_check.py     # regenerates docs/ENVIRONMENT_REPORT.md + environment_report.json
```

Bulk data (datasets, Spark event logs, Spark temp) is written to `%USERPROFILE%\sparkrl_data` by default;
override it with `SPARKRL_DATA_ROOT`. No absolute paths are hard-coded in code.

**Tests.** Integration tests start real Spark jobs and are skipped unless explicitly enabled (DEC-037):

```powershell
python -m pytest tests                                  # unit tests; integration tests are skipped
$env:SPARKRL_ALLOW_SPARK = "1"; python -m pytest tests/integration   # live Spark; may write manifests that count against the training budget
```

**Timing harness.** `python scripts/run_smoke_warm.py --config configs/spark.yaml` checks timing
stability (target: warm CV < 10%); details in `docs/day03_timing_harness.md`.

**Report.** `manuscript/build_docx.py` builds `manuscript/AdaSpark_CaseStudy_Report.docx` from
`manuscript/sections/*.md` into the official course template.

**Research gates (must not be violated).**

- No RL implementation before the Day-24 configuration-sensitivity gate (EXP-002) passes.
- No deep RL (DQN/PPO), no multi-node clusters, no Kubernetes — approved exclusions.
- AQE is OFF in the main study; AQE-on is a separate comparison condition (EXP-005b).
- The full approved planning document is committed as `docs/PLAN.md`.

## Contributors

- [@prakharagrawal191](https://github.com/prakharagrawal191) — author and maintainer

Licensed under the Apache License 2.0 (see [`LICENSE`](LICENSE)).
