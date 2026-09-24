# A Pre-Registered Measurement of Monitoring Overhead in Apache Spark, and the Failure of the √n Repetition Model

**Status:** DRAFT v1 — internal. Not submitted. All figures traceable to committed artifacts.
**Evidence commit:** `7937db8` (execution), `7fee020` (prior-art record).
**Audience:** systems / performance-measurement venue (ISMM, ICPE, OOPSLA-style artifact track).

---

## Abstract

Instrumentation is supposed to be cheap enough to leave on. Quantifying "cheap enough" requires
deciding whether a measured overhead sits below a stated budget — a question of *resolution*,
not of point estimates. We pre-registered a falsifiable prediction about how much measurement
this would take, derived from the standard assumption that confidence-interval half-width
shrinks as 1/√n, and then executed 4,842 Spark job runs to test it.

The prediction failed on every one of seven workload cells. No cell reached the predicted ~2
percentage-point half-width at the repetition count the model prescribed; observed/predicted
ratios spanned 0.12× to 7.7×, and no log–log slope was close to the predicted −0.5. The cause is
measurable rather than inferred: lag-1 autocorrelation of execution time is +0.584…+0.886 in all
21 condition-series. The runs are not noisy so much as *episodic* — within a quiet 20-run window
the robust dispersion is 0.63–2.06%, while a contention window in the same series reaches 75.4%.

The practical cost is large. The repetition counts the model prescribed overstated what was
actually needed by 2.9–4.5× on five of six decided cells: roughly 3,000 of our 4,842 runs were
unnecessary. In the opposite direction, one cell never converged at all — its interval reached
1.48 pp at n = 150, then *widened* to 14.95 pp by n = 247, ending wider than it began at n = 5.

We do not claim the underlying phenomenon is new; non-independence between benchmark
repetitions and the absence of a reliable steady state are established results. Our contribution
is a controlled, interval-adjudicated measurement of Spark monitoring overhead specifically, and
a pre-registered test whose failure is reported against a record written before the data
existed.

---

## 1. Introduction

A monitoring system that perturbs the workload it observes is a measurement instrument with a
systematic error. Practitioners routinely assert that sampling-based monitoring costs "a few
percent," and projects routinely adopt a numeric budget — ours was **≤5% of job execution
time**. Verifying such a budget is harder than it looks, because the quantity being tested is a
*difference* between two configurations whose run-to-run variability is of the same order as the
budget itself.

This paper reports what happened when we tried to verify that budget rigorously.

The initial measurement (n = 5 repetitions per condition, 105 usable observations, 7 cells)
produced a point estimate of 6.715% on one cell — above the 5% budget — and an initial verdict
of FAIL. That verdict was withdrawn before publication, on the grounds that at n = 5 the
sampling error of a difference of medians was the same order as the effect under test: 7 of 14
component measurements were *negative*, down to −13.42%, and instrumentation cannot make a job
run faster. Every cell's 95% bootstrap interval straddled both 0 and 5%.

The withdrawal raised the obvious question: how much more measurement would settle it? The
standard answer is the √n model — scale the observed half-width by 1/√n and solve for the n that
reaches a target precision. We applied it, recorded the resulting per-cell repetition counts
**and an explicit prediction that they would work**, and then ran them.

**Contributions.**

1. A controlled measurement of Apache Spark monitoring overhead — a sampling profiler and event
   logging, reported separately — against a stated 5% budget, adjudicated by interval rather
   than point estimate (§4, §5).
2. A pre-registered falsifiable prediction of the √n model's adequacy, recorded before
   execution, and its falsification on all seven cells (§6).
3. A quantification of what the model's failure costs in practice: 2.9–4.5× over-provisioning on
   the cells it did decide, and non-convergence on the one it did not (§6.4).
4. A negative result we did not design for: **more repetitions made one cell's interval worse**
   (§6.3).

---

## 2. Background and Related Work

Our measured mechanism is not novel, and we state its precedents plainly.

**Kalibera and Jones** [ISMM 2013] give a statistically rigorous methodology for choosing
repetition counts to reach a target precision, explicitly treating independence between
repetitions and reporting effect-size confidence intervals. The √n construction we
pre-registered is the naive form of exactly the problem they address, and the independence
violation we measure is the failure mode they warn about. Readers should regard our §6 as
empirical confirmation of their concern in a new runtime, not as its discovery.

