# D-NEW-02 | 2026-10-09 | Experiments that could measure an online-learning effect, and a stronger static reference

**Status:** PROPOSED. No execution is authorized and nothing here has been run.

## Why

[D-NEW-01](D-NEW-01_q0_test_time_provenance.md) shows that the confirmatory evaluation cannot attribute
anything to online learning: test episodes never reach a state whose choice training changed. The first
question a machine-learning reviewer will ask is "where is the learning contribution?". Today the only
honest answer is "none was measured".

There is descriptive evidence about the likely answer, in
[`evidence/q0_provenance.json`](evidence/q0_provenance.json), field `gt0_choices_vs_exp002_grid`. Online
training changed the greedy choice only in the positive-feedback states. On the training cells, the
EXP-002 grid measured those learned choices as **equal to or slower than** Q₀'s choice in every family:

| Training cell | Q₀ choice (grid median) | Learned positive-feedback choices, seeds 0 / 1 / 2 | Grid best |
|---|---|---|---|
| F1_agg small | G-p8-sp16 (2.10 s) | G-p8-sp16 / G-p4-sp64 / G-p4-sp32 | G-p8-sp16 (2.10 s) |
| F2_join medium | G-p8-sp16 (1.45 s) | G-p4-sp16 / G-p2-sp32 / G-p4-sp32 | G-p8-sp16 (1.45 s) |
| F5_mixed medium | G-p8-sp32 (4.13 s) | G-p4-sp16 / G-p4-sp32 / G-p8-sp32 | G-p8-sp32 (4.13 s) |

Each grid median rests on about two runs, so this is a pointer, not a test. The EXP-012 demo points the
same way, with one run per episode: on F5_mixed small, the learned positive-feedback choice (`G-p4-sp16`,
1.73 s and 1.77 s) was slower than Q₀'s (`G-p8-sp32`, 1.42 s). The prior expectation for an online-learning
effect is therefore null or negative. Measured properly, either outcome is publishable.

## Candidate experiments

| ID | Design | Runs (approx.) | Split / ledger | Value |
|---|---|---:|---|---|
| E1 | Q₀-only policy vs the trained policy under the frozen protocol | 0 | none | Already decided by configuration identity: 43/43 test cells identical (D-NEW-01). Report as a derived ablation. |
| E2 | **Learning-effect test.** The previous reward is carried into the state, as in training and the demo. Arms: (a) the frozen trained policy, greedy; (b) a feedback-agnostic Q₀ policy that uses Q₀'s choice in both feedback states, which is the "no online learning" counterfactual; (c) B1 as the static reference. Six-episode sequences, five independent sequences per cell. | about 665 (7 cells × 3 arms × 6 × 5, plus 35 B0 runs for reference times) | validation (seed 3), own ledger line, 0 charged to SC6 (EXP-009/014 precedent) | Directly answers "does online RL add value beyond its initialization?" |
| E3 | Continual adaptation: learning stays on during evaluation; regret against B1 over a job sequence | larger; design open | validation | Tests the self-adaptive claim itself; only after E2 |
| E4 | Per-cell exhaustive static oracle on a stratified subset of test cells (all 12 configurations) | about 480 (8 cells × 12 × 5) | test (re-opens the sealed split by decision) | Measures the headroom any adaptive method could exploit, and how far B1 and RL are from it |
| E5 | Bayesian-optimization or evolutionary baseline | — | — | Not recommended. With 12 discrete configurations, exhaustive search costs 12 runs per context and is exact; a reviewer gains nothing from BO here. |
| E6 | Larger action space (e.g. broadcast threshold, caching, memory fractions) | large | new study | Would make search non-trivial and BO/RL comparisons meaningful, but changes the study; not before submission |

Notes on E2:

- **Reference times.** Rewards, and hence the feedback state, need a reference time T_ref for each
  cell, and T_ref exists only for dataset seed 0. The validation cells therefore need one B0 block each
  (included in the count).
- **Pace.** EXP-013 and EXP-014 ran at about 45–65 s per run elapsed, so E2 is roughly 8–12 hours. Four
  cells instead of seven cut it to about 5–7 hours.
- **Hypothesis to pre-register (example).** The trained policy's median runtime over episodes 2–6 is at
  most 0.9 × that of the feedback-agnostic Q₀ policy on at least half the cells; test paired per cell with
  Holm correction (the DEC-053 machinery).
- **Validation-split caveat.** B1 was tuned on the validation split, so arm (c) is a reference there, not
  a fair competitor. The trained-versus-Q₀ contrast, which is the point, is unaffected.

## Options

- **A. No new experiments.** Report E1 and disclose the missing learning-effect measurement as a limitation.
- **B. Authorize E2** on the validation split, pre-registered, on its own ledger line.
- **C. B plus E4** (needs a separate test-crossing decision).

**Recommendation:** report E1 now (it costs nothing). If there is time for one experiment, choose E2; E4
is second priority. Do not add a Bayesian-optimization baseline or expand the action space before
submission; state in the paper why exhaustive static search is the right strong baseline for a
12-configuration space.

## Documents requiring synchronization (only if B or C is chosen)

`DECISIONS.md` (authorization), `experiments/registry.csv` or its successor, a pre-registration record in
`docs/research/`, a new driver and analyzer under `scripts/`, `docs/research/CLAIM_EXPERIMENT_MAP.md`,
`README.md` and `docs/REPRODUCE.md`.
