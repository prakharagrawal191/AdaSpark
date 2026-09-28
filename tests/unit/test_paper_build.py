"""Can the paper's in-page check fail? A test that cannot lose is no test.

`docs/paper/icpe2027/build.py` re-typesets main.tex and reads the built PDF
back, requiring every short numeric claim the .tex makes to appear in the
rendered pages - the last link of artifact -> .tex -> what a reviewer reads.
That is only worth running if it detects a page that does NOT carry the
figures, so these tests drive the real comparison against pages that are wrong
in the ways that matter (a mis-rounded figure, a figure swallowed by a longer
number, a page with nothing on it) and against the ways that must not fail it
(a claim wrapped over two lines, a word hyphenated across a break, a figure
the source never claimed).

The registry and main.tex are read from the repository, so the tests also
pin that the check is not vacuous: a checker with no claims to make passes
anything, and these would notice.

No LaTeX, no pdftotext, no Spark, no writes outside tmp_path; 0 charged to SC6.
"""


from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[2]


def _load(alias: str, rel: str):
    """Load a repository script by path: they are scripts, not a package."""
    spec = importlib.util.spec_from_file_location(alias, PROJECT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def bld():
    return _load("t_paper_build", "docs/paper/icpe2027/build.py")


@pytest.fixture(scope="module")
def real():
    """(normalized main.tex, the real claim registry, the real normalizer)."""
    chk = _load("t_paper_build_claims", "scripts/verify_paper_claims.py")
    texts, _ = chk.documents()
    tex = texts[[k for k in texts if k.endswith("main.tex")][0]]
    return tex, chk.payload(chk.load(), chk.load_baseline()), chk.norm


# --- the matcher: what may a page do to a figure, and what may it not? ------

def test_a_figure_must_be_the_figure_itself(bld):
    page = "the policy skips 2,976 of 10,048 runs at a ratio of 0.18"
    assert bld._pdf_contains(page, "2,976")
    assert bld._pdf_contains(page, "0.18")
    assert not bld._pdf_contains(page, "2,975")            # one unit off
    assert not bld._pdf_contains(page, "10,047")           # ... in the other
    assert not bld._pdf_contains(page, "0.1")              # a prefix of it


def test_a_longer_number_does_not_stand_in_for_a_claimed_one(bld):
    # the failure the boundary is there for: right digits, wrong magnitude
    assert not bld._pdf_contains("the ratio is 0.187", "0.18")
    assert not bld._pdf_contains("the share is 175.38", "75.38")
    assert not bld._pdf_contains("it ran 29760 seconds", "2,976")


def test_punctuation_around_a_figure_is_not_part_of_it(bld):
    for page in ("reaching 75.38% of the", "(75.38%)", "75.38% -", "at 75.38%."):
        assert bld._pdf_contains(page, "75.38%"), page
    # a comma that ends the clause, not the number: this is the paper's own
    # sentence, and it once failed the check
    assert bld._pdf_contains("negative, down to -13.42%, and instru", "-13.42%")
    assert not bld._pdf_contains("of 2,976,000 runs", "2,976")   # ... but this


def test_signs_and_delimiters_are_exact(bld):
    claim = "[-6.42, +14.82]"
    assert bld._pdf_contains("interval [-6.42, +14.82] covers", claim)
    assert not bld._pdf_contains("interval [+6.42, +14.82] covers", claim)
    assert not bld._pdf_contains("interval [-6.42, -14.82] covers", claim)


def test_a_wrapped_or_hyphenated_claim_is_still_on_the_page(bld):
    # extraction turns a line break into a space, and a hyphen break into a
    # hyphen plus a space; neither may be reported as a missing figure.
    assert bld._pdf_contains("a Half- width measure", "Half-width")
    assert bld._pdf_contains("the compo- nent share", "component")
    assert bld._pdf_contains("interval [-6.42, +14.82] covers",
                             "[-6.42, +14.82]")


def test_hyphenation_tolerance_does_not_become_number_tolerance(bld):
    assert not bld._pdf_contains("the range is 2.9-4.5x", "2.9-5.4x")
    assert not bld._pdf_contains("the range is 2.9-4.5x", "29-4.5x")
    assert not bld._pdf_contains("the range is 2.9 - 4.5x", "2.9-45x")


# --- the scope rule: which claims the pages are asked to carry --------------

def test_short_figure_takes_figures_and_leaves_prose(bld):
    assert bld._short_figure("2,976")
    assert bld._short_figure("75.38%")
    assert bld._short_figure("[-6.42, +14.82]")
    assert not bld._short_figure("no digits here")
    assert not bld._short_figure(
        "Half-width at the prescribed n (system-monitor component)")
    assert not bld._short_figure("Verdicts are reached on 6 of 7 cells")


def test_dehyphen_touches_hyphens_only(bld):
    assert bld._dehyphen("compo- nent") == "component"
    assert bld._dehyphen("Half- width") == "Halfwidth"
    assert bld._dehyphen("75.38%") == "75.38%"
    assert bld._dehyphen("2.9-4.5x") == "2.94.5x"


# --- against the real paper: the check must not be vacuous ------------------

def test_the_paper_really_makes_figures_to_check(bld, real):
    tex, claims, norm = real
    missing, checked, skipped = bld._missing_claims(tex, tex, claims, norm)
    assert checked >= 15, "the in-page check has nothing to check"
    assert checked + skipped == len(claims)
    # a page that carries the source verbatim carries every claim it makes
    assert missing == []


def test_a_blank_page_loses_every_figure_on_it(bld, real):
    tex, claims, norm = real
    missing, checked, _ = bld._missing_claims("", tex, claims, norm)
    assert checked >= 15
    expected = sorted(label for label, alts, _ in claims
                      if any(norm(a) in tex and bld._short_figure(norm(a))
                             for a in alts))
    assert sorted(missing) == expected


def test_one_digit_changed_on_the_page_is_caught(bld, real):
    tex, claims, norm = real
    for label, alts, _scope in claims:
        present = [norm(a) for a in alts
                   if norm(a) in tex and bld._short_figure(norm(a))]
        if not present:
            continue
        page = tex
        for a in present:                       # corrupt every spelling of it
            first = next(c for c in a if c.isdigit())
            page = page.replace(a, a.replace(first, str((int(first) + 1) % 10),
                                             1))
        missing, checked, _ = bld._missing_claims(page, tex, claims, norm)
        assert label in missing, "%s survived a changed digit" % label
        assert len(missing) <= checked
        return
    pytest.fail("main.tex makes no short numeric claim to corrupt")


def test_a_figure_the_source_does_not_claim_is_not_demanded(bld, real):
    tex, _claims, norm = real
    missing, checked, skipped = bld._missing_claims(
        "", tex, [("invented", ["99.99%"], "paper")], norm)
    assert (missing, checked, skipped) == ([], 0, 1)
