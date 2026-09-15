# Day 33 — EXP-005 7-Run Dry Slice (corrected record)

**Status.** Dry slice complete: 7 of the authorized 245 TEST executions. 238
remain and proceed only on explicit operator instruction.
**Corrections.** This document supersedes the first Day-33 report, which
contained three errors. They are listed in §6 rather than silently fixed, so the
correction itself is auditable.

Every hash below was copied from the artifact, not transcribed by hand. All are
64 hex characters.

---

## 1. Authorization

**DEC-014 is `APPROVED (OPERATOR)` — DEC-018 Decision B, 2026-09-14.**
It is **not** pending. No supervisor reviewed it; DEC-018 Decision A converted
that self-imposed gate into an operator decision and recorded the absence of
supervisor review permanently.

Authorized scope: 7 instances x 7 arms x 5 repetitions = **245 TEST
executions**, on EXP-005's own register line, outside the SC6 TRAIN cap.

Governance snapshot: `git log --oneline -1` = `715a7d3`.

## 2. Frozen instances and the executed cell

`results/evaluation/exp005_instances.json` holds 7 instances, `executed: false`,
every one verified `split == "test"` by `split_of()` at driver load time:

| # | Family | Scale | Seed | Unseen dimension |
|---|---|---|---|---|
| 1 | F1_agg | large | 3 | unseen scale L |
| 2 | F2_join | large | 3 | unseen scale L |
| 3 | F3_rdd | large | 3 | unseen scale L |
| 4 | F4_ski | large | 3 | unseen family + scale |
| 5 | F5_mixed | large | 3 | unseen scale L |
| 6 | F4_ski | small | 4 | unseen family + seed |
| 7 | F4_ski | medium | 4 | unseen family + seed |

The dry slice ran **instance 1 only** (`F1_agg|large|seed3`), confirmed present
in the frozen list. No other TEST cell was touched.

## 3. Queue and slice

Full queue: **245** entries; 7 arms x 35 runs each (7 instances x 5 reps).

Arms: `B0, B1, B2, B4, RL-s0, RL-s1, RL-s2`.
Excluded and confirmed absent from the queue: **B3** (analytic finding, DEC-017)
and **B0'** (EXP-005b only).

The slice is a true prefix — queue entries 1-7:

| idx | Arm | Rep | exec_s | source | usable |
|---|---|---|---|---|---|
| 1 | B0 | 1 | 53.613 | runner | true |
| 2 | B0 | 2 | 54.948 | runner | true |
| 3 | B0 | 3 | 49.227 | runner | true |
| 4 | B0 | 4 | 48.276 | runner | true |
| 5 | B0 | 5 | 47.471 | runner | true |
| 6 | B1 | 1 | 9.945 | runner | true |
| 7 | B1 | 2 | 10.869 | runner | true |

Ledger: planned 7, started 7, completed 7, failed 0, remaining in slice 0,
**remaining total 238**.

## 4. Identity verification

| Quantity | Value |
|---|---|
| spec artifact_id | `e3c902841db1bef21ba66ff37b91bba7fab53f7c36b1e7c66cae573f67298449` |
| summary artifact_id | `0c7577ca0acf052b6294a421aa05505407836c8ca0683e8b42b941721c391dcb` |
| instances_fingerprint (spec == summary) | `1c33975aebf813023777a209165e3aa5ee8b66fe61ae5eefa80337750787c815` |
| dataset_fingerprint (all 7 runs) | `030fda480417612ac68bde6f52d57054fc15cee78f1e88f0d51f00f9a611688b` |
| B0 declared / applied | `a69cee0fdc39840749530e92c11c45bb093d1ebf2b8b36396ce34443e0153612` / `949ddaf560401299d91b6ceb218e265a9fa80a585d7ea05c58a79bb2b7b653ee` |
| B1 declared / applied | `f857d8de346b88fc1a849b9d5bec6f7e67060d80633621f2cc62e0b33e58204c` / `285ad990e5bc5b8e691073f7a37e363ebb938b95fff945b64cab2f2820398681` |

**B1 did not drift — this is the strong check and it passes.** B1's *applied*
fingerprint `285ad990...398681` equals `resolve("B1").config_fingerprint`
exactly, and equals the frozen `G-p8-sp16` fingerprint recorded on Day 32.
B1's `arm_provenance.selection_artifact_id` is
`0a0ecbe5151c81eda87a54f97ebe5d3037f45d3fa2ad9b97cc5e9033e089d6ad`, which
matches `baseline_selection.json`'s `artifact_id` exactly.

The declared/applied split is structural, not drift: *declared* is the knob-only
`ConfigPoint.fingerprint()`, *applied* is the full `SparkConfig.fingerprint()`
after resolution. B1 exhibits the same pattern.

**B0's check is weaker and must not be overstated.** B0's applied fingerprint
matches neither its declared value nor the live `configs/baseline_b0.yaml`
fingerprint (`9270d2ce...`). This is expected — `app_name` and path fields differ
at run time and are inside the SparkConfig hash — but it means **no frozen value
exists to cross-check B0's executed configuration against**. What does hold is
that the driver calls `assert_b0_unchanged(base)` before executing, which is a
real guard on the source file.

