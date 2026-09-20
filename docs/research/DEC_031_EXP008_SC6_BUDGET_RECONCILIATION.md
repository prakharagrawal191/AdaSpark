# DEC-031 — EXP-008 / SC6 BUDGET RECONCILIATION (B5)

**Decision ID:** DEC-031
**Date:** 2026-09-18
**Scope:** EXP-008 / SC6 budget reconciliation only.
**Status:** DECIDED — recorded in `DECISIONS.md` as the DEC-031 entry; **`EXP-008 execution authorization = NO`**.
**Standalone decision artifact.** This is the repository-convention standalone record for DEC-031. The authoritative log entry is the appended DEC-031 section of `DECISIONS.md`; this document carries the same decision content, self-contained, so that the decision also exists as an addressable artifact. It performs **0 Spark executions**, trains nothing, executes no TEST, and modifies no artifact.
**Companion artifacts:** `docs/research/DAY37_EXP008_BUDGET_RECONCILIATION.md` (reconciliation report — touched only by the **additive** DEC-031 identifier note; its accounting text is unchanged), `results/evaluation/exp008_budget_reconciliation.json` (machine artifact, **retained byte-identical**), `scripts/reconcile_exp008_budget.py` (deterministic, read-only, zero-Spark runner).
**Supersedes nothing.** DEC-030 is unchanged; no historical decision entry is rewritten.

---

**Status.** **DECIDED (B5 budget decision recorded).** **Supervisor counter-signature: PENDING** (conventional expectation only, exactly as DEC-020/DEC-021/DEC-022/DEC-023/DEC-024/DEC-025/DEC-026; DEC-018 Decision A converted the self-imposed supervisor gate into an operator decision, and PLAN line 276 requires only that a decision be "recorded"). **NO SUPERVISOR HAS REVIEWED THIS ENTRY.** A future review is a new entry; this one is never rewritten. This entry performs **0 Spark executions**, trains nothing, executes no TEST, creates no run directory, and modifies no result artifact, no implementation file, no configuration and no prior decision entry.

**0 — Governance basis and the DEC-number resolution (checked against the repository, not assumed).**

