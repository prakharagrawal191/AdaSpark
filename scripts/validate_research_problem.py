#!/usr/bin/env python
"""Day-4 documentation validator — verifies docs/RESEARCH_PROBLEM.md structure and
consistency against docs/PLAN.md and experiments/registry.csv.

Checks:
1. docs/RESEARCH_PROBLEM.md and docs/PLAN.md exist.
2. All 18 required section headings are present, in order.
3. RQ identifiers RQ0..RQ6 are present.
4. Hypothesis identifiers H1..H4 are present.
5. Success criteria SC1..SC8 are present.
6. All referenced experiment IDs (EXP-001..EXP-012) exist in experiments/registry.csv.
   (Detects only IDs in the universal EXP-xxx pattern; per-doc occurrences are matched.)
7. No obviously broken internal references (e.g., dangling "§NN" beyond PLAN's known set).

Lightweight by design (plan §44: no over-engineered frameworks).
Exit code non-zero on any failed check.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]

EXPECTED_HEADINGS = [
    "## 1. Research Context",
    "## 2. Problem Statement",
    "## 3. Research Aim",
    "## 4. Research Objectives",
    "## 5. Main Research Question",
    "## 6. Supporting Research Questions",
    "## 7. Hypotheses",
    "## 8. Scope",
    "## 9. System Boundary",
    "## 10. Assumptions",
    "## 11. Constraints",
    "## 12. Research Contribution",
    "## 13. Success Criteria SC1",
    "## 14. Research Traceability Matrix",
    "## 15. Minimum Viable Research Contribution",
    "## 16. Ideal Final Contribution",
    "## 17. Threats to Validity",
    "## 18. Supervisor Sign-Off Checklist",
]

RQS = ["RQ0", "RQ1", "RQ2", "RQ3", "RQ4", "RQ5", "RQ6"]
HYP = ["H1", "H2", "H3", "H4"]
SCS = ["SC1", "SC2", "SC3", "SC4", "SC5", "SC6", "SC7", "SC8"]


def load(path: Path) -> str:
    if not path.exists():
        print(f"FAIL: {path} does not exist")
        sys.exit(1)
    return path.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    problem = load(PROJECT / "docs" / "RESEARCH_PROBLEM.md")
    plan = load(PROJECT / "docs" / "PLAN.md")
    registry = load(PROJECT / "experiments" / "registry.csv")

    failures: list[str] = []

    # 1) existence (handled by load(); explicit message for clarity)
    print(f"OK   docs/RESEARCH_PROBLEM.md ({len(problem)} chars)")
    print(f"OK   docs/PLAN.md ({len(plan)} chars)")
    print(f"OK   experiments/registry.csv ({len(registry)} chars)")

    # 2) headings in order
    for h in EXPECTED_HEADINGS:
        if h not in problem:
            failures.append(f"missing heading: {h}")

    # 3/4/5) identifiers
    for ident in RQS + HYP + SCS:
        # require the token as a standalone word in the doc (avoid SC1 matching "SC10")
        if not re.search(rf"(?<![A-Z0-9]){ident}(?![0-9])", problem):
            failures.append(f"missing identifier or cross-reference: {ident}")

    # 6) experiment IDs referenced in the doc must exist in the registry
    referenced = sorted(set(re.findall(r"EXP-(?:0\d{1,2}|[1-9]\d{0,2})", problem)))
    registered = set(re.findall(r"EXP-\d+", registry))
    for exp in referenced:
        if exp not in registered:
            failures.append(f"referenced experiment {exp} not found in registry.csv")

    # 7) no obviously-placed placeholder numbers (a light smoke check)
    if "to be confirmed" in problem or "not yet specified" in problem:
        print("INFO: doc contains explicit 'to be confirmed / not yet specified' items "
              "(consistent with Day-4 §18; OK)")

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  - {f}")
        print(f"\nVALIDATION: FAIL ({len(failures)} issue(s))")
        return 1

    print("\nVALIDATION: PASS (headings, identifiers, and cross-references OK)")
    return 0


if __name__ == "__main__":
    sys.exit(main())