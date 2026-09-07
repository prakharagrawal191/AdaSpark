# AdaSpark — Frozen Project Execution Plan

> **This file is the frozen project execution plan.**
> Approved in the planning phase (2026-09-07). Any change requires a new `DEC-xxx` entry in
> `DECISIONS.md` and explicit user/supervisor approval. The 50-day schedule, milestones,
> experiment IDs, research questions, hypotheses, feasibility gates, Plan B, Definition of
> Done, and architecture decisions below are authoritative.

---

## 0. Environment Audit (ground truth, measured — Day 0/1)

| Item | Value | Class |
|---|---|---|
| OS / CPU / RAM | Windows 11 Home 64-bit (26200) / Intel Core Ultra 9 275HX, 24 logical cores / 32 GB | fact |
| GPU | RTX 5070 Laptop 8 GB | NOT NEEDED |
| Disk | 534 GB free (C:) | fact |
| Java | Temurin 17.0.20.1, JAVA_HOME set | REQUIRED |
| Python | 3.12.10 (Day-1 env kept recoverable); 3.11.9 added Day 2 | REQUIRED |
| Spark | initially absent → pip PySpark (see DEC-006 / DEC-007) | REQUIRED |
| Hadoop/winutils | absent → 3.3.6 shim at `%USERPROFILE%\hadoop` | REQUIRED (Windows) |
| Docker / WSL2 | present / present (no Linux distro) | OPTIONAL fallback |
| Kubernetes / conda | kubectl via Docker Desktop / absent | NOT NEEDED / not needed |

## 1. Executive Summary

**AdaSpark** closes the loop *workload → monitoring → state → RL agent → Spark configuration → execution → metrics → reward → learning*. Primary objective: **median end-to-end execution time**; secondary: **task-duration imbalance** and **spill waste**. Selected architecture: **hybrid offline-initialization + online fine-tuning** — a small controlled grid scan proves configuration sensitivity (feasibility gate), calibrates T_ref, and pre-initializes a tabular Q-function; ε-greedy Q-learning then adapts online within ≤500 cached executions. Deep RL (DQN/PPO), clusters, Kubernetes, and microservices are excluded. Evaluation: 5 workload families × 3 scales, frozen unseen test set, 5–7 baselines incl. a rule heuristic and equal-budget random search, 5 seeded repetitions, Wilcoxon signed-rank + Cliff's δ + Holm correction. The existential risk (config insensitivity) is tested Days 23–24, before any RL is built.

## 2. Proposed Research Problem

**Problem statement.** Given a fixed, parameterized big-data pipeline executed on a known single-node Spark deployment, learn — from a strictly limited number of online executions — a policy π: s → a mapping compact state s (workload context + runtime feedback) to a discrete execution-configuration action a, such that median end-to-end execution time improves relative to (i) Spark's default configuration, (ii) a static hand-tuned configuration, and (iii) a non-RL rule-based adaptive heuristic, under both seen and unseen workload conditions, within a bounded training budget and without failed submitted configurations.

**Motivation.** Spark exposes ~200 configuration knobs; defaults are rarely optimal and optimal settings shift with data scale, skew, and operator mix. Manual tuning goes stale under workload drift — the classic self-adaptive (MAPE-K) setting — while Spark already emits rich runtime telemetry that default execution ignores.

**Research gap (verified against the literature matrix, Days 6–10; not asserted before verification).** Published Spark auto-tuning work clusters into: (a) offline Bayesian-optimization tuners producing one static config per workload type; (b) deep-RL approaches requiring thousands of executions and cluster resources; (c) DBMS-side learned optimizers not operating on Spark configuration. Under-explored: **sample-efficient online adaptation (tabular/bandit RL) for Spark config selection on single-node deployments, with offline-initialization, an execution cache, validated comparison against strong non-RL heuristics, and explicit unseen-workload generalization.**

**Aim.** Determine whether a sample-efficient RL agent can make a Spark big-data workload self-adaptive — measurably reducing execution time and improving resource-efficiency indicators versus static and rule-based configuration strategies — within the budget of a single 32 GB machine.

**Hypotheses.**
- **H1 (sensitivity gate):** on shuffle/join-heavy workloads, the action space spans ≥10% median execution-time difference on this hardware.
- **H2:** the trained policy reduces median execution time ≥10% vs Spark defaults on ≥half of test workloads (p < 0.05, paired).
- **H3:** the policy is never significantly worse than, and on ≥half of test workloads better than, the rule heuristic and equal-budget random search.
- **H4:** on unseen scale/skew workloads, the policy retains ≥50% of its seen advantage and never falls below the default.

**Success criteria.** SC1 = H1 gate passes · SC2–SC4 = H2–H3 accepted statistically · SC5 = H4 accepted · SC6 = training ≤500 executions, monitoring overhead ≤5% of job time · SC7 = re-run reproducibility within ±5% · SC8 = tests green; repo reproducible from fresh clone.

## 3. Research Questions

