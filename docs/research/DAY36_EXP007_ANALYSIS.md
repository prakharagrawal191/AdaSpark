# DAY36 — EXP-007 TRAIN Analysis (descriptive; zero Spark executions)

**Status:** analysis of the four frozen EXP-007 TRAIN runs. **0 Spark
executions.** No training run artifact modified; no implementation file
modified; DEC-025/DEC-026 unchanged. Machine companion:
`results/evaluation/exp007_analysis.json` (analysis fingerprint
`06bb5859…ce36`; file SHA256 `e010072f…0043b68`).
Analyzer: `scripts/analyze_exp007.py` (stdlib only; rerun byte-identical;
`--self-check` passes).

**Inputs (fingerprints).** A1-s0 manifest `8f88b88f…f3db7f7` / episodes
`28e2940b…0a2a4479` / final policy `bceab0a1…1b415b56`; A1-s1 manifest
`fb0413f2…94f0c29` / episodes `57c8d6a7…4542c596e` / final policy
`dd96c57f…2eb05a9`; A2-s0 manifest `d4819b70…a3f624` / episodes
`9f2dcc63…3deb0514` / final policy `d1aa5da7…2554d8723a8`; A2-s1 manifest
`1c7e69c7…ef53b788` / episodes `b34cc0eb…0b6ef6c7ca` / final policy
`e29f4617…0797ef0`. Full-state reference: main-study TRAIN
`train-a0-d0-20260912T112906Z` (84 eps), `train-a1-d0-20260912T115123Z`
(49 eps, early stop epoch 7), `train-a2-d0-20260912T120648Z` (42 eps,
early stop epoch 6); all `state-v1.5`, all `q0-exp002/v1`. These three
are the only full-state runs in the frozen record (the Day-29 replicate
set; DEC-015; `day29_policy_agreement.json`). No post-EXP-007 TEST
result used.

## 1. Source runs (exactly four)

| Label | Run directory | Variant | State | Agent seed | Dataset seed |
|---|---|---|---|---|---|
| A1-s0 | `results/training/train-a0-d0-20260917T055042Z` | A1 | `state-v1` | 0 | 0 |
| A1-s1 | `results/training/train-a1-d0-20260917T060047Z` | A1 | `state-v1` | 1 | 0 |
| A2-s0 | `results/training/train-a0-d0-20260917T061316Z` | A2 | `state-v2` | 0 | 0 |
| A2-s1 | `results/training/train-a1-d0-20260917T062346Z` | A2 | `state-v2` | 1 | 0 |

All four: 7 TRAIN cells (`F1_agg|small/medium`, `F2_join|small/medium`,
`F3_rdd|small`, `F5_mixed|small/medium`; `F3_rdd|medium` excluded,
`t_ref_null`); same T_ref (`exp002-gate:gate.json`,
`e30a7b0c…aa05392`); same hyperparameters (alpha 0.2, gamma 0.0,
epsilon 1.0→0.05 decay 0.95, q0_default 0.5); neutral Q0
(`q0-neutral/v1`, `projection_from_exp002: false`); TRAIN-only cells.

## 2. Run-level results

| Label | Episodes | Executions | Failed | Epochs | Stop reason | Early stop | Mean | Median | Min | Max | Neg | Stdev\* | Final eps |
|---|---:|---:|---:|---:|---|---|---|---|---|---|---|---|---|
| A1-s0 | 35 | 35 | 0 | 5 | planned_episodes | no | 0.7407 | 0.8237 | 0.2547 | 0.9316 | 0/35 | 0.1775 | 0.1661 |
| A1-s1 | 35 | 35 | 0 | 5 | planned_episodes | no | 0.6275 | 0.6416 | 0.2611 | 0.8692 | 0/35 | 0.1764 | 0.1661 |
| A2-s0 | 35 | 35 | 0 | 5 | early_stop_policy_stable (epoch 5) | yes, epoch 5 | 0.7622 | 0.8235 | 0.3749 | 0.9206 | 0/35 | 0.1663 | 0.1661 |
| A2-s1 | 21 | 21 | 0 | 3 | early_stop_policy_stable (epoch 3) | yes, epoch 3 | 0.6724 | 0.7223 | 0.4246 | 0.8349 | 0/21 | 0.1236 | 0.3406 |

\* sample stdev (ddof=1, existing `statistics.stdev` convention);
descriptive spread only.

