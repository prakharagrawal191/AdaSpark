#!/usr/bin/env python
"""EXP-009 robustness re-analysis - Track R (R1/R2/R4/R5/R6/R7/R8), descriptive only.

METHOD (frozen before running; see docs/research/PAPER_FOLLOWUP_TASKS.md):
  Inputs are the COMMITTED observations only
  (results/experiments/exp-009/observations.jsonl + ext/observations_ext.jsonl).
  Series are built with analyze_exp009_ext.samples (same filter, rep order).
  The adjudicated quantity is unchanged: overhead() of arm medians and
  adjudicate() vs THRESHOLD_PCT=5.0, imported from analyze_exp009 - never
  redefined. The i.i.d. percentile bootstrap draw statistic is replicated
  exactly (same RNG consumption) with the seed parameterized.

  R1: seed sensitivity (seeds 0-4, 4000 draws), BCa CI (seed 0), circular
      block-bootstrap percentile CI (block lengths 5/10/20, seed 0) for the
      sysmon component (FULL vs NO-SYSMON) on all 7 pooled cells.
  R2: per (cell, condition) pooled series (21): n, ACF lags 1-10 with the
      drift_diagnostic lag estimator form, white-noise reference band
      +-1.96/sqrt(n) (reference, NOT a gate), CUSUM single-changepoint scan
      (location + median-based shift %).
  R4: cost accounting from committed rows (counts, wall-clock span, bytes).
  R5: per-cell per-condition n + median runtime.
  R6: F1_agg|small FULL-series bimodality: 20-bin histogram, bimodality
      coefficient (skew^2+1)/kurtosis, histogram modes, CUSUM split.
  R7: eventlog component (NO-SYSMON vs NEITHER) pooled point + i.i.d. CI +
      verdict with the frozen estimator; monotone inputs read from the
      committed artifact (no recomputation).
  R8: stabilization-rule sensitivity on committed artifact trajectories:
      canonical (PASS and stays PASS), V1 (last-2 grid points PASS), V2
      (first PASS anywhere). Descriptive.

NOTHING here adjudicates, re-verdicts, or moves any recorded result. A
variant that moves a verdict is REPORTED, not hidden; no threshold, test, or
correction is invented. Writes ONE new file, overwrites none. Zero Spark
executions. Read-only guards mirror analyze_exp009_ext.main.
"""
from __future__ import annotations

import importlib.util
import json
import math
import random
import statistics
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT / "src"))

OUT_DIR = Path(r"C:\Users\prakh\AppData\Local\Temp\opencode\robustness")
OUT_JSON = OUT_DIR / "exp009_robustness.json"


def _load(name: str, filename: str):
    path = PROJECT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


AN = _load("rb_canonical", "analyze_exp009.py")
XE = _load("rb_ext", "analyze_exp009_ext.py")
EXT = _load("rb_runext", "run_exp009_ext.py")

THRESHOLD_PCT = AN.THRESHOLD_PCT
RESAMPLES = AN.BOOTSTRAP_RESAMPLES
SEEDS = (0, 1, 2, 3, 4)
BLOCKS = (5, 10, 20)
CONDS = ("FULL", "NO-SYSMON", "NEITHER")


def _median(vals):
    return AN._median(vals)


def _stat(a, b):
    mb = _median(b)
    if not mb:
        return None
    return 100.0 * (_median(a) - mb) / mb


def _percentile_ci_from_draws(draws):
    draws = sorted(draws)
    n = len(draws)
    lo = draws[int(0.025 * n)]
    hi = draws[min(int(0.975 * n), n - 1)]
    return lo, hi


def iid_draws(full, base, seed, resamples=RESAMPLES):
    """Exact replication of analyze_exp009.bootstrap_ci draw stream."""
    rng = random.Random(seed)
    draws = []
    for _ in range(resamples):
        ra = [full[rng.randrange(len(full))] for _ in full]
        rb = [base[rng.randrange(len(base))] for _ in base]
        v = _stat(ra, rb)
        if v is not None:
            draws.append(v)
    return draws


