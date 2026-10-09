# D-NEW-05 | 2026-10-08/09 | Engineering changes for transcription into the decision log

**Status:** IMPLEMENTED in the working tree on the owner's instruction of 2026-10-08 and NOT YET COMMITTED.
This packet records the changes so that the owner can transcribe them as a decision. None changes a
result, a verdict, a frozen analyzer, a frozen driver, a ledger or a manifest.

## Changes

| File | Change | Why | Verified |
|---|---|---|---|
| `tests/unit/conftest.py` (new) | Collection hook. Skips 38 named unit tests, with a reason naming the missing input, when their inputs are absent: 17 need raw research records, 21 need the generated datasets. Prints a summary line. | On a fresh clone these tests failed with `FileNotFoundError`, indistinguishable from defects. Test bodies are untouched because `DECISIONS.md` cites their line numbers. | Recording machine: unchanged results (no skip added). Fresh clone: 0 failed, 38 skips with reasons. |
| `scripts/generate_dataset_matrix.py` | Creates the data root before the disk check; sizes the check to the requested datasets (estimate + margin clamped to 1–10 GiB; the full matrix still needs the original 40 GiB); exits 0 when every *requested* dataset is valid. | It crashed on a new `SPARKRL_DATA_ROOT`, exited 1 after a successful single-dataset run, and demanded about 40 GiB for 36 MB. | 6 new unit tests; real runs in a scratch clone: new data root created, 1.2 GiB required, exit 0. |
| `tests/unit/test_generate_dataset_matrix.py` (new) | Hermetic tests: missing root, single dataset (exit 0), repeated generation (no regeneration), failed dataset (exit 1), full matrix, insufficient disk (exit 2), request-sized requirement. | Requested regression tests. | 6 passed. |
| `scripts/verify_reproducibility.py` | New I0 integrity checks: EXP-013/014 artifact self-hashes, analysis-code digests against the code, frozen policy fingerprints. New EXP-013/014 L1 input digests and L2 re-derivation through the analyzers' own `analyze()`, in memory. New `--integrity-only` mode for fresh clones. A missing raw record is now a named FAIL instead of a traceback; it is still never a SKIP. | The headline experiment was outside the harness, and the script crashed on a fresh clone. | Recording machine: 25/25 PASS (EXP-013 and EXP-014 re-derived content-identically). Fresh clone: `--integrity-only` 7/7 PASS; the default mode reports named FAILs. |
| `scripts/env_check.py`, `src/sparkrl/utils/envcheck.py` | Default no longer writes; `--write-report` regenerates `docs/ENVIRONMENT_REPORT.md` and `docs/environment_report.json`. The report's regeneration hint is updated for future regenerations. | A new user's environment check overwrote the study machine's committed record. | Fresh clone: 14 checks PASS, tracked files untouched. |
| `scripts/spark_smoke_matrix.py` | Same default and `--write-report` flag for `docs/smoke_matrix_report.*`. | Same reason. | Compiles; not executed (it starts Spark). |
| `scripts/analyze_q0_provenance.py` (new) | Zero-Spark analysis behind [D-NEW-01](D-NEW-01_q0_test_time_provenance.md); writes [`evidence/q0_provenance.json`](evidence/q0_provenance.json). | Quantifies where test-time choices come from. | 43/43 test cells identical to the Q₀-only policy. |
| `README.md`, `docs/REPRODUCE.md`, `docs/PROJECT_HISTORY.md`, `docs/decisions/*`, `docs/research/NOVELTY_POSITIONING.md`, `experiments/README.md` | Documentation. | Publication readiness. | Link and anchor checks pass. |

## What was not touched

`DECISIONS.md`, `docs/PLAN.md`, `docs/research/CLAIM_EXPERIMENT_MAP.md`, everything under `results/` (hashed
before and after: identical), `models/policies/`, the frozen analyzers (`scripts/analyze_exp013.py`,
`scripts/analyze_exp014.py`, `src/sparkrl/analysis/inference.py`), the experiment drivers, and the
manuscripts.

## Governance notes

- `scripts/validate_day31.py` check 27 lists uncommitted modifications to tracked files outside its
  signed allowlist, so it reports the modified files until they are committed. The allowlist must not be
  extended to silence it.
- The validators' unit-test gates (`validate_day30.py` check 23, `validate_day31.py` check 35) run
  `pytest tests/unit`. On the recording machine the new conftest skips nothing, so they run the same
  tests plus the 6 new generator tests.
- **Executions outside the study record.** Verification ran only in scratch clones under `C:\sc8`, each with
  its own `SPARKRL_DATA_ROOT`: the EXP-012 demo (5 runs) and one workload run on 2026-10-08, two
  single-dataset generations, and one environment-check Spark session. None wrote to this repository's
  `results/`, its SC6 ledger, or the study's event-log directory (verified by hash manifest and an
  event-log count).

## Proposed decision text

> The engineering changes listed in D-NEW-05 are adopted. They change no result, verdict, ledger, manifest,
> frozen analyzer or frozen driver. `scripts/verify_reproducibility.py` now has 25 checks and an
> `--integrity-only` mode; records citing 16/16 stay true of their date.
