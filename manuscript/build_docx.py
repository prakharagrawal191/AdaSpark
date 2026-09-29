#!/usr/bin/env python
"""Assemble AdaSpark_CaseStudy_Report.docx from sections/ + diagrams/ (python-docx).

Equations stay as numbered text lines (final formatting converts them to
Equation Editor objects). Figures embedded in plan order.
"""
from pathlib import Path
from docx import Document
from docx.shared import Pt, Inches

HERE = Path(__file__).resolve().parent
SECTIONS = HERE / "sections"
DIAGRAMS = HERE / "diagrams"
OUT = HERE / "AdaSpark_CaseStudy_Report.docx"

ORDER = ["00-exec-summary.md", "01-keywords.md", "02-introduction.md",
         "03-problem.md", "04-background.md", "05-requirements.md",
         "06-architecture.md", "07-execution-layer.md", "08-rl-layer.md",
         "09-scheduling.md", "10-self-tuning.md", "11-explainability.md",
         "12-monitoring.md", "13-governance.md", "14-exp-setup.md",
         "15-metrics.md", "16-results.md", "17-comparative.md",
         "18-trust.md", "19-usecases.md", "20-business.md",
         "21-limitations.md", "22-future.md", "23-conclusion.md",
         "24-references.md", "25-appendix.md"]

# Figure file (by number prefix) -> insert after this section file.
FIG_AFTER = {"01": "02-introduction.md", "02": "02-introduction.md",
             "03": "03-problem.md", "04": "04-background.md",
             "05": "05-requirements.md", "06": "06-architecture.md",
             "07": "06-architecture.md", "08": "07-execution-layer.md",
             "09": "08-rl-layer.md", "10": "08-rl-layer.md",
             "11": "09-scheduling.md", "12": "09-scheduling.md",
             "13": "10-self-tuning.md", "14": "10-self-tuning.md",
             "15": "11-explainability.md", "16": "11-explainability.md",
             "17": "12-monitoring.md", "18": "13-governance.md",
             "19": "14-exp-setup.md", "20": "15-metrics.md",
             "21": "16-results.md", "22": "16-results.md",
             "23": "16-results.md", "24": "17-comparative.md",
             "25": "18-trust.md", "26": "19-usecases.md",
             "27": "19-usecases.md", "28": "20-business.md",
             "29": "21-limitations.md", "30": "22-future.md",
             "31": "22-future.md", "32": "23-conclusion.md"}


def add_table(doc, lines):
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")]
            for ln in lines]
    if len(rows) > 2 and all(set(c) <= set("-: ") for c in rows[1]):
        del rows[1]
    table = doc.add_table(rows=len(rows), cols=len(rows[0]))
    table.style = "Table Grid"
    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            if j < len(table.columns):
                table.cell(i, j).text = cell
    doc.add_paragraph("")


def add_markdown(doc, path):
    lines = path.read_text(encoding="utf-8").splitlines()
    i, tbl = 0, []
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("|"):
            tbl.append(ln)
            i += 1
            continue
        if tbl:
            add_table(doc, tbl)
            tbl = []
        if ln.startswith("## "):
            doc.add_heading(ln[3:], level=2)
        elif ln.startswith("# "):
            doc.add_heading(ln[2:], level=1)
        elif ln.startswith("- ") or ln.startswith("* "):
            doc.add_paragraph(ln[2:], style="List Bullet")
        elif ln.strip():
            doc.add_paragraph(ln.strip())
        i += 1
    if tbl:
        add_table(doc, tbl)


def main():
    doc = Document()
    style = doc.styles["Normal"]
    style.font.size = Pt(11)
    doc.add_heading("Self-Adaptive Big Data Programming Using Reinforcement "
                    "Learning and Spark — Case Study Report", level=0)
    figs = {}
    for p in DIAGRAMS.glob("Fig *.png"):
        figs[p.name[4:6]] = p
    for sec in ORDER:
        add_markdown(doc, SECTIONS / sec)
        for num, after in sorted(FIG_AFTER.items()):
            if after == sec and num in figs:
                doc.add_picture(str(figs[num]), width=Inches(6.0))
                doc.add_paragraph("")
    doc.save(OUT)
    words = sum(len((SECTIONS / s).read_text(encoding="utf-8").split())
                for s in ORDER)
    print("wrote %s (%d section-words, %d figures)" % (OUT, words, len(figs)))


if __name__ == "__main__":
    main()
