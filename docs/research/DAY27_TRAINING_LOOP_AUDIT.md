# Day 27 - Training loop (`training-loop/v1`) Audit

## 1. Objective

Implement the machinery named by frozen `docs/PLAN.md` line 273 - **epsilon
schedule, checkpoints, budget guard, smoke training** - over the frozen Day-25
environment (COMP-RL-09) and Day-26 agent (COMP-RL-10). **Machinery only.**
Day 28 owns the first full training run (agent seed 0) and Day 29 the replicate
seeds; nothing in this deliverable supports a claim about learning, convergence,
improvement or superiority, and the smoke run is explicitly not evidence of any
of them.

## 2. Day-27 contract

PLAN line 273 (verbatim): `| 27 | Training loop | epsilon schedule; checkpoints;
budget guard | smoke training |`.

PLAN section 16 (frozen hyperparameters, transcribed nowhere else): alpha=0.2;
gamma in {0, 0.9}; epsilon 1.0 -> 0.05 decay 0.95/episode; optimistic init
Q0=+0.5; no replay buffer (tabular); checkpoint every 25 episodes; 3 training
seeds {0,1,2}; cap 500 executions; early stop when the greedy policy is stable
for 2 consecutive epochs. PLAN section 10 (data flow) fixes the per-episode
chain `... -> Q-update -> JSONL run record + checkpoint -> next episode`.

No new hyperparameter was introduced. `configs/rl.yaml` gained exactly one
additive `training:` block (loop_version, epoch_definition,
checkpoint_every_episodes=25, early_stop_stable_epochs=2, dataset_seed=0,
run_root, smoke_run_root); every numeric value in it is a PLAN-section-16
transcription or a measured fact, and `TrainingConfig.from_yaml` hard-errors
(`RLConfigError`, reused from `sparkrl.agent.q_learning`) if any of 25 / 2 / 0 /
the epoch definition / `live_execution_cap: 500` / `training_seeds: [0,1,2]`
drifts. Episode counts are deliberately absent from the config: PLAN freezes no
episode count, so it lives on the CLI and can never masquerade as frozen.

## 3. Loop responsibilities (owns / delegates)

Owns: the episode schedule, epoch bookkeeping, the append-only episode log and
the run manifest, the checkpoint cadence, the early-stop criterion, and the
`last_reward` thread. Delegates: Spark execution + frozen R3 reward + T_ref +
split/budget guards to `sparkrl.rl.env.SparkTuningEnv`; the epsilon schedule and
the Q update to `sparkrl.agent.q_learning.QLearningAgent`; serialization to
`sparkrl.agent.policy_store`; Q0 to `sparkrl.agent.q0.build_q0_from_exp002`.

`src/sparkrl/training/loop.py` imports no `RewardCalculator`, no `execute_run`,
no `SparkSession` and no environment internals; it reads `reward` off
`env.step` and copies it (`"reward_source": "env.step (frozen R3)"`), never
recomputes it. It keeps no budget counter of its own and performs no epsilon
arithmetic (`agent.end_episode()` is the only mutator).

## 4. Episode schedule and the derived cell set

The cell set is DERIVED at plan time, never hard-coded:
`TRefStore.calibrated_keys()` intersected with `split_of(family, scale,
dataset_seed) == TRAIN` at dataset seed 0, sorted by `"family|scale"`. On the
current `results/experiments/exp-002/analysis/gate.json` that is 7 cells:

| # | cell | T_ref (s) |
|---|---|---|
| 1 | F1_agg\|medium | 36.669743 |
| 2 | F1_agg\|small | 22.347372 |
| 3 | F2_join\|medium | 16.126881 |
| 4 | F2_join\|small | 2.214523 |
| 5 | F3_rdd\|small | 25.109380 |
| 6 | F5_mixed\|medium | 32.759411 |
| 7 | F5_mixed\|small | 3.903756 |

`F3_rdd|medium` is excluded automatically (null T_ref, invalid B0 panel) and
RECORDED, never silently dropped: `_excluded_cells` walks the whole
TRAIN_FAMILIES x TRAIN_SCALES universe and emits `{"cell", "reason", "t_ref_s"}`
with `reason` in {`t_ref_null`, `not_train`, `not_selected`} - the last one
covers cells a `--cells` filter or `--smoke` removed, so a narrowed plan still
carries a trace of the six cells it dropped.

