"""Validate Day-11 architecture candidate doc (structural only).

Checks docs/architecture/ARCHITECTURE_CANDIDATES.md for: candidate A/B/C
sections, eight criteria (K1-K8), comparison matrix, recommendation,
Plan-B discussion, invariants, change control, open questions; and
DECISIONS.md for a DEC-008 architecture-selection entry.

STRUCTURAL ONLY. Exit 0 pass, 1 fail.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOC = REPO / "docs" / "architecture" / "ARCHITECTURE_CANDIDATES.md"
DEC = REPO / "DECISIONS.md"


def main() -> int:
    errors: list[str] = []
    if not DOC.exists():
        print(f"FAIL: {DOC} not found")
        return 1
    t = DOC.read_text(encoding="utf-8")
    for marker in ["## 1. Requirements", "## 2. Candidate A",
                   "## 3. Candidate B", "## 4. Candidate C"]:
        if marker not in t:
            errors.append(f"missing '{marker}'")
    for k in [f"K{i}" for i in range(1, 9)]:
        if k not in t:
            errors.append(f"missing criterion {k}")
    for marker in ["## 6. Candidate Comparison Matrix",
                   "## 7. Experimental Compatibility",
                   "## 8. Plan-B Compatibility",
                   "## 9. Risk Comparison",
                   "## 10. Recommended Architecture",
                   "## 11. Decision Summary",
                   "## 12. Open Questions for Day 12",
                   "Architectural Invariants",
                   "Architecture Change Control",
                   "RECOMMENDED: Candidate C"]:
        if marker not in t:
            errors.append(f"missing '{marker}'")
    if len(t) < 4000:
        errors.append("candidate doc trivially short")
    if not DEC.exists():
        errors.append("DECISIONS.md not found")
    else:
        d = DEC.read_text(encoding="utf-8")
        if "DEC-008" not in d:
            errors.append("DEC-008 entry missing in DECISIONS.md")
        for marker in ["Selected architecture", "Rejected alternatives",
                       "Fallback", "Status"]:
            if marker.lower() not in d.lower():
                errors.append(f"DEC-008 missing '{marker}'")
    empties = re.findall(r"^#+\s+\w+\s*\n\s*(?=#|\Z)", t, flags=re.M)
    if empties:
        errors.append(f"empty sections: {len(empties)}")
    if errors:
        print(f"FAIL: {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("PASS: architecture candidates doc + DEC-008 present and structural")
    print("  NOTE: structural only — not proof of design correctness.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
