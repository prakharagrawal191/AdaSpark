# DAY 39 — DEC-043 EXP-009 repetition extension, stages 1–7 (COMPLETE): execution and analysis

**Date:** 2026-09-22 … 2026-09-24 (Day 39–41; stage 7 completed 2026-09-24)
**Authority:** DEC-043 §3, scope-bound. Protocol unchanged from DEC-040; interval rule from DEC-042.
**Starting commit:** `8a89f02`
**Executions:** 4842 Spark runs, all VALIDATION split, seed 3. **0 charged to SC6.**
**Ledger:** SC6 **483 / 500, remaining 17 — unmoved**, probed before each stage and after every single run.
**TEST:** not touched. **TRAIN:** not touched. **AQE:** off in every run. **`docs/PLAN.md`:** unchanged.

> This document reports what was measured. It makes no claim about SC6 clause 2 as a whole,
> and it does not restate, relax or withdraw any threshold.

---

## 1 — What was authorized and what was run

DEC-043 §3 authorizes additional repetitions per cell, ordered by resolution efficiency
(lowest required n first), stoppable after any completed stage. **All seven stages were
executed**, so the DEC-043 §3 authorization is now fully discharged.

| Stage | Cell | n/cond authorized | Executions | Recorded | Timing-valid | Failures | SC6 | Wall-clock |
|---|---|---|---|---|---|---|---|---|
| 1 | `F5_mixed\|medium` | 32 | 96 | 96 | 96 | 0 | 0 | 1.44 h |
| 2 | `F3_rdd\|small` | 116 | 348 | 348 | 348 | 0 | 0 | 3.84 h |
| 3 | `F2_join\|medium` | 141 | 423 | 423 | 423 | 0 | 0 | 4.55 h |
| 4 | `F2_join\|small` | 165 | 495 | 495 | 495 | 0 | 0 | 0.80 h |
| 5 | `F1_agg\|medium` | 202 | 606 | 606 | 606 | 0 | 0 | 17.30 h |
| 6 | `F1_agg\|small` | 242 | 726 | 726 | 726 | 0 | 0 | 8.39 h |
| 7 | `F5_mixed\|small` | 716 | 2148 | 2148 | 2148 | 0 | 0 | 5.88 h |
| | **total** | | **4842** | **4842** | **4842** | **0** | **0** | **42.20 h** |

Every authorized execution completed and carries a valid runner clock. There were no
STOP-rule activations, no retries and no excluded observations.

**Repetition semantics.** DEC-043 §3 fixes both `n per condition` and `executions (×3) = n×3`,
and its wall-clock estimates are `n × 3 × median duration`; the same section also requires that
already-recorded observations are "retained and pooled … nothing is discarded and no prior
observation is re-run or overwritten". Both hold together only if each stage executes **n new**
repetitions per condition and analyses **n + 5** pooled. That is what was done: new repetitions
are numbered rep 6…n+5, so no `run_id` can collide with the DEC-040 record. The reading is
recorded in every stage spec (`reps_per_condition_new`, `reps_pooled_per_condition`).

**Derivation, not transcription.** Each stage's n is read at runtime from
`reps_needed_for_2pp_halfwidth.sysmon` in `results/evaluation/exp009_analysis.json`, whose
`artifact_id` is pinned in the driver, and is cross-checked against the DEC-043 §3 table. A
disagreement is a STOP. All seven agreed (32, 116, 141, 165, 202, 242, 716).

**Unchanged (DEC-043 §5).** Cells, the three conditions FULL / NO-SYSMON / NEITHER, interleaving
within (cell, rep), AQE OFF, Day-3 timing semantics, the per-run `sysmon_enabled` /
`event_log_enabled` fields, separate reporting of the two components with the DEC-040 §4
event-log caveat, the 5% acceptance from `docs/PLAN.md` line 45, and DEC-042's interval rule.
`F3_rdd|medium` remains excluded (DEC-040 §6, DEC-042 §2); coverage is unchanged by this work.

---

## 2 — Result: six of seven cells became decided; one did not

A component is **decided** when its whole 95% bootstrap CI lies on one side of the 5% gate;
a straddling interval is INCONCLUSIVE in both directions (DEC-042 §3). A cell is decided when
both components are.