Order: fixed round-robin, no RNG. `epoch = 1 + (i-1)//len(cells)`,
`cell = cells[(i-1) % len(cells)]`, `rep = epoch`. `plan_episodes` is pure and
machine-independent; the same `(cells, n_episodes)` always yields the same plan,
which `--dry-run` prints verbatim.

`rep = epoch` is load-bearing. `SparkTuningEnv._record_path` is
`<result_root>/<family>/<scale>/seed<N>/<config_name>/rep<R>.json` and the env
`os.replace`s that file, so under a fixed `rep` two visits to one cell that
selected the same action would silently destroy each other's immutable
transition record. Round-robin visits each cell once per cycle, so `rep = epoch`
is unique per (cell, visit). `plan_episodes` additionally refuses duplicate
cells, and a unit test asserts N episodes produce N distinct record paths.

Smoke shape (`scripts/run_training.py --smoke`): cells = [`F1_agg|small`],
episodes = 3, budget_limit = 3, run root `results/training/smoke`, run_kind
`smoke`, policy dir `<run_dir>/checkpoints`. Three episodes always exercises
an epoch boundary, epsilon decay across episodes and the final checkpoint -
it does NOT guarantee a stability streak reaching 2 (CONFIRMED fix 9):
epoch 2 normally inserts a positive-reward `gt0` row Q0 lacks, the greedy
snapshot changes, and the streak resets; reaching 2 needs four epochs on an
unchanging snapshot. Cost: 3 x ~22.3 s of Spark plus session
startup.

## 5. The loop state machine

Per episode k (1-based), exactly as implemented in `run_training`:

1. `env.budget_remaining <= 0` -> clean stop (`truncated` / `budget_exhausted`),
   loud stderr line naming how many planned episodes will not run.
2. `env.reset(family=, scale=, seed=plan.dataset_seed, rep=ep.rep,
   last_reward=last_reward)`. The `seed=` keyword here is the env's DATASET
   seed and is the single annotated `seed=` call site in the module.
   `BudgetExhausted` from reset is caught to the same clean stop (defence in
   depth).
3. `eps_used = agent.epsilon`; the best-effort greedy label is computed from
   `agent.q_table()` BEFORE selection; `action = agent.select_action(obs.state)`.
4. The episode line dict is built from the pre-execution facts and marked
   `executed: false`; `flags["mid_step"] = True`.
5. `s2, reward, terminated, truncated, step = env.step(action)`; `mid_step`
   clears. `usable` / `failed` are read off `step.metrics` (`usable`,
   `timeout`); the reward is COPIED.
6. `agent.update(Transition(...))` -> `td_delta`; `InvalidTransition` sets
   `updated=false` + `update_error` and re-raises (COMP-RL-10: Q untouched +
   abort).
7. `last_reward = float(reward)`; `eps_after = agent.end_episode()`.
8. If `k % 25 == 0`: checkpoint (AFTER the decay), id recorded on the line.
9. `_append_jsonl` (write + flush + fsync), counters, the loud stderr line on a
   failed episode, the optional `on_episode` progress callback.
10. If `k % episodes_per_epoch == 0`: greedy snapshot, stability comparison,
    epoch record, atomic manifest rewrite, early-stop test.

On any clean terminal stop (`planned_episodes`, `early_stop_policy_stable`,
`budget_exhausted`) the loop writes one FINAL checkpoint and the final manifest
INSIDE the guarded block, so a `PolicyExistsError` raised by that last
checkpoint still finalizes the manifest as `failed` / `policy_exists` / exit 1
rather than leaving it frozen at `running`. A `QueueLock` (reused from
`sparkrl.experiments.runner`, not reimplemented) is held over `plan.run_dir` for
the duration - see Limitation 4 for what that lock does and does not buy.

## 6. Epsilon schedule

