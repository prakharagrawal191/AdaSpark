# DEC-032 — DAY-31 VALIDATOR LEDGER RECONCILIATION (DEC-031 follow-up)

**Decision ID:** DEC-032
**Date:** 2026-09-18
**Scope:** Bookkeeping reconciliation of the Day-31 governance validator's pre-EXP-007 ledger assumption with the canonical DEC-031 ledger. **Nothing else.**
**Status:** DECIDED — a validator-only repair is AUTHORIZED for a separate later task; **NOT performed by this entry**.
**Standalone decision artifact.** The authoritative log entry is the appended DEC-032 section of `DECISIONS.md`; this document carries the same decision content, self-contained, so the decision also exists as an addressable artifact (the DEC-031 convention).
**Supersedes nothing.** DEC-030 and DEC-031 are unchanged; no historical decision entry is rewritten.

> **This entry performs 0 Spark executions, trains nothing, executes no TEST, creates no run directory, modifies no result artifact, no manifest, no budget, no ledger and no implementation file.**
> **EXP-008 execution authorization remains NO. A5 remains DISABLED. TEST remains NOT AUTHORIZED. `docs/PLAN.md` is UNCHANGED.**

---

## 0 — Identifier resolution

The highest formally used decision identifier is **DEC-031** (`DECISIONS.md` headings run DEC-001…DEC-026 plus DEC-031; DEC-030 is formally recorded outside `DECISIONS.md` as `docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md`). No `DEC-027`, `DEC-028`, `DEC-029`, `DEC-032` or `DEC-033` decision artifact exists; the prose references to "DEC-027..032 drafts" in the Day-37 preflight/methodology artifacts are **non-authoritative worktree drafts and occupy no identifier** (DEC-031 §0). The next sequential identifier is therefore **DEC-032**.

## 1 — The stale assumption being superseded

`scripts/validate_day31.py` check 22 ("22 Day-31 spent nothing; growth is authorized", lines 721–731) asserts a four-term conjunction:

```
n_manifests == DAY29_MANIFEST_COUNT (9)
AND unexplained == 0        # unexplained = live_total - DAY29_LIVE_EXECUTIONS(232) - b4_spent - exp001_spent
AND live_total <= LIVE_EXECUTION_CAP (500)
AND not ledger_errors
```

Two of the four terms now evaluate false against the live repository tree:

| Term | Expected | Actual | Status |
|---|---|---|---|
| `n_manifests == 9` | 9 | **14** | FALSE |
| `unexplained == 0` | 0 | **126** | FALSE |
| `live_total <= 500` | ≤ 500 | 462 | TRUE |
| `not ledger_errors` | no errors | no errors | TRUE |

The `unexplained` formula carries a subtrahend for the DEC-017/B4 spend (84) and for the EXP-001 spend (20), but **has never been given a term for EXP-007**. The residual 126 is exactly EXP-007's authorized live TRAIN spend.

**`DAY29_MANIFEST_COUNT = 9` is superseded in two independent ways** — and this entry records both:

1. **By a LATER zero-live artifact that is NOT part of the Day-29 baseline.** A tenth manifest directory appeared on **2026-09-16** — `results/training/smoke/train-a0-d0-20260916T043003Z` (`live_executions: 0`, `exit_code: 1`) — **three days after DEC-011 was signed on 2026-09-13**. It is therefore **not** a Day-29 baseline artifact. DEC-011 §7's baseline is, and remains, **9 manifests / 232 live executions**; this document does not reinterpret it. DEC-031 §3 later re-summed that same **232** total across **"10 manifests: 3+3+3+3+3+0+42+84+49+42"** — a *live-total* re-sum whose tenth row contributes **+0**. That wording must **not** be read as enlarging the signed Day-29 baseline to ten. DEC-031 §5 (charged category 3) supplies only a charging rule: *"A smoke attempt with 0 live executions is still a charged row at 0."* The row broke the manifest-**count** clause on 2026-09-16, one day before any EXP-007 execution, while adding nothing to live totals and charging nothing.
2. **By DEC-026's authorized execution.** EXP-007 added **4** manifests carrying 126 live executions.

