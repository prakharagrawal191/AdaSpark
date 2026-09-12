# Day 28 - First full bandit-mode training run (agent seed 0) Audit

Every number in this document is read from the stored artifacts of the run of
record - `results/training/train-a0-d0-20260912T083120Z/{manifest.json,
episodes.jsonl, checkpoints/, transitions/}` - via `scripts/analyze_day28.py`,
whose deterministic report is
`results/training/train-a0-d0-20260912T083120Z/analysis/day28_analysis.json`
(`day28-analysis/v1`, 31820 bytes, sha256
`3ad92f8073014f4775ecd370d6c03d676b495c3793f0ea3f0ad7cbb72cd850cd`). No value
below was typed by hand and none was recomputed under a different formula. The
analyzer resolves its `--run` argument, so that sha256 is reproducible from any
spelling of the run directory (absolute, relative, or one containing `..`).

## 1. Objective

Execute and document the run named by frozen `docs/PLAN.md` line 274:
`| 28 | First full training run | bandit-mode training (seed 0) | reward trend
up |`. The run was executed by the operator; this deliverable is **analysis,
validation and documentation of artifacts that already exist** - no Spark, no
training and no integration suite was run to produce it.

**Day 28 is an OBSERVATION, not a result.** One agent seed, one dataset seed,
42 episodes, no baseline, no replicate. Nothing here supports a claim that the
agent learned, converged, improved execution time, or beat anything. Section 16
states in as many words which sentence the artifacts do support and which they
do not.

## 2. Frozen training configuration

Read off `manifest.hyperparameters` (which the loop copies from `agent.config`,
itself loaded from `configs/rl.yaml`, `rl_yaml_sha256` `4bb71750e51c8ea6...`),
all of it a PLAN section 16 transcription:

| parameter | value | role |
|---|---|---|
| `alpha` | 0.2 | learning rate |
| `gamma` | 0.0 | **bandit mode** - terminal transitions never bootstrap |
| `epsilon_start` / `epsilon_min` / `epsilon_decay` | 1.0 / 0.05 / 0.95 | per-episode schedule |
| `q0_default` | 0.5 | optimistic default for pairs with no EXP-002 evidence |
| checkpoint cadence | every 25 episodes | PLAN section 16 |
| early stop | greedy policy stable for 2 consecutive epochs | PLAN section 16 |
| `live_execution_cap` | 500 | frozen research budget |

Run identity: `run_id` `train-a0-d0-20260912T083120Z`, `run_kind` `training`,
`loop_version` `training-loop/v1`, `record_schema_version` `rl-training-run/v1`,
`code_version` `6d85481-dirty`, window `2026-09-12T08:31:20Z` ->
`2026-09-12T08:42:29Z` (669 s wall for 42 live Spark executions plus session
startup). Terminal state: `status=completed`,
`stop_reason=early_stop_policy_stable`, `exit_code=0`.

**PLAN freezes no episode count for Day 28 and no numerical reward-trend
threshold.** The planned 84 episodes (12 epochs x 7 cells) were derived by the
operator from frozen constants only and entered on the CLI, exactly as Day-27
section 19 requires; `manifest.schedule.episodes_planned = 84`. 84 is a plan
figure, not a frozen one, and the run did not reach it (section 11).

## 3. Seeds - two different names, both on every record

`manifest.seed_semantics` (verbatim): *"agent_rng_seed = PLAN section 16
training seed (exploration replicate); dataset_seed = workload instance seed
(T_ref calibrated for dataset seed 0 only)"*.

* `agent_rng_seed = 0` - seeds `QLearningAgent`'s own `random.Random` and
  nothing else. It selects **which exploration draws happen**, i.e. it indexes
  the replicate in the PLAN section 16 set {0,1,2}. Day 29 varies it.
* `dataset_seed = 0` - selects **which workload instance is executed**
  (`env.reset(seed=...)`). It is pinned to 0 because T_ref is calibrated for
  dataset seed 0 only; seeds 1 and 2 are legitimately TRAIN but uncalibrated and
  are refused at plan time, seed 3 is VALIDATION and seed 4 is TEST.

