# DEC-038 | 2026-09-20 | 2026-09-20 smoke ledger classification — the five completed smoke TRAIN executions are CHARGED; ledger 483/500, remaining 17; charged-but-unauthorized (Day 38)

**Decision ID:** DEC-038
**Date:** 2026-09-20
**Scope:** Classification of the 2026-09-20 smoke run directories against the SC6 ledger, and the consequential validator/test terms. **Nothing else.**
**Status:** DECIDED — the same treatment DEC-033 gave the 2026-09-19 six, applied to the 2026-09-20 five.
**Standalone decision artifact.** The authoritative log entry is this appended DEC-038 section of `DECISIONS.md`; `docs/research/DEC_038_20260920_SMOKE_LEDGER_CLASSIFICATION.md` carries the same decision content, self-contained (the DEC-031/DEC-032 convention).
**Supersedes nothing.** DEC-011, DEC-026, DEC-030, DEC-031, DEC-032 and DEC-033 are unchanged. DEC-033's figures remain correct **as of its own date** and are not edited.

> **This entry performs 0 Spark executions, trains nothing, executes no TEST, creates no run directory, and modifies no manifest, no result artifact and no prior decision entry.**
> **EXP-008 execution authorization = NO. A5 = DISABLED. TEST = NOT AUTHORIZED. SC6 cap = 500, NOT raised. `docs/PLAN.md` = UNCHANGED.**

---

**0 — Identifier resolution.** `DECISIONS.md` headings run DEC-001…DEC-026 and DEC-031…DEC-037 (DEC-030 is recorded outside the ledger, per DEC-031 §0). No DEC-038 artifact exists. The next sequential identifier is **DEC-038**.

**1 — Scope.** (a) whether the 2026-09-20 smoke executions are charged to SC6; (b) the resulting canonical ledger; (c) the consequential validator term and test pin. Not in scope: any EXP-008 methodology, implementation or authorization question; the SC6 cap; `docs/PLAN.md`; the zero-live counting rule (DEC-037 §3).

**2 — Evidence: the six 2026-09-20 smoke directories, read from their own manifests.**

| Directory | Started (UTC) | Status | exit | Live | `code_version` |
|---|---|---|---|---|---|
| `train-a0-d0-20260920T072732Z` | 07:27:32 | failed | 1 | **0** | `c2e980a` |
| `train-a0-d0-20260920T073748Z` | 07:37:48 | completed | 0 | **3** | `c2e980a` |
| `train-a0-d0-20260920T073953Z` | 07:39:53 | completed | 0 | **3** | `c2e980a` |
| `train-a0-d0-20260920T074224Z` | 07:42:24 | completed | 0 | **3** | `c2e980a` |
| `train-a0-d0-20260920T075301Z` | 07:53:01 | completed | 0 | **3** | `c2e980a-dirty` |
| `train-a0-d0-20260920T075643Z` | 07:56:43 | completed | 0 | **3** | `c2e980a-dirty` |

Five completed runs at 3 live TRAIN executions each = **15**. The sixth aborted at startup and contributes **0**. `code_version` places all six **after** commit `c2e980a` (the DEC-033 commit). Separately, `docs/environment_report.json` records `generated_utc: 2026-09-20T08:00:49Z` with `spark_version 3.5.9` and `python 3.11.9` — the canonical `sparkrl_env311` stack, immediately after the run window.

**3 — Canonical arithmetic.** DEC-033 recorded **468 / 32**. Adding the five completed runs:

`232 (Day-29, DEC-011 §7) + 84 (B4, DEC-016 C / DEC-017) + 20 (EXP-001) + 126 (EXP-007, DEC-026) + 6 (2026-09-19 smoke, DEC-033) + 15 (2026-09-20 smoke, this entry) = **483**`

`500 − 483 = **17 remaining**`. Measured independently: `ledger_from_manifests()` returns **(28 manifests, 483 live)**. The residual against the DEC-033 chain was exactly **15** before this entry, which is the quantity this entry classifies and no other.

**4 — The charging rule applied is the standing one; no new category is invented.** DEC-031 §5 **charged-category 1** covers *"TRAIN live executions — every real environment transition consumed by a training run's budget counter"*, and **charged-category 3** covers smoke executions inside charged TRAIN accounting. The five completed runs are real smoke TRAIN executions with `status: completed` and non-zero `budget.live_executions`; they satisfy both on the evidence alone. The aborted sixth is a **charged row at 0** under charged-category 3's second sentence (*"a smoke attempt with 0 live executions is still a charged row at 0"*). Nothing in DEC-031 §5's NOT-CHARGED list reaches them: they are not planned-but-unexecuted rows, not cache hits, not EXP-003 validation, and not TEST — the TEST seal is untouched and these executed TRAIN cells only.