**9 historical Day-29 baseline manifests + 1 later zero-live aborted-smoke manifest + 4 later EXP-007 manifests = 14 current manifest directories.** The count clause and the spend clause therefore decayed on different dates for different reasons, and any repair must address both.

## 2 — Canonical current values (from DEC-031; not re-derived here)

| Quantity | Canonical value | Authority |
|---|---|---|
| SC6 cap | **500** | `docs/PLAN.md` line 45; `configs/rl.yaml` line 17 — **not raised** |
| Historical Day-29 baseline | **9 manifests / 232 live** | DEC-011 §7, signed 2026-09-13 — unchanged, not reinterpreted |
| Later zero-live aborted-smoke manifest (2026-09-16) | **1 manifest / 0 live / 0 charged** | filesystem; DEC-031 §5 charged-category 3 gives the charging rule only; authorization attribution **ABSENT** |
| B4 equal-budget search | **84** | DEC-016 C / DEC-017 |
| EXP-001 noise calibration | **20** | `results/experiments/exp-001/spec.json` |
| EXP-007 A1/A2 | **126** over **4** manifests (35+35+35+21) | DEC-026 authorization scope; DEC-031 §3 |
| Current manifest directories | **14** | 9 baseline + 1 later zero-live + 4 EXP-007 |
| Live manifest sum | **358** | 232 + 126 |
| **Cumulative charge** | **462** | 232 + 84 + 20 + 126 (DEC-031 §§3–4) |
| **Remaining headroom** | **38** | 500 − 462 (DEC-031 §8) |

This entry **adds no new accounting and changes no figure**. Every value above is read from DEC-031.

## 3 — Semantic status: OBSOLETE ASSUMPTION, not a historical invariant

The repository has its own written discriminator between figures that legitimately go stale and figures that must track the ledger. `src/sparkrl/training/ablation.py` (lines 49–55) says of its `SC6_LEDGER_CITED = "336/500"` / `SC6_REMAINING = 164`: **"the ledger is never re-derived here."** `tests/unit/test_exp007_scope.py:76` pins the same pair with the comment **"# historical ledger, cited"**.

That is the line:

* **CITED figures** — `ablation.py`'s 336/500 and 164, DEC-023 §8's 184, DEC-025 §1's 164, DEC-024/DEC-026's 24 — record what the ledger was *as of a decision's date*. They are chronology. DEC-031 §7 classifies 164 as *"Historically correct for its date, now superseded … A time-slice, not an error; DEC-025 remains unedited."* **They must not be touched.**
* **RE-DERIVED assertions** — check 22 computes `ledger_from_manifests()` over the **live tree** every time it runs. It does not cite a figure; it measures one. A measurement whose expectation no longer matches reality is an obsolete assumption, not a preserved record.

Check 22's own in-file comment (lines 693–701) disclaims the frozen reading in terms: the assertion is that **"Day-31 created no training run and that every execution above the Day-29 baseline is attributable to those authorized spends, NEVER that the total is frozen."**

**What check 22 protects, conjunct by conjunct:**

| Conjunct | Protects | Status today |
|---|---|---|
| `n_manifests == 9` | manifest-count consistency, used as a run-existence proxy (catches a training run that charged **zero**) | **broken** — 14 ≠ 9 |
| `unexplained == 0` | unexplained-spend detection; the mechanism implementing protection against unauthorized execution | **broken** — 126 ≠ 0 |
| `live_total <= 500` | canonical current-ledger cap validation | intact (462 ≤ 500) |
| `not ledger_errors` | anti-undercount integrity guard on the computation itself | intact |

