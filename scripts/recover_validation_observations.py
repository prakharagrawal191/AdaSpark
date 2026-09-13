#!/usr/bin/env python
"""Recover the per-observation inventory of the validation selection grid.

Named for what it does rather than for the experiment register line: it is a
forensic recovery tool, not an experiment runner, and the Days 25-28 drift
guards that scan scripts/ for premature experiment scripts stay intact.

Day 31 executed 96 real validation runs but persisted only the per-candidate
AGGREGATES in ``results/evaluation/baseline_selection.json``. The individual
observations were never written, which breaks the project's own standard that a
raw record stays auditable (Day-28 audit: "Do not store only a final average").

Spark wrote one event log per execution, and each carries the run identity in its
application name, so the INVENTORY is recoverable at zero Spark cost. This script
rebuilds it and cross-checks it against the frozen selection artifact.

WHAT IS RECOVERED: identity (family, scale, dataset seed, configuration, rep),
Spark application id, event-log path, completion outcome, and the event-log
duration.

WHAT IS **NOT** RECOVERED: the AUTHORITATIVE ``execution_time_s``. That is the
frozen Day-3 runner clock, measured outside the event log, and it was not
persisted per observation. The event-log duration reported here is a DIFFERENT
clock and is labelled ``eventlog_duration_s_NOT_AUTHORITATIVE``. It must never be
substituted for the authoritative timing, compared against T_ref, or used to
re-derive a selection. The medians inside baseline_selection.json remain the only
authoritative aggregates, and this script does not recompute them.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from sparkrl.experiments.spec import split_of                       # noqa: E402
from sparkrl.utils.paths import eventlog_dir                        # noqa: E402

SCHEMA = "validation-observation-inventory/v1"
OUT = PROJECT / "results" / "evaluation" / "validation_observations.json"
APP_RE = re.compile(r"exp003-(?P<fam>f\d-[a-z]+)-(?P<scale>small|medium|large)"
                    r"-s(?P<seed>\d+)-(?P<cfg>g-p\d+-sp\d+)-r(?P<rep>\d+)")
FAMILY = {"f1-agg": "F1_agg", "f2-join": "F2_join", "f3-rdd": "F3_rdd",
          "f4-ski": "F4_ski", "f5-mixed": "F5_mixed"}


def _read_app(path: str) -> dict | None:
    """App-start/end facts from one event log. Streams; never loads it whole."""
    start = end = None
    app_id = app_name = None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"SparkListenerApplicationStart"' in line:
                d = json.loads(line)
                app_id, app_name = d.get("App ID"), d.get("App Name")
                start = d.get("Timestamp")
            elif '"SparkListenerApplicationEnd"' in line:
                end = json.loads(line).get("Timestamp")
    if app_name is None:
        return None
    return {"app_id": app_id, "app_name": app_name, "start": start, "end": end}


def collect() -> list[dict]:
    rows = []
    for path in sorted(glob.glob(os.path.join(str(eventlog_dir()), "*"))):
        if os.path.isdir(path):
            continue
        facts = _read_app(path)
        if not facts or "exp003-" not in (facts["app_name"] or ""):
            continue
        m = APP_RE.search(facts["app_name"])
        if not m:
            continue
        family = FAMILY[m.group("fam")]
        scale, seed = m.group("scale"), int(m.group("seed"))
        dur = None
        if facts["start"] is not None and facts["end"] is not None:
            dur = round((facts["end"] - facts["start"]) / 1000.0, 6)
        rows.append({
            "family": family, "scale": scale, "dataset_seed": seed,
            "split": split_of(family, scale, seed),
            "config_name": m.group("cfg").upper().replace("G-P", "G-p").replace("SP", "sp"),
            "rep": int(m.group("rep")),
            "spark_app_id": facts["app_id"],
            "spark_app_name": facts["app_name"],
            "event_log": os.path.basename(path),
            "completed": facts["end"] is not None,
            "eventlog_duration_s_NOT_AUTHORITATIVE": dur,
        })
    rows.sort(key=lambda r: (r["family"], r["scale"], r["config_name"], r["rep"]))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true", help="persist the inventory")
    args = ap.parse_args()

    rows = collect()
    leaked = sorted({f"{r['family']}/{r['scale']}/seed{r['dataset_seed']}"
                     for r in rows if r["split"] != "validation"})
    sel = json.loads((PROJECT / "results" / "evaluation"
                      / "baseline_selection.json").read_text(encoding="utf-8"))
    counts = sel["observation_counts"]
    incomplete = [r for r in rows if not r["completed"]]

    print("EXP-003 observation inventory, recovered from Spark event logs")
    print("  observations recovered      : %d" % len(rows))
    print("  selection artifact total    : %d  (match=%s)"
          % (counts["total"], len(rows) == counts["total"]))
    print("  distinct cells              : %d"
          % len({(r["family"], r["scale"], r["dataset_seed"]) for r in rows}))
    print("  distinct configurations     : %d" % len({r["config_name"] for r in rows}))
    print("  non-validation observations : %s" % (leaked or "NONE"))
    print("  event logs without app-end  : %d (selection reported %d unusable)"
          % (len(incomplete), counts["unusable_excluded"]))
    for r in incomplete:
        print("     incomplete: %s/%s/seed%d %s"
              % (r["family"], r["scale"], r["dataset_seed"], r["config_name"]))
    print("  AUTHORITATIVE execution_time_s: NOT RECOVERABLE - not persisted per")
    print("    observation; the event-log clock is a different clock and is never")
    print("    substituted. baseline_selection.json holds the only authoritative")
    print("    aggregates and is not recomputed here.")

    if args.write:
        body = {"schema_version": SCHEMA, "observations": rows,
                "recovered_count": len(rows),
                "selection_artifact_id": sel.get("artifact_id"),
                "non_validation_observations": leaked,
                "authoritative_timing_recovered": False,
                "authoritative_timing_note":
                    "execution_time_s is the frozen Day-3 runner clock and was not "
                    "persisted per observation. The event-log duration recorded "
                    "here is a different clock, is explicitly NOT authoritative, "
                    "and must not be compared to T_ref or used to re-derive any "
                    "selection.",
                "no_research_claim":
                    "An inventory of executions. It establishes nothing about "
                    "whether any configuration or strategy outperforms another."}
        canon = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        body["fingerprint"] = hashlib.sha256(canon).hexdigest()
        OUT.parent.mkdir(parents=True, exist_ok=True)
        tmp = OUT.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(body, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(tmp, OUT)
        print("  written: %s (%s)" % (OUT.relative_to(PROJECT), body["fingerprint"][:16]))
    return 0 if not leaked and len(rows) == counts["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
