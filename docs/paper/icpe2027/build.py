#!/usr/bin/env python
"""Build the ICPE 2027 submission PDF and check it against the page limit.

  python docs/paper/icpe2027/build.py            # figures + PDF + checks
  python docs/paper/icpe2027/build.py --no-figs  # reuse figures/*.pdf

1. Converts the committed SVG figures (docs/figures/) to vector PDFs in
   figures/, sized exactly to each SVG, with Microsoft Edge's headless
   print-to-PDF (no extra installs on Windows).
2. Runs pdflatex, bibtex, pdflatex, pdflatex into build/ (ignored by Git).
3. Reports the page on which the body ends (label `body-end`, placed just
   before the references) against ICPE's 10-page limit, which excludes
   references and appendices; the total page count; and every unresolved
   \\TODO in main.tex.
4. IN-PAGE CHECK. Extracts the text of the built PDF (xpdf's pdftotext, which
   ships with Git for Windows) and requires every claim the .tex makes - as
   derived from the analysis artifact by scripts/verify_paper_claims.py - to
   appear in the rendered pages too. A correct .tex is not a correct PDF: a
   table column can run off the page and a caption can be lost in a float, and
   the artifact-to-.tex checker cannot see either. Needs no extra installs; if
   pdftotext is absent the check says so instead of passing quietly.
Exit 1 if the body is over the limit, the build fails, a claim the .tex makes
is missing from the rendered pages, or a TODO remains (use --allow-todo while
drafting).

TeX: a user-level TinyTeX (docs/research/PAPER_ICPE2027_PLAN.md, P6).
0 Spark executions; reads docs/figures/*.svg and writes only inside this folder.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
BUILD = HERE / "build"
FIGURES = HERE / "figures"
SVGS = ("exp009_ci_halfwidth_vs_reps.svg", "exp009_regime_structure.svg")
PAGE_LIMIT = 10
TEXBIN = Path(os.environ.get("APPDATA", "")) / "TinyTeX" / "bin" / "windows"
EDGE = next((p for p in (
    Path(os.environ.get("ProgramFiles(x86)", "")) / "Microsoft/Edge/Application/msedge.exe",
    Path(os.environ.get("ProgramFiles", "")) / "Microsoft/Edge/Application/msedge.exe")
    if p.exists()), None)


def tool(name: str) -> str:
    exe = TEXBIN / (name + ".exe")
    return str(exe) if exe.exists() else name


def svg_to_pdf(svg: Path, pdf: Path) -> None:
    text = svg.read_text(encoding="utf-8")
    m = re.search(r'<svg[^>]*\bwidth="(\d+)"[^>]*\bheight="(\d+)"', text)
    if not m:
        raise SystemExit("no width/height on the root <svg> of %s" % svg.name)
    w, h = m.groups()
    with tempfile.TemporaryDirectory(prefix="icpe-fig-") as tmp:
        page = Path(tmp) / "page.html"
        page.write_text(
            "<!doctype html><html><head><style>@page{size:%spx %spx;margin:0}"
            "html,body{margin:0;padding:0}</style></head><body>"
            '<img src="%s" style="display:block;width:%spx;height:%spx">'
            "</body></html>" % (w, h, svg.as_uri(), w, h), encoding="utf-8")
        subprocess.run([str(EDGE), "--headless=new", "--disable-gpu",
                        "--no-pdf-header-footer", "--user-data-dir=" + tmp + "\\profile",
                        "--print-to-pdf=" + str(pdf), page.as_uri()],
                       check=True, capture_output=True, timeout=120)
    if not pdf.exists() or pdf.stat().st_size == 0:
        raise SystemExit("Edge produced no PDF for %s" % svg.name)


def latex(args: list[str]) -> str:
    p = subprocess.run(args, cwd=str(HERE), capture_output=True, timeout=600)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def load_claim_checker():
    """The paper's own claim checker, loaded by path.

    Loaded rather than re-implemented so the in-page check cannot drift from
    the claim set: whatever scripts/verify_paper_claims.py derives from the
    artifact is what the rendered pages are asked to carry.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_build_verify_paper_claims",
        PROJECT / "scripts" / "verify_paper_claims.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def pdftotext_exe() -> Path | None:
    """xpdf's pdftotext, shipped with Git for Windows, if it is installed."""
    cands = [shutil.which("pdftotext")]
    for env in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        base = os.environ.get(env)
        if base:
            cands.append(str(Path(base) / "Git" / "mingw64" / "bin"
                              / "pdftotext.exe"))
    return next((Path(c) for c in cands if c and Path(c).exists()), None)