| Cell | pooled n/cond | sysmon | 95% CI | half | eventlog | 95% CI | half | verdict |
|---|---|---|---|---|---|---|---|---|
| `F5_mixed\|medium` | 37 | +0.161% | [−2.554, +1.454] | 2.00 pp | −0.135% | [−1.633, +2.891] | 2.26 pp | **PASS** |
| `F3_rdd\|small` | 121 | −0.167% | [−0.648, +0.921] | 0.78 pp | +0.045% | [−1.066, +0.468] | 0.77 pp | **PASS** |
| `F2_join\|medium` | 146 | −0.059% | [−0.591, +0.434] | 0.51 pp | +0.005% | [−0.421, +0.593] | 0.51 pp | **PASS** |
| `F2_join\|small` | 170 | −0.093% | [−0.422, +0.535] | 0.48 pp | +0.261% | [−0.215, +0.567] | 0.39 pp | **PASS** |
| `F1_agg\|medium` | 207 | +0.177% | [−0.151, +0.527] | 0.34 pp | +0.156% | [−0.206, +0.515] | 0.36 pp | **PASS** |
| `F1_agg\|small` | 247 | +0.203% | [−14.680, +15.210] | **14.95 pp** | +1.110% | [−12.904, +17.922] | 15.41 pp | **INCONCLUSIVE** |
| `F5_mixed\|small` | 721 | +0.143% | [−0.701, +1.015] | 0.86 pp | −0.047% | [−0.771, +1.025] | 0.90 pp | **PASS** |

Before DEC-043, **0 of 7** analysed cells were decided. With all seven stages executed,
**6 of 7** are. `F1_agg|small` received its full authorized 242 repetitions per condition and
is **still undecided** — see §3.4, which is the strongest single result in this work.

Every decided cell's sysmon point estimate lies in **−0.167% … +0.203%**, and every decided
interval is contained within **±2.6 pp**, far inside the 5% gate.

### 2.1 — The withdrawn FAIL is corroborated by measurement

DEC-042 withdrew a FAIL verdict that rested on `F2_join|medium` reading **sysmon = 6.715%**
against the 5% gate, on the argument that at n = 5 the reading was not separable from noise.
That argument is now supported by direct evidence rather than by inference:

| Cell | n = 5 (DEC-040/042) | pooled (DEC-043) |
|---|---|---|
| `F5_mixed\|medium` | +2.214% [−3.01, +7.02] | +0.161% [−2.55, +1.45] (n=37) |
| `F3_rdd\|small` | −0.641% [−6.42, +12.80] | −0.167% [−0.65, +0.92] (n=121) |
| `F2_join\|medium` | **+6.715%** [−6.42, +14.82] | **−0.059%** [−0.59, +0.43] (n=146) |
| `F2_join\|small` | −0.143% [−11.88, +11.09] | −0.093% [−0.42, +0.54] (n=170) |
| `F1_agg\|medium` | −3.003% [−13.43, +11.95] | +0.177% [−0.15, +0.53] (n=207) |

At n = 146 the cell that produced the withdrawn FAIL reads −0.059%, with the whole interval
inside ±0.6 pp. **This corroborates the withdrawal. It does not convert the withdrawn FAIL into
a PASS for SC6 clause 2**, which is addressed in §5.

---

## 3 — The DEC-043 §7 prediction: NOT SUPPORTED

DEC-043 §7 recorded, in advance and so that it could be wrong:

> "The power model behind §3 says the CI half-width shrinks as 1/√n. At the authorized n each
> completed cell should reach a half-width of about 2 percentage points. If the observed
> half-widths do not shrink as predicted, the noise is not independent between repetitions —
> drift, thermal or host contention — and the model is wrong."

**Test method, fixed before the data were seen.** For a grid of k values the CI is recomputed
from the **first k repetitions in execution order** — chronological prefixes, never a selected
subset. The grid always contains k = 5 (the DEC-040 result), k = the authorized n (the model's
own prediction point, because `required_n` solves `half₅·√(5/n) = 2`), and k = the pooled n.
No repetition was dropped, reordered or excluded; no goodness-of-fit threshold was invented;
no parameter was tuned to the observations.

### 3.1 — The magnitude prediction

