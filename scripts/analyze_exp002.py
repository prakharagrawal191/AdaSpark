#!/usr/bin/env python
"""EXP-002 analysis + sensitivity-gate evaluation (Day 22).

Reads ONLY stored run manifests. Recomputes the configuration-level summaries, the
B0-relative differences, the repeatability measures and the pre-registered gate, then
emits both a machine-readable result and a human-readable summary:

    results/experiments/exp-002/analysis/gate.json
    results/experiments/exp-002/analysis/summary.md

The gate criterion comes from the pre-registered spec (experiments/exp002.yaml) and is
never adjusted here. Re-running this script on unchanged inputs reproduces an identical
gate result.

An existing gate.json is NEVER silently overwritten with a different verdict: use
--force to replace one, which also archives the previous file alongside it.

Usage:
    python scripts/analyze_exp002.py
    python scripts/analyze_exp002.py --force
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SRC = PROJECT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sparkrl.analysis.exp002 import (build_report, render_summary,  # noqa: E402
                                     report_json,)
from sparkrl.experiments.runner import code_version, load_records  # noqa: E402
from sparkrl.experiments.spec import ExperimentSpec  # noqa: E402

DEFAULT_SPEC = PROJECT / "experiments" / "exp002.yaml"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="EXP-002 analysis and sensitivity gate")
    ap.add_argument("--spec", default=str(DEFAULT_SPEC))
    ap.add_argument("--out", default=None,
                    help="analysis output directory (default <result_root>/analysis)")
    ap.add_argument("--force", action="store_true",
                    help="replace an existing gate.json (the old one is archived)")
    ap.add_argument("--print-only", action="store_true",
                    help="print the summary without writing any file")
    args = ap.parse_args(argv)

    spec = ExperimentSpec.from_yaml(args.spec)
    result_root = PROJECT / spec.result_root
    records = load_records(result_root)
    if not records:
        print(f"ERROR: no EXP-002 run records found under {result_root / 'runs'}. "
              f"Run scripts/run_exp002.py first.")
        return 2

    report = build_report(records, spec,
                          generated_utc=datetime.now(timezone.utc).isoformat(),
                          code_version=code_version())
    summary = render_summary(report)
    print(summary)

    if args.print_only:
        return 0

    out_dir = Path(args.out) if args.out else result_root / "analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    gate_path = out_dir / "gate.json"

    if gate_path.exists() and not args.force:
        try:
            previous = json.loads(gate_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            previous = None
        prev_result = (previous or {}).get("gate", {}).get("result")
        new_result = report["gate"]["result"]
        if previous is not None and prev_result == new_result:
            print(f"\ngate.json already exists with the same verdict "
                  f"({prev_result}); leaving it untouched. Use --force to rewrite.")
            return 0
        print(f"\nERROR: {gate_path} already exists with verdict {prev_result!r} but the "
              f"recomputed verdict is {new_result!r}. Refusing to overwrite a stored "
              f"gate result silently. Inspect the difference, then re-run with --force "
              f"if replacing it is correct.")
        return 3

    if gate_path.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive = out_dir / f"gate.superseded-{stamp}.json"
        archive.write_text(gate_path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"\narchived previous gate result -> {archive}")

    gate_path.write_text(report_json(report), encoding="utf-8")
    (out_dir / "summary.md").write_text(summary, encoding="utf-8")
    print(f"\nwrote {gate_path}")
    print(f"wrote {out_dir / 'summary.md'}")
    print(f"\nEXP-002 SENSITIVITY GATE: {report['gate']['result']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
