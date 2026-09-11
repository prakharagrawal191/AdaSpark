#!/usr/bin/env python
"""Render EXP-002 audit result sections from the stored gate result (Day 22).

Sections 19 (raw results), 20 (aggregate results) and 21 (PASS/FAIL determination) of
``docs/research/EXP002_CONFIGURATION_SENSITIVITY_AUDIT.md`` are GENERATED from
``results/experiments/exp-002/analysis/gate.json`` and spliced between the
``<!-- GENERATED-RESULTS-BEGIN -->`` / ``<!-- GENERATED-RESULTS-END -->`` markers.

No experimental number is ever typed into the documentation by hand.

Usage:
    python scripts/render_exp002_audit.py            # rewrite the audit section
    python scripts/render_exp002_audit.py --check    # verify it is up to date (CI-style)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SRC = PROJECT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

BEGIN = "<!-- GENERATED-RESULTS-BEGIN -->"
END = "<!-- GENERATED-RESULTS-END -->"

AUDIT = PROJECT / "docs" / "research" / "EXP002_CONFIGURATION_SENSITIVITY_AUDIT.md"
GATE = PROJECT / "results" / "experiments" / "exp-002" / "analysis" / "gate.json"


def _pct(value, digits=1):
    return "n/a" if value is None else f"{value * 100:.{digits}f}%"


def _sec(value, digits=3):
    return "n/a" if value is None else f"{value:.{digits}f}"


def render(report: dict) -> str:
    ex = report["execution"]
    gate = report["gate"]
    crit = gate["criteria"]
    out: list[str] = [BEGIN, ""]

    # ---------------------------------------------------------------- 19
    out.append("## 19. Raw results summary\n")
    out.append("Generated from `results/experiments/exp-002/analysis/gate.json` "
               f"(`{report['schema_version']}`, analysis `{report['analysis_version']}`, "
               f"code `{report.get('code_version')}`).\n")
    out.append("| quantity | value |")
    out.append("|---|---|")
    out.append(f"| planned runs | {ex['planned_runs']} |")
    out.append(f"| run manifests found | {ex['records_found']} |")
    out.append(f"| **valid** observations | **{ex['valid']}** |")
    out.append(f"| invalid / failed observations | {ex['invalid']} |")
    out.append(f"| planned but not executed | {ex['missing']} |")
    out.append(f"| unexpected (not in plan) | {ex['unexpected']} |")
    out.append(f"| spec fingerprint | `{report['spec_fingerprint'][:16]}` |")
    out.append(f"| grid fingerprint | `{report['grid_fingerprint'][:16]}` |")
    out.append(f"| AQE | {'ON' if report['aqe_enabled'] else 'OFF'} |")
    out.append(f"| metric | `{report['metric']}` |")
    out.append("")
    if ex["invalid_breakdown"]:
        out.append(f"Invalid breakdown by status: `{ex['invalid_breakdown']}`\n")

    if ex["invalid_runs"]:
        out.append("### Invalid / failed observations (recorded, never dropped)\n")
        out.append("| run id | status | event log | reason |")
        out.append("|---|---|---|---|")
        for r in ex["invalid_runs"]:
            reason = (r.get("error") or "").replace("|", "/").replace("\n", " ")
            if len(reason) > 160:
                reason = reason[:157] + "..."
            out.append(f"| `{r['run_id']}` | {r['status']} | "
                       f"{r['event_log_status']} | {reason or '-'} |")
        out.append("")
    else:
        out.append("No invalid or failed observations were recorded.\n")

    if ex["missing_run_ids"]:
        shown = ex["missing_run_ids"][:20]
        out.append(f"### Planned runs not executed ({ex['missing']})\n")
        out.append("These are absent from the analysis and are **not** treated as "
                   "results of any kind:\n")
        for run_id in shown:
            out.append(f"- `{run_id}`")
        if ex["missing"] > len(shown):
            out.append(f"- … and {ex['missing'] - len(shown)} more "
                       f"(full list in `gate.json`)")
        out.append("")

    out.append("### T_ref calibration (B0 medians, PLAN §§15/33)\n")
    out.append("Emitted as calibration data only. **No reward is computed anywhere "
               "in this work.**\n")
    out.append("| family \\| scale | T_ref (s) |")
    out.append("|---|---|")
    for key, value in sorted(report["t_ref_calibration"].items()):
        out.append(f"| {key} | {_sec(value)} |")
    out.append("")

    # ---------------------------------------------------------------- 20
    out.append("## 20. Aggregate results\n")
    out.append("Per-panel summary. *Spread* is the relative range of per-configuration "
               "median `execution_time_s` across the 12 varied configurations; *noise* is "
               "the pooled within-configuration CV; *ρ* is the Spearman rank agreement of "
               "the configuration ordering between the two repetitions.\n")
    out.append("| family | scale | complete | valid | invalid | spread (varied) "
               "| spread (incl. B0) | noise CV | ρ | sensitive |")
    out.append("|---|---|---|---|---|---|---|---|---|---|")
    for p in report["panels"]:
        rho = p["rep_rank_agreement_spearman"]
        out.append(
            f"| {p['family']} | {p['scale']} | {'yes' if p['complete'] else '**NO**'} "
            f"| {p['n_valid']} | {p['n_invalid']} "
            f"| {_pct(p['observed_spread'])} "
            f"| {_pct(p['spread']['including_reference']['relative'])} "
            f"| {_pct(p['pooled_within_config_cv'], 2)} "
            f"| {'n/a' if rho is None else f'{rho:+.2f}'} "
            f"| {'**YES**' if p['sensitive'] else 'no'} |")
    out.append("")

    for p in report["panels"]:
        out.append(f"### {p['family']} / {p['scale']}\n")
        if p["n_valid"] == 0:
            out.append("No valid observations.\n")
            for reason in p["reasons"]:
                out.append(f"- {reason}")
            out.append("")
            continue
        out.append(f"B0 median (= T_ref) = **{_sec(p['b0_median_s'])} s**. "
                   f"Fastest varied configuration: "
                   f"`{p['spread']['varied_only']['argmin']}` at "
                   f"{_sec(p['spread']['varied_only']['min_s'])} s; slowest: "
                   f"`{p['spread']['varied_only']['argmax']}` at "
                   f"{_sec(p['spread']['varied_only']['max_s'])} s.\n")
        out.append("| configuration | idx | n | median (s) | mean (s) | SD (s) | CV "
                   "| Δ vs B0 (s) | Δ vs B0 (%) |")
        out.append("|---|---|---|---|---|---|---|---|---|")
        for c in p["configs"]:
            idx = "ref" if c["is_reference"] else str(c["grid_index"])
            cv = "n/a" if c["cv"] is None else f"{c['cv']:.3f}"
            rel = ("n/a" if c["rel_diff_from_b0"] is None
                   else f"{c['rel_diff_from_b0'] * 100:+.1f}%")
            abs_ = ("n/a" if c["abs_diff_from_b0_s"] is None
                    else f"{c['abs_diff_from_b0_s']:+.3f}")
            out.append(f"| `{c['name']}` | {idx} | {c['n_valid']} "
                       f"| {_sec(c['median_s'])} | {_sec(c['mean_s'])} "
                       f"| {_sec(c['std_s'])} | {cv} | {abs_} | {rel} |")
        out.append("")
        per_rep = p.get("per_rep_spread") or {}
        if per_rep:
            parts = [f"rep {k}: {_pct(v['relative'])}" for k, v in sorted(per_rep.items())]
            out.append(f"Per-repetition spread — {'; '.join(parts)}.\n")
        for reason in p["reasons"]:
            out.append(f"- {reason}")
        out.append("")

    # ---------------------------------------------------------------- 21
    out.append("## 21. PASS / FAIL determination\n")
    out.append("Criterion, fixed before measurement (PLAN H1 / SC1 / §33 / R2):\n")
    out.append("```")
    out.append(f"metric                : {crit['metric']} ({crit['statistic']})")
    out.append(f"scope                 : {crit['scope']}")
    out.append(f"min relative spread   : {crit['min_relative_spread']:.2f}")
    out.append(f"noise rule            : {crit['noise_rule']}")
    out.append(f"family rule           : {crit['family_rule']}")
    out.append(f"min families          : {crit['min_families']}")
    out.append(f"complete panel needed : {crit['require_complete_panel']}")
    out.append("```\n")
    out.append("| family | sensitive | sensitive scales | spread by scale |")
    out.append("|---|---|---|---|")
    for family, detail in sorted(gate["families"].items()):
        spreads = "; ".join(f"{s}: {_pct(v)}"
                            for s, v in sorted(detail["spread_by_scale"].items()))
        out.append(f"| {family} | {'**YES**' if detail['sensitive'] else 'no'} "
                   f"| {', '.join(detail['sensitive_scales']) or '-'} | {spreads} |")
    out.append("")
    out.append(f"Families meeting the criterion: **{gate['n_families_sensitive']}** "
               f"(required: {crit['min_families']}).\n")
    out.append(f"### EXP-002 SENSITIVITY GATE: **{gate['result']}**\n")
    for reason in gate["reasons"]:
        out.append(f"- {reason}")
    out.append("")
    out.append("This verdict is a deterministic function of the stored run manifests: "
               "re-running `scripts/analyze_exp002.py` on unchanged inputs reproduces it "
               "byte-for-byte, and `scripts/validate_exp002.py` re-derives and compares "
               "it independently.\n")
    out.append(END)
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render EXP-002 audit result sections")
    ap.add_argument("--gate", default=str(GATE))
    ap.add_argument("--audit", default=str(AUDIT))
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the audit document is not up to date")
    args = ap.parse_args(argv)

    gate_path, audit_path = Path(args.gate), Path(args.audit)
    if not gate_path.is_file():
        print(f"ERROR: {gate_path} not found. Run scripts/analyze_exp002.py first.")
        return 2
    if not audit_path.is_file():
        print(f"ERROR: {audit_path} not found.")
        return 2

    report = json.loads(gate_path.read_text(encoding="utf-8"))
    text = audit_path.read_text(encoding="utf-8")
    if BEGIN not in text or END not in text:
        print(f"ERROR: markers {BEGIN} / {END} not found in {audit_path}")
        return 2

    head, rest = text.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    updated = head + render(report) + tail

    if args.check:
        if updated == text:
            print("audit document is up to date with the stored gate result")
            return 0
        print("ERROR: audit document is STALE relative to gate.json; "
              "re-run scripts/render_exp002_audit.py")
        return 1

    audit_path.write_text(updated, encoding="utf-8")
    print(f"rendered EXP-002 results into {audit_path}")
    print(f"  gate result : {report['gate']['result']}")
    print(f"  valid runs  : {report['execution']['valid']}"
          f"/{report['execution']['planned_runs']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
