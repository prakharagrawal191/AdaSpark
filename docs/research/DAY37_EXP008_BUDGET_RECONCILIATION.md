# DAY37 — EXP-008 / SC6 BUDGET RECONCILIATION (B5)

**Artifact ID:** `DAY37_EXP008_BUDGET_RECONCILIATION`
**Status:** B5 BUDGET DECISION — **reconciliation complete, budget uniquely established**.
**DEC number:** assignment + appending to `DECISIONS.md` is a **separate mechanical step** and was
**NOT performed by this task** (see §13). This document is the decision *content* required by DEC-030 §10.
**Repository:** `5cf0cf850f022750fa7df734328f6807e3546ee9` on `main`.
**Worktree:** DIRTY (untracked Day-34..37 artifacts incl. this file; tracked modifications to
`DECISIONS.md`, `ARCHITECTURE_FREEZE.md`, `run_exp005.py`, `run_training.py`, `q0.py`, `q_learning.py`,
`rl/__init__.py`, `state.py`, `training/__init__.py`, `loop.py`, `test_exp005_strategies.py`).
**Machine artifact:** `results/evaluation/exp008_budget_reconciliation.json`
(SHA256 `bd67da1735aaaa9d62ac977f2874034dca1f70db7da849db436b2ca939a596c5`, 33 236 bytes).
**Runner:** `scripts/reconcile_exp008_budget.py` (deterministic, read-only, zero-Spark).

> **ADDENDUM — 2026-09-18 (formal decision recording).** The B5 budget decision whose content
> this document contains is now **formally recorded as DEC-031** (`DECISIONS.md`, DEC-031 entry;
> standalone record `docs/research/DEC_031_EXP008_SC6_BUDGET_RECONCILIATION.md`). The accounting,
> figures, classifications and status below are **unchanged** by that recording. The remaining
> `DEC-031` reference in §13 belongs to DEC-030 §12's gate-chain step 4 — the *future
> execution-authorization* decision — which stays separate and will carry its own later
> identifier under DEC-030's own "or equivalent" wording; no text of DEC-030 or of this document's
> substantive accounting is altered. The machine artifact
> `results/evaluation/exp008_budget_reconciliation.json` is **retained byte-identical**
> (it records the `DECISIONS.md` fingerprint as of its own run).

---

## 1. Scope, firewall, and what this document is NOT

This is the **B5 budget decision** that DEC-030 §10 explicitly left unresolved:

> DEC-030 §10: *"B5 is NOT resolved by DEC-030. Budget reconciliation is a separate required
> decision."* — and: *"Contradictory figures cited from the preflight audit, NONE selected as
> authoritative: spent before EXP-008 = 379; remaining-capacity candidates = −89 (DEC-chain
> post-EXP-007), 121 (nominal TRAIN-only), 38 (validation-excluded basis). SC6 cap = 500 (frozen)."*

It does **exactly one** thing: it derives the SC6 counting rule from authoritative sources and
reconstructs the SC6 ledger from raw manifests/artifacts, so that **one** cumulative charge and
**one** remaining-capacity figure are established by evidence instead of by selection.

**This document does NOT:**

- execute Spark, run training, or execute TEST — **0 executions of any kind**;
- implement A3/A4, or modify any RL/training source or artifact;
- modify `DECISIONS.md`, `PLAN.md`, `configs/rl.yaml`, `experiments/registry.csv`, or any
  EXP-005/006/007 result; **no historical DEC entry is rewritten**;
- freeze A3/A4 seeds, horizon, cells, Q0 source, arm set, implementation, or an execution plan;
- authorize EXP-008 execution (authorization remains **NO**);
- raise, reinterpret, or re-scope the 500 cap, and does not de-scope EXP-008;
- re-enable A5 (A5 remains **DISABLED** under DEC-011).

**Terminology.** *Charge* = live TRAIN-split Spark executions counted against SC6. *Ledger* = the
running SC6 total reported by the decision chain. *Manifest subtotal* = a sum over
`results/training/**/manifest.json` that is **not** by itself the ledger.

---

## 2. Authoritative sources and fingerprints

Precedence applied (DEC-010 precedence rule, restated in DEC-030 §1): **PLAN** governs over derived
documents; a later DEC amends an earlier one only by a **new** entry (DEC-021 clerical-correction
tradition); raw manifests/artifacts outrank generated prose summaries.

| Source | Role | SHA256 |
|---|---|---|
| `docs/PLAN.md` | SC6 success criterion (line 45); EXP-008 envelope (line 315) | `db5e8210…e349ee63` |
| `DECISIONS.md` | DEC-011/016/018/023/024/025/026 accounting chain | `313e6f03…dde957e9` |
| `configs/rl.yaml` | `live_execution_cap: 500` (line 17) | `8ca70d6d…e6428b80` |
| `docs/research/DAY37_EXP008_PREFLIGHT_AUDIT.md` | contradictory figures (evidence only) | `69f7c6a7…31a82b1` |
| `docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md` | methodology freeze; B5 deferral | `ec487bf2…01912a5a` |
| `results/evaluation/exp008_preflight_audit.json` | preflight values (evidence only) | `6f49f9b8…9d009ca47a` |
| `results/evaluation/exp008_methodology_freeze.json` | DEC-030 machine artifact | `d05e824f…a53d0be2` |
| `results/evaluation/b4_selection.json` | B4 TRAIN charge (`budget: 84`) | `b813f73d…dec4e8d5` |
| `results/experiments/exp-001/spec.json` | EXP-001 declared `sc6_charge` | `6409e383…8ea6bc421` |
| `results/experiments/exp-002/attempts.jsonl` | EXP-002 attempted/completed/failed | `a8566470…7ab5127e6a` |
| `results/evaluation/validation_observations.json` | EXP-003 validation observations | `303f45e4…d4bc3bac` |
| `results/experiments/exp-005/{observations.jsonl,summary.json}` | EXP-005 TEST (245/245) | `d928cf5d…703d3ae1`, `cede3e8f…5c49a97c` |
| `results/experiments/exp-006/{observations.jsonl,summary.json}` | EXP-006 TEST (125/125) | `be270c0b…ad2eb577`, `253d4d7a…aa673d1b` |
| `experiments/registry.csv` | experiment register | `40232dca…53239b722` |
| `results/training/**/manifest.json` | **14** RUN manifests (raw bytes) | per-file, in the JSON artifact |
| `src/sparkrl/rl/env.py`, `src/sparkrl/training/loop.py` | budget guard semantics | cited, not hashed |