| Cell | half-width at the authorized n | predicted | observed / predicted |
|---|---|---|---|
| `F5_mixed\|medium` (n=32) | **14.21 pp** | 2.00 pp | **7.11×** |
| `F3_rdd\|small` (n=116) | **0.73 pp** | 2.00 pp | **0.37×** |
| `F2_join\|medium` (n=141) | **0.53 pp** | 2.00 pp | **0.26×** |
| `F2_join\|small` (n=165) | **0.50 pp** | 2.00 pp | **0.25×** |
| `F1_agg\|medium` (n=202) | **0.35 pp** | 2.00 pp | **0.18×** |
| `F1_agg\|small` (n=242) | **15.41 pp** | 2.00 pp | **7.71×** |
| `F5_mixed\|small` (n=716) | **0.87 pp** | 2.00 pp | **0.43×** |

**No cell reached ~2 pp at the n the model designated.** Two are 7–8× too wide; five are
2–6× too narrow. The prediction fails on every one of the seven cells.

`F5_mixed|medium` does reach 2.004 pp — but at the **pooled** n = 37, not at n = 32 where the
model predicts it. Quoting the n = 37 figure as a confirmation would be reading the model on
terms it does not set, so it is recorded here as a coincidence of the trajectory, not as support.

### 3.2 — The scaling prediction

| Cell | log-log slope | predicted | monotone decreasing | max observed/predicted |
|---|---|---|---|---|
| `F5_mixed\|medium` | **+0.170** | −0.5 | no | 12.3 |
| `F3_rdd\|small` | **−0.893** | −0.5 | no | 1.7 |
| `F2_join\|medium` | **−1.012** | −0.5 | no | 2.6 |
| `F2_join\|small` | **−0.982** | −0.5 | yes | 1.2 |
| `F1_agg\|medium` | **−1.187** | −0.5 | no | 3.9 |
| `F1_agg\|small` | **−0.150** | −0.5 | no | 7.7 |
| `F5_mixed\|small` | **−0.796** | −0.5 | no | 1.3 |

No cell's slope is −0.5, and six of seven trajectories are non-monotone. `F5_mixed|medium`
climbs from 5.0 pp at n = 5 to **28.0 pp at n = 21** before collapsing to 2.0 pp at n = 37.

### 3.3 — Why, measured rather than inferred

DEC-043 §7 names the alternative: the noise is not independent between repetitions. It is not.

| | lag-1 autocorrelation | quiet-window dispersion | worst-window dispersion |
|---|---|---|---|
| all 15 condition-series | **+0.604 … +0.871** | **0.67 – 2.06%** | 5.0 – 33.4% |

- **Lag-1 autocorrelation is +0.60 to +0.87 in every one of the fifteen series.** Under
  independence it should be ≈ 0. This is uniform across all five cells and all three conditions,
  and it is the single most direct refutation of the model's assumption.
- **The series are not uniformly noisy.** Within a quiet 20-run window the windowed
  dispersion (IQR / median) is **0.67 – 2.06%**; within a contention window in the *same*
  series it reaches **33.4%** — a swing of up to ~40×. The measurement is extremely precise
  when the host is quiet.
- **The excess dispersion arrives in episodes that persist for tens of consecutive runs**, which
  is precisely what a high lag-1 figure detects. `F1_agg|medium` is the clearest instance: dead
  stable at 30.5 s (windowed IQR 0.3 s, ≈1%) across reps 66–105, a contention episode over reps
  106–151 peaking at 111 s, then dead stable again through rep 207.
- **Two distinct violations are present, not one.** (a) *Level shifts*, both within a stage
  (`F5_mixed|medium`, a −23…−24% step at reps 12–16, common-mode across all three conditions,
  spread 1.39 pp) and **between sessions** (`F1_agg|medium` ran ~22% faster than during the
  DEC-040 baseline: 38.7/39.9/38.3 s → 30.5/30.4/30.4 s). (b) *Episodic contention bursts*, as
  above. Both break independence; neither is a condition effect, since both are common-mode.