- **RQ0 (gate):** How sensitive is execution time of shuffle/join-heavy Spark workloads to shuffle-partition and parallelism settings on single-node local-mode Spark? *(Days 23–24; pivot path pre-agreed if insufficient.)*
- **RQ1:** Which state representation yields better policies — workload context only, or context + runtime feedback?
- **RQ2:** Does the learned policy outperform Spark defaults, static tuning, a data-size rule heuristic, and random search of equal budget?
- **RQ3:** Does the policy generalize to unseen data scales, unseen skew profiles, and an external public dataset, and what is the degradation?
- **RQ4:** How do reward-function variants and action-space granularity affect learning stability and final policy quality?
- **RQ5:** What are the training cost (number of Spark executions) and the runtime overhead of the adaptation loop?
- **RQ6:** How does the agent interact with built-in AQE — does it add value on top of AQE-on defaults?

## 4. Objectives

**O1** reproducible single-node Spark+Python environment (M1) · **O2** parameterized workload suite (5 families × 3 scales) + seeded synthetic generators (M5) · **O3** monitoring pipeline (event logs + psutil) with a fixed metrics schema (M6) · **O4** config-sensitivity grid scan and statistical feasibility gate (Days 23–24) · **O5** RL environment + tabular Q-learning agent with offline initialization and execution cache (M7–M8) · **O6** main comparison, generalization, ablation, AQE-complementarity, and overhead experiments with statistical validation (M9–M11) · **O7** thesis, verified literature matrix, visualization suite, reproducible repository, presentation, live+backup demo (M12–M14).

## 5. Research Gap

Verification protocol: literature matrix of 25–30 rows from IEEE Xplore, ACM DL, Springer, ScienceDirect, arXiv, and official Spark documentation, using search strings: *"Spark configuration tuning reinforcement learning"*, *"Spark auto-tuning Bayesian optimization"*, *"self-adaptive big data systems"*, *"reinforcement learning resource allocation cluster"*, *"learned query optimization"*, *"MAPE-K autonomic computing"*, *"Spark adaptive query execution evaluation"*. No paper is cited before its row is verified. Novelty claims (§6) are re-checked at Day 10 against the completed matrix.

## 6. Expected Contribution

| Tier | Content |
|---|---|
| Known techniques (applied, honestly labeled) | tabular Q-learning / ε-greedy bandits; Spark configuration knobs; event-log metrics extraction |
| Adaptation of known | Spark configuration selection cast as a contextual-bandit / small-MDP problem with discretized workload-context states |
| Engineering contribution | AdaSpark: integrated, configuration-driven, cached, reproducible adaptivity loop (monitor → state → decide → configure → measure → learn) with a resumable experiment runner |
| Experimental contribution | controlled, seeded, statistically tested comparison across 5–7 baselines incl. random-search-equal-budget and AQE-on/off conditions, on 5 workload families with a frozen unseen test set |
| Potentially novel (verified Day 10) | (1) hybrid offline-grid initialization + online fine-tuning with an execution cache for sample-efficient Spark adaptation; (2) state encoding fusing workload-manifest context with prior-run runtime feedback; (3) generalization evidence of such a policy on single-node Spark |

## 7. Scope Decisions (locked)

Single-node local-mode Spark (`local[N]`); no cluster (the policy operates on metrics, not cluster behavior). AQE **off** in the main study so pre-execution configuration selection is well-defined; AQE-on is a dedicated comparison condition (RQ6) — AQE adapts shuffle partitions per-shuffle at runtime but does not choose job-level parallelism, caching, or broadcast strategy pre-execution, and does not learn across workloads. Training/validation/test split is leakage-guarded; the test set stays frozen until Day 31.

## 8. System Concept

```
Workload manifest ─► Monitoring Layer ◄── Spark Execution (config a) ─┐
 (family, scale,  │  (event logs + psutil)        ▲                   │
  skew, seed)     ▼                               │                   │
 Feature/State Extraction ─► RL Agent ────────────┘                    │
 (discretize → s)                  │ action a                          │
                                   ▼                                   │
 Configuration Application (SparkSession)                              │
 Metrics Collection ─► Reward Computation ─► Q-update ─► next decision │
        └────────► results store / run manifest (+ execution cache) ───┘
```

Components: workload registry; seeded data generators; Spark runner (session lifecycle, config application, warm-up, timeout); monitoring (event-log parser primary, psutil secondary); state encoder; reward calculator; agent (Q-learning/bandit); execution cache (hash of workload+seed+config+code-version); experiment runner (YAML-driven, resumable, immutable manifests); analysis (stats + plots).

## 9. Candidate Architectures

| Criterion | A: Offline surrogate (grid/BO → static config) | B: Pure online RL | **C: Hybrid offline-init + online adapt + cache (SELECTED)** |
|---|---|---|---|
| Complexity | Low | High | Medium |
| Research value | Low (static output) | High | High (adaptive + sample-efficient) |
| Spark executions | 150–300 | 1000s (infeasible) | ~600–900 total, cache-bounded |
| Reproducibility | High | Medium | High |
| 50-day feasibility | High | Low | High |
| Evaluation risk | Low | High variance | Medium (standard stats) |
| Unseen workloads | No (re-tune) | Unproven cheaply | Yes — tested explicitly |