* `DECISIONS.md` headings end at **DEC-026** (the ledger was read in full at recording time; no later heading exists).
* **DEC-030 is already formally recorded as a decision OUTSIDE `DECISIONS.md`**: `docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md` (`Decision ID: DEC-030`; `Status: DECIDED — methodology frozen; execution NOT authorized`) with machine artifact `results/evaluation/exp008_methodology_freeze.json`. Its **identity is preserved unchanged** — this entry does not renumber it, does not fold it into another number, and does not edit it.
* No `DEC-027`, `DEC-028` or `DEC-029` decision artifact exists anywhere in the working tree, in `.kilo/worktrees/**`, or in any git object reachable from `main` or from the Cline checkpoint refs (searched by heading and by string). The prose references to "DEC-027..032 drafts" in the Day-37 preflight/audit artifacts are **non-authoritative evidence** and occupy no identifier.
* Therefore the highest formally used decision identifier is **030** and the **next sequential identifier is DEC-031** — selected because it is the next sequential ID after a formally recorded decision, **not** because any draft file used that number. (DEC-030 §10's phrase "(DEC-031 or equivalent)" for a future *authorization* decision remains satisfied by its own "or equivalent" clause; that decision remains separate and, when created, will carry its own later identifier. No text of DEC-030 is changed.)
* **Content authority.** This entry records the accounting already established, verified and published by `docs/research/DAY37_EXP008_BUDGET_RECONCILIATION.md` (SHA256 `3ab808c8…dcd9e` as published; after this entry's **additive** DEC-031 identifier note in that report's header its hash is `edba9f93…ff9b4d`, with **no accounting text changed**) and `results/evaluation/exp008_budget_reconciliation.json` (SHA256 `bd67da1735aaaa9d62ac977f2874034dca1f70db7da849db436b2ca939a596c5`, 33 236 bytes), reconstructed by the deterministic zero-Spark runner `scripts/reconcile_exp008_budget.py`. **This entry adds no new accounting and changes no figure.**

**1 — Scope.** EXP-008 / SC6 budget reconciliation only: (a) the SC6 counting rule actually applied by the decision chain; (b) the current cumulative charge; (c) the currently remaining capacity; (d) the classification of historical/stale figures; and (e) the conditional any future EXP-008 specification must satisfy. Nothing else is in scope.

**2 — SC6 cap: 500 charged live TRAIN executions.** Unchanged and **not raised**. Sources: `docs/PLAN.md` line 45 (*"SC6 = training ≤500 executions, monitoring overhead ≤5% of job time"*) and `configs/rl.yaml` line 17 (`live_execution_cap: 500 # frozen cap (PLAN section 16 / SC6); env owns the guard`). It is **one global cap**, not a per-run and not a per-experiment cap; cross-run totals are *reported*, not enforced in code (`src/sparkrl/training/loop.py`, `BUDGET_ENFORCEMENT_NOTE`: cross-run SC6 totals are "the SUM over manifests, REPORTED not enforced (COMP-EXP-11 deferred)"), which is exactly why the cap is enforced by decision governance. `docs/PLAN.md` and `configs/rl.yaml` are **not** modified by this entry.

**3 — Current authoritative cumulative charge: 462.** Continuous with the recorded decision chain and machine-reconstructed from raw manifests/artifacts:

| Component | Executions | Authority |
|---|---|---|
| Existing charged TRAIN main-training manifest chain, **including 15 charged smoke executions** | **232** | DEC-011: *"(5 runs × 3) + 217 training (42 + 84 + 49 + 42) = 232 of the frozen 500"*; re-summed from `results/training/**/manifest.json` (10 manifests: 3+3+3+3+3+0+42+84+49+42) |
| B4 TRAIN calibration | **84** | DEC-016 C (*"taking the ledger from 232 to 316 of 500"*); `results/evaluation/b4_selection.json` `budget: 84`, `split: "train"`; commit `9e83742` |
| EXP-001 TRAIN noise calibration | **20** | `results/experiments/exp-001/spec.json`: `"sc6_charge": "20 TRAIN executions (316 -> 336 of 500)"` |
| EXP-007 A1/A2 live TRAIN executions | **126** | DEC-026 authorization scope; four 2026-09-17 manifests `35 + 35 + 35 + 21 = 126` |
| **Cumulative charge** | **462** | 232 + 84 + 20 + 126 |

**4 — Exact accounting chain.** `232 + 84 + 20 + 126 = 462`. Independent cross-check: `358 (all 14 manifests, live) + 84 + 20 = 462`, and `358 − 126 = 232` reproduces DEC-011. **Remaining capacity: `500 − 462 = 38`.**

**5 — Charging and non-charging categories (the rule as actually applied, now formally recorded).**

**CHARGED (counts against SC6):**

1. **TRAIN live executions** — every real environment transition consumed by a training run's budget counter (`live_executions` in the run manifest), charged to the training register lines.
2. **Failed live executions** — a failed execution still consumes a Spark run and therefore consumes budget; failure changes the reward (DEC-010), not the charge.
3. **Smoke executions when they are part of charged TRAIN accounting** — DEC-011's `(5 runs × 3)` term charges them; the **15 live smoke executions are inside the 232 chain**. A smoke attempt with 0 live executions is still a charged row at 0.
4. **The non-manifest TRAIN charges bound by decision** — B4's 84 (DEC-016 C) and EXP-001's 20 (its own spec, kept charged by DEC-024 §5).

**NOT CHARGED:**

1. **Undefined/unexecuted planned rows** — e.g. EXP-007's 14 unexecuted planned rows, EXP-006's 20 undefined B2×F4_ski rows (DEC-019 class), and every planned row that never ran. Plan is not charge.
2. **Cache hits** — a replayed/cached transition consumes no live Spark execution.
3. **EXP-003 validation** — `results/evaluation/validation_observations.json` (96 observations): separate register line, validation split, charged **0**.
4. **EXP-005 TEST** — 245/245 TEST observations, charged **0** (TEST seal, DEC-018 Decision B).
5. **EXP-006 TEST** — 125/125 TEST observations, charged **0**.
6. **EXP-002 historical sensitivity-grid executions** — 208 recorded attempts (192 grid + 16 reference; 189 COMPLETED + 19 FAILED), executed *before* the SC6 ledger existed; **no DEC ever charges them**, and no retroactive re-designation is made here (that would require a new decision).

**6 — Explicit per-item statement.** **EXP-002 = 0 charge. EXP-003 validation = 0 charge. EXP-005 TEST = 0 charge. EXP-006 TEST = 0 charge. EXP-007 = 126 charge** (35+35+35+21 live, TRAIN-split, 0 failures, 0 smoke, 14 unexecuted planned rows charging nothing). **Smoke executions are included in the charged 232 chain** (DEC-011). **Failed live executions consume budget** — the rule is recorded; EXP-007 itself executed 0 failures, so the rule alters no current figure.

**7 — Historical / stale figures, and why each is not the current authoritative headroom.**

| Figure | What it is | Why it is not the current authoritative figure |
|---|---|---|
| **343** | Non-smoke manifest subtotal (`42+84+35+35+49+35+21+42`) | Arithmetically correct **as a manifest subtotal**, but it is **not the SC6 ledger**: it omits the 15 smoke live executions DEC-011 explicitly charged, and it omits B4's 84 and EXP-001's 20, which are not manifests at all. **Non-smoke manifest subtotal, not the authoritative ledger.** |
| **379** | Preflight "spent before EXP-008" basis (`343 + 20 + 16`) | **Stale/contradictory basis.** It drops the 15 charged smoke executions (contra DEC-011) and B4's 84 (contra DEC-016 C) while adding 16 EXP-002 B0 reference runs that **no decision ever charged** — a cherry-picked subset of EXP-002's 208 recorded runs. No decision authorizes this basis. |
| **121** | `500 − 379` ("nominal TRAIN-only" remaining) | **Stale consequence of the 379 basis**; it inherits every defect above. Not a rounding difference from 38 — it is a different *category mix*. |
| **−89** | Preflight claim of "DEC-chain post-EXP-007 remaining" | **Not reproducible and internally inconsistent with its own stated chain**: the same artifact states "336 spent pre-007, remaining 164; EXP-007 executed 126", which yields `164 − 126 = 38`, not −89. No derivation, component list or ledger entry for −89 exists anywhere; the unexplained gap is 127 executions. Recorded as **unresolvable from cited evidence** — not silently discarded — and superseded by the reconstructed 38. |
| **164** | DEC-024 §3 / DEC-025 §1 remaining **before** the EXP-007 execution (`500 − 336`) | **Historically correct for its date, now superseded** by the 126 live executions performed under DEC-026's authorization. A time-slice, not an error; DEC-025 remains unedited. |
| **24** | DEC-025 §12 / DEC-026 §3 headroom at authorization time (`164 − 140`) | **Historical headroom under the earlier EXP-007 authorization envelope**: computed against the planned *maximum* 140, not against the executed 126. Superseded by execution; DEC-025 and DEC-026 remain unedited. |

For completeness, the reconciliation additionally classified `184` (DEC-023's arithmetically wrong "500 − 336 = 184", already corrected by DEC-024 §3/§6 and DEC-025 §1), `519` (illustrative `379 + 140`) and `−229` (illustrative, truncated derivation) as **stale or illustrative**. None is authoritative; none is rewritten here.

**8 — Current remaining headroom: 38 charged live TRAIN executions.** `500 − 462 = 38`, reproducible two independent ways (`500 − 462`; and `500 − (358 manifests + 84 + 20)`).

> **NOT AN APPROVAL.** "38 remaining" means **only** that **38 charged live TRAIN executions remain under the current global SC6 accounting envelope**. It does **not** mean — and must never be reported as — "38 A3/A4 executions approved". This entry approves **no** A3/A4 execution count, shape, arm set, seed set or schedule.

**9 — No cap amendment enacted. No de-scoping enacted.** The SC6 cap remains **500**; `docs/PLAN.md` line 45 and `configs/rl.yaml` line 17 stand verbatim. Nothing is de-scoped: no EXP-008 arm, seed, cell or register line is removed or reduced. For this decision `cap_amendment_required` = **false** and `de_scoping_required` = **false**.

**10 — PLAN-internal scope/envelope tension (recorded as a governance dependency; NOT resolved here).** `docs/PLAN.md` line 315 registers EXP-008 with an envelope of **~300** executions (*"EXP-008 | RQ4 | design matters | Train/Test | A3, A4, A5 | ~300 | ablation table | planned"*), while PLAN line 45 caps SC6 at **500** and 462 is already charged. DEC-011 already recorded that whether EXP-008's envelope is charged to SC6's ≤500 or to its own ~300 line is an **internal-PLAN conflict that DEC-010's precedence rule cannot arbitrate**. This entry records that tension as a dependency; it does **not** decide the amendment mechanism, does **not** amend PLAN, does **not** raise the cap and does **not** re-scope EXP-008.

> **Current accounting is unambiguous; the remaining 38-execution capacity is authoritative. Any future EXP-008 specification exceeding that capacity requires a separate scope/cap governance action before execution authorization.**

**11 — Explicit future trigger.** A future **frozen** EXP-008 specification whose **charged** live TRAIN execution requirement **exceeds 38** **cannot be authorized** under the current SC6 envelope without a **separate governance decision** — either an explicit **cap/PLAN amendment** or an explicit **scope reduction** to ≤ 38 charged live TRAIN executions, enacted by its own decision (a new DEC entry plus, for a cap change, the PLAN header's change-control amendment). No such amendment and no such reduction exists today, and neither is created by this entry.

**12 — Relationship to DEC-030.** **DEC-030 remains unchanged** — not rewritten, not superseded, not reinterpreted. This entry resolves **only** the B5 budget question DEC-030 §10 explicitly deferred (*"B5 is NOT resolved by DEC-030. Budget reconciliation is a separate required decision."*). This decision **does not alter A3/A4 methodology** and does not change DEC-030's arm tables, isolation verdicts, A5 lock, statistical-governance position or `execution authorization: NO`.

**13 — What this decision deliberately does NOT decide** (each remains governed by DEC-030 and subsequent decisions): the **A3 number of seeds**; the **A4 number of seeds**; the **episode horizon**; the **A3/A4 arm count**; the **Q0 source**; the **execution schedule**; the **implementation design**; the **final experiment scope**; the statistical governance of EXP-008; the completeness of A3-R4; and the amendment mechanism for the PLAN tension in §10. This entry freezes only the **charging rule** and the **remaining capacity** (B5) — nothing else. It is **not** the B6 implementation decision and **not** an authorization decision.

**14 — Non-authorization firewall (explicit).**

| Item | State recorded by this entry |
|---|---|
| **EXP-008 execution authorization** | **FALSE / NO** |
| **Implementation authorization** (A3/A4, B6) | **FALSE / NO** — A3/A4 remain **UNIMPLEMENTED** |
| **A5** | **DISABLED / excluded** (DEC-011; re-affirmed DEC-016 §7, DEC-023 §2, DEC-024 A5 row, DEC-025 §7, DEC-030 §9); `configs/rl.yaml` `gamma` stays 0.0 |
| **TEST** | **NOT AUTHORIZED** — no TEST queue, specification or ledger is created; nothing here opens TEST for anything |
| **`docs/PLAN.md`** | **UNCHANGED** — no line edited |
| **Historical decisions** | **UNCHANGED** — DEC-001 … DEC-026 and DEC-030 are not rewritten; this entry is appended, never substituted |
| **Spark / training / TEST executions performed by this entry** | **0 / 0 / 0** |

**15 — Evidence and fingerprints (read-only; nothing listed here was modified except that this entry is appended).**

| Source | Role | SHA256 (at recording time) |
|---|---|---|
| `docs/research/DAY37_EXP008_BUDGET_RECONCILIATION.md` | reconciliation report + decision content | `3ab808c8…dcd9e` as published; `edba9f93…ff9b4d` after the additive DEC-031 identifier note (accounting text unchanged) |
| `results/evaluation/exp008_budget_reconciliation.json` | machine artifact — **retained byte-identical, NOT modified by this entry** | `bd67da1735aaaa9d62ac977f2874034dca1f70db7da849db436b2ca939a596c5` (33 236 bytes) |
| `docs/PLAN.md` | SC6 (line 45); EXP-008 envelope (line 315) | `db5e82102833efe6bab8db1adaf1b35ad195faf385e63ab296d50562e349ee63` (**unchanged**) |
| `configs/rl.yaml` | `live_execution_cap: 500` (line 17) | `8ca70d6dd7df68841c409a4441dc538616206bccea7877b28c73df20e6428b80` (**unchanged**) |
| `docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md` | DEC-030 identity preserved | `ec487bf2…01912a5a` (**unchanged**) |
| `DECISIONS.md` | this entry appended; every prior byte intact | `313e6f0353670bef42e1c10bbfa3069dfc29d5e348617d81b1add5d2dde957e9` **before** this append (the value recorded inside the reconciliation JSON, which is retained unchanged) |

Note: the reconciliation JSON records the `DECISIONS.md` fingerprint as of **its own** run (`313e6f03…`). This entry appends to `DECISIONS.md`, so that recorded field now describes the pre-DEC-031 state. That is expected, is **not** an accounting change, and is why the JSON is **retained rather than regenerated**: re-running the runner would change only that fingerprint field, while every accounting number would remain **462 / 38**.

**16 — Validation of this entry (performed after recording it; read-only, zero Spark).**

| Check | Evidence | Result |
|---|---|---|
| New DEC ID unique | heading scan of `DECISIONS.md` + repository-wide search for `DEC-031` | PASS |
| No historical DEC text changed | pre-edit copy byte-identical prefix; `DECISIONS.md` only appended to | PASS |
| DEC-030 unchanged | SHA256 of the DEC-030 artifact unchanged | PASS |
| SC6 cap = 500 | `docs/PLAN.md` line 45; `configs/rl.yaml` line 17 | PASS |
| cumulative charge = 462 | reconciliation JSON `cumulative_charge`; charge-table sum | PASS |
| remaining = 38 | `500 − 462` | PASS |
| accounting chain sums exactly | `232 + 84 + 20 + 126 = 462` | PASS |
| charged categories represented | §5 / §6 | PASS |
| non-charged categories represented | §5 / §6 | PASS |
| stale figures classified | §7 (343, 379, 121, −89, 164, 24) | PASS |
| no A3/A4 execution scope authorized | §8 note; §14 table | PASS |
| no implementation authorized | §14 table | PASS |
| A5 remains disabled | §14 table | PASS |
| TEST remains unauthorized | §14 table | PASS |
| PLAN remains unchanged | `docs/PLAN.md` SHA256 `db5e8210…` re-checked after recording | PASS |
| deterministic validation passes | read-only, zero-Spark check script re-parsed `DECISIONS.md` + the reconciliation JSON and asserted every figure and classification above | PASS |

**Validation detail (recorded at recording time).** The read-only check script ran **twice, with byte-identical output on both runs** (**55/55** checks passed); it parsed `DECISIONS.md`, the pre-edit copy, `docs/PLAN.md`, `configs/rl.yaml`, the reconciliation JSON, both Day-37 documents and the Cline checkpoint snapshot of the B5 report (proving the report was changed **additively only**, delta = 0 characters of accounting text). The pre-edit `DECISIONS.md` copy used for the append-only proof stayed in the session temp directory and was **not** added to the repository. `python -m pytest tests/unit/test_exp006_runner.py` — the existing governance test that enforces DEC-022 heading uniqueness and fingerprint binding against `DECISIONS.md` — still passes **31/31** after the append.

**Status.** **B5 budget decision recorded: `SC6 cap = 500`; `authoritative cumulative charge = 462`; `remaining = 38`; `232 + 84 + 20 + 126 = 462`; no cap amendment enacted; no de-scoping enacted.** `EXP-008 execution authorization = NO`. `A3/A4 implementation = NOT AUTHORIZED / NOT IMPLEMENTED`. `A5 = DISABLED`. `TEST = NOT AUTHORIZED`. `PLAN.md = UNCHANGED`. Historical decisions (DEC-001 … DEC-026, DEC-030) = **UNCHANGED**. Supervisor counter-signature: **PENDING** (conventional expectation only; never simulated, and not a prerequisite under DEC-018 Decision A). **This entry performs 0 Spark executions and trains nothing.**

*End of DEC-031.*