No cross-contamination: B0 rows carry only B0 provenance, B1 rows only B1.

## 5. Guards and integrity

**Split guard.** All 7 observations carry `split: "test"`. The driver
independently re-derives `split_of(family, scale, dataset_seed)` for every one of
the 7 instances at load time and refuses the run if any is not TEST, and refuses
unless `executed is false` and exactly 7 instances are present. This re-derivation
— not any fingerprint — is the actual leakage protection, and it is sound.

**A genuine integrity gap, recorded not repaired.** Two load-bearing evaluation
artifacts fail the project's own `freeze.verify_artifact()`:

| artifact | `artifact_id` | `fingerprint` | `verify_artifact` |
|---|---|---|---|
| `baseline_selection.json` | yes | yes | **PASS** |
| `evaluation_spec.json` | yes | yes | **PASS** |
| `test_freeze.json` | yes | yes | **PASS** |
| `b4_selection.json` | yes | **no** | **ArtifactCorrupt** |
| `exp005_instances.json` | **no** | yes | **ArtifactCorrupt** |

Neither failure indicates tampering. Both artifacts were written with hand-rolled
hashing instead of `freeze.seal()`, so they carry only one of the two fields the
verifier requires. `b4_selection.json` is a Day-32 defect of this project's own
`scripts/run_b4_search.py`, which computed `artifact_id` inline rather than
sealing through `freeze`. `exp005_instances.json` declares a `fingerprint` that
could not be reproduced from its content by file-bytes or canonical-JSON hashing,
so its derivation is unknown and it should not be cited as a verified pin.

**These are deliberately NOT re-sealed.** Re-sealing would change
`exp005_instances.json`'s fingerprint, which is already recorded inside the
`spec.json` and `summary.json` of an executed TEST slice, and would change
`b4_selection.json`'s `artifact_id`, which is cited in `DECISIONS.md` and in the
Day-31 validator. Mutating an artifact after it has been used is precisely the
failure mode this project's discipline exists to prevent. The gap is recorded as
a limitation; any repair belongs to a fresh artifact under a new decision.

## 6. Corrections to the first Day-33 report

1. **Authorization status was wrong.** It stated DEC-014 was
   `PENDING SUPERVISOR APPROVAL — unchanged`. DEC-014 is `APPROVED (OPERATOR)`
   under DEC-018 Decision B. The report cited commit `715a7d3` — which *is* the
   DEC-018 commit — while describing the pre-DEC-018 state, so it contradicted
   itself. Uncorrected it would assert that TEST was executed while authorization
   was still outstanding, which is false and is the more damaging direction of
   error.

2. **Five hashes were quoted with one extra character each** (65 chars; SHA-256
   is 64). Affected: B0 applied, B1 `selection_artifact_id`, dataset fingerprint,
   spec `artifact_id`, summary `artifact_id`. The artifacts on disk are correct;
   only the transcription was wrong. §4 above carries the verified values.

3. **`exp005_instances.json` does not contain per-instance dataset fingerprints.**
   The report described "fingerprints computed over each instance's manifest tree
   (exact file set + bytes)". Its instance records hold only `family`, `scale`,
   `dataset_seed`, `split`, `unseen_dimension`. A single artifact-level
   `fingerprint` covers the list; there is no per-dataset content hash, so the
   `dataset_fingerprint` recorded in each observation has **no frozen counterpart
   to be checked against**. Relatedly, the report's claim that B0's two
   fingerprints are "both consistent with the frozen B0 baseline" asserts a check
   no artifact supports (see §4).

## 7. Scope discipline

No analysis, no retuning, no winner selection, no queue alteration. The 7
observations are a harness-validation sample: 5 B0 and 2 B1 observations on one
instance support no arm ranking and no statistical claim of any kind.

**Noise floor (DEC-018).** EXP-001 worst-cell CV = **0.1189**. A within-cell arm
difference below roughly 12% is not to be described as an independently
established effect without additional justification. The dry slice is not an
occasion to test that threshold.

**Descriptive note, explicitly not a finding.** B0 ran 47-55 s and B1 ran ~10 s.
This is recorded solely to confirm the timing path captured plausible values. It
is 7 points on 1 of 7 instances with no repetition structure across instances,
and no inference — directional or otherwise — is drawn from it here.

## 8. State after Day 33

```
EXP-005      7 / 245 executed, 238 remaining
TRAIN ledger 336 / 500 unchanged (TEST runs are not charged to SC6)
TEST         executed only through the authorized EXP-005 path
EXP-005b     not executed        EXP-006  not executed
B3           not an arm          B0'      not an arm
DEC-014      APPROVED (OPERATOR), DEC-018 Decision B
```

**Next gate.** The dry slice passed every technical dimension it was designed to
test. The remaining 238 runs are **not** continued automatically and proceed only
on explicit operator instruction.
