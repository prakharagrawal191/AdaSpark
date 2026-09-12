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

## 9. Implemented contract — Day 25 (RL environment) — 2026-09-11

The Day-25 implementation realizes the frozen COMP-RL-06..09 contracts exactly as specified above. Authoritative implementation record: `docs/research/DAY25_RL_ENVIRONMENT_AUDIT.md`. Frozen plan sections: §12 (bandit mode), §13 (state), §14 (actions), §15 (reward), §16 (budget), §18 (splits).

| Frozen contract | Implemented by | Notes |
|---|---|---|
| COMP-RL-06 State Encoder | `sparkrl.rl.state.StateEncoder` / `StateVector` | v1 (15) + v1.5 (30) discrete states; bins from dataset manifests; no-history feedback convention `le0` (pinned by tests); unknown schema -> error; missing input size -> error |
| COMP-RL-07 Action Mapper | `sparkrl.rl.action.ActionMapper` | reuses the frozen EXP-002 grid (12 points, fingerprint-verified); mode4 subset {0,3,6,9}; pre-execution rejection of out-of-domain actions; B0 is reference, never an action |
| COMP-RL-08 Reward Calculator | `sparkrl.rl.reward.RewardCalculator` + `configs/reward.yaml` | frozen R3 formula; weights frozen-validated at load (tamper -> error); failed/timeout -> exactly -1.0; missing CV/input_bytes -> term 0 + recorded; missing T_ref -> `TRefMissing` BEFORE execution |
| COMP-RL-09 RL Environment | `sparkrl.rl.env.SparkTuningEnv` | bandit-mode reset/step; guards: split (TRAIN only, `SplitViolation`), budget (default 500, `BudgetExhausted` at episode boundary), episode (`EpisodeDone`); execution fully delegated to `sparkrl.experiments.runner.execute_run`; transition records atomic + deterministic; `cached=False` is the stable COMP-EXP-11 boundary; NO learning/policy/cache implemented |

T_ref source: `sparkrl.rl.tref.TRefStore` (read-only over the EXP-002 gate artifact `t_ref_calibration`, seed 0). Deferred to Day 26+: COMP-RL-10 agent, COMP-EXP-11 cache + durable budget enforcement, COMP-EXP-12 orchestrator.

## 10. Implemented contract — Day 26 (tabular Q agent + policy store) — 2026-09-x

Day-26 implementation realizes COMP-RL-10 (frozen PLAN section 16). See `docs/research/DAY26_RL_AGENT_AUDIT.md`.

| Frozen element | Implemented by | Notes |
|---|---|---|
| Agent | `sparkrl.agent.q_learning.QLearningAgent` (`tabular-q/v1`) | Q key = `StateVector.key()`; rows 12-wide (frozen action order); alpha=0.2, gamma in {0.0, 0.9}, eps 1.0 -> 0.05 @ 0.95/episode, Q0 default +0.5 (configs/rl.yaml, frozen-validated) |
| Update rule | `QLearningAgent.update` | Q += alpha*(r + gamma*maxQ(s'') - Q); terminal never bootstraps; invalid transition -> Q untouched + raise |
| Epsilon-greedy | `select_action` / `end_episode` | seeded RNG owned by the agent; lowest-index tie-break; mode4 = selection subset {0,3,6,9} |
| Offline Q0 | `sparkrl.agent.q0.build_q0_from_exp002` | EXP-002 TRAIN records only (LeakageError otherwise); per-observation frozen R3 reward vs T_ref; median aggregation (PLAN section 22); B0 excluded; unnormalizable counted+skipped; evidence-free pairs default +0.5 |
| Policy store | `sparkrl.agent.policy_store` | `policy/v1` JSON, fingerprint identity (excludes policy_id/created_utc); immutable (PolicyExistsError); verified load (PolicyCorrupt / PolicyVersionMismatch) |
| Deferred | COMP-EXP-11 cache + durable budget; orchestrator | not implemented |

## 11. Implemented contract — Day 27 (training loop) — 2026-09-12



Day-27 implementation realizes PLAN line 273 (epsilon schedule; checkpoints; budget guard; smoke training) over the frozen COMP-RL-09 environment and COMP-RL-10 agent. It adds no new frozen contract: the loop is the driver that composes them. See `docs/research/DAY27_TRAINING_LOOP_AUDIT.md`.



| Frozen element | Implemented by | Notes |

|---|---|---|

| Training loop | `sparkrl.training.loop.run_training` (`training-loop/v1`) | owns the schedule, episode log, manifest, checkpoint cadence, epoch/early-stop rule and the `last_reward` thread; owns no Spark, no reward, no T_ref, no budget counter; `env` is duck-typed (real env or unit-test fake) |

