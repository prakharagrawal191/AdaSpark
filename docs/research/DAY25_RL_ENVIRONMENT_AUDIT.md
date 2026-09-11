# Day 25 — RL Environment (`SparkTuningEnv`) Audit

## 1. Objective

Establish the minimal, research-controlled RL environment contract
(`SparkTuningEnv`, COMP-RL-09) connecting the frozen Spark/monitoring
infrastructure to the future RL agent: deterministic state, constrained
action, delegated execution, explicit transition records. **No learning.**

## 2. Scope

Implemented: environment class, observation/state interface (COMP-RL-06),
action/configuration interface (COMP-RL-07), frozen reward calculation
(COMP-RL-08), reset/step semantics, guards, transition records, T_ref store,
tests, validator, documentation.

Deliberately NOT implemented: Q-table/learning rule, epsilon/exploration,
policy store (COMP-RL-10, Day 26+), adaptive cache + durable ≤500 enforcement
(COMP-EXP-11, Day 26+), orchestrator (COMP-EXP-12), EXP-003/005/005b,
multi-step episodes (gated Day 30).

## 3. Architecture contracts used

DEC-009 (Candidate C); PLAN §12 (bandit mode: one decision per episode), §13
(v1 15-state / v1.5 30-state), §14 (12 actions), §15 (R3 reward, weights in
`configs/reward.yaml`), §16 (≤500 live executions), §18 (split ownership);
COMPONENT_CONTRACTS COMP-RL-06/07/08/09.

## 4. Environment responsibilities and boundaries

Owns: guard enforcement (split, budget, action domain, T_ref), episode
bookkeeping, transition-record persistence, integration of frozen components.
Delegates: Spark session/timing/monitoring/metrics to
`sparkrl.experiments.runner.execute_run` (Day-20/21 runner — the environment
embeds **no second Spark runner, no timing code, no monitoring code**).
Never owns: learning, policy, cache, experiment design.

## 5. Observation contract (COMP-RL-06)

