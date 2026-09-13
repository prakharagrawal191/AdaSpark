# Day 31 - Evaluation Harness Audit

> **Day 31 · Status: COMPLETE · Type: harness/freeze day (PLAN line 277)
> · Spark executions: 0**
> Authority: `docs/PLAN.md` line 277 (`| 31 | Eval harness + B1/B2 | frozen
> test set; static baselines tuned on validation | configs frozen |`),
> section 17 (baselines B1/B2 definitions), section 18 (split), section 23
> (repetitions), line 310 (EXP-003 register row, ~30 estimate); `DECISIONS.md`
> DEC-011 (multi-step NOT enabled, Day-30 mode gate resolves NO); prior
> Day-28/29/30 audits and their machine-readable artifacts.
>
> **No Spark executions were performed during Day 31.** The evaluation
> harness is built, the TEST-split identity is frozen, the evaluation
> specification is declared, and the B1/B2 selection machinery is proved
> to accept validation observations and structurally reject all others.
> Validation measurement, B1/B2 empirical selection, EXP-003 comparison
> and TEST execution remain **PENDING** operator action on later days.
>
> **Artifacts (fingerprinted, immutable):**
> - `results/evaluation/evaluation_spec.json` artifact_id=`e9c4777047cf4454`
> - `results/evaluation/test_freeze.json` artifact_id=`699e98dfe6e706ce`
>   manifest_fingerprint=`cb829aec95346502` cell_count=43

# Day 31 - Evaluation Harness Audit

> **Day 31 · Status: COMPLETE · Type: harness/freeze day (PLAN line 277)
> · Spark executions: 0**
> Authority: `docs/PLAN.md` line 277 (`| 31 | Eval harness + B1/B2 | frozen
> test set; static baselines tuned on validation | configs frozen |`),
> section 17 (baselines B1/B2 definitions), section 18 (split), section 23
> (repetitions), line 310 (EXP-003 register row, ~30 estimate); `DECISIONS.md`
> DEC-011 (multi-step NOT enabled, Day-30 mode gate resolves NO); prior
> Day-28/29/30 audits and their machine-readable artifacts.
>
> **No Spark executions were performed during Day 31.** The evaluation
> harness is built, the TEST-split identity is frozen, the evaluation
> specification is declared, and the B1/B2 selection machinery is proved
> to accept validation observations and structurally reject all others.
> Validation measurement, B1/B2 empirical selection, EXP-003 comparison
> and TEST execution remain **PENDING** operator action on later days.

## 1. Objective

Execute and document the task named by frozen `docs/PLAN.md` line 277:

```
| 31 | Eval harness + B1/B2 | frozen test set; static baselines tuned on
                         validation | configs frozen |
```

Day 31 is a **harness/freeze day**, not an execution day. Its frozen
deliverable is the string in the success column - **configs frozen** -
and the machinery that selects B1/B2 on the validation split. It runs
no Spark, executes no validation grid, selects no empirical baseline,
and opens no test cell. This document is the evidence record behind
that harness.

Nothing here is a claim about whether B1 beats B0, whether B2 beats B0,
whether any strategy generalizes, or whether the research hypothesis
succeeds. Section 11 states exactly what is and is not claimed.

## 2. What "configs frozen" means (frozen text, with line references)

**PLAN section 17, lines 153-154 - the two frozen static baselines:**


## 3. Completed today

### 3.1 Evaluation harness (`src/sparkrl/evaluation/`)

Five modules, each owning one concern and nothing else:

| Module | Responsibility | What it deliberately does NOT own |
|--------|---------------|----------------------------------|
| `spec.py` | scope, split authorization, cost projection, frozen definitions | Spark sessions, timing, event-log parsing |
| `selection.py` | B1/B2 selection on validation observations only | file I/O, Spark, any split other than validation |
| `orchestration.py` | queue shape and execution authorization | session creation, warm-up, the timing clock |
| `freeze.py` | immutable fingerprinted artifacts (write once, verify) | measurement, metrics, any result data |
| `__init__.py` | package exports | (re-exports only) |

### 3.2 Split authorization

`split_of` (`sparkrl.experiments.spec.split_of`) remains the **single
authority** and is NOT re-implemented or weakened. The evaluation package
adds an explicit authorization layer on top:

- `authorize_validation_cell(...)` admits VALIDATION only
- `authorize_test_cell(...)` admits TEST only (but execution is still sealed)
- `authorize_cell(required_split, ...)` the general guard

A non-validation cell in the selection path raises
`SplitAuthorizationError` before any arithmetic happens. This is
**structural**, not documentary: the guard is code that runs, not prose
that hopes.

### 3.3 Validation-only baseline selection