The loop never touches epsilon arithmetic. `epsilon_used` on a line is
`agent.epsilon` read immediately before `select_action`; `epsilon_after` is the
return of `agent.end_episode()`, called exactly once per completed episode after
the update. Therefore `epsilon_used` on line k equals `epsilon_after` on line
k-1 (pinned by `test_epsilon_is_decayed_exactly_once_per_episode`), and the
sequence is the frozen `max(0.05, 1.0 * 0.95**(k-1))`. The floor is reached on
episode 60 (`0.95**58 = 0.0511`, `0.95**59 = 0.0486`): a run shorter than ~60
episodes never observes the floored regime, and a longer one explores at 5% for
the remainder. Checkpoints, written after the decay, always carry the post-decay
epsilon.

## 7. Checkpointing

`build_policy_artifact(agent, init_provenance=q0_provenance, created_utc=...)`
-> `save_policy(artifact, plan.policy_dir)`, every 25 episodes AFTER
`end_episode()`, plus exactly one final checkpoint on any clean stop (including
a boundary interrupt). No checkpoint follows a mid-step interrupt or any abort.
Because the checkpoint is written after the decay, its `episodes` counter always
equals the `episode_index` of the line it is attached to and its `epsilon` is
the post-decay value (pinned by
`test_checkpoint_at_25_is_written_after_end_episode`).

`init_provenance` stays PURE Q0 provenance - no run context is injected - so
checkpoint identity stays content-addressed: two runs that reach an identical
`(Q, epsilon, counters)` state produce the identical `policy_id`, and a repeated
id inside one run's checkpoint list is correct, not a bug. `save_policy` returns
the existing path when an identical artifact is re-saved, so a run whose length
is an exact multiple of 25 legitimately lists the same `policy_id` at episode 25
and again as its final checkpoint.

`policy_dir` defaults to `<run_dir>/checkpoints` for BOTH run kinds;
`models/policies/` is reserved for deliberately published policies and is never
written by this loop (pinned by
`test_checkpoints_are_never_written_to_models_policies`). Checkpoints are
write-only: there is no resume and no warm start (deferred to Day 28+), and the
manifest records the deferral together with the recovery procedure - a crashed
run's consumed executions are counted from the files under `transitions/`, and
the run is re-planned into a NEW run directory rather than resumed.

## 8. Budget guard and the SC6 ledger

The environment is the single counter; the loop keeps none. `budget_limit` is
`min(live_execution_cap=500, --budget)` for a training run - a caller-supplied
value above 500 raises `BudgetPlanError` at plan level and the CLI refuses it
with exit 2, so `--budget` may only LOWER the cap - and exactly the planned
episode count for a smoke run, so a mistyped `--episodes` cannot reach the
research budget through the env. Pre-flight refuses `episodes > budget_limit`
before any Spark session exists, which makes an overrun impossible-by-plan
rather than discovered mid-run.

In-run, the loop checks `env.budget_remaining` before each episode and also
catches `BudgetExhausted` from `env.reset`; both produce the same clean stop
(`status=truncated`, `stop_reason=budget_exhausted`, final checkpoint, exit 0,
loud stderr line).

**Smoke executions count against the frozen 500.** There is no separate ledger
and no `counts_against_sc6` field: every manifest records
`budget.live_executions`, and the cross-run total is the SUM over every manifest
under `results/training/` (smoke included), REPORTED and not enforced - durable
cross-process enforcement is COMP-EXP-11 and remains deferred. **The SC6 training ledger stands at 15 live
executions entering Day 28**, across five 3-episode smoke runs under
`results/training/smoke/`:

| run | origin | status |
|---|---|---|
| `train-a0-d0-20260912T052836Z` | operator, pre-review build | SUPERSEDED (its `visited_state_keys` accumulated across epochs) |
| `train-a0-d0-20260912T081149Z` | `tests/integration/test_rl_training_smoke.py` (full-suite run) | valid |
| `train-a0-d0-20260912T081451Z` | `tests/integration/test_rl_training_smoke.py` (full-suite run) | valid |
| `train-a0-d0-20260912T081737Z` | operator, committed build | valid; the Day-27 smoke of record |
| `train-a0-d0-20260912T082054Z` | `tests/integration/test_rl_training_smoke.py` (final full-suite run) | valid |

The superseded run is retained, not deleted: its 3 executions really happened
and really consumed budget, so removing it would understate the ledger.

