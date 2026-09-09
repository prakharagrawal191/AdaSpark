# Day-12 freeze validator header (structural only; see body below)
"""Validate Day-12 architecture freeze (structural only)."""
from __future__ import annotations
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FREEZE = REPO / "docs" / "architecture" / "ARCHITECTURE_FREEZE.md"
CONTRACTS = REPO / "docs" / "architecture" / "COMPONENT_CONTRACTS.md"
CHECK = REPO / "docs" / "architecture" / "ARCHITECTURE_CHECKLIST.md"
DEC = REPO / "DECISIONS.md"

COMPS = ["COMP-SPARK-01", "COMP-SPARK-02", "COMP-SPARK-03",
         "COMP-SPARK-04", "COMP-MEAS-05", "COMP-RL-06",
         "COMP-RL-07", "COMP-RL-08", "COMP-RL-09",
         "COMP-RL-10", "COMP-EXP-11", "COMP-EXP-12"]
DATAS = ["SparkConfig", "WorkloadSpec", "WorkloadResult",
         "RuntimeMetrics", "StateVector", "Action", "Reward",
         "EpisodeResult", "ExperimentManifest", "CacheKey",
         "BaselineResult", "EvaluationResult"]


def main() -> int:
    errors: list[str] = []
    if not FREEZE.exists():
        return print("FAIL: ARCHITECTURE_FREEZE.md missing") or 1
    f = FREEZE.read_text(encoding="utf-8")
    for s in ["## 1. Architecture Status", "## 5. Component Inventory",
              "## 6. Component Contracts", "## 7. Data Contracts",
              "## 8. Configuration Contract", "## 9. RL Contract",
              "## 10. Offline Initialization Contract",
              "## 11. Cache Contract", "## 12. Baseline Contract",
              "## 13. AQE Contract",
              "## 14. Training/Validation/Test Boundary",
              "## 15. Failure and Recovery",
              "## 16. Plan-B Architecture",
              "## 17. Experiment Compatibility",
              "## 18. Diagrams", "## 19. Technology Mapping",
              "## 20. Architecture Acceptance Checklist",
              "ARCHITECTURE FROZEN FOR IMPLEMENTATION",
              "Candidate C"]:
        if s not in f:
            errors.append(f"FREEZE missing '{s}'")
    for c in COMPS:
        if c not in f:
            errors.append(f"FREEZE missing {c}")
    if f.count("```mermaid") < 6:
        errors.append("fewer than 6 mermaid diagrams")
    if not CONTRACTS.exists():
        errors.append("COMPONENT_CONTRACTS.md missing")
    else:
        c = CONTRACTS.read_text(encoding="utf-8")
        for d in DATAS + COMPS:
            if d not in c:
                errors.append(f"CONTRACTS missing '{d}'")
    if not CHECK.exists():
        errors.append("ARCHITECTURE_CHECKLIST.md missing")
    d = DEC.read_text(encoding="utf-8") if DEC.exists() else ""
    if "DEC-009" not in d:
        errors.append("DEC-009 missing")
    for m in ["Architecture freeze", "Change-control",
              "ARCHITECTURE FROZEN FOR IMPLEMENTATION"]:
        if m not in d:
            errors.append(f"DEC-009 missing '{m}'")
    blob = f + d
    for pat, label in [(r"RQ[789]|RQ1[0-9]", "RQ"),
                       (r"EXP-0(1[3-9]|2[0-9])", "EXP")]:
        hits = set(re.findall(pat, blob))
        if hits:
            errors.append(f"new {label} IDs: {sorted(hits)}")
    if re.search(r"(?<![A-Z0-9])H[5-9](?![0-9])", blob):
        errors.append("new H IDs found")
    sc_new = [s for s in set(re.findall(r"SC\d+", blob))
              if s not in ("SC1", "SC2", "SC3", "SC4", "SC5", "SC6", "SC7", "SC8")]
    if sc_new:
        errors.append(f"new SC IDs: {sorted(sc_new)}")
    if errors:
        print(f"FAIL: {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("PASS: architecture freeze docs + DEC-009 structural")
    print("  NOTE: structural only — not proof of design correctness.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