The offline grid is not wasted work: it is the sensitivity gate (RQ0), the reward-normalization source (T_ref), the Q-table initialization, and the fallback contribution. Architecture B's DQN/PPO variant is rejected (sample cost ≫ budget).

## 10. Recommended Architecture (AdaSpark)

Data flow: `configs/*.yaml` → generators build/validate Parquet datasets → runner loads workload instance → (bandit mode: one decision per episode; optional multi-step mode: decisions at 3 pipeline phases) → state = discretize(context ∨ + last-feedback) → agent picks a ∈ 12 actions → runner applies config (session restart if parallelism changed), runs warm-up micro-job, then timed pipeline with event log + psutil → parser extracts metrics → reward computed vs T_ref → Q-update → JSONL run record + checkpoint → next episode. Every execution is uniquely keyed and cached; every run writes an immutable manifest; failure/timeout ⇒ reward −1.

## 11. Spark Design

pip-installed PySpark on Java 17; driver memory 6 GB; `spark.eventLog.enabled=true` (uncompressed JSON) under the external data root; Spark local dirs outside OneDrive. Session per configuration; changing parallelism (`local[N]`) ⇒ session restart (startup excluded from measured time via warm-up micro-job). **Workload families:** F1 Aggregation (multi-key groupBy + window sums — stresses shuffle partitions); F2 Join (fact × 20–40 MB broadcastable dimension — stresses broadcast threshold/partitions); F3 RDD sort+filter+reduceByKey (stresses `default.parallelism`); F4 Skewed join (Zipf(1.5) keys — stresses partitioning under skew); F5 Mixed 3-phase pipeline (ingest-clean → join → aggregate-write; intermediate consumed twice — makes caching meaningful). **Scales:** S ≈ 0.3 GB, M ≈ 1 GB, L ≈ 3 GB Parquet. Controlled: AQE off (main study), fixed versions, fixed warm-up, timeout = 5× default-config median.

## 12. RL Formulation

Environment = Spark execution + monitoring wrapper (gymnasium `Env` API). State s = discretized context (§13). Action a = one of 12 discrete configurations (§14). Transition: bandit mode — s → terminal (one decision per episode); multi-step mode — s_t = (context, phase_t, feedback) across 3 pipeline phases. Reward r = §15. Episode = one full workload execution under one selected configuration (bandit) or one pipeline under 3 sequential decisions (multi-step). Policy = ε-greedy over Q. γ = 0 (bandit, default) or 0.9 (multi-step, gated Day 30). Update: Q(s,a) ← Q(s,a) + α[r − Q(s,a)] (γ=0) or standard Q-learning with γ·max_a′Q(s′,a′).

## 13. State Space

**v1 (15 contexts):** `workload_class ∈ {agg, join, rdd_sort, skew_join, mixed}` × `input_size_bin ∈ {S<512MB, M 0.5–2GB, L>2GB}`. **v1.5 (30):** + `feedback_bin ∈ {last_reward ≤ 0, > 0}`. Features: workload_class and size bin from the manifest (available before execution); skew encoded via class (skew_join); last-run feedback from the previous episode record; execution time, shuffle read/write, spill, task-duration CV, stage/task counts, CPU%, RSS — collected **after** execution for reward, logs, and multi-step mode, never fabricated pre-decision. Missing features at decision time ⇒ run-failure path (reward −1, logged). Continuous features are min-max normalized against EXP-002-calibrated ranges (reward/plots only); the tabular states are already discrete.

## 14. Action Space

