#!/usr/bin/env python
"""Assemble AdaSpark_CaseStudy_Report.docx inside the official course template.

The official template (manuscript/template/official_template.docx, downloaded from the link in
the manuscript guidelines) is a course cover page plus Index / List of Figures / List of Tables /
Contributions pages, followed by an IEEE-Access-style paper: title and author block, ABSTRACT,
INDEX TERMS, then a two-column body. This builder keeps the cover and front matter, fills the
front-matter tables (page numbers are PAGEREF fields that Word updates on open), replaces the
template's sample paper with sections/*.md, and formats every element by cloning the
template's own paragraphs (headings, body text, equations, captions). Full-width figures and
tables are set in single-column blocks between continuous section breaks, as IEEE layouts do.

Equations: editable Microsoft Equation Editor (OMML) objects converted from equations.json with
Office's MML2OMML.XSL. Requires python-docx and lxml (manuscript toolchain interpreter).
The build fails loudly if any figure, table, caption or equation is missing.
"""
import copy
import json
import os
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from lxml import etree

HERE = Path(__file__).resolve().parent
SECTIONS = HERE / "sections"
DIAGRAMS = HERE / "diagrams"
TEMPLATE = HERE / "template" / "official_template.docx"
OUT = HERE / "AdaSpark_CaseStudy_Report.docx"
XSL = Path(os.environ.get("MML2OMML_XSL",
                          r"C:\Program Files\Microsoft Office\root\Office16\MML2OMML.XSL"))
TITLE = "Self-Adaptive Big Data Programming Using Reinforcement Learning and Spark"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"

BODY = ["02-introduction.md", "03-problem.md", "04-background.md", "05-requirements.md",
        "06-architecture.md", "07-execution-layer.md", "08-rl-layer.md", "09-scheduling.md",
        "10-self-tuning.md", "11-explainability.md", "12-monitoring.md", "13-governance.md",
        "14-exp-setup.md", "15-metrics.md", "16-results.md", "17-comparative.md", "18-trust.md",
        "19-usecases.md", "20-business.md", "21-limitations.md", "22-future.md",
        "23-conclusion.md", "25-appendix.md", "../data_availability.md", "24-references.md"]
FIG_AFTER = {1: "02", 2: "02", 3: "03", 4: "04", 5: "05", 6: "06", 7: "06", 8: "07",
             9: "08", 10: "08", 11: "09", 12: "09", 13: "10", 14: "10", 15: "11",
             16: "11", 17: "12", 18: "13", 19: "14", 20: "15", 21: "16", 22: "16",
             23: "16", 24: "17", 25: "18", 26: "19", 27: "19", 28: "20", 29: "21",
             30: "22", 31: "22", 32: "23"}
# template paragraph indices of the prototypes (verified against the downloaded template)
P_COVER_TITLE, P_TITLE, P_ABSTRACT, P_TERMS, P_SECTION0_END = 1, 89, 95, 96, 98
P_H1, P_BODY, P_H2, P_EQ, P_FIGCAP, P_TABCAP = 99, 100, 107, 125, 133, 149

EQUATION_LINE = re.compile(r"^(?P<body>.*\S)\s+\((?P<n>\d{1,2})\)\s*$")
TABLE_CAPTION = re.compile(r"^##\s+Table\s+(\d+):\s*(.+)$")
INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|(?<![\w*])\*[^*\s][^*]*\*(?![\w*]))")
ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII",
         "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX", "XXI", "XXII"]
# OOXML child order (ECMA-376 CT_PPr / CT_RPr); Word rejects out-of-order properties.
PPR_SEQ = ("pStyle keepNext keepLines pageBreakBefore framePr widowControl numPr "
           "suppressLineNumbers pBdr shd tabs suppressAutoHyphens kinsoku wordWrap overflowPunct "
           "topLinePunct autoSpaceDE autoSpaceDN bidi adjustRightInd snapToGrid spacing ind "
           "contextualSpacing mirrorIndents suppressOverlap jc textDirection textAlignment "
           "textboxTightWrap outlineLvl divId cnfStyle rPr sectPr pPrChange").split()
