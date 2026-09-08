"""Validate docs/LITERATURE_MATRIX.md structural completeness.

Checks:
- file exists
- row count within the verified-foundation window (14–30 rows; Day-10 target 25–30)
- unique row IDs in the A/B/C numbering scheme
- no duplicate paper titles
- no duplicate DOI/stable-link values
- every row has all required fields (incl. Verification status)
- Verification is present, is not [TK], and starts with VERIFIED or EXCLUDED
- VERIFIED rows must carry a source URL in 'DOI / Stable Link'
- category is A, B, or C
- synthesis, RQ-relevance, verification-notes, and references sections present

NOTE: This validator is STRUCTURAL ONLY. A "VERIFIED" string in the file is not
proof of academic authenticity; human/source inspection remains the verification
step (see docs/research/LITERATURE_VERIFICATION_LOG.md).

Exit 0 on success, 1 on failure.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MATRIX = REPO / "docs" / "LITERATURE_MATRIX.md"

REQUIRED_FIELDS = [
    "ID",
    "Category",
    "Paper",
    "Authors",
    "Year",
    "Venue",
    "DOI / Stable Link",
    "Research Problem",
    "Method",
    "Context",
    "Optimization Target",
    "Parameters / Knobs",
    "Dataset / Workload",
    "Evaluation Metrics",
    "Main Verified Finding",
    "Limitation",
    "Relevance",
    "Research Gap",
    "Verification",
]

VALID_CATEGORIES = {"A", "B", "C"}

MIN_ROWS = 14  # verified Day-6 foundation (16 rows currently)
MAX_ROWS = 30  # upper bound of the Day-10 target range (25–30 verified rows)
MIN_CATEGORY_ROWS = {"A": 3, "B": 3, "C": 5}
REQUIRED_SECTIONS = [
    "# Synthesis of Literature A–C",
    "# Relevance to Frozen Research Problem",
    "# Verification Notes",
    "# References",
]


def read_matrix() -> str:
    if not MATRIX.exists():
        print(f"FAIL: {MATRIX} not found")
        sys.exit(1)
    return MATRIX.read_text(encoding="utf-8")


def find_rows(content: str) -> list[dict[str, str]]:
    """Parse rows delimited by ### A1, ### B1, etc."""
    rows: list[dict[str, str]] = []
    blocks = re.split(r"^### ", content, flags=re.MULTILINE)
    for block in blocks[1:]:
        lines = block.splitlines()
        header = lines[0].strip()
        row_id = header.split("\n")[0].strip()
        if not re.match(r"^[ABC]\d+$", row_id):
            continue
        fields: dict[str, str] = {}
        for line in lines[1:]:
            m = re.match(r"^\|\s*([^|]+?)\s*\|\s*(.*?)\s*\|$", line)
            if m:
                key = m.group(1).strip()
                val = m.group(2).strip()
                fields[key] = val
        fields["_id"] = row_id
        rows.append(fields)
    return rows


def main() -> int:
    content = read_matrix()
    rows = find_rows(content)

    errors: list[str] = []

    if not (MIN_ROWS <= len(rows) <= MAX_ROWS):
        errors.append(
            f"Row count {len(rows)} outside required window [{MIN_ROWS}, {MAX_ROWS}] "
            f"(Day-10 target: 25–30 verified rows)"
        )

    ids = {r["_id"] for r in rows}
    if len(ids) != len(rows):
        errors.append("Duplicate row IDs found")

    cat_counts: dict[str, int] = {}
    for row in rows:
        cat = row.get("Category", "").strip()
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    for cat, minimum in sorted(MIN_CATEGORY_ROWS.items()):
        found = cat_counts.get(cat, 0)
        if found < minimum:
            errors.append(f"Category {cat}: expected at least {minimum} rows, found {found}")
    unexpected_cats = set(cat_counts) - set(MIN_CATEGORY_ROWS)
    if unexpected_cats:
        errors.append(f"Unexpected categories: {sorted(unexpected_cats)}")

    titles: list[str] = []
    links: list[str] = []
    for row in rows:
        rid = row["_id"]
        for field in REQUIRED_FIELDS:
            if field not in row or not row[field].strip():
                errors.append(f"Row {rid}: missing or empty field '{field}'")
        cat = row.get("Category", "").strip()
        if cat not in VALID_CATEGORIES:
            errors.append(f"Row {rid}: invalid category '{cat}'")
        title = row.get("Paper", "").strip()
        if title in titles:
            errors.append(f"Row {rid}: duplicate paper title '{title}'")
        titles.append(title)

        verification = row.get("Verification", "").strip()
        if "[TK]" in verification:
            errors.append(f"Row {rid}: Verification still marked [TK] (unverified)")
        elif not (verification.startswith("VERIFIED") or verification.startswith("EXCLUDED")):
            errors.append(
                f"Row {rid}: Verification must start with 'VERIFIED' or 'EXCLUDED' "
                f"(found: '{verification[:60]}')"
            )

        link = row.get("DOI / Stable Link", "").strip()
        if link in links:
            errors.append(f"Row {rid}: duplicate DOI/stable link '{link}'")
        links.append(link)
        if verification.startswith("VERIFIED") and not link.lower().startswith("http"):
            errors.append(
                f"Row {rid}: VERIFIED row must include a source URL in 'DOI / Stable Link'"
            )

    for section in REQUIRED_SECTIONS:
        if section not in content:
            errors.append(f"Missing section '{section}'")

    if errors:
        print(f"FAIL: {len(errors)} error(s) in {MATRIX.name}:")
        for e in errors:
            print(f"  - {e}")
        return 1

    verified = sum(1 for r in rows if r.get("Verification", "").startswith("VERIFIED"))
    excluded = sum(1 for r in rows if r.get("Verification", "").startswith("EXCLUDED"))
    print(f"PASS: {MATRIX.name} — {len(rows)} rows, all fields present, categories valid, sections present")
    print(f"  Rows: {', '.join(sorted(ids))}")
    print(f"  Categories: {dict(sorted(cat_counts.items()))}")
    print(f"  Verification: {verified} VERIFIED, {excluded} EXCLUDED")
    print(f"  Progress toward Day-10 target (25-30 verified rows): {verified}/30")
    print("  NOTE: structural validation only — a 'VERIFIED' string is not proof of")
    print("  authenticity; human/source inspection is the verification step.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