`manifest.policy_rng_seed_is_agent_rng_seed = true`. Both names appear on the
manifest and on all 42 episode lines, and no episode line carries a bare `seed`.
**The transition records carry neither name.** Each of the 42 records instead
carries a bare `"seed": 0` twice - under `metrics` and under
`observation_before` - which is the DATASET seed and nothing else; the agent
seed does not appear there at all. The episode log, not the transition record,
is therefore the seed-provenance join point: every line carries
`agent_rng_seed`, `dataset_seed`, `env_run_id`, `episode_key` and
`transition_record_relpath`, and the last three are what join it to its record.
Confusing the two seeds would make an exploration replicate look like a workload
replicate, so validator check 02 asserts this exact shape on both sides rather
than leaving it to prose.

## 4. Training-cell schedule

The cell set is derived at plan time - `TRefStore.calibrated_keys()` intersected
with `split_of(family, scale, dataset_seed=0) == TRAIN` - never hard-coded.
`manifest.schedule` records 7 cells, `episodes_per_epoch = 7`, order
`fixed_round_robin_over_sorted_cells`, epoch definition
`one_full_pass_over_the_planned_cell_cycle`:

| # | cell | T_ref (s) |
|---|---|---|
| 1 | F1_agg\|medium | 36.669743 |
| 2 | F1_agg\|small | 22.347372 |
| 3 | F2_join\|medium | 16.126881 |
| 4 | F2_join\|small | 2.214523 |
| 5 | F3_rdd\|small | 25.109380 |
| 6 | F5_mixed\|medium | 32.759411 |
| 7 | F5_mixed\|small | 3.903756 |

`manifest.schedule.excluded_cells` carries exactly one entry:
`{"cell": "F3_rdd|medium", "reason": "t_ref_null", "t_ref_s": null}`. The eighth
TRAIN cell is excluded by the frozen null-T_ref rule - its EXP-002 B0 panel was
invalid, so no normalizer exists and the frozen R3 reward cannot be formed - and
the exclusion is RECORDED in the artifact, not silently dropped. T_ref source:
`exp002-gate:gate.json`, `t_ref_gate_sha256` `e30a7b0c953d9965...`.

Scale `large`, family `F4_ski`, dataset seed 3 and dataset seed 4 appear nowhere
in the episode log, in any transition record or in any record path.

## 5. Q0 provenance

`manifest.q0_provenance` (`q0-exp002/v1`), carried verbatim into every
checkpoint's `init_provenance`:

| field | value |
|---|---|
| `source` / `aggregation` | `exp002` / `median` |
| `records_scanned` | 208 |
| `records_valid_used` | 167 |
| `records_invalid_skipped` | 17 |
| `records_tref_missing_skipped` | 8 (`tref_missing_cells: ["F3_rdd\|medium"]`) |
| `records_b0_reference` | 16 |
| `pairs_initialized` | 4 |
| `spec_fingerprint` | `9fb5cb51f74fe37f9883a8fdc27636926990d9a8528403fde70c97769b29303e` |
| `leakage_guard` | `split_of()!=TRAIN -> hard error; none encountered` |
| `reward_formula` / `state_schema` / `grid_fingerprint` | `R3` / `state-v1.5` / `97d70dc18a1d...` |

The partition balances: 208 = 167 + 17 + 8 + 16. `pairs_initialized = 4` counts
initialized Q ROWS - the four `le0` state keys (`agg|S`, `join|S`, `mixed|S`,
`rdd_sort|S`), whose `pair_observation_counts` block enumerates 4 x 12 = 48
(state, action) entries. Every pair with no EXP-002 evidence keeps the
optimistic +0.5 at access; no evidence from a non-TRAIN cell entered Q0.

## 6. Learner version

`contract_versions.learner_version = tabular-q/v1` (COMP-RL-10, frozen Day 26),
`policy_schema = policy/v1`. The loop performed no learning arithmetic of its
own: 42 of 42 episodes recorded `updated=true`, 0 recorded an `update_error`,
and every update used the agent's frozen rule with `gamma=0.0` on a terminated
transition, so the target was the reward itself.

## 7. State / action / reward versions

`manifest.contract_versions`, read off the duck-typed environment and never
recomputed:

| contract | value |
|---|---|
| `env_version` | `spark-tuning-env/v1` |
| `state_schema` | `state-v1.5` |
| `action_mode` | `mode12` (all 12 grid actions selectable) |
| `grid_fingerprint` | `97d70dc18a1d5369928964201f2169fd0eebfb8c3c747001900a472885819ba1` |
| `reward_formula` | `R3` |
| `base_config_fingerprint` | `9270d2ce2dcaa57e3c01a6c218ce4e88d5ef6a201298115d59a076d19b8be7e1` |