**None of the four conjuncts preserves a historical ledger figure.** `DAY29_LIVE_EXECUTIONS = 232` enters check 22 only as an **addend inside a decomposition**, never as an equality target. The strict historical-preservation pin — `live_total == DAY29_LIVE_EXECUTIONS` — lives in the *sibling* validator `scripts/validate_day30.py` check 14 (lines 398–404), which is a different artifact with a different meaning and is **out of scope here** (§7).

**The decisive finding — check 22 is SATURATED.** It fails today, and it would fail *identically* tomorrow if an unauthorized execution occurred (`unexplained` would read 127 instead of 126; `n_manifests` 15 instead of 14). Its pass/fail bit therefore carries **zero information** about unauthorized execution right now. Its protective function is not being preserved by leaving it red — it is **dead**. Repair restores it; inaction does not conserve it.

## 4 — Precedent: commit `9e83742` (and `715a7d3`)

Check 22 has been amended **twice**, both times because an authorized spend legitimately invalidated its expectation:

* **`9e83742`** (2026-09-14) — DEC-017's authorized B4 spend (+84) invalidated the then-current pin. The commit body is a written governance ruling: *"Day-31 check 22 asserted the ledger was frozen at the Day-29 figure, which DEC-017's authorized spend legitimately invalidated. **It now asserts what it always meant** — that DAY 31 spent nothing (manifest count unchanged) and that every execution above the baseline is attributable to the one authorized search … **An unexplained execution would still fail it.**"*
* **`715a7d3`** (2026-09-14, the DEC-018 commit) — added the `exp001_spent` subtrahend for EXP-001's +20 and relabelled the check.

**What the precedent establishes (METHOD — this transfers):** the sanctioned repair shape is to **RETAIN the historical constants** — `DAY29_MANIFEST_COUNT` and `DAY29_LIVE_EXECUTIONS` are byte-identical before and after `9e83742` — and to **DERIVE each authorized spend from its own artifact**, asserting a residual `unexplained == 0`. A constant is **never** re-pinned to a new total. The check keeps its teeth.

**What the precedent does NOT establish (AUTHORIZATION — this does not transfer):** `9e83742` touched exactly two files (`results/evaluation/b4_selection.json`, `scripts/validate_day31.py`) and carried **no `DECISIONS.md` entry at all**. `715a7d3` amended check 22 in the *same commit* that recorded DEC-018 Decision E, which adopted the amendment **retrospectively**. The repository's demonstrated practice is therefore **amend-first, ratify-concurrently-or-never** — *not* decision-first.

> **Correction of record.** An earlier Day-37 statement in this work-stream asserted that the `9e83742` repair "was previously done under an explicit decision." That is **wrong** and is corrected here: `9e83742` was never ratified by any decision entry. DEC-018 Decision E (`DECISIONS.md:1034–1039`) adopts *"the accompanying amendments to `scripts/validate_day31.py` and `scripts/validate_rl_environment.py`"* as *"operator-authorized Day-32 work"* — past tense, scoped to the EXP-001 change set, dated three days and one 126-execution experiment before the present staleness. It is the only decision sentence in the 2238-line ledger that names a validator.

**Two further facts distinguish today from the precedent:** (a) the precedent's defect was *undercounting* (B4 wrote an evaluation artifact invisible to the ledger), whereas EXP-007's 126 is fully counted and only the *expectation* is stale; (b) `9e83742` deliberately preserved `n_manifests == DAY29_MANIFEST_COUNT` intact and let that clause carry the whole "Day 31 spent nothing" meaning — and that is precisely the clause today's tree breaks, for a reason unrelated to EXP-007 (§1).

## 5 — Why a decision is required nonetheless, and what is NOT claimed

No existing decision authorizes this repair:

