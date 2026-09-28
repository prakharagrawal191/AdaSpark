#!/usr/bin/env python
"""Verify every headline number in the write-ups against the artifacts.

WHY THIS EXISTS. The paper and the research report quote figures that are
hand-transcribed from the analysis artifact. Transcription has already gone
wrong twice in this project: three wrong numbers in the first paper draft (a
not-decided cell's estimate quoted inside a decided-cells range, a wrong
interval bound, a wrong ratio), and a summary table in the research report left
stale for a whole stage after the narrative around it was updated. Both were
caught by hand. This script makes that check mechanical.

It is READ-ONLY and derives every expected value from the artifact, so it
cannot be satisfied by editing the script to match a wrong document. It
computes nothing new: it re-reads what the analysis already wrote. The single
exception is `earliest_stable_pass`, which is re-derived from the committed
implementation so that the recorded column is traceable to code rather than to
a number someone typed.

Three things are checked:

  1. PAYLOAD CLAIMS - every derived figure must appear in some write-up.
  2. ROW CLAIMS      - the tables are checked ROW BY ROW, not number by number:
     the figures for a cell must be on the same line as that cell's name, and
     an ordered row (a prefix trajectory) must also be in the right order. A
     number that is present but attached to the wrong cell is not a claim the
     table makes, and a checker that only greps for tokens cannot see the
     difference.
  3. THE PAPER       - the LaTeX source of record is checked too, through
     `tex_norm()`, which strips comments and unwraps the inline markup the
     paper puts around numbers. A number that survives only inside a LaTeX
     comment is not in the paper, so it does not count as present.

  python scripts/verify_paper_claims.py            # check, exit 1 on mismatch
  python scripts/verify_paper_claims.py --emit     # print the tables instead

A FAILURE HERE IS A DOCUMENT BUG, NOT A DATA BUG. The artifact is
authoritative; fix the prose.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]

# The authoritative artifact: the tracked analysis of the DEC-043 extension.
ANALYSIS = PROJECT / "results" / "evaluation" / "exp009_ext_analysis.json"
# The n=5 artifact the extension pools with and the paper quotes in the
# introduction and in section 6.1.
BASELINE = PROJECT / "results" / "evaluation" / "exp009_analysis.json"
# The analyzer writes a second copy of the same document next to the 4842 raw
# rows it was derived from. That copy is NOT the authority, and it is what a
# reader of the extension directory would find - so if it exists it must agree
# with the tracked artifact, or the record has forked in two.
TWIN = PROJECT / "results" / "experiments" / "exp-009" / "ext" / "analysis_ext.json"
# The submission source of record. Its figures are checked here rather than by
# eye: a transcription slip in a submitted PDF is not recoverable later.
PAPER_TEX = PROJECT / "docs" / "paper" / "icpe2027" / "main.tex"
DOCS = (
    PROJECT / "docs" / "report" / "PAPER_DRAFT_monitoring_overhead.md",
    PROJECT / "docs" / "research" / "DAY39_DEC043_EXP009_STAGES_1_7_EXECUTION.md",
)
# Where `earliest_stable_pass` is DEFINED, so the helper below re-derives the
# trajectory verdicts with the committed rule instead of a re-typed copy.
ANALYSIS_IMPL = PROJECT / "scripts" / "analyze_exp009_ext.py"

# Inline markup the paper wraps numbers in. Unwrapping is what makes an
# emphasised figure (emphasised 14.95 pp) or a cell name (cell F1_agg|small)
# checkable; without it every emphasised number reads as missing.
MACRO = re.compile(r"\\(?:textbf|emph|texttt|cell|text|mathrm)\{([^{}]*)\}")


def rel(path: Path) -> str:
    """Project-relative display path, tolerating paths outside the project.

    ``Path.relative_to`` raises for anything outside PROJECT, which made the
    verifier crash rather than report when pointed at a document elsewhere -
    exactly what its own negative-control test does.
    """
    try:
        return str(path.relative_to(PROJECT))
    except ValueError:
        return str(path)


def norm(text: str) -> str:
    """Normalise typography before comparing.

    The write-ups use typographic characters that Python's formatting does
    not emit: U+2212 MINUS SIGN for negatives, U+00D7 for the multiplication
    sign, and non-breaking spaces. Comparing raw would report every negative
    number as missing, which is a bug in the comparator rather than in the
    prose - it did exactly that on first run.
    """
    return (text.replace("\u2212", "-").replace("\u00d7", "x")
                .replace("\u00a0", " ").replace("\u2013", "-"))


def tex_norm(text: str) -> str:
    """Reduce LaTeX source to the text a reader sees, so figures compare.

    Four jobs, in this order:

    1. drop comments. ``% ...`` is not part of the document, so a figure that
       survives only inside a comment is NOT in the paper. That is the whole
       reason this normaliser exists: a comment-blind grep would pass a paper
       whose numbers had been commented out.
    2. unescape the characters LaTeX needs escaped, so ``14.95\\%`` is the
       token ``14.95%`` and ``F1\\_agg`` is the cell name.
    3. convert LaTeX dashes to the characters they render as, so a range
       written ``2.9--4.5`` matches the artifact-derived ``2.9-4.5``.
    4. unwrap the inline formatting macros, repeatedly, because they nest.
    """
    text = "\n".join(re.sub(r"(?<!\\)%.*", "", line)
                     for line in text.splitlines())
    for src, dst in (("\\%", "%"), ("\\_", "_"), ("\\&", "&"), ("\\#", "#"),
                     ("\\$", "$")):
        text = text.replace(src, dst)
    text = text.replace("---", "\u2014").replace("--", "\u2013")
    text = text.replace("{\\sim}", "~").replace("\\sim", "~")
    text = text.replace("\\,", "").replace("\\ ", " ").replace("~", " ")
    prev: str | None = None
    while prev != text:
        prev = text
        text = MACRO.sub(r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def tex_text(path: Path) -> str:
    """A .tex document, comment-stripped and normalised for comparison."""
    return norm(tex_norm(path.read_text(encoding="utf-8")))


def load() -> dict[str, Any]:
    """Read the authoritative artifact, refusing to work around the twin."""
    if not ANALYSIS.exists():
        raise SystemExit("refusing: %s missing; run analyze_exp009_ext first"
                         % ANALYSIS)
    doc = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    if TWIN.exists():
        twin = json.loads(TWIN.read_text(encoding="utf-8"))
        if twin != doc:
            raise SystemExit(
                "refusing: %s is a working copy of the tracked artifact %s and "
                "no longer matches it (compared as parsed JSON, not as bytes). "
                "The tracked copy is authoritative - restore it with "
                "`git checkout -- %s` and re-run; do not edit the tracked copy "
                "to match a working copy."
                % (rel(TWIN), rel(ANALYSIS), rel(ANALYSIS)))
    return doc


def load_baseline() -> dict[str, Any]:
    if not BASELINE.exists():
        raise SystemExit("refusing: %s missing; the paper quotes its figures"
                         % BASELINE)
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def load_impl():
    """Load the analyzer that DEFINES the extension statistics."""
    spec = importlib.util.spec_from_file_location("v_analyze_exp009_ext",
                                                 ANALYSIS_IMPL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------
# The claim set
# --------------------------------------------------------------------------

def payload(d: dict[str, Any], b: dict[str, Any]) -> list[tuple]:
    """(label, alternatives, scope) claims: a derived figure must appear.

    scope "any"   - some document in DOCS must contain it;
    scope "paper" - the submission source of record must, because the agreed
                    corrections to the submitted text are required there even
                    while the internal report still reads differently.
    """
    out: list[tuple] = []
    add = lambda lab, alts, scope="any": out.append((lab, list(alts), scope))

    n = d["n_new_observations"]
    add("total executions, thousands-separated", ["{:,}".format(n)])
    add("total executions, plain", [str(n)])

    decided = [c for c in d["cells"] if c["cell_decided"]]
    verdicts = sorted({c["verdict"] for c in decided})
    add("decided-cell verdict prose",
        ["Verdicts are reached on %d of %d cells, all %s"
         % (len(decided), len(d["cells"]), verdicts[0])], scope="paper")

    lag = [v["lag1_autocorrelation"] for c in d["cells"]
           for v in c["drift_diagnostic"]["per_condition"].values()]
    add("lag-1 minimum", ["+%.3f" % min(lag)])
    add("lag-1 maximum", ["+%.3f" % max(lag)])
    add("condition-series count", ["%d condition-series" % len(lag)])

    quiet, worst = [], []
    for c in d["cells"]:
        for v in c["drift_diagnostic"]["per_condition"].values():
            w = [x["robust_dispersion_pct"] for x in v["windowed"]]
            if len(w) >= 6:
                quiet.append(min(w))
                worst.append(max(w))
    add("quiet-window minimum dispersion", ["%.2f" % min(quiet)])
    add("quiet-window maximum dispersion", ["%.2f" % max(quiet)])
    add("worst-window dispersion", ["%.2f%%" % max(worst)])

    pts = [c["overhead_sysmon_pct"] for c in decided]
    add("decided sysmon estimate range lo", ["%+.3f%%" % min(pts)])
    add("decided sysmon estimate range hi", ["%+.3f%%" % max(pts)])

    target = d["cells"][0]["power_model"]["target_halfwidth_pp"]
    ratios = [c["power_model"]["sysmon_halfwidth_at_authorized_n_pp"] / target
              for c in d["cells"]]
    add("ratio-to-target range",
        ["%.2f\u00d7 to %.2f\u00d7" % (min(ratios), max(ratios))])
    over = sorted(c["power_model"]["sysmon_required_n_overstatement"]
                  for c in decided
                  if c["power_model"]["sysmon_required_n_overstatement"] > 1)
    add("overstatement range", ["%.1f\u2013%.1f\u00d7" % (over[0], over[-1])])

    conds = len(d["cells"][0]["conditions"])
    pool = sum(c["n_per_condition_pooled_min"]
               - c["power_model"]["sysmon_earliest_stable_pass_n"]
               for c in decided)
    add("repetitions past the earliest stable PASS", ["{:,}".format(pool)])
    add("unnecessary runs, %d conditions" % conds,
        ["{:,}".format(conds * pool)])

    pv = [c["paired_diagnostic"]["sysmon"]["paired_median_pct"]
          for c in d["cells"]]
    add("paired point-estimate lo", ["%+.3f%%" % min(pv)])
    add("paired point-estimate hi", ["%+.3f%%" % max(pv)])

    comp = [v for c in b["cells"]
            for v in (c["overhead_sysmon_pct"], c["overhead_eventlog_pct"])]
    add("baseline negative component count",
        ["%d of %d" % (len([v for v in comp if v < 0]), len(comp))])
    add("baseline most negative component", ["%+.2f%%" % min(comp)])
    add("baseline in-scope observations",
        [str(b["observation_counts"]["recorded_in_scope"])])
    reps = sorted(c["reps_needed_for_2pp_halfwidth"]["sysmon"]
                  for c in b["cells"])
    add("baseline required-n range",
        ["%d to %d" % (reps[0], reps[-1]), "%d\u2026%d" % (reps[0], reps[-1])])
    add("baseline worst sysmon estimate", ["%+.3f%%" % b["worst_sysmon_pct"]])
    hit = [c for c in b["cells"]
           if c["overhead_sysmon_pct"] == b["worst_sysmon_pct"]]
    if hit:
        add("baseline worst sysmon interval",
            ["[%+.2f, %+.2f]" % tuple(hit[0]["sysmon_ci95_pct"])])

    # The caption the plan fixes for the prediction table.
    add("Table 2 caption verbatim",
        ["Half-width at the prescribed n (system-monitor component), and its "
         "ratio to the 2 pp target."], scope="paper")
    return out


def rows(d: dict[str, Any]) -> list[tuple]:
    """(label, anchor, tokens, ordered) claims: figures must share a ROW.

    A table row is checked as a unit. The anchor is the cell name, and every
    token must be on the same line as that anchor, so a figure that belongs to
    another cell - or to another table - cannot satisfy it. `ordered` also
    requires the tokens to run left to right, which is what makes a prefix
    trajectory checkable as a sequence instead of as a bag of numbers.
    """
    out: list[tuple] = []
    for c in d["cells"]:
        out.append(("overhead row %s" % c["cell"], c["cell"], [
            str(c["n_per_condition_pooled_min"]),
            "%+.3f%%" % c["overhead_sysmon_pct"],
            "[%+.3f, %+.3f]" % tuple(c["sysmon_ci95_pct"]),
            "%.2f pp" % c["sysmon_ci_halfwidth_pp"],
            "%+.3f%%" % c["overhead_eventlog_pct"],
            "%.2f pp" % c["eventlog_ci_halfwidth_pp"],
            c["verdict"],
        ], False))

    for c in d["cells"]:
        pm = c["power_model"]
        out.append(("prediction row %s" % c["cell"], c["cell"], [
            "%.2f pp" % pm["sysmon_halfwidth_at_authorized_n_pp"],
            "%.2f\u00d7" % (pm["sysmon_halfwidth_at_authorized_n_pp"]
                            / pm["target_halfwidth_pp"]),
            "%+.3f" % pm["sysmon_loglog_slope"],
            "yes" if pm["sysmon_trajectory_monotone_decreasing"] else "no",
        ], False))

    traj = [c for c in d["cells"] if c["cell"] == "F1_agg|small"][0]
    points = traj["power_model"]["sysmon_trajectory"]
    out.append(("trajectory n row, in order", "n & 5",
                [str(p["n_per_condition"]) for p in points], True))
    out.append(("trajectory half-width row, in order", "half-width (pp)",
                ["%.2f" % p["ci_halfwidth_pp"] for p in points], True))

    for c in d["cells"]:
        pm = c["power_model"]
        e = pm["sysmon_earliest_stable_pass_n"]
        over = pm["sysmon_required_n_overstatement"]
        toks = [str(c["n_authorized_new_per_condition"]),
                "never" if e is None else str(e)]
        if over is None:
            # A null overstatement has to be said in words AND with the dash a
            # reader sees - an empty table cell would claim nothing at all.
            toks += ["never", "\u2014"]
        else:
            toks.append("%.1f\u00d7" % over)
        out.append(("cost row %s" % c["cell"], c["cell"], toks, False))

    for c in d["cells"]:
        p = c["paired_diagnostic"]["sysmon"]
        out.append(("paired row %s" % c["cell"], c["cell"], [
            str(c["n_per_condition_pooled_min"]),
            "%.2f pp" % c["sysmon_ci_halfwidth_pp"],
            "%.2f pp" % p["paired_ci_halfwidth_pp"],
            "%.1f\u00d7" % (c["sysmon_ci_halfwidth_pp"]
                            / p["paired_ci_halfwidth_pp"]),
        ], False))
    return out


def registry(d: dict[str, Any], b: dict[str, Any]) -> tuple[list, list]:
    """The registered claim set. N is derived here and nowhere else.

    The paper quotes the size of this set, so the size is computed from the set
    rather than maintained beside it: a claim added here without updating the
    paper fails the count statement, and a paper that quotes a stale total
    fails too. The statement itself is part of the collection it describes, so
    the printed total and the number the paper must carry are the same figure.
    """
    pres = payload(d, b)
    rowl = rows(d)
    pres.append(("headline-figure count statement",
                 ["all %d headline figures" % (len(pres) + len(rowl) + 1)],
                 "paper"))
    return pres, rowl


def impl_checks(d: dict[str, Any]) -> list[str]:
    """Properties of the artifact, re-derived from the committed code.

    These are not document claims: they hold or fail independently of any
    prose, so they are reported alongside the claim failures but cannot be
    satisfied by editing a write-up.
    """
    try:
        mod = load_impl()
    except Exception as exc:                      # environment, not content
        return ["cannot re-derive earliest_stable_pass from %s: %s: %s"
                % (rel(ANALYSIS_IMPL), type(exc).__name__, exc)]
    problems = []
    for c in d["cells"]:
        traj = c["power_model"]["sysmon_trajectory"]
        got = mod.earliest_stable_pass(traj)
        want = c["power_model"]["sysmon_earliest_stable_pass_n"]
        if got != want:
            problems.append(
                "%s: the committed implementation returns %s for the recorded "
                "trajectory, the artifact records %s"
                % (c["cell"], got, want))
    return problems


# --------------------------------------------------------------------------
# The search spaces. Payload claims search the whole document; row claims need
# line boundaries, so they search the lines and never the flattened text.
# --------------------------------------------------------------------------

def tex_lines(path: Path) -> list[str]:
    """Comment-stripped, macro-unwrapped LINES of a LaTeX document."""
    return [norm(tex_norm(ln))
            for ln in path.read_text(encoding="utf-8").splitlines()]


def documents() -> tuple[dict[str, str], dict[str, list[str]]]:
    """(flattened text, lines) per document, the paper included.

    The paper is not optional: it is the submission source of record, and a
    checker that silently skips a missing paper would report success for a
    submission it never read.
    """
    texts: dict[str, str] = {}
    lines: dict[str, list[str]] = {}
    for p in DOCS:
        if p.exists():
            raw = p.read_text(encoding="utf-8")
            texts[rel(p)] = norm(raw)
            lines[rel(p)] = [norm(ln) for ln in raw.splitlines()]
    if not PAPER_TEX.exists():
        raise SystemExit("refusing: %s missing; the paper is checked here"
                         % rel(PAPER_TEX))
    texts[rel(PAPER_TEX)] = norm(tex_norm(PAPER_TEX.read_text(encoding="utf-8")))
    lines[rel(PAPER_TEX)] = tex_lines(PAPER_TEX)
    return texts, lines


def _fields(line: str) -> set[str]:
    """The cells of one LaTeX table row, as written."""
    return {f.strip(" \\{}") for f in line.split("&")}


def _row_ok(line: str, toks: list[str], ordered: bool) -> bool:
    """Do all tokens sit on this line - and, if ordered, in this order?

    Two ways to satisfy a row: the tokens are whole cells of that row (the
    LaTeX case, where `28` cannot be satisfied by the `28` inside `128`), or
    they are present in a document without table markup. Order is enforced by
    searching forward from the end of the previous match, which is what makes
    the trajectory rows checkable as sequences.

    Tokens are put through `norm()` here rather than at the call sites: the
    line is already normalised, and a token left in typographic form (a `×`
    that the document writes as U+00D7) would otherwise never match.
    """
    toks = [norm(t) for t in toks]
    if ordered:
        pos = 0
        for t in toks:
            i = line.find(t, pos)
            if i < 0:
                return False
            pos = i + len(t)
        return True
    if "&" in line:
        # A LaTeX table row: a token must BE a cell of that row, never a
        # substring of one, or `28` would be satisfied by `128`.
        return all(t in _fields(line) for t in toks)
    return all(t in line for t in toks)


def emit(d: dict[str, Any]) -> None:
    """Print the tables the write-ups quote, derived from the artifact."""
    print("## Overhead per cell at the pooled n (from %s)\n" % rel(ANALYSIS))
    print("| Cell | pooled n | sysmon | 95% CI | half-width | eventlog | "
          "half-width | verdict |")
    print("|---|---|---|---|---|---|---|---|")
    for c in d["cells"]:
        print("| `%s` | %d | %+.3f%% | [%+.3f, %+.3f] | %.2f pp | %+.3f%% | "
              "%.2f pp | %s |"
              % (c["cell"], c["n_per_condition_pooled_min"],
                 c["overhead_sysmon_pct"], c["sysmon_ci95_pct"][0],
                 c["sysmon_ci95_pct"][1], c["sysmon_ci_halfwidth_pp"],
                 c["overhead_eventlog_pct"], c["eventlog_ci_halfwidth_pp"],
                 c["verdict"]))
    print("\n## Half-width at the prescribed n (system-monitor component)\n")
    print("| Cell | at prescribed n | ratio to target | log--log slope | "
          "monotone |")
    print("|---|---|---|---|---|")
    for c in d["cells"]:
        pm = c["power_model"]
        print("| `%s` | %.2f pp | %.2f\u00d7 | %+.3f | %s |"
              % (c["cell"], pm["sysmon_halfwidth_at_authorized_n_pp"],
                 pm["sysmon_halfwidth_at_authorized_n_pp"]
                 / pm["target_halfwidth_pp"], pm["sysmon_loglog_slope"],
                 "yes" if pm["sysmon_trajectory_monotone_decreasing"] else "no"))
    print("\n## What the model cost (retrospective; not a stopping rule)\n")
    print("| Cell | prescribed n | earliest stable PASS | overstated |")
    print("|---|---|---|---|")
    for c in d["cells"]:
        pm = c["power_model"]
        e = pm["sysmon_earliest_stable_pass_n"]
        over = pm["sysmon_required_n_overstatement"]
        print("| `%s` | %d | %s | %s |"
              % (c["cell"], c["n_authorized_new_per_condition"],
                 e if e else "never",
                 "%.1f\u00d7" % over if over else "\u2014"))
    print("\n## Paired diagnostic (secondary, exploratory)\n")
    print("| Cell | n | unpaired | paired | ratio |")
    print("|---|---|---|---|---|")
    for c in d["cells"]:
        p = c["paired_diagnostic"]["sysmon"]
        u = c["sysmon_ci_halfwidth_pp"]
        print("| `%s` | %d | %.2f pp | %.2f pp | %.1f\u00d7 |"
              % (c["cell"], c["n_per_condition_pooled_min"], u,
                 p["paired_ci_halfwidth_pp"], u / p["paired_ci_halfwidth_pp"]))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--emit", action="store_true",
                    help="print the generated tables instead of checking")
    args = ap.parse_args(argv)

    d = load()
    b = load_baseline()
    if args.emit:
        emit(d)
        return 0

    pres, rowl = registry(d, b)
    texts, lines = documents()
    paper = rel(PAPER_TEX)

    missing: list[str] = []
    for label, alts, scope in pres:
        space = {paper: texts[paper]} if scope == "paper" else texts
        if not any(norm(a) in t for a in alts for t in space.values()):
            missing.append("%s (%s) is not in %s"
                           % (label, " | ".join(alts),
                              "the paper" if scope == "paper"
                              else "any write-up"))
    for label, anchor, toks, ordered in rowl:
        got_row = False
        near = None
        for name, doc_lines in lines.items():
            for ln in doc_lines:
                if anchor not in ln:
                    continue
                if _row_ok(ln, toks, ordered):
                    got_row = True
                    break
                if near is None:
                    near = "%s: %s" % (name, ln[:150])
            if got_row:
                break
        if not got_row:
            missing.append("%s: no single row carries %s%s"
                           % (label, ", ".join(repr(t) for t in toks),
                              "" if near is None
                              else " (nearest such row %s)" % near))

    problems = impl_checks(d)

    print("verify_paper_claims: %d claims checked against %s"
          % (len(pres) + len(rowl), rel(ANALYSIS)))
    print("  authoritative:  %s (artifact_id %s)"
          % (rel(ANALYSIS), d["artifact_id"][:16]))
    print("  n=5 baseline:   %s" % rel(BASELINE))
    print("  working copy:   %s" % (rel(TWIN) if TWIN.exists()
                                    else "%s (absent, nothing to compare)"
                                    % rel(TWIN)))
    for name in texts:
        print("  document:       %s" % name)
    if problems or missing:
        print("\nMISMATCH - the artifact is authoritative; fix the prose:")
        for m in problems + missing:
            print("  - %s" % m)
        return 1
    print("  OK: every checked figure is traceable to the artifact.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
