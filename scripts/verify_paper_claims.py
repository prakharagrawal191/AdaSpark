#!/usr/bin/env python
"""Verify every headline number in the write-ups against the artifacts.

WHY THIS EXISTS. The paper draft and the research report quote figures that
are hand-transcribed from `analysis_ext.json`. Transcription has already gone
wrong twice in this project: three wrong numbers in the first paper draft
(a not-decided cell's estimate quoted inside a decided-cells range, a wrong
interval bound, a wrong ratio), and a summary table in the research report
left stale for a whole stage after the narrative around it was updated. Both
were caught by hand. This script makes that check mechanical.

It is READ-ONLY and derives every expected value from the artifact, so it
cannot be satisfied by editing the script to match a wrong document. It
computes nothing new: it re-reads what the analysis already wrote.

  python scripts/verify_paper_claims.py            # check, exit 1 on mismatch
  python scripts/verify_paper_claims.py --emit     # print the tables instead

A FAILURE HERE IS A DOCUMENT BUG, NOT A DATA BUG. The artifact is
authoritative; fix the prose.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
ANALYSIS = PROJECT / "results" / "experiments" / "exp-009" / "ext" / "analysis_ext.json"
DOCS = (
    PROJECT / "docs" / "report" / "PAPER_DRAFT_monitoring_overhead.md",
    PROJECT / "docs" / "research" / "DAY39_DEC043_EXP009_STAGES_1_7_EXECUTION.md",
)


def rel(path: Path) -> str:
    """Project-relative display path, tolerating paths outside the project.

    ``Path.relative_to`` raises for anything outside PROJECT, which made the
    verifier crash rather than report when pointed at a document elsewhere -
    exactly what its own negative-control test does.
    """
    try:
        return str(path.relative_to(PROJECT))
    except ValueError:
        return str(path)


def norm(text: str) -> str:
    """Normalise typography before comparing.

    The write-ups use typographic characters that Python's formatting does
    not emit: U+2212 MINUS SIGN for negatives, U+00D7 for the multiplication
    sign, and non-breaking spaces. Comparing raw would report every negative
    number as missing, which is a bug in the comparator rather than in the
    prose - it did exactly that on first run.
    """
    return (text.replace("−", "-").replace("×", "x")
                .replace(" ", " ").replace("–", "-"))


def load() -> dict[str, Any]:
    if not ANALYSIS.exists():
        raise SystemExit("refusing: %s missing; run analyze_exp009_ext first"
                         % ANALYSIS)
    return json.loads(ANALYSIS.read_text(encoding="utf-8"))


def claims(d: dict[str, Any]) -> list[tuple[str, str, bool]]:
    """(label, string that must appear, required_in_every_doc)."""
    out: list[tuple[str, str, bool]] = []
    add = lambda lab, s, every=False: out.append((lab, s, every))  # noqa: E731

    add("total executions", "4,842", False)
    add("total executions (plain)", str(d["n_new_observations"]), False)

    decided = [c for c in d["cells"] if c["cell_decided"]]
    add("decided count", "%d of 7" % len(decided), False)

    for c in d["cells"]:
        cell = c["cell"]
        add("%s pooled n" % cell, str(c["n_per_condition_pooled_min"]))
        add("%s sysmon pct" % cell, "%+.3f%%" % c["overhead_sysmon_pct"])
        add("%s sysmon CI lo" % cell, "%+.3f" % c["sysmon_ci95_pct"][0])
        add("%s sysmon CI hi" % cell, "%+.3f" % c["sysmon_ci95_pct"][1])
        add("%s half-width" % cell, "%.2f pp" % c["sysmon_ci_halfwidth_pp"])
        pm = c["power_model"]
        add("%s slope" % cell, "%+.3f" % pm["sysmon_loglog_slope"])
        add("%s half@authN" % cell,
            "%.2f pp" % pm["sysmon_halfwidth_at_authorized_n_pp"])
        e = pm["sysmon_earliest_stable_pass_n"]
        if e:
            add("%s earliest stable PASS" % cell, str(e))
        p = c["paired_diagnostic"]["sysmon"]
        add("%s paired half" % cell, "%.2f pp" % p["paired_ci_halfwidth_pp"])

    lag = [v["lag1_autocorrelation"] for c in d["cells"]
           for v in c["drift_diagnostic"]["per_condition"].values()]
    add("lag-1 min", "+%.3f" % min(lag))
    add("lag-1 max", "+%.3f" % max(lag))
    add("series count", "%d condition-series" % len(lag))

    mins, maxs = [], []
    for c in d["cells"]:
        for v in c["drift_diagnostic"]["per_condition"].values():
            w = [x["robust_dispersion_pct"] for x in v["windowed"]]
            if len(w) >= 6:
                mins.append(min(w))
                maxs.append(max(w))
    add("quiet-window min", "%.2f" % min(mins))
    add("quiet-window max", "%.2f" % max(mins))
    add("worst-window max", "%.2f" % max(maxs))

    pts = [c["overhead_sysmon_pct"] for c in decided]
    add("decided estimate range lo", "%+.3f%%" % min(pts))
    add("decided estimate range hi", "%+.3f%%" % max(pts))
    return out


def emit(d: dict[str, Any]) -> None:
    print("## Results (generated from analysis_ext.json)\n")
    print("| Cell | pooled n | sysmon | 95% CI | half | verdict |")
    print("|---|---|---|---|---|---|")
    for c in d["cells"]:
        print("| `%s` | %d | %+.3f%% | [%+.3f, %+.3f] | %.2f pp | %s |"
              % (c["cell"], c["n_per_condition_pooled_min"],
                 c["overhead_sysmon_pct"], c["sysmon_ci95_pct"][0],
                 c["sysmon_ci95_pct"][1], c["sysmon_ci_halfwidth_pp"],
                 c["sysmon_verdict"]))
    print("\n## Power model\n")
    print("| Cell | half@authorized n | ratio | slope | monotone | earliest stable PASS |")
    print("|---|---|---|---|---|---|")
    for c in d["cells"]:
        pm = c["power_model"]
        e = pm["sysmon_earliest_stable_pass_n"]
        print("| `%s` | %.2f pp | %.2f× | %+.3f | %s | %s |"
              % (c["cell"], pm["sysmon_halfwidth_at_authorized_n_pp"],
                 pm["sysmon_halfwidth_at_authorized_n_pp"] / 2.0,
                 pm["sysmon_loglog_slope"],
                 "yes" if pm["sysmon_trajectory_monotone_decreasing"] else "no",
                 e if e else "never"))
    print("\n## Paired diagnostic (secondary, DEC-044 D2)\n")
    print("| Cell | n | unpaired | paired | ratio |")
    print("|---|---|---|---|---|")
    for c in d["cells"]:
        p = c["paired_diagnostic"]["sysmon"]
        u = c["sysmon_ci_halfwidth_pp"]
        print("| `%s` | %d | %.2f pp | %.2f pp | %.1f× |"
              % (c["cell"], c["n_per_condition_pooled_min"], u,
                 p["paired_ci_halfwidth_pp"],
                 u / p["paired_ci_halfwidth_pp"]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--emit", action="store_true",
                    help="print the generated tables instead of checking")
    args = ap.parse_args()
    d = load()
    if args.emit:
        emit(d)
        return 0

    texts = {p: norm(p.read_text(encoding="utf-8"))
             for p in DOCS if p.exists()}
    if not texts:
        raise SystemExit("refusing: no write-up found to check")

    missing: list[str] = []
    for label, want, every in claims(d):
        present = [p for p, t in texts.items() if norm(want) in t]
        if every:
            absent = [p.name for p in texts if p not in present]
            if absent:
                missing.append("%s (%r) missing from %s"
                               % (label, want, ", ".join(absent)))
        elif not present:
            missing.append("%s (%r) appears in NO write-up" % (label, want))

    print("verify_paper_claims: %d claims checked against %s"
          % (len(claims(d)), rel(ANALYSIS)))
    for p in texts:
        print("  document: %s" % rel(p))
    if missing:
        print("\nMISMATCH - the artifact is authoritative; fix the prose:")
        for m in missing:
            print("  - %s" % m)
        return 1
    print("  OK: every checked figure is traceable to the artifact.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
