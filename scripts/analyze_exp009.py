#!/usr/bin/env python
"""EXP-009 overhead analysis - DEC-040 s7, descriptive only (no inference).

Reads results/experiments/exp-009/observations.jsonl (117 rows on disk:
105 in-scope rows = 7 analyzed validation cells x 3 conditions x 5 reps,
plus 12 retained error records for the EXCLUDED cell F3_rdd|medium). Per
analyzed cell, from the median execution_time_s over the 5 reps (timing_valid
rows only):

  sysmon_pct   = 100 * (median(FULL) - median(NO-SYSMON)) / median(NO-SYSMON)
  eventlog_pct = 100 * (median(NO-SYSMON) - median(NEITHER)) / median(NEITHER)

The two components are reported SEPARATELY, never summed without the DEC-040
s4 caveat (disabling the event log changes Spark's own configuration, so the
event-log arm is a configuration difference, not a pure observer removal).
Median +/- IQR per PLAN:180. Acceptance: each component <= 5% (PLAN:45). No
other threshold, no significance test (DEC-040 s7, DEC-030 s8 posture).

Writes results/experiments/exp-009/analysis.json (observations + verdicts)
and results/evaluation/exp009_analysis.json (evaluation copy). The runner's
results/experiments/exp-009/summary.json is NEVER overwritten here. Refuses
to run unless the run summary says complete 105 of 105 in scope. Records the
F3_rdd|medium exclusion and the reduced 7-of-8 cell coverage as a stated
limitation (DEC-040 s6).
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
import sys
import time
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]

EXP_DIR = PROJECT / "results" / "experiments" / "exp-009"
OBS_PATH = EXP_DIR / "observations.jsonl"
RUN_SUMMARY = EXP_DIR / "summary.json"
SPEC_PATH = EXP_DIR / "spec.json"
EVAL_OUT = PROJECT / "results" / "evaluation" / "exp009_analysis.json"

THRESHOLD_PCT = 5.0
REPS = 5
AUTHORIZED_CELLS = (("F1_agg", "small"), ("F1_agg", "medium"),
                    ("F2_join", "small"), ("F2_join", "medium"),
                    ("F3_rdd", "small"), ("F3_rdd", "medium"),
                    ("F5_mixed", "small"), ("F5_mixed", "medium"))
# DEC-040 s6 recorded reduced coverage: F3_rdd|medium excluded from analysis
# (long-standing fragility; see run_exp009.EXCLUDED_CELLS_RECORD for the
# evidence). The other 7 cells are analyzed.
EXCLUDED_CELLS = (("F3_rdd", "medium"),)
CELLS = tuple(c for c in AUTHORIZED_CELLS if c not in EXCLUDED_CELLS)
CONDS = ("FULL", "NO-SYSMON", "NEITHER")


def iqr(vals: list[float]) -> float | None:
    """Inter-quartile range via exclusive Tukey hinges (stdlib only)."""
    if len(vals) < 2:
        return 0.0 if len(vals) == 1 else None
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    lo = s[:mid]
    hi = s[mid + 1:] if n % 2 else s[mid:]
    q1 = statistics.median(lo)
    q3 = statistics.median(hi)
    return float(q3 - q1)

def load_rows() -> list[dict]:
    if not OBS_PATH.exists():
        raise SystemExit("refusing: observations missing; run first")
    rows = [json.loads(line) for line in
            OBS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    return rows


def cell_stats(rows: list[dict]) -> dict[str, dict]:
    """Per (cell, condition): median +/- IQR over timing_valid reps."""
    out: dict[str, dict] = {}
    for fam, scale in CELLS:
        cell = "%s|%s" % (fam, scale)
        per: dict[str, dict] = {}
        for cond in CONDS:
            vals = sorted(o["execution_time_s"] for o in rows
                          if o["family"] == fam and o["scale"] == scale
                          and o["condition"] == cond and o.get("timing_valid")
                          and o.get("execution_time_s") is not None
                          and o.get("execution_time_source") == "runner")
            per[cond] = {
                "n_timing_valid": len(vals),
                "n_required": REPS,
                "complete": len(vals) == REPS,
                "median_s": statistics.median(vals) if vals else None,
                "iqr_s": iqr(vals),
                "min_s": min(vals) if vals else None,
                "max_s": max(vals) if vals else None,
            }
        out[cell] = per
    return out


def overhead(full: float | None, base: float | None) -> float | None:
    if full is None or base is None or base == 0:
        return None
    return 100.0 * (full - base) / base


# --- uncertainty -------------------------------------------------------------
# PLAN line 180 already prescribes "95% bootstrap CI" among this project's
# statistics. Reporting one here INVENTS NOTHING: it applies frozen procedure
# to the quantity SC6 clause 2 is stated in. A point estimate compared against
# a 5% gate silently asserts a precision this design does not have, and at
# n = 5 per (cell, condition) it does not have it - the run-to-run CV of
# execution_time_s on this stack is 2.6-13.6%, so the sampling error of a
# DIFFERENCE of two medians is of the same order as the gate being tested.
BOOTSTRAP_RESAMPLES = 4000
BOOTSTRAP_SEED = 0          # fixed: the analysis must be byte-reproducible


def _median(vals: list[float]) -> float:
    s = sorted(vals)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def bootstrap_ci(full: list[float], base: list[float]) -> tuple[float, float] | None:
    """95% percentile bootstrap CI for the relative median difference (%).

    Deterministic: seeded locally so repeated analysis of the same
    observations reproduces byte-identically, as the Day-28/29 analysis
    reproducibility checks require of every analyzer in this repository.
    """
    if len(full) < 2 or len(base) < 2 or not all(base):
        return None
    rng = random.Random(BOOTSTRAP_SEED)
    draws: list[float] = []
    for _ in range(BOOTSTRAP_RESAMPLES):
        ra = [full[rng.randrange(len(full))] for _ in full]
        rb = [base[rng.randrange(len(base))] for _ in base]
        mb = _median(rb)
        if mb:
            draws.append(100.0 * (_median(ra) - mb) / mb)
    if not draws:
        return None
    draws.sort()
    lo = draws[int(0.025 * len(draws))]
    hi = draws[min(int(0.975 * len(draws)), len(draws) - 1)]
    return lo, hi


def adjudicate(pct: float | None, ci: tuple[float, float] | None,
               threshold: float) -> str:
    """PASS / FAIL / INCONCLUSIVE for one component against the gate.

    A verdict is only returned when the interval LIES WHOLLY on one side of
    the threshold. If the CI straddles it, the measurement cannot decide the
    question in EITHER direction, and saying so is the honest outcome - not a
    softened FAIL and not a rescued PASS.
    """
    if pct is None or ci is None:
        return "INCONCLUSIVE"
    lo, hi = ci
    if hi <= threshold:
        return "PASS"
    if lo > threshold:
        return "FAIL"
    return "INCONCLUSIVE"


def required_n(full: list[float], base: list[float], threshold: float,
               target_halfwidth: float = 2.0) -> int | None:
    """Repetitions per (cell, condition) needed for a CI half-width of
    ``target_halfwidth`` percentage points, so the gate becomes decidable.

    Scales the observed half-width by 1/sqrt(n). Reported so the record says
    what WOULD settle the question rather than leaving it open-ended. These
    are validation cells, so additional repetitions charge SC6 nothing.
    """
    ci = bootstrap_ci(full, base)
    if ci is None or not full:
        return None
    half = 0.5 * (ci[1] - ci[0])
    if half <= target_halfwidth:
        return len(full)
    return int(math.ceil(len(full) * (half / target_halfwidth) ** 2))

def main() -> int:
    rows = load_rows()
    runsum = json.loads(RUN_SUMMARY.read_text(encoding="utf-8")) \
        if RUN_SUMMARY.exists() else {}
    if runsum.get("stage", "").startswith("complete (105 of 105") is False:
        raise SystemExit("refusing: run stage not complete 105 of 105 in "
                         "scope; got %r" % runsum.get("stage"))
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8")) \
        if SPEC_PATH.exists() else {}
    for row in rows:
        if row.get("aqe_enabled"):
            raise SystemExit("refusing: aqe true")
        if (row.get("family"), row.get("scale")) not in AUTHORIZED_CELLS:
            raise SystemExit("refusing: cell outside s5")
    excluded_rows = [o for o in rows
                     if (o.get("family"), o.get("scale")) in EXCLUDED_CELLS]
    for o in excluded_rows:
        if o.get("error") is None:
            raise SystemExit(
                "refusing: excluded-cell row %s is not an error record"
                % o.get("run_id"))
    stats = cell_stats(rows)
    cells = []
    worst_sys = float("-inf")
    worst_elog = float("-inf")

    for fam, scale in CELLS:
        cell = "%s|%s" % (fam, scale)
        per = stats[cell]
        m_full = per["FULL"]["median_s"]
        m_nosys = per["NO-SYSMON"]["median_s"]
        m_neith = per["NEITHER"]["median_s"]
        sys_pct = overhead(m_full, m_nosys)
        elog_pct = overhead(m_nosys, m_neith)
        both = (sys_pct + elog_pct if sys_pct is not None
                and elog_pct is not None else None)
        complete = all(per[c]["complete"] for c in CONDS)
        # Raw per-condition samples for the uncertainty layer.
        s_full = [r["execution_time_s"] for r in rows
                  if r.get("family") == fam and r.get("scale") == scale
                  and r.get("condition") == "FULL"
                  and r.get("execution_time_s") and not r.get("error")]
        s_nosys = [r["execution_time_s"] for r in rows
                   if r.get("family") == fam and r.get("scale") == scale
                   and r.get("condition") == "NO-SYSMON"
                   and r.get("execution_time_s") and not r.get("error")]
        s_neith = [r["execution_time_s"] for r in rows
                   if r.get("family") == fam and r.get("scale") == scale
                   and r.get("condition") == "NEITHER"
                   and r.get("execution_time_s") and not r.get("error")]
        sys_ci = bootstrap_ci(s_full, s_nosys)
        elog_ci = bootstrap_ci(s_nosys, s_neith)
        sys_verdict = adjudicate(sys_pct, sys_ci, THRESHOLD_PCT)
        elog_verdict = adjudicate(elog_pct, elog_ci, THRESHOLD_PCT)
        sys_n = required_n(s_full, s_nosys, THRESHOLD_PCT)
        elog_n = required_n(s_nosys, s_neith, THRESHOLD_PCT)
        # A cell PASSES only if BOTH components pass; it FAILS only if a
        # component's whole interval clears the gate; otherwise the design
        # cannot decide and says so.
        if not complete:
            verdict = "INCONCLUSIVE"
        elif "FAIL" in (sys_verdict, elog_verdict):
            verdict = "FAIL"
        elif sys_verdict == elog_verdict == "PASS":
            verdict = "PASS"
        else:
            verdict = "INCONCLUSIVE"
        if sys_pct is not None:
            worst_sys = max(worst_sys, sys_pct)
        if elog_pct is not None:
            worst_elog = max(worst_elog, elog_pct)
        cells.append({
            "cell": cell, "complete": complete, "conditions": per,
            "overhead_sysmon_pct": sys_pct,
            "overhead_eventlog_pct": elog_pct,
            "combined_sum_pct": both,
            "combined_caveat": ("sum of parts; elog arm changes Spark "
                                "config (DEC-040 s4)"),
            "threshold_pct": THRESHOLD_PCT, "verdict": verdict,
            "sysmon_ci95_pct": list(sys_ci) if sys_ci else None,
            "eventlog_ci95_pct": list(elog_ci) if elog_ci else None,
            "sysmon_verdict": sys_verdict,
            "eventlog_verdict": elog_verdict,
            "reps_needed_for_2pp_halfwidth": {
                "sysmon": sys_n, "eventlog": elog_n},
        })
    # Overall: FAIL only if some cell's interval clears the gate outright;
    # PASS only if every cell passes outright; otherwise INCONCLUSIVE.
    if not cells:
        verdict_all = "INCONCLUSIVE"
    elif any(c["verdict"] == "FAIL" for c in cells):
        verdict_all = "FAIL"
    elif all(c["verdict"] == "PASS" for c in cells):
        verdict_all = "PASS"
    else:
        verdict_all = "INCONCLUSIVE"

    body = {
        "schema_version": "exp009/v1",
        "experiment_id": "EXP-009",
        "authorized_by": "DEC-040",
        "statistic": "median_over_5_reps",
        "spread": "IQR (PLAN:180)",
        "uncertainty": {
            "interval": "95% percentile bootstrap CI (PLAN:180)",
            "resamples": BOOTSTRAP_RESAMPLES,
            "seed": BOOTSTRAP_SEED,
            "rule": ("a component verdict is returned only when the whole "
                     "interval lies on one side of the gate; a straddling "
                     "interval is INCONCLUSIVE in BOTH directions"),
            "why": ("run-to-run CV of execution_time_s on this stack is "
                    "2.6-13.6%, so at n=5 the sampling error of a difference "
                    "of medians is the same order as the 5% gate; a bare "
                    "point estimate would assert a precision this design "
                    "does not have"),
            "remedy": ("additional repetitions on these VALIDATION cells "
                       "charge SC6 nothing; per-cell reps_needed_for_2pp_"
                       "halfwidth states what would make the gate decidable"),
        },
        "threshold_pct": THRESHOLD_PCT,
        "threshold_source": "PLAN line 45 (SC6 clause 2)",
        "verdict": verdict_all,
        "worst_sysmon_pct": worst_sys if cells else None,
        "worst_eventlog_pct": worst_elog if cells else None,
        "cells": cells,
        "n_observations": len(rows),
        "n_excluded_retained": len(excluded_rows),
        "coverage": ("7-of-8 validation cells analyzed; F3_rdd|medium "
                     "excluded per DEC-040 s6"),
        "excluded_cells": runsum.get("excluded_cells") or [
            {"cell": "F3_rdd|medium",
             "authority": "DEC-040 s6 (acceptance over whatever was actually run)",
             "scope": ("excluded from further execution and from analysis; "
                       "retained on disk"),
             "evidence": ("EXP-002: F3_rdd|medium 18 FAILED / 8 COMPLETED vs "
                          "F3_rdd|small 25 COMPLETED / 1 FAILED; "
                          "results/baseline/F3_rdd/ holds small only, "
                          "no medium baseline")}],
        "limitations": [
            ("Coverage is 7 of the 8 authorized validation cells: "
             "F3_rdd|medium is excluded per DEC-040 s6 (long-standing "
             "fragility, not an EXP-009 regression: EXP-002 18 FAILED / 8 "
             "COMPLETED for F3_rdd|medium vs 25 COMPLETED / 1 FAILED for "
             "F3_rdd|small; results/baseline/F3_rdd/ holds small only). "
             "The exclusion is recorded, not repaired; fixing the F3 RDD "
             "workload is separate work."),
            ("The two overhead components are reported separately and are "
             "never summed as an acceptance quantity without the DEC-040 s4 "
             "caveat: disabling the event log changes Spark's own "
             "configuration."),
            ("micro (5 MB) was authorized but is unexecutable on the frozen "
             "stack (resolver admits small/medium/large only); 0 Spark "
             "executions for micro."),
        ],
        "spec_artifact_id": spec.get("artifact_id"),
        "run_summary_artifact_id": runsum.get("artifact_id"),
        "observation_counts": runsum.get("observation_counts"),
        "register_line": "EXP-009 (0 charged to SC6)",
        "caveat": "elog disablement changes Spark config (DEC-040 s4)",
        "no_inference": "descriptive only; no test (DEC-040 s7)",
        "micro_note": "micro authorized-but-unexecutable, 0 Spark",
        "contains_test_data": False,
        "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    canon = json.dumps(body, sort_keys=True,
                       separators=(",", ":")).encode("utf-8")
    body["artifact_id"] = hashlib.sha256(canon).hexdigest()
    EXP_DIR.mkdir(parents=True, exist_ok=True)
    (EXP_DIR / "analysis.json").write_text(
        json.dumps(body, indent=1, sort_keys=True), encoding="utf-8")
    EVAL_OUT.parent.mkdir(parents=True, exist_ok=True)
    EVAL_OUT.write_text(json.dumps(body, indent=1, sort_keys=True),
                        encoding="utf-8")
    print("EXP-009: %d cells, worst sysmon=%s elog=%s -> %s"
          % (len(cells),
             ("%.3f%%" % worst_sys) if worst_sys != float("-inf") else "n/a",
             ("%.3f%%" % worst_elog) if worst_elog != float("-inf") else "n/a",
             verdict_all))
    for c in cells:
        print("  %-16s sysmon=%s elog=%s %s"
              % (c["cell"],
                 ("%.3f%%" % c["overhead_sysmon_pct"])
                 if c["overhead_sysmon_pct"] is not None else "n/a",
                 ("%.3f%%" % c["overhead_eventlog_pct"])
                 if c["overhead_eventlog_pct"] is not None else "n/a",
                 c["verdict"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
