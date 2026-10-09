# D-NEW-06 | 2026-10-09 | Aligning the manuscripts with the evidence

**Status:** PROPOSED. No manuscript was edited. The committed report (`manuscript/sections/*.md` and the
`.docx` built from them) and the owner's newer journal-format draft (untracked in the working tree) are the
owner's documents.

## Basis

A claim-consistency audit on 2026-10-08 compared, claim by claim, the README, the claim map, the committed
report sources, the owner's draft (text extracted that day) and the ICPE draft's abstract and conclusion
with the evidence (`results/evaluation/exp013_analysis.json`, the frozen policies, the Day-32 audit,
`docs/PLAN.md` §17, `configs/baseline_b0.yaml`). The draft's abstract, executive summary and contributions
table were word-for-word those of the committed report, so the fixes apply to both. The draft has since
been revised further, so locate each sentence by its text, not by line number.

All headline numbers are consistent: H2 0.249 (0.212–0.295), 36/37 cells, Holm p = 4.4×10⁻¹¹; H3 1.218 and
1.206, worse on 16 cells against B1/B3 (15 of them F4) and 15 against B4, better on 1; the AQE, SC5, SC7,
overhead and pilot verdicts. No document claims to be "first".

## Corrections that change an interpretation (need D-NEW-01 first)

| Where | Current reading | Proposed reading |
|---|---|---|
| Results ("what the learner did deliver …"), conclusion, related-work table ("adapts online: yes, ≤500 runs") | The 4.0× gain was delivered by the learner within the 500-execution budget | The frozen policy's test-time choices all came from its offline initialization (208 EXP-002 grid attempts, not counted in the budget) or a tie-break; online training (232 executions) changed none of them. Related-work table: "Adapts online: during training only (test-time choices = offline Q₀ or tie-break); 208 grid runs (Q₀) + 232 training runs" |
| Interpretation of the skew-join deficit | "points to a specific gap in what the policy learned" | Skew joins were held out of training and absent from the grid, so their configuration is the lowest-index tie-break over untrained values. The deficit shows what the policy does on a family it never saw, not a learned preference |
| Seed agreement ("yet on test inputs the replicates collapse to one rule") | Implies the seeds converge on test inputs | They act identically on test inputs only because every test episode uses the shared offline initialization, which training never changed |

## Wording and factual corrections (no conclusion changes)

| Theme | Problem | Proposed fix |
|---|---|---|
| "Spark defaults" (abstract, summary, conclusion, baseline table "Factory settings, AQE-off") | B0 is Spark's default 200 shuffle partitions with the master pinned to `local[2]` (2 of 24 cores) and AQE off; PLAN §17 names the AQE-on variant B0′ as the Spark 3.x factory default | "the default baseline B0 (Spark's default 200 shuffle partitions, `local[2]`, AQE off; enabling AQE, Spark 3.x's default, made no difference beyond noise on the 6 cells where it was tested)" |
| Budget labels ("training used 483") | 483 is the SC6 ledger: 232 policy training + 84 B4 calibration + 20 EXP-001 + 126 EXP-007 + 21 unauthorized smoke runs; EXP-002's 208 attempts are not counted | State the composition, and that the grid that supplied Q₀ was not charged |
| Strength of B1 ("best", "well-chosen", "competent static tuning") | B1 is the lowest median among the 4 of 12 configurations with a usable run on every validation cell, one run each; an ineligible configuration had a lower median | "a static configuration chosen on the validation split" |
| Scope in the abstract | Omits one Windows 11 machine, Spark 3.5.9 local mode, synthetic data, inputs at most about 0.4 GB, all in one size bin | Add them |
| Return-on-investment paragraph ("proportionally fewer executor-hours") | Contradicts the report's own CPU measurements (tuned configurations draw about twice B0's CPU on two families) and extrapolates to production | "finished about 4× faster on the 37 test cells of this single-machine study while drawing more CPU; compute savings would be smaller than the runtime ratio and were not measured" |
| √n finding ("about 3,000 runs avoidable", "fail universally", "measured waste") | The count is retrospective; no stopping rule was built; the evidence is 7 of 7 cells of one study | "in hindsight, about 3,000 of the 4,842 runs were not needed for the final verdicts; a stopping rule that would have saved them in advance was not built or tested" |
| Cause of the M8 failure ("a measurement-density fact") | Goes beyond the Day-32 audit, which does not claim denser training would change the verdict | "Training was sparse, which limits what M8 can show; whether denser training would produce agreement was not tested" |
| "Pre-registered" | Journal readers assume an external registry | "hypotheses, decision rules and analysis code committed to the project repository before the first run (no external registry; supervisor counter-signature pending)" |
| Data availability and the artifact appendix | States that the EXP-002/005/009 raw records are committed, that 16/16 checks pass from committed artifacts alone, and that the EXP-014 analysis awaits close-out | Only EXP-002's raw record is tracked; all other raw observations await the DEC-045 deposit; the harness now has 25 checks, passes on the recording machine, and runs integrity-only on a fresh clone; the EXP-014 analysis is committed (see [D-NEW-04](D-NEW-04_reproduction_plan_and_registry.md)) |
| Count of refuted conclusions | The conclusion lists four, but one (the random-search tie) was INCONCLUSIVE under its pre-registered rule | "three were refuted by their pre-registered rules, and the apparent tie with random search was shown to be a queue-order artifact" |
| A/A control ("a 2% noise floor") | Median gap 2.0%, maximum 9.7% | "a median 2.0% gap (maximum 9.7%; all 38 cells inside ±11.89%)" |
| ICPE draft abstract and availability section | "The cause is measurable rather than inferred"; "unnecessary" without hindsight; fresh-clone re-derivation stated as fact | "The likely cause is directly measured …"; "in hindsight … not needed"; "rehearsed on the recording machine; a second machine has not been tried" |

## Recommendation

Decide D-NEW-01 first. Then apply all rows above to the owner's draft and to `manuscript/sections/`, and
rebuild the `.docx`. The second group needs no decision; it corrects wording against recorded evidence.