def _phi(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _phi_inv(p):
    """Acklam rational approximation; p in (0,1)."""
    p = min(max(p, 1e-300), 1.0 - 1e-15)
    a = (-3.969683028665376e+01, 2.209460984245205e+02,
         -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02,
         -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141287968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01,
         2.445134137142996e+00, 3.754408661907416e+00)
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
                ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def bca_ci(full, base, draws, point):
    """BCa interval over the seed-0 draw distribution (descriptive)."""
    n = len(draws)
    z0 = _phi_inv(sum(1 for d in draws if d < point) / n)
    ju, jv = [], []
    for i in range(len(full)):
        v = _stat(full[:i] + full[i + 1:], base)
        if v is not None:
            ju.append(v)
    for j in range(len(base)):
        v = _stat(full, base[:j] + base[j + 1:])
        if v is not None:
            jv.append(v)
    u = [(statistics.fmean(ju) - v) for v in ju] + \
        [(statistics.fmean(jv) - v) for v in jv]
    s2 = sum(x * x for x in u)
    a = sum(x ** 3 for x in u) / (6.0 * s2 ** 1.5) if s2 else 0.0
    out = {}
    srt = sorted(draws)
    for label, alpha in (("lo", 0.025), ("hi", 0.975)):
        z = _phi_inv(alpha)
        adj = _phi(z0 + (z0 + z) / (1 - a * (z0 + z)))
        idx = min(int(adj * n), n - 1)
        out[label] = srt[idx]
    out["z0"] = z0
    out["acceleration"] = a
    return out


def block_draws(arm, seed, block_len, resamples=RESAMPLES):
    """Circular block bootstrap of one arm in rep order (seeded)."""
    n = len(arm)
    starts = list(range(n))

    def one(rng):
        out = []
        while len(out) < n:
            s = starts[rng.randrange(n)]
            for k in range(block_len):
                out.append(arm[(s + k) % n])
                if len(out) == n:
                    break
        return out

    rng = random.Random(seed)
    return [one(rng) for _ in range(resamples)]


def block_ci(full, base, block_len, seed=0):
    fb = block_draws(full, seed, block_len)
    bb = block_draws(base, seed + 1000, block_len)
    draws = []
    for ra, rb in zip(fb, bb):
        v = _stat(ra, rb)
        if v is not None:
            draws.append(v)
    return _percentile_ci_from_draws(draws)


def acf(vals, max_lag=10):
    n = len(vals)
    mean = statistics.fmean(vals)
    den = sum((v - mean) ** 2 for v in vals)
    out = []
    if not den:
        return [None] * max_lag
    for h in range(1, max_lag + 1):
        num = sum((vals[i] - mean) * (vals[i + h] - mean)
                  for i in range(n - h))
        out.append(num / den)
    return out


def cusum_split(vals):
    """Location of max |CUSUM| + median-based shift across the split."""
    n = len(vals)
    mean = statistics.fmean(vals)
    s, best, loc = 0.0, -1.0, None
    for i in range(n - 1):
        s += vals[i] - mean
        if abs(s) > best:
            best, loc = abs(s), i + 1
    if loc is None:
        return None
    left, right = vals[:loc], vals[loc:]
    ml = statistics.median(left) if left else None
    mr = statistics.median(right) if right else None
    mall = statistics.median(vals)
    return {"split_index": loc, "n": n,
            "shift_pct_of_median": (100.0 * (mr - ml) / mall) if (ml and mall) else None}


def histogram(vals, nbins=20):
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return {"bins": nbins, "counts": [len(vals)] + [0] * (nbins - 1)}
    w = (hi - lo) / nbins
    counts = [0] * nbins
    for v in vals:
        counts[min(int((v - lo) / w), nbins - 1)] += 1
    return {"lo": lo, "hi": hi, "counts": counts}


def bimodality_coefficient(vals):
    n = len(vals)
    mean = statistics.fmean(vals)
    m2 = sum((v - mean) ** 2 for v in vals) / n
    if not m2:
        return None
    m3 = sum((v - mean) ** 3 for v in vals) / n
    m4 = sum((v - mean) ** 4 for v in vals) / n
    skew = m3 / (m2 ** 1.5)
    kurt = m4 / (m2 ** 2)
    return (skew ** 2 + 1) / kurt if kurt else None


def main() -> int:
    base_rows, ext_rows = XE.load_rows()
    if not ext_rows:
        raise SystemExit("refusing: no DEC-043 observations recorded yet")
    for row in ext_rows:  # read-only integrity guards (mirror canonical)
        if row.get("aqe_enabled"):
            raise SystemExit("refusing: aqe true in %s" % row.get("run_id"))
        if row.get("split") != "validation":
            raise SystemExit("refusing: non-validation row")
        if row.get("authorized_by") != "DEC-043":
            raise SystemExit("refusing: row not DEC-043")
    ids = [r["run_id"] for r in ext_rows]
    if len(ids) != len(set(ids)):
        raise SystemExit("refusing: duplicate run_id")

    stages_done = []
    for stage in EXT.STAGES:
        path = EXT.stage_summary_path(stage["stage"])
        if path.exists():
            stages_done.append(json.loads(path.read_text(encoding="utf-8")))
    if not stages_done:
        raise SystemExit("refusing: no completed stage summary")

    cells = [EXT.STAGE_BY_ID[s["stage"]] for s in stages_done]
    body = {"cells": [], "series": [], "cost": {}, "runtimes": [],
            "bimodality": {}, "eventlog": [], "stabilization": {}}

    for st in cells:
        fam, scale = st["family"], st["scale"]
        cell = "%s|%s" % (fam, scale)
        pooled = {c: XE.samples(base_rows, fam, scale, c)
                  + XE.samples(ext_rows, fam, scale, c) for c in CONDS}
        s_full, s_nosys, s_neith = (pooled["FULL"], pooled["NO-SYSMON"],
                                    pooled["NEITHER"])
        point = AN.overhead(_median(s_full), _median(s_nosys))
        seed_runs = []
        for sd in SEEDS:
            ci = _percentile_ci_from_draws(iid_draws(s_full, s_nosys, sd))
            seed_runs.append({"seed": sd, "ci95_pct": list(ci),
                              "halfwidth_pp": XE.halfwidth(ci),
                              "verdict": AN.adjudicate(point, ci, THRESHOLD_PCT)})
        d0 = iid_draws(s_full, s_nosys, 0)
        bca = bca_ci(s_full, s_nosys, d0, point)
        bca_ci_pair = (bca["lo"], bca["hi"])
        blocks = {}
        for L in BLOCKS:
            ci = block_ci(s_full, s_nosys, L)
            blocks[str(L)] = {"ci95_pct": list(ci),
                              "halfwidth_pp": XE.halfwidth(ci),
                              "verdict": AN.adjudicate(point, ci, THRESHOLD_PCT)}
        elog_point = AN.overhead(_median(s_nosys), _median(s_neith))
        elog_ci = _percentile_ci_from_draws(iid_draws(s_nosys, s_neith, 0))
        body["cells"].append({
            "cell": cell, "n_full": len(s_full), "n_nosys": len(s_nosys),
            "point_estimate_pct": point,
            "seed_sensitivity": seed_runs,
            "bca_seed0": {"ci95_pct": [bca["lo"], bca["hi"]],
                          "halfwidth_pp": XE.halfwidth(bca_ci_pair),
                          "verdict": AN.adjudicate(point, bca_ci_pair, THRESHOLD_PCT),
                          "z0": bca["z0"], "acceleration": bca["acceleration"]},
            "block_bootstrap_seed0": blocks})
        body["eventlog"].append({
            "cell": cell, "n_nosys": len(s_nosys), "n_neith": len(s_neith),
            "point_estimate_pct": elog_point,
            "ci95_pct": list(elog_ci), "halfwidth_pp": XE.halfwidth(elog_ci),
            "verdict": AN.adjudicate(elog_point, elog_ci, THRESHOLD_PCT)})
        for c in CONDS:
            vals = pooled[c]
            body["series"].append({
                "series": "%s|%s" % (cell, c), "n": len(vals),
                "acf_lag1_10": acf(vals),
                "white_noise_band": 1.96 / math.sqrt(len(vals)) if vals else None,
                "cusum_split": cusum_split(vals)})
            if vals:
                body["runtimes"].append({"series": "%s|%s" % (cell, c),
                                        "n": len(vals),
                                        "median_s": statistics.median(vals)})

    f1 = ([v for v in XE.samples(base_rows, "F1_agg", "small", "FULL")]
          + [v for v in XE.samples(ext_rows, "F1_agg", "small", "FULL")])
    body["bimodality"] = {"series": "F1_agg|small|FULL", "n": len(f1),
                          "bimodality_coefficient": bimodality_coefficient(f1),
                          "histogram_20bin": histogram(f1),
                          "cusum_split": cusum_split(f1)}

    uts = sorted(r["recorded_utc"] for r in ext_rows if r.get("recorded_utc"))
    ext_bytes = (EXT.OBS_PATH.stat().st_size if EXT.OBS_PATH.exists() else None)
    body["cost"] = {
        "ext_rows_total": len(ext_rows),
        "ext_rows_usable": sum(1 for r in ext_rows if r.get("usable")),
        "wall_span_start_utc": uts[0] if uts else None,
        "wall_span_end_utc": uts[-1] if uts else None,
        "observations_ext_jsonl_bytes": ext_bytes}

    artifact = json.loads((PROJECT / "results" / "evaluation" /
                           "exp009_ext_analysis.json").read_text(encoding="utf-8"))
    for c in artifact["cells"]:
        seq = [(p["n_per_condition"], p["verdict"])
               for p in c["power_model"]["sysmon_trajectory"]]
        canon, v1, v2 = None, None, None
        for i, (k, v) in enumerate(seq):
            if v2 is None and v == "PASS":
                v2 = k
            if canon is None and all(q == "PASS" for _, q in seq[i:]):
                canon = k
        if len(seq) >= 2 and seq[-1][1] == "PASS" and seq[-2][1] == "PASS":
            v1 = seq[-1][0]
        body["stabilization"][c["cell"]] = {
            "canonical_earliest_stable_pass_n": canon,
            "V1_last_two_pass_n": v1, "V2_first_pass_anywhere_n": v2,
            "verdict_sequence": seq}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(body, indent=1), encoding="utf-8")

    print("R1 seed range pp | block L=5/10/20 pp | verdicts(iid/bca/b5/b10/b20)")
    for c in body["cells"]:
        hw = [s["halfwidth_pp"] for s in c["seed_sensitivity"]]
        b = c["block_bootstrap_seed0"]
        v = [c["seed_sensitivity"][0]["verdict"],
             c["bca_seed0"]["verdict"], b["5"]["verdict"],
             b["10"]["verdict"], b["20"]["verdict"]]
        print("  %-14s seeds[%s] bca=%.2f blk=[%s] %s" % (
            c["cell"], ",".join("%.2f" % h for h in hw),
            c["bca_seed0"]["halfwidth_pp"],
            ",".join("%.2f" % b[k]["halfwidth_pp"] for k in ("5", "10", "20")),
            "/".join(v)))
    print("R2 lag-1 range: %.3f..%.3f over %d series" % (
        min(s["acf_lag1_10"][0] for s in body["series"]),
        max(s["acf_lag1_10"][0] for s in body["series"]), len(body["series"])))
    print("R7 eventlog verdicts: %s" % (
        ",".join("%s=%s" % (e["cell"], e["verdict"]) for e in body["eventlog"])))
    print("wrote %s" % OUT_JSON)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
