# Day 26 — RL Agent (`tabular-q/v1`) + Versioned Policy Store Audit

## 1. Objective

Implement the frozen tabular ε-greedy Q-learning agent and immutable versioned
policy store (COMP-RL-10), including offline Q₀ initialization from authorized
EXP-002 TRAIN records. **Implementation only — no training campaign, no
baseline comparison, no evaluation.**

## 2. COMP-RL-10 contract

"ε-greedy tabular Q + versioned store · (StateVector, ε) → action;
update(transition) · rl.yaml α/γ/ε · update-fail → Q untouched + abort ·
Q-version + ε + update count · seeded tie-break; save/load round-trip."

Frozen plan §16: α=0.2; γ∈{0, 0.9} (0.0 = bandit default); ε 1.0→0.05 decay
0.95/episode; optimistic init Q₀=+0.5; no replay buffer; 3 training seeds
{0,1,2}; cap 500 executions.

## 3. Learner responsibilities (owns / delegates)

Owns: Q-table, ε-greedy selection, seeded RNG, Q update, ε schedule,
counters, policy serialization/versioning. Delegates: Spark execution,
monitoring/RunMetrics, T_ref, guards, reward computation — all to the frozen
environment (Day-25). The agent consumes `transition.reward` verbatim.

## 4. Q-table schema

Key = `StateVector.key()` stringified `schema|class|size_bin|feedback`
(e.g. `state-v1.5|join|S|le0`) — never floats/object-id/order-dependent.
Row = 12 floats in the frozen action order (mode4 restricts selection, not
storage). Missing rows are created with the frozen optimistic default +0.5.

## 5. Q₀ initialization (offline, EXP-002)

`sparkrl.agent.q0.build_q0_from_exp002`:
* source = stored `exp002-run/v1` records (`results/experiments/exp-002`), TRAIN
  cells only; `split_of() != TRAIN` → `LeakageError` (hard).
* value = per-observation frozen R3 reward (RewardCalculator + T_ref from the
  EXP-002 gate artifact + input_bytes from dataset manifests); never
  recomputed under a different formula.
* action = the record's `config_grid_index` (0..11); B0 records (grid_index
  None) excluded — B0's role is T_ref.
* aggregation = median (PLAN §22 primary statistic).
* measured partition (real data): 208 scanned = 167 valid + 17 invalid
  (counted, skipped) + 8 T_ref-pending (`F3_rdd|medium`) + 16 B0; 4 states
  initialized (agg|S, join|S, mixed|S, rdd_sort|S, all feedback=le0).
* evidence-free pairs stay None in Q0 rows; the agent fills +0.5 at access.

## 6. Update rule

`Q(s,a) ← Q(s,a) + α·[r + γ·max_{a'} Q(s',a') − Q(s,a)]`.
Terminal transitions NEVER bootstrap (bandit-mode target = r). Fully validated
before mutation — an invalid transition raises and leaves Q untouched
(COMP-RL-10 failure rule). γ default 0.0 (bandit); γ=0.9 is the gated
multi-step variant, statically available but unused on terminal steps.

## 7. ε-greedy and randomness

Own `random.Random(seed)` — never the global RNG. ε=1.0 (start), floor 0.05,
×0.95 per episode. Exploration = uniform over allowed actions; exploitation =
argmax with lowest-index tie-break. Same seed → identical action sequence
(pinned by tests); different seed → different sequence also verified.

## 8. Policy store

`models/policies/policy-<id16>.json`, plain JSON (no pickle). `policy_id` =
sha256 over canonical content excluding `policy_id`/`created_utc` → a rebuild
from identical inputs yields the identical version. `save_policy` refuses to
overwrite an occupied version (`PolicyExistsError`); `load_policy` verifies
fingerprint (PolicyCorrupt) and contract compatibility — state schema, action
grid fingerprint, reward formula, learner version, policy schema
(PolicyVersionMismatch). Artifact carries learner_config, contract_versions,
q_table, ε, rng_seed, updates/episodes, q0_provenance.

## 9. Reward delegation / timing

The learner never computes reward (no RewardCalculator import in
`q_learning.py`), never reads T_ref at decision time, never touches
`execution_time_s` except as `metrics` provenance carried on the transition.
Timing semantics remain the frozen Day-3 runner clock.

## 10. Boundaries

No cache (COMP-EXP-11 stays deferred; `cached=False` always), no durable ≤500
enforcement beyond the environment's in-memory budget counter, no online
adaptation orchestration, no experiment auto-run, no DQN/PPO/replay/target
network, no multi-node/K8s/cloud.

## 11. Tests

Unit: `test_rl_agent.py` (frozen config, terminal/non-terminal update with
hand-calculated fixtures, invalid-transition Q-untouched, ε-greedy determinism
and tie-break, mode4 restriction, ε schedule), `test_rl_policy_store.py`
(round-trip, fingerprint identity excluding metadata, immutability,
tamper/version rejection), `test_rl_q0.py` (synthetic EXP-002 fixture: median
aggregation, bins, invalid counting, leakage raises for validation/test cells,
spec-fingerprint refusal, optimistic defaults). Integration (no Spark):
real EXP-002 storage → Q0 → agent → immutable policy round-trip with
deterministic identity and train-only accounting. Integration (real Spark):
one episode state→select_action→env.step→reward→update with the Q updated by
exactly α·(r−Q₀).

## 12. Validator

`scripts/validate_rl_agent.py` — 16 checks: imports, frozen hyperparams,
Q0 from real EXP-002 (partition invariant + determinism + train-only),
no test cells structurally, terminal-update sanity, ε schedule, policy
immutability, reward delegation, no duplicate runner, no cache, no deep-RL
libs, no EXP-003/005, unit tests, integration presence, docs.

## 13. Research-drift boundary

Allowed now: tabular Q-learning, Q-table, ε-greedy, policy store. Still
forbidden and absent: DQN/PPO/actor-critic/policy-gradient/replay/target-net,
automatic hyperparameter search, adaptive execution cache, experiment
orchestration, EXP-003/005/005b, Kubernetes/multi-node/cloud.

## 14. Limitations

1. Measured dataset sizes bin small→S and medium→S under the frozen byte
   thresholds, so the TRAIN grid populates only the S size bin (4/30 discrete
   states with evidence; M/L bins appear only with the reserved TEST data).
   The state representation follows the frozen rule; this is a recorded
   observation, not a workaround.
2. `F3_rdd|medium` has no T_ref (its EXP-002 B0 panel was invalid); those 8
   valid-but-unnormalizable observations are counted and skipped until EXP-003
   calibrates the cell.
3. Durable, cache-aware ≤500 execution enforcement is still COMP-EXP-11
   (deferred); the Day-25 environment budget counter is per-instance.
4. Day 26 establishes the learner contract — it does NOT demonstrate that Q
   learning converges, improves execution time, or beats any baseline.

## 15. Exact next task

Per frozen `docs/PLAN.md` §31: **Day 27 — Training loop | ε schedule,
checkpointing/25 episodes, budget guard ≤500, seeds; smoke training on F1
only.** NOT started.