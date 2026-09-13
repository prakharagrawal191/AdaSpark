# Day 29 - Training Replicates and M8 Audit

> **Day 29 · Status: COMPLETE · M8 gate: FAIL · Type: training replicates + M8 gate (PLAN line 275)**
> Authority: `docs/PLAN.md` line 275 (`| 29 | Training replicates | seeds {0,1,2};
> policy inspection | policies agree >= 70% (M8) |`), section 16 (frozen
> hyperparameters and seeds), section 15 (frozen R3 reward); `DECISIONS.md`
> DEC-010 (failure semantics); `DAY27_TRAINING_LOOP_AUDIT.md`; Day-28 audit.
>
> **M8 result (machine-read from `results/training/analysis/day29_policy_agreement.json`):
> greedy policy agreement over the pre-specified primary denominator `D_all3`
> is **0.2000** (1 of 5 evidence-bearing states unanimous), below the frozen
> 0.70 threshold. Day 29 therefore does not pass its pre-registered gate.**
> This is a recorded result, not a failure of the procedure; no hyperparameter
> was retuned, no seed rerun selectively, and no denominator was re-chosen.

## 1. Objective

Execute and document the task named by frozen `docs/PLAN.md` line 275: three
independent training replicates (agent RNG seeds {0,1,2}) under the identical
frozen learner/environment configuration, greedy-policy extraction per
replicate, and evaluation of the frozen M8 criterion **"policies agree >= 70%"**.
M8 concerns replicate policy agreement only; it is not a claim about learning,
convergence, optimality, superiority, generalization or production readiness.

## 2. DEC-010 resolution (pre-run blocker, now resolved)

Day 29 was previously blocked by an unresolved failure-semantics conflict
(ARCHITECTURE_FREEZE / COMPONENT_CONTRACTS said *skip the update on failed
runs*; PLAN sections 10/12/13/14/15 make a failure a first-class observation at
reward -1). The blocker is resolved by **DEC-010** (`DECISIONS.md`), which
records the precedence rule the repository lacked: **`docs/PLAN.md` governs
where a derived Day-12 document contradicts it.** DEC-010 states:

* a failed episode is a first-class observation at reward `-1.0`;
* the Q-update IS applied (the frozen Day-27 loop already implements this);
* no learning code, hyperparameter, configuration or loop semantics changed.

The two derived documents kept their frozen text and gained additive
"superseded on one point" pointers (90 insertions, 0 deletions). No Day-29
replicate contained a failed transition, so DEC-010's reward path was not
exercised by the measured episodes; the validator confirms the semantics that
would govern one.

## 3. Replicate design (frozen; what the three runs did)

* Three fresh runs of the Day-27 CLI (`scripts/run_training.py`), once per
  agent RNG seed, into independent run directories. Day-29 seed 0 is a FRESH
  replicate; the Day-28 seed-0 run of record
  (`results/training/train-a0-d0-20260912T083120Z`) is historical and was NOT
  reused as a Day-29 replicate.
* **Seed semantics** (no bare `seed` anywhere; Day-27 audit section 13):
  * **agent RNG seed** = PLAN-16 training seed = exploration replicate index
    from the frozen set {0,1,2}; reaches `QLearningAgent(rng_seed=...)` only.
    **This is what Day 29 varies.**
  * **dataset seed** = workload instance seed, pinned to 0 (T_ref calibrated
    for dataset seed 0 only). **Fixed for all replicates.**
  * **repetition identifier** = epoch/rep index within a run; not a seed.
* Held fixed across replicates (from `configs/rl.yaml`, rl_yaml_sha256-pinned
  `4bb71750e51c8ea605f7feaaa368a2f1dcbe4ecd2aacbeed0f059f8d18cfb5a14`):
  alpha 0.2, gamma 0.0 (bandit), epsilon 1.0 -> 0.05 decay 0.95/episode,
  Q0 default +0.5, checkpoint every 25, early stop on greedy-policy stability
  (3 identical consecutive epoch snapshots; 2 consecutive needed), cap 500.
* Q0 provenance identical for all three (q0-exp002/v1, source exp002,
  aggregation median, TRAIN-only, leakage-guarded; grid_fingerprint
  `97d70dc18a1d5369928964201f2169fd0eebfb8c3c747001900a472885819ba1`,
  spec_fingerprint `9fb5cb51f74fe37f9883a8fdc27636926990d9a8528403fde70c97769b29303e`,
  pairs_initialized 4 from `records_valid_used` 167 after skipping invalid).
  No warm-starting between seeds.
* Episode count per replicate derived from the frozen cell cycle: 7 eligible
  cells (F1_agg medium/small, F2_join medium/small, F3_rdd small,
  F5_mixed medium/small) x 12 epochs = **84 planned episodes** per replicate.
  F3_rdd|medium is excluded (t_ref null) per the frozen schedule.