All 14 training manifests record `live_execution_cap = 500`, machine-asserted by the runner.
---

## 3. The SC6 counting rule (traced, not inferred)

**Governing source — PLAN (highest authority).** `docs/PLAN.md` line 45:

> *"**Success criteria.** SC1 = H1 gate passes · SC2–SC4 = H2–H3 accepted statistically · SC5 = H4
> accepted · **SC6 = training ≤500 executions**, monitoring overhead ≤5% of job time · SC7 = re-run
> reproducibility within ±5% · SC8 = tests green; repo reproducible from fresh clone."*

**Frozen configuration (same cap, machine-readable).** `configs/rl.yaml` line 17:
`live_execution_cap: 500  # frozen cap (PLAN section 16 / SC6); env owns the guard`.

**Authoritative accounting application (the DEC chain, which is how SC6 has actually been counted):**

| Decision | Text (verbatim) | Ledger effect |
|---|---|---|
| DEC-011 | *"(5 runs × 3) + 217 training (42 + 84 + 49 + 42) = **232** of the frozen 500"* | 232 |
| DEC-016 C | *"Projected cost: 84 executions, taking the ledger from 232 to 316 of 500"* | +84 → 316 |
| EXP-001 `spec.json` | *`"sc6_charge": "20 TRAIN executions (316 -> 336 of 500)"`* | +20 → 336 |
| DEC-018 closing | *"The SC6 TRAIN ledger stands at 336/500"* | 336 |
| DEC-024 §3 / DEC-025 §1 | *"remaining SC6 capacity: 500 − 336 = **164**"* | 336 / 164 rem. |
| DEC-025 §12 | *"headroom: 164 − 140 = **24** live executions"* | EXP-007 max 140 |
| DEC-026 §10 | *"maximum **140** live Spark executions charged to SC6 (remaining 164, headroom 24)"* | authorization scope |
| DEC-026 §14 | *"more than **140** total EXP-007 live executions … the frozen 500 cap is never raised"* | ceiling |

**Rule (established by those sources, applied here forward):**

1. **What counts:** **live TRAIN-split Spark executions** charged to the training register lines —
   i.e. real environment transitions consumed by a training run's budget counter.
2. **Cap scope:** **ONE global cap of 500**, not per run and not per experiment. The DEC chain
   maintains a *single* ledger (232 → 316 → 336 → 462). Per-run limits
   (`budget_limit_this_run`) are a different, local control; `src/sparkrl/training/loop.py`
   `BUDGET_ENFORCEMENT_NOTE` states cross-run totals are *"the SUM over manifests, REPORTED not
   enforced (COMP-EXP-11 deferred)"* — the global cap is enforced by **decision governance**, which
   is exactly why this reconciliation exists.