The integration test writes to the REAL smoke run root, not a pytest
`tmp_path`, so **every invocation of the integration suite spends 3 of the
frozen 500** and appears in the ledger. This follows from D4 (no hidden
executions) but has a consequence the operator must accept deliberately:
`pytest` is not a free operation on this project. 15 of 500 are spent before
Day 28 begins (3 by the superseded pre-review run, 9 by three integration-suite
runs, 3 by the Day-27 smoke of record). All of it is local: `results/**` is gitignored (the EXP-002
manifests are the single committed exception), so none of it enters version
control.

## 9. Early stop

`episodes_per_epoch = len(plan.cells)` is DERIVED, never configured. At each
epoch boundary the loop takes `greedy_snapshot(agent)` = `{q_key: argmax over
agent.allowed_actions(), lowest-index tie-break}` computed ONLY from
`agent.q_table()` (a deep copy). It never probes with `select_action(state,
epsilon=0.0)` - that would call `self._rng.random()` before comparing to epsilon
and desynchronize the exploration stream - and never uses `q_values(state)`,
which inserts an optimistic default row for an unseen key and would change
`n_states` and hence the checkpoint `policy_id`.
`test_greedy_snapshot_touches_neither_rng_nor_n_states` pins both.

`stable = (snap == prev_snap)`; `streak = streak + 1 if stable else 0`; the stop
fires at `streak >= 2`, i.e. THREE identical consecutive snapshots, so a run can
never stop before three completed epochs
(`test_early_stop_needs_three_identical_snapshots_not_two`,
`test_a_changed_argmax_resets_the_stability_streak`). The stop is
`status=completed`, `stop_reason=early_stop_policy_stable`, final checkpoint,
exit 0. Each epoch record carries `visited_state_keys` (the distinct
`state_key_before` values seen in that epoch) next to the snapshot hash, so a
snapshot that is "stable" only over Q0-seeded rows nobody visited is visible in
the artifact instead of inferred. The rule is a budget-saving heuristic over
argmax movement; it is not a convergence test.

## 10. Records and provenance

Layout: `<run_root>/<run_id>/{manifest.json, episodes.jsonl, transitions/,
checkpoints/}`, `run_id =
train-a<agent_rng_seed>-d<dataset_seed>-<YYYYmmddTHHMMSSZ>`. A pre-existing run
directory is refused (`RunDirExistsError`): the loop never appends into a prior
run's log.