`select_baselines(observations)` accepts only `ValidationObservation`
values and runs every one of them through `authorize_validation_cell`
then `split_of` before any arithmetic happens. A single TEST or TRAIN cell
in the input raises `SplitAuthorizationError` and no selection is
produced. There is no flag, no keyword and no code path that admits a
non-validation cell.

A **pre-declared deterministic tie-break rule** is documented: lowest
frozen grid index wins an exact validation tie. This rule was declared
on Day 31 BEFORE any validation observation exists. It is NOT a
PLAN-frozen rule (the plan freezes no such rule). It is applied ONLY
when actual candidate results tie during a future selection execution.

### 3.4 TEST-split identity freeze

`test_freeze.json` (built by `freeze.build_test_freeze()`) contains only:

- exact TEST cells
- family, scale, seed
- split tag, dataset ID, dataset fingerprint
- schema/version, manifest fingerprint
- expected future evaluation scope (EXP-005/EXP-006)
- provenance

It contains **NO** execution times, rewards, baseline results, RL
results, or tuning metrics. It is the identity of the test set, not
any measurement from it.

### 3.5 Evaluation specification

`evaluation_spec.json` (built by `freeze.build_evaluation_spec_artifact()`)
declares what a later day WILL run:

- B0 (pinned reference, `configs/baseline_b0.yaml`)
- B1 = validation-selected static global baseline
- B2 = validation-selected per-family baseline
- future TEST evaluation scope (EXP-005/006)
- 5 repetitions (PLAN section 23, frozen)
- authoritative `execution_time_s` (runner clock)
- AQE OFF (PLAN section 7, frozen)
- warm-up policy
- cost projection with the documented discrepancy

Where the actual B1/B2 configuration is not yet measured, the artifact
uses `selection_status: pending`, NOT a fabricated configuration.

### 3.6 Baseline selection artifact (PENDING)

### 3.7 Artifact immutability

All three artifacts (`evaluation_spec.json`, `baseline_selection.json`,
`test_freeze.json`) follow the frozen `sparkrl.agent.policy_store`
pattern:

- SHA-256 content fingerprint over canonical JSON
- identity = fingerprint
- timestamps excluded from identity
- a differing overwrite raises `ArtifactExistsError`
- tampering is detected by `verify_artifact()` then `ArtifactCorrupt`

### 3.8 Cost projection

The projection is **computed, never executed**. The independently
verified calculation:

| Stage | Computation | Runs |
|-------|------------|------|
| B1/B2 selection | 12 configurations x 8 cells x 1 rep | **96** |
| EXP-003 B0/B1/B2 comparison | 3 strategies x 8 cells x 5 reps | **120** |
| Combined | 96 + 120 (different rep counts, no reuse) | **216** |
| PLAN line 310 estimate | | **~30** |
| **Discrepancy** | 216 - 30 | **186** |

The discrepancy is a **planning-budget discrepancy**: the independently
verified combined projection is 216 runs while PLAN line 310 estimates
~30. The gap is reported, not resolved: how much of it to spend is an
operator / supervisor decision, not a Day-31 code change. PLAN.md is
NOT changed.

### 3.9 Validator and tests

- `scripts/validate_day31.py` checks all 18 acceptance gates (D31-01
  through D31-18)
- `tests/unit/test_day31_evaluation.py` covers split authorization,
  validation-only selection, TEST rejection, TRAIN rejection, tie
  fixture, immutable test freeze, immutable specification,
  candidate-grid fingerprint, cost calculation, cost projection
  reproducibility, no fabricated baseline, future TEST execution
  refusal
- `tests/unit/test_evaluation_harness.py` covers the same guarantees
  from a different angle

All tests are zero-live-execution.

## 4. Not completed today

The following are explicitly **NOT** completed and remain pending
validation execution on later days:

- **Validation measurement** - no validation grid was run
- **B1 empirical selection** - no configuration was selected
- **B2 empirical selection** - no per-family configuration was selected
- **EXP-003 comparison** - no B0/B1/B2 comparison was run
- **TEST execution** - no test cell was opened
- **RL-vs-baseline comparison** - no comparison was made

## 5. TEST set

The frozen TEST identity (`test_freeze.json`) contains 43 cells
derived from `split_of(...) == "test"`:

- All families x large scale x seeds {3,4} (unseen scale)

## 7. Structural leakage test

The selection API structurally rejects non-validation observations:

- validation observation accepted (when all cells are in scope)
- TRAIN observation raises `SplitAuthorizationError`
- TEST observation raises `SplitAuthorizationError`

The selection function validates `split_of(...) == "validation"` for
every supplied observation BEFORE any arithmetic happens. An invalid
observation raises `SplitAuthorizationError` (a named exception), not a
generic error. This is enforced by code, not by comments.

## 8. No TEST execution

The Day-31 harness contains a future TEST execution interface
(`execute_test_run`). That interface is inert today. Any attempt to
execute TEST during Day 31 raises `TestSplitSealed` (the project's
authorization error). `split_of()` is NOT weakened. The existing
split guards are NOT bypassed.