Totals: 35+35+35+21 = **126 live executions, 0 failures, 0 TEST
executions**. Final Q-table sizes: A1 15 rows / A2 2 rows (as frozen);
non-default rows: A1-s0 4, A1-s1 4, A2-s0 2, A2-s1 2. Unique visited
states: A1-s0 4, A1-s1 4, A2-s0 2, A2-s1 2. Unique state/action pairs:
A1-s0 16, A1-s1 15, A2-s0 9, A2-s1 7. Distinct actions tried: A1-s0 10,
A1-s1 10, A2-s0 8, A2-s1 6.

## 3. Variant summary (descriptive aggregation defined here)

| Variant | Seeds | Total executions | Episode range | Mean of run-means\* | Median of run-medians\* | Early stops | State cardinality |
|---|---:|---:|---:|---|---|---:|---:|
| A1 | 2 | 70 | [35, 35] | 0.6841 | 0.7327 | 0 | 15 |
| A2 | 2 | 56 | [21, 35] | 0.7173 | 0.7729 | 2 | 2 |

\* Mean/median of the two per-run statistics (equal weight per run).
Episode-level rewards are NOT pooled: denominators differ (35/35 vs
35/21). No inferential reading.

## 4. Full-state reference (frozen; limitations explicit)

Used: the three Day-29 main-study TRAIN runs (`state-v1.5`, 30 states,
`q0-exp002/v1`, 7 TRAIN cells, same T_ref, gamma 0.0): FULL-s0 84 eps /
mean 0.7365 / median 0.8180 / 5 states visited / no early stop; FULL-s1
49 eps / mean 0.6681 / median 0.7001 / 5 states / early stop epoch 7;
FULL-s2 42 eps / mean 0.7716 / median 0.8037 / 5 states / early stop
epoch 6. All three ran under EXP-002-derived Q0 and longer/unequal
horizons (84/49/42 vs 35/35/35/21). No seed was selected after
inspecting A1/A2: all three frozen replicates are reported side by
side. EXP-007 reward numbers are therefore compared only as observed
per-run descriptions, never as like-for-like state-effect estimates.

## 5. State coverage

| Space | Possible | Observed (union) | Proportion |
|---|---:|---|---|
| Full `state-v1.5` (30) | 30 | 5 (`agg|S|gt0`, `agg|S|le0`, `join|S|gt0`, `mixed|S|gt0`, `rdd_sort|S|gt0`) | 5/30 |
| A1 `state-v1` (15) | 15 | 4 (`agg|S`, `join|S`, `mixed|S`, `rdd_sort|S`) | 4/15 |
| A2 `state-v2` (2) | 2 | 2 (`gt0`, `le0`) | 2/2 |

Within-variant: A1 both seeds visit the identical 4-state set
(intersection = union); A2 both seeds visit both states
(intersection = union). Known project limitation (DEC-023 §2, manifests
`state_aliasing_note`): every frozen dataset resolves to size bin S, so
only the S slice of the nominal space is reachable; `skew_join` never
appears because F4_ski is TEST-only. Unreachable states are not evidence
of poor learning.

## 6. Action / policy coverage (descriptive only)

Final greedy actions (lowest-index tie-break over stored Q; rows never
visited stay at the shared neutral 0.5 and their argmax 0 is reported
for completeness, not as learned behavior):

- A1-s0: `agg|S`→8, `join|S`→4, `mixed|S`→11, `rdd_sort|S`→4 (visited);
  all L/M/skew rows →0 (unvisited, Q=0.5 everywhere).
- A1-s1: `agg|S`→1, `join|S`→10, `mixed|S`→5, `rdd_sort|S`→5 (visited);
  unvisited rows →0.
- A2-s0: `gt0`→8, `le0`→6. A2-s1: `gt0`→7, `le0`→1.
- Full reference: FULL-s0 `agg|S|gt0`→8, `join|S|gt0`→4,
  `mixed|S|gt0`→4, `rdd_sort|S|gt0`→5; FULL-s1 →6/1/5/4; FULL-s2
  →5/5/9/4 (evidence-bearing `gt0` rows). `le0` rows agree at 8/9/7
  across seeds but rest on a single episode each (no-evidence
  agreement, not reported as policy).

Patterns: A1 seeds disagree on every visited state's greedy action (0/4
agreement); A2 seeds disagree on both states (0/2). A1-s0 and the full
reference agree on 3 of 4 mappable visited rows; A1-s1 agrees on none.
A2's `gt0` greedy (8/7) coincides numerically with A1-s0 `agg|S`→8 but
the states are not comparable (feedback-only vs context-only), so this
is a numeric coincidence, not policy agreement. Per-state evidence: A1
states rest on 5–10 episodes with 3–5 distinct actions each; A2 `gt0`
rests on 34/20 episodes (8/6 actions) while `le0` rests on exactly 1
episode in both seeds (chosen once — not established policy behavior).
No "best variant" ranking is made.