**v1 — 12 actions:** `spark.sql.shuffle.partitions ∈ {16, 32, 64, 128}` × execution parallelism (`local[N]`, `spark.default.parallelism=N) ∈ {2, 4, 8}`. **v2 (ablation/extension only, +4):** `spark.sql.autoBroadcastJoinThreshold ∈ {10MB, −1}` × cache {persist MEMORY_ONLY on intermediate, off}. Rejected as actions: executor memory (OOM risk on fixed hardware), dynamic allocation (off in local mode), arbitrary JVM/IO knobs. Timeout guard converts pathological configs into reward −1, never hangs. Max action space ever used: 16.

## 15. Reward Function

Candidates: R1 = −T/T_ref (unbounded — rejected); R2 = clip(ΔT, −1, +1), ΔT=(T_ref−T)/T_ref (adopted primary); R3 = R2 + efficiency terms (**selected**); R4 = −ln(T/T_ref) (ablation variant).
**Final formula (weights in `configs/reward.yaml`):**

```
R = 1.0·clip((T_ref − T)/T_ref, −1, +1)
  + 0.2·(1 − min(1, CV_task/0.5))                             # task-imbalance penalty
  − 0.2·min(1, (spill_disk_bytes/input_bytes)/0.10)           # spill waste penalty
  − 1.0·1[failure or timeout]
```

T_ref = default-configuration time for the same workload instance + seed, calibrated once (EXP-002/003) and stored in the manifest; used only for reward normalization — never shown to the agent as state. Stability: clipping; constant step-size α (noisy rewards); failures capped at −1; evaluation uses median-of-5 repetitions only.

## 16. RL Algorithm Selection

**Primary: tabular Q-learning (ε-greedy)** — 15–30 states × 12 actions = 180–360 cells; outcomes observed in-episode; sample-efficient; interpretable. Co-primary/fallback: contextual bandit (γ=0). Optional comparison: SARSA (config flag). Stretch: LinUCB only if time remains after Day 37. **Rejected:** DQN / Double DQN / PPO (thousands of samples, neural instability, overkill for 12 actions — documented rationale). Hyperparameters (config-driven): α=0.2; γ∈{0, 0.9}; ε 1.0→0.05 decay 0.95/episode; optimistic init Q₀=+0.5; no replay buffer (tabular); checkpoint every 25 episodes; 3 training seeds {0,1,2}; cap 500 executions; early stop when the greedy policy is stable for 2 consecutive epochs.

## 17. Baselines

| ID | Baseline | Definition | Purpose |
|---|---|---|---|
| B0 | Spark default | out-of-box settings, pinned | vendor reality |
| B0′ | AQE-on default | Spark 3.x factory default (AQE enabled) | modern default + RQ6 |
| B1 | Static global | one config tuned on validation, used everywhere | "tuned once" practice |
| B2 | Static per-family | best validation-grid config per family | near-oracle static bound |
| B3 | Rule-based adaptive | `partitions = clamp(input_GB × k, 16, 128)`; core-count rule for parallelism | the key "is RL needed?" baseline |
| B4 | Random search | uniform over the same 12 actions, same budget as RL | "is it just exploration?" |
| RL | AdaSpark policy | trained Q-policy, frozen before test evaluation | — |

Fairness: identical code path, seeds, repetitions, warm-up, timeouts for all strategies; policy frozen before the test set is opened.

## 18. Dataset Strategy

Primary: seeded synthetic generators (numpy + pyarrow → Parquet): transactions/orders/customers schemas with Zipf-skewed keys for F4; exact scale ladder S/M/L; checksummed. External validity: NYC Taxi subset (~1–2 GB Parquet, fixed month) as an unseen real-data test workload; if download fails, a "pseudo-public" dataset with a non-synthetic statistical profile is generated and the substitution documented. **Split (leakage-guarded):** Train = {F1,F2,F3,F5}×{S,M}×seeds{0,1,2}; Validation = same families × seed{3} (B1/B2 tuning + hyperparameters); **Test (frozen until Day 31)** = all families × {L} × seeds{3,4} + F4 skew (unseen family) + public dataset + F5 with unseen parameters. No instance appears in more than one split; no test metric influences training or tuning.

## 19. Workload Design

Each workload = manifest (family, phase list, input paths, expected shuffle intensity, skew profile) + implementation (`BaseWorkload.run(session, config)`) + phase structure for multi-step mode (F5 has 3 natural phases). Estimated per-run 15–90 s (confirmed in EXP-001). All workloads unit-tested at 5 MB micro-scale.

## 20. Monitoring Architecture

**Primary:** Spark event logs (JSON, uncompressed) parsed post-run → stage/task metrics: shuffle read/write, disk/memory spill, task durations (median, p95, CV), stage/task counts. Deterministic, offline-parseable, reproducible. **Secondary:** psutil sampling (500 ms) of the JVM child process → CPU%, RSS peak. **Tertiary (optional):** Spark REST API. Validation: parsed metrics cross-checked against Spark UI for one run (Day 19).
**Metrics schema (one row per run; Parquet + JSONL):** `run_id, exp_id, workload_id, family, scale, seed, config_json, aqe, shuffle_partitions, parallelism, exec_time_s, throughput_MBps, shuffle_read_MB, shuffle_write_MB, spill_disk_MB, spill_mem_MB, num_tasks, num_stages, task_median_s, task_p95_s, cv_task, cpu_mean_pct, rss_peak_GB, monitor_overhead_s, reward, T_ref_s, cache_hit, timed_out, git_sha, spark_version, timestamp`.

## 21. Experiment Pipeline

`raw seeds → generators → Parquet (families × S/M/L) → workload registry → runner (config apply → warm-up → timed run) → event log + psutil → parser → metrics row → reward → JSONL + Parquet results → analysis`. Formats: Parquet (data + results), YAML (configs), JSONL (run stream/manifests), JSON (manifests/checksums). No database.

## 22. Evaluation Metrics

Primary: median end-to-end execution time (s). Secondary: task-duration CV; spill-disk MB / input GB. Also: throughput MB/s, shuffle read/write, stage/task counts, CPU mean %, RSS peak, adaptation overhead %. Statistics: median ± IQR, mean ± SD, 95% bootstrap CI, paired Wilcoxon signed-rank (paired by workload-instance × seed), Mann-Whitney U where unpaired, Cliff's δ, Holm-Bonferroni correction.

## 23. Experimental Plan

IVs: strategy (B0,B0′,B1,B2,B3,B4,RL), family, scale, seed, ablation variant. DVs: §22 metrics. CVs: Spark/Java/Python versions, AQE flag, power profile, warm-up, timeout policy, quiet-machine protocol. Training = 1 run/episode with cache; **all evaluation = 5 repetitions × fixed seeds, medians analyzed**. Warm-up per session; plugged-in high-performance profile; sync paused; background load constant. All experiments YAML-driven and resumable.

## 24. Ablation Studies (selected 5)

A1 runtime-feedback state removed (RQ1) · A2 workload-context removed (RQ1) · A3 reward variants: time-only (1,0,0) vs final (1,0.2,0.2) vs R4 log-ratio (RQ4) · A4 action space: 4-action minimal vs 12-action full (RQ4) · A5 γ=0 vs γ=0.9 multi-step, only if the Day-30 gate passed (RQ4). Dropped (documented): DQN-vs-Q, ε-vs-UCB, >16 actions, per-knob reward decomposition.

## 25. Generalization Study

Frozen policy (never retrained) evaluated on Test split (unseen scale L, unseen seeds, unseen family F4-skew, unseen F5 parameters, public dataset). Report per workload: RL vs B0/B2/B3 relative improvement seen vs unseen, degradation %, adaptation benefit (first vs steady episode). Acceptance (SC5): unseen RL ≥ B0 on all test instances and ≥50% of its seen relative advantage on ≥half of them. Negative results documented.

## 26. Testing Strategy

Unit: state encoder binning; action→config mapping; reward golden values; cache-key hashing; event-log parser on fixtures; config merge/restoration (pytest). Integration: env reset+step on a 5 MB micro-workload; runner applies/restores config; parser+psutil merge. System: 10-episode adaptive loop on micro data; EXP-002 resume-from-interrupt. Reproducibility: same-seed data checksums; same-seed double-run within ±5%; manifest completeness. Performance: monitoring overhead ≤5%; cache-hit latency <1 s. Fast suite (`-m unit`) <60 s for daily work; full suite before milestone commits.

## 27. Reproducibility Strategy

Pinned `requirements.txt` (exact versions incl. pyspark patch), Python/Java/OS recorded, per-experiment YAML with seeds, dataset regeneration script + checksum manifest, one-command reproduction (`python scripts/run_experiment.py --config …`, `scripts/reproduce_all.sh`), immutable run manifests (git SHA, versions, timestamps), policy checkpoints with training-config hash, `docs/REPRODUCE.md` walkthrough, results convention `results/EXP-XXX/<timestamp>/` (never overwritten). Absolute times are machine-relative; all comparisons are within-machine paired — documented.

## 28. Repository Structure

```
src/sparkrl/{spark,datagen,workloads,monitoring,env,agent,runner,analysis,utils}
scripts/  configs/  experiments/  tests/{unit,integration,system,fixtures}
data/ results/ logs/ plots/  models/policies/  notebooks/  docs/{report,figures,decisions}
README.md  DECISIONS.md  requirements.txt  pyproject.toml
```
(data/results/logs gitignored with .gitkeep; bulk data in external SPARKRL_DATA_ROOT)

## 29. Technology Stack

| Tool | Role | Status |
|---|---|---|
| PySpark 3.5.9 (pinned) | execution engine | frozen Day 2 (DEC-007) |
| Java 17 (Temurin) | JVM | installed |
| Python 3.11.9 (frozen env) | implementation | frozen Day 2 |
| numpy, pandas, pyarrow | generators, data IO, results | research extras (Day 13+) |
| psutil, PyYAML | monitoring, config-driven execution | core |
| gymnasium | Env API convention | Day 25 |
| scipy, scikit-learn | statistics; optional surrogate | core/research |
| matplotlib (+seaborn ≤2 plots) | visualization | research extras |
| pytest | testing | core |
| Jupyter | analysis notebooks only | research extras |
| **Rejected** | SB3/PyTorch (no deep RL); MLflow (JSONL/Parquet manifests suffice); Docker (repro image only); Kubernetes; FastAPI/Flask; Scala; Kafka/streaming | deliberate simplifications |

## 30. Risks and Mitigation

| # | Risk | P | I | Early warning | Mitigation | Fallback |
|---|---|---|---|---|---|---|
| R1 | Windows/Spark IO issues | M | H | Day-2 smoke failures | winutils shim; backend abstraction | WSL2 Ubuntu; Docker |
| R2 | **Configs barely affect runtime (existential)** | M | H | EXP-002 effect <10% (Day 24) | skew/join-heavy workloads, small partition counts, memory pressure, RDD stages | pivot to adaptive caching/partitioning + spill objective; benchmark-framed thesis |
| R3 | Execution noise | H | M | EXP-001 CV >10% | 5 reps, medians, paired stats, quiet protocol | more reps; report variance openly |
| R4 | RL sample cost too high | L-M | M | budget alarm in runner | tabular + cache + offline init | γ=0 bandit mode |
| R5 | Metrics collection fragility | M | M | parser gaps Day 18–19 | event logs primary; validated vs UI | REST API; minimal timing+psutil |
| R6 | Unstable reward | M | M | oscillating Q (Day 28) | clipping, T_ref normalization, failure cap | time-only reward (A3) |
| R7 | Overfitting / leakage | M | M | good train, poor test | frozen test set, unseen family/scale | shrink claims; report honestly |
| R8 | Timeline overrun | M | H | milestone slip >2 days | day-level plan, buffers D38/40/48–50 | drop multi-step, LinUCB, A5 |
| R9 | OneDrive interference | M | L-M | slow IO, file locks | data dir outside OneDrive; pause sync | move repo to C:\sparkrl |
| R10 | AQE masks config effects | M | M | EXP-002 flat with AQE on | AQE off in main study; RQ6 condition | AQE-on-only framing |
| R11 | Novelty challenged | L | M | — | contribution tiering §6; verified matrix | emphasize experimental+engineering contributions |

## 31. 50-Day Detailed Plan (● = heavy Spark-execution day)

| Day | Goal | Deliverable | Validation |
|---|---|---|---|
| 1 | Repo + env scaffold | ENVIRONMENT_REPORT.md; pinned venv; git scaffold | SparkSession starts |
| 2 | Spark backend validation + freeze | smoke matrix A–K; DEC-007; frozen requirements | full matrix PASS |
| 3 | Timing harness + baseline job | warm-up/timing/timeout utils | repeat timing CV <10% |
| 4 | Research problem draft | RESEARCH_PROBLEM.md draft | self-review vs §2 |
| 5 | Problem freeze | SC1–SC8 signed off | supervisor note |
| 6–7 | Literature A–C (Spark tuning/AQE/BO) | 15 matrix rows | verified sources |
| 8–9 | Literature D–J (RL-for-systems, MAPE-K, learned optimizers) | 30 matrix rows | verified sources |
| 10 | Gap note | LITERATURE_MATRIX.md v1; novelty tiering | gap cross-checked |
| 11 | Architecture candidates | A/B/C vs 8 criteria (DEC) | criteria table |
| 12 | Architecture freeze | component contracts; diagrams (DEC) | design checklist |
| 13 | Data generators | schema + Zipf skew + scales; checksums | unit tests |
| 14 | Generate datasets | families × S/M/L × seeds | sizes + README |
| 15 | Workloads F1, F2 | aggregation, join (+broadcast hook) | micro smoke |
| 16 | Workloads F3, F4, F5 | RDD sort/filter, skew join, 3-phase mixed | micro smoke ×5 |
| 17 | Baseline calibration | B0 default runs; all workloads via config | M5 |
| 18 | Event-log parser | parser + fixture tests | matches hand-checked log |
| 19 | Metrics merge + schema | psutil sampler; manifest writer | validated vs Spark UI |
| 20 | Experiment runner v1 | YAML runner; cache; resume | integration test |
| 21 | Runner hardening + overhead | runner v1.0; EXP-009 first | overhead ≤5% (M6) |
| 22 | EXP-001 noise calibration | 20-run noise profile | median CV ≤10% |
| 23 | EXP-002 grid scan ● | 192 runs, resumable | queue completes |
| 24 | EXP-002 analysis + GATE | effect sizes; T_ref; GO/pivot (DEC) | SC1 evaluated |
| 25 | RL environment | state/action/reward + gym Env + tests | golden-value tests (M7) |

| 26 | Agent + offline init | tabular Q agent; Q₀ from EXP-002 | unit tests |
| 27 | Training loop | ε schedule; checkpoints; budget guard | smoke training |
| 28 | First full training run ● | bandit-mode training (seed 0) | reward trend ↑ |
| 29 | Training replicates ● | seeds {0,1,2}; policy inspection | policies agree ≥70% (M8) |
| 30 | Mode gate decision | multi-step only if stable (DEC) | decision recorded |
| 31 | Eval harness + B1/B2 | frozen test set; static baselines tuned on validation | configs frozen |
| 32 | EXP-005 main comparison ● | 7 instances × 7 strategies × 5 reps | queue completes |
| 33 | EXP-005 analysis | medians; win/loss; Wilcoxon+δ+Holm | SC2–SC4 (M9) |
| 34 | EXP-006 generalization ● | frozen policy on unseen L/F4/seeds/public | unseen table |
| 35 | Generalization analysis | seen-vs-unseen advantage; degradation | SC5 evaluated |
| 36 | Ablations A1, A2 ● | retrain context-only / feedback-only | ablation rows |
| 37 | Ablations A3, A4 (A5) ● | reward variants; 4-action; multi-step if gated | ablations complete (M10) |
| 38 | AQE complementarity + stats pass | EXP-005b; EXP-009 final; corrected tests | results CSVs |
| 39 | Visualization suite | 12 figures to spec | captions ↔ claims |
| 40 | Interpretation + buffer | claim↔experiment map; rerun buffer | every claim has EXP ID (M11) |
| 41 | Report Ch1–3 | Intro, Background, Literature | draft in docs/report |
| 42 | Report Ch4–6 | Problem, Methodology, Architecture | cross-referenced |
| 43 | Report Ch7–8 | Implementation, Experimental Methodology | matches repo |
| 44 | Report Ch9–10 | Results & Analysis, Discussion | generated results only |
| 45 | Report Ch11–12 + repro audit | Limitations, Conclusion; EXP-011 re-run | ±5%; tests green (M12) |
| 46 | Presentation | 15–18 slides; demo script | slide↔claim mapping |
| 47 | Demo rehearsal | live dry-run ×2; backup packaged (EXP-012) | deterministic <10 min (M13) |
| 48 | Fix + repo audit | issues fixed; full suite; tag v1.0 | DoD partially ticked |
| 49 | Viva rehearsal | Q&A (AQE, novelty, negatives); repro polish | mock viva notes |
| 50 | Final audit + submit | DoD complete; submission | M14 |

## 32. Milestones and Weekly Evidence

M1 Environment Ready — Day 3 · M2 Research Problem Frozen — Day 5 · M3 Literature Review Complete — Day 10 · M4 Architecture Frozen — Day 12 · M5 Spark Baseline Working — Day 17 · M6 Monitoring Pipeline Working — Day 21 · M7 RL Environment Working — Day 25 · M8 First RL Agent Working — Day 29 · M9 Adaptive Optimization Demonstrated — Day 33 · M10 Experiments Complete — Day 37 · M11 Analysis Complete — Day 40 · M12 Final System Complete — Day 45 · M13 Report Complete — Day 47 · M14 Presentation & Demo Complete — Day 50.

Weekly evidence: W1 (D1–5) env report + frozen problem · W2 (D6–12) literature matrix + frozen architecture · W3 (D13–17) datasets + 5 workloads + B0 calibration · W4 (D18–21) monitoring + runner v1.0 · W5 (D22–28) gate decision + RL env + first training · W6 (D29–35) policies + main comparison + generalization · W7 (D36–40) ablations + stats + figures · W8 (D41–45) report draft + repro audit · W9 (D46–50) slides + demo + submission.

## 33. Experiment Register

| ID | RQ | Hypothesis | Workload | Algorithm/Baselines | Runs | Acceptance | Status |
|---|---|---|---|---|---|---|---|
| EXP-001 | noise | run CV ≤10% | F1,F2 × S,M | — | 20 | CV ≤10% | planned |
| EXP-002 | RQ0 (H1/SC1 gate) | ≥10% spread on ≥2 families | 12-config grid × F1,F2,F3,F5 × S,M | — | 192 | GO/pivot decision | planned |
| EXP-003 | support RQ2 | B1/B2 beat B0 | validation split | B0,B1,B2 | ~30 | frozen B1/B2 | planned |
| EXP-004 | H2 prep | Q-learning converges | Train split | tabular Q, 3 seeds | ≤500 (cached) | policies + curves | planned |
| EXP-005 | RQ2 (H2,H3) | RL ≥ heuristics ≥ default | Test split (7 instances) | RL vs B0,B0′,B1,B2,B3,B4 | ~245 | SC2–SC4 | planned |
| EXP-006 | RQ3 (H4) | advantage retained unseen | unseen L/F4/seeds | frozen RL vs B0,B2,B3 | ~100 | SC5 | planned |
| EXP-007 | RQ1 | context+feedback > context-only | Train/Test | A1, A2 variants | ~300 | ablation table | planned |
| EXP-008 | RQ4 | design matters | Train/Test | A3, A4, A5 | ~300 | ablation table | planned |
| EXP-009 | RQ5 | overhead ≤5% | micro + real | — | ~20 | overhead report | planned |
| EXP-010 | external validity | transfers to real data | NYC Taxi subset | frozen RL vs B0,B3 | ~25 | validity row | planned |
| EXP-011 | SC7 | ±5% median | EXP-005 subset | same manifests | ~60 | repro report | planned |
| EXP-012 | demo determinism | identical output twice | demo workload | frozen RL + backup | ~10 | run-book | planned |

## 34. Final Report Structure

12 chapters, each with purpose/sections/evidence/figures/tables: **1** Introduction (contributions tier) · **2** Background (Spark/AQE, RL, MAPE-K) · **3** Literature Review (verified matrix; per-area synthesis; gap) · **4** Problem & Objectives (frozen §2–§4) · **5** Methodology (hybrid architecture rationale; RL formulation; reward design) · **6** System Architecture (components; data flow; cache) · **7** Implementation (generators, workloads, monitoring, env, agent; code quality) · **8** Experimental Methodology (variables; protocol; statistics; budgets) · **9** Results & Analysis (sensitivity; main comparison; generalization; ablations; AQE; overhead) · **10** Discussion (where/why RL wins; threats to validity) · **11** Limitations (single-node; synthetic-first; tabular-only; hardware variance) · **12** Conclusion & Future Work (deep RL, clusters, multi-objective).

## 35. Final Presentation Structure

Title → Motivation → Research gap → Problem + RQs → System architecture → RL formulation → Spark integration + monitoring → Experimental setup → Baselines → Sensitivity gate (EXP-002) → Main results RL vs baselines → Statistical validation → Generalization → Ablations + AQE complementarity → Limitations → Conclusion → Future work → Demo.

## 36. Final Demonstration Plan

**Live** (`scripts/demo.py --mode live`, <10 min, deterministic): fixed-seed F5-mixed S-scale workload → B0 run → B3 run → frozen policy for 3 episodes with printed state/action/reward trace → comparison table + one figure. All printed numbers originate from logged manifests. **Backup** (`--mode backup`): replays stored manifests, regenerates identical tables/figures without Spark. Both modes tested twice on Day 47.

## 37. Definition of Done

[ ] Research problem finalized · [ ] Literature review completed (verified matrix) · [ ] Research gap justified · [ ] Architecture implemented · [ ] Spark baseline implemented · [ ] Monitoring implemented · [ ] RL environment implemented · [ ] RL agent implemented · [ ] Adaptive optimization implemented · [ ] Baseline comparison completed (≥5 baselines) · [ ] Multiple workloads tested (5 families) · [ ] Generalization tested · [ ] Ablation completed · [ ] Statistical analysis completed · [ ] Visualizations completed (12 figures) · [ ] Unit tests passed · [ ] Integration tests passed · [ ] End-to-end system tested · [ ] Reproducibility verified (±5% re-run) · [ ] Results documented · [ ] Final report completed · [ ] Final presentation completed · [ ] Final demo completed · [ ] Backup demo prepared

## 38. Feasibility Assessment (1–5; risk 5 = dangerous)

| Component | Feas | Value | Cplx | Risk | RAG |
|---|---|---|---|---|---|
| Env setup + smoke matrix | 5 | 1 | 2 | 2 | 🟢 |
| Generators + workloads | 4 | 3 | 3 | 2 | 🟢 |
| Monitoring + runner + cache | 4 | 3 | 3 | 2 | 🟢 |
| EXP-002 sensitivity gate | 5 | **5** | 2 | 3 | 🟡 pivot trigger |
| Tabular Q + offline init | 4 | 4 | 2 | 2 | 🟢 |
| Multi-step mode | 3 | 4 | 3 | 3 | 🟡 gated Day 30 |
| Generalization study | 4 | **5** | 2 | 2 | 🟢 |
| Ablations A1–A5 | 4 | 4 | 2 | 2 | 🟢 |
| Statistical validation | 5 | 4 | 2 | 1 | 🟢 |
| Visualization suite | 5 | 3 | 1 | 1 | 🟢 |
| Public-dataset test | 3 | 3 | 2 | 3 | 🟡 substitution path |
| Report/presentation/demo | 5 | 3 | 2 | 1 | 🟢 |
| ~~DQN/PPO~~ | 1 | 2 | 5 | 5 | 🔴 → tabular Q (selected) |
| ~~Cluster / Kubernetes~~ | 1 | 2 | 5 | 5 | 🔴 → single-node (selected) |
| ~~TB-scale datasets~~ | 1 | 2 | 5 | 5 | 🔴 → 0.3–3 GB ladder (selected) |

## 39. Recommended Plan B (three tiers)

1. **Environment tier (R1):** native Windows → WSL2 Ubuntu (install distro) → Docker. Runner abstracts the backend; switch ≤1 day.
2. **Scientific tier (R2):** if the Day-24 gate fails — pivot objective to spill/memory efficiency and adaptive caching decisions; enlarge skew/join stressors; reframe as controlled empirical benchmark of config sensitivity + bandit adaptation vs heuristics. Same codebase; still a complete thesis.
3. **Scope tier (R8):** drop multi-step → drop LinUCB → shrink ablations to A1+A3 → 4-action space. **Minimum viable contribution (protected):** EXP-002 sensitivity study + trained bandit/Q policy statistically matching-or-beating the rule heuristic and beating Spark defaults on ≥2 workload families, fully reproducible.

## 44. Execution Decision Summary (planning phase)

1. **First:** Day-1 environment finalization + Day-2 backend smoke matrix — done before anything else. 2. **Not yet:** no RL code before the Day-24 gate; no deep RL ever; no cluster/K8s; no unverified citations; no test-set access before Day 31; no monolithic notebook; no hard-coded hyperparameters. 3. **Most dangerous risk:** R2 (configuration insensitivity) — mitigated by making EXP-002 the Day-23/24 gate. 4. **Most important research decision:** AQE-off controlled main study + minimal 12-action space + hybrid offline-init/online-adapt architecture. 5. **Minimum viable contribution:** Plan-B tier 3. 6. **Ideal final system:** AdaSpark v1.5 state, 12 actions, cached hybrid training, ablations, generalization + AQE studies, 12-figure suite, 24/24 DoD. 7. **Plan B system:** bandit-mode AdaSpark, 4 actions, benchmark-framed. 8. **Day-1 tasks:** executed 2026-09-07 (commit `ffadd3a`).

*End of frozen plan.*