RPR_SEQ = ("rStyle rFonts b bCs i iCs caps smallCaps strike dstrike outline shadow emboss imprint "
           "noProof snapToGrid vanish webHidden color spacing w kern position sz szCs highlight u "
           "effect bdr shd fitText vertAlign rtl cs em lang eastAsianLayout specVanish oMath").split()


def ordered_insert(parent, el, seq):
    """Replace any same-tag child, then insert el at its schema position."""
    tag = el.tag.split("}")[1]
    for old in parent.findall(el.tag):
        parent.remove(old)
    rank = seq.index(tag)
    for child in parent:
        ctag = child.tag.split("}")[1]
        if ctag in seq and seq.index(ctag) > rank:
            child.addprevious(el)
            return el
    parent.append(el)
    return el


def figure_refs(text):
    """Template rule: in-text figure references use the abbreviation "Fig."."""
    text = re.sub(r"\bFigures (?=\d)", "Figs. ", text)
    return re.sub(r"\bFigure (?=\d)", "Fig. ", text)


class Builder:
    def __init__(self):
        if not XSL.exists():
            sys.exit(f"MML2OMML.XSL not found at {XSL}; set MML2OMML_XSL")
        self.doc = Document(str(TEMPLATE))
        paras = self.doc.paragraphs
        self.proto = {k: copy.deepcopy(paras[i]._p) for k, i in
                      (("h1", P_H1), ("body", P_BODY), ("h2", P_H2), ("eq", P_EQ),
                       ("figcap", P_FIGCAP), ("tabcap", P_TABCAP), ("abstract", P_ABSTRACT))}
        self.xslt = etree.XSLT(etree.parse(str(XSL)))
        self.mathml = {k: v for k, v in json.loads(
            (HERE / "equations.json").read_text(encoding="utf-8")).items() if k.isdigit()}
        body = self.doc.element.body
        kids = list(body)
        sect0_end = paras[P_SECTION0_END]._p
        self.col1_sectpr = copy.deepcopy(sect0_end.find(qn("w:pPr")).find(qn("w:sectPr")))
        type_el = self.col1_sectpr.find(qn("w:type"))
        if type_el is None:
            type_el = OxmlElement("w:type")
            self.col1_sectpr.insert(0, type_el)
        type_el.set(qn("w:val"), "continuous")
        two_col_end = [el for el in kids if el.tag == qn("w:p") and el.find(qn("w:pPr")) is not None
                       and el.find(qn("w:pPr")).find(qn("w:sectPr")) is not None]
        self.anchor = two_col_end[1]               # closes the template's two-column section
        self.col2_sectpr = copy.deepcopy(self.anchor.find(qn("w:pPr")).find(qn("w:sectPr")))
        start = kids.index(sect0_end) + 1
        for el in kids[start:]:                    # drop the template's sample paper body
            if el is not self.anchor and el.tag != qn("w:sectPr"):
                body.remove(el)
        self.bookmark_id = 100
        self.equations, self.figures, self.tables, self.sections = [], [], [], []
        self.in_block = False

    # ---------- primitives ----------
    def _clone(self, key, keep_runs=False):
        p = copy.deepcopy(self.proto[key])
        if not keep_runs:
            for child in list(p):
                if child.tag != qn("w:pPr"):
                    p.remove(child)
        return p

    def _run(self, text, rpr_from=None, bold=False, italic=False, code=False, size=None):
        r = OxmlElement("w:r")
        if rpr_from is not None and rpr_from.find(qn("w:rPr")) is not None:
            rpr = copy.deepcopy(rpr_from.find(qn("w:rPr")))
        else:
            rpr = OxmlElement("w:rPr")
        if bold:
            ordered_insert(rpr, OxmlElement("w:b"), RPR_SEQ)
        if italic:
            ordered_insert(rpr, OxmlElement("w:i"), RPR_SEQ)
        if code:
            fonts = OxmlElement("w:rFonts")
            for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
                fonts.set(qn(a), "Consolas")
            ordered_insert(rpr, fonts, RPR_SEQ)
        if size:
            for tag in ("w:sz", "w:szCs"):
                el = OxmlElement(tag)
                el.set(qn("w:val"), str(size))
                ordered_insert(rpr, el, RPR_SEQ)
        r.append(rpr)
        for i, part in enumerate(text.split("\t")):
            if i:
                r.append(OxmlElement("w:tab"))
            t = OxmlElement("w:t")
            t.set(qn("xml:space"), "preserve")
            t.text = part
            r.append(t)
        return r

    def _inline(self, p, text, size=None, base_run=None):
        for tok in INLINE.split(text.replace("\\|", "|")):
            if not tok:
                continue
            if tok.startswith("**") and tok.endswith("**"):
                p.append(self._run(tok[2:-2], base_run, bold=True, size=size))
            elif tok.startswith("`") and tok.endswith("`"):
                p.append(self._run(tok[1:-1], base_run, code=True, size=size))
            elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
                p.append(self._run(tok[1:-1], base_run, italic=True, size=size))
            else:
                p.append(self._run(tok, base_run, size=size))

    def _put(self, el):
        self.anchor.addprevious(el)

    def _bookmark(self, p, name):
        start, end = OxmlElement("w:bookmarkStart"), OxmlElement("w:bookmarkEnd")
        start.set(qn("w:id"), str(self.bookmark_id))
        start.set(qn("w:name"), name)
        end.set(qn("w:id"), str(self.bookmark_id))
        self.bookmark_id += 1
        ppr = p.find(qn("w:pPr"))
        if ppr is not None:
            ppr.addnext(start)
        else:
            p.insert(0, start)
        p.append(end)

    def _section_break(self, sectpr):
        p = OxmlElement("w:p")
        ppr = OxmlElement("w:pPr")
        ppr.append(copy.deepcopy(sectpr))
        p.append(ppr)
        self._put(p)

    def _open_block(self):
        if not self.in_block:
            self._section_break(self.col2_sectpr)      # end the two-column text before it
            self.in_block = True

    def _close_block(self):
        if self.in_block:
            self._section_break(self.col1_sectpr)      # end the single-column block
            self.in_block = False

    # ---------- elements ----------
    def heading(self, level, text, bookmark=None):
        self._close_block()
        p = self._clone("h1" if level == 1 else "h2")
        proto_run = self.proto["h1" if level == 1 else "h2"].find(qn("w:r"))
        p.append(self._run(text, proto_run))
        if bookmark:
            self._bookmark(p, bookmark)
        self._put(p)

    def paragraph(self, text, size=None, hanging=False):
        self._close_block()
        p = self._clone("body")
        if hanging:
            ind = OxmlElement("w:ind")
            ind.set(qn("w:left"), "360")
            ind.set(qn("w:hanging"), "360")
            ordered_insert(p.find(qn("w:pPr")), ind, PPR_SEQ)
        self._inline(p, figure_refs(text), size=size, base_run=self.proto["body"].find(qn("w:r")))
        self._put(p)

    def equation(self, line):
        m = EQUATION_LINE.match(line.strip())
        if not m or m["n"] not in self.mathml or not re.search(r"[=←]", m["body"]):
            return False
        self._close_block()
        p = self._clone("eq")
        ppr = p.find(qn("w:pPr"))
        if ppr.find(qn("w:ind")) is not None:
            ppr.remove(ppr.find(qn("w:ind")))
        tabs = OxmlElement("w:tabs")
        tab = OxmlElement("w:tab")
        tab.set(qn("w:val"), "right")
        tab.set(qn("w:pos"), "4320")                # right edge of a two-column column
        tabs.append(tab)
        ordered_insert(ppr, tabs, PPR_SEQ)
        omml = self.xslt(etree.fromstring(self.mathml[m["n"]].encode("utf-8"))).getroot()
        p.append(copy.deepcopy(omml))
        p.append(self._run("\t(%s)" % m["n"], self.proto["eq"].find(qn("w:r"))))
        self._put(p)
        self.equations.append(int(m["n"]))
        return True

    def table(self, lines, number=None, title=None):
        self._open_block()
        for text in (("TABLE %d" % number, title) if number else ()):
            cap = self._clone("tabcap")
            cap.append(self._run(text, self.proto["tabcap"].find(qn("w:r"))))
            if text.startswith("TABLE"):
                self._bookmark(cap, "_AdaTab%d" % number)
            self._put(cap)
        rows = [[c.strip() for c in re.split(r"(?<!\\)\|", ln.strip().strip("|"))] for ln in lines]
        if len(rows) > 1 and all(set(c) <= set("-: ") for c in rows[1]):
            del rows[1]
        width = max(len(r) for r in rows)
        t = self.doc.add_table(rows=len(rows), cols=width)
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, row in enumerate(rows):
            for j in range(width):
                cell = t.cell(i, j)
                par = cell.paragraphs[0]._p
                for child in list(par):
                    if child.tag != qn("w:pPr"):
                        par.remove(child)
                self._inline(par, row[j] if j < len(row) else "", size=16)
                if i == 0:
                    for r in par.findall(qn("w:r")):
                        ordered_insert(r.find(qn("w:rPr")), OxmlElement("w:b"), RPR_SEQ)
        self._put(t._tbl)
        spacer = OxmlElement("w:p")
        self._put(spacer)
        if number:
            self.tables.append(number)

    def figure(self, number, path):
        self._open_block()
        par = self.doc.add_paragraph()
        par.alignment = 1
        par.add_run().add_picture(str(path), width=Inches(6.2))
        self._put(par._p)
        cap = self._clone("figcap")
        proto_runs = self.proto["figcap"].findall(qn("w:r"))
        cap.append(self._run("FIGURE %d.\u2003" % number, proto_runs[0]))
        cap.append(self._run(path.stem[7:], proto_runs[-1]))
        ordered_insert(cap.find(qn("w:pPr")), self._jc("center"), PPR_SEQ)
        self._bookmark(cap, "_AdaFig%d" % number)
        self._put(cap)
        self.figures.append(number)

    @staticmethod
    def _jc(val):
        jc = OxmlElement("w:jc")
        jc.set(qn("w:val"), val)
        return jc

    # ---------- section files ----------
    def section_file(self, fn):
        path = (SECTIONS / fn).resolve()
        lines = path.read_text(encoding="utf-8").splitlines()
        tbl, table_cap, sub = [], None, 0
        is_refs = fn.startswith("24-")
        for ln in lines + [""]:
            if ln.startswith("|"):
                tbl.append(ln)
                continue
            if tbl:
                self.table(tbl, *(table_cap or ()))
                tbl, table_cap = [], None
            m = TABLE_CAPTION.match(ln)
            if m:
                table_cap = (int(m[1]), m[2].strip())
            elif ln.startswith("# "):
                title = ln[2:].strip()
                num = re.match(r"^(\d+)\.\s+(.*)$", title)
                label = ("%s.\u2003%s" % (ROMAN[int(num[1])], num[2].upper())) if num else title.upper()
                name = "_AdaSec%d" % (len(self.sections) + 1)
                words = 0 if is_refs else len(path.read_text(encoding="utf-8").split())
                self.sections.append((label.replace("\u2003", " "), name, words))
                self.heading(1, label, name)
                sub = 0
            elif ln.startswith("## "):
                text = re.sub(r"^(\d+\.\d+|[A-Z]\.)\s+", "", ln[3:].strip())
                self.heading(2, "%s.\u2002%s" % (chr(ord("A") + sub), text.upper()))
                sub += 1
            elif ln.startswith(("- ", "* ")):
                self.paragraph("•\u00a0" + ln[2:])
            elif ln.strip() and not self.equation(ln):
                self.paragraph(ln.strip(), size=16 if is_refs else None, hanging=is_refs)

    # ---------- front matter ----------
    def front_matter(self, exec_lines, keywords):
        paras = self.doc.paragraphs
        for r in paras[P_COVER_TITLE].runs:                     # cover: On "<Title>"
            if r.text in ("<", ">"):
                r.text = ""
            elif "Title" in r.text:
                r.text = r.text.replace("Title", TITLE)
        title_p = paras[P_TITLE]._p
        for t in title_p.iter(qn("w:t")):
            t.text = TITLE.upper() if "TITLE OF THE PAPER" in (t.text or "") else t.text
        # ABSTRACT = the Executive Summary and Abstract section; Table 1 follows it
        abs_p = paras[P_ABSTRACT]._p
        runs = abs_p.findall(qn("w:r"))
        for r in runs[1:]:
            abs_p.remove(r)
        body_run = runs[1] if len(runs) > 1 else None
        texts = [l for l in exec_lines if l.strip() and not l.startswith(("#", "|"))]
        self._inline(abs_p, " " + texts[0], base_run=body_run)
        anchor = abs_p
        for text in texts[1:]:
            p = copy.deepcopy(self.proto["abstract"])
            for child in list(p):
                if child.tag != qn("w:pPr"):
                    p.remove(child)
            self._inline(p, text, base_run=body_run)
            anchor.addnext(p)
            anchor = p
        self._bookmark(abs_p, "_AdaSec0")
        cap_lines = [l for l in exec_lines if l.startswith("|")]
        m = next(TABLE_CAPTION.match(l) for l in exec_lines if TABLE_CAPTION.match(l))
        saved, self.anchor = self.anchor, paras[P_TERMS]._p
        self.in_block = True                                   # section 0 is single-column already
        self.table(cap_lines, int(m[1]), m[2].strip())
        self.in_block = False
        self.anchor = saved
        terms_p = paras[P_TERMS]._p
        tr = terms_p.findall(qn("w:r"))
        for r in tr[1:]:
            terms_p.remove(r)
        terms_p.append(self._run(" " + ", ".join(sorted(keywords, key=str.lower)) + ".",
                                 tr[1] if len(tr) > 1 else None))

    def _pageref(self, cell, bookmark):
        par = cell.paragraphs[0]._p
        for child in list(par):
            if child.tag != qn("w:pPr"):
                par.remove(child)
        for kind, text in (("begin", None), ("instr", " PAGEREF %s \\h " % bookmark),
                           ("separate", None), ("text", "–"), ("end", None)):
            r = OxmlElement("w:r")
            if kind == "instr":
                el = OxmlElement("w:instrText")
                el.set(qn("xml:space"), "preserve")
                el.text = text
            elif kind == "text":
                el = OxmlElement("w:t")
                el.text = text
            else:
                el = OxmlElement("w:fldChar")
                el.set(qn("w:fldCharType"), kind)
            r.append(el)
            par.append(r)

    @staticmethod
    def _fit_rows(table, needed):
        while len(table.rows) - 1 < needed:
            table._tbl.append(copy.deepcopy(table.rows[-1]._tr))
        while len(table.rows) - 1 > needed:
            table._tbl.remove(table.rows[-1]._tr)

    def fill_tables(self, segment_words):
        t_index, t_figs, t_tabs, t_contrib, t_total = self.doc.tables[:5]
        entries = [("Executive Summary and Abstract", "_AdaSec0")] + \
                  [(label, name) for label, name, _f in self.sections]
        self._fit_rows(t_index, len(entries))
        for i, (label, name) in enumerate(entries, 1):
            t_index.cell(i, 0).text, t_index.cell(i, 1).text = str(i), label
            self._pageref(t_index.cell(i, 2), name)
        self._fit_rows(t_figs, len(self.figures))
        names = {int(p.name[4:6]): p.stem[7:] for p in DIAGRAMS.glob("Fig *.png")}
        for i, n in enumerate(sorted(self.figures), 1):
            t_figs.cell(i, 0).text, t_figs.cell(i, 1).text = str(n), names[n]
            self._pageref(t_figs.cell(i, 2), "_AdaFig%d" % n)
        self._fit_rows(t_tabs, len(self.tables))
        for i, (n, title) in enumerate(sorted(self.table_titles.items()), 1):
            t_tabs.cell(i, 0).text, t_tabs.cell(i, 1).text = str(n), title
            self._pageref(t_tabs.cell(i, 2), "_AdaTab%d" % n)
        self._fit_rows(t_contrib, len(segment_words))
        for i, (label, words) in enumerate(segment_words, 1):
            t_contrib.cell(i, 0).text, t_contrib.cell(i, 1).text = str(i), label
            t_contrib.cell(i, 2).text, t_contrib.cell(i, 3).text = "", str(words)
        t_total.rows[-1].cells[-1].text = str(sum(w for _l, w in segment_words))


