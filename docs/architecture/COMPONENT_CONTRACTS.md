# Component Contracts — Candidate C Freeze

*Day 12 companion to ARCHITECTURE_FREEZE.md · conceptual signatures only, no implementation code · another developer implements from this without architectural decisions.*

## 1. Interface contracts

SparkConfig.from_yaml(path)/from_dict(d)/fingerprint()/with_overrides()/to_spark_settings() — invariants: validated ranges, unknown keys rejected, fingerprint = SHA-256(normalized JSON). Errors: ValueError on invalid. SparkWorkload(workload_id, seed).run(spark, config) → WorkloadResult; .reference_check(n) → expected; .validate(result) → bool — deterministic for (rows, seed). SparkRunner.run_workload(spark, workload, config) → RunResult (exists Day 3; timed region = workload.run only). MetricsCollector.collect(run_result, event_log_ref) → RuntimeMetrics (exec_s, imbalance, spill_bytes, overhead_s, provenance{log_used}); missing log → wall-clock-only + flag. StateEncoder.encode(context, metrics_history) → StateVector (schema v1.5; A1 selector drops feedback fields). ActionMapper.to_config(index) → SparkConfig-delta + fingerprint; .validate(index); .subset(mode12|mode4). RewardCalculator.compute(episode_metrics, T_ref) → Reward{R2, eff_terms, R3}; requires T_ref; failures raise, never return number. RLEnvironment.reset(seed, split)/step(action) → (state, cached_flag); refuses test split pre-Day-31; budget guard inside. RLAgent.select(state, ε)/update(transition)/save(version)/load(version); Q-table keyed (context_bucket, action). BaselineStrategy.{id, select(state)→action, describe}; harness-owned RNG. ExperimentCache.lookup(key)→hit|miss; .store(key, episode); .quarantine(key). ExperimentRunner.run(exp_yaml) → manifests; owns seeds/AQE/split gates. ResultManifest.append(row)→hash-chained JSONL. AQEController.mode()→off|on; logged per manifest; flag-only.
## 2. Per-component sheets (ID · Responsibility · Inputs · Outputs · Dependencies · Configuration · Failure · Logging · Test boundary · Research role)

COMP-SPARK-01 Session Manager · validated local-mode sessions · SparkConfig · SparkSession · PySpark/Java/winutils · spark.yaml runtime · explicit startup error, no fallback · app id + version + timings · session create/stop/version-reject · M1/M5 backend.
COMP-SPARK-02 Configuration Manager · YAML→validated config + fingerprint + AQE flag · YAML/dict/action deltas · SparkConfig · none (pure) · spark.yaml · ValueError on unknown/out-of-range · resolved config + fingerprint · from_dict/to_spark/fingerprint round-trips · AQE control surface.
COMP-SPARK-03 Workload Interface · deterministic workloads + reference values · (rows, seed, scale) · WorkloadResult · Spark API · workload section of EXP yaml · ValueError pre-run on bad params; run-errors propagate · workload_id/seed/rows/checksum · Spark-vs-reference equality · supplies RQ0/RQ3 material.
COMP-SPARK-04 Execution Runner · warmup→timed→timeout-cancel→RunResult · (spark, workload, config) · RunResult · 01,02,03 · execution section · timeout→success=false + cancel + grace flag; never invents timing · warmup/exec/total, timeout, app id · warmup-excluded timing, timeout path · all timing evidence.
COMP-MEAS-05 Metrics Collector · wall-clock + event-log parse → RuntimeMetrics · (RunResult, log ref) · RuntimeMetrics · 04 + eventlog dir · monitoring section · missing log→wall-clock-only + flag; missing clock→abort · provenance + overhead_s · determinism of parse; overhead accounting · EXP-009 + state feedback.
COMP-RL-06 State Encoder · context + feedback → versioned StateVector · (WorkloadSpec, metrics history) · StateVector · 03,05 · rl.yaml state_schema · unknown schema→error; unnormalized→error · schema version + field vector · A1/A2 selector equivalence classes · RQ1/EXP-007.
COMP-RL-07 Action Mapper · index ↔ 12 config deltas · action index · (SparkConfig delta, fingerprint) · 02 · rl.yaml action_space · out-of-range→reject pre-exec · index + fingerprint · 12 rows valid; mode4 ⊂ mode12 · RQ4/EXP-008 action arm.
COMP-RL-08 Reward Calculator · metrics + T_ref → R3 · (RuntimeMetrics, T_ref) · Reward · T_ref store · rl.yaml reward_variant/weights · no T_ref→hard error; failed run→raise · R2/terms/R3/T_ref id · R2/R3/R4 formula checks on fixtures · RQ4/EXP-008 reward arm.
COMP-RL-09 RL Environment · Gymnasium-style reset/step with guards · (seeds, split, budget, cache) · (state, cached_flag, done) · 06,07,04,11 · EXP yaml + rl.yaml · test-access→abort; budget-hit→done · split tag + budget count · guard behavior on fixtures · train/test separation owner.
COMP-RL-10 RL Agent · ε-greedy tabular Q + versioned store · (StateVector, ε) · action; update(transition) · 09 · rl.yaml α/γ/ε · update-fail→Q untouched + abort · Q-version + ε + update count · seeded tie-break; save/load round-trip · RQ2 learning claim.
COMP-EXP-11 Cache + Guard · deterministic memo + ≤500 enforcement · CacheKey · hit|miss + EpisodeResult · filesystem lock · cache section · corruption→quarantine+miss; >500→refuse · key + hit flag + count · hit/miss/invalidation matrix · RQ5/SC6.
COMP-EXP-12 Orchestrator · seeds, baselines, AQE, manifests, gates, stats handoff · EXP yaml · manifests + eval tables · all · EXP yaml · any gate violation→loud abort · full resolved config + provenance · manifest schema validation · owns RQ2/RQ6 comparison validity.
## 3. Method-signature reference (conceptual)

