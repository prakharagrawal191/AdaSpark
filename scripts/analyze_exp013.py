"""EXP-013 pre-registered analysis (DEC-053 section 3) - written BEFORE any EXP-013 data.

Reads results/experiments/exp-013/{spec.json, observations.jsonl} and writes
results/evaluation/exp013_analysis.json (executed=false: an analysis, 0 Spark).
The decision rules, thresholds and predictions are fixed in DEC-053; this file
implements them and nothing else. Its sha256 is frozen into spec.json by the first
--run of scripts/run_exp013.py; any later edit is a protocol DEVIATION that the
output discloses (analysis_code_deviation) and that must be reported with both outputs.

Unit of analysis for every decision = the workload instance (cell), exactly as PLAN
section 22 pairs its Wilcoxon test. Per (cell, unit): median of exactly 5 usable
repetitions (DEC-017 item 5); fewer -> INCOMPLETE, never imputed. Only fully executed
stages enter the decisions (no partial-stage selection).
"""
from __future__ import annotations

import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from sparkrl.analysis.inference import (cliffs_delta, geometric_mean_ratio, holm,  # noqa: E402
                                        mann_whitney, wilcoxon_signed_rank)

ANALYSIS_VERSION = "exp013-analysis/v1"
REPS = 5
ALPHA = 0.05
H2_GAIN = 0.10            # PLAN line 41: >= 10% vs Spark defaults
TAU = 0.1189              # EXP-001 worst-cell CV; DEC-018 Decision F noise rule
SC7_BAND = 0.05           # PLAN line 45: re-run within +/-5% median
AA_WITHIN_FRACTION = 0.90
RL_ARMS = ("RL-s0", "RL-s1", "RL-s2")
EXP005_OBS = PROJECT / "results" / "experiments" / "exp-005" / "observations.jsonl"
X10_CELLS = ("F4_ski|medium|s4", "F4_ski|small|s4")
FROZEN_FILES = ("scripts/analyze_exp013.py", "src/sparkrl/analysis/inference.py")


