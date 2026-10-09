# D-NEW-04 | 2026-10-09 | Reproduction promises in the frozen plan, the experiment register, and an availability error in the claim map

**Status:** PROPOSED. `docs/PLAN.md`, `experiments/registry.csv` and `docs/research/CLAIM_EXPERIMENT_MAP.md`
are unchanged. `docs/REPRODUCE.md` was created and `experiments/README.md` was relabelled; both are
explanatory, not governed.

## Issues

1. **Plan promises that were not built.** `docs/PLAN.md` §27 promises one-command reproduction
   (`scripts/run_experiment.py`, `scripts/reproduce_all.sh`), a `docs/REPRODUCE.md` walkthrough, and a
   `results/EXP-XXX/<timestamp>/` layout. Only the walkthrough exists now (written 2026-10-09). The study
   used one frozen driver and one pre-registered analyzer per experiment, under
   `results/experiments/<study>/`. The plan is frozen: many decisions assert "`docs/PLAN.md` = UNCHANGED".
2. **The register is the original plan.** `experiments/registry.csv` lists EXP-001 to EXP-012, all with
   status "planned". It has no rows for EXP-013, EXP-014 or the X-family pilots.
   `scripts/validate_research_problem.py` only checks that referenced IDs exist in it.
3. **Factual error in the claim map.** The provenance note at `docs/research/CLAIM_EXPERIMENT_MAP.md`
   line 85 says the EXP-002/005/009 raw records are committed and tracked, and that the harness verifies
   16/16 "from committed artifacts". In the published history only the EXP-002 raw record is tracked
   (`git ls-files results/experiments`). The harness needs the other raw records, which are git-ignored
   and pending the DEC-045 deposit. The owner's report draft repeats the error in its artifact-availability
   appendix.
4. **The X-family pilots cannot be re-run from the repository.** Their drivers were never committed; only
   their observations (local, untracked) and three analysis files (X6, X9, X10) exist.
5. **The harness changed.** `scripts/verify_reproducibility.py` now runs 25 checks (16 before, plus
   EXP-013/014 integrity and re-derivation) and has an `--integrity-only` mode ([D-NEW-05](D-NEW-05_engineering_changes_2026-10-08.md)).
   Records that cite "16/16" remain true of their date.

## Options

- **Plan.** A: amend §27 by decision, recording that the per-study drivers plus `docs/REPRODUCE.md`
  replace the promised one-command tooling and that results live under `results/experiments/<study>/`. B:
  build a `reproduce_all` wrapper. Not needed: `scripts/verify_reproducibility.py` already is the
  zero-Spark entry point, and a wrapper that re-runs every campaign would mean days of Spark time.
- **Register.** A: keep `registry.csv` as the frozen plan register, now labelled as such in
  `experiments/README.md`. B: add EXP-013/014 and the pilots and update the statuses (safe for the
  validator, which only checks that IDs exist).
- **Claim map.** Correct the line-85 note. Proposed wording:

> Committed + tracked: the reproducibility harness, `results/evaluation/*.json` (including the EXP-013 and
> EXP-014 analyses and the X6/X9/X10 pilot analyses), the EXP-002 raw record, figures, the decision log,
> manuscript sources and research drafts. Held for the DEC-045 deposit: every other raw observation
> (EXP-001, -005, -006, -009, -013, -014, the training runs and the X family). The harness passes 25/25 on
> the recording machine; on a fresh clone only `--integrity-only` (7 checks) can run until the deposit is
> installed. The X-family drivers are not in the repository.

## Recommendation

Plan option A, register option A (B optional), and the claim-map correction, in one decision.

## Documents requiring synchronization

`DECISIONS.md`, `docs/research/CLAIM_EXPERIMENT_MAP.md` (line 85) and the report draft's
artifact-availability appendix. `docs/PLAN.md` itself stays frozen: the amendment lives in the decision.