def _short_figure(s: str) -> bool:
    """A claim short enough that a page cannot wrap it out of reach.

    The in-page check is about figures that rendering can LOSE - a clipped
    table column, a dropped caption number - so it takes the short numeric
    claims. Longer prose claims are reflowed, hyphenated and, in extraction,
    interleaved across columns; requiring those would fail correct PDFs, and
    they are already verified against the source by the claim checker.
    """
    return any(c.isdigit() for c in s) and len(s) <= 24


def _dehyphen(s: str) -> str:
    """Text with every hyphen and its trailing space removed.

    A line break at a hyphen ("Half-" / "width") or an automatic hyphenation
    ("compo-" / "nent") both come back from extraction with a space the claim
    does not have. Comparing with hyphens dropped on both sides is what makes
    the comparison survive typesetting without allowing a figure to be
    approximate: digits and signs are still matched exactly.
    """
    return re.sub(r"-\s*", "", s)


def _pattern(claim: str) -> str:
    """A regex for the claim: loose about space and hyphen, exact otherwise.

    TeX may break a line at a hyphen ("Half-" / "width") or hyphenate a word
    ("compo-" / "nent"), both of which come back from extraction with a space
    the claim does not have, so those two characters match loosely.

    The number, though, must be the number and not merely contain it: a page
    that reads "0.187" does not carry the claim "0.18", and "175.38" does not
    carry "75.38". A claim that sits inside a longer number is therefore no
    match, which is what keeps a mis-rounded or mis-scaled figure on the page
    from passing quietly. A comma after the claim is only a problem when digits
    follow it (",000" - another group of the same number); "down to -13.42%,
    and" is prose, and is a match.
    """
    body = "".join("\\s+" if ch == " " else ("-\\s?" if ch == "-"
                                            else re.escape(ch))
                   for ch in claim)
    return r"(?<![\d,.])(?:%s)(?!\d)(?!,\d)" % body


def _pdf_contains(text: str, claim: str) -> bool:
    """Is the claim on the rendered pages, tolerating typeset line breaks?"""
    if re.search(_pattern(claim), text):
        return True
    return re.search(_pattern(_dehyphen(claim)), _dehyphen(text)) is not None


def _missing_claims(pdf_text: str, tex: str, claims, norm) -> tuple[list[str], int, int]:
    """(labels absent from the pages, figures checked, claims out of scope).

    Pure: `pdf_text` is the extracted text of the rendered pages, `tex` the
    normalized source, `claims` the checker's payload registry, `norm` the
    checker's own normalizer so both sides are compared in the same alphabet.
    Kept apart from the extraction so a test can hand it a page with one digit
    changed and see whether the check notices - which is the only way to know
    it can fail.
    """
    missing, checked, skipped = [], 0, 0
    for label, alts, _scope in claims:
        present = [norm(a) for a in alts
                   if norm(a) in tex and _short_figure(norm(a))]
        if not present:
            skipped += 1                   # not claimed in the .tex, or prose
            continue
        checked += 1
        if not any(_pdf_contains(pdf_text, a) for a in present):
            missing.append(label)
    return missing, checked, skipped