def main():
    b = Builder()
    b.table_titles = {}
    for fn in ["00-exec-summary.md"] + [f for f in BODY if not f.startswith("..")]:
        for ln in (SECTIONS / fn).read_text(encoding="utf-8").splitlines():
            m = TABLE_CAPTION.match(ln)
            if m:
                b.table_titles[int(m[1])] = m[2].strip()
    exec_lines = (SECTIONS / "00-exec-summary.md").read_text(encoding="utf-8").splitlines()
    keywords = [k.strip() for k in (SECTIONS / "01-keywords.md").read_text(encoding="utf-8")
                .splitlines()[-1].split(",") if k.strip()]
    b.front_matter(exec_lines, keywords)
    figs = {int(p.name[4:6]): p for p in DIAGRAMS.glob("Fig *.png")}
    for fn in BODY:
        b.section_file(fn)
        for n in sorted(k for k, v in FIG_AFTER.items() if fn.startswith(v)):
            if n in figs:
                b.figure(n, figs[n])
    b._close_block()
    count = lambda fn: len((SECTIONS / fn).read_text(encoding="utf-8").split())
    labels = [("Executive Summary and Abstract", count("00-exec-summary.md")),
              ("Keywords (Index Terms)", count("01-keywords.md"))] + \
             [(lab, w) for lab, _n, w in b.sections]
    b.fill_tables(labels)
    total = sum(w for _l, w in labels)
    settings = b.doc.settings.element
    upd = OxmlElement("w:updateFields")
    upd.set(qn("w:val"), "true")
    settings.append(upd)
    b.doc.save(OUT)

    problems = []
    if sorted(b.figures) != list(range(1, 33)):
        problems.append(f"figures placed {sorted(b.figures)}")
    if sorted(set(b.equations)) != list(range(1, 14)):
        problems.append(f"equations converted {sorted(set(b.equations))}")
    if sorted(b.tables) != list(range(1, 16)):
        problems.append(f"tables {sorted(b.tables)}")
    n_omml = len(etree.XPath(".//m:oMath", namespaces={"m": M_NS})(b.doc.element))
    def is_code(run):
        fonts = run.find(qn("w:rPr") + "/" + qn("w:rFonts"))
        return fonts is not None and fonts.get(qn("w:ascii")) == "Consolas"
    joined = "".join(t.text or "" for r in b.doc.element.iter(qn("w:r")) if not is_code(r)
                     for t in r.iter(qn("w:t")))
    for leak in ("**", "[@", "<TITLE", "<Title>"):
        if leak in joined:
            problems.append(f"leak {leak!r}")
    print("wrote %s: %d figures, %d tables, %d OMML equations, %d sections, %d words excl. references"
          % (OUT.name, len(b.figures), len(b.tables), n_omml, len(b.sections), total))
    if problems:
        sys.exit("BUILD CHECK FAILED: " + "; ".join(problems))


if __name__ == "__main__":
    main()