`episodes.jsonl` (`rl-training-episode/v1`) is the append-only truth, one line
per episode: write + `flush` + `os.fsync`. This is DURABLE APPEND, NOT
POSIX-ATOMIC - a crash mid-write can leave a partial trailing line, and the
documented reader rule (for Day 28's reader, which does not exist yet) is to
tolerate exactly ONE malformed FINAL line and hard-fail on a malformed non-final
one. Each line carries both seed names and never a bare `seed` key
(`test_every_line_carries_both_seed_names_and_no_bare_seed`), the cell and
`episode_key`, the feedback fields, `state_key_before/after`, the action with
its best-effort `action_source`, `epsilon_used/before/after`, the config name
and fingerprint, `reward` + `reward_source`, `usable`/`failed`, `t_ref_s`,
`updated`/`update_error`/`td_delta`, `q_before`/`q_after` (read from
`agent.q_table()` around the update, never via `q_values()`), the agent and env
counters, `env_run_id`, `transition_record_relpath`, `checkpoint_policy_id`,
contract versions, `wall_s`, `code_version`, `written_utc`. No metrics and no
`execution_time_s` are copied - the env transition record owns them and the
frozen Day-3 runner clock stays the single timing authority. The reward IS
copied, because Day 28 must be able to read the reward series from the log
alone, and it names its source on the same line.

`manifest.json` (`rl-training-run/v1`) is the derived summary, rewritten
ATOMICALLY (tmp + `os.replace`) at run start, at every checkpoint, at every
epoch boundary and at stop, so a crashed run still leaves a readable, honest
summary (`test_manifest_is_valid_json_at_every_rewrite_point`). It carries
status/stop_reason/exit_code, both seeds plus `seed_semantics`, the schedule
with its cells and exclusions, `t_ref_source` + `t_ref_gate_sha256`, the frozen
hyperparameters read off `agent.config` + `rl_yaml_sha256`, `contract_versions`
(env version, state schema, action mode, grid fingerprint, reward formula,
learner version, policy schema, base config fingerprint - all read off the
duck-typed env, never recomputed), the verbatim `q0_provenance`, the budget
block with its enforcement caveat, counts, the early-stop block, per-epoch
records, checkpoints, `final_policy`, the resume deferral + recovery procedure,
`feedback_chain_origin`, the state-aliasing note, and a machine-readable
`learning_claim` block whose `learning_demonstrated` and
`convergence_demonstrated` are both `false` and whose note is the no-claim
sentence (`test_manifest_makes_no_learning_claim`).

Joins: `episode.env_run_id == StepInfo.run_id ==` the `run_id` inside the env's
own transition JSON; `episode.transition_record_relpath ==
transitions/<family>/<scale>/seed<dataset_seed>/<config_name>/rep<epoch>.json`;
the env record's `episode_key` carries the same `rep`, so the join is
bidirectional (`test_episode_line_joins_to_the_env_transition_record`).
Checkpoints join by `checkpoint_policy_id` on the line, mirrored by
`manifest.checkpoints[]` keyed on `episode_index`.

## 11. `last_reward` threading

`reset(..., last_reward=...)` is `None` on episode 1 (`feedback_source:
"no_history_convention"` - the frozen Day-25 `le0` convention applied by the
encoder), and thereafter the previous COMPLETED episode's reward float taken
from `env.step` only, never a recomputed or averaged value. The chain is global
and chronological across cells, not per-cell: episode k receives episode k-1's
reward whichever cell that was
(`test_last_reward_chain_is_global_and_chronological`). A failed episode's
`-1.0` is threaded like any other value, and the authoritative per-episode
`failed` boolean is threaded alongside it as `last_failed`; the next line
records `feedback_from_failed_episode` from that flag, never from a
`reward == -1.0` sentinel (CONFIRMED fix 6 - a usable run clips to exactly
-1.0 when T >= 2*T_ref, so the sentinel lies).

## 12. Failure table

| Condition | Raised by | Loop behaviour | status / stop_reason | Exit |
|---|---|---|---|---|
| non-TRAIN cell requested | plan-time `split_of` | refuse before any Spark, message names the SPLIT | - (`TrainingPlanError`) | 2 |
| cell with no calibrated T_ref | plan-time `TRefStore` | refuse, message names T_REF CALIBRATION | - (`TrainingPlanError`) | 2 |
| `dataset_seed` in {1, 2} (TRAIN but uncalibrated) | plan-time | refuse with a
T_REF CALIBRATION reason | - (`TrainingPlanError`) | 2 |
| `dataset_seed` in {3} (validation) or {4} (test) | plan-time | refuse with a
PLAN-section-18 SPLIT reason (CONFIRMED fix 1 - the old text blamed T_ref
for every seed, denying that 3/4 are split) | - (`TrainingPlanError`) | 2 |
| `agent_rng_seed` not in {0,1,2}; `episodes < 1` | plan-time | refuse | - (`TrainingPlanError`) | 2 |
| `episodes > budget_limit`; `--budget > 500`; `--smoke --episodes > 500` |
plan-time | refuse | - (`BudgetPlanError`) | 2 |
| run dir exists | plan-time | refuse; never append to a prior log | - (`RunDirExistsError`) | 2 |
| `BudgetExhausted` (pre-check or `env.reset`) | loop / env | clean stop: final checkpoint + manifest, loud line | `truncated` / `budget_exhausted` | 0 |
| unusable run / timeout (reward -1.0) | not an exception | record + update + thread the -1.0 + continue; loud stderr; `episodes_failed += 1`; no retry, no circuit breaker | run continues | - |
| `TRefMissing` from `env.step` | env | write the episode line (NO
`interrupted_mid_step`, NO `uncertain` budget story - a step-level planned
abort raises pre-execution, so `budget.live_executions` is exact), finalize
the manifest, re-raise | `failed` / `tref_missing` | 1 |
| `SplitViolation` | env | never caught, never skipped, never retried | `failed` / `split_violation` | 1 |
| `EpisodeDone` | env | loop control-flow bug; abort | `failed` / `episode_done` | 1 |
| `InvalidTransition` | agent | line written first (`updated=false` + `update_error`), then abort | `failed` / `invalid_transition` | 1 |
| `PolicyExistsError` / `PolicyCorrupt` | policy_store | never retry, never rename | `failed` / `policy_exists` | 1 |
| `OSError` on append | os | abort immediately | `failed` / `log_write_failed` | 1 |
| any other exception | - | generic abort branch | `failed` / `aborted` | 1 |
| `KeyboardInterrupt` at an episode boundary | operator | final checkpoint + finalize | `interrupted` / `interrupted` | 130 |
| `KeyboardInterrupt` during `env.step` | operator | NO checkpoint; the manifest carries `interrupted_mid_step`, `in_flight_episode` and a `budget_accounting` field saying the in-flight execution may or may not have completed and that records under `transitions/` reconcile it | `interrupted` / `interrupted` | 130 |

The dividing line: a condition the frozen design anticipates as a TERMINAL state
stops cleanly; one it anticipates as DATA is recorded and the run continues; one
that means the loop's own plan or control flow is wrong aborts, because
recovering would produce a run whose schedule silently differs from its plan.
The episode line is always written before any abort (with `executed=false` and
an `abort_error` field when the step itself raised), because a live execution
costs ~20-90 s of the frozen 500 and that line is its only forensic record.
Every abort path EXCEPT two is covered by
`test_env_exceptions_abort_with_the_right_stop_reason`,
`test_invalid_transition_writes_the_line_then_aborts`,
`test_policy_exists_error_aborts` and the two interrupt tests. The
`OSError -> log_write_failed` row and the generic `aborted` branch are
implemented but UNEXERCISED by any test - stated here rather than left to be
discovered. (`BudgetExhausted`
raised by `env.step` rather than `env.reset` is unreachable in-process - reset
asserts the budget first - and would fall to the generic abort branch.)

**Unresolved conflict, recorded rather than resolved by code.** PLAN sections
10/13/15 say a failure yields reward -1 and that the -1 is a first-class
observation, while `docs/architecture/COMPONENT_CONTRACTS.md` section 3's
CONCEPTUAL signature list says `Agent.update(s, a, r, s2)` is "skipped on
failure episodes". The loop follows PLAN and APPLIES the update on a failed
episode (recorded `failed=true`, `usable=false`, `reward=-1.0`, `updated=true`;
`test_failed_episode_is_recorded_updated_and_the_run_continues`). Both citations
are given deliberately: **the operator should sign this off before Day 28**,
because any full run containing failed episodes depends on which reading holds.

## 13. Seed semantics

The bare name `seed` is absent from the loop module except at the one annotated
`env.reset(seed=plan.dataset_seed, ...)` call site. `agent_rng_seed` is the
PLAN-section-16 training seed - an EXPLORATION replicate - and reaches
`QLearningAgent(rng_seed=...)` only; `dataset_seed` is the workload instance
seed and is fixed at 0 because T_ref is calibrated for dataset seed 0 only. The
CLI has no `--seed` flag (argparse rejects it as unknown); it has `--agent-seed`
and `--dataset-seed`, each documented with its role. Every episode line and the
manifest carry both names, and the manifest additionally carries the
`seed_semantics` sentence and `policy_rng_seed_is_agent_rng_seed: true`.
`test_run_is_reproducible_for_the_same_seeds` and
`test_a_different_agent_seed_changes_only_exploration` pin the distinction
behaviourally.

## 14. Boundaries - what Day 27 does NOT implement

Execution cache and durable cross-run budget enforcement (COMP-EXP-11);
experiment orchestrator / multi-seed driver (COMP-EXP-12 - Day 29 runs the CLI
three times); resume-from-checkpoint and warm start; retry-on-failure;
consecutive-failure circuit breaker; reward-trend, convergence metrics or plots;
per-epoch schedule shuffle; multi-step / gamma=0.9 paths (Day-30 gate);
hash-chained JSONL; EXP-003 / EXP-005; DQN / PPO / replay buffer / target
network / any neural net; a second Spark runner; a second timing clock; any
reward or T_ref recomputation. No frozen file was modified: `configs/rl.yaml`
gained the additive `training:` block and nothing else, and this document plus
one appended `COMPONENT_CONTRACTS.md` section are the only documentation edits.

## 15. Tests

`tests/unit/test_rl_training.py` (49 tests) and
`tests/unit/test_rl_training_fixes.py` (10 tests, the review-fix probes) -
59 tests, `pytest.mark.unit`, fakes only, no Spark, 0.9 s. A `FakeEnv` exposes
`reset/step/budget_limit/executions_used/budget_remaining/env_version`, returns
scripted rewards and can raise any env exception on a chosen episode; a stub
`TRefStore` supplies the gate values. Coverage: the derived cell set and the
`t_ref_null` exclusion; the dataset-seed-1 refusal naming T_ref and not the
split, with the mirror case of a non-TRAIN cell naming the split;
`plan_episodes` purity and round-robin shape; N episodes -> N distinct record
paths; duplicate-cell refusal; the budget and run-dir refusals; the smoke plan
shape; `greedy_snapshot` touching neither the RNG nor `n_states`; early stop at
three snapshots and not two, and the streak reset; derived
`episodes_per_epoch`; the epsilon sequence; the global `last_reward` chain;
failed-episode recording and continuation; checkpoint-after-decay; a final
checkpoint on a short clean run; never writing to `models/policies/`; both
`BudgetExhausted` paths; smoke executions counting against the cap; every abort
path with its `stop_reason`; both interrupt paths; both seed names on every
line; the manifest's `learning_claim`; manifest validity at every rewrite point;
the episode-to-transition join; reproducibility per seed; and the frozen-config
drift errors. The whole unit gate is green: `pytest -m unit` -> 267 passed, 102
deselected.

`tests/integration/test_rl_training_smoke.py` (`@pytest.mark.integration`, real
Spark, F1_agg|small only, 3 episodes, dataset seed 0, agent seed 0, `tmp_path`
run root) is the separate Day-27 integration deliverable: it asserts mechanics
only - 3 lines in `episodes.jsonl`, 3 distinct transition records,
`env.executions_used == 3`, a final checkpoint that `load_policy` verifies, a
manifest with a `status` in {completed, truncated} and its `learning_claim`
block, and nothing written to `models/policies/` - never a reward threshold,
never a trend, never an improvement. It had not been authored or run at the time
this audit was written; the operator runs it, because it costs real Spark
executions against the frozen 500.

## 16. Validator

`scripts/validate_rl_training.py` follows the shape of
`scripts/validate_rl_agent.py` (a `check(name, ok|None, detail)` helper printing
`NN name PASS/FAIL/SKIP detail`, an `OVERALL: PASS|FAIL (p passed, s skipped, f
failed of n)` line, exit 0 iff no FAIL) with 18 checks: training imports; the
frozen training config; the derived 7-cell schedule with its exclusion; the
dataset-seed guard; plan determinism and distinct record paths; epoch and
early-stop arithmetic; no seed ambiguity in `loop.py` / `run_training.py`;
reward delegation by source scan; no cache and no orchestrator; no deep-RL
libraries; the budget guard; the cross-run SC6 ledger (the sum of
`budget.live_executions` over every manifest under `results/training/` plus a
count of `transitions/**/*.json`, both printed against 500, FAIL above it, SKIP
while no run exists); no smoke policy in `models/policies/`; the unit suite; the
integration test's presence; the no-learning-claim scan over manifests and this
document; this document's existence; and the appended contracts section. Like
the integration test it is a separate deliverable and was not present when this
audit was written; this document's evidence is the loop source,
`configs/rl.yaml`, the CLI and the unit suite.

## 17. Research-drift boundary

Allowed and present: a tabular Q-learning training loop, an epsilon schedule
consumed from the frozen agent, checkpoints, a budget guard, an episode log and
a run manifest. Refused and absent, each with the day that owns it:
COMP-EXP-11 cache + durable budget enforcement; COMP-EXP-12 orchestration
(Day 29 runs the CLI three times); resume / warm start (Day 28+); reward-trend
and convergence analysis (Day 28+); multi-step episodes and gamma=0.9 (Day-30
gate); the TEST split (frozen until Day 31); EXP-003 / EXP-005; every deep-RL
family. No hyperparameter was added or retuned.

## 18. Limitations

1. **The smoke run demonstrates machinery only.** Three episodes on one cell is
   not evidence of learning, convergence, improvement or superiority, and the
   manifest says so in a machine-readable field. Worse, with one cell an epoch
   IS one episode, so a 3-episode smoke can legitimately terminate with
   `stop_reason=early_stop_policy_stable` at episode 3 - that outcome is an
   artifact of the smoke shape and must never be read as stability.
2. **Durable cross-process budget enforcement is still COMP-EXP-11 (deferred).**
   The env counter is per-process and per-instance. Cross-run SC6 totals are the
   SUM over manifests, REPORTED by the validator and enforced by nothing; two
   concurrent processes could jointly exceed 500 and neither would notice.
3. **T_ref exists only for dataset seed 0, and `F3_rdd|medium` is
   uncalibrated.** 7 of the 8 TRAIN cells are trainable. Dataset seeds 1 and 2
   are legitimately TRAIN but uncalibrated, so they are refused at plan time
   with a T_ref message - a calibration limit, not a split decision.
4. **The `QueueLock` is weaker than it looks.** It is taken over
   `plan.run_dir`, which is unique per `run_id` (agent seed + dataset seed + a
   UTC timestamp to the second), so it prevents a second process from entering
   the SAME run directory but does NOT serialize two trainings in different run
   directories - unlike EXP-002, where the same lock sits on a shared result
   root. Concurrent trainings would contend for cores and contaminate every
   timing measured during the overlap. Until a shared lock root is chosen this
   is operator discipline, not a guarantee.
5. **Early stop measures argmax movement, not convergence.** The snapshot spans
   every key in the Q table, including Q0-seeded rows nobody visited, which is
   exactly why each epoch record also carries `visited_state_keys`.
6. **State aliasing.** The frozen size binning maps both small and medium to bin
   S, so `F1_agg|small` (T_ref 22.35 s) and `F1_agg|medium` (36.67 s) share one
   Q row; likewise F2_join and F5_mixed. Reward variance driven by which cell
   ran is indistinguishable from within-state noise. The manifest carries this
   note verbatim.
7. **The fixed round-robin confounds `feedback_bin` with cycle position.** The
   feedback bin of episode k is set by episode k-1, which is always a different
   cell in the same fixed order, so the feedback feature and the schedule
   position are not independent within a run.
8. **Epsilon reaches its floor at episode 60.** A run shorter than that never
   observes the floored regime; a longer one explores at 5% for the remainder.
9. **`usable=False` can be a measurement artifact** (a lost event log, a
   harvesting failure) rather than a bad configuration, yet the frozen reward is
   -1.0 either way and the loop applies the update. See the unresolved conflict
   in section 12.
10. **The episode log is durable, not atomic** (append + fsync); a crash
    mid-write can leave one partial trailing line. `save_policy` is likewise not
    `os.replace`-atomic - it writes a tmp file and then `write_text`s the target
    - but it is a frozen Day-26 file, so this is flagged for a later day, not
    patched here.
11. **`action_source` is a best-effort label.** It means "equals the greedy
    action", not "was produced by the exploitation branch" - an exploration draw
    can coincide with the greedy action. The field's own comment says so.
12. **No resume, no warm start.** A crashed or interrupted run is re-planned
    into a new run directory; its consumed executions are reconciled by counting
    files under `transitions/`.
13. **Implementation notes worth an operator's eye.** `loop.py` is 946 lines
    against the spec's "~400" guidance (grep-verified that nothing from the
    deferred list crept in; the volume is the mandated record shapes, dataclass
    field declarations and rationale docstrings); `code_version()` is cached once
    per process because the frozen helper shells out to git twice per call and
    the loop calls it once per line; and the manifest uses a fifth status
    `running` for its in-flight writes, since none of the four terminal statuses
    is honest before a run stops.

## 19. Exact next task

Per frozen `docs/PLAN.md`: **Day 28 - first full training run, agent seed 0.**
The episode count is Day 28's decision (PLAN freezes none) and must be entered
on the CLI as `--episodes N`, with N bounded by 500 minus whatever the SC6
training ledger already holds. Day 29 replicates agent seeds {0,1,2} by running
the same CLI three times (no orchestrator). Before Day 28 starts, the operator
should (a) run `scripts/run_training.py --agent-seed 0 --smoke`, (b) sign off
the failure-episode update conflict recorded in section 12, and (c) record the
resulting live-execution count against the frozen 500.

**The Day-27 smoke proves the machinery runs and proves nothing about
convergence, improvement or superiority.**