* **DEC-031** — the word "validator" appears in it **zero** times. §13: *"This entry freezes only the charging rule and the remaining capacity (B5) — nothing else … It is **not** the B6 implementation decision and **not** an authorization decision."* §14 sets Implementation authorization = **FALSE / NO**.
* **DEC-026** — its §11 "explicit and exhaustive" not-permitted list never mentions validators, ledger pins or downstream staleness. It anticipates none of this. (Its §7 recorded a pre-execution baseline of *"Full unit suite: 560 passed, 1 skipped, exit 0"*, which its own authorized 126 executions then falsified.)
* **DEC-018 Decision E** — past-tense, scoped to the EXP-001 change set (§4).
* **`scripts/validate_day30.py`** is named in **no** decision or research document.

**What this entry does not claim.** The repository contains **no written rule** requiring a decision before amending a validator. The only change-control rule (`DECISIONS.md:161–166`, restated by DEC-009) is scoped to *"substantive architectural changes"* and holds that *"Editorial clarifications need only a commit message note."* Moreover `scripts/validate_day31.py:842` pre-names `scripts/validate_day30.py,  # validator maintenance` inside check 27's authorized-modified-file allowlist — the repository's frozen-file governance already carries a standing category called **validator maintenance**, which has never been adjudicated. **DEC-032 does not decide whether that standing category would have sufficed.** It is recorded because the operator required an explicit decision before the validator is touched, and because an explicit record is strictly safer than relying on an unadjudicated carve-out.

## 6 — Authorized repair (NOT performed here)

Following DEC-025 §11's template — **Implementation consequence (NOT implemented here)** — the NEXT SEPARATE task is authorized to make a **validator-only, minimal, local** repair to `scripts/validate_day31.py` check 22 and the comments/docstring text that directly describe its assumptions (`:24–28`, `:96–101`, `:693–701`).

**The repair MUST:**

1. Follow the `9e83742` method: **retain** `DAY29_MANIFEST_COUNT` and `DAY29_LIVE_EXECUTIONS` as named historical addends; **add** an EXP-007 term; **derive** each authorized spend from its own artifact rather than hard-coding a new total.
2. Keep the residual assertion `unexplained == 0` as the detection mechanism.
3. Account for the manifest count as **9 historical Day-29 baseline + 1 later zero-live aborted-smoke manifest (2026-09-16) + 4 later EXP-007 = 14 current manifest directories**, preserving the distinction between the historical baseline, later manifests, live-execution totals and budget charging. It must **not** re-pin `9 → 14` as an opaque literal, and must **never** enlarge DEC-011's signed 9-manifest baseline. Because no written rule yet says whether a zero-live manifest counts toward a manifest-count invariant (§7.3), the repair must not silently assume one.
4. **Preserve the detection invariant below.**

**THE INVARIANT THAT MUST SURVIVE (binding):**

> After the repair, a live TRAIN execution that is **not attributable to a recorded authorization** must still make check 22 **FAIL loudly**. Concretely: with today's tree the check must evaluate `462 − 232 − 84 − 20 − 126 = 0` → PASS; with one additional unattributable execution it must evaluate to `1` → FAIL.

**Specific anti-pattern the repair MUST avoid.** The EXP-007 term must **not** be defined as an unbounded re-sum of the same manifests that already produce `live_total`. `live_total` includes the EXP-007 manifests; if the subtrahend is computed by re-summing those same manifests without an independent authorized bound, then `unexplained` becomes **identically zero by construction**, growth is absorbed silently, and unexplained-spend detection is destroyed while the check shows green. The term must be bounded by an independent authorized source — DEC-026's authorized maximum of **140** and DEC-031's recorded **126** are both available for that purpose.

**The repair MUST NOT:** weaken, delete, skip, `xfail` or bypass check 22; remove or raise the `live_total <= 500` ceiling; remove the `not ledger_errors` guard; convert a strict failure into a warning; hard-code a passing value not derived from the canonical ledger; change any manifest, result, budget or ledger artifact; or alter authorization state.

## 7 — Explicitly OUT of scope (not decided, not authorized, not resolved)

