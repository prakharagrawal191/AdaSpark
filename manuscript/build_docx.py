#!/usr/bin/env python
"""Assemble AdaSpark_CaseStudy_Report.docx from sections/ + diagrams/ + equations.json.

Requires python-docx and lxml (the manuscript toolchain interpreter, not the sparkrl venv) and
Microsoft Office's MML2OMML.XSL, which turns each MathML equation into an editable Equation
Editor (OMML) object. Figures get "Figure N: Title" captions, tables get "Table N: Title"
captions, markdown emphasis becomes Word formatting, and the build fails loudly if any
figure, table, caption or equation is missing from the output.
"""
import copy
import json
import os
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.shared import Inches, Pt
from lxml import etree

HERE = Path(__file__).resolve().parent
SECTIONS = HERE / "sections"
DIAGRAMS = HERE / "diagrams"
OUT = HERE / "AdaSpark_CaseStudy_Report.docx"
XSL = Path(os.environ.get("MML2OMML_XSL",
                          r"C:\Program Files\Microsoft Office\root\Office16\MML2OMML.XSL"))

ORDER = ["00-exec-summary.md", "01-keywords.md", "02-introduction.md",
         "03-problem.md", "04-background.md", "05-requirements.md",
         "06-architecture.md", "07-execution-layer.md", "08-rl-layer.md",
         "09-scheduling.md", "10-self-tuning.md", "11-explainability.md",
         "12-monitoring.md", "13-governance.md", "14-exp-setup.md",
         "15-metrics.md", "16-results.md", "17-comparative.md",
         "18-trust.md", "19-usecases.md", "20-business.md",
         "21-limitations.md", "22-future.md", "23-conclusion.md",
         "data_availability.md", "24-references.md", "25-appendix.md"]

# Figure number -> section file after which it is placed (planning table order).
FIG_AFTER = {1: "02", 2: "02", 3: "03", 4: "04", 5: "05", 6: "06", 7: "06", 8: "07",
             9: "08", 10: "08", 11: "09", 12: "09", 13: "10", 14: "10", 15: "11",
             16: "11", 17: "12", 18: "13", 19: "14", 20: "15", 21: "16", 22: "16",
             23: "16", 24: "17", 25: "18", 26: "19", 27: "19", 28: "20", 29: "21",
             30: "22", 31: "22", 32: "23"}

EQUATION_LINE = re.compile(r"^(?P<body>.*\S)\s+\((?P<n>\d{1,2})\)\s*$")
TABLE_CAPTION = re.compile(r"^##\s+(Table\s+\d+):\s*(.+)$")
INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|(?<![\w*])\*[^*\s][^*]*\*(?![\w*]))")


def add_inline(par, text):
    """Markdown **bold**, *italic* and `code` -> Word runs; escaped pipes unescaped."""
    for tok in INLINE.split(text.replace("\\|", "|")):
        if not tok:
            continue
        if tok.startswith("**") and tok.endswith("**"):
            par.add_run(tok[2:-2]).bold = True
        elif tok.startswith("`") and tok.endswith("`"):
            run = par.add_run(tok[1:-1])
            run.font.name = "Consolas"
            run.font.size = Pt(10)
        elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
            par.add_run(tok[1:-1]).italic = True
        else:
            par.add_run(tok)


def add_table(doc, lines):
    rows = [[c.strip() for c in re.split(r"(?<!\\)\|", ln.strip().strip("|"))] for ln in lines]
    if len(rows) > 1 and all(set(c) <= set("-: ") for c in rows[1]):
        del rows[1]
    width = max(len(r) for r in rows)
    table = doc.add_table(rows=len(rows), cols=width)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j in range(width):
            cell = table.cell(i, j)
            cell.text = ""
            par = cell.paragraphs[0]
            add_inline(par, row[j] if j < len(row) else "")
            for run in par.runs:
                run.font.size = Pt(9)
                if i == 0:
                    run.bold = True
    doc.add_paragraph()