**Barrett et al.** [OOPSLA 2017] use changepoint analysis to show that language VM benchmarks
frequently never reach a steady state of peak performance, contradicting a near-universal
assumption in JIT benchmarking. The regime structure we observe (§6.2) and the non-convergence
of one cell (§6.3) are instances of the same phenomenon in a different setting: a JVM-based
distributed data engine driven from Python, rather than a VM benchmark loop.

**Mytkowicz et al.** and the broader measurement-bias literature establish that plausible
experimental setups can yield systematically wrong conclusions. Our withdrawn FAIL (§1) is a
concrete instance.

**What is comparatively under-served** is Spark monitoring overhead itself. Apache Spark's
documentation describes its metrics and instrumentation interfaces, and practitioner reports
discuss listener overhead qualitatively, but we found no controlled study measuring the cost of
sampling-based system monitoring and event logging in Spark against a stated budget with
interval-based adjudication. That gap is what we fill.

---

## 3. Experimental Setup

**Hardware and software.** Single host, Windows 11 (10.0.26200), Intel 24 logical cores,
31.4 GB RAM (13.0 GB available at audit), local NVMe with 483 GB free. OpenJDK 17.0.20.1,
PySpark 3.5.9, Python 3.11.9. Spark in `local[2]`, driver memory 6 GB.