1. **`scripts/validate_day30.py` check 14** — also failing (`n_manifests == 9` and `live_total == 232` under **strict equality**, against a live 14/358; strictly more brittle than check 22, with no authorized-growth term at all). Its constants are headed *"Day 30 must move NEITHER number"* — a genuine historical-preservation framing that `9e83742` deliberately left alone. It is a **different artifact with a different semantic status** and needs its own audit and its own decision. **DEC-032 authorizes nothing there.**
2. **The propagation path** — `scripts/validate_day31.py:907–913` re-executes the six prior validators as subprocesses (checks 29–34), so day30's failure propagates into day31 independently of check 22. Repairing check 22 alone will **not** make `validate_day31.py` exit 0.
3. **The 2026-09-16 aborted zero-live smoke manifest** — `results/training/smoke/train-a0-d0-20260916T043003Z`. Established facts, and only these: the manifest **exists**; it records **0 live executions**; it **charged 0**; it **post-dates DEC-011** (2026-09-16 vs 2026-09-13); and its own reconciliation instruction (`budget_accounting: "uncertain: the in-flight execution may or may not have completed; count records under transitions/ to reconcile"`) refers to a `transitions/` directory that **does not exist**, so the reconciliation it prescribes is unperformable. DEC-031's live/budget accounting therefore **cannot** be read as evidence that this row was a Day-29 baseline artifact. DEC-031 §3 carries it only as an anonymous `+0` term inside a live-total re-sum; it is **not** part of DEC-011's signed Day-29 baseline (§1). **UNRESOLVED GOVERNANCE GAP — not resolved here.** The repository currently has **no written rule** answering: *should an aborted / zero-live manifest count toward a manifest-count invariant?* DEC-031 §5 charged-category 3 supplies a **charging** rule only ("still a charged row at 0"); it says nothing about counting. No decision names this run directory or attributes it to an authorized activity. This amendment **invents no policy** for zero-live manifests and **redesigns no ledger**.
4. **DEC-026 §8's defunct discriminator** — it asserts *"every one of them has an EMPTY `variant` field: no A1/A2 ablation run directory exists."* No manifest in the tree carries a `variant` key at all, before or after EXP-007; the real label key is `exp007_variant`. The discriminator no longer distinguishes anything. **Recorded, not corrected** — DEC-026 is historical and is not rewritten.
5. Any EXP-008 matter — methodology (DEC-030), budget (DEC-031), the B6 implementation decision, R4 semantics, Q0 provenance, any DEC-030 §12 field, and EXP-008 execution authorization. **All untouched.**

## 8 — Retrospective coverage of the already-performed test repair

For chronological completeness, and following DEC-018 Decision E's retrospective-adoption precedent: the live-tree ledger assertion in `tests/unit/test_exp001_maintenance.py` (`test_exp003_or_exp005_are_never_charged_to_sc6`) was re-pinned from `336 / 164` to `462 / 38` earlier on 2026-09-18, under operator instruction, **before any decision covered it**. That change is **adopted here as operator-authorized Day-37 work**, on the same reasoning as §3 (the assertion re-derives from the live tree; it does not cite a historical figure) and subject to the same invariant as §6 (the pin was not weakened — it remains an exact equality, and an unauthorized execution still breaks it). Its fixture-tree sibling assertions correctly remain at 336 and were not touched.

This is recorded rather than left implicit because the B6 implementation report (§8, §10 row 5) had classified that repair as *"a DEC-031 follow-up, not an implementation-only change"* — i.e. as owed work requiring a decision that did not then exist. **DEC-032 is that decision.** The B6 report and `results/evaluation/exp008_b6_implementation.json` are **not** regenerated: they are correct as B6-time records and their historical status is preserved.

## 9 — Why this authorizes no experiment execution