def sha256(path: Path) -> str:
    """LF-normalised digest (DEC-037 s4): CRLF and LF checkouts of the same file agree."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def cell_of(row: dict) -> str:
    return "%s|%s|s%d" % (row["family"], row["scale"], row["seed"])


def complete_stages(spec: dict, rows: list[dict]) -> list[str]:
    have = {r["queue_index"] for r in rows}
    return [s for s in spec["stages"]
            if all(e["queue_index"] in have for e in spec["queue"] if e["stage"] == s)]


def unit_samples(rows: list[dict], stages: list[str]) -> dict[tuple[str, str], list[float]]:
    out: dict[tuple[str, str], list[float]] = {}
    for r in rows:
        if r["stage"] in stages and r["usable"] and r["execution_time_s"] is not None:
            out.setdefault((cell_of(r), r["unit"]), []).append(float(r["execution_time_s"]))
    return out


class Data:
    """Arm-level access through the frozen identity map; None = INCOMPLETE/UNDEFINED."""

    def __init__(self, spec: dict, samples: dict, cells: list[str]):
        self.spec, self.samples, self.cells = spec, samples, cells
        self.cfg = {c: {u["unit"]: u["config_fingerprint"] for u in units}
                    for c, units in spec["units"].items()}

    def same_config(self, cell: str, unit_a: str, unit_b: str) -> bool:
        return self.cfg[cell].get(unit_a) == self.cfg[cell].get(unit_b)

    def unit_of(self, cell: str, arm: str) -> str | None:
        u = self.spec["identity_map"][cell].get(arm)
        return None if u in (None, "UNDEFINED") else u

    def arm(self, cell: str, arm: str) -> list[float] | None:
        unit = self.unit_of(cell, arm)
        vals = self.samples.get((cell, unit)) if unit else None
        return vals if vals is not None and len(vals) == REPS else None

    def pairs(self, a: str, b: str) -> list[tuple[str, list[float], list[float]]]:
        out = []
        for c in self.cells:
            x, y = self.arm(c, a), self.arm(c, b)
            if x is not None and y is not None:
                out.append((c, x, y))
        return out


def per_cell(c: str, x: list[float], y: list[float]) -> dict:
    mx, my = statistics.median(x), statistics.median(y)
    return {"cell": c, "median_x": mx, "median_y": my, "ratio": mx / my,
            "mw_p_x_faster": mann_whitney(x, y, "less")["p"],
            "mw_p_x_slower": mann_whitney(x, y, "greater")["p"],
            "cliffs_delta": cliffs_delta(x, y)}


def comparison(data: Data, a: str, b: str, shift: float = 0.0) -> dict:
    """One-sided exact Wilcoxon across cells on ln(med_a/med_b) - shift (H1: < 0)."""
    cells = [per_cell(c, x, y) for c, x, y in data.pairs(a, b)]
    logs = [math.log(r["ratio"]) for r in cells]
    w = wilcoxon_signed_rank([v - shift for v in logs], "less")
    better = [r["cell"] for r in cells if r["ratio"] <= 1 - TAU and r["mw_p_x_faster"] <= ALPHA]
    worse = [r["cell"] for r in cells if r["ratio"] >= 1 + TAU and r["mw_p_x_slower"] <= ALPHA]
    gain = [r["cell"] for r in cells
            if 1 - r["ratio"] >= H2_GAIN and r["mw_p_x_faster"] <= ALPHA]
    return {"a": a, "b": b, "n_cells": len(cells), "wilcoxon": w,
            "gmr": geometric_mean_ratio(logs), "cells_a_better_outside_noise": better,
            "cells_a_worse_outside_noise": worse, "cells_gain_ge_10pct": gain,
            "per_cell": cells}


def distinct_rl_arms(data: Data) -> dict[str, str]:
    """RL arm -> the first RL arm with an identical unit in every cell (identity on TEST)."""
    rep: dict[str, str] = {}
    for arm in RL_ARMS:
        twin = next((r for r in rep.values() if all(
            data.unit_of(c, arm) == data.unit_of(c, r) for c in data.cells)), None)
        rep[arm] = twin or arm
    return rep


def hypotheses(data: Data) -> dict:
    rep = distinct_rl_arms(data)
    tests: dict[str, dict] = {}
    for arm in sorted(set(rep.values())):
        tests[f"T1|{arm}|B0"] = comparison(data, arm, "B0", math.log(1 - H2_GAIN))
        tests[f"T2|{arm}|B3"] = comparison(data, arm, "B3")
        tests[f"T3|{arm}|B4"] = comparison(data, arm, "B4")
    keys = list(tests)
    adjusted = holm([tests[k]["wilcoxon"]["p"] for k in keys])
    for k, p in zip(keys, adjusted):
        t = tests[k]
        t["holm_p"] = p
        t["decidable"] = t["n_cells"] > 0 and len(keys) * 2.0 ** -t["n_cells"] < ALPHA
        # H3 "better on >= half of test workloads": significant across cells AND counted per cell
        t["superior"] = (t["decidable"] and p < ALPHA and len(t["cells_a_better_outside_noise"])
                         >= math.ceil(t["n_cells"] / 2))
    verdicts = {}
    for arm in RL_ARMS:
        r = rep[arm]
        t1, t2, t3 = tests[f"T1|{r}|B0"], tests[f"T2|{r}|B3"], tests[f"T3|{r}|B4"]

        def h3(t):
            if not t["decidable"]:
                return "UNDECIDABLE"
            # "never significantly worse than" AND "on >= half better than"
            ok = t["superior"] and not t["cells_a_worse_outside_noise"]
            return "ACCEPTED" if ok else "REJECTED"
        h2 = ("UNDECIDABLE" if not t1["decidable"] else
              "ACCEPTED" if t1["holm_p"] < ALPHA and len(t1["cells_gain_ge_10pct"])
              >= math.ceil(t1["n_cells"] / 2) else "REJECTED")
        v3 = {"vs_B3": h3(t2), "vs_B4": h3(t3)}
        both = ("ACCEPTED" if all(v == "ACCEPTED" for v in v3.values()) else
                "UNDECIDABLE" if "UNDECIDABLE" in v3.values() else "REJECTED")
        verdicts[arm] = {"analysed_as": r, "H2": h2, "H3": both, "H3_parts": v3}
    return {"tests": tests, "verdicts": verdicts, "holm_family": keys}


def aa_control(data: Data) -> dict:
    """B4 vs B1 (identical configuration on every TEST cell) + RL vs B1 where identical."""
    def summary(pairs):
        rel = sorted(abs(statistics.median(x) / statistics.median(y) - 1) for _, x, y in pairs)
        if not rel:
            return {"n": 0}
        logs = [math.log(statistics.median(x) / statistics.median(y)) for _, x, y in pairs]
        return {"n": len(rel), "median_abs_gap": statistics.median(rel),
                "p95_abs_gap": rel[min(len(rel) - 1, math.ceil(0.95 * len(rel)) - 1)],
                "max_abs_gap": rel[-1],
                "fraction_within_noise": sum(v <= TAU for v in rel) / len(rel),
                "wilcoxon_two_sided": wilcoxon_signed_rank(logs, "two-sided")}
    same = [(c, x, y) for c, x, y in data.pairs("RL-s0", "B1")
            if data.same_config(c, "RL", "B1")]
    return {"B4_vs_B1": summary(data.pairs("B4", "B1")), "RL_vs_B1_same_config": summary(same)}


def exp005_medians() -> dict[tuple[str, str], float]:
    by: dict[tuple[str, str], list[float]] = {}
    for line in EXP005_OBS.read_text(encoding="utf-8").splitlines():
        o = json.loads(line)
        if o["usable"]:
            by.setdefault((cell_of(o), o["arm"]), []).append(o["execution_time_s"])
    return {k: statistics.median(v) for k, v in by.items() if len(v) == REPS}


def sc7(data: Data) -> dict:
    ref = exp005_medians()
    rows = []
    for (cell, arm), m_ref in sorted(ref.items()):
        if cell in data.cells and (fresh := data.arm(cell, arm)) is not None:
            d = statistics.median(fresh) / m_ref - 1
            rows.append({"cell": cell, "arm": arm, "exp005_median": m_ref,
                         "fresh_median": statistics.median(fresh), "rel_diff": d,
                         "within_5pct": abs(d) <= SC7_BAND})
    return {"rows": rows, "n": len(rows), "n_within": sum(r["within_5pct"] for r in rows)}


def aqe(data: Data) -> dict:
    return {c: per_cell(c, x, y) for c, x, y in data.pairs("B0'", "B0")}


def lag1_acf(vals: list[float]) -> float | None:
    if len(vals) < 3:
        return None
    m = statistics.fmean(vals)
    den = sum((v - m) ** 2 for v in vals)
    return sum((vals[i] - m) * (vals[i + 1] - m) for i in range(len(vals) - 1)) / den if den else None


def drift(rows: list[dict], stages: list[str]) -> dict:
    """Lag-1 ACF of each row's log deviation from its (cell, unit) median, in queue order."""
    use = sorted((r for r in rows if r["stage"] in stages and r["usable"]),
                 key=lambda r: r["queue_index"])
    med: dict[tuple, float] = {}
    for key in {(cell_of(r), r["unit"]) for r in use}:
        med[key] = statistics.median([r["execution_time_s"] for r in use
                                      if (cell_of(r), r["unit"]) == key])
    dev = [math.log(r["execution_time_s"] / med[(cell_of(r), r["unit"])]) for r in use]
    return {"n": len(dev), "lag1_acf": lag1_acf(dev)}