def in_page_check(pdf: Path) -> tuple[list[str], str]:
    """Claims the .tex makes that the RENDERED pages do not carry.

    A .tex that is right is not a PDF that is right: a figure can be dropped by
    an overfull box, a table column can run off the page, a caption can be lost
    in a float. This closes the last link - artifact -> .tex -> what a reviewer
    reads - by extracting the text of the built PDF and requiring every claim
    the paper's own checker says the .tex makes to appear there too.

    The comparison is on flattened text (whitespace collapsed), because a claim
    that wraps across two lines is still on the page, and it is scoped to the
    short numeric claims: those are the ones rendering can clip, and long prose
    cannot be recovered reliably from extracted text at all. Only payload
    claims are used - a table ROW cannot be reconstructed from a text dump, and
    pretending otherwise would weaken the row checks that
    scripts/verify_paper_claims.py performs on the source.
    """
    exe = pdftotext_exe()
    if exe is None:
        return [], "no pdftotext (xpdf, shipped with Git) - not checked"
    mod = load_claim_checker()
    with tempfile.TemporaryDirectory(prefix="icpe-txt-") as tmp:
        out = Path(tmp) / "main.txt"
        subprocess.run([str(exe), "-enc", "UTF-8", str(pdf), str(out)],
                       check=False, capture_output=True, timeout=180)
        if not out.exists():
            return [], "pdftotext produced no output - not checked"
        text = mod.norm(re.sub(r"\s+", " ", out.read_text(encoding="utf-8",
                                                         errors="replace")))
    texts, _ = mod.documents()
    tex = texts[[k for k in texts if k.endswith("main.tex")][0]]
    d, b = mod.load(), mod.load_baseline()
    missing, checked, skipped = _missing_claims(text, tex, mod.payload(d, b),
                                                mod.norm)
    return missing, ("%d short figure(s) the .tex makes are present in the "
                     "rendered pages; %d claim(s) are prose or not claimed "
                     "here, checked against the source only"
                     % (checked, skipped))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-figs", action="store_true", help="reuse figures/*.pdf")
    ap.add_argument("--allow-todo", action="store_true", help="drafting: warn only")
    args = ap.parse_args(argv)

    if not args.no_figs:
        if EDGE is None:
            raise SystemExit("Microsoft Edge not found; run with --no-figs")
        FIGURES.mkdir(exist_ok=True)
        for name in SVGS:
            svg_to_pdf(PROJECT / "docs" / "figures" / name,
                       FIGURES / name.replace(".svg", ".pdf"))
            print("figure  %s" % name.replace(".svg", ".pdf"))

    BUILD.mkdir(exist_ok=True)
    tex = [tool("pdflatex"), "-interaction=nonstopmode", "-halt-on-error",
           "-output-directory=build", "main.tex"]
    log = latex(tex)
    if "Output written" not in log:
        print(log[-3000:])
        return 1
    shutil.copy(HERE / "references.bib", BUILD / "references.bib")
    bib = subprocess.run([tool("bibtex"), "main"], cwd=str(BUILD),
                         capture_output=True, timeout=120)
    latex(tex)
    log = latex(tex)
    pages = int(re.search(r"Output written on \S+ \((\d+) pages?", log).group(1))
    aux = (BUILD / "main.aux").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"\\newlabel\{body-end\}\{\{[^}]*\}\{(\d+)\}", aux)
    body = int(m.group(1)) if m else None
    todos = [ln.strip() for ln in (HERE / "main.tex").read_text(encoding="utf-8").splitlines()
             if "\\TODO{" in ln and not ln.lstrip().startswith("%") and "newcommand" not in ln]
    warnings = sorted(set(re.findall(r"LaTeX Warning: ([^\n]*(?:undefined|multiply)[^\n]*)", log)))
    pdf = BUILD / "main.pdf"
    in_page, in_page_note = (in_page_check(pdf) if pdf.exists()
                             else ([], "no main.pdf - not checked"))

    print("bibtex  exit %d" % bib.returncode)
    print("pages   %d total; body ends on page %s (limit %d, references and "
          "appendices excluded)" % (pages, body, PAGE_LIMIT))
    for w in warnings:
        print("warning %s" % w)
    print("in-page %s" % (", ".join(in_page) if in_page else in_page_note))
    for t in todos:
        print("TODO    %s" % t[:110])
    over = body is None or body > PAGE_LIMIT
    print("RESULT  %s" % ("OVER THE LIMIT" if over else "within the limit"))
    return 1 if (over or bib.returncode or in_page
                 or (todos and not args.allow_todo)) else 0


if __name__ == "__main__":
    raise SystemExit(main())
