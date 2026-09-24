#!/usr/bin/env python
"""EXP-009 repetition-extension analysis - DEC-043, descriptive only.

Pools the DEC-040 observations (reps 1-5, unchanged on disk) with the DEC-043
stage repetitions (reps 6..n+5) and re-computes, per extended cell, exactly
the statistics DEC-042 adjudicated on: median +/- IQR, the 95% percentile
bootstrap CI of the relative median difference (PLAN line 180), and the
interval rule - a component verdict only when the whole interval lies on one
side of the 5% gate (PLAN line 45).

NOTHING STATISTICAL IS RE-IMPLEMENTED HERE. bootstrap_ci, _median, iqr,
overhead, adjudicate, required_n, the 5% threshold, the 4000 resamples and
the seed 0 are IMPORTED from scripts/analyze_exp009.py, so the extension is
adjudicated by the same procedure as the n=5 result and no threshold, test or
correction is invented.

It writes NEW artifacts and overwrites none: the DEC-042-signed
results/evaluation/exp009_analysis.json and
results/experiments/exp-009/analysis.json are read, never written.

THE PRE-REGISTERED PREDICTION UNDER TEST (DEC-043 s7)
  "The power model behind s3 says the CI half-width shrinks as 1/sqrt(n). At
   the authorized n each completed cell should reach a half-width of about 2
   percentage points. If the observed half-widths do not shrink as predicted,
   the noise is not independent between repetitions - drift, thermal or host
   contention - and the model is wrong."

  The test is a PREFIX TRAJECTORY, fixed before the data were seen and
  applied identically to every cell: for a grid of k values the CI is
  recomputed from the FIRST k repetitions in execution (rep) order. Prefixes
  in chronological order, never a selected subset - no repetition is dropped,
  reordered or excluded to smooth the curve. The grid always contains k=5
  (the DEC-040 result), k=n_authorized (the exact point DEC-043 s7 predicts
  ~2 pp for, because required_n solves half_5*sqrt(5/n)=2) and k=n_pooled.

  Reported per k: observed half-width; the model prediction
  half_5*sqrt(5/k); the ratio observed/predicted; and the normalised
  half*sqrt(k), which is CONSTANT if and only if the 1/sqrt(n) law holds.
  A log-log least-squares slope of half against k is reported as a
  diagnostic; the model predicts -0.5. No goodness-of-fit threshold is
  invented and no parameter is tuned to the observations.

DECIDED CELL (DEC-042 s3, DEC-043 s5)
  A COMPONENT is decided when its whole 95% CI lies on one side of the 5%
  gate (PASS below, FAIL above); a straddling interval is INCONCLUSIVE in
  both directions. DEC-043 s3 sizes each stage from the SYSMON component's
  required n, so the event-log component is reported at whatever resolution
  it happens to reach and is NOT expected to be decided by these stages. A
  CELL is decided only when both components are.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import random
import statistics
import sys
import time
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT / "src"))


def _load(name: str, filename: str):
    path = PROJECT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


AN = _load("analyze_exp009_canonical", "analyze_exp009.py")
EXT = _load("run_exp009_ext_canonical", "run_exp009_ext.py")

# Imported, never re-defined: the DEC-040/042 procedure.
THRESHOLD_PCT = AN.THRESHOLD_PCT
BOOTSTRAP_RESAMPLES = AN.BOOTSTRAP_RESAMPLES
BOOTSTRAP_SEED = AN.BOOTSTRAP_SEED
bootstrap_ci = AN.bootstrap_ci
adjudicate = AN.adjudicate
overhead = AN.overhead
required_n = AN.required_n
iqr = AN.iqr

BASELINE_REPS = EXT.BASELINE_REPS
TARGET_HALFWIDTH_PP = EXT.TARGET_HALFWIDTH_PP
CONDS = ("FULL", "NO-SYSMON", "NEITHER")

EXT_DIR = EXT.EXT_DIR
OUT_JSON = EXT_DIR / "analysis_ext.json"
EVAL_OUT = PROJECT / "results" / "evaluation" / "exp009_ext_analysis.json"
FIGURE = PROJECT / "docs" / "figures" / "exp009_ci_halfwidth_vs_reps.svg"
FIGURE_REGIME = PROJECT / "docs" / "figures" / "exp009_regime_structure.svg"

# Cells shown in the regime figure, chosen to span the observed behaviours:
# a within-stage warm-up step, a stable series punctuated by one contention
# episode, a ~50/50 bimodal series, and the longest series. Every cell's full
# data is in the artifact; this selection is presentational only.
REGIME_PANELS = ("F5_mixed|medium", "F1_agg|medium", "F1_agg|small",
                 "F5_mixed|small")

TRAJECTORY_POINTS = 10          # size of the prefix grid, fixed in advance
WINDOW = 20                     # presentation window for the regime series


def load_rows() -> tuple[list[dict], list[dict]]:
    base = [json.loads(line) for line in
            EXT.BASE.OBS_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    ext: list[dict] = []
    if EXT.OBS_PATH.exists():
        ext = [json.loads(line) for line in
               EXT.OBS_PATH.read_text(encoding="utf-8").splitlines()
               if line.strip()]
    return base, ext


def samples(rows: list[dict], fam: str, scale: str, cond: str) -> list[float]:
    """Timing-valid execution_time_s for one (cell, condition), in rep order.

    Same filter as analyze_exp009.cell_stats: runner clock, timing_valid,
    no error. Ordered by rep so a prefix is a chronological prefix.
    """
    got = [(r["rep"], r["execution_time_s"]) for r in rows
           if r.get("family") == fam and r.get("scale") == scale
           and r.get("condition") == cond and r.get("timing_valid")
           and r.get("execution_time_s") is not None
           and r.get("execution_time_source") == "runner"
           and not r.get("error")]
    return [v for _rep, v in sorted(got)]


def halfwidth(ci: tuple[float, float] | None) -> float | None:
    return None if ci is None else 0.5 * (ci[1] - ci[0])


def _by_rep(base_rows: list[dict], ext_rows: list[dict], fam: str,
            scale: str, cond: str) -> dict[int, float]:
    """{rep: execution_time_s} pooled over baseline and extension rows.

    Same row filter as ``samples``; keyed by rep so the three conditions can
    be matched within a repetition for the paired diagnostic.
    """
    out: dict[int, float] = {}
    for rows in (base_rows, ext_rows):
        for r in rows:
            if (r.get("family") == fam and r.get("scale") == scale
                    and r.get("condition") == cond and r.get("timing_valid")
                    and r.get("execution_time_s") is not None
                    and r.get("execution_time_source") == "runner"
                    and not r.get("error")):
                out[r["rep"]] = r["execution_time_s"]
    return out


def prefix_grid(n_pooled: int, n_authorized: int) -> list[int]:
    """Fixed k grid: always 5, the authorized n, and the pooled n."""
    must = {BASELINE_REPS, n_pooled}
    if BASELINE_REPS <= n_authorized <= n_pooled:
        must.add(n_authorized)
    span = n_pooled - BASELINE_REPS
    if span > 0:
        for i in range(1, TRAJECTORY_POINTS):
            must.add(int(round(BASELINE_REPS + span * i / TRAJECTORY_POINTS)))
    return sorted(k for k in must if k >= 2)


def trajectory(full: list[float], base: list[float], ks: list[int],
               label: str) -> list[dict[str, Any]]:
    """CI half-width from the first k repetitions, for each k in the grid."""
    out: list[dict[str, Any]] = []
    half5: float | None = None
    for k in ks:
        if len(full) < k or len(base) < k:
            continue
        ci = bootstrap_ci(full[:k], base[:k])
        half = halfwidth(ci)
        pct = overhead(AN._median(full[:k]), AN._median(base[:k]))
        if k == BASELINE_REPS:
            half5 = half
        predicted = (half5 * math.sqrt(BASELINE_REPS / k)
                     if half5 is not None else None)
        out.append({
            "component": label,
            "n_per_condition": k,
            "point_estimate_pct": pct,
            "ci95_pct": list(ci) if ci else None,
            "ci_halfwidth_pp": half,
            "predicted_halfwidth_pp": predicted,
            "observed_over_predicted": (half / predicted
                                        if half is not None and predicted
                                        else None),
            "normalised_halfwidth_times_sqrt_n": (half * math.sqrt(k)
                                                  if half is not None else None),
            "verdict": adjudicate(pct, ci, THRESHOLD_PCT),
        })
    return out


def drift_diagnostic(vals: list[float]) -> dict[str, Any] | None:
    """Is the repetition series independent, or is it drifting?

    POST-HOC, and labelled as such. It is computed because DEC-043 s7 names
    this exact alternative in advance - "if the observed half-widths do not
    shrink as predicted, the noise is not independent between repetitions -
    drift, thermal or host contention - and the model is wrong" - so when the
    trajectory departs from 1/sqrt(n) the record should say what the series
    actually did. It changes no verdict, no threshold and no pre-registered
    statistic; it is evidence about WHY, not a rescue of the prediction.
    """
    n = len(vals)
    if n < 6:
        return None
    half = n // 2
    first, second = vals[:half], vals[half:]
    m_first = statistics.median(first)
    m_second = statistics.median(second)
    mean = statistics.fmean(vals)
    den = sum((v - mean) ** 2 for v in vals)
    lag1 = (sum((vals[i] - mean) * (vals[i + 1] - mean) for i in range(n - 1))
            / den) if den else None
    return {
        "n": n,
        "median_first_half_s": m_first,
        "median_second_half_s": m_second,
        "level_shift_pct": (100.0 * (m_second - m_first) / m_first
                            if m_first else None),
        "lag1_autocorrelation": lag1,
        "cv_all_pct": 100.0 * statistics.pstdev(vals) / mean if mean else None,
        "cv_second_half_pct": (100.0 * statistics.pstdev(second)
                               / statistics.fmean(second)
                               if statistics.fmean(second) else None),
        # Robust counterparts. The CVs above are standard-deviation based and
        # a handful of transient host-contention runs can dominate them while
        # leaving the median untouched (F1_agg|medium: 3 runs of 111/107/62 s
        # against a stable 30.6 s median). The analysis itself is median-based
        # (PLAN:180), so a median-based dispersion is the like-for-like
        # summary. Both are reported; neither is a verdict and no observation
        # is excluded from either.
        "robust_dispersion_all_pct": (100.0 * iqr(vals)
                                      / statistics.median(vals)
                                      if statistics.median(vals) else None),
        "robust_dispersion_second_half_pct": (
            100.0 * iqr(second) / statistics.median(second)
            if statistics.median(second) else None),
        # Regime structure, in execution order. The series are not uniformly
        # noisy: they sit at a very stable level (windowed IQR/median ~1%)
        # punctuated by episodes of host contention that persist for tens of
        # CONSECUTIVE runs, which is what the lag-1 figure above is detecting.
        # The window is a fixed presentation size, not a threshold, and no
        # observation is excluded or reweighted by it.
        "window_size": WINDOW,
        "windowed": [
            {"start_index": i,
             "median_s": statistics.median(vals[i:i + WINDOW]),
             "robust_dispersion_pct": (
                 100.0 * iqr(vals[i:i + WINDOW])
                 / statistics.median(vals[i:i + WINDOW])
                 if statistics.median(vals[i:i + WINDOW]) else None)}
            for i in range(0, n - WINDOW + 1, WINDOW)],
    }


def paired_diagnostic(a: dict[int, float], b: dict[int, float],
                      label: str) -> dict[str, Any] | None:
    """Per-repetition paired relative difference. DIAGNOSTIC ONLY.

    THIS IS NOT THE ADJUDICATED STATISTIC AND CHANGES NO VERDICT. DEC-040 s7
    freezes the acceptance quantity as the difference of independent medians,
    and DEC-042 freezes the interval rule applied to it; both are computed
    unchanged elsewhere in this file and are what every verdict here rests on.

    It is recorded because the DEC-040 s5 protocol interleaves the three
    conditions WITHIN each (cell, rep), so the repetitions are already
    matched, and because the drift this experiment measured is common-mode -
    a level shift moves all three conditions at the same rep together. A
    paired statistic would therefore difference the shift out, while the
    unpaired one carries its full variance. Quantifying that gap is evidence
    about WHY the unpaired intervals behave as they do; acting on it would
    require its own decision and is NOT done here.

    Uses the same seed and resample count as the frozen procedure so the
    diagnostic is reproducible on the same terms.
    """
    reps = sorted(set(a) & set(b))
    if len(reps) < 2:
        return None
    paired = [100.0 * (a[r] - b[r]) / b[r] for r in reps if b[r]]
    if len(paired) < 2:
        return None
    rng = random.Random(BOOTSTRAP_SEED)
    draws = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        draws.append(AN._median(
            [paired[rng.randrange(len(paired))] for _ in paired]))
    draws.sort()
    lo = draws[int(0.025 * len(draws))]
    hi = draws[min(int(0.975 * len(draws)), len(draws) - 1)]
    return {
        "component": label,
        "n_paired_repetitions": len(paired),
        "paired_median_pct": AN._median(paired),
        "paired_ci95_pct": [lo, hi],
        "paired_ci_halfwidth_pp": 0.5 * (hi - lo),
        "status": ("DIAGNOSTIC ONLY - not the DEC-040 s7 acceptance "
                   "quantity; no verdict is derived from it"),
    }


def earliest_stable_pass(traj: list[dict[str, Any]]) -> int | None:
    """Smallest grid n whose verdict is PASS and stays PASS to the end.

    RETROSPECTIVE. It is knowable only after running to the authorized n, so
    it is NOT a prospective stopping rule and must not be read as one: the
    same trajectories show a verdict can be reached and then LOST
    (F5_mixed|small is PASS at n=77, INCONCLUSIVE again at n=148; see also
    F1_agg|small). It is reported to quantify how far the DEC-042 s5
    required-n figures departed from what the measurement actually needed,
    at the resolution of the prefix grid - the true crossing lies between
    this point and the previous grid point.
    """
    for i, p in enumerate(traj):
        if all(q["verdict"] == "PASS" for q in traj[i:]):
            return p["n_per_condition"]
    return None


def loglog_slope(points: list[dict[str, Any]]) -> float | None:
    """Least-squares slope of log(half-width) on log(n). Model predicts -0.5."""
    xs, ys = [], []
    for p in points:
        if p["ci_halfwidth_pp"] and p["ci_halfwidth_pp"] > 0:
            xs.append(math.log(p["n_per_condition"]))
            ys.append(math.log(p["ci_halfwidth_pp"]))
    if len(xs) < 3:
        return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den


def analyse_cell(stage: dict[str, Any], base_rows: list[dict],
                 ext_rows: list[dict]) -> dict[str, Any]:
    fam, scale = stage["family"], stage["scale"]
    cell = "%s|%s" % (fam, scale)
    pooled = {c: samples(base_rows, fam, scale, c)
              + samples(ext_rows, fam, scale, c) for c in CONDS}
    n_new = {c: len(samples(ext_rows, fam, scale, c)) for c in CONDS}
    n_pool = {c: len(pooled[c]) for c in CONDS}
    n_min = min(n_pool.values())

    s_full, s_nosys, s_neith = (pooled["FULL"], pooled["NO-SYSMON"],
                                pooled["NEITHER"])
    m_full, m_nosys, m_neith = (statistics.median(s_full) if s_full else None,
                                statistics.median(s_nosys) if s_nosys else None,
                                statistics.median(s_neith) if s_neith else None)
    sys_pct = overhead(m_full, m_nosys)
    elog_pct = overhead(m_nosys, m_neith)
    sys_ci = bootstrap_ci(s_full, s_nosys)
    elog_ci = bootstrap_ci(s_nosys, s_neith)
    sys_verdict = adjudicate(sys_pct, sys_ci, THRESHOLD_PCT)
    elog_verdict = adjudicate(elog_pct, elog_ci, THRESHOLD_PCT)

    n_auth = BASELINE_REPS + stage["n"]        # pooled n at the authorized n
    ks = prefix_grid(n_min, stage["n"])
    traj_sys = trajectory(s_full, s_nosys, ks, "sysmon")
    traj_elog = trajectory(s_nosys, s_neith, ks, "eventlog")

    at_auth = next((p for p in traj_sys
                    if p["n_per_condition"] == stage["n"]), None)
    at_full = traj_sys[-1] if traj_sys else None

    if sys_verdict == "INCONCLUSIVE" or elog_verdict == "INCONCLUSIVE":
        cell_verdict = ("FAIL" if "FAIL" in (sys_verdict, elog_verdict)
                        else "INCONCLUSIVE")
    elif sys_verdict == elog_verdict == "PASS":
        cell_verdict = "PASS"
    else:
        cell_verdict = "FAIL"

    return {
        "cell": cell,
        "stage": stage["stage"],
        "n_per_condition_baseline": BASELINE_REPS,
        "n_per_condition_new": n_new,
        "n_per_condition_pooled": n_pool,
        "n_per_condition_pooled_min": n_min,
        "n_authorized_new_per_condition": stage["n"],
        "n_authorized_pooled_per_condition": n_auth,
        "conditions": {
            c: {"n": n_pool[c],
                "median_s": statistics.median(pooled[c]) if pooled[c] else None,
                "iqr_s": iqr(pooled[c]),
                "min_s": min(pooled[c]) if pooled[c] else None,
                "max_s": max(pooled[c]) if pooled[c] else None}
            for c in CONDS},
        "overhead_sysmon_pct": sys_pct,
        "overhead_eventlog_pct": elog_pct,
        "combined_sum_pct": (sys_pct + elog_pct
                             if sys_pct is not None and elog_pct is not None
                             else None),
        "combined_caveat": ("sum of parts; elog arm changes Spark config "
                            "(DEC-040 s4)"),
        "threshold_pct": THRESHOLD_PCT,
        "sysmon_ci95_pct": list(sys_ci) if sys_ci else None,
        "eventlog_ci95_pct": list(elog_ci) if elog_ci else None,
        "sysmon_ci_halfwidth_pp": halfwidth(sys_ci),
        "eventlog_ci_halfwidth_pp": halfwidth(elog_ci),
        "sysmon_verdict": sys_verdict,
        "eventlog_verdict": elog_verdict,
        "sysmon_decided": sys_verdict != "INCONCLUSIVE",
        "eventlog_decided": elog_verdict != "INCONCLUSIVE",
        "verdict": cell_verdict,
        "cell_decided": cell_verdict != "INCONCLUSIVE",
        "reps_needed_for_2pp_halfwidth_recomputed": {
            "sysmon": required_n(s_full, s_nosys, THRESHOLD_PCT),
            "eventlog": required_n(s_nosys, s_neith, THRESHOLD_PCT)},
        "power_model": {
            "prediction": ("CI half-width proportional to 1/sqrt(n); "
                           "~%.1f pp at the authorized n (DEC-043 s7)"
                           % TARGET_HALFWIDTH_PP),
            "prefix_grid_n": ks,
            "sysmon_trajectory": traj_sys,
            "eventlog_trajectory": traj_elog,
            "sysmon_loglog_slope": loglog_slope(traj_sys),
            "eventlog_loglog_slope": loglog_slope(traj_elog),
            "predicted_loglog_slope": -0.5,
            "sysmon_halfwidth_at_authorized_n_pp": (
                at_auth["ci_halfwidth_pp"] if at_auth else None),
            "sysmon_observed_over_predicted_at_authorized_n": (
                at_auth["observed_over_predicted"] if at_auth else None),
            "sysmon_halfwidth_at_pooled_n_pp": (
                at_full["ci_halfwidth_pp"] if at_full else None),
            "sysmon_observed_over_predicted_at_pooled_n": (
                at_full["observed_over_predicted"] if at_full else None),
            "target_halfwidth_pp": TARGET_HALFWIDTH_PP,
            # Descriptive facts about the trajectory shape, not new thresholds.
            "sysmon_earliest_stable_pass_n": earliest_stable_pass(traj_sys),
            "sysmon_required_n_overstatement": (
                stage["n"] / earliest_stable_pass(traj_sys)
                if earliest_stable_pass(traj_sys) else None),
            "earliest_stable_pass_caveat": (
                "RETROSPECTIVE, not a prospective stopping rule; knowable "
                "only after running to the authorized n, and a verdict can "
                "be reached and then lost"),
            "sysmon_trajectory_monotone_decreasing": _monotone(traj_sys),
            "sysmon_max_observed_over_predicted": _max_ratio(traj_sys),
            "eventlog_trajectory_monotone_decreasing": _monotone(traj_elog),
            "eventlog_max_observed_over_predicted": _max_ratio(traj_elog),
        },
        "paired_diagnostic": {
            "note": ("DIAGNOSTIC ONLY. The adjudicated quantity remains the "
                     "DEC-040 s7 difference of independent medians reported "
                     "above; no verdict here is derived from these numbers. "
                     "Recorded because the protocol already interleaves the "
                     "three conditions within each (cell, rep), so the "
                     "repetitions are matched, and the measured drift is "
                     "common-mode. Acting on this would require its own "
                     "decision and is NOT done here."),
            "sysmon": paired_diagnostic(
                _by_rep(base_rows, ext_rows, fam, scale, "FULL"),
                _by_rep(base_rows, ext_rows, fam, scale, "NO-SYSMON"),
                "sysmon"),
            "eventlog": paired_diagnostic(
                _by_rep(base_rows, ext_rows, fam, scale, "NO-SYSMON"),
                _by_rep(base_rows, ext_rows, fam, scale, "NEITHER"),
                "eventlog"),
        },
        "drift_diagnostic": {
            "note": ("POST-HOC, prompted by the DEC-043 s7 falsification "
                     "clause; changes no verdict and no pre-registered "
                     "statistic"),
            "per_condition": {c: drift_diagnostic(pooled[c]) for c in CONDS},
            "common_mode_level_shift": _common_mode(
                {c: drift_diagnostic(pooled[c]) for c in CONDS}),
        },
    }


def _monotone(traj: list[dict[str, Any]]) -> bool | None:
    hs = [p["ci_halfwidth_pp"] for p in traj if p["ci_halfwidth_pp"]]
    if len(hs) < 3:
        return None
    return all(b <= a for a, b in zip(hs, hs[1:]))


def _max_ratio(traj: list[dict[str, Any]]) -> float | None:
    rs = [p["observed_over_predicted"] for p in traj
          if p["observed_over_predicted"]]
    return max(rs) if rs else None


def _common_mode(diags: dict[str, Any]) -> dict[str, Any]:
    """A shift present in ALL conditions is host drift, not an overhead effect.

    A common-mode shift partially cancels in the PAIRED difference of medians
    that the overhead statistic is built from, but it still violates the
    independence the 1/sqrt(n) power model assumes.
    """
    shifts = {c: d["level_shift_pct"] for c, d in diags.items()
              if d and d.get("level_shift_pct") is not None}
    if len(shifts) < 2:
        return {"shifts_pct": shifts, "common_mode": None}
    vals = list(shifts.values())
    return {
        "shifts_pct": shifts,
        "min_pct": min(vals),
        "max_pct": max(vals),
        "spread_pct": max(vals) - min(vals),
        "all_same_sign": all(v < 0 for v in vals) or all(v > 0 for v in vals),
        "common_mode": (all(v < 0 for v in vals) or all(v > 0 for v in vals))
        and (max(vals) - min(vals)) < abs(statistics.fmean(vals)),
    }


# --- figure (stdlib SVG; matplotlib is a declared extra but is deliberately
# --- NOT installed in the canonical stdlib-only analysis environment) --------
PALETTE = ("#1f4e79", "#b03a2e", "#1e8449", "#7d3c98")


def _fmt(x: float) -> str:
    return ("%.3f" % x).rstrip("0").rstrip(".")


COND_STYLE = {"FULL": ("#1f4e79", 1.0), "NO-SYSMON": ("#b03a2e", 1.0),
              "NEITHER": ("#1e8449", 1.0)}


def write_regime_figure(base_rows: list[dict], ext_rows: list[dict],
                        meta: dict[str, Any]) -> None:
    """Execution time against repetition index, all three conditions overlaid.

    This is the evidence for the mechanism claim in a way the CI-vs-n figure
    cannot show: the level shifts and contention episodes are visible, and
    because the three conditions are drawn together it is apparent that they
    move TOGETHER (common-mode) rather than the instrumentation under test
    causing them. Panels are autoscaled per cell because the cells differ by
    an order of magnitude in duration.
    """
    if not any(_by_rep(base_rows, ext_rows, *c.split("|"), "FULL")
               for c in REGIME_PANELS):
        return
    PW, PH = 860, 122               # panel plot area
    L, R, T, GAP, B = 92, 150, 54, 30, 56
    H = T + len(REGIME_PANELS) * (PH + GAP) + B
    W = L + PW + R
    o: list[str] = []
    o.append('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
             'viewBox="0 0 %d %d" font-family="DejaVu Sans, Arial, sans-serif">'
             % (W, H, W, H))
    o.append('<rect width="%d" height="%d" fill="#ffffff"/>' % (W, H))
    o.append('<text x="%d" y="26" font-size="16" font-weight="bold" '
             'fill="#111">EXP-009: execution time by repetition — regime '
             'structure, not noise</text>' % L)
    o.append('<text x="%d" y="44" font-size="11" fill="#555">all three '
             'conditions overlaid; shifts move them TOGETHER (common-mode), '
             'so they are host behaviour, not the instrumentation under '
             'test</text>' % L)

    for idx, cell in enumerate(REGIME_PANELS):
        fam, scale = cell.split("|")
        top = T + idx * (PH + GAP)
        series = {cond: _by_rep(base_rows, ext_rows, fam, scale, cond)
                  for cond in COND_STYLE}
        allv = [v for s in series.values() for v in s.values()]
        if not allv:
            continue
        reps = sorted({r for s in series.values() for r in s})
        x0, x1 = min(reps), max(reps)
        y0, y1 = min(allv) * 0.94, max(allv) * 1.06

        def px(r: float, _x0=x0, _x1=x1) -> float:
            return L + PW * (r - _x0) / ((_x1 - _x0) or 1)

        def py(v: float, _y0=y0, _y1=y1, _t=top) -> float:
            return _t + PH * (1.0 - (v - _y0) / ((_y1 - _y0) or 1.0))

        o.append('<rect x="%d" y="%d" width="%d" height="%d" fill="#fbfbfb" '
                 'stroke="#333"/>' % (L, top, PW, PH))
        for frac in (0.0, 0.5, 1.0):
            v = y0 + (y1 - y0) * frac
            o.append('<text x="%d" y="%s" font-size="10" fill="#444" '
                     'text-anchor="end">%.0f s</text>'
                     % (L - 7, _fmt(py(v) + 3), v))
        o.append('<text x="%d" y="%s" font-size="12" font-weight="bold" '
                 'fill="#111">%s</text>' % (L + 6, _fmt(top - 6), cell))
        o.append('<text x="%d" y="%s" font-size="10" fill="#666">n = %d per '
                 'condition</text>'
                 % (L + PW - 116, _fmt(top - 6), len(series["FULL"])))
        for r in (5, x1):
            if x0 <= r <= x1:
                o.append('<text x="%s" y="%d" font-size="10" fill="#444" '
                         'text-anchor="middle">%d</text>'
                         % (_fmt(px(r)), top + PH + 14, r))
        # the five DEC-040 baseline repetitions, marked so the reader can see
        # which part of each series the power model was anchored on
        if x0 <= 5 <= x1:
            o.append('<rect x="%s" y="%d" width="%s" height="%d" '
                     'fill="#d68910" opacity="0.13"/>'
                     % (_fmt(px(x0)), top, _fmt(max(px(5) - px(x0), 1.2)), PH))
        for cond, (col, wd) in COND_STYLE.items():
            pts = sorted(series[cond].items())
            if not pts:
                continue
            o.append('<polyline points="%s" fill="none" stroke="%s" '
                     'stroke-width="%.1f" opacity="0.82"/>'
                     % (" ".join("%s,%s" % (_fmt(px(r)), _fmt(py(v)))
                                 for r, v in pts), col, wd))
    legend_y = T + 4
    for cond, (col, _w) in COND_STYLE.items():
        o.append('<rect x="%d" y="%d" width="14" height="3" fill="%s"/>'
                 % (L + PW + 14, legend_y, col))
        o.append('<text x="%d" y="%d" font-size="11" fill="#222">%s</text>'
                 % (L + PW + 34, legend_y + 5, cond))
        legend_y += 20
    o.append('<rect x="%d" y="%d" width="14" height="10" fill="#d68910" '
             'opacity="0.25"/>' % (L + PW + 14, legend_y + 4))
    o.append('<text x="%d" y="%d" font-size="10" fill="#666">reps 1–5:</text>'
             % (L + PW + 34, legend_y + 9))
    o.append('<text x="%d" y="%d" font-size="10" fill="#666">the power '
             'model\'s</text>' % (L + PW + 34, legend_y + 22))
    o.append('<text x="%d" y="%d" font-size="10" fill="#666">anchor</text>'
             % (L + PW + 34, legend_y + 34))
    o.append('<text x="%d" y="%d" font-size="12" fill="#222" '
             'text-anchor="middle">repetition index</text>'
             % (L + PW // 2, H - 24))
    o.append('<text x="%d" y="%d" font-size="9" fill="#888">source: '
             'results/experiments/exp-009/ext/analysis_ext.json | artifact '
             '%s</text>' % (L, H - 6, meta.get("artifact_id", "")[:16]))
    o.append("</svg>")
    FIGURE_REGIME.parent.mkdir(parents=True, exist_ok=True)
    FIGURE_REGIME.write_text("\n".join(o), encoding="utf-8")


def write_figure(cells: list[dict[str, Any]], meta: dict[str, Any]) -> None:
    """CI half-width against repetition count, observed vs 1/sqrt(n) model."""
    W, H = 900, 560
    L, R, T, B = 85, 250, 60, 70
    pw, ph = W - L - R, H - T - B
    pts = [(p["n_per_condition"], p["ci_halfwidth_pp"])
           for c in cells for p in c["power_model"]["sysmon_trajectory"]
           if p["ci_halfwidth_pp"]]
    if not pts:
        return
    xs = [x for x, _ in pts]
    ys = [y for _, y in pts] + [TARGET_HALFWIDTH_PP]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys) * 0.8, max(ys) * 1.15

    def px(v: float) -> float:
        return L + pw * (math.log(v) - math.log(x0)) / (
            math.log(x1) - math.log(x0) or 1.0)

    def py(v: float) -> float:
        return T + ph * (1.0 - (math.log(v) - math.log(y0)) / (
            math.log(y1) - math.log(y0) or 1.0))

    o: list[str] = []
    o.append('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
             'viewBox="0 0 %d %d" font-family="DejaVu Sans, Arial, sans-serif">'
             % (W, H, W, H))
    o.append('<rect width="%d" height="%d" fill="#ffffff"/>' % (W, H))
    o.append('<text x="%d" y="28" font-size="16" font-weight="bold" '
             'fill="#111">EXP-009 DEC-043: 95%% bootstrap CI half-width vs '
             'repetitions (sysmon component)</text>' % L)
    o.append('<text x="%d" y="46" font-size="11" fill="#555">log-log; '
             'observed = pooled DEC-040 reps 1-5 + DEC-043 stage reps; '
             'dashed = pre-registered 1/sqrt(n) from each cell\'s own n=5 '
             'half-width</text>' % L)

    for k in (5, 10, 20, 50, 100, 200):
        if x0 <= k <= x1:
            X = px(k)
            o.append('<line x1="%s" y1="%d" x2="%s" y2="%d" stroke="#e8e8e8"/>'
                     % (_fmt(X), T, _fmt(X), T + ph))
            o.append('<text x="%s" y="%d" font-size="11" fill="#444" '
                     'text-anchor="middle">%d</text>' % (_fmt(X), T + ph + 18, k))
    for v in (1, 2, 5, 10, 20, 50):
        if y0 <= v <= y1:
            Y = py(v)
            o.append('<line x1="%d" y1="%s" x2="%d" y2="%s" stroke="#e8e8e8"/>'
                     % (L, _fmt(Y), L + pw, _fmt(Y)))
            o.append('<text x="%d" y="%s" font-size="11" fill="#444" '
                     'text-anchor="end">%d</text>' % (L - 8, _fmt(Y + 4), v))
    o.append('<rect x="%d" y="%d" width="%d" height="%d" fill="none" '
             'stroke="#333"/>' % (L, T, pw, ph))
    o.append('<text x="%d" y="%d" font-size="12" fill="#222" '
             'text-anchor="middle">repetitions per condition, n</text>'
             % (L + pw // 2, H - 22))
    o.append('<text x="18" y="%d" font-size="12" fill="#222" '
             'text-anchor="middle" transform="rotate(-90 18 %d)">CI half-width '
             '(percentage points)</text>' % (T + ph // 2, T + ph // 2))

    if y0 <= TARGET_HALFWIDTH_PP <= y1:
        Y = py(TARGET_HALFWIDTH_PP)
        o.append('<line x1="%d" y1="%s" x2="%d" y2="%s" stroke="#d68910" '
                 'stroke-width="2" stroke-dasharray="2,3"/>'
                 % (L, _fmt(Y), L + pw, _fmt(Y)))
        o.append('<text x="%d" y="%s" font-size="11" fill="#d68910">'
                 '~%.0f pp target (DEC-043 s7)</text>'
                 % (L + pw + 8, _fmt(Y + 4), TARGET_HALFWIDTH_PP))

    legend_y = T + 6
    for i, c in enumerate(cells):
        col = PALETTE[i % len(PALETTE)]
        traj = [p for p in c["power_model"]["sysmon_trajectory"]
                if p["ci_halfwidth_pp"]]
        if not traj:
            continue
        obs = " ".join("%s,%s" % (_fmt(px(p["n_per_condition"])),
                                  _fmt(py(p["ci_halfwidth_pp"])))
                       for p in traj)
        o.append('<polyline points="%s" fill="none" stroke="%s" '
                 'stroke-width="2.2"/>' % (obs, col))
        pred = [p for p in traj if p["predicted_halfwidth_pp"]]
        if pred:
            o.append('<polyline points="%s" fill="none" stroke="%s" '
                     'stroke-width="1.6" stroke-dasharray="6,4" '
                     'opacity="0.75"/>'
                     % (" ".join("%s,%s"
                                 % (_fmt(px(p["n_per_condition"])),
                                    _fmt(py(p["predicted_halfwidth_pp"])))
                                 for p in pred), col))
        for p in traj:
            o.append('<circle cx="%s" cy="%s" r="3.1" fill="%s"/>'
                     % (_fmt(px(p["n_per_condition"])),
                        _fmt(py(p["ci_halfwidth_pp"])), col))
        slope = c["power_model"]["sysmon_loglog_slope"]
        o.append('<rect x="%d" y="%d" width="12" height="3" fill="%s"/>'
                 % (L + pw + 12, legend_y, col))
        o.append('<text x="%d" y="%d" font-size="11" fill="#222">%s</text>'
                 % (L + pw + 30, legend_y + 5, c["cell"]))
        o.append('<text x="%d" y="%d" font-size="10" fill="#666">stage %d, '
                 'n=%d, slope %s</text>'
                 % (L + pw + 30, legend_y + 19, c["stage"],
                    c["n_per_condition_pooled_min"],
                    ("%.2f" % slope) if slope is not None else "n/a"))
        o.append('<text x="%d" y="%d" font-size="10" fill="#666">sysmon '
                 '%s</text>' % (L + pw + 30, legend_y + 32, c["sysmon_verdict"]))
        legend_y += 50

    o.append('<text x="%d" y="%d" font-size="10" fill="#222">solid = observed'
             '</text>' % (L + pw + 12, legend_y + 8))
    o.append('<text x="%d" y="%d" font-size="10" fill="#222">dashed = model '
             '1/sqrt(n)</text>' % (L + pw + 12, legend_y + 22))
    o.append('<text x="%d" y="%d" font-size="10" fill="#666">bootstrap: %d '
             'resamples, seed %d</text>'
             % (L + pw + 12, legend_y + 40, BOOTSTRAP_RESAMPLES, BOOTSTRAP_SEED))
    o.append('<text x="%d" y="%d" font-size="9" fill="#888">source: %s | '
             'artifact %s</text>'
             % (L, H - 6, "results/experiments/exp-009/ext/analysis_ext.json",
                meta.get("artifact_id", "")[:16]))
    o.append("</svg>")
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    FIGURE.write_text("\n".join(o), encoding="utf-8")


def main() -> int:
    base_rows, ext_rows = load_rows()
    if not ext_rows:
        raise SystemExit("refusing: no DEC-043 observations recorded yet")
    EXT.check_baseline_untouched()
    for row in ext_rows:
        if row.get("aqe_enabled"):
            raise SystemExit("refusing: aqe true in %s" % row.get("run_id"))
        if row.get("split") != "validation":
            raise SystemExit("refusing: non-validation row %s" % row.get("run_id"))
        if row.get("authorized_by") != "DEC-043":
            raise SystemExit("refusing: row %s not DEC-043" % row.get("run_id"))
    ids = [r["run_id"] for r in ext_rows]
    if len(ids) != len(set(ids)):
        raise SystemExit("refusing: duplicate run_id in the extension record")
    overlap = set(ids) & {r["run_id"] for r in base_rows}
    if overlap:
        raise SystemExit("refusing: extension re-ran %s" % sorted(overlap)[:3])

    stages_done = []
    for stage in EXT.STAGES:
        path = EXT.stage_summary_path(stage["stage"])
        if path.exists():
            stages_done.append(json.loads(path.read_text(encoding="utf-8")))
    if not stages_done:
        raise SystemExit("refusing: no completed stage summary")

    cells = [analyse_cell(EXT.STAGE_BY_ID[s["stage"]], base_rows, ext_rows)
             for s in stages_done]
    decided = [c["cell"] for c in cells if c["cell_decided"]]
    sys_decided = [c["cell"] for c in cells if c["sysmon_decided"]]

    body = {
        "schema_version": "exp009-ext/v1",
        "experiment_id": "EXP-009",
        "authorized_by": "DEC-043",
        "extends": "DEC-040 (protocol), DEC-042 (interval rule)",
        "statistic": "median over pooled repetitions",
        "spread": "IQR (PLAN:180)",
        "uncertainty": {
            "interval": "95% percentile bootstrap CI (PLAN:180)",
            "resamples": BOOTSTRAP_RESAMPLES,
            "seed": BOOTSTRAP_SEED,
            "rule": ("a component verdict is returned only when the whole "
                     "interval lies on one side of the gate; a straddling "
                     "interval is INCONCLUSIVE in BOTH directions (DEC-042)"),
            "imported_from": "scripts/analyze_exp009.py (not re-implemented)",
        },
        "threshold_pct": THRESHOLD_PCT,
        "threshold_source": "PLAN line 45 (SC6 clause 2)",
        "stages_executed": [s["stage"] for s in stages_done],
        "stage_summaries": [
            {k: s.get(k) for k in
             ("stage", "cell", "stage_status", "executions_authorized",
              "executions_recorded", "executions_timing_valid",
              "sc6_live_before", "sc6_live_after", "sc6_charged",
              "artifact_id", "wall_clock_seconds")} for s in stages_done],
        "cells": cells,
        "cells_decided": decided,
        "cells_sysmon_component_decided": sys_decided,
        "n_new_observations": len(ext_rows),
        "n_baseline_observations": len(base_rows),
        "baseline_observations_sha256": EXT.BASELINE_OBS_SHA256,
        "baseline_analysis_artifact_id": EXT.SOURCE_ANALYSIS_ARTIFACT_ID,
        "power_model_note": (
            "prefix trajectory in execution order; k grid fixed before the "
            "data were seen; no repetition dropped, reordered or excluded; "
            "no goodness-of-fit threshold invented and no parameter tuned "
            "to the observations"),
        "decided_definition": (
            "a component is decided when its whole 95% CI lies on one side "
            "of the 5% gate; a cell is decided when both components are. "
            "DEC-043 s3 sizes stages from the SYSMON required n, so the "
            "event-log component is not expected to be decided by these "
            "stages"),
        "register_line": "EXP-009 (0 charged to SC6)",
        "sc6_charged": sum(s.get("sc6_charged", 0) for s in stages_done),
        "sc6_cap": 500,
        "contains_test_data": False,
        "no_inference": "descriptive only; no significance test (DEC-040 s7)",
        "limitations": [
            ("The event-log arm is a configuration difference, not a pure "
             "observer removal (DEC-040 s4); the two components are never "
             "summed as an acceptance quantity without that caveat."),
            ("F3_rdd|medium remains excluded (DEC-040 s6, DEC-042 s2); "
             "coverage is unchanged by this extension."),
            ("DEC-043 s3 sizes n from the sysmon component only, so an "
             "undecided event-log component at these n is expected and is "
             "not evidence against the power model."),
            ("The prefix trajectory shares observations between its k "
             "points, so successive points are not independent of one "
             "another; it shows how the interval evolved as data arrived, "
             "not a set of independent experiments."),
        ],
        "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    canon = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    body["artifact_id"] = hashlib.sha256(canon).hexdigest()
    EXT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(body, indent=1, sort_keys=True),
                        encoding="utf-8")
    EVAL_OUT.parent.mkdir(parents=True, exist_ok=True)
    EVAL_OUT.write_text(json.dumps(body, indent=1, sort_keys=True),
                        encoding="utf-8")
    write_figure(cells, body)
    write_regime_figure(base_rows, ext_rows, body)

    print("EXP-009 DEC-043 extension: stages %s, %d new observations"
          % (body["stages_executed"], len(ext_rows)))
    for c in cells:
        pm = c["power_model"]
        print("  %-16s n=%-4d sysmon=%7.3f%% CI=[%7.3f,%7.3f] half=%5.2fpp "
              "%-12s slope=%s obs/pred=%s"
              % (c["cell"], c["n_per_condition_pooled_min"],
                 c["overhead_sysmon_pct"],
                 c["sysmon_ci95_pct"][0], c["sysmon_ci95_pct"][1],
                 c["sysmon_ci_halfwidth_pp"], c["sysmon_verdict"],
                 ("%+.3f" % pm["sysmon_loglog_slope"])
                 if pm["sysmon_loglog_slope"] is not None else "n/a",
                 ("%.2f" % pm["sysmon_observed_over_predicted_at_pooled_n"])
                 if pm["sysmon_observed_over_predicted_at_pooled_n"] else "n/a"))
        print("  %-16s          elog  =%7.3f%% CI=[%7.3f,%7.3f] half=%5.2fpp %s"
              % ("", c["overhead_eventlog_pct"],
                 c["eventlog_ci95_pct"][0], c["eventlog_ci95_pct"][1],
                 c["eventlog_ci_halfwidth_pp"], c["eventlog_verdict"]))
    print("  cells decided (both components): %s" % (decided or "none"))
    print("  sysmon component decided: %s" % (sys_decided or "none"))
    print("  artifact %s" % body["artifact_id"][:16])
    print("  figure   %s" % FIGURE)
    print("  figure   %s" % FIGURE_REGIME)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