* Sequential, exclusive execution (queue/exclusive mechanism); no concurrent
  Spark job, benchmark or stress load. No cache, orchestrator, multi-step RL,
  EXP-003/005/005b or deep-RL anywhere.

## 4. Budget accounting (conservative, machine-audited)

| quantity | value | provenance |
|---|---|---|
| prior ledgered executions before Day 29 | 57 | Day-28 audit (6 stored manifests: 42 Day-28 training + 15 of record) |
| known-but-unledgered real test executions | 6 (min) | 2 per integration-suite run of record x 3 suite runs |
| Day-29 live executions (three replicates) | 84 + 49 + 42 = **175** | `day29_policy_agreement.json` runs[].live_executions |
| conservative total consumed | **238** | 57 + 6 + 175 |
| hard cap (PLAN-16 / SC6) | 500 | frozen; not reset, not modified |
| conservative remaining bound | **<= 262** | 500 - 238 |

The exact global execution count since project start cannot be reconstructed
from stored artifacts (the unledgered-test-execution count is a minimum
derived from suite runs of record, not an exact audit). The conservative
interpretation is used throughout, and the three prescribed replicates fit with
margin. Day 29 added no exploratory seeds and no extra training runs.
## 5. M8 denominator - frozen BEFORE any policy inspection

PLAN line 275 freezes the phrase "policies agree >= 70%" and no computation:
no state universe, no denominator, no unanimous-vs-pairwise rule. Because a
denominator chosen after seeing the policies would be a chosen result, the
following pre-specification was fixed in writing (and recorded in
`scripts/analyze_day29.py` PRE_SPECIFICATION) before any final policy was
inspected, and is binding regardless of the number it produces:

* **Primary denominator `D_all3`**: state keys visited (>= 1 episode) in ALL
  THREE runs. **M8 = the fraction of those states where all three greedy
  actions are equal.**
* **Rationale**: an unvisited state keeps its offline EXP-002 Q0 row, and all
  three replicates share the IDENTICAL frozen Q0, so such a state agrees
  trivially and carries no evidence about replicate consistency. Counting it
  would inflate agreement for free.
* **Greedy extraction**: argmax over the frozen 12 actions of the stored
  policy/v1 q_table, ties to the **LOWEST action index** (frozen Day-26 rule).
  The agent is never instantiated and `select_action` is never called (that
  would advance the agent RNG); the stored artifact is read only.
* **Variants (transparency only, NEVER alternative verdicts)**: V1 union of
  q_tables, V2 visited in any run, V3 pairwise mean over D_all3,
  V4 union states visited by no run. The verdict is the primary denominator
  only; it is not reconsidered after seeing its result.
* Threshold `0.70` (frozen, unchanged); gate `>=` (exact 0.70 would PASS).

## 6. State universe and visitation (machine-read)

The union of stored q_tables across the three replicates is 8 states
(4 families x feedback in {gt0, le0}, where feedback le0 is the no-history
bin). States and their measured visitation:

| state key | feedback | visits s0/s1/s2 | in D_all3 |
|---|---|---|---|
| state-v1.5\|agg\|S\|gt0 | gt0 | 23/13/11 | yes |
| state-v1.5\|agg\|S\|le0 | le0 | 1/1/1 | yes |
| state-v1.5\|join\|S\|gt0 | gt0 | 24/14/12 | yes |
| state-v1.5\|join\|S\|le0 | le0 | 0/0/0 | **no** (Q0-only) |
| state-v1.5\|mixed\|S\|gt0 | gt0 | 24/14/12 | yes |
| state-v1.5\|mixed\|S\|le0 | le0 | 0/0/0 | **no** (Q0-only) |
| state-v1.5\|rdd_sort\|S\|gt0 | gt0 | 12/7/6 | yes |
| state-v1.5\|rdd_sort\|S\|le0 | le0 | 0/0/0 | **no** (Q0-only) |

* 5 states were visited by all three runs: these form D_all3, the denominator.
* 3 states (`join|S|le0`, `mixed|S|le0`, `rdd_sort|S|le0`) were visited by NO
  run in any replicate; their rows are still the shared frozen EXP-002 Q0.
  They are excluded from D_all3 and reported, not hidden: their per-seed
  greedy actions agree only because all three rows are the identical offline
  Q0 row (trivial agreement; V4 counts exactly these 3). Unvisited states are
  NOT counted as evidence of agreement.
* The analysis records, per state and seed, the number of distinct actions
  tried, so the sample size behind each argmax is visible (e.g. in
  `rdd_sort|S|gt0`, seed 0 tried all 12 actions in 12 visits; seeds 1 and 2
  tried 5 each in 7/6 visits). 4 greedy actions in evidence-bearing states
  were never actually executed by some seed's exploration.