This entry authorizes an edit to an **assertion about already-recorded history**. It creates no run directory, no queue, no specification and no schedule; it grants no Spark, training, validation or TEST execution; it does not raise the SC6 cap (500, unchanged), does not change the cumulative charge (462, unchanged), does not change the remaining headroom (38, unchanged), and charges **0** executions. A validator reading the ledger cannot spend it. **EXP-008 execution authorization = NO.**

## 10 — Why this is bookkeeping, not methodology

Nothing in the frozen research design is touched: no reward, no action space, no state schema, no Q0, no T_ref, no seed, no split, no horizon, no hyperparameter, no DEC-030 §12 field, and no statistical procedure. The repair changes **what a validator expects the ledger to read** — an arithmetic expectation about executions that already happened under DEC-026's authorization and that DEC-031 has already reconciled. Under the repository's own discriminator (§3) this is a re-derived measurement, and reconciling a measurement's expectation with the canonical ledger is bookkeeping.

## 11 — Evidence and fingerprints (read-only; nothing listed was modified by this entry)

| Source | Role | SHA256 |
|---|---|---|
| `docs/PLAN.md` | SC6 cap line 45 | `db5e82102833efe6bab8db1adaf1b35ad195faf385e63ab296d50562e349ee63` (**unchanged**) |
| `configs/rl.yaml` | `live_execution_cap: 500` | `8ca70d6dd7df68841c409a4441dc538616206bccea7877b28c73df20e6428b80` (**unchanged**) |
| `docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md` | DEC-030 identity preserved | `ec487bf2a84a9c1a6f506bdd83c71b7c7bb7ae2cceaf7e761f000c7201912a5a` (**unchanged**) |
| `docs/research/DEC_031_EXP008_SC6_BUDGET_RECONCILIATION.md` | DEC-031 content authority | `af5c18216c6fdbcba86c891934a4b2d1026a32c4e2ada91eee91f7c8ab12852c` (**unchanged**) |
| `results/evaluation/exp008_budget_reconciliation.json` | canonical 462/38 machine artifact | `bd67da1735aaaa9d62ac977f2874034dca1f70db7da849db436b2ca939a596c5` (**unchanged, byte-identical**) |
| `scripts/validate_day31.py` | the artifact this entry authorizes repairing LATER | `2dfcb82c6706e521…` — **NOT MODIFIED by this entry** |
| `scripts/validate_day30.py` | out of scope (§7.1) | **NOT MODIFIED** |
| `results/training/**/manifest.json` | 14 manifests, 358 live | **NOT MODIFIED** |

**Working-tree disclosure.** DEC-030, DEC-031 and DEC-032 are **uncommitted working-tree state** on top of HEAD `5cf0cf850f022750fa7df734328f6807e3546ee9` (`git show HEAD:DECISIONS.md | grep -c "DEC-031"` returns 0). Any future repair citing DEC-031 or DEC-032 cites an authority that presently exists only in the working tree. This is disclosed, not hidden, and matches DEC-024 §6 / DEC-026's disclosure of the same condition.

## 12 — Validation of this entry (read-only, zero Spark)

| Check | Result |
|---|---|
| DEC-032 is the next free identifier | PASS (§0) |
| `DECISIONS.md` appended only; every prior byte intact | PASS |
| DEC-030 artifact unchanged (SHA256 re-checked) | PASS |
| DEC-031 artifact and budget JSON unchanged | PASS |
| `docs/PLAN.md`, `configs/rl.yaml` unchanged | PASS |
| `scripts/validate_day31.py` NOT modified | PASS |
| `scripts/validate_day30.py` NOT modified | PASS |
| No manifest, result, budget or ledger artifact modified | PASS |
| Canonical figures restated, none re-derived or changed | PASS (462 / 38 / 500) |
| No execution authorized | PASS (§9) |
| EXP-008 authorization still NO; A5 still DISABLED; TEST still NOT AUTHORIZED | PASS |
| Spark / training / TEST executions performed | **0 / 0 / 0** |

