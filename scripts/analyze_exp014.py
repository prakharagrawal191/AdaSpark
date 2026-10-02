"""EXP-014 pre-registered analysis (DEC-054 s3) - written BEFORE any EXP-014 data.

Primary (DEC-044 D3, fixed on 2026-09-24 for every future overhead measurement): per cell and
component, the median over repetitions of the per-repetition relative difference, 95%
percentile bootstrap over repetitions (4000 resamples, seed 0), adjudicated by the DEC-042
whole-interval rule against the unchanged 5% gate (docs/PLAN.md line 45). The two components
are reported separately (DEC-040 s4): sysmon = FULL vs NO-SYSMON, eventlog = NO-SYSMON vs
NEITHER. A repetition counts only when all three of its conditions are timing-valid.

Secondary, never deciding: the DEC-040 s7 unpaired statistic (continuity with EXP-009), the
DEC-044 D4 steady-state screen, and agreement with EXP-009's recorded paired estimates.
Writes results/evaluation/exp014_analysis.json (executed=false: an analysis, 0 Spark).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import random
import statistics
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("analyze_exp009", PROJECT / "scripts" / "analyze_exp009.py")
AN = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(AN)

ANALYSIS_VERSION = "exp014-analysis/v1"
GATE_PCT = 5.0                       # docs/PLAN.md line 45, unchanged
COMPONENTS = {"sysmon": ("FULL", "NO-SYSMON"), "eventlog": ("NO-SYSMON", "NEITHER")}
PENALTY_FACTOR = 15.0                # Barrett et al. (OOPSLA 2017): penalty 15 * ln(n)
EXP009_EXT = PROJECT / "results" / "evaluation" / "exp009_ext_analysis.json"


def paired_ci(d: list[float]) -> tuple[float, float] | None:
    """Percentile bootstrap of the median paired difference, AN's seed/resamples/indexing."""
    if len(d) < 2:
        return None
    rng = random.Random(AN.BOOTSTRAP_SEED)
    draws = sorted(AN._median([d[rng.randrange(len(d))] for _ in d])
                   for _ in range(AN.BOOTSTRAP_RESAMPLES))
    return draws[int(0.025 * len(draws))], draws[min(int(0.975 * len(draws)), len(draws) - 1)]


def changepoints(x: list[float]) -> list[int]:
    """Exact optimal partitioning for a change in mean (the optimum PELT computes with
    pruning), Gaussian cost on the series scaled by a robust sigma from first differences,
    penalty 15 * ln(n). Returns segment start indices after the first segment."""
    n = len(x)
    if n < 4:
        return []
    diffs = [abs(b - a) for a, b in zip(x, x[1:])]
    sigma = statistics.median(diffs) / (0.6745 * math.sqrt(2))
    if sigma <= 0:
        return []
    z = [v / sigma for v in x]
    cs, cs2 = [0.0], [0.0]
    for v in z:
        cs.append(cs[-1] + v)
        cs2.append(cs2[-1] + v * v)
    cost = lambda a, b: (cs2[b] - cs2[a]) - (cs[b] - cs[a]) ** 2 / (b - a)
    beta = PENALTY_FACTOR * math.log(n)
    best, last = [-beta] + [math.inf] * n, [0] * (n + 1)
    for t in range(2, n + 1):
        for s in [0] + list(range(2, t - 1)):
            if best[s] < math.inf and t - s >= 2:
                c = best[s] + cost(s, t) + beta
                if c < best[t]:
                    best[t], last[t] = c, s
    out, t = [], n
    while t > 0:
        if last[t] > 0:
            out.append(last[t])
        t = last[t]
    return sorted(out)