**5 — Authorization status: CHARGED-BUT-UNAUTHORIZED.** No decision in `DECISIONS.md` (DEC-001 … DEC-037) names, scopes or approves any 2026-09-20 smoke execution. They post-date every recorded authorization. They are counted against the cap and disclosed; they are **not** deleted, because deleting an execution record would falsify the register this ledger exists to protect. **Any future smoke execution requires its own explicit authorization.** This is the identical status DEC-033 assigned the 2026-09-19 six, applied on identical evidence.

**6 — Causation, stated as far as the evidence supports and no further.** The runs were **not** produced by the governance audit in progress at the time: none of `scripts/validate_rl_environment.py`, `scripts/validate_rl_agent.py`, `scripts/validate_rl_training.py`, `scripts/validate_day28.py`, `scripts/validate_day29.py`, `scripts/validate_day30.py` or `scripts/validate_day31.py` opens a Spark session or invokes a training driver, and the only test target exercised by that work was `tests/unit`, which executes no Spark. The `code_version` values and the 08:00:49Z environment-report regeneration are consistent with an operator working session on the canonical venv. **This entry attributes the runs to no person and invents no narrative beyond the artifacts.** The DEC-037 §4 live-Spark test gate remains the standing mitigation for the accidental-execution path.

**7 — Consequential implementation (performed with this entry, in the amend-and-ratify-concurrently shape of `9e83742` / DEC-018 Decision E).**

1. `scripts/validate_day31.py` check 22: the charged-smoke subtrahend is extended from DEC-033's 6 to **21** (`6 + 15`). Every contributing manifest is **named explicitly** and must be `status=completed` with exactly 3 live executions; the total is a **named, bounded constant** recorded by DEC-033 and this entry. It is **never** computed by re-summing the manifests that produce `live_total` — the self-cancelling anti-pattern DEC-032 §6 forbids. An additional completed smoke manifest, or a changed live count in any named directory, leaves the residual non-zero and FAILS loudly. The aborted zero-live rows are deliberately absent from the list: they charge 0 and, under DEC-037 §3, count toward no manifest-COUNT invariant.
2. `tests/unit/test_exp001_maintenance.py`: the live-tree pin is set to **483 / 17** and **restored to an exact equality**. It had been relaxed to `assert live <= CAP`, which cannot fail on an unauthorized execution and therefore detects nothing — the saturation DEC-032 §6 forbids. That relaxation is **recorded and reverted**, not carried forward. The hermetic fixture-tree assertions remain at 336 and are untouched.

**8 — Effect on DEC-034 … DEC-037, which were drafted hours earlier against 468/32.** Those four entries were drafted before this run window was discovered and cite **468 / 32** as the then-current ledger. The canonical figure at signature is **483 / 17**. A supersession note is appended to each; none of their conclusions depends on the difference, and each states why. In particular **DEC-034's zero-charge scope resolution is unaffected and is strengthened**: a charged requirement of **0** satisfies any headroom, and the 28-execution single-epoch alternative DEC-034 §7 rejected no longer fits at all (28 > 17), so the rejected option is now foreclosed by arithmetic as well as by design.

**9 — What this entry does NOT decide.** It does not raise the SC6 cap (500, unchanged). It does not authorize any execution, retroactively or prospectively. It does not resolve the zero-live counting question beyond DEC-037 §3's resolution. It does not amend `docs/PLAN.md`. It does not alter DEC-033's figures, which remain correct as of DEC-033's date. It does not attribute the runs to any person. It makes no research claim and grades nothing.

**Status.** **DECIDED.** The five completed 2026-09-20 smoke TRAIN executions are **CHARGED** under DEC-031 §5 categories 1+3; the aborted sixth is a **charged row at 0**; the canonical ledger is **483 charged of 500, remaining 17**, arithmetic `232 + 84 + 20 + 126 + 6 + 15 = 483`; the eight-plus-six runs' authorization status is **CHARGED-BUT-UNAUTHORIZED**. `SC6 cap = 500, NOT raised`. `EXP-008 execution authorization = NO`. `A5 = DISABLED`. `TEST = NOT AUTHORIZED`. `docs/PLAN.md = UNCHANGED`. Historical decisions (DEC-001 … DEC-026, DEC-030 … DEC-037) = **UNCHANGED**. Supervisor counter-signature: **PENDING** (conventional expectation only; never simulated; not a prerequisite under DEC-018 Decision A). **NO SUPERVISOR HAS REVIEWED THIS ENTRY.** A future review is a new entry; this one is never rewritten. **This entry performs 0 Spark executions and trains nothing.**

---

*Standalone companion artifact. The authoritative log entry is the appended DEC-038 section of DECISIONS.md; this document carries the same decision content, self-contained (the DEC-031/DEC-032 convention).*