3. **Smoke runs charge.** DEC-011's ledger composition is explicit: the `(5 runs × 3)` term **is**
   the `results/training/smoke/*` manifests at 3 live executions each. Reinforced by
   `tests/integration/test_rl_training_smoke.py` (*"running the integration suite SPENDS frozen
   budget"*). **Smoke is inside the ledger, not outside it.**
4. **Failed live executions charge.** DEC-010 makes failure a first-class observation (reward −1,
   Q-update applied): the execution was consumed. (No failure occurred inside any charged category,
   so this rule changes no number here.)
5. **Cache hits do not charge.** `src/sparkrl/rl/env.py` (*"Cache hits do NOT consume budget"*);
   DEC-026 §4 (*"cache hits free; only live executions increment the budget"*).
6. **Undefined / not-executed planned rows do not charge.** Charging is per-episode
   (`budget_limit = int(episodes)`, DEC-025 §12). EXP-007 A2 seed 1 planned 35 and executed 21; the
   14 unexecuted rows charge **nothing**.
7. **Validation-split executions do not charge.** DEC-012 (EXP-003/B1-B2 is a separate authorized
   register line) and DEC-013 (validation execution gate, Model B); `scripts/validate_day31.py`:
   *"EXP-003 is a separate register line that is not charged to that cap at all"*.
8. **TEST-split executions do not charge.** DEC-018 Decision B TEST seal; DEC-024 §5, DEC-025 §13,
   DEC-026 §12; preflight §12 (*"EXP-005 TEST 245 and EXP-006 125 do not charge SC6 TRAIN"*).
9. **The second SC6 clause** (*"monitoring overhead ≤5% of job time"*) is a measured-overhead
   criterion (EXP-009 scope), consumes no execution charge, and is out of scope here.
10. **Which DECISION controls if documents conflict:** PLAN (line 45, and the plan header's
    change-control rule) governs over derived documents (DEC-010 precedence, restated by DEC-030 §1
    for raw artifacts). Later decisions amend earlier ones **only by a new entry** — hence this
    document's reconciliation findings are recorded here rather than by editing DEC-023/024/025.

**Applied forward to EXP-008:** every live TRAIN execution of an A3/A4 arm charges SC6 **1:1**
(one execution per episode/cell transition, DEC-025 §12 loop semantics); cache hits are free; failed
live executions charge; smoke charges; unexecuted rows do not charge; validation/TEST do not charge.
The cap remains **500**, global, unchanged.
---

## 4. Ledger reconstruction from raw artifacts

### 4.1 Row-level manifest ledger (14 raw `manifest.json` files, machine-summed)

`live = budget.live_executions`; `planned = budget.budget_limit_this_run`; every row records the
frozen cap 500.

| # | run dir (under `results/training/`) | kind | variant | seed | planned | **live** | stop_reason | SC6 |
|---|---|---|---|---|---|---|---|---|
| 1 | `smoke/train-a0-d0-20260912T052836Z` | smoke | – | 0 | 3 | **3** | planned_episodes | charged |
| 2 | `smoke/train-a0-d0-20260912T081149Z` | smoke | – | 0 | 3 | **3** | planned_episodes | charged |
| 3 | `smoke/train-a0-d0-20260912T081451Z` | smoke | – | 0 | 3 | **3** | planned_episodes | charged |
| 4 | `smoke/train-a0-d0-20260912T081737Z` | smoke | – | 0 | 3 | **3** | planned_episodes | charged |
| 5 | `smoke/train-a0-d0-20260912T082054Z` | smoke | – | 0 | 3 | **3** | planned_episodes | charged |
| 6 | `smoke/train-a0-d0-20260916T043003Z` | smoke | – | 0 | 3 | **0** | aborted | charged (0) |
| 7 | `train-a0-d0-20260912T083120Z` | training | – | 0 | 84 | **42** | early_stop_policy_stable | charged |
| 8 | `train-a0-d0-20260912T112906Z` | training | – | 0 | 84 | **84** | planned_episodes | charged |
| 9 | `train-a1-d0-20260912T115123Z` | training | – | 1 | 84 | **49** | early_stop_policy_stable | charged |
| 10 | `train-a2-d0-20260912T120648Z` | training | – | 2 | 84 | **42** | early_stop_policy_stable | charged |
| 11 | `train-a0-d0-20260917T055042Z` | training | **A1** | 0 | 35 | **35** | planned_episodes | charged |
| 12 | `train-a0-d0-20260917T061316Z` | training | **A2** | 0 | 35 | **35** | early_stop_policy_stable | charged |
| 13 | `train-a1-d0-20260917T060047Z` | training | **A1** | 1 | 35 | **35** | planned_episodes | charged |
| 14 | `train-a1-d0-20260917T062346Z` | training | **A2** | 1 | 35 | **21** | early_stop_policy_stable | charged |

**Subtotals (machine-asserted in the runner):**

- smoke (rows 1–6): `15 + 0 = 15` live  ← *the fifth smoke row at 0 is still a smoke manifest*.
- non-smoke (rows 7–14): `42 + 84 + 49 + 42 + 35 + 35 + 35 + 21 = 343` live.
- **all manifests: 358 live.**
- pre-EXP-007 manifest ledger (rows 1–10): `15 + (42 + 84 + 49 + 42) = 15 + 217 = **232**` — reproduces
  DEC-011's composition exactly.
- EXP-007 manifests (rows 11–14): `35 + 35 + 35 + 21 = **126**`.

Note the reconciliation trap: rows 7–10 planned 84 each but early-stopped at 42/84/49/42. **Charging
follows `live_executions`, not `budget_limit_this_run`** — the DEC chain's "217" is the live sum, and
the DEC-026 authorization ceiling (140) is likewise a *maximum*, not a charge.

### 4.2 Non-manifest charges (each from its own authoritative artifact)

| Charge | Value | Authoritative record |
|---|---|---|
| B4 TRAIN calibration | **84** | `results/evaluation/b4_selection.json`: `budget: 84`, `split: "train"`, `observation_counts {failed: 0, total: 84, usable: 84}`; DEC-016 C *"232 to 316 of 500"*; commit `9e83742` |
| EXP-001 noise calibration | **20** | `results/experiments/exp-001/spec.json`: `"sc6_charge": "20 TRAIN executions (316 -> 336 of 500)"`, `total_planned: 20`; DEC-024 §5 keeps it charged |

### 4.3 Categories measured but NOT charged

| Register line | Raw measurement | Split | Charge |
|---|---|---|---|
| EXP-002 (SC1 sensitivity gate, Days 23–24) | `attempts.jsonl` **208 rows** = 189 COMPLETED + 19 FAILED (192 grid + 16 reference per `EXP002_CONFIGURATION_SENSITIVITY_AUDIT.md`) | train (pre-ledger era) | **0** |
| EXP-003 / B1-B2 selection | `validation_observations.json` **96 observations** (recovered_count 96; 0 non-validation) | validation | **0** |
| EXP-005 main comparison | `observations.jsonl` **245 rows**; summary `complete (245 of 245)` | test | **0** |
| EXP-006 generalization | `observations.jsonl` **125 rows**; summary `complete (125 of 125)` | test | **0** |

EXP-002 requires an explicit accounting-boundary note: it was executed *before* the SC6 ledger
existed, DEC-011's composition charges only the training manifests, and **no DEC ever charges
EXP-002 to SC6**. This is recorded as a boundary convention and is **not** a retroactive
re-designation (DEC-024 §5 / DEC-025 §13 precedent: recorded history is not rewritten). Any partial
charge of EXP-002 *rows* (e.g. 16 B0 references) would be a **new** decision and is **not** taken
here.
---

## 5. Experiment-by-experiment charge table

Every experiment the task asked to reconcile, with planned / attempted / successful / failed /
undefined / smoke and the authoritative charge.

| # | Register line | Split | Planned | Attempted | Successful | Failed | Unexec. rows | Smoke | Counts to SC6? | **Charge** |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | EXP-002 SC1 sensitivity gate | train (pre-ledger) | 208 (192 grid + 16 ref) | **208** | 189 | 19 | 0 | 0 | **no** (no DEC charges it) | **0** |
| 2 | EXP-003 / B1-B2 selection | validation | DEC-012 plan (PLAN env. ~30) | **96** obs. | 96 obs. | not recorded | not recorded | 0 | **no** (separate register line) | **0** |
| 3 | EXP-004 / RL **main training** (Day-27/29 inc. smoke) | train | per-manifest (42/84/49/42 + 3×smoke) | **232** | 232 | 0 | 0 | **15** | **yes** (DEC-011) | **232** |
| 4 | **B4** TRAIN calibration | train | 84 | **84** | 84 | 0 | 0 | 0 | **yes** (DEC-016 C) | **84** |
| 5 | **EXP-001** noise calibration | train | 20 | **20** | 20 declared | not recorded | 0 | 0 | **yes** (own spec) | **20** |
| 6 | EXP-005 main comparison | test | 245 | **245** | 245 rows | recorded in rows | 0 | 0 | **no** (DEC-018 B seal) | **0** |
| 7 | EXP-006 generalization | test | 125 | **125** | 125 | recorded in rows | 0 | 0 | **no** (DEC-018 B seal) | **0** |
| 8 | **EXP-007** A1/A2 state ablations | train | 140 max | **126** | 126 | **0** | **14** | 0 | **yes** (DEC-026) | **126** |

Rows 1–2 and 6–7 are **charged zero by the governing decisions**, not by this document's preference;
rows 3–5 and 8 are charged because a decision (or the artifact that a decision bound itself to)
charges them. Nothing above is inferred from a prose summary: every counted number is read from a raw
manifest, a raw JSONL/JSON artifact, or a quoted DEC line.

## 6. Cumulative arithmetic (reproducible, step by step)

**A. Cumulative charged executions before EXP-007:**

```
232  (rows 1-10 manifests: 15 smoke + 217 non-smoke; = DEC-011)
+ 84  (B4 TRAIN calibration; DEC-016 C)
+ 20  (EXP-001 sc6_charge; its own spec.json)
= 336   == DEC-024 §3 / DEC-025 §1 authoritative spent   ✔
```

Cross-check against the manifest ledger: `358 (all manifests) + 84 + 20 = 462`, and
`358 − 126 (EXP-007) = 232` reproduces DEC-011. Both paths agree.

**B. EXP-007 charge:** `35 (A1-s0) + 35 (A1-s1) + 35 (A2-s0) + 21 (A2-s1) = **126**` live TRAIN
executions, **0** smoke, **0** failures, **14** unexecuted planned rows charging nothing (§7).

**C. Cumulative charged executions after EXP-007:**

```
336 (A) + 126 (B) = 462
```

**D. Remaining capacity:**

```
500 (PLAN line 45 / rl.yaml line 17, frozen) − 462 = 38
```

Independent cross-check of D through a second decomposition:

```
500 − (358 manifests + 84 B4 + 20 EXP-001) = 500 − 462 = 38   ✔
```

**Result: cumulative charged = 462 / 500; remaining = 38.** Both are uniquely established by the
authoritative records above; no figure in this reconciliation relies on a generated summary.

---

## 7. EXP-007 charge: reconciliation of the 126

The preflight and DEC-026 agree on the facts; this section verifies them against the four raw
manifests rather than adopting either statement.

| Arm / seed | Manifest | planned | **live** | stop_reason | counted |
|---|---|---|---|---|---|
| A1-s0 | `train-a0-d0-20260917T055042Z` | 35 | **35** | planned_episodes | 35 |
| A2-s0 | `train-a0-d0-20260917T061316Z` | 35 | **35** | early_stop_policy_stable | 35 |
| A1-s1 | `train-a1-d0-20260917T060047Z` | 35 | **35** | planned_episodes | 35 |
| A2-s1 | `train-a1-d0-20260917T062346Z` | 35 | **21** | early_stop_policy_stable | 21 |
| **total** | | 140 max | **126** | | **126** |

- **All 126 are live, TRAIN-split training executions** (`run_kind: "training"`, `exp007_variant`
  set, dataset seed 0, no TEST cell) → **all 126 count**, matching the "EXECUTED 126 live
  (35+35+35+21), 0 failures" record cited by the preflight (§2) and DEC-026 §10's 140-max ceiling.
- **0 smoke** runs inside EXP-007 → the smoke rule is not exercised here.
- **0 failures** → the failed-execution rule changes nothing here.
- **14 planned-but-unexecuted rows** (A2-s1) → charged **0** (rule 6, §3).
- **Analysis and file-generation work is not counted.** `results/evaluation/exp007_analysis.json`,
  `scripts/analyze_exp007.py` and any report writing are non-Spark artifacts and consume no
  executions (DEC-025 §12: unit tests, dry-run planning calls, skipped tests and hypothetical
  episodes are **not** live executions).
- Verification of the requested facts: A1-s0 = 35 ✔, A1-s1 = 35 ✔, A2-s0 = 35 ✔, A2-s1 = 21 ✔,
  total = 126 ✔.

**EXP-007 charge = 126** (not 140: the authorization ceiling is a maximum, not a charge).

## 8. Resolution of every conflicting figure

Every figure the preflight and DEC-030 raised, plus four further stale figures that the trace
exposed. No contradictory number is deleted, and none is left unaddressed.

| Figure | Source | Definition | Counts to SC6? | Authoritative? | Reason / status |
|---|---|---|---|---|---|
| **343** | preflight §1/§10; the 8 non-smoke manifests | live sum of the 8 non-smoke manifests (`42+84+35+35+49+35+21+42`) | **partially** — a manifest subtotal, not the ledger | no | `232 − 15 + 126 = 343` is *arithmetically correct* as a manifest subtotal, but it **omits the 15 smoke live executions DEC-011 explicitly charged** and **omits B4's 84 and EXP-001's 20**, which are not manifests at all. **STALE AS A LEDGER** (valid as a subtotal). |
| **379** | preflight §10; `exp008_preflight_audit.json.cumulative_live_executions_before_exp008`; quoted (not selected) by DEC-030 §2/§10 | `343 + 20 (EXP-001) + 16 (EXP-002 B0 refs)` | no | no | **Internally inconsistent basis.** It *excludes* the 15 smoke executions DEC-011 charged and *excludes* B4's 84 that DEC-016 C charged, while *adding* 16 EXP-002 B0 reference runs that **no DEC ever charged** — and those 16 are a cherry-picked subset of EXP-002's 208 recorded runs (the 192 grid runs are ignored). No decision authorizes this basis. **STALE / CONTRADICTED.** |
| **462** | DEC-025 chain + DEC-026 charge (`336 + 126`); machine-reconstructed here | cumulative SC6 charge **after** EXP-007 | yes | **yes** | Continuous with DEC-011 (232) → DEC-016 C (316) → EXP-001 spec (336) → DEC-025 (336) → DEC-026 (+126). Every component machine-verified (§4–§6). **CURRENT — adopted.** |
| **38** | `500 − 462`; also `exp008_preflight_audit.json.remaining_sc6_capacity.validation_excluded_basis`; DEC-030 §10 ("38 (validation-excluded basis)") | remaining SC6 capacity under the authoritative rule | n/a (capacity) | **yes** | Reproducible two independent ways (§6 C/D). **CURRENT — adopted** as remaining capacity. *Label note:* "validation-excluded basis" is a **mislabel in effect** — the DEC chain never charged validation at all (§3 rules 7–8), so 38 is simply the DEC-chain basis; the label implies a distinction the chain does not make. The **value** is correct. |
| **121** | preflight §10; `exp008_preflight_audit.json.remaining_sc6_capacity.nominal_train_only`; DEC-030 §10 | `500 − 379` | n/a (capacity) | no | Inherits every defect of the 379 basis (smoke excluded contra DEC-011; B4-84 omitted contra DEC-016 C; 16 uncharged EXP-002 B0 rows included). **STALE / CONTRADICTED.** It is not "121 instead of 38 by different rounding" — it is a different *category mix*. |
| **−89** | preflight §10 (*"DEC-chain remaining −89"*); `exp008_preflight_audit.json.remaining_sc6_capacity.dec_chain_post007`; DEC-030 §10 | claimed "DEC-chain post-EXP-007 remaining" | n/a (capacity) | no | **Not reproducible, internally inconsistent with its own stated chain.** The preflight states *"336 spent pre-007, rem 164; EXP-007 executed 126"*, which yields `164 − 126 = 38`, **not** −89. Neither the preflight MD nor its JSON records any derivation, component list or ledger entry for −89; no artifact records a 127-execution charge, the size of the unexplained gap (`38 − 127 = −89`). **Recorded as an unexplained, non-reproducible artifact value — not silently discarded** (§8.1 gives its only candidate reading, explicitly unverified). |
| **184** | DEC-023 §8/§13 | DEC-023's frozen "remaining TRAIN cap: 500 − 336 = 184" | n/a (capacity) | no (historical) | **Arithmetically wrong when written**: `500 − 336 = 164`; 184 equals `500 − 316`, the ledger state *before* the EXP-001 charge. Already flagged by DEC-024 §3/§6 and corrected by DEC-025 §1. Preserved as recorded history; **not used** here. **STALE (superseded).** |
| **164** | DEC-024 §3 table; DEC-025 §1 | authoritative remaining **before** EXP-007 execution | n/a | yes *for its date* | Correct for the 2026-09-17 pre-execution state (`500 − 336`). Superseded by the execution of 126. **SUPERSEDED BY TIME.** |
| **24** | DEC-025 §12; DEC-026 §3/§14 | headroom at authorization time (`164 − 140`) | n/a | yes *for its date* | Correct as *authorization* headroom, computed against the **planned maximum** 140 — not against the executed 126. **SUPERSEDED BY TIME.** |
| **519** | preflight §10; `projected_total_illustrative` | illustrative projection `379 + 140` | n/a | no | Illustrative only; built on the rejected 379 basis, and **internally inconsistent** with the same artifact's `headroom_illustrative: −229` (which derives from 121). **ILLUSTRATIVE / INCONSISTENT.** |
| **−229** | preflight §10; `headroom_illustrative` | illustrative headroom under an unstated larger shape | n/a | no | The preflight sentence is cut off mid-derivation (*"headroom −229 (−103 even"*), so the 350-execution total it implies is recorded nowhere. **NOT REPRODUCIBLE / TRUNCATED DERIVATION.** |

### 8.1 The −89 gap: what can and cannot be said

- `38 − (−89) = 127` executions of category disagreement separate the 38 basis from the −89 value.
- The only *candidate* composition found anywhere in the repository that equals 127 is
  `96 (EXP-003 validation observations) + 16 (EXP-002 B0 references) + 15 (smoke live)`.
  **This is an unverified hypothesis**: no artifact or decision records any such 127-execution
  charge, and the smoke term contradicts DEC-011 (smoke is TRAIN-charged, so it is already inside
  the 232/336 chain and cannot also be the difference).
- Therefore −89 is **formally identified as unresolvable from cited evidence** and is superseded by
  the reconstructed `500 − 462 = 38`. Resolving it by assumption is exactly what this decision
  refuses to do.

### 8.2 Why 343 / 379 are not "the TRAIN-only truth"

Occasionally the 343/379 basis is defended as counting "TRAIN only". That defence fails on the
evidence: the basis **drops two TRAIN categories that a decision charged** (15 smoke by DEC-011,
84 B4 by DEC-016 C) while **adding a category no decision charged** (16 EXP-002 B0 rows). Dropping a
charged TRAIN category makes a figure *smaller than truth*, not *more conservative*; adding an
uncharged row makes it *larger than truth*. The two errors partially cancel — which is exactly why
121 *looks* plausible, and why the ledger rather than plausibility must decide. The identity
`121 − 38 = 83 = 15 + 84 − 16` isolates that cancellation precisely.

## 9. DEC-025 reconciliation (a time-slice, not an error to rewrite)

DEC-025 was correct **for 2026-09-17 before EXP-007 executed**; it is stale now. What it believed and
why:

- **Believed spent = 336.** DEC-025 §1/§11 re-derived it from the *raw* manifest sum
  (`232 = 15 smoke + 217 non-smoke`), commit `9e83742` for B4's 84, and `exp-001/spec.json`'s
  `"316 -> 336 of 500"`. It explicitly **refused** DEC-023's frozen 184 and substituted
  *"the ledger state before the EXP-001 charge"* as the explanation.
- **Why its remaining was 164:** `500 − 336 = 164` (DEC-025 §1, §12) — consistent with this
  reconciliation's step A.
- **Why its headroom was 24:** `164 − 140 = 24`, computed against the **planned maximum** 140 for
  EXP-007 (DEC-025 §12) — internally consistent.
- **Did it omit any experiment charge?** No omission within its own scope. EXP-002 (208 runs),
  EXP-003 (96 validation observations), EXP-005 (245 TEST) and EXP-006 (125 TEST) were all correctly
  outside SC6 then, exactly as they are now (§3 rules 7–8, §4.3). No *charged* register line existing
  at that date is missing from 336.
- **Is its arithmetic still valid after EXP-007?** `164` and `24` are time-slices, not errors:
  EXP-007 *consumed* capacity after they were written. The live reconciliation is
  `336 + 126 = 462`, `500 − 462 = 38`.
- **Was it superseded?** DEC-025's *budget statement* was superseded by an **execution performed
  under a later entry** (DEC-026's authorization), and its *remaining/headroom* figures are now
  historical. Its *method* — raw-manifest ledger, one global cap, no retroactive re-designation — is
  the method this decision continues.
- **DEC-025 remains unedited.** The staleness of 164/24 is recorded here as a **current
  reconciliation finding**, resolved by the new figures in §6 — not by rewriting DEC-025.
---

## 10. EXP-008 headroom — capacity computed, scope deliberately NOT frozen

DEC-030 §7 and §10 left **A3/A4 seeds, horizon, episode limit, cells, early-stop, Q0 source, arm set,
implementation and the charging rule** unresolved ("UNFROZEN — REQUIRES DECISION"). Only the
*charging rule* (§3) and the *remaining capacity* (38, §6 D) are inside this decision. Therefore an
A3/A4 execution plan is **not** frozen, authorized, or implied here.

**Authenticated current capacity: 38 charged live TRAIN executions.**

The following shapes are **HYPOTHETICAL ILLUSTRATIONS ONLY**. They assume DEC-023-parity episode
counts (5 epochs × 7 cells = 35 per arm-seed) purely to make the arithmetic legible. None of them is
a recommendation, a proposal, or an authorized count, and no reader may convert one into scope.

| # | Hypothetical shape | Charge | Fits 38? | Remaining after |
|---|---|---|---|---|
| H1 | one arm, 1 agent seed × 35 episodes | 35 | **yes** | 3 |
| H2 | DEC-023-parity single arm, 2 seeds × 35 | 70 | no | −32 |
| H3 | two arms (e.g. one A3 variant + A4), 1 seed × 35 each | 70 | no | −32 |
| H4 | DEC-023-parity A3 + A4 (2 arms × 2 seeds × 35) | 140 | no | −102 |
| H5 | three A3 reward arms + A4 at DEC-023 parity (4 × 70) | 280 | no | −242 |
| H6 | PLAN line 315 EXP-008 envelope (~300 runs) | ~300 | no | ≈ −262 |

**Reading:** the existing cap (as currently charged) can host only the smallest single-arm,
single-seed shape. Every multi-arm shape that the PLAN's own register line describes
(`docs/PLAN.md` line 315: *"EXP-008 | RQ4 | design matters | Train/Test | **A3, A4, A5** | **~300** |
ablation table | planned"*) is **irreconcilable with the remaining 38 while that envelope is charged
to the same 500**. Whether it must be charged to the same 500 is precisely the internal-PLAN conflict
DEC-011 §"Consequences" already recorded and DEC-010's precedence rule cannot arbitrate:

> DEC-011: *"The ablation set becomes A1–A4 … which first requires the operator to settle whether an
> A5 retrain is charged to SC6's ≤500 (PLAN line 45) or to EXP-008's ~300 (PLAN line 315). **That
> conflict is internal to PLAN; DEC-010's precedence rule cannot arbitrate it.**"*

and, for the envelope class:

> `docs/PLAN.md` line 101: *"| Spark executions | **150–300** | 1000s (infeasible) | ~600–900 total,
> cache-bounded |"*

**No illustrative count above is authorized. No de-scoping has been performed or prescribed.**

## 11. Budget policy decision (state)

**State: A-qualified.**

**State A** holds on the evidence: *the existing SC6 cap remains valid*, and current headroom is
**uniquely and reproducibly established** (462 charged / 38 remaining). The figures are not
ambiguous, so **State C (invalid/ambiguous accounting requiring amendment) is rejected**: the
contradictions were all in the *preflight/prose layer*, and every one of them is fully resolved from
authoritative records in §8 without changing a frozen rule.

**State B (headroom insufficient → de-scope) is NOT enacted here**, and cannot be, because
DEC-030 intentionally left the A3/A4 scope unfrozen: declaring headroom "insufficient" would require
first inventing the scope it is insufficient *for*, which this task forbids. Instead the insufficiency
is recorded as a **conditional on any future scope**:

- **`cap_amendment_required` = false** — no amendment is enacted, and none is required by the
  accounting.
- **`cap_amendment_required_if`** — a frozen A3/A4 plan charges **> 38** live TRAIN executions and is
  **not** de-scoped. Because `docs/PLAN.md` line 315 describes ~300 and PLAN line 45 caps SC6 at 500
  while 462 is already spent, any such plan requires **either** a formal **cap amendment** (a new DEC
  entry **plus** a PLAN amendment under the PLAN header's change-control rule) **or** an explicit
  decision that EXP-008 is charged to its own register line rather than to SC6's 500 — which is
  itself a **PLAN clarification amendment**, not a silent reading.
- **`de_scoping_required` = false** — nothing is de-scoped today; de-scoping becomes the alternative
  *if* the operator declines an amendment and freezes a > 38 plan.

**Cap increase is NOT applied and NOT assumed.** The 500 cap is raised by nothing in this document.
Any future increase must arrive as its own amendment (`docs/PLAN.md` line 45 + `configs/rl.yaml`
line 17 + a new DEC entry), and this reconciliation records that requirement explicitly rather than
performing it. **State D** is therefore partially operative as well: the PLAN-level envelope conflict
(§10) means an eventual amendment is *the likely mechanism*, but the accounting itself needs none.
## 12. Governance impact

| Item | Effect of this reconciliation |
|---|---|
| **DEC-030** | **Unchanged, not invalidated, not rewritten.** DEC-030 §10 anticipated exactly this separate budget decision; §11's `execution authorization: NO` and §9's A5 lock stand. Its methodology freeze (arm tables, isolation verdicts, seed/horizon/cells/Q0 left UNFROZEN) is untouched. |
| **EXP-008 methodology** | **Unchanged.** Seeds, horizon, episode limit, cells, early-stop, Q0 source, arm set and implementation remain UNFROZEN. This decision freezes the *charging rule* (§3) and the *remaining capacity* (§6) only — the two things that are B5. |
| **Experiment registry** | **Unchanged.** `experiments/registry.csv` is cited, not edited. |
| **PLAN** | **Unchanged by this document.** No line of `docs/PLAN.md` is edited. A PLAN amendment is *required later* only if a > 38-charged A3/A4 plan is frozen without de-scoping (or if the line-315 envelope is to be charged outside SC6). That amendment must use the PLAN header's own change-control mechanism — it is **not** performed here, because the governing documents for this task authorize reconciliation, not amendment. |
| **SC6 wording** | **Unchanged.** PLAN line 45 and `configs/rl.yaml` line 17 stand verbatim. |
| **Prior authorization boundaries** | **Unchanged.** DEC-024's refusal, DEC-025's reconciliation, DEC-026's authorization and its 140 ceiling all stand as recorded history; DEC-023's stale 184 stays inside DEC-023. No historical entry rewritten. |
| **Preflight / DEC-030 artifacts** | **Unchanged.** Their contradictory figures are *resolved*, not *edited*; this document supersedes their *figures* by adding a new authoritative statement, per the new-entry-only amendment rule. |
| **Is a new DEC sufficient?** | **Yes** for the budget question (B5). Appending this content to `DECISIONS.md` under the next unused DEC number is the remaining mechanical step and was **intentionally not performed by this task**. No file in `DECISIONS.md` was modified. |
| **Does the corrected budget change prior authorization boundaries?** | **No.** It adds a downstream constraint (§10–§11); it does not widen any earlier authorization. |

## 13. Non-authorization and firewall statement

- **EXP-008 execution: NOT AUTHORIZED — NO.** The gate chain to any future execution remains
  DEC-030 §12's four steps: (1) DEC-030 methodology freeze ✔; (2) **a separate budget DEC resolving
  B5 — supplied in content by this document, pending its own DEC entry**; (3) a separate
  implementation DEC resolving B6 with green zero-Spark tests (**NOT DONE — A3/A4 are UNIMPLEMENTED**);
  (4) a separate authorization DEC (DEC-031 or equivalent) with worst-case counts and ledger charge,
  plus a clean preflight re-run (**NOT DONE**).
- **A3/A4 implementation: NOT AUTHORIZED** and not implemented by this task.
- **A5: DISABLED** under DEC-011 (re-affirmed DEC-016 §7, DEC-023 §2, DEC-024 A5 row, DEC-025 §7,
  DEC-030 §9). `configs/rl.yaml` `gamma` remains 0.0.
- **Executions performed by this task: 0 Spark, 0 training, 0 TEST.** No RL code, training artifact,
  EXP-005/006/007 result, `PLAN.md`, or historical DEC entry was modified.
- **Cap: 500, unchanged.** No cap raise, no assumed re-scope, no experiment de-scoped by assumption.
- **Decision status: PASS — reconciliation complete.** Existing SC6 cap valid; accounting uniquely
  established (462 charged / 38 remaining); no cap amendment enacted; no de-scoping enacted;
  execution remains NO.
## 14. Validation

**Runner:** `scripts/reconcile_exp008_budget.py` — deterministic, read-only, zero-Spark, no network,
no clock/randomness inputs; `json.dumps(..., indent=2, sort_keys=True, ensure_ascii=True)` with a
forced `\n` newline for cross-platform byte stability.

**Executed twice:** output byte-identical.

```
run 1: 33236 bytes  SHA256 bd67da1735aaaa9d62ac977f2874034dca1f70db7da849db436b2ca939a596c5
run 2: 33236 bytes  SHA256 bd67da1735aaaa9d62ac977f2874034dca1f70db7da849db436b2ca939a596c5
BYTE_IDENTICAL = TRUE
```

**Machine assertions that must all hold (they gate the JSON write, so the artifact cannot exist if
any fails):**

1. 8 non-smoke training manifests sum 343 (`42+84+35+35+49+35+21+42`)
2. 6 smoke manifests sum 15 live (5 × 3 + 1 × 0)
3. manifest ledger pre-EXP-007 = `217 + 15 = 232` (reproduces DEC-011's composition)
4. `232 + 84 (B4) + 20 (EXP-001) = 336` (reproduces DEC-024/DEC-025's spent figure)
5. `35 + 35 + 35 + 21 = 126` (the four EXP-007 manifests; breakdown asserted key-by-key)
6. `336 + 126 = 462`; `500 − 462 = 38`
7. `343 + 20 + 16 = 379`; `500 − 379 = 121` (the rejected basis, reconstructed to prove the trace)
8. `121 − 38 = 83 = 15 + 84 − 16` (isolates the category disagreement)
9. EXP-002 attempts `208 = 192 grid + 16 reference` (189 COMPLETED, 19 FAILED)
10. EXP-003 validation observations 96; EXP-005 245/245; EXP-006 125/125 (all uncharged)
11. all 14 training manifests record `live_execution_cap = 500`
12. every B4/EXP-001 artifact field used is asserted (`split == "train"`,
    `observation_counts == {failed: 0, total: 84, usable: 84}`,
    `sc6_charge == "20 TRAIN executions (316 -> 336 of 500)"`, `total_planned == 20`)
13. governance anchors present in `DECISIONS.md` (`of the frozen 500`, `316 -> 336 of 500`,
    `9e83742`, `stands at 336/500`, `the ledger state before the EXP-001 charge`, `headroom: 24`,
    `headroom = 24`, `SC6 TRAIN ledger: 336/500`), matched against whitespace-normalised text so that
    line-wrapping in the document cannot mask a missing quote.
14. **charge-table closure**: the `experiment_charges` table's integer `authoritative_charge` column
    sums to **462**, independently equal to the cumulative charge derived from the manifest ledger.

**Independent cross-checks performed (two decompositions per figure):**

| Quantity | Path 1 | Path 2 | Agree |
|---|---|---|---|
| cumulative charged | `232 + 84 + 20 + 126 = 462` | `358 (all manifests) + 84 + 20 = 462` | ✔ |
| remaining capacity | `500 − 462 = 38` | `500 − (358 + 84 + 20) = 38` | ✔ |
| EXP-007 charge | four-manifest sum 126 | `140 max − 14 unexecuted = 126` | ✔ |
| rejected basis | `343 + 20 + 16 = 379` | `462 − 83 = 379`, with `83 = 15 + 84 − 16` | ✔ |
| charge table closure | `Σ experiment_charges = 462` | manifest-ledger cumulative `= 462` | ✔ |

**Acceptance gates:**

- [x] SC6 counting rule traced to authoritative sources (PLAN line 45; `rl.yaml` line 17; DEC-011/016/018/023/024/025/026 quoted)
- [x] Every experiment's budget charge independently reconstructed (§5)
- [x] EXP-007's 126 executions reconciled from raw manifests (§7)
- [x] 343 explained · [x] 379 explained · [x] 462 explained · [x] 38 explained · [x] 121 explained · [x] −89 explained (§8)
- [x] Stale figures explicitly identified (343-as-ledger, 379, 121, −89, 184, 164, 24, 519, −229)
- [x] No contradictory figure silently discarded (−89 recorded as unresolvable, its candidate reading flagged unverified)
- [x] Current cumulative charge uniquely established (462) under a stated, cited rule
- [x] Current remaining capacity uniquely established (38) by two independent decompositions
- [x] No A3/A4 execution plan silently authorized (every shape labelled hypothetical, §10)
- [x] DEC-030 not rewritten (nor any other DEC entry)
- [x] Execution authorization remains NO · [x] A5 remains disabled
- [x] No Spark executed · [x] No training executed · [x] No TEST executed
- [x] Deterministic rerun byte-identical (`bd67da17…a596c5`)
- [x] Amendment requirement recorded rather than assumed (`cap_amendment_required: false`, with an explicit trigger condition)

**Files created by this task (2):**

1. `docs/research/DAY37_EXP008_BUDGET_RECONCILIATION.md` (this document)
2. `results/evaluation/exp008_budget_reconciliation.json`
   (SHA256 `bd67da1735aaaa9d62ac977f2874034dca1f70db7da849db436b2ca939a596c5`, 33 236 bytes)

**Supporting runner added:** `scripts/reconcile_exp008_budget.py` (read-only accounting script; the
only executable artifact of this task).

**Stop.** This task ends here: no implementation, no DEC-031, no authorization.