def predictions(data: Data, hyp: dict, aa: dict, sc: dict, aq: dict, probes: dict) -> dict:
    v = hyp["verdicts"]
    rep = {a: v[a]["analysed_as"] for a in RL_ARMS}
    t2 = {a: hyp["tests"][f"T2|{rep[a]}|B3"] for a in RL_ARMS}

    def flag(ok, undecided=False):
        return "UNDECIDABLE" if undecided else ("AFFIRMED" if ok else "REFUTED")
    f4 = [r for r in t2["RL-s0"]["per_cell"] if r["cell"].startswith("F4_ski")]
    same = [r for r in t2["RL-s0"]["per_cell"] if data.same_config(r["cell"], "RL", "B1")]
    f4_slow = [r for r in f4 if r["ratio"] >= 1 + TAU and r["mw_p_x_slower"] <= ALPHA]
    gmr4 = hyp["tests"][f"T3|{rep['RL-s0']}|B4"]["gmr"]
    lo, hi = gmr4["ci95"] or (None, None)
    p4 = ("UNDECIDABLE" if lo is None else "AFFIRMED" if 1 - TAU <= lo and hi <= 1 + TAU
          else "REFUTED" if hi < 1 - TAU or lo > 1 + TAU else "INCONCLUSIVE")
    aa1 = aa["B4_vs_B1"]
    f2l = aq.get("F2_join|large|s3")
    others = [r for c, r in aq.items() if c != "F2_join|large|s3"]
    fast = lambda r: r["ratio"] <= 1 - TAU and r["mw_p_x_faster"] <= ALPHA
    x10 = {(r["cell"], r["arm"]): r["within_5pct"] for r in sc["rows"]
           if r["cell"] in X10_CELLS and r["arm"] in ("B0", "B1")}
    return {
        "P1_H2_accepted_all_RL": flag(all(v[a]["H2"] == "ACCEPTED" for a in RL_ARMS),
                                      any(v[a]["H2"] == "UNDECIDABLE" for a in RL_ARMS)),
        "P2_RL_did_not_beat_static": flag(not any(t2[a]["superior"] for a in RL_ARMS),
                                          not all(t2[a]["decidable"] for a in RL_ARMS)),
        "P3_F4_parallelism_pattern": flag(
            len(f4_slow) >= math.ceil(len(f4) / 2) and
            sum(abs(r["ratio"] - 1) <= TAU for r in same) >= AA_WITHIN_FRACTION * len(same),
            not f4 or not same),
        "P4_RL_competitive_with_random_search": p4,
        "P5_AA_identical_configs_within_noise": flag(
            aa1.get("fraction_within_noise", 0) >= AA_WITHIN_FRACTION and
            aa1["wilcoxon_two_sided"]["p"] >= ALPHA, not aa1.get("n")),
        "P6_F3_large_structural_all_seeds": flag(
            all(p["structural"] for p in probes.values()), not probes),
        "P7_AQE_only_F2_join_large": flag(
            f2l is not None and fast(f2l) and not any(fast(r) for r in others), f2l is None),
        "P8_X10_pattern_medium_reproduces_small_drifts": flag(
            x10.get(("F4_ski|medium|s4", "B0")) is True and
            x10.get(("F4_ski|medium|s4", "B1")) is True and
            (x10.get(("F4_ski|small|s4", "B0")) is False or
             x10.get(("F4_ski|small|s4", "B1")) is False), len(x10) < 4),
    }