class Equations:
    def __init__(self):
        if not XSL.exists():
            sys.exit(f"MML2OMML.XSL not found at {XSL}; set MML2OMML_XSL")
        self.xslt = etree.XSLT(etree.parse(str(XSL)))
        self.mathml = {k: v for k, v in json.loads(
            (HERE / "equations.json").read_text(encoding="utf-8")).items() if k.isdigit()}
        self.done = []

    def try_add(self, doc, line):
        m = EQUATION_LINE.match(line.strip())
        if not m or m["n"] not in self.mathml or not re.search(r"[=←]", m["body"]):
            return False
        omml = self.xslt(etree.fromstring(self.mathml[m["n"]].encode("utf-8"))).getroot()
        par = doc.add_paragraph()
        stops = par.paragraph_format.tab_stops
        stops.add_tab_stop(Inches(3.25), WD_TAB_ALIGNMENT.CENTER)
        stops.add_tab_stop(Inches(6.5), WD_TAB_ALIGNMENT.RIGHT)
        par.add_run("\t")
        par._p.append(copy.deepcopy(omml))
        par.add_run("\t(%s)" % m["n"])
        self.done.append(int(m["n"]))
        return True


def caption(doc, label, title):
    par = doc.add_paragraph()
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = par.add_run(label + ": ")
    run.bold = True
    par.add_run(title)
    par.paragraph_format.keep_with_next = label.startswith("Table")
    return par


def add_section(doc, path, eqs, captions):
    lines = path.read_text(encoding="utf-8").splitlines()
    tbl = []
    for ln in lines + [""]:
        if ln.startswith("|"):
            tbl.append(ln)
            continue
        if tbl:
            add_table(doc, tbl)
            tbl = []
        m = TABLE_CAPTION.match(ln)
        if m:
            caption(doc, m[1], m[2])
            captions.append(m[1])
        elif ln.startswith("## "):
            doc.add_heading(ln[3:].strip(), level=2)
        elif ln.startswith("# "):
            doc.add_heading(ln[2:].strip(), level=1)
        elif ln.startswith(("- ", "* ")):
            add_inline(doc.add_paragraph(style="List Bullet"), ln[2:])
        elif ln.strip() and not eqs.try_add(doc, ln):
            add_inline(doc.add_paragraph(), ln.strip())


def main():
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    normal.paragraph_format.space_after = Pt(6)
    for s in doc.sections:
        s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Inches(1)
    doc.add_heading("Self-Adaptive Big Data Programming Using Reinforcement Learning and "
                    "Spark — Case Study Report", level=0)
    figs = {int(p.name[4:6]): p for p in DIAGRAMS.glob("Fig *.png")}
    eqs, captions, placed = Equations(), [], []
    for sec in ORDER:
        add_section(doc, SECTIONS / sec if (SECTIONS / sec).exists() else HERE / sec,
                    eqs, captions)
        for n in sorted(k for k, v in FIG_AFTER.items() if sec.startswith(v)):
            if n not in figs:
                continue
            par = doc.add_paragraph()
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            par.add_run().add_picture(str(figs[n]), width=Inches(6.0))
            caption(doc, "Figure %d" % n, figs[n].stem[7:])
            placed.append(n)
    doc.save(OUT)

    n_omml = len(etree.XPath(".//m:oMath", namespaces={
        "m": "http://schemas.openxmlformats.org/officeDocument/2006/math"})(doc.element))
    problems = []
    if sorted(placed) != list(range(1, 33)):
        problems.append(f"figures placed {sorted(placed)}")
    if sorted(set(eqs.done)) != list(range(1, 14)):
        problems.append(f"equations converted {sorted(set(eqs.done))}")
    if sorted(int(c.split()[1]) for c in captions) != list(range(1, 16)):
        problems.append(f"table captions {captions}")
    paragraphs = list(doc.paragraphs) + [p for t in doc.tables for row in t.rows
                                         for cell in row.cells for p in cell.paragraphs]
    prose = "\n".join(r.text for p in paragraphs for r in p.runs if r.font.name != "Consolas")
    for leak in ("**", "`", "[@"):
        if leak in prose:
            problems.append(f"markdown leak {leak!r}")
    words = sum(len((SECTIONS / s).read_text(encoding="utf-8").split())
                for s in ORDER if (SECTIONS / s).exists() and s != "24-references.md")
    print("wrote %s: %d figures, %d tables, %d OMML equations, %d words excl. references"
          % (OUT.name, len(placed), len(doc.tables), n_omml, words))
    if problems:
        sys.exit("BUILD CHECK FAILED: " + "; ".join(problems))


if __name__ == "__main__":
    main()