**Status.** **DECIDED.** The Day-31 check-22 ledger assumption is recorded as an **OBSOLETE ASSUMPTION** superseded by DEC-031's canonical ledger (**462 / 38**, baseline recounted to **10** manifests, **14** total). A **validator-only, minimal, invariant-preserving** repair to `scripts/validate_day31.py` check 22 is **AUTHORIZED for a separate later task** and is **NOT performed by this entry**. `scripts/validate_day30.py`, the 2026-09-16 smoke-run attribution and DEC-026 §8's defunct discriminator are **recorded as open items, out of scope, and not resolved**. Supervisor counter-signature: **PENDING** (conventional expectation only; never simulated; not a prerequisite under DEC-018 Decision A). **This entry performs 0 Spark executions and trains nothing.**

*End of DEC-032.*


---

## 13 — Amendment record (2026-09-18, chronology correction)

This document was amended in place to remove a defective chronology statement. Nothing else in DEC-032 is withdrawn; every other conclusion stands.

**What was wrong.** §§1, 2 and 6(3) treated DEC-031 §3's *"10 manifests"* wording as if the canonical **Day-29 baseline** were ten manifests, and instructed the future Day-31 repair to account for the count as *"10 baseline + 4 EXP-007 = 14."* That silently backdated a **2026-09-16** artifact into a baseline signed on **2026-09-13**, and would have put a future validator in direct textual conflict with signed DEC-011 §7 (*"recomputed from all **9** training manifests"*), on the authority of a working-tree-only decision.

**What it now says.** The chronology is stated in three distinct strata, never collapsed:

| Stratum | Manifests | Live | Charged | Authority |
|---|---|---|---|---|
| Historical Day-29 baseline | **9** | **232** | 232 | DEC-011 §7, signed 2026-09-13 — unchanged |
| Later zero-live aborted smoke (2026-09-16) | **1** | **0** | **0** | attribution **ABSENT**; counting rule **UNRESOLVED** |
| Later EXP-007 (2026-09-17) | **4** | **126** | 126 | DEC-026; DEC-031 §3 |
| **Current filesystem** | **14** | **358** | — | 9 + 1 + 4; 232 + 0 + 126 |

Adding the two non-manifest charged spends — B4 **84** (DEC-016 C / DEC-017) and EXP-001 **20** — gives the canonical ledger **462**, remaining **38** (DEC-031 §§4, 8). Unchanged by this amendment.

**What this amendment does NOT do.** It does not reinterpret DEC-011's historical ledger; does not invent an accounting policy for zero-live manifests; does not redesign the budget ledger; does not modify DEC-030 or DEC-031; does not touch `scripts/validate_day30.py` or `scripts/validate_day31.py`; does not regenerate any freeze artifact; and does not change any authorization. **EXP-008 execution authorization remains NO.** Spark / training / TEST executions performed: **0 / 0 / 0**.

**Invariant retained verbatim (§6).** Canonical state `462 − 232 − 84 − 20 − 126 = 0` → **PASS**; one unattributable execution `463 − 232 − 84 − 20 − 126 = 1` → **FAIL**. The §6 anti-pattern clause still forbids a self-cancelling subtrahend computed by re-summing the same live manifests that produce `live_total`.

**One further supersession, recorded not re-decided.** §7.1 provisionally called `scripts/validate_day30.py`'s framing *"a genuine historical-preservation framing"* and said it *"needs its own audit and its own decision."* That audit has since been performed (read-only, 0 Spark) and found check 14 to be an **obsolete assumption** on the same cited-vs-re-derived discriminator this document applies in §3, and found that commit `9e83742` left it alone because it was still passing, not as an act of preservation. §7.1's provisional characterization is therefore **superseded as to characterization**; its **scope ruling stands unchanged** — DEC-032 still authorizes nothing for `validate_day30.py`.