## 9. Training budget distinction

**SC6 training budget**: <=500 Spark executions (tabular Q training,
cached, offline-init). This is a SEPARATE register line from EXP-003.

**EXP-003 validation/evaluation executions**: 216 projected runs
(96 selection + 120 comparison). This is a SEPARATE register line
(PLAN line 310) and is NOT charged to the frozen 500-execution
TRAINING cap (SC6).

The 500 budget does NOT protect EXP-003 unless the repository
explicitly says so. The repository does NOT say so.

## 10. Repository state

No frozen source was modified. No split guard was modified. No PLAN
was modified. No DECISIONS was modified. No EXP-002 artifact was
modified. No Day-28/29/30 artifact was modified. No TEST execution
artifact was generated. No large Spark log was generated.

New files created:
- `src/sparkrl/evaluation/spec.py`
- `src/sparkrl/evaluation/selection.py`
- `src/sparkrl/evaluation/orchestration.py`
- `src/sparkrl/evaluation/freeze.py`
- `src/sparkrl/evaluation/__init__.py`
- `scripts/run_evaluation.py`
- `scripts/validate_day31.py`
- `tests/unit/test_day31_evaluation.py`
- `tests/unit/test_evaluation_harness.py`
- `docs/research/DAY31_EVAL_HARNESS_AUDIT.md` (this document)

DEC-011 is preserved (multi-step NOT enabled). Day-29 M8 artifact is
untouched. AQE is unchanged (OFF). RL policy is untouched. No
multi-step RL. No cache changes. No EXP-005/006 execution.

## 11. Research integrity

Day 31 establishes infrastructure and freezes the future evaluation
protocol. It makes NO research claim. Specifically, it does NOT claim:

- B1 is better than B0
- B2 is better than B0
- B1/B2 beat B0
- RL beats baselines
- TEST generalization
- Statistical significance
- Research hypothesis success

## 12. Limitations

- No validation measurements exist; B1/B2 selection is pending
- The PLAN ~30 estimate discrepancy (186 runs) is unresolved
- The test split remains sealed; EXP-005/006 are not run
- The evaluation harness delegates future execution to the existing
  experiment runner; it owns no Spark session, timer or parser

## 13. Exact next task

Read `docs/PLAN.md`.

Do NOT assume Day 32 until the baseline-selection / test-execution
prerequisites are genuinely satisfied.

- F4_ski (unseen family) x all scales x seeds {0,1,2,3,4}
- F5 with unseen parameters (declared)

The exact TEST cells match the repository split definitions
(`sparkrl.experiments.spec.split_of`). No TEST results appear in any
baseline-selection artifact.

## 6. B1/B2 definitions

**B1 = Static global**: one configuration tuned on the validation split,
used everywhere. Selected by median execution time over the 8
validation cells at 1 repetition.

**B2 = Static per-family**: best validation-grid configuration per
family. Selected independently for each family that has validation
cells.

**Selection status**: PENDING_VALIDATION_EXECUTION. No configuration
has been selected. No configuration will be selected until the
validation grid is actually run and its observations fed to
`select_baselines()`.


Because validation measurement has NOT happened, the baseline-selection
specification clearly distinguishes:

`selection_status = PENDING_VALIDATION_EXECUTION`

It contains: B1 definition, B2 definition, candidate grid, validation
cell set, selection metric, aggregation method, tie-break rule
(documented as Day-31-declared, not PLAN-frozen), required execution
count, provenance, schema version.

It does NOT contain any invented selected configuration. No action or
configuration is assigned merely because its index is lowest. The
deterministic lowest-grid-index rule applies ONLY when actual candidate
results tie during a future selection execution.

> B1 | Static global     | one config tuned on validation, used everywhere
> B2 | Static per-family | best validation-grid config per family

**PLAN section 18, line 163 - the split B1/B2 are tuned on:**

> Validation = same families x seed{3} (B1/B2 tuning + hyperparameters)

**PLAN section 23 - repetitions:**

> "all evaluation = 5 repetitions x fixed seeds, medians analyzed"

**PLAN line 310 - EXP-003 in the experiment register:**

> `| EXP-003 | support RQ2 | B1/B2 beat B0 | validation split | B0,B1,B2 | ~30 | frozen B1/B2 | planned |`

**PLAN line 312 - EXP-005 (the TEST execution Day 31 does NOT perform):**

> `| EXP-005 | RQ2 (H2,H3) | RL >= heuristics >= default | Test split (7 instances) | RL vs B0,B0',B1,B2,B3,B4 | ~245 | SC2-SC4 | planned |`

**ARCHITECTURE_FREEZE line 73 - TEST is sealed until EXP-005/006:**

> "Frozen policies evaluated once on test (EXP-005/006)"
