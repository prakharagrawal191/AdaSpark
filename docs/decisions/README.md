# Owner decision packets

These packets prepare decisions that only the research owner can take. **None of them is a decision.**
Each one sets out an issue found in the publication-readiness review of 2026-10-08, the evidence, what
the governed record currently says, the options and a recommendation. A packet takes effect only when
the owner transcribes a chosen option into [`DECISIONS.md`](../../DECISIONS.md) as a numbered, signed
entry (the next free number at the time of writing is DEC-056). Until then:

- `DECISIONS.md`, `docs/PLAN.md`, `docs/research/CLAIM_EXPERIMENT_MAP.md` and the manuscripts are
  unchanged on the basis of these packets;
- the README and `docs/REPRODUCE.md` describe the findings as open, with their evidence;
- no experiment proposed here has been run.

| Packet | Question for the owner |
|---|---|
| [D-NEW-01](D-NEW-01_q0_test_time_provenance.md) | How should H2 be interpreted now that every test-time RL choice is shown to come from the offline Q₀ or a tie-break? |
| [D-NEW-02](D-NEW-02_learning_effect_and_baseline_experiments.md) | Should an experiment that can measure an online-learning effect (and a stronger static baseline) be authorized? |
| [D-NEW-03](D-NEW-03_ai_assistance_disclosure.md) | DEC-045 D4 requires an AI-assistance disclosure in the README; the README has none. Restore it or supersede D4? |
| [D-NEW-04](D-NEW-04_reproduction_plan_and_registry.md) | The frozen plan promises reproduction tooling that was never built. Amend the plan? |
| [D-NEW-05](D-NEW-05_engineering_changes_2026-10-08.md) | Record and adopt the engineering fixes of 2026-10-08. |
| [D-NEW-06](D-NEW-06_manuscript_claim_alignment.md) | Which manuscript sentences to correct, and how. |

Evidence produced for these packets is in [`evidence/`](evidence/). It was produced with 0 Spark
executions, charges nothing to SC6 and touches no test-split run.