## 7. Greedy policies (machine-read from stored q_tables)

argmax over the stored policy/v1 q_table, ties to lowest action index:

| state (in D_all3) | s0 | s1 | s2 | unanimous |
|---|---|---|---|---|
| agg\|S\|gt0 | a8 | a6 | a5 | no |
| agg\|S\|le0 | a8 | a8 | a8 | **yes** |
| join\|S\|gt0 | a4 | a1 | a5 | no |
| mixed\|S\|gt0 | a4 | a5 | a9 | no |
| rdd_sort\|S\|gt0 | a5 | a4 | a4 | no |

Q0-only states (excluded from D_all3): join\|S\|le0 = a8/a8/a8,
mixed\|S\|le0 = a9/a9/a9, rdd_sort\|S\|le0 = a7/a7/a7 (trivial agreement).

Final-policy identifiers (manifest `final_policy.policy_id`):

* seed 0: `b801f4a7df200b04c630978f0476c29245da9a9336802f26bff4c2e5b8a7d033`
* seed 1: `af41d8ae7a21d81f5c570f3d96246e26c393bc32018ff3b82126a7a0600a9566c`
* seed 2: `d8fd7b9859d2feeab753d9a40f89f07fb759a481accdf9d86bb1d578dd54bc16b`

## 8. Replicate execution results (machine-read from manifests)

| seed | run_id | episodes | epochs | live exec | mean R | med R | stop reason |
|---|---|---|---|---|---|---|
| 0 | train-a0-d0-20260912T112906Z | 84/84 | 12 | 84 | 0.7365 | 0.8180 | planned_episodes |
| 1 | train-a1-d0-20260912T115123Z | 49/84 | 7 | 49 | 0.6681 | 0.7001 | early_stop_policy_stable |
| 2 | train-a2-d0-20260912T120648Z | 42/84 | 6 | 42 | 0.7716 | 0.8037 | early_stop_policy_stable |

* 0 failed episodes in any replicate (DEC-010 semantics not exercised; validator
  confirmed the governing rule for both cases).
* Reward summaries are DESCRIPTIVE only. They are not part of M8 and support no
  claim of learning or convergence.
* Final epsilon (post-decay): seed 0 = 0.0500, seed 1 = 0.0853, seed 2 = 0.1221
  (seed 1 and seed 2 stopped early on greedy-policy stability before reaching
  the epsilon floor; the early-stop rule is frozen and was not overridden).
## 9. Policy agreement and the M8 gate (machine-read)

| quantity | value |
|---|---|
| M8 denominator | D_all3 (5 evidence-bearing states) |
| states unanimous | 1 (agg\|S\|le0: a8/a8/a8) |
| **M8 agreement** | **0.2000** (1/5) |
| threshold | 0.70 (>=) |
| **M8 verdict** | **FAIL** |

Disagreeing states (4): agg|S|gt0 (a8/a6/a5), join|S|gt0 (a4/a1/a5),
mixed|S|gt0 (a4/a5/a9), rdd_sort|S|gt0 (a5/a4/a4).

Pairwise agreement over D_all3 (transparency; NOT the M8 formula):
seed0-vs-seed1 0.2 (1/5), seed0-vs-seed2 0.2 (1/5), seed1-vs-seed2 0.4 (2/5);
mean pairwise 0.2667. Variants on larger universes are reported in the
artifact and are NOT verdicts: including Q0-only states raises the number
(e.g. union = 0.5), which is exactly why D_all3 excludes them.

**Day 29 = FAIL under the frozen gate.** The three prescribed replicates did
not satisfy the frozen >= 70% policy-agreement criterion. This is the recorded
result of Day 29. No denominator was re-chosen, no hyperparameter was retuned,
and no seed was rerun to move the number.

## 10. Same-seed auxiliary observation (NOT part of M8)

Day-28 seed 0 (42 episodes, early stop) vs Day-29 seed 0 (84 episodes, planned)
are two runs at the SAME agent RNG seed and dataset seed. Reported for
context only; it is NOT a fourth M8 replicate and the M8 denominator is
unaffected.

* agreement over the union of their greedy policies: 0.875 (7/8)
* agreement over states visited in both: 0.8 (4/5)
* greedy policies identical: false; the single differing evidence-bearing
  state is rdd_sort|S|gt0 (Day-28 a4 vs Day-29 a5).
* Note: the two runs are not the same trajectory (different episode counts and
  stop reasons), so the difference is run-to-run variability at fixed seed,
  not a defect. Spark execution times are noisy; the same seed need not
  reproduce the same policy.

## 11. Reproducibility (machine-verifiable)

* `scripts/analyze_day29.py` was run twice against identical stored data, and
  once with `--reverse-input`; both produce **byte-identical canonical JSON**.