`StateVector` (frozen, value object): `workload_class ∈ {agg, join,
rdd_sort, skew_join, mixed}` (from the family registry), `input_size_bin ∈
{S<512MiB, M<2GiB, L≥2GiB}` (from **dataset manifests**, never live
measurement), `feedback_bin ∈ {le0, gt0}` (v1.5 only; from the previous
episode's realized reward; documented Day-25 convention: no history → `le0`).
Index: v1 = class*3+size (0..14); v1.5 = class*6+size*2+feedback (0..29).
Deterministic, serializable (`to_dict`), hashable (`key()`). Missing input
size → error, never fabricated. Continuous metrics are never state.

## 6. Action contract (COMP-RL-07)

12 actions = the frozen EXP-002 grid, **reused** (`sparkrl.experiments.grid`),
frozen enumeration `grid_index = parallelism_index*4 + shuffle_index`:
action *i* → (parallelism, shuffle.partitions) ∈ {2,4,8}×{16,32,64,128}.
`mode4` (pre-authorized Plan-B subset) = indices {0,3,6,9}. B0 is the
reference, never an action. Non-int/bool/out-of-range/non-subset actions
raise `InvalidAction` **before** any Spark execution. `to_config` applies the
frozen knobs to a `SparkConfig` (AQE must remain OFF) and returns its
fingerprint.

## 7. Reward (COMP-RL-08 — frozen formula, no optimization)

`configs/reward.yaml` (validated against PLAN §15 at load; tampering is a
hard error) → `RewardCalculator.compute(metrics, t_ref, input_bytes, failed)`:

```
R = 1.0·clip((T_ref−T)/T_ref, −1, +1) + 0.2·(1−min(1, CV/0.5))
  − 0.2·min(1, (spill_disk/input_bytes)/0.10) − 1.0·1[failure or timeout]
```

Missing CV / input_bytes → term contributes 0 and is recorded in
`Reward.missing` (never guessed). Failed/timeout run → exactly −1.0.
Missing/non-positive `T_ref` → `TRefMissing` **before** execution.

## 8. T_ref store

Read-only `TRefStore` over the EXP-002 gate artifact
(`results/experiments/exp-002/analysis/gate.json`, key
`t_ref_calibration`; B0 medians at seed 0). Seed ≠ 0 → None (EXP-003 owns
further calibration). `F3_rdd|medium` is null (invalid B0 panel) → env
refuses to execute that cell. EXP-002 artifacts are never written.

## 9. Reset semantics

`reset(family, scale, seed, rep, last_reward)` → (Observation, info). PURE
bookkeeping: **no Spark execution, no budget consumption**. Enforces TRAIN
split, budget availability, known family; resolves the dataset manifest
(input_bytes, dataset_id/fingerprint); encodes the state; resolves T_ref.
`Observation` carries pre-execution facts only (no metrics, no reward).

## 10. Step semantics (bandit mode)

`step(action)` → (state_next, reward, terminated=True, truncated=False,
StepInfo). Guard order: action domain → T_ref presence → budget → execute
(delegated) → reward → next state (feedback bin from realized reward) →
atomic transition record → episode closed. A second `step` raises
`EpisodeDone`. StepInfo carries run_id, action/config identity +
fingerprints, state_before/after, full Reward terms, full `RunMetrics`
(including failures verbatim), runner provenance, `cached=False` (stable
COMP-EXP-11 boundary).

## 11. Failure handling

Failed/timed-out runs keep provenance (`RunMetrics.usable=False`, error text
verbatim, missing timings stay `None`) and yield reward −1.0. No silent
retry, no zero-filling, no fabricated success.

## 12. Guards (COMP-RL-09)

* Split: TRAIN cells only (PLAN §18). TEST (F4_ski / large / seed 4) and
  VALIDATION (seed 3) → `SplitViolation`; `execute_run` re-checks
  independently (defense in depth).
* Budget: live executions counted; default limit 500 (frozen §16/SC6).
  Exhausted → `BudgetExhausted` at the episode boundary (the Day-25
  interpretation of "budget-hit → done"). Cache hits would not consume
  budget; the cache itself is deferred.

## 13. Timing integrity

`execution_time_s` (Day-3 runner clock, warm-up excluded) is the only
execution-time source used for reward and records. Runner wall time, parse
time, manifest time and Day-21 overhead fields are never substituted.

## 14. Tests

Unit (`tests/unit/test_rl_{state,action,reward,env}.py`): 60 tests, no
Spark — frozen sets/thresholds/index ranges, action→config mapping and
rejection, exact fixture arithmetic for every reward term, guard behaviour
with a mocked `execute_run`, transition-record determinism, absence of a
learning API. Integration (`tests/integration/test_rl_env_smoke.py`): one
real run — reset → action 0 → real Spark (F2_join/small/seed0,
local[2]+sp16, AQE OFF) → RunMetrics → frozen reward → deterministic record;
asserts `execution_time_source == "runner"`, COMPLETE event log, budget
accounting.

## 15. Validator

`scripts/validate_rl_environment.py` — 19 checks (imports, signatures,
frozen domains, reward weights, T_ref provenance, budget default,
infrastructure reuse, timing semantics, no-learning/no-cache source scan,
no EXP-001/003/005, agent placeholder still empty, EXP-002 gate intact,
guard behaviour, unit tests, integration presence, documentation).

## 16. Research drift

Source scan of `src/sparkrl/rl/`: no Q-table, no epsilon/schedule, no
Bellman/TD update, no policy, no cache. `src/sparkrl/agent/__init__.py`
remains an empty placeholder. Note: the OS-level Application Control policy
began blocking numpy DLLs under the system Python 3.12 interpreter this day;
all validation was run under the frozen `sparkrl_env311` environment (the
project's authoritative environment since Day 2). 3.12 unit runs were not
possible — recorded as a limitation, not worked around.

## 17. Limitations

1. Bandit mode only; multi-step (3-phase) is gated to Day 30.
2. T_ref calibrated for seed 0 only (7 of 8 panels; `F3_rdd|medium` null) —
   the environment refuses uncalibrated cells rather than fabricating.
3. Budget accounting is per-environment-instance, in-memory; the durable,
   cache-aware ≤500 enforcement arrives with COMP-EXP-11.
4. `cached` is always False — the cache boundary only.
5. v1.5 no-history feedback convention (`le0`) is a documented Day-25
   decision, pinned by tests, revisitable by the supervisor before training.

## 18. What Day 25 does NOT establish

That RL learns, converges, improves execution time, or generalizes; that
Candidate C works; that any policy beats B0/B1/B2/B3/B4. The environment is
a contract, not a result.

## 19. Exact next task

Per frozen `docs/PLAN.md` §31: **Day 26 — RL agent (COMP-RL-10): tabular
Q-learning agent with offline Q₀ initialization from EXP-002 logs.** NOT
started.