def probe_outcomes(spec: dict, rows: list[dict]) -> dict:
    out: dict[str, dict] = {}
    by_index = {r["queue_index"]: r for r in rows}
    for e in spec["queue"]:
        if e["probe"] and e["queue_index"] in by_index:
            r = by_index[e["queue_index"]]
            d = out.setdefault(cell_of(r), {"probe_rows": []})
            d["probe_rows"].append({"unit": r["unit"], "usable": r["usable"],
                                    "error_head": (r["error"] or "")[:160]})
    for d in out.values():
        d["structural"] = (len(d["probe_rows"]) == 2
                           and not any(x["usable"] for x in d["probe_rows"]))
    return out


def analyze(spec: dict, rows: list[dict], obs_sha: str, code_sha: dict) -> dict:
    stages = complete_stages(spec, rows)
    cells = [c["cell"] for c in spec["cells"] if c["stage"] in stages]
    data = Data(spec, unit_samples(rows, stages), cells)
    hyp = hypotheses(data)
    aa = aa_control(data)
    sc = sc7(data)
    aq = aqe(data)
    probes = probe_outcomes(spec, [r for r in rows if r["stage"] in stages])
    deviation = {k: v for k, v in code_sha.items() if spec["code_sha256"].get(k) != v}
    doc = {
        "analysis": ANALYSIS_VERSION, "experiment_id": "EXP-013",
        "authorized_by": spec["authorized_by"], "executed": False, "spark_executions": 0,
        "spec_artifact_id": spec["artifact_id"], "input_observations_sha256": obs_sha,
        "analysis_code_sha256": code_sha, "analysis_code_deviation": deviation,
        "stages_complete": stages, "n_cells_analysed": len(cells),
        "rows": {"total": len(rows), "usable": sum(r["usable"] for r in rows),
                 "not_executed": sum(r.get("event_log_status") == "NOT_EXECUTED" for r in rows)},
        "thresholds": {"alpha": ALPHA, "h2_gain": H2_GAIN, "noise_tau": TAU,
                       "sc7_band": SC7_BAND, "aa_within_fraction": AA_WITHIN_FRACTION},
        "hypotheses": hyp, "aa_control": aa, "sc7_secondary": sc, "aqe_secondary": aq,
        "f3_large_probes": probes, "drift_secondary": drift(rows, stages),
        "cell_medians": {f"{c}|{u}": {"n_usable": len(v), "median": statistics.median(v)}
                         for (c, u), v in sorted(data.samples.items())},
    }
    doc["predictions"] = predictions(data, hyp, aa, sc, aq, probes)
    doc["artifact_id"] = hashlib.sha256(
        json.dumps(doc, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return doc


def main() -> int:
    exp = PROJECT / "results" / "experiments" / "exp-013"
    spec = json.loads((exp / "spec.json").read_text(encoding="utf-8"))
    obs_path = exp / "observations.jsonl"
    rows = [json.loads(l) for l in obs_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    code_sha = {rel: sha256(PROJECT / rel) for rel in FROZEN_FILES}
    doc = analyze(spec, rows, sha256(obs_path), code_sha)
    out = PROJECT / "results" / "evaluation" / "exp013_analysis.json"
    out.write_text(json.dumps(doc, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print("stages complete:", doc["stages_complete"], "cells:", doc["n_cells_analysed"])
    for arm, v in doc["hypotheses"]["verdicts"].items():
        print(f"  {arm}: H2 {v['H2']}  H3 {v['H3']} {v['H3_parts']}")
    for k, v in doc["predictions"].items():
        print(f"  {k}: {v}")
    if doc["analysis_code_deviation"]:
        print("  DEVIATION: analysis code differs from the frozen spec:",
              list(doc["analysis_code_deviation"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