```
SparkConfig.fingerprint() -> str  # sha256, 64 hex
SessionManager.build(config) -> SparkSession  # raises RuntimeError
Workload.run(spark, config) -> WorkloadResult  # deterministic
Runner.run_workload(spark, workload, config) -> RunResult
Collector.collect(run_result, log_ref) -> RuntimeMetrics
Encoder.encode(context, history) -> StateVector  # schema v1.5
Mapper.to_config(i: int[0,11]) -> (delta, fingerprint)
Reward.compute(metrics, T_ref) -> Reward  # raises without T_ref
Env.reset(seed, split) -> StateVector  # refuses test pre-Day-31
Env.step(action) -> (next_state, episode, cached: bool)
Agent.select(state) -> int  # epsilon-greedy, seeded ties
Agent.update(s, a, r, s2) -> None  # skipped on failure episodes
Cache.lookup(key) -> Hit(EpisodeResult) | Miss
Guard.check_and_increment(live: bool) -> ok | BudgetExhausted
Orchestrator.run(exp_yaml) -> list[ExperimentManifest]
```

## 4. Data-contract field tables

SparkConfig: master str, app_name str, driver_memory str, ui bool, event_log{enabled,dir}, local_dir, version_prefix str, aqe bool, shuffle int, dflt_parallel int|null, warmup{ ware/runs, micro}, timeout{timeout_s float, grace_s}, workload{rows, scale, seed}. JSON, fingerprint-keyed.
WorkloadSpec: family enum[agg, join, skew, ml, mixed, taxi], scale enum[micro..large], seed int≥0, rows int, aqe enum[off,on], split enum[train,val,test]. Required all.
WorkloadResult: checksum{...}, measurements{...}; deterministic per spec.
RuntimeMetrics: exec_s float>0, task_imbalance float≥0, spill_bytes int≥0, overhead_s float≥0, provenance{log_used bool, log_ref str|null}. Seconds SI.
StateVector: schema str="v1.5", family/scale/skew/mix floats, prev_ratio float, imbalance float, spill_log float; A1 drops last three (schema "v1.5-ctx").
Action: index int 0–11, deltas{parallelism, shuffle_partitions, cache_mode}, fingerprint str.
Reward: R2 float[−1,1], eff_imb float≤0, eff_spill float≤0, R3 float, T_ref float>0 + id str, variant enum[R2,R3,R4].
EpisodeResult: state, action, reward|null on failure, metrics, cache_hit bool, success bool, error str|null.
ExperimentManifest: exp_id, strategy_id, seeds[], config_fingerprints[], aqe_mode, policy_version str|null, rows[][episode summaries], stats_ref str|null; JSONL hash-chained.
CacheKey: workload_id, seed, config_fingerprint, code_version (git sha), env_version (spark|python|java). Key change → miss.
BaselineResult: strategy_id enum[B0,B0p,B1,B2,B3,B4,RL], manifest_ref.
EvaluationResult: medians{}, wilcoxon{p}, cliffs_delta, holm_decision, figure_refs[].