These facts explain both directions of departure. The model anchors its extrapolation on
`half₅`, the n = 5 half-width, and treats it as an estimate of iid sampling error. It is not:
the n = 5 samples are five consecutive draws from an episodic, level-shifting series, so `half₅`
measures whatever regime those five runs happened to fall in. Where the anchor was inflated the
model over-predicted the required n and the CI came in far tighter than forecast (the four
undershoots, 0.18–0.37×). Where the pooled sample straddles two regimes the bootstrap median
jumps between them and the interval blows up mid-trajectory (the `F5_mixed|medium` 12.3×
excursion, and a smaller 3.9× one in `F1_agg|medium` at n = 25).

The median-based design is what keeps the endpoint intervals usable despite this: the
`F1_agg|medium` episode moves the standard deviation enormously (second-half CV 34%) while
leaving the median at 30.6 s, so the bootstrap-of-medians CI still reaches 0.34 pp. **No
observation was excluded** — DEC-043 defines no outlier procedure and none was invented.

### 3.4 — `F1_agg|small`: the interval reached the target and then LOST it

This cell is reported separately because it falsifies the model in a way the other five do
not. It received its **full authorized 242 repetitions per condition** — the count DEC-042 §5
derived as sufficient — and finished **INCONCLUSIVE**, with a half-width of **14.95 pp at
n = 247, WIDER than the 13.90 pp it had at n = 5.**

The prefix trajectory shows it is not a monotone failure but an oscillation:

| n | 5 | 29 | 53 | 78 | 102 | 126 | **150** | 174 | 199 | 223 | 242 | 247 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| half-width (pp) | 13.90 | 5.14 | 18.43 | 15.90 | 2.88 | 3.10 | **1.48** | 3.05 | 4.05 | 15.96 | 15.41 | 14.95 |
| obs / predicted | 1.00 | 0.89 | 4.32 | 4.52 | 0.94 | 1.12 | **0.58** | 1.30 | 1.84 | 7.67 | 7.71 | 7.56 |

**At n = 150 the interval reached 1.48 pp — inside the ~2 pp target the model predicts — and
then lost it**, returning to ~15 pp by n = 223 and staying there. Under any independent-sampling
model this cannot happen: additional observations cannot systematically widen a confidence
interval. Here they did.

The measured cause is the regime structure of the series, which is bimodal at whole-series
scale rather than locally noisy:

| reps | 6–25 | 26–145 | 146–245 | 246–247 |
|---|---|---|---|---|
| median (s) | ~20.9 | ~15.1 | ~20.2 | ~14.9 |

The quartiles of the pooled sample sit on the two modes (p25 = 15.11 s, p75 = 20.30 s), i.e.
the cell spends roughly half its repetitions in each. A median is **least** stable in exactly
that configuration: every bootstrap resample can place it in either mode, so the bootstrap
distribution is itself bimodal and the interval is enormous. By n = 150 the sample was
dominated by the fast regime and the interval was tight; by n = 223 the host had returned to
the slow regime, the sample was ~50/50, and the interval blew up.

The five baseline repetitions happen to fall entirely in the slow regime (21.0, 22.0, 19.3,
23.5, 23.0 s), so `half₅` for this cell measured the dispersion of one regime and the model
extrapolated from it as though it were iid sampling error. That is the same failure as the
other cells, in its most extreme form.

**No repetition was excluded and no statistic was changed in response.** The verdict stands as
INCONCLUSIVE.

### 3.5 — A diagnostic on WHY, recorded but NOT applied

The DEC-040 §5 protocol interleaves the three conditions within each (cell, rep), so the
repetitions are already matched, and every level shift measured here is **common-mode** — it
moves all three conditions at the same rep together. The adjudicated statistic (DEC-040 §7) is
the difference of *independent* medians, which discards that matching and therefore carries the
full variance of the shift.

Quantifying the gap, using the same seed and resample count:

| Cell | n | unpaired half-width (adjudicated) | paired half-width (diagnostic) | ratio |
|---|---|---|---|---|
| `F5_mixed\|medium` | 37 | 2.00 pp | 1.07 pp | 1.9× |
| `F3_rdd\|small` | 121 | 0.78 pp | 0.39 pp | 2.0× |
| `F2_join\|medium` | 146 | 0.51 pp | 0.43 pp | 1.2× |
| `F2_join\|small` | 170 | 0.48 pp | 0.36 pp | 1.3× |
| `F1_agg\|medium` | 207 | 0.34 pp | 0.25 pp | 1.4× |
| `F1_agg\|small` | 247 | **14.95 pp** | **0.42 pp** | **35.7×** |
| `F5_mixed\|small` | 721 | 0.86 pp | 0.18 pp | 4.8× |