**Configuration.** A frozen out-of-box baseline: adaptive query execution **off**,
`shuffle.partitions` = 200 (Spark's default), no performance tuning of any kind. The
configuration is content-addressed by fingerprint and every run records it; a run whose applied
configuration does not match is refused, not corrected.

**Workloads.** Four families over two data scales, all derived from a TPC-H-like
lineitem/orders schema at skew 1.0: `F1_agg` (join → groupBy → windowed cumulative sum),
`F2_join` (join on order key → groupBy), `F3_rdd` (RDD map → sortByKey → filter → reduceByKey),
and `F5_mixed` (three-phase: ingest-clean → join with a cached intermediate → aggregate-write).
Seven of eight cells were analysed; `F3_rdd|medium` was excluded before this study as
long-standing fragile — 18 failed / 8 completed in an earlier experiment, against 25 completed /
1 failed for `F3_rdd|small` — and its failure records are retained rather than deleted.

**Timing.** `execution_time_s` from the harness clock, with two warm-up runs executed and
discarded per session. A measurement lacking a harness-sourced clock is recorded as invalid
rather than substituted.

**Conditions.** Three, applied to every repetition of every cell:

| Condition | system sampler | event log |
|---|---|---|
| FULL | on | on |
| NO-SYSMON | off | on |
| NEITHER | off | off |

The two overhead components are reported **separately and never summed** as an acceptance
quantity. Disabling the event log changes Spark's own configuration, so that arm is a
configuration difference rather than a clean observer removal — a confound we carry explicitly
rather than dissolve.

`sysmon overhead = 100 · (median(FULL) − median(NO-SYSMON)) / median(NO-SYSMON)`
`eventlog overhead = 100 · (median(NO-SYSMON) − median(NEITHER)) / median(NEITHER)`

The three conditions are **interleaved within each (cell, repetition)**, so a slow period
affects all three arms at the same point in the sequence.

---

## 4. Adjudication by Interval

A point estimate compared against a 5% gate silently asserts a precision the design may not
have. We therefore adjudicate by interval, using a 95% percentile bootstrap of the relative
difference of medians (4,000 resamples, fixed seed, so re-analysis is bit-reproducible):

> A component returns a verdict **only when the whole interval lies on one side of the gate**.
> PASS below, FAIL above. **A straddling interval is INCONCLUSIVE in both directions** — neither
> a softened FAIL nor a rescued PASS.

A *cell* is decided only when both components are. This rule, the 5% gate, and the bootstrap
parameters were all fixed before the repetitions reported here were run, and none was altered
afterwards.

---

## 5. The Pre-Registered Prediction

From the n = 5 data we computed, per cell, the repetitions needed for a 2 pp half-width by
scaling the observed half-width by 1/√n — i.e. solving `half₅·√(5/n) = 2`. This yielded counts
from 32 to 716 repetitions per condition, ordered by *resolution efficiency* (cheapest to
decide first). Notably the ordering is not by job duration: a 2.1 s job needed 165 repetitions
while a 21.7 s job needed 242, so cost-to-decide is a property of dispersion, not runtime.

We then recorded the following **before executing any of it**:

> The power model says the CI half-width shrinks as 1/√n. At the authorized n each completed
> cell should reach a half-width of about 2 percentage points. If the observed half-widths do
> not shrink as predicted, the noise is not independent between repetitions — drift, thermal or
> host contention — and the model is wrong.

**Test procedure, also fixed in advance.** For a grid of k values we recompute the interval from
the **first k repetitions in execution order** — chronological prefixes, never a selected
subset. The grid always contains k = 5 (the original result), k = the prescribed n (the model's
own prediction point), and k = the full pooled n. No repetition is dropped, reordered or
excluded, and no goodness-of-fit threshold was introduced after seeing the data.

**Estimator control.** On synthetic data that is i.i.d. *by construction*, the same analysis
code recovers a log–log slope inside (−0.85, −0.2). Any departure reported below is therefore a
property of the observations, not of the estimator. This control is a unit test in the artifact.

---

## 6. Results

4,842 runs across seven cells; every authorized run completed with a valid clock; zero failures,
zero protocol deviations.

### 6.1 Overhead

| Cell | pooled n | sysmon | 95% CI | half-width | eventlog | half-width | verdict |
|---|---|---|---|---|---|---|---|
| `F5_mixed\|medium` | 37 | +0.161% | [−2.554, +1.454] | 2.00 pp | −0.135% | 2.26 pp | PASS |
| `F3_rdd\|small` | 121 | −0.167% | [−0.648, +0.921] | 0.78 pp | +0.045% | 0.77 pp | PASS |
| `F2_join\|medium` | 146 | −0.059% | [−0.591, +0.434] | 0.51 pp | +0.005% | 0.51 pp | PASS |
| `F2_join\|small` | 170 | −0.093% | [−0.422, +0.535] | 0.48 pp | +0.261% | 0.39 pp | PASS |
| `F1_agg\|medium` | 207 | +0.177% | [−0.151, +0.527] | 0.34 pp | +0.156% | 0.36 pp | PASS |
| `F1_agg\|small` | 247 | +0.203% | [−14.680, +15.210] | **14.95 pp** | +1.110% | 15.41 pp | **INCONCLUSIVE** |
| `F5_mixed\|small` | 721 | +0.143% | [−0.701, +1.015] | 0.86 pp | −0.047% | 0.90 pp | PASS |

Six of seven cells are decided, all PASS. Every decided sysmon point estimate lies in
**−0.167% … +0.177%**, and every decided interval is contained within ±2.9 pp — far inside the
5% budget.

The cell that produced the withdrawn FAIL is instructive: at n = 5 it read **+6.715%**
[−6.42, +14.82]; at n = 146 it reads **−0.059%** [−0.591, +0.434]. The original reading was
noise. We report this as vindication of the *withdrawal*, not as evidence that the budget is met
overall — one cell remains undecided, so the criterion as a whole is unevidenced.

### 6.2 The prediction failed on every cell

| Cell | half-width at prescribed n | predicted | ratio | log–log slope | monotone |
|---|---|---|---|---|---|
| `F5_mixed\|medium` | 14.21 pp | 2.00 | 7.11× | **+0.170** | no |
| `F3_rdd\|small` | 0.73 pp | 2.00 | 0.37× | −0.893 | no |
| `F2_join\|medium` | 0.53 pp | 2.00 | 0.26× | −1.012 | no |
| `F2_join\|small` | 0.50 pp | 2.00 | 0.25× | −0.982 | yes |
| `F1_agg\|medium` | 0.35 pp | 2.00 | 0.18× | −1.187 | no |
| `F1_agg\|small` | 15.41 pp | 2.00 | 7.70× | −0.150 | no |
| `F5_mixed\|small` | 0.87 pp | 2.00 | 0.43× | −0.796 | no |

No cell reached ~2 pp at its prescribed n. The model's error is not a mis-calibrated constant:
it is wrong in **both directions**, four-to-six times too conservative on five cells and seven
to eight times too optimistic on two. Six of seven trajectories are non-monotone — the interval
does not even shrink reliably, let alone at the predicted rate.

**Why.** Lag-1 autocorrelation of execution time is **+0.584 … +0.886 in all 21 condition-series**
(under independence it should be ≈ 0). The series are not uniformly noisy: within a quiet 20-run
window the robust dispersion (IQR/median) is **0.63–2.06%**, while a contention window in the
same series reaches **75.4%**. Excess variance arrives in *episodes spanning tens of consecutive
runs*. `F1_agg|medium` illustrates it: dead stable at 30.5 s with a windowed IQR of 0.3 s across
runs 66–105, a contention episode over runs 106–151 peaking at 111 s, then dead stable again
through run 207.

Two distinct violations are present. **Level shifts**, both within a session (one cell steps
−23% at runs 12–16) and *between* sessions (another ran ~22% faster than during the original
n = 5 measurement, months of wall-clock apart). And **episodic contention bursts**. Both are
common-mode — they move all three conditions together — so neither is an artifact of the
instrumentation under test.

This explains both directions of failure at once. The model anchors on `half₅` and treats it as
an estimate of i.i.d. sampling error. It is not: five consecutive runs sample whatever regime
they happen to land in.

### 6.3 A cell where more data made the answer worse

`F1_agg|small` received its full prescribed 242 repetitions per condition and finished
**INCONCLUSIVE**, with a half-width of **14.95 pp at n = 247 — wider than the 13.90 pp it had at
n = 5**.

| n | 5 | 29 | 53 | 78 | 102 | 126 | **150** | 174 | 199 | 223 | 242 | 247 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| half-width (pp) | 13.90 | 5.14 | 18.43 | 15.90 | 2.88 | 3.10 | **1.48** | 3.05 | 4.05 | 15.96 | 15.41 | 14.95 |

At n = 150 the interval reached **1.48 pp**, inside the target, and then lost it. Under any
independent-sampling model this cannot happen.

The series is bimodal at whole-series scale — ~15.1 s over runs 26–145, ~20.2 s over runs
146–245 — with the pooled quartiles landing on the two modes (p25 = 15.11 s, p75 = 20.30 s).
Roughly half the repetitions sit in each regime, and a median is *least* stable in exactly that
configuration: each bootstrap resample can place it in either mode. The five original
repetitions fall entirely in the slow regime, so the anchor measured one regime's dispersion.

**No repetition was excluded and no statistic was changed in response.** The cell is reported as
undecided.

### 6.4 What the model cost

Comparing the prescribed counts against the n at which each verdict became PASS and stayed PASS:

| Cell | prescribed n | earliest stable PASS | overstated |
|---|---|---|---|
| `F5_mixed\|medium` | 32 | 34 | 0.9× |
| `F3_rdd\|small` | 116 | 40 | 2.9× |
| `F2_join\|medium` | 141 | 33 | 4.3× |
| `F2_join\|small` | 165 | 38 | 4.3× |
| `F1_agg\|medium` | 202 | 45 | 4.5× |
| `F1_agg\|small` | 242 | never | — |
| `F5_mixed\|small` | 716 | 220 | 3.3× |

Approximately **3,000 of the 4,842 runs were not needed** to reach the verdicts reached.

**This is retrospective and is not a stopping rule**, and we stress the distinction because it
is the tempting misreading. The figure is knowable only after running to the prescribed n, and
the same trajectories show a verdict can be reached and then lost: `F5_mixed|small` is PASS at
n = 77, **INCONCLUSIVE again at n = 148**, and PASS from n = 220. An experimenter stopping at the
first PASS would have been wrong on at least two of seven cells. The over-provisioning is real;
"stop earlier" is not the remedy it appears to license.

---

## 7. Threats to Validity

**Single host.** All measurements come from one machine, one OS, one Spark version. The
overhead magnitudes should not be generalized; the *methodological* finding is more portable,
and is consistent with prior results on other runtimes [Barrett et al. 2017].

**The event-log arm is not a clean control.** Disabling event logging changes Spark's own
configuration, so that component conflates observer removal with a configuration change. We
never sum the two components into a single overhead figure.

**Reduced coverage.** Seven of eight cells; `F3_rdd|medium` was excluded for pre-existing
fragility, on evidence predating this study.

**One undecided cell.** The budget question is therefore *not* settled overall. We report six
PASS verdicts for six cells at six repetition counts, and explicitly decline to aggregate them
into a claim that the budget is met.

**The prefix trajectory is not a set of independent experiments.** Successive points share
observations; it shows how the interval evolved as data arrived.

**Local contention was not controlled.** We did not isolate the host, which is precisely how the
episodes became visible. A quieter host would likely produce a different — and possibly
misleadingly better-behaved — result.

---

## 8. Conclusion

We pre-registered a standard √n repetition model, ran 4,842 Spark jobs to test it, and it failed
on every cell. The mechanism is measurable: repetitions on a real system are episodically
autocorrelated, so the small-sample half-width that the model extrapolates from does not
estimate i.i.d. sampling error. The consequence is practical and two-sided — several times more
measurement than necessary on most cells, and a cell that never converged at all.

For practitioners sizing a measurement campaign, the actionable implication is not a corrected
constant. It is that a repetition count derived from a handful of pilot runs carries no
guarantee, and that reporting *whether the interval stabilised* matters more than reporting how
many repetitions were performed.

---

## 9. Artifact

All raw observations (4,842 records), per-stage specifications and reconciliations, the
analysis, and the figure are committed. The bootstrap is seeded and every statistic is imported
from the original n = 5 analysis code rather than reimplemented, so the extension is adjudicated
by exactly the procedure that adjudicated the initial result — a property enforced by a unit
test. The pre-registered prediction, the withdrawn FAIL, and the authorization for the
additional repetitions are all timestamped in the project's decision log, committed before the
data they govern.

---

## Appendix A — [PENDING: include only if DEC-044 §D2 is signed]

> **Draft note, not for submission.** The following is a *secondary, exploratory* analysis. Its
> inclusion is contingent on DEC-044 §D2 being signed; as of this draft that decision is
> unsigned, and this appendix must be removed if it is not adopted. It is **not** the registered
> acceptance quantity and no verdict above derives from it.

Because the protocol interleaves conditions within each repetition, the repetitions are matched,
and every level shift measured is common-mode. A paired statistic — the median over repetitions
of the per-repetition relative difference — differences the shift out. Using the same seed and
resample count:

| Cell | n | unpaired (registered) | paired (exploratory) | ratio |
|---|---|---|---|---|
| `F5_mixed\|medium` | 37 | 2.00 pp | 1.07 pp | 1.9× |
| `F3_rdd\|small` | 121 | 0.78 pp | 0.39 pp | 2.0× |
| `F2_join\|medium` | 146 | 0.51 pp | 0.43 pp | 1.2× |
| `F2_join\|small` | 170 | 0.48 pp | 0.36 pp | 1.3× |
| `F1_agg\|medium` | 207 | 0.34 pp | 0.25 pp | 1.4× |
| `F1_agg\|small` | 247 | **14.95 pp** | **0.42 pp** | **35.7×** |
| `F5_mixed\|small` | 721 | 0.86 pp | 0.18 pp | 4.8× |

Paired point estimates agree across all seven cells (−0.214% … +0.172%). The gap is modest where
the series is well behaved and opens to 35.7× only on the cell whose regime split is ~50/50 —
which is what a common-mode shift predicts.

We report this as exploratory and do **not** use it to decide `F1_agg|small`. Adopting it
retroactively would mean selecting a statistic because it produces the preferred outcome on data
already seen. The registered result stands; the paired statistic is pre-registered for future
work instead.

---

## References

1. T. Kalibera and R. Jones. *Rigorous Benchmarking in Reasonable Time.* ISMM 2013.
   doi:10.1145/2464157.2464160
2. E. Barrett, C. F. Bolz-Tereick, R. Killick, S. Mount, L. Tratt. *Virtual Machine Warmup Blows
   Hot and Cold.* Proc. ACM Program. Lang. 1, OOPSLA, 2017. doi:10.1145/3133876
3. T. Mytkowicz, A. Diwan, M. Hauswirth, P. F. Sweeney. *Producing Wrong Data Without Doing
   Anything Obviously Wrong!* ASPLOS 2009. — [VERIFY citation before submission]
4. Apache Spark. *Monitoring and Instrumentation*, Spark 3.5.x documentation.