def steady_state(series: list[float]) -> dict:
    cps = changepoints([math.log(v) for v in series])
    n = len(series)
    status = ("flat" if not cps else
              "steady" if cps[-1] <= n // 2 else "no-steady-state")
    return {"n": n, "changepoints": cps, "status": status}


def blocks(rows: list[dict]) -> dict[str, dict[int, dict[str, float]]]:
    out: dict[str, dict[int, dict[str, float]]] = {}
    for r in rows:
        if r["timing_valid"] and r["execution_time_s"]:
            out.setdefault("%s|%s" % (r["family"], r["scale"]), {}).setdefault(
                r["rep"], {})[r["condition"]] = float(r["execution_time_s"])
    return out


def analyze(spec: dict, rows: list[dict], obs_sha: str, code_sha: dict) -> dict:
    ref = {c["cell"]: c for c in json.loads(EXP009_EXT.read_text(encoding="utf-8"))["cells"]}
    cells = {}
    for cell, reps in sorted(blocks(rows).items()):
        full_reps = sorted(r for r, conds in reps.items() if len(conds) == 3)
        entry = {"n_complete_blocks": len(full_reps), "components": {}, "steady_state": {}}
        for cond in ("FULL", "NO-SYSMON", "NEITHER"):
            entry["steady_state"][cond] = steady_state([reps[r][cond] for r in full_reps])
        for comp, (a, b) in COMPONENTS.items():
            d = [100.0 * (reps[r][a] - reps[r][b]) / reps[r][b] for r in full_reps]
            point = AN._median(d) if d else None
            ci = paired_ci(d)
            xa, xb = [reps[r][a] for r in full_reps], [reps[r][b] for r in full_reps]
            unpaired = AN.overhead(AN._median(xa), AN._median(xb)) if d else None
            unpaired_ci = AN.bootstrap_ci(xa, xb) if d else None
            ref_point = ref.get(cell, {}).get("paired_diagnostic", {}).get(comp, {}).get(
                "paired_median_pct")
            entry["components"][comp] = {
                "paired_median_pct": point, "paired_ci95_pct": ci,
                "verdict": AN.adjudicate(point, ci, GATE_PCT),
                "unpaired_pct_secondary": unpaired, "unpaired_ci95_secondary": unpaired_ci,
                "unpaired_verdict_secondary": AN.adjudicate(unpaired, unpaired_ci, GATE_PCT),
                "exp009_verdict": ref.get(cell, {}).get(f"{comp}_verdict"),
                "exp009_paired_median_pct": ref_point,
                "exp009_point_inside_fresh_ci": (None if ci is None or ref_point is None
                                                 else ci[0] <= ref_point <= ci[1])}
        cells[cell] = entry

    def verdict_prediction(comp: str) -> str:
        v = [c["components"][comp]["verdict"] for c in cells.values()]
        if len(v) < 7:
            return "UNDECIDABLE"
        n_pass, n_fail = v.count("PASS"), v.count("FAIL")
        return ("AFFIRMED" if n_pass >= 6 and n_fail == 0 else
                "REFUTED" if n_fail >= 1 or n_pass <= 4 else "INCONCLUSIVE")

    inside = [c["components"][k]["exp009_point_inside_fresh_ci"]
              for c in cells.values() for k in COMPONENTS]
    q3 = ("UNDECIDABLE" if len(inside) < 14 or None in inside else
          "AFFIRMED" if sum(inside) >= 12 else "REFUTED" if sum(inside) <= 8 else "INCONCLUSIVE")
    doc = {"analysis": ANALYSIS_VERSION, "experiment_id": "EXP-014",
           "authorized_by": spec["authorized_by"], "executed": False, "spark_executions": 0,
           "spec_artifact_id": spec["artifact_id"], "input_observations_sha256": obs_sha,
           "analysis_code_sha256": code_sha,
           "analysis_code_deviation": {k: v for k, v in code_sha.items()
                                       if spec["code_sha256"].get(k) != v},
           "statistic": "DEC-044 D3 paired median of per-repetition relative differences",
           "gate_pct": GATE_PCT, "bootstrap": {"resamples": AN.BOOTSTRAP_RESAMPLES,
                                               "seed": AN.BOOTSTRAP_SEED},
           "rows": {"total": len(rows), "timing_valid": sum(bool(r["timing_valid"]) for r in rows)},
           "cells": cells,
           "predictions": {
               "Q1_sysmon_overhead_below_5pct_on_6_of_7": verdict_prediction("sysmon"),
               "Q2_eventlog_overhead_below_5pct_on_6_of_7": verdict_prediction("eventlog"),
               "Q3_exp009_paired_estimates_reproduce": q3}}
    doc["artifact_id"] = hashlib.sha256(
        json.dumps(doc, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return doc


def main() -> int:
    exp = PROJECT / "results" / "experiments" / "exp-014"
    spec = json.loads((exp / "spec.json").read_text(encoding="utf-8"))
    obs = exp / "observations.jsonl"
    rows = [json.loads(l) for l in obs.read_text(encoding="utf-8").splitlines() if l.strip()]
    sha = lambda p: hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    code = {r: sha(PROJECT / r) for r in spec["code_sha256"]}
    doc = analyze(spec, rows, sha(obs), code)
    out = PROJECT / "results" / "evaluation" / "exp014_analysis.json"
    out.write_text(json.dumps(doc, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
    for cell, c in doc["cells"].items():
        print("  %-17s n=%-3d sysmon %s  eventlog %s" % (
            cell, c["n_complete_blocks"], c["components"]["sysmon"]["verdict"],
            c["components"]["eventlog"]["verdict"]))
    for k, v in doc["predictions"].items():
        print(f"  {k}: {v}")
    if doc["analysis_code_deviation"]:
        print("  DEVIATION: frozen code differs from spec:", list(doc["analysis_code_deviation"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