The paired point estimates agree across all seven cells (−0.214% … +0.172%), and the gap is
modest (1.2–4.8×) wherever the series is well behaved, opening to 35.7× only in the cell whose
regime split is ~50/50 — which is what a common-mode shift predicts.

**This is a diagnostic and nothing more.** DEC-040 §7 freezes the acceptance quantity and
DEC-042 freezes the interval rule applied to it; both are computed unchanged and every verdict
in this document rests on them. Switching to a paired statistic after seeing the data would be
precisely the post-hoc rescue this work exists to avoid. `F1_agg|small` remains
**INCONCLUSIVE**. Whether the acceptance quantity should exploit the pairing the design already
creates is a methodological question for a future decision, recorded in §8 and **not decided
here**.

### 3.6 — How far the required-n figures were mispriced

With all seven stages run, the DEC-042 §5 required-n figures can be compared against the n at
which each cell's verdict actually became PASS and stayed PASS through the end of its
trajectory:

| Cell | DEC-042 §5 required n | earliest stable PASS | overstated by |
|---|---|---|---|
| `F5_mixed\|medium` | 32 | 34 | 0.9× |
| `F3_rdd\|small` | 116 | 40 | 2.9× |
| `F2_join\|medium` | 141 | 33 | 4.3× |
| `F2_join\|small` | 165 | 38 | 4.3× |
| `F1_agg\|medium` | 202 | 45 | 4.5× |
| `F1_agg\|small` | 242 | **never** | — |
| `F5_mixed\|small` | 716 | 220 | 3.3× |

Five of the six decided cells were overstated by **2.9–4.5×**, and the seventh could not be
decided at any n on its grid. Roughly **3,000 of the 4,842 executions were not needed** to
reach the verdicts that were reached.

**This is retrospective and is NOT a stopping rule.** The figure is knowable only after running
to the authorized n, and the same trajectories show a verdict can be reached and then lost:
`F5_mixed|small` is PASS at n = 77, **INCONCLUSIVE again at n = 148**, and PASS from n = 220;
`F1_agg|small` reaches 1.48 pp at n = 150 and then loses it entirely. An experimenter stopping
at the first PASS would have been wrong in at least two of seven cells. The mispricing is real;
"stop earlier" is not the remedy it implies. The resolution is also that of the prefix grid —
the true crossing lies between the stated point and the previous grid point.

### 3.7 — Was the prediction falsifiable, and was it falsified?

Yes, and yes. The falsification path was stated in DEC-043 §7 before execution: half-widths
that do not shrink as predicted, with non-independent noise as the named mechanism. The
evidence that would have **supported** the prediction was available and did not occur —
half-widths near 2 pp at the authorized n with slopes near −0.5. Instead, **all seven cells
missed the magnitude prediction and all seven missed the slope**, and the named mechanism was
confirmed by an independent diagnostic (lag-1 autocorrelation, **+0.584 … +0.886 across all 21
condition-series**) that the prediction did not require.
`F1_agg|small` (§3.4) falsifies it beyond the terms §7 set: it received its full authorized n
and the interval ended **wider** than at n = 5, having transiently met the target at n = 150
and then lost it.

A control is recorded in `tests/unit/test_exp009_ext.py`: on synthetic data that is iid **by
construction**, the same analysis code recovers a slope inside (−0.85, −0.2). The departure
measured above is therefore a property of the observations, not of the estimator.

**Conclusion: the pre-registered power model is NOT SUPPORTED by the measured data.**
With the authorization fully discharged, the verdict rests on all seven cells, not a subset.
The repetition counts it prescribed were not the counts required: five cells were decided far
more cheaply than forecast (0.12–0.43× the predicted width, overstated 2.9–4.5× in n), one was
not decided at the n it designated, and one was **not decided at its full authorized n at
all**. The model's error is not a mis-calibrated constant — it is directional in both
directions and, in `F1_agg|small`, non-convergent.

---

## 4 — Figure

