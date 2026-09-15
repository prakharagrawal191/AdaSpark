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

**What DEC-018 Decision B approved**, in its own words: TEST is opened "solely
and strictly for the frozen EXP-005 protocol at the resolved scope: **7
instances x 7 arms x 5 repetitions = 245 TEST executions**, charged to EXP-005's
own register line and outside the SC6 TRAIN cap… TEST remains sealed for every
other purpose, including EXP-005b and EXP-006, each of which requires its own
decision."

Two consequences follow, and they are distinct:

1. **The 7-run dry slice was legitimately authorized when it ran.** It is a
   prefix of the 245 that Decision B released. It was **not** executed under a
   still-pending authorization: DEC-018 was committed as `715a7d3` and the slice
   ran afterwards, against instance 1 of the 7 named in the same decision.
2. **The remaining 238 are also already authorized.** They are the balance of
   the same 245. What gates them is not authorization but an operator
   *sequencing* control — the dry-slice protocol requires explicit instruction
   before continuing. Authorization and instruction are different things, and
   the earlier record blurred them.

Nothing outside the 245 is authorized by any current decision.

Governance snapshot at correction time: `715a7d3` (DEC-018), `feb5a16` (this
record).

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
after resolution. Both arms exhibit the pattern, and both declared values were
independently recomputed: `ConfigPoint("B0").fingerprint()` = `a69cee0f...3612`
and `ConfigPoint("G-p8-sp16").fingerprint()` = `f857d8de...204c`, each equal to
the declared value recorded on every row of its arm.

**B0's check is weaker and must not be overstated.** The evidence-based
statement is:

> B0 was resolved from the frozen `configs/baseline_b0.yaml` source. The applied
> runtime fingerprint is a *derived runtime* configuration fingerprint and is
> **not** identical to the source-file fingerprint (`9270d2ce...`), because
> `app_name` and path metadata are resolved per run and fall inside the
> `SparkConfig` hash. **No evidence of B0 configuration drift was found.**

No claim of exact fingerprint equality is made for B0, because none exists. What
does hold is that the driver calls `assert_b0_unchanged(base)` before executing,
which is a real guard on the source file, and that AQE is recorded `false` in
B0's arm provenance. B1's case remains the stronger one and is stated as such
above.

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

Neither failure indicates tampering, but **the two failures have different causes
and must not be described together.** Each artifact carries only one of the two
fields `verify_artifact()` requires, and that is where the similarity ends:

- **`exp005_instances.json` — the content hash is GENUINE.** Its `fingerprint`
  `1c33975a...c815` is **bit-identical** to `freeze.artifact_fingerprint()`
  recomputed over the file (sha256 over canonical JSON, `sort_keys=True`,
  `separators=(",",":")`, `ensure_ascii=True`, excluding the
  `_FINGERPRINT_EXCLUDED` keys `artifact_id`/`fingerprint`/`created_utc`,
  `freeze.py:37,60-65`). The hashing is **not** hand-rolled and the value **is a
  verified content pin** of the frozen instance list. What is missing is only the
  `artifact_id` stamp that `seal()` would have added, and `verify_artifact()`
  fails solely on that: *"artifact_id does not match content"*.
- **`b4_selection.json` — the hash really is hand-rolled.** It carries an
  `artifact_id` of `0f87744727d1e12d...cff52` computed inline by
  `scripts/run_b4_search.py`, and no `fingerprint` field at all;
  `freeze.artifact_fingerprint()` over the same file yields a different value,
  `4b0b1c47d50360ad...daad`. `verify_artifact()` fails with *"stored fingerprint
  None != recomputed 4b0b1c47d50360ad"*. **This one is a genuine Day-32 defect of
  this project's own code**, which computed the id inline instead of sealing
  through `freeze`.

So the frozen instance list is content-pinned and trustworthy; the B4 selection
artifact is the one whose integrity rests on an unverifiable inline hash.

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
   (exact file set + bytes)". No such per-instance hash exists. Relatedly, the
   report's claim that B0's two fingerprints are "both consistent with the frozen
   B0 baseline" asserts a check no artifact supports (see §4). The precise
   position is set out in §6.1.

### 6.1 How EXP-005 instances are actually frozen

> **`exp005_instances.json` freezes identity tuples, not content fingerprints.**

Precisely:

- **The queue is built from the frozen identity tuple**
  `(dataset_seed, family, scale, split, unseen_dimension)`. Those five fields are
  the complete per-instance record; no instance carries a content hash.
- **The observation records carry a `dataset_fingerprint`** — `030fda48...688b`
  for all 7 runs — produced by the runner at execution time from the dataset it
  actually read.
- **That relationship is an observation-level provenance property, not a
  verification against the freeze artifact.** The observation fingerprint does
  **not** demonstrate that the frozen instance artifact contains that value,
  because the artifact contains no such field. There is no frozen counterpart to
  compare it against.
- **One artifact-level `fingerprint` does exist** at the top level of
  `exp005_instances.json` (`1c33975aebf813023777a209165e3aa5ee8b66fe61ae5eefa80337750787c815`),
  recorded identically in the dry slice's `spec.json` and `summary.json`. It
  covers the artifact as a whole and **is a genuine content pin**: it reproduces
  bit-identically from `freeze.artifact_fingerprint()` (see §5). It is, however,
  **not** a per-instance dataset hash — it pins the identity-tuple list as
  written, not the bytes of any dataset on disk. So it cannot be used to verify
  that the dataset actually read at run time is the one intended; that gap is
  what the bullet above describes.

No fingerprint field was added to the instance-freeze artifact. Changing that
artifact is not authorized by any current decision, and it has already been
consumed by an executed TEST slice.

### 6.2 A correction to this correction

The first version of this corrected record (commit `feb5a16`) itself asserted,
twice, that `exp005_instances.json`'s fingerprint "could not be reproduced from
its content by file-bytes or canonical-JSON hashing, so its derivation is
unknown" and that it "should not be cited as a verified pin". **That was wrong.**
The fingerprint reproduces bit-identically from the project's own
`freeze.artifact_fingerprint()`; the failed reproduction attempts had simply
omitted the `_FINGERPRINT_EXCLUDED` keys (`artifact_id`, `fingerprint`,
`created_utc`) that the function excludes. The same version wrongly attributed
"hand-rolled hashing" to both failing artifacts, which is true only of
`b4_selection.json`.

The error is recorded rather than quietly overwritten because it is the same
failure mode this document was written to correct: **asserting a negative from a
failed personal attempt instead of consulting the authority that already exists
in the repository.** The corrected position is in §5. Net effect on the
conclusions: `exp005_instances.json`'s integrity is *better* than the first
correction claimed, and `b4_selection.json`'s is unchanged.

An adversarial verification pass over this record confirmed, independently, that
all ten full-length hashes are exactly 64 characters and byte-identical to their
artifacts, that `resolve("B1").config_fingerprint` equals the applied value, and
that B1's `selection_artifact_id` equals `baseline_selection.json`'s
`artifact_id`. One of that pass's four checks (scope and preserved findings)
failed on a network error and did **not** run; the scope claims in §7 therefore
rest on the primary verification recorded here, not on an independent second
reading.

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
