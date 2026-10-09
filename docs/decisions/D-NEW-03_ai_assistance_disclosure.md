# D-NEW-03 | 2026-10-09 | AI-assistance disclosure (DEC-045 D4) and public release (DEC-045 D7)

**Status:** PROPOSED. Not a decision. The README has not been changed in either direction on this issue.

## Issue 1: disclosure

**What the governing record says.** DEC-045 is DECIDED: the operator approved D1–D11 by name on
2026-09-26 (`DECISIONS.md`, DEC-045). D4 reads:

> No AI tool is listed as a creator (Zenodo does not permit it). AI assistance is disclosed in the source
> README and in the acknowledgements of any paper.

**What the repository says.** The README has carried no such statement since the repository cleanup of
2026-10-04, which removed AI-related wording at the owner's request. No decision records that change, so
an approved decision and the repository now disagree.

**What the target venue requires.** IEEE's submission policy states that the use of AI-generated content
"shall be disclosed in the acknowledgments section of any article submitted to an IEEE publication". The
AI system must be identified, with "a brief explanation regarding the level at which the AI system was
used". Use limited to editing and grammar is "generally outside the intent" of the policy, and disclosure
is then recommended rather than required
([IEEE Author Center, submission and peer-review policies](https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/guidelines-and-policies/submission-and-peer-review-policies/),
read 2026-10-09). The paper's acknowledgements must therefore follow IEEE's rule, whatever is decided
about the README.

### Options

- **A. Comply with D4.** Add one neutral sentence to the README stating that AI assistance was used and
  that the author reviewed the result, and keep the paper's acknowledgement as IEEE requires.
- **B. Supersede D4's README clause by a new decision.** The README stays free of such wording, and the
  paper's acknowledgements are the single disclosure point.

### Recommendation

Record a decision either way; the present state, with D4 in force and the README silent, is the one
outcome that is not defensible. A implements an existing approved decision and is the smaller change to
the governed record. B is legitimate if recorded, because it narrows D4 instead of ignoring it.

## Issue 2: public release

**What the governing record says.** DEC-045 records "Public release = HELD until the paper venue is
decided (D7)".

**What is true.** The GitHub repository `prakharagrawal191/AdaSpark` is public: the anonymous GitHub API
reported `"visibility": "public"` on 2026-10-08 and 2026-10-09, with the last push on 2026-10-05. No
decision records the release or the venue.

**Why it matters.** A public, named repository is compatible with single-anonymous review but can
conflict with double-anonymous rules (the ICPE 2027 draft is prepared for a double-blind track). IEEE
Access describes its review as single- and/or double-anonymous; check the current submission guidelines
for the chosen article type.

### Options

- **A. Record the release:** its date, that D7's hold is superseded, and the venue decision it follows.
- **B. Make the repository private again** until the venue is decided, as D7 says.

### Recommendation

Choose A if the IEEE Access route is chosen and its review of the article is single-anonymous. Choose B if
a double-anonymous submission is still planned.

## Documents requiring synchronization

`DECISIONS.md` (one entry can settle both issues); `README.md` (option A of issue 1); the paper's
acknowledgements; `docs/research/SC8_RAW_OBSERVATION_DEPOSIT_PLAN.md` if the deposit wording changes.