`docs/figures/exp009_ci_halfwidth_vs_reps.svg` — CI half-width against repetitions per
condition, log-log, one colour per cell. Solid = observed; dashed = the pre-registered
1/√n reference from that cell's own n = 5 half-width; the ~2 pp DEC-043 §7 target is drawn as a
horizontal reference. Excursions are shown, not smoothed — including the `F5_mixed|medium`
12.3× bump and the `F1_agg|small` trajectory, which dips below the 2 pp reference at n = 150
and then rises away from it.

---

## 5 — Consequence for SC6 clause 2, stated precisely

**SC6 clause 2 is NOT established by this work, and nothing here may be read as establishing it.**

- **6 of 7** analysed cells are now decided, all PASS on both components. Applying the DEC-042
  interval rule across the set, the overall result is **INCONCLUSIVE**: no cell FAILS, but not
  every cell PASSES.
- **`F1_agg|small` is INCONCLUSIVE despite receiving its full authorized 242 repetitions per
  condition** (§3.4). It is not undecided for want of data; it is undecided because the
  adjudicated statistic does not converge on a non-stationary series. More repetitions under
  the present statistic are **not** evidently the remedy.
- **`F3_rdd|medium` remains excluded** (DEC-040 §6, DEC-042 §2). No cell now rests on n = 5.

DEC-042 §6's finding therefore stands as to the whole: clause 2 is neither satisfied nor
refuted across the full cell set. What has changed is coverage — from 0 to 6 decided cells, and
the DEC-043 authorization is now fully discharged — not the status of the criterion. **The
remaining obstacle is not budget, wall-clock or coverage; it is that the adjudicated statistic
does not converge on `F1_agg|small`.** **No write-up may claim SC6 clause 2 is met**, and equally
none may claim monitoring overhead exceeds the budget.

The event-log component carries the DEC-040 §4 confound unchanged: disabling the event log
changes Spark's own configuration, so that arm is a configuration difference, not a clean
observer removal. The two components are never summed as an acceptance quantity without it.

---

## 6 — Protocol deviations

**None.** No STOP rule fired. No cell outside DEC-040 §5 was touched, no `aqe_enabled: true`
run occurred, the SC6 ledger did not move by a single execution, and no TRAIN or TEST cell was
executed. Every DEC-040/042 artifact is byte-identical: `observations.jsonl` still hashes to
`e58a543e…5ce2` (pinned in the driver and re-verified before every stage), and
`exp009_analysis.json`, `analysis.json`, `spec.json` and `summary.json` carry their original
`artifact_id`s.

### 6.1 — Disclosure: the DEC-043 §3 wall-clock estimates are low by ~2.5×

DEC-043 §3 estimated ~17.68 h for all seven stages; the measured total was **42.20 h**.

| Stage | §3 estimate | measured | ratio |
|---|---|---|---|
| 1 | ~36 min | 86.2 min | 2.39× |
| 2 | ~79 min | 230.7 min | 2.92× |
| 3 | ~121 min | 273.0 min | 2.26× |
| 4 | ~17 min | 47.9 min | 2.82× |
| 5 | ~398 min | 1038.1 min | 2.61× |
| 6 | ~263 min | 503.6 min | 1.91× |
| 7 | ~147 min | 352.6 min | 2.40× |

The §3 estimates are `n × 3 × median execution_time_s`. Each execution additionally costs a
Spark session build and teardown plus the discarded warm-up run that PLAN §22 requires, so the
per-run wall-clock is roughly `session + 2 × execution_time_s`. This is an estimate error in the
signed table, **not** a protocol deviation: DEC-043 §4 states the cost of the decision is
"wall-clock, not budget", and the budget was unaffected. It is disclosed here so that any future
future decision sizing repetition work does not inherit it. **This document does not amend DEC-043.**

---

## 7 — Artifacts