Reward provenance: all 42 lines carry `reward_source = "env.step (frozen R3)"`,
and each line's `reward` is byte-equal to `reward.value` in its own transition
record. The loop copies; it never computes. Timing stays the frozen Day-3 runner
clock (`execution_time_source = "runner"` on all 42 records).

Action usage over the 42 episodes (`action_source` is the best-effort "equals
the greedy action" label, not a branch trace):

* explore 15 / exploit 27.
* action index counts: `4`=19, `8`=9, `6`=3, `1`=2, `10`=2, `11`=2, `0`=1,
  `2`=1, `3`=1, `5`=1, `9`=1, **`7`=0**.
* `actions_never_taken = [7]`. Action index 7 is config `G-p4-sp128`; it was
  never selected in 42 episodes. The analyzer emits the full 0..11 domain, so a
  zero count appears as `7`=0 instead of vanishing from the table - 11 of the 12
  grid actions were observed, not 12.
* config names: `G-p4-sp16`=19, `G-p8-sp16`=9, `G-p4-sp64`=3, `G-p2-sp32`=2,
  `G-p8-sp128`=2, `G-p8-sp64`=2, and one each of `G-p2-sp128`, `G-p2-sp16`,
  `G-p2-sp64`, `G-p4-sp32`, `G-p8-sp32`. `G-p4-sp128` is absent.

## 8. Epsilon schedule

Frozen schedule `epsilon_used[n] = max(0.05, 1.0 * 0.95 ** n)`, n from 0, with
`agent.end_episode()` the only mutator. Re-checked against the log two ways by
the analyzer: value-wise against the closed form, and by chaining
(`epsilon_used[k] == epsilon_after[k-1]` on every line). Result:
`matches_frozen_schedule = true`, 0 value mismatches, 0 chaining mismatches -
epsilon was decayed exactly once per completed episode.

Observed trajectory: 1.0 (episode 1) -> 0.12208654873684793 (episode 42).
`floor_reached = false`: the 0.05 floor arrives at episode 60 and this run
stopped at 42, so the floored regime was never observed (Limitation 2).

## 9. Budget accounting

`manifest.budget`:

| field | value |
|---|---|
| `live_execution_cap` | 500 |
| `budget_limit_this_run` | 84 |
| `live_executions` | 42 |
| `budget_remaining` | 42 |

`live_executions = 42` equals the 42 executed episodes and the 42 files under
`transitions/`; `cached_records = 0` (no cache exists - COMP-EXP-11 deferred).

Cross-run SC6 ledger = the SUM of `budget.live_executions` over EVERY manifest
under `results/training/`, smoke runs included:

| run | kind | live executions |
|---|---|---|
| `train-a0-d0-20260912T052836Z` | smoke | 3 |
| `train-a0-d0-20260912T081149Z` | smoke | 3 |
| `train-a0-d0-20260912T081451Z` | smoke | 3 |
| `train-a0-d0-20260912T081737Z` | smoke | 3 |
| `train-a0-d0-20260912T082054Z` | smoke | 3 |
| `train-a0-d0-20260912T083120Z` | training (this run) | 42 |
| **total** | 6 manifests | **57** |

57 of the frozen 500 are spent; 443 remain. This total is **REPORTED, never
ENFORCED**: `manifest.budget.enforcement` says *"in-run only; the env counter is
per-process. Cross-run SC6 totals are the SUM over manifests, REPORTED not
enforced (COMP-EXP-11 deferred)"*. Two concurrent processes could jointly exceed
500 and neither would notice.

## 10. Checkpoint behavior

Cadence every 25 episodes AFTER `end_episode()`, plus exactly one final
checkpoint on the clean stop. `manifest.checkpoints` holds two entries and both
artifacts exist under `checkpoints/` and verify through
`policy_store.load_policy`:

| episode_index | policy_id (16) | episodes | updates | epsilon (post-decay) |
|---|---|---|---|---|
| 25 | `43bdde3e490a3c41` | 25 | 25 | 0.27738957312183365 |
| 42 | `4f74a0f4f088c030` | 42 | 42 | 0.11598222130000553 |

`manifest.final_policy` names the episode-42 artifact (`policy_id`
`4f74a0f4f088c0300c22a6676e222d4b65ab0cc79de71bf6e35b1719294799e3`). Each
artifact's `episodes` counter equals its `episode_index`, confirming the
checkpoint was taken after the decay. Nothing was written to `models/policies/`
- that directory is reserved for deliberately published policies.

Final Q table (read from the final checkpoint, not recomputed): 8 state rows,
96 (state, action) pairs, 66 differing from the optimistic default 0.5, value
range [-0.21358006318610337, 0.8955304384348249]. The 8 rows are the 4
Q0-seeded `le0` rows plus 4 `gt0` rows created during the run when a positive
previous reward changed the feedback bin.

| state key | greedy action | greedy value | pairs != 0.5 |
|---|---|---|---|
| `state-v1.5\|agg\|S\|gt0` | 8 | 0.8410910165694572 | 3 |
| `state-v1.5\|agg\|S\|le0` | 8 | 0.8955304384348249 | 12 |
| `state-v1.5\|join\|S\|gt0` | 4 | 0.7304499862492907 | 5 |
| `state-v1.5\|join\|S\|le0` | 8 | 0.8343570406538554 | 12 |
| `state-v1.5\|mixed\|S\|gt0` | 4 | 0.7118032693713977 | 4 |
| `state-v1.5\|mixed\|S\|le0` | 9 | 0.8072918368967217 | 12 |
| `state-v1.5\|rdd_sort\|S\|gt0` | 4 | 0.5076442899991570 | 6 |
| `state-v1.5\|rdd_sort\|S\|le0` | 7 | 0.5089242455603278 | 12 |

Greedy action = argmax with ties broken to the lowest index. These are stored
table values, not recommendations, and `pairs != 0.5` is a table-shape count,
not a measure of anything learned.

## 11. Execution count

| quantity | value |
|---|---|
| episodes planned | 84 (12 epochs x 7 cells) |
| episodes completed | 42 |
| epochs completed | 6 of 12 planned |
| episode log lines | 42 |
| transition records under `transitions/` | 42 |
| live executions | 42 |
| planned episodes never run | 42 |

The run halted at the epoch-6 boundary because the frozen early-stop rule fired:
`stop_reason = early_stop_policy_stable`, `early_stop.triggered = true`,
`at_epoch = 6`, `stable_epochs_required = 2`, rule *"greedy snapshot identical at
3 consecutive epoch boundaries"*. Recomputed from the per-epoch snapshot hashes:

| epoch | greedy snapshot sha256 (12) | stable vs previous | stability streak | visited state keys |
|---|---|---|---|---|
| 1 | `039b9789f35e` | false | 0 | 5 |
| 2 | `aa3d0fbb8f13` | false | 0 | 4 |
| 3 | `f438ca857c8b` | false | 0 | 4 |
| 4 | `10c31762a5ec` | false | 0 | 4 |
| 5 | `10c31762a5ec` | true | 1 | 4 |
| 6 | `10c31762a5ec` | true | 2 | 4 |

The greedy argmax stopped moving after epoch 4 and the stop fired at epoch 6.
**This is a budget-saving heuristic and nothing more.** It measures argmax
movement over the whole Q table - including Q0-seeded rows nobody visited, which
is why each epoch record also carries `visited_state_keys`. It is
not evidence of convergence. The 42 unspent executions returned to the frozen
500 are the entire benefit claimed for it.

## 12. Reward trajectory

All 42 rewards are the frozen R3 values copied from `env.step`.

Overall: n=42, mean 0.7384545220637554, median 0.7766737867086928, min
0.29475074773727966, max 0.923882195186552.

Per epoch (7 episodes each, one full pass over the 7 cells):

| epoch | n | mean | median | min | max |
|---|---|---|---|---|---|
| 1 | 7 | 0.6882236919776851 | 0.7663 | 0.2948 | 0.9239 |
| 2 | 7 | 0.7267457964300391 | 0.7258 | 0.4735 | 0.9128 |
| 3 | 7 | 0.7426633632961820 | 0.8290 | 0.4299 | 0.8677 |
| 4 | 7 | 0.7360076976035026 | 0.7482 | 0.3874 | 0.9014 |
| 5 | 7 | 0.7642852492646147 | 0.8701 | 0.3432 | 0.9190 |
| 6 | 7 | 0.7728013338105088 | 0.8532 | 0.5382 | 0.9151 |

(Median/min/max at the analyzer's 4-decimal display precision; the full-precision
per-episode series is `reward.per_episode` in `day28_analysis.json`.)

Per cell, reps aggregated (cell identity is `family|scale`; each cell was
visited once per epoch, so n=6 everywhere):

| cell | n | mean | median | min | max |
|---|---|---|---|---|---|
| F1_agg\|small | 6 | 0.9002058034686260 | 0.9139 | 0.8290 | 0.9239 |
| F1_agg\|medium | 6 | 0.8488472794406023 | 0.8595 | 0.7663 | 0.8851 |
| F5_mixed\|medium | 6 | 0.8471273603382730 | 0.8587 | 0.7792 | 0.8701 |
| F2_join\|medium | 6 | 0.8094237038145584 | 0.8489 | 0.6654 | 0.8857 |
| F2_join\|small | 6 | 0.7434250250129678 | 0.7465 | 0.7059 | 0.7742 |
| F5_mixed\|small | 6 | 0.5903095463276457 | 0.6484 | 0.2948 | 0.6743 |
| F3_rdd\|small | 6 | 0.4298429360436147 | 0.4184 | 0.3432 | 0.5382 |

The between-cell spread (0.4298 to 0.9002 in cell means) is larger than the
whole across-epoch movement, so a per-epoch mean is dominated by which cells it
contains - here every epoch contains each cell exactly once, which is the only
reason the epoch means are comparable at all.

**Composition is not concentration.** Equal composition makes the epoch means
comparable; it does not make the movement between them broadly based. Because
each epoch mean is `sum_cell (1/7) * cell_mean`, the epoch-6-minus-epoch-1
difference splits exactly over the 7 cells. `per_cell_trend_descriptive` in the
analysis artifact carries this split (`contribution_sum = 0.08457764183282372`,
the headline difference to 15 decimals), together with every epoch mean
recomputed with that one cell dropped:

| cell | epoch 1 | epoch 6 | delta | share of 0.0846 | % | last-first without it | OLS slope without it |
|---|---|---|---|---|---|---|---|
| F5_mixed\|small | 0.2948 | 0.6272 | +0.33242759024961316 | +0.04748965574994474 | 56.1 | 0.04326931709669213 | 0.009419619966230613 |
| F3_rdd\|small | 0.4068 | 0.5382 | +0.13141546354771566 | +0.018773637649673665 | 22.2 | 0.0767713382136751 | 0.01656459193396812 |
| F1_agg\|medium | 0.7663 | 0.8627 | +0.09641828959638699 | +0.013774041370912427 | 16.3 | 0.08260420053889661 | 0.014980035528945588 |
| F2_join\|small | 0.7059 | 0.7538 | +0.047901241041374054 | +0.006843034434482008 | 8.1 | 0.09069037529806534 | 0.015903422439439725 |
| F2_join\|medium | 0.8558 | 0.8594 | +0.0036500300347912518 | +0.000521432862113036 | 0.6 | 0.09806557713249586 | 0.014840837079683467 |
| F1_agg\|small | 0.9239 | 0.9151 | -0.008767012963542875 | -0.001252430423363268 | -1.5 | 0.10013508429888485 | 0.017403488081378843 |
| F5_mixed\|medium | 0.8642 | 0.8532 | -0.011002108676572142 | -0.0015717298109388775 | -1.9 | 0.10050760025105654 | 0.016658185365386914 |

Two of the seven cells moved DOWN from epoch 1 to epoch 6. One cell,
`F5_mixed|small`, supplies 56.1% of the headline difference, and its epoch-1
value (0.29475074773727966) is the global minimum over all 42 episodes, so the
share comes from a low anchor rather than a high finish - its epoch-6 value
(0.6272) sits below its own median (0.6484). Dropping that single cell leaves
0.04326931709669213 (a 49% reduction) and an OLS slope of 0.009419619966230613
(a 38% reduction). This is arithmetic, not an explanation: it says where the
difference sits, not what produced it (Limitation 14).

## 13. Trend analysis

**`docs/PLAN.md` defines no numerical reward-trend threshold for Day 28.** The
PLAN success column reads "reward trend up" and freezes no slope, no effect
size, no test and no significance level. This document therefore reports the
observed trajectory and emits **no PASS**. Manufacturing a threshold after
seeing the data would be a post-hoc gate, and none is invented here.

Observed epoch means, in order:

`0.6882236919776851, 0.7267457964300391, 0.7426633632961820,
0.7360076976035026, 0.7642852492646147, 0.7728013338105088`

Descriptive summaries computed by the analyzer and labelled `DESCRIPTIVE ONLY`
in the artifact:

* last epoch mean minus first epoch mean = **0.08457764183282368**
* ordinary least squares of epoch mean on epoch index 1..6 =
  **0.015110025770719024 per epoch**

Both are summary statistics over 6 points from a single run with no error model,
no replicate and no baseline. Neither is a significance test. The series is not
monotone - epoch 4 (0.7360) sits below epoch 3 (0.7427) - so even "the mean rose
every epoch" is false; what the artifact shows is a rise from the first epoch to
the last with one intervening decrease. The trailing rolling mean (window 7, a
display choice recorded in the JSON and not a frozen constant) is in
`reward.rolling_mean` for anyone who wants the finer view.

Three confounds must travel with any reading of this trajectory:

1. **Epsilon fell monotonically from 1.0 to 0.12208654873684793 across the
   run.** Later epochs took fewer random draws, so a rising mean is exactly what
   a fixed table plus a shrinking exploration rate would also produce.
2. **The greedy snapshot stopped changing after epoch 4, yet the epoch mean kept
   rising (0.7360 -> 0.7643 -> 0.7728).** Over those last two epochs the argmax
   was constant, so whatever moved the mean was not a change in the policy the
   table would recommend. At least two things moved it, and the artifacts do not
   separate them: the exploration stream (which cells drew a different action),
   and per-execution noise (confound 3). Over the epoch 5 -> 6 step the two pull
   in opposite directions: `repeat_execution_spread` shows five cells holding the
   IDENTICAL action across epochs 5 and 6, and every one of the five returned a
   LOWER reward in epoch 6 (`F1_agg|medium` 0.8851 -> 0.8627, `F1_agg|small`
   0.9190 -> 0.9151, `F2_join|small` 0.7742 -> 0.7538, `F5_mixed|medium` 0.8701
   -> 0.8532, `F5_mixed|small` 0.6727 -> 0.6272). The epoch mean still rose.
   Attributing that rise to the exploration stream alone would be a story the
   artifacts do not tell.
3. **Repeated executions of an identical (cell, action, config) differ by up to
   0.069386 in reward.** That is a measured noise floor with no policy change in
   it at all (Limitation 13), and it is present in every number above.

The reader judges. This document does not.

## 14. Failures

Zero. From the episode side: `episodes_failed = 0`, `episodes_unusable = 0`,
`episodes_with_update_error = 0`, `episodes_updated = 42` of 42. From the
transition side: 42 records found, `records_failed_or_unusable = 0`,
`cached_records = 0`, no transition-level failure entries.

No `-1.0` reward was threaded, so the Day-27 section 12 unresolved conflict
(PLAN applies the Q update on a failed episode;
`docs/architecture/COMPONENT_CONTRACTS.md` section 3's conceptual signature list
says it is skipped) was NEVER EXERCISED by this run. It remains unresolved and
still needs operator sign-off before any run that does contain a failed episode.

No abort path, no interrupt path and no budget-exhaustion path was taken: the
single terminal condition reached was `early_stop_policy_stable` with
`exit_code=0`.

## 15. Limitations

1. **Early stop is a budget-saving heuristic, not convergence evidence.** It
   fires when the greedy argmax is identical at three consecutive epoch
   boundaries. That is a statement about argmax movement over a table that
   includes Q0-seeded rows nobody visited - not about the value estimates, not
   about optimality, not about stability of anything the agent would do on
   unseen data. `manifest.learning_claim.convergence_demonstrated = false`.

   How much of the snapshot was free is measured, not asserted. Per
   `policy_coverage` in the analysis artifact: of the 8 states in the final
   policy, **3 were never visited in this run at all** (`join|S|le0`,
   `mixed|S|le0`, `rdd_sort|S|le0` - 0 episodes each), and **4 of 8
   states have a greedy action that was never executed once** (those three plus
   `agg|S|le0`, which was visited once and never at its own argmax). An unvisited
   row cannot change, so it contributes stability to every snapshot comparison at
   no evidential cost; the argmax of half the table was decided by the EXP-002
   offline Q0 and the optimistic +0.5 default, not by anything this run measured.
   The stability that stopped the run therefore rests on the 5 rows the run
   actually touched.
2. **The run stopped at epoch 6 of 12 planned, so the epsilon floor was never
   reached.** Epsilon ended at 0.12208654873684793; the 0.05 floor arrives at
   episode 60 and the run ended at 42. The low-exploration regime in which a
   greedy policy would actually be exercised was never observed.
3. **No baseline comparison was performed.** No B0/B1/B2 static configuration,
   no default Spark configuration and no random-action control was run alongside
   this training. `manifest.learning_claim.baseline_comparison = null`. There is
   nothing in these artifacts to compare 0.7384545220637554 against; baselines
   are Day 31 and EXP-005 (Days 32-33).
4. **Durable cross-process budget enforcement is deferred (COMP-EXP-11).** The
   57/500 ledger is a SUM over manifests, REPORTED and enforced by nothing. The
   in-run counter is per-process and per-instance.
5. **T_ref exists only for dataset seed 0, and `F3_rdd|medium` has none.** 7 of
   the 8 TRAIN cells are trainable; dataset seeds 1 and 2 are TRAIN but
   uncalibrated and refused at plan time. Every reward here is normalized
   against a seed-0 reference.
6. **A single seed is a single sample, not a replicate set.** `agent_rng_seed=0`
   is one draw from the frozen exploration-replicate set {0,1,2}. No variance
   estimate, no confidence statement and no replicate agreement can be computed
   from one run; that is precisely Day 29's job.
7. **State aliasing persists.** The frozen size binning maps both `small` and
   `medium` to bin `S`, so `F1_agg|small` (T_ref 22.347372 s) and
   `F1_agg|medium` (36.669743 s) share one Q row, as do the F2_join and
   F5_mixed pairs. Section 12 shows those paired cells differ by 0.05 to 0.26 in
   mean reward, so between-cell variation is folded into what looks like
   within-state noise. `manifest.state_aliasing_note` carries this.
8. **The fixed round-robin confounds the feedback bin with cycle position.** The
   `gt0`/`le0` feature of episode k is set by episode k-1, always the previous
   cell in the same fixed order, so the feedback feature is not independent of
   schedule position. All four `gt0` rows were created in-run by this mechanism.
9. **Action coverage is thin, uneven and incomplete.** 42 episodes over 12
   actions and 8 state rows. Per `actions.action_index_counts` in the analysis
   artifact (12 keys, one per grid action): action 4 was taken 19 times, action
   8 nine times, and **five** of the twelve actions were taken exactly once
   (indices 0, 2, 3, 5, 9). **Action index 7 (`G-p4-sp128`) was never selected
   in 42 episodes** - `actions_never_taken = [7]`. Its column was therefore
   never updated in-run: it still holds the optimistic +0.5 in the four `gt0`
   rows and the EXP-002 offline Q0 value in the four `le0` rows. That is not
   inert. Because the greedy action is an argmax over the whole row, action 7
   IS the greedy action of `state-v1.5|rdd_sort|S|le0` in the section-10 table,
   at a value (0.5089242455603278) that no execution in this run ever tested.
   66 of 96 pairs differ from the Q0 default, and many differ after a single
   update.
10. **Exploration and the reward series are entangled.** With epsilon falling
    from 1.0 to 0.1221 over the run, the composition of actions changes
    systematically with epoch index; nothing in this design separates that from
    any effect of the updates themselves.
11. **`action_source` is a best-effort label**, meaning "equals the greedy
    action", not "was produced by the exploitation branch" - the 15/27
    explore/exploit split inherits that caveat.
12. **The analysis is reproducible; the run is not re-derivable.** Analyzer
    invocations produce byte-identical JSON (sha256 `3ad92f80...`) across
    re-runs, across a reversed episode list, and across absolute, relative and
    `..`-containing spellings of the run directory - validator check 16 tests
    the last of these by deliberately running the two invocations with DIFFERENT
    path spellings. The executions themselves, however, were real Spark runs on
    one machine at one moment and cannot be replayed without spending budget.
13. **There is a measured per-execution noise floor, and it is the same order as
    the trend.** `repeat_execution_spread` groups the episodes by (cell, action);
    every group holds ONE config fingerprint and ONE T_ref, so what remains
    inside a group is per-execution variation with no policy change in it. The
    largest spread is `F5_mixed|small` at action 4: range 0.06938622701884167,
    sample sd 0.03374885985397845 over 4 executions; `F2_join|small` at action 4
    spans 0.06830468683400004 over all 6. The sharpest case is that same
    `F2_join|small` cell, which held action 4 (`G-p4-sp16`, one config
    fingerprint, T_ref 2.214523 s) in every one of the six epochs and still
    produced an OLS slope of 0.010349645758394912 per epoch - 68.5% of the
    headline 0.015110025770719024 - with no policy change and every episode
    labelled `exploit`. The 42 records carry 42 distinct `application_id`s, so
    this is per-execution variation, not one session warming up. Any reading of
    the epoch means has to carry this floor; nothing in this single run
    separates it from the movement.
14. **The headline difference is concentrated in one cell, not spread over
    seven.** Section 12's decomposition shows 56.1% of the
    0.08457764183282368 comes from `F5_mixed|small` alone, anchored on the
    global minimum reward of the whole run; two of the seven cells moved down.
    Excluding that one cell the difference falls to 0.04326931709669213 and the
    slope to 0.009419619966230613. A number that halves when one of seven cells
    is removed is not a robust summary of 42 episodes, and the epoch medians
    (0.7663, 0.7258, 0.8290, 0.7482, 0.8701, 0.8532) are not even monotone -
    epoch 1 exceeds epoch 2.

## 16. Exact interpretation

Supportable by these artifacts, stated exactly:

> **Reward increased across the observed epochs of this run.** The mean frozen
> R3 reward per epoch went from 0.6882236919776851 in epoch 1 to
> 0.7728013338105088 in epoch 6 - a difference of 0.08457764183282368, with one
> intervening decrease at epoch 4 - while the machinery executed 42 episodes
> over 7 TRAIN cells with 0 failures, an exactly-frozen epsilon schedule and a
> complete, joinable artifact trail.

That sentence must travel with two facts from the same artifacts, or it will be
read as more than it is: 56.1% of the 0.08457764183282368 comes from one of the
seven cells and the difference falls to 0.04326931709669213 without it
(Limitation 14), and repeated executions of an identical (cell, action, config)
differ by up to 0.06938622701884167 with no policy change involved at all
(Limitation 13).

NOT supportable by these artifacts, stated exactly:

> The agent **learned**. The agent **converged**. The policy is **optimal** or
> **stable**. The agent is **better than a baseline** or than default Spark. The
> **adaptive system works**. Reward will keep rising. The final Q table
> generalizes to any cell, scale, family or seed outside the 7 TRAIN cells at
> dataset seed 0.

The difference is not rhetorical. "Reward rose across epochs" is a description
of 42 numbers in a file. Each claim in the second block needs something these
artifacts do not contain: a control (no baseline was run - Limitation 3), a
replicate set (one seed - Limitation 6), a convergence criterion on the value
estimates rather than on argmax movement (Limitation 1), a held-out evaluation
(the TEST split is frozen until Day 31), a separation of the effect of the
updates from the effect of a monotonically falling epsilon (Limitation 10), or a
movement large enough to stand clear of the run's own measured execution noise
and not to rest on a single cell (Limitations 13 and 14).
`manifest.learning_claim` states the same thing in machine-readable form:
`learning_demonstrated = false`, `convergence_demonstrated = false`,
`baseline_comparison = null`.

The early stop firing at epoch 6 does not change any of this. It saved 42
executions of the frozen 500 because the greedy argmax stopped changing. It is
not a convergence result.

## 17. Exact next task

Per frozen `docs/PLAN.md` line 275: **Day 29 - Training replicates | seeds
{0,1,2}; policy inspection | policies agree >= 70% (M8).** NOT started.

Concretely: run `scripts/run_training.py` twice more, with `--agent-seed 1` and
`--agent-seed 2`, `--dataset-seed 0`, the same derived 7-cell schedule, each
into its own run directory. There is no orchestrator (COMP-EXP-12 remains
deferred) - the operator invokes the CLI once per seed. Day 29 then compares the
three final greedy policies against the frozen M8 criterion; that comparison,
not this document, is the first place a cross-seed agreement number may appear.

Budget entering Day 29: **57 of 500 spent, 443 remaining** (REPORTED, not
ENFORCED). Two further runs of this shape would cost at most 84 executions each
and would stop sooner if the same early-stop rule fires; the operator sets
`--episodes` from frozen constants and records the result against the ledger, as
Day-27 section 19 requires.

Still deferred and still absent, each with its owner: the execution cache and
durable budget enforcement (COMP-EXP-11); the orchestrator (COMP-EXP-12);
multi-step / gamma=0.9 (Day-30 gate); the eval harness and B1/B2 baselines
(Day 31); EXP-003 / EXP-005 / EXP-005b; every deep-RL family. No hyperparameter
was added, retuned or searched on Day 28 - the run used the frozen values and
nothing else.

**The Day-28 run shows the training machinery executed end to end on 42 real
Spark episodes, and records what the reward did. It proves nothing about
convergence, improvement or superiority.**
