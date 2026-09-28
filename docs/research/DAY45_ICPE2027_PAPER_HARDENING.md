# Day 45 - ICPE 2027 paper hardening: final execution report

**Date:** 2026-09-28 (Day 45)
**Decision record:** `DECISIONS.md` DEC-046 - DRAFTED, operator approval PENDING
**Scope:** the paper (`docs/paper/icpe2027/main.tex`), its two verification scripts, the paper build, and `docs/report/PAPER_DRAFT_monitoring_overhead.md`.
**Charges:** 0 Spark executions, 0 charged to SC6. No result artifact, ledger, manifest or hash was edited.

## 1. Outcome - every gate run on 2026-09-28

| Check | Command | Result |
| --- | --- | --- |
| Claim traceability | `python scripts/verify_paper_claims.py` | 55 claims checked against `results/evaluation/exp009_ext_analysis.json`; every checked figure traceable |
| Corroboration | `python scripts/verify_reproducibility.py` | OVERALL PASS (16 checks, 16 pass, 0 fail, 0 skip) |
| Unit suite | `python -m pytest tests/unit` | 756 passed, 1 skipped (the skip is pre-existing) |
| Day-31 gate | `python scripts/validate_day31.py` | OVERALL PASS (36 checks, 36 pass, 0 fail, 0 skip) |
| Paper build | `python docs/paper/icpe2027/build.py --allow-todo --no-figs` | 6 pages; body ends on page 5 of a 10-page limit; bibtex exit 0; in-page 21/21 figures present; 1 `\TODO` open |

`--allow-todo` is needed only because of the one author-confirmation item in section 5; without it the build exits 1 by design.

## 2. What was wrong, and what the evidence was

**(i) The claim checker could not fail in the ways that mattered.** It searched the paper as a bag of numbers over raw LaTeX, so a figure inside a `\comment{}`, a number copied into the wrong column of a table, or a verdict contradicting its own test statistic all passed - nothing tied a figure to the line or cell that asserted it. `tex_norm()` now drops comments and macro scaffolding so a figure counts only if it is in the rendered text; row claims are anchored to the line their cell's anchor sits on; the claim tally is derived from the registry the script builds, so it cannot disagree with itself. Six negative controls in `tests/unit/test_exp009_ext.py` prove each property can fail: `test_verifier_fails_when_only_the_paper_is_wrong`, `test_verifier_ignores_figures_inside_latex_comments`, `test_tex_norm_unwraps_markup_and_latex_dashes`, `test_row_claims_reject_a_reordered_trajectory`, `test_verifier_refuses_a_missing_paper`, `test_verifier_counts_the_claims_it_registers`.

**(ii) The corroboration harness failed 13 of 16 on a clean checkout.** The cause was measured, not assumed: 29 of the analyzer's float leaves - 21 `lag1_autocorrelation` and 8 `*_loglog_slope` - re-derive within 1.7e-15 relative of the committed values, about 15 ULP at those magnitudes. That is association noise in how `analyze_exp009_ext.py` derives those two quantities; every other leaf, including every verdict, median, interval, half-width and prefix-trajectory point, is bit-identical. The comparison now keeps content strict and tolerates only that arithmetic (`FLOAT_REL_TOL = 1e-9`): a non-float leaf difference or any structural difference is a hard FAIL; `artifact_id` is not compared to the committed hash but must satisfy the artifact's own hash convention, recomputed here; both SVGs must re-render identically with the stamped hash masked out. The committed artifact is the research record and was NOT regenerated to match the code.

**(iii) The checks stopped at the `.tex`.** A figure the source makes can still be absent from what a reviewer reads - a clipped table column, a caption lost in a float. `build.py` now reads the built PDF back (`pdftotext`, which ships with Git for Windows, so no new dependency) and requires every short numeric claim the `.tex` makes, as derived from the artifact by the claim checker, to appear in the rendered pages: 21 of 21 present.

**(iv) Four paper figures did not match the artifact they cite.** Corrected in `main.tex` and mirrored into the report draft under one source of record:

| Figure | Was | Now | Where |
| --- | --- | --- | --- |
| Ratio of half-width to the 2 pp target, across cells | `0.12x-7.7x` | `0.18x-7.70x` | `main.tex:40` |
| Worst contention window in one series | `75.4%` | `75.38%` | `main.tex:43`, `:327` |
| Cost of not deciding a cell early | implied | `992 x 3 = 2,976` runs, explicit | `main.tex:411` |
| Headline figures the checker traces | 73 | 55 | `main.tex:466` |

The last one is the one that mattered most: the paper claimed a traceable-figure count the checker could never produce, so the claim was a promise rather than a result.

## 3. What the new in-page check found when it first ran

Its first run flagged 7 figures, and both causes are worth recording because one was a real weakness in the check itself. Six were the checker's normalisation not being applied to the extracted text (U+2212 minus, `x` for `times`, en dashes), so the claims never matched. The seventh was different: TeX had broken the Table 2 caption across a column, so extraction returned `sys | stem-monitor com466 | ponent` - a correct PDF, an unrecoverable string. Prose cannot be reliably recovered from a text dump, so the check is scoped to short numeric figures: a claim wrapped over two lines or hyphenated across a break is accepted, digits and signs are matched exactly, and a figure embedded in a longer number (`0.187` for a claim of `0.18`) does not count as present. `tests/unit/test_paper_build.py` (12 tests, new) pins all of it, including the non-vacuity controls: a blank page must lose every figure, and a claim the source never makes must not be demanded.

## 4. Files

| File | Change | DEC-046 |
| --- | --- | --- |
| `scripts/verify_paper_claims.py` | rewritten: `tex_norm()`, row-anchored checks, self-consistent claim count | D1 |
| `tests/unit/test_exp009_ext.py` | 6 negative controls for the claim checker | D1 |
| `docs/paper/icpe2027/main.tex` | four figures corrected to the artifact; captions and decided-cell prose aligned | D2 |
| `docs/report/PAPER_DRAFT_monitoring_overhead.md` | aligned to the paper under a source-of-record banner | D4 |
| `scripts/verify_reproducibility.py` | `FLOAT_REL_TOL = 1e-9` on float leaves of the one non-byte-exact analyzer; content otherwise exact | D3 |
| `docs/paper/icpe2027/build.py` | in-page check: claims the `.tex` makes must be in the rendered PDF | D5 |
| `tests/unit/test_paper_build.py` | new, 12 tests for that matcher, including non-vacuity controls | D5 |
| `scripts/validate_day31.py` | check 27's allow-list names the four tracked files above, citing DEC-046 | D4 |
| `DECISIONS.md` | DEC-046 appended, DRAFTED | - |

## 5. Outstanding - not done here, and why

1. **One `\TODO` remains in `main.tex`**: the author must confirm the disclosure sentence about full responsibility for the content (plan P4). That is a statement only the author can make; the build runs with `--allow-todo` until then and exits 1 without it.
2. **DEC-046 is DRAFTED.** The four check-27 allow-list entries are in place and cite it, but the decision text itself is unsigned - the approval line is in `DECISIONS.md` under its `**Status.**` paragraph.
3. **The in-page check needs `pdftotext`** (xpdf, shipped with Git for Windows). If it is absent the build prints *not checked* for that step; it never reports a pass it did not perform.
4. **Three claims are verified against the source only** - prose, or figures the paper does not state. That is a deliberate limit of extraction, recorded in the code that applies it.

## 6. What this work did NOT do

0 Spark executions; no TRAIN or TEST cell; no analyzer, artifact, ledger, manifest or hash edited; `SC6 cap = 500` and `SC6 ledger = 483 / 17` unchanged; `docs/PLAN.md` unchanged; no gate, threshold or acceptance criterion changed (`FLOAT_REL_TOL` is a comparison tolerance for one stored artifact, not a criterion); no prior decision entry amended; nothing published, tagged, submitted, and no venue decided.

## 7. Reproduce

```powershell
python scripts/verify_paper_claims.py
python scripts/verify_reproducibility.py
python -m pytest tests/unit
python scripts/validate_day31.py
python docs/paper/icpe2027/build.py --allow-todo --no-figs
```

The build converts the two committed SVGs to PDF with Microsoft Edge unless `--no-figs` is passed; drop that flag to re-render them. Both PDF figure paths must exist for the paper to typeset.