| Path | Contents | Tracked |
|---|---|---|
| `results/experiments/exp-009/ext/baseline_pre_dec043.json` | read-only pre-DEC-043 snapshot (HEAD, ledger, per-cell n/CI/half-width/point estimates) | no |
| `results/experiments/exp-009/ext/stage{1..7}_spec.json` | frozen per-stage queues, derived n, provenance pins | no |
| `results/experiments/exp-009/ext/stage{1..7}_summary.json` | per-stage reconciliation, SC6 before/after | no |
| `results/experiments/exp-009/ext/observations_ext.jsonl` | 4842 raw measurement records | no |
| `results/experiments/exp-009/ext/analysis_ext.json` | pooled analysis, trajectories, drift/regime + paired diagnostics | no |
| `results/evaluation/exp009_ext_analysis.json` | evaluation copy of the above | **yes** |
| `docs/figures/exp009_ci_halfwidth_vs_reps.svg` | CI half-width vs n | **yes** |
| `scripts/run_exp009_ext.py` | stage driver | **yes** |
| `scripts/analyze_exp009_ext.py` | pooled analysis + figure | **yes** |
| `tests/unit/test_exp009_ext.py` | 19 unit checks incl. the iid control | **yes** |

The pre-DEC-043 and DEC-043 evidence are in **separate files**; no pooled artifact overwrites
a DEC-040/042 one.

**Reproducibility.** The bootstrap is seeded (seed 0, 4000 resamples) and every statistic is
imported from `scripts/analyze_exp009.py` rather than re-implemented, so re-analysis of the same
observations reproduces byte-identically and the extension is adjudicated by exactly the
procedure that adjudicated the n = 5 result. A unit test pins that the statistics are defined in
the canonical file.

---

## 8 — What this document does NOT decide

Whether `docs/PLAN.md`'s EXP-009 register estimate or
DEC-043's wall-clock estimates should be amended. Whether to repair `F3_rdd|medium`. Whether
SC6 clause 2 should be restated. Any EXP-005b, EXP-008, EXP-010 or EXP-011 matter. It authorizes
no TRAIN cell, no TEST cell and no AQE-on run, and it amends no prior decision entry.

**Explicitly NOT decided: whether the acceptance quantity should be paired.** §3.5 measures
that the DEC-040 §7 unpaired difference of medians discards a matching the protocol already
creates, and that this costs a factor of 1.2–2.0× on well-behaved cells and 35.7× on
`F1_agg|small`. Adopting a paired statistic would change the acceptance quantity of a signed
experiment after its data were seen. It is recorded as evidence for a future decision and is
**not applied**; every verdict above uses the frozen unpaired statistic.

**Explicitly NOT decided: whether `F1_agg|small` should receive further repetitions.** §3.4
shows its interval is non-convergent under the present statistic, so more repetitions are not
obviously the remedy, and DEC-043 authorizes no repetition count beyond the 242 already run
for that cell.

**Validators at completion:** `scripts/validate_day31.py` OVERALL PASS (36 checks, 36 pass,
0 fail, 0 skip), including the six prior validators. Tests: 696 passed, 18 skipped.

---

## 9 — Amendment record (2026-09-23; amended in place, nothing withdrawn)

This document was first committed at `0441972` covering **stages 1–4**. Stage 5
(`F1_agg|medium`, 606 executions, 0 charged to SC6) was subsequently executed under the same
DEC-043 §3 authorization and the document is extended to **stages 1–5**. No stage 1–4 number,
verdict, artifact or observation was altered; the stage 1–4 rows are unchanged throughout, and
the DEC-040/042 record remains byte-identical.

**One claim is corrected.** §3.3 previously read *"The settled CV is 1.20–1.73% in every
series"*, computed as a standard-deviation CV over the second half of each series. That figure
did not generalise: `F1_agg|medium` records a second-half CV of 27–34%, because a contention
episode of roughly forty consecutive runs (peaking at 111 s against a 30.6 s median) dominates
a standard deviation while leaving the median untouched. A standard-deviation CV was the wrong
summary for a median-based analysis. The diagnostic now reports **robust dispersion
(IQR / median)** alongside the original CV — both are retained, neither is a verdict, and no
observation is excluded from either — together with a windowed regime series. The corrected and
more precise statement is the one now in §3.3: quiet-window dispersion **0.67–2.06%**,
worst-window dispersion up to **33.4%**, in the same series.

