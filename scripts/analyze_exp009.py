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
        verdict = ("PASS" if complete and sys_pct is not None
                   and elog_pct is not None
                   and sys_pct <= THRESHOLD_PCT
                   and elog_pct <= THRESHOLD_PCT else "FAIL")
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
        })
    verdict_all = "PASS" if cells and all(
        c["verdict"] == "PASS" for c in cells) else "FAIL"

    body = {
        "schema_version": "exp009/v1",
        "experiment_id": "EXP-009",
        "authorized_by": "DEC-040",
        "statistic": "median_over_5_reps",
        "spread": "IQR (PLAN:180)",
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