| Episode schedule | `trainable_cells` + `plan_episodes` | DERIVED from `TRefStore.calibrated_keys()` x `split_of() == TRAIN` at dataset seed 0 (7 cells; `F3_rdd|medium` excluded, reason `t_ref_null`); fixed RNG-free round-robin over sorted cells; `rep = epoch index` keeps each transition record path unique |

| Epsilon schedule | `agent.end_episode()` | called exactly once per completed episode, after the update; the loop performs no epsilon arithmetic; `epsilon_used` on line k == `epsilon_after` on line k-1 |

| Checkpoints | `policy_store.build_policy_artifact` + `save_policy` | every 25 episodes AFTER `end_episode()`, plus one final checkpoint on any clean stop; none after a mid-step interrupt or an abort; write-only (resume deferred to Day 28+); written to `<run_dir>/checkpoints`, never `models/policies/`; `init_provenance` stays pure Q0 provenance so ids remain content-addressed |

| Early stop | `greedy_snapshot` over `agent.q_table()` | epoch = one full pass over the planned cell cycle (`episodes_per_epoch = len(cells)`, derived); fires on 3 identical consecutive snapshots (2 stable comparisons); never probes via `select_action`/`q_values` (both would perturb the run); a budget-saving heuristic, never evidence of convergence |

| Budget guard | `env.budget_remaining` / `BudgetExhausted` | the loop keeps no counter; `--budget` may only LOWER the frozen 500 cap; pre-flight refuses `episodes > budget_limit` before any Spark; `BudgetExhausted` is a clean stop (`truncated`, exit 0); smoke executions COUNT against SC6; cross-run totals are REPORTED by `scripts/validate_rl_training.py`, enforcement is COMP-EXP-11 (deferred) |

| Records | `episodes.jsonl` (append + flush + fsync) + `manifest.json` (tmp + `os.replace`) | `rl-training-episode/v1` and `rl-training-run/v1`; join via `env_run_id` + `transition_record_relpath` (and `episode_key`/`rep` back from the env record); reward is COPIED from `env.step` and names its source; no metrics and no `execution_time_s` copied; every manifest carries a machine-readable `learning_claim` block asserting no learning/convergence claim |

| Configuration | `configs/rl.yaml` `training:` block + `TrainingConfig.from_yaml` | additive block only; hard-errors (`RLConfigError`) on drift of 25 / 2 / dataset seed 0 / the epoch definition / `live_execution_cap: 500` / `training_seeds: [0,1,2]`; episode counts deliberately live on the CLI, not in config |

| Seeds | `agent_rng_seed` vs `dataset_seed` | `agent_rng_seed` = PLAN section 16 training seed = EXPLORATION replicate (reaches `QLearningAgent(rng_seed=)` only); `dataset_seed` = workload instance seed, fixed 0 because T_ref is calibrated for dataset seed 0 only; both names appear on every record, no bare `seed` key, and the CLI has no `--seed` flag |

| Deferred | resume-from-checkpoint; COMP-EXP-11 cache + durable budget; COMP-EXP-12 orchestrator | not implemented |



Open item for the operator, recorded not resolved: section 3's *conceptual*

signature list above says `Agent.update(...)` is "skipped on failure

episodes", while PLAN sections 10/13/15 make a failure a first-class

observation with reward -1. The Day-27 loop follows PLAN and applies the

update on failed episodes; sign-off is requested before the Day-28 run

(`DAY27_TRAINING_LOOP_AUDIT.md` section 12).

Review record (Day 27). The workflow's Fix agent and its frozen-drift review
lens were rate-limited and never ran; the remaining findings were verified and
applied by the operator afterwards. Applied: a pre-execution `env.step` guard
(`TRefMissing` / `SplitViolation` / `EpisodeDone` / `BudgetExhausted`) no
longer stamps `interrupted_mid_step` or an uncertain budget story, because the
execution counter is exact in that case; `visited_state_keys` is now reset at
each epoch boundary (it had been ACCUMULATING across epochs, so epoch 2
reported keys it never visited - caught by
`test_visited_state_keys_are_scoped_to_their_own_epoch`); the calibration
refusal for dataset seeds 1/2 no longer reads as a split refusal; the rep
handed to `env.reset` is now pinned by a test; and the audit's abort-coverage
and test-count claims were corrected. One review test that asserted a mid-step
`KeyboardInterrupt` propagates was removed: the loop catches it and returns
exit 130, which `test_interrupt_during_step_writes_no_checkpoint` already
covers. NOT independently reviewed: the frozen-drift lens (its one known
defect, a UTF-8 double-encode of this file, was found and reverted by the
operator).
