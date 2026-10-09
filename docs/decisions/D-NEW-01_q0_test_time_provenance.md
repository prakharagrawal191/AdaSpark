# D-NEW-01 | 2026-10-08 | Where the RL policy's test-time choices come from, and what H2 therefore shows

**Status:** PROPOSED. Not a decision; requires the owner. Nothing in `DECISIONS.md`, the claim map, the
plan or the manuscripts has been changed on its basis.

## Issue

EXP-013 accepted H2: the frozen RL policy is about 4.0× faster than the default baseline B0 (runtime ratio
0.249, 95% CI 0.212–0.295; DEC-053). A zero-execution analysis shows that every test-time choice of that
policy is either its **offline initialization Q₀** (built from the EXP-002 sensitivity grid) or the agent's
**tie-break default**. The 500-execution online training changed none of them. Several records and
manuscript sentences attribute the gain to the learned, adaptive policy.

## Evidence (0 Spark executions)

`scripts/analyze_q0_provenance.py` resolves every frozen test cell through the EXP-005 driver's own frozen
code (`scripts/run_exp005.py::resolve_rl_arm`, the path EXP-013 used: no feedback history, ε = 0). It
compares the three frozen policies with an agent that holds Q₀ and no update. Output:
[`evidence/q0_provenance.json`](evidence/q0_provenance.json).

| Test state | Test cells | Q₀-only choice | RL-s0 / s1 / s2 choice | Source |
|---|---:|---|---|---|
| `agg\|S\|le0` | 7 | 8 = `G-p8-sp16` | 8 / 8 / 8 | Q₀; greedy entry never updated online |
| `join\|S\|le0` | 7 | 8 = `G-p8-sp16` | 8 / 8 / 8 | Q₀; row never updated online |
| `mixed\|S\|le0` | 7 | 9 = `G-p8-sp32` | 9 / 9 / 9 | Q₀; row never updated online |
| `rdd_sort\|S\|le0` | 7 | 7 = `G-p4-sp128` | 7 / 7 / 7 | Q₀; row never updated online |
| `skew_join\|S\|le0` | 15 | 0 = `G-p2-sp16` | 0 / 0 / 0 | No row in Q₀ or any policy: lowest-index tie-break |

- **43 of 43** test cells: all three trained policies choose exactly the Q₀-only action.
- Evaluation always starts with no previous reward (state bin `le0`), and every test input is below
  512 MiB (size bin `S`), so evaluation reaches only these five states (also DEC-053 §1(c);
  `manuscript/sections/08-rl-layer.md` line 21).
- Training updated values almost only in the positive-feedback states (`gt0`): 2 to 12 entries per row
  per seed. In the `le0` rows it changed one non-greedy aggregation entry per seed and nothing else.
  This matches the Day-32 audit (`docs/research/DAY32_CONVERGENCE_AND_STATE_COVERAGE.md` §3.2–3.3).
- Q₀ is the median R3 reward of the EXP-002 training-split records: 167 valid of 208 scanned, about four
  observations per state–action pair. Those 208 attempts are not counted in the 500-execution cap
  (DEC-038 §3 composition of the 483).

## What this changes and what it does not

- **H2's verdict stands.** H2 is stated about "the trained policy", the frozen artifact is that policy,
  and the EXP-013 numbers are unaffected.
- **The attribution changes.** EXP-013 measured the per-family configurations encoded in Q₀ (chosen from a
  sensitivity grid on training data) plus a tie-break default for the never-trained skew-join family. A
  Q₀-only policy would have run identical configurations on every test cell, so under the frozen protocol
  the contribution of online learning to H2 is zero by construction.
- **Adaptation was not evaluated.** The feedback-dependent states, the only place training changed
  values, were never reached in confirmatory evaluation (only in training and the 5-run EXP-012 demo).
- **Budget framing.** The evaluated behaviour derives from EXP-002's 208 attempts, outside the 500-cap; the
  232 policy-training executions did not shape it.
- **H3.** The deficit against static tuning (RL/B1 1.218) comes almost entirely from F4, where the choice
  was the unlearned tie-break (15 of the 16 cells worse beyond noise).

## Current ruling

None. DEC-053 §1(c) records that the policies act as one per-family lookup on test inputs but not where
that lookup comes from, and no record draws the consequence for H2's attribution.

## Options

- **A. Record the finding** as a new decision. Add a claim-map row and a note on the H2 row (wording below)
  and synchronize the manuscripts. No verdict changes.
- **B. A, plus authorize an experiment** that can measure an online-learning effect ([D-NEW-02](D-NEW-02_learning_effect_and_baseline_experiments.md)).
- **C. Leave the governed records as they are**, keeping the finding only in the README and
  `docs/REPRODUCE.md`. Not recommended: the claim map would stay silent on the main caveat to H2.

**Recommendation: A now; B if the submission timeline allows.**

## Proposed wording

Claim-map row (section "Main comparison"):

> | RL test-time choices come from online learning | D-NEW-01 analysis (0 Spark) | 43/43 TEST cells: every RL choice equals the offline Q₀ argmax (4 families) or the lowest-index tie-break (F4); evaluation never reaches a state whose greedy choice training changed | NOT SUPPORTED (H2 verdict unaffected; attribution to Q₀) |

Note to append to the H2 row:

> The accepted effect is that of the frozen policy's per-family choices, which equal its offline
> initialization (EXP-002 grid) or a tie-break; it is not evidence that online learning improved them
> (D-NEW-01).

Manuscript sentence (results and conclusion):

> On the test split the frozen policy acts as a five-rule lookup whose rules are its offline
> initialization from the sensitivity grid (four families) or a tie-break default (skew joins); online
> training changed none of them. The 4.0× improvement over the default baseline is therefore a property of
> those grid-derived choices, not evidence of online learning.

## Documents requiring synchronization

- `DECISIONS.md`: the new entry, operator-signed.
- `docs/research/CLAIM_EXPERIMENT_MAP.md`: the new row and the H2 note.
- `manuscript/sections/*.md`, then a rebuild of `manuscript/AdaSpark_CaseStudy_Report.docx`.
- The owner's journal-format revision of the report (untracked in the working tree): abstract,
  contributions and conclusion. See [D-NEW-06](D-NEW-06_manuscript_claim_alignment.md).
- Already consistent (explanatory only): `README.md` and `docs/REPRODUCE.md`.
