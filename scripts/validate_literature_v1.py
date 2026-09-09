"""Validate the Day-10 literature v1 freeze (structural only).

Checks matrix v1 header, 25-30 VERIFIED rows, no [TK], unique
IDs/titles/links, A-J minimums, synthesis sections, companion docs
(RESEARCH_GAP, NOVELTY_TIERING with Tier 1/2/3, EVIDENCE_LIMITATIONS,
RQ traceability, M3 audit with PASS), and novelty-claim safety.

STRUCTURAL ONLY — not proof of academic correctness.
Exit 0 on success, 1 on failure.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MATRIX = REPO / "docs" / "LITERATURE_MATRIX.md"
GAP = REPO / "docs" / "research" / "RESEARCH_GAP.md"
TIERING = REPO / "docs" / "research" / "NOVELTY_TIERING.md"
LIMITS = REPO / "docs" / "research" / "LITERATURE_EVIDENCE_LIMITATIONS.md"
TRACE = REPO / "docs" / "research" / "RQ_LITERATURE_TRACEABILITY.md"
M3AUDIT = REPO / "docs" / "research" / "M3_LITERATURE_FREEZE_AUDIT.md"

MIN_ROWS, MAX_ROWS = 25, 30
MIN_CATEGORY_ROWS = {"A": 3, "B": 3, "C": 5, "D": 1, "E": 1,
                     "F": 1, "G": 1, "H": 1, "I": 1, "J": 1}
REQUIRED_SECTIONS = [
    "# Synthesis of Literature A–C",
    "# Synthesis of Literature D–J",
    "# Cross-Domain Synthesis",
    "# Relevance to Frozen Research Problem",
    "# Verification Notes",
    "# References",
]
SELF_CLAIM_RES = [
    re.compile(r"our (rl|approach|method|policy|system) (improves|outperforms|beats|proves|demonstrates)", re.I),
    re.compile(r"we (prove|demonstrate|outperform|improve) ", re.I),
    re.compile(r"(is|was) the first ", re.I),
    re.compile(r"no (prior|existing) work ", re.I),
]


def main() -> int:
    errors: list[str] = []
    if not MATRIX.exists():
        print(f"FAIL: {MATRIX} not found")
        return 1
    content = MATRIX.read_text(encoding="utf-8")
    if "Literature Matrix Version: v1.0" not in content:
        errors.append("Matrix missing v1.0 version header (Day-10 freeze marker)")
    if "Day: 10" not in content or "Verified Sources: 30" not in content:
        errors.append("Matrix v1 header must state Day: 10 and Verified Sources: 30")
    blocks = re.split(r"^### ", content, flags=re.MULTILINE)[1:]
    rows = [b for b in blocks if re.match(r"^[A-J]\d+", b.splitlines()[0].strip())]
    if not (MIN_ROWS <= len(rows) <= MAX_ROWS):
        errors.append(f"Row count {len(rows)} outside [{MIN_ROWS}, {MAX_ROWS}]")
    ids, titles, links, cats = [], [], [], {}
    for b in rows:
        rid = b.splitlines()[0].strip()
        fields = dict(re.findall(r"^\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|$", b, flags=re.M))
        ids.append(rid)
        cat = fields.get("Category", "").strip()
        cats[cat] = cats.get(cat, 0) + 1
        t = fields.get("Paper", "").strip()
        link = fields.get("DOI / Stable Link", "").strip()
        ver = fields.get("Verification", "").strip()
        titles.append(t)
        links.append(link)
        if "[TK]" in ver:
            errors.append(f"Row {rid}: [TK] status remains")
        if not ver.startswith("VERIFIED"):
            errors.append(f"Row {rid}: v1 needs VERIFIED (found '{ver[:40]}')")
        if not link.lower().startswith("http"):
            errors.append(f"Row {rid}: missing http(s) source URL")
    if len(set(ids)) != len(ids):
        errors.append("Duplicate row IDs")
    if len(set(titles)) != len(titles):
        errors.append("Duplicate paper titles")
    if len(set(links)) != len(links):
        errors.append("Duplicate DOI/stable links")
    for cat, minimum in sorted(MIN_CATEGORY_ROWS.items()):
        if cats.get(cat, 0) < minimum:
            errors.append(f"Category {cat}: {cats.get(cat, 0)} < min {minimum}")
    for section in REQUIRED_SECTIONS:
        if section not in content:
            errors.append(f"Missing section '{section}'")
    companions = {str(GAP): ["# Research Gap", "Claim-to-Evidence"],
                  str(TIERING): ["Tier 1", "Tier 2", "Tier 3",
                                 "Requires positive experimental results"],
                  str(LIMITS): ["Abstract/Title-Scoped"],
                  str(TRACE): ["RQ0", "RQ6"],
                  str(M3AUDIT): ["PASS"]}
    for path, markers in companions.items():
        p = Path(path)
        if not p.exists() or p.stat().st_size < 500:
            errors.append(f"Missing or trivial companion doc: {p.name}")
            continue
        text = p.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                errors.append(f"{p.name}: missing marker '{marker}'")
    for path in (GAP, TIERING):
        if path.exists():
            text = path.read_text(encoding="utf-8")
            for rx in SELF_CLAIM_RES:
                m = rx.search(text)
                if m:
                    errors.append(f"{path.name}: unsupported self-claim: '{m.group(0)}'")
    if errors:
        print(f"FAIL: {len(errors)} error(s) in literature v1 freeze:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"PASS: literature v1 freeze — {len(rows)} VERIFIED rows, A–J covered, companions present")
    print(f"  Categories: {dict(sorted(cats.items()))}")
    print("  NOTE: structural validation only — not proof of academic correctness.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