* `scripts/validate_day29.py` check "18 analysis reproducible" re-derives the
  analyzer output into a throwaway temp directory (normal + reversed), requires
  byte-identity, and confirms the temp output matches the stored
  `day29_policy_agreement.json`. The three training replicates were NOT rerun.
* All numerical values in this document were read from machine-readable
  artifacts (`day29_policy_agreement.json`, run manifests, episode logs); none
  were hand-typed from memory.
## 12. Validation and tests (zero live Spark)

* `scripts/validate_day29.py`: **OVERALL PASS - 24/24 checks (0 fail, 0 skip)**,
  exit code 0. Covers: exactly seeds {0,1,2}; dataset seed 0; identical Q0
  provenance; identical env/learner/reward/loop versions; per-run provenance
  (schema, hyperparameters == frozen block, counts); no train/test leakage
  (every episode's cell in TRAIN); Day-28 artifacts untouched (mtime-bounded);
  no hyperparameter tuning; independent policy artifacts; denominator frozen
  (D_all3, fixed before inspection); unvisited-state handling explicit;
  deterministic tie-breaking; deterministic greedy extraction; agreement in the
  machine-readable artifact; threshold 0.70; gate from frozen metric;
  analysis reproducible; budget accounting (238 <= 500); no forbidden future
  components in source; DEC-010 failure semantics per run.
* Full deterministic unit suite (`pytest -m unit`, no Spark): **all passed
  (exit 0)**, including `tests/unit/test_day29_m8.py` (analyzer unit tests:
  exact-70% boundary, below/above 70%, pairwise and aggregate agreement,
  frozen denominator, unvisited/Q0-only handling, deterministic ties,
  reversed-input reproducibility, seed-set enforcement, duplicate/missing-seed
  detection).
* Day-25/26/27/28 validators were re-run after DEC-010: PASS 19/19, 17/17,
  25/25, 20/20 (recorded in the DEC-010 change). No integration suite was run
  for Day-29 bookkeeping; no live Spark budget was consumed by this audit.
## 13. Failure handling

All three replicates completed with 0 failed transitions, so the DEC-010
reward=-1/update-applied path was not exercised by the measured episodes. The
validator confirms: (a) no failed transition in any stored log, and (b) the
rule that WOULD govern one (failed -> reward -1.0, Q-update applied, first
class observation) is exactly the frozen Day-27 loop behavior that DEC-010
records. No alternate failure semantics were used.

## 14. Limitations (factual only)

1. The exact global live-execution count since project start cannot be
   reconstructed from existing artifacts; the unledgered-test-execution count
   is a documented minimum, not an exact audit. The conservative bound (238
   consumed of 500; <= 262 remaining) is used throughout.
2. Early stopping stopped seed 1 at epoch 7 and seed 2 at epoch 6 by the frozen
   rule (3 identical consecutive greedy snapshots); seed 0 ran the full 12
   epochs. Policy agreement is therefore measured across runs of different
   lengths, which is a property of the frozen procedure, not a deviation.
3. Action-space sparsity: most evidence-bearing states tried only 2-5 of the
   12 actions (seed 0 tried all 12 only in rdd_sort|S|gt0), so most of each
   Q-row remains at the shared Q0 value; the agreement metric is defined over
   greedy actions of partially-initialized rows.
4. No failed episode occurred, so DEC-010's reward=-1 path remains untested by
   live data in this day's artifacts (it is covered by unit tests and by the
   loop's recorded semantics).
5. The M8 gate was evaluated as frozen; no inference about learning,
   convergence, stability, optimality, superiority, generalization or
   production readiness is made or implied by this document.

## 15. Exact interpretation

> **Day 29 = FAIL under the frozen M8 gate.** The three prescribed training
> replicates (agent RNG seeds {0,1,2}, dataset seed 0, frozen configuration)
> produced greedy policies whose agreement over the pre-specified denominator
> D_all3 (states visited by all three runs) is **0.2000**, below the frozen
> **0.70** threshold. This is the recorded result of the day. No algorithmic
> change, hyperparameter tuning, seed rerun or denominator adjustment was made
> to alter it.

That is the ONLY claim. It does not mean the RL procedure failed to learn, that
it is unstable in general, that the policies are wrong, that a baseline wins,
or that the research question of the project is answered. It means the
pre-registered replicate-consistency gate was not met.

## 16. Exact next task

Frozen `docs/PLAN.md` line 276: `| 30 | Mode gate decision | multi-step only
if stable (DEC) | decision recorded |`. Day 29 is complete (M8 = 0.2000, FAIL
recorded). The next incomplete task is **Day 30 - Mode gate decision**, which
under the frozen plan records a DEC on whether multi-step mode is enabled only
if stable. It is NOT started here per the absolute stop rule; read the plan
before beginning it.