## 7. Reward trajectories (epoch means; horizons labeled)

- A1-s0 (5 epochs): 0.7003, 0.7566, 0.7450, 0.7598, 0.7415.
- A1-s1 (5 epochs): 0.6011, 0.5678, 0.6395, 0.6057, 0.7234.
- A2-s0 (5 epochs): 0.7199, 0.7485, 0.7796, 0.7744, 0.7883.
- A2-s1 (3 epochs): 0.6750, 0.6574, 0.6847 — not extrapolated to 5.

Per-state means: A1 `rdd_sort|S` is the lowest-mean state on both seeds
(0.4465/0.4547 vs 0.56–0.88 elsewhere); observed pairing only, no
causal reading.

## 8. Early stopping

Frozen rule: greedy snapshot identical at 3 consecutive epoch
boundaries. A1-s0/s1: never triggered (5 epochs each,
`planned_episodes`). A2-s0: triggered at epoch 5 with all 35 episodes
executed (`early_stop_policy_stable`; streak reached 2 exactly at the
planned horizon). A2-s1: triggered at epoch 3 (21 episodes; snapshot
stable across epochs 1–3). Early stopping is observed behavior of the
frozen rule, not a quality verdict; A2-s1 is not called worse for
stopping early, and its trajectory is not extended.

## 9. Q0 limitation (mandatory)

The ablation differs from the full-state main study not only in state
representation, but also in Q0 initialization because no frozen
many-to-one projection from the full-state EXP-002 Q0 table existed.
A1/A2 = neutral `0.5` (`q0-neutral/v1`); main study = EXP-002-derived
Q0 (`q0-exp002/v1`). Any A1/A2 vs full-state difference is therefore an
observed difference between frozen training configurations under their
registered initialization schemes — a state-representation ablation
under a neutral-Q0 initialization constraint — never a pure state
effect.

## 10. Seed limitation (mandatory)

EXP-007 = two seeds per ablation (DEC-025); main study = three seeds.
Lower replication than the main study. Conclusions are descriptive and
not inferential. "Seed-level consistency" wording only: A1 shows the
same 4 visited states on both seeds but disagrees on all 4 greedy
actions and differs in run-mean by 0.11; A2 visits both states on both
seeds with `gt0` dominant (34/35 and 20/21 episodes) but disagrees on
both greedy actions. Partial consistency (coverage) with policy
divergence — not reproducibility in any strong statistical sense.

## 11. Hypothesis status (descriptive only)

Registered: `context + feedback > context-only`; acceptance:
`ablation table / ablation rows`. Status: **observed pattern; not
established**. The full-state reference run-means (0.7365/0.6681/0.7716)
and A1 run-means (0.7407/0.6275) overlap descriptively with no frozen
acceptance criterion to decide them; no threshold is invented. A2
(feedback-only) is contextual evidence about the contribution of
workload context, not the direct context-only comparison.

## 12. Claims supported / not supported

Supported: §2 totals (126 live / 0 failed / 0 TEST / no A3–A5); §2–3
per-run and variant descriptions; §5 coverage; §6 greedy-action
patterns with evidence counts; §8 early-stop outcomes; §9–10
limitations as stated.
NOT supported: "feedback causes improvement"; any pure
state-representation causal claim; any significance/inferential claim;
any TEST generalization claim for A1/A2; any best-variant ranking; any
claim about unvisited states or single-episode (`le0`) policy behavior.

## 13. Artifacts

- `results/evaluation/exp007_analysis.json` (SHA256 `e010072f…0043b68`;
  analysis fingerprint `06bb5859…ce36`; rerun byte-identical).
- This document: `docs/research/DAY36_EXP007_ANALYSIS.md`.
- Analyzer `scripts/analyze_exp007.py` (new; read-only; stdlib only).
- No training artifact modified (the fingerprints in "Inputs" above are
  both the read and the re-verified values).

## 14. Validation

Exactly 4 source runs; A1 = 2 seeds; A2 = 2 seeds; 126 total live
executions; 0 failures; A2-s1 = 21 episodes; all four state schemas
correct (`state-v1`×2, `state-v2`×2); Q0 provenance correct
(`q0-neutral/v1`, neutral, no projection) on all four; no TEST data
included (all episode `run_kind` = training, all cells TRAIN);
EXP-007 unit tests 75 passed; deterministic rerun byte-identical
(file SHA256 `e010072f…0043b68` twice; internal fingerprint
`06bb5859…ce36` stable).

## NO EXECUTION

`Spark executions during analysis = 0`