**The correction strengthens rather than weakens the finding.** The mechanism is now
characterised as *episodic contention with long correlation lengths* plus *level shifts within
and between sessions*, rather than as monotone drift. Lag-1 autocorrelation is unchanged at
**+0.604 … +0.871**, now across fifteen series rather than twelve, and remains the primary
evidence. The stage 1–4 conclusion — the DEC-043 §7 power model is NOT SUPPORTED — is unchanged
and is reinforced by stage 5 (half-width 0.18× the prediction at the authorized n, log-log slope
−1.187, non-monotone trajectory).

**An expectation recorded before stage 5 was analysed is reported as partially confirmed.** It
was expected that `F1_agg|medium`, whose baseline and new repetitions come from regimes ~22%
apart, would show a non-monotone excursion like `F5_mixed|medium`. It does — the trajectory
peaks at 22.3 pp at n = 25, 3.93× the prediction — but the excursion is markedly smaller than
`F5_mixed|medium`'s 12.3× and resolves sooner. Recorded as partially confirmed, not confirmed.

### 9.1 — Second amendment (2026-09-23, stage 6)

Extended from **stages 1–5** to **stages 1–6**. Stage 6 (`F1_agg|small`, 726 executions, 0
charged to SC6, 8.39 h) completed 726 of 726 with zero failures and no STOP. All stage 1–5
numbers, verdicts and trajectories are unchanged and were verified field by field; the
DEC-040/042 record remains byte-identical at sha256 `e58a543e…5ce2`.

Stage 6 produced the study's strongest result and it is a **negative** one: `F1_agg|small`
received its full authorized 242 repetitions per condition and finished **INCONCLUSIVE**, with
a half-width of 14.95 pp — **wider than the 13.90 pp it had at n = 5** — after transiently
reaching 1.48 pp at n = 150. New §3.4 records it in full. The cell is bimodal at whole-series
scale (~15.1 s and ~20.2 s regimes, roughly half the repetitions in each), which is the
configuration in which a median is least stable.

Two diagnostics were added, both clearly labelled and neither verdict-bearing: the **paired**
per-repetition statistic (new §3.5), recorded because the protocol already interleaves
conditions within (cell, rep) and every measured shift is common-mode; and the windowed regime
series from §9. The paired statistic is **not** adopted — doing so would change a signed
experiment's acceptance quantity after seeing its data — and `F1_agg|small` remains
INCONCLUSIVE under the frozen DEC-040 §7 statistic.

No claim was weakened or re-framed: the §3 conclusion is unchanged and strengthened, the SC6
position in §5 is unchanged (clause 2 remains unevidenced as a whole), and no observation was
excluded from any statistic.

### 9.2 — Third amendment (2026-09-24, stage 7 — authorization fully discharged)

Extended from **stages 1–6** to **stages 1–7**. Stage 7 (`F5_mixed|small`, 2148 executions, 0
charged to SC6, 5.88 h) completed 2148 of 2148 with zero failures and no STOP. **All seven
DEC-043 §3 stages are now executed and the authorization is fully discharged.** All stage 1–6
numbers, verdicts and trajectories are unchanged and were verified field by field; the
DEC-040/042 record remains byte-identical at sha256 `e58a543e…5ce2`.

`F5_mixed|small` is **decided, PASS** on both components at n = 721 (sysmon +0.143%,
CI [−0.701, +1.015], half-width 0.86 pp). Coverage is **6 of 7**; only `F1_agg|small` remains
undecided, and §3.4 records why.

The §3 conclusion is unchanged and now rests on the complete cell set rather than a subset:
all seven cells missed the magnitude prediction, all seven missed the slope, six of seven
trajectories are non-monotone, and lag-1 autocorrelation is **+0.584 … +0.886 across all 21
condition-series**.

New §3.6 quantifies the consequence now that every cell has run: the DEC-042 §5 required-n
figures overstated the repetitions actually needed by **2.9–4.5×** on five of the six decided
cells, and roughly **3,000 of the 4,842 executions were not needed** to reach the verdicts
reached. That figure is recorded together with its own limitation — it is **retrospective and
is not a stopping rule**, because `F5_mixed|small` is PASS at n = 77 and INCONCLUSIVE again at
n = 148, so stopping at a first PASS would have been wrong.

No verdict was changed, no statistic was switched, and no observation was excluded. The paired
statistic of §3.5 remains a diagnostic and remains unapplied. SC6 clause 2 remains unevidenced
as a whole (§5).

