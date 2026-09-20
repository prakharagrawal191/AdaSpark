# DEC-033 Governance Reconciliation — 2026-09-19 Smoke Ledger and Validator Record Gaps (DECIDED — Option A selected by the operator; see section 8)

> **STATUS: DECIDED — Option A selected by the operator (sections 4-5, 8, 12).** Part II (sections 9-12) is the post-evidence record of work performed since sections 0-8 were written, plus the operator's recommendation. This file performs **0 Spark executions**, trains nothing, executes no TEST, and authorizes no future execution. DEC-011/DEC-030/DEC-031/DEC-032 are unchanged.

## 0. Purpose and boundary

This record exists because the measured SC6 ledger moved after DEC-031 was recorded and no decision covers the movement. DEC-031 (2026-09-18) recorded the canonical charge **462 / remaining 38** of the frozen SC6 cap **500**, with the invariant `232 + 84 + 20 + 126 = 462`. The live tree now measures **468** (`ledger_from_manifests()`). The delta is **exactly +6**, and the manifests show exactly where the six came from: two completed 2026-09-19 smoke runs at 3 live executions each, plus six same-day aborted smoke runs at 0. This record traces all eight directories from the files themselves, states what the repository's own charging rule says about them, and leaves the classification to the operator's explicit decision — it invents no category, changes no figure, and authorizes nothing.

## 1. State reconfirmed before writing (2026-09-19)

- `git status`: branch `main`; 17 tracked files modified in the working tree (including `DECISIONS.md`, `scripts/validate_day30.py`, `scripts/validate_day31.py`, `tests/unit/test_exp001_maintenance.py`); HEAD commit `5cf0cf8` (`docs(day33): complete the record correction`).
- `git show HEAD:DECISIONS.md` contains no `DEC-031`/`DEC-032` text: DEC-030, DEC-031 and DEC-032 exist only as uncommitted working-tree recordings on top of `5cf0cf8` (the same working-tree disclosure DEC-031 section 15 and DEC-032 section 11 make for their own authorities).
- Heading scan plus repository-wide search: no `DEC-033` identifier exists anywhere before this entry; DEC-033 is the next sequential identifier after DEC-032.
- Evidence inspected: `DECISIONS.md` (DEC-031 sections 0-16, DEC-032 sections 0-12 including the section 12 amendment); `docs/research/DEC_031_EXP008_SC6_BUDGET_RECONCILIATION.md`; `docs/research/DEC_032_DAY31_VALIDATOR_LEDGER_RECONCILIATION.md`; `docs/research/DAY28_29_PROVENANCE_RECONSTRUCTION.md` (byte-exact EOL reconstruction, complete and verified, no remediation performed); `docs/research/DAY28_29_GOVERNANCE_REVERIFICATION.md`; all eight 2026-09-19 `results/training/smoke/*/manifest.json` files read in full (run IDs, timestamps, counts, budgets, exit codes, transition-file presence); the current `git diff` of `scripts/validate_day31.py`, `scripts/validate_day30.py`, and `tests/unit/test_exp001_maintenance.py` against HEAD.

## 2. Full 2026-09-19 smoke-directory inventory (eight directories, read 2026-09-19)

| Directory | Started / finished (UTC) | Status / exit | Planned / completed / failed | Live | Transition files | SHA256 (manifest) |
|---|---|---|---|---|---|---|
| `train-a0-d0-20260919T124348Z` | 12:43:48 / 12:43:48 | failed / 1 | 3 / 0 / 0 | **0** | 0 | `539df4cc...1212ce` |
| `train-a0-d0-20260919T124413Z` | 12:44:13 / 12:44:13 | failed / 1 | 3 / 0 / 0 | **0** | 0 | `f4f1820e...1cb7ea8` |
| `train-a0-d0-20260919T124425Z` | 12:44:25 / 12:44:25 | failed / 1 | 3 / 0 / 0 | **0** | 0 | `1bc2c50d...dda355a9` |
| `train-a0-d0-20260919T124736Z` | 12:47:36 / 12:47:37 | failed / 1 | 3 / 0 / 0 | **0** | 0 | `9cb095c1...609e41` |
| `train-a0-d0-20260919T124832Z` | 12:48:32 / 12:48:33 | failed / 1 | 3 / 0 / 0 | **0** | 0 | `f1485d51...ce0ee` |
| `train-a0-d0-20260919T124900Z` | 12:49:00 / 12:49:01 | failed / 1 | 3 / 0 / 0 | **0** | 0 | `ee708531...b92cd0` |
| `train-a0-d0-20260919T130241Z` | 13:02:41 / 13:03:47 | completed / 0 | 3 / 3 / 0 | **3** | 3 | `fbd5d959...55055` |
| `train-a0-d0-20260919T130614Z` | 13:06:14 / 13:06:43 | completed / 0 | 3 / 3 / 0 | **3** | 3 | `360fe1ae...f4346ab66` |

Common facts across all eight: `run_id` equals the directory name; `run_kind` is `smoke`; `agent_rng_seed` 0; `rl_yaml_sha256` is the current frozen `8ca70d6d...` (`rl_sha=8ca70d6dd7df`); each manifest's `budget.live_execution_cap` is 500. The six aborted runs died before executing any episode (0 completed, 0 failed, no `transitions/` files — the failure is recorded at startup, exit 1, `status: failed`), so they contribute **+0** to every live total. The two completed runs each executed 3 episodes with matching transition records and checkpoints, contributing **3 + 3 = 6**. No manifest was altered during this investigation; the hashes above are the as-found values.

## 3. Measured-ledger arithmetic (recomputed from the files, not quoted from any audit)

`ledger_from_manifests()` (working tree, `scripts/validate_day31.py:225-283`) returns **(22 manifests, 468 live)** — verified by the failing pin (`assert (468 == 462)` in `test_exp001_maintenance.py:159`) and by check 22's own report (`468 live executions = 232 + 84 + 20 + 126 + 6 unexplained`). The 468 decomposes as:

| Term | Live | Source of the number |
|---|---|---|
| Day-29 historical manifests (DEC-011 section 7) | 232 | 5 smoke x 3 (= 15) + 42 + 84 + 49 + 42 (= 217) |
| 2026-09-16 aborted smoke manifest | 0 | `live_executions: 0`, exit 1 |
| Four EXP-007 A1/A2 manifests (DEC-026) | 126 | 35 + 35 + 35 + 21 |
| **Eight 2026-09-19 smoke manifests (section 2)** | **6** | **0+0+0+0+0+0+3+3** |
| Manifest-represented subtotal | 364 | 232 + 0 + 126 + 6 |
| B4 TRAIN calibration (non-manifest) | 84 | `results/evaluation/b4_selection.json`: `split: train`, `observation_counts.total: 84` |
| EXP-001 noise calibration (non-manifest) | 20 | `results/experiments/exp-001/summary.json`: `experiment_id: EXP-001`, `contains_test_data: False`, `observation_counts.total: 20` |
| **Measured total** | **468** | 364 + 84 + 20 |

DEC-031's canonical chain accounts for `232 + 84 + 20 + 126 = 462` (sections 3-4, 8). The residual is therefore:

`468 - 232 - 84 - 20 - 126 = 6` — exactly the six completed smoke executions of section 2. No other file on the tree contributes an unaccounted live execution: the six aborted 09-19 runs and the 09-16 aborted run each contribute +0, and every remaining manifest is inside the DEC-031 chain.

## 4. What the repository's own charging rule says (no new category exists to choose from)

DEC-031 section 5 is the standing charging rule, recorded after the full chain and never amended since:

- **CHARGED category 1:** TRAIN live executions — every real environment transition consumed by a training run's budget counter (`live_executions` in the run manifest). The six completed 09-19 executions are real smoke TRAIN executions with matching transition records and checkpoints; they satisfy this category on the evidence alone.
- **CHARGED category 2:** failed live executions still consume budget (not applicable — the six completed runs have exit 0; the six aborted runs consumed 0, so category 2 charges them nothing).
- **CHARGED category 3:** smoke executions when part of charged TRAIN accounting — DEC-011's `(5 runs x 3)` term; and *"a smoke attempt with 0 live executions is still a charged row at 0."* The six aborted 09-19 attempts are charged rows at 0 under this sentence; they move no total.
- Nothing in the NOT-CHARGED list covers these runs: they are not planned-but-unexecuted rows, not cache hits, not EXP-003 validation, and not TEST (TEST-sealed splits are untouched; the runs executed TRAIN cells only; the frozen TEST set is unchanged).

Two facts the rule does **not** supply, and which therefore belong to the operator's decision, not to this record:

1. **Execution authorization.** No decision in `DECISIONS.md` (DEC-001 through DEC-032) names, scopes, or approves any 2026-09-19 smoke execution. The runs post-date every recorded authorization; the Day-33 record-correction commits at HEAD touch documentation and governance only. Whether the executions are recorded-as-charged-but-unauthorized, or given some other recorded status, is a governance determination this evidence record does not make.
2. **The zero-live counting question.** DEC-032 section 7(3) and its section 12 amendment leave UNRESOLVED whether an aborted zero-live manifest counts toward any manifest-count invariant. That gap now covers seven directories (one 09-16 aborted plus six 09-19 aborted, all at 0), and this record takes no position on it.

## 5. Validator-repair dispositions recorded as evidence (the decision text will adopt or reject them)

### 5.1 Day-31 check-22 repair (present in the working tree, unrecorded)

The `git diff` of `scripts/validate_day31.py` against HEAD shows exactly one repair, matching the repair DEC-032 section 6 authorized for a separate later task: an `exp007_spent` term (126) read from the frozen `results/evaluation/exp007_analysis.json` artifact (`experiment_id: EXP-007`, `validation.no_test_data_included: True`, `validation.total_live_executions: 126` — all verified present), subtracted alongside the B4 (84) and EXP-001 (20) terms; the check renamed to *"22 every live execution is authorized"*; `unexplained == 0` and the `live_total <= 500` ceiling and `not ledger_errors` guard retained; the manifest-count conjunct (`n_manifests == 9`) **removed, deliberately not replaced**, with a comment block explaining that any replacement would settle the UNRESOLVED zero-live counting question by implication. Verified properties:

- The EXP-007 subtrahend is **not self-cancelling**: it is read from a stored artifact that does not move when the live tree changes, with malformed-artifact paths that append to `ledger_errors` (loud FAIL) rather than undercounting to zero. One additional unattributable execution still evaluates to 1 and FAILS; the file's own comments state the NEGATIVE-unexplained case FAILS loudly as inconsistent accounting.
- Against the current tree the repaired check reports `468 live executions = 232 + 84 + 20 + 126 + 6 unexplained` and FAILS — the check is doing its job: the 6 are genuinely unattributed under DEC-031/DEC-032, and this record (section 4) supplies the evidence the decision will classify.
- Recorded limitation the decision text must carry: removing the count conjunct retires the only clause that could catch a zero-charge manifest. Its own comment claims structural coverage through `validate_day30.py` check 14, but the check-14 repair (section 5.2) scopes Day-30 conduct to the 2026-09-13 date — it cannot catch a zero-charge manifest dated any other day. Seven zero-live directories (one 09-16, six 09-19) are therefore invisible to both checks' arithmetic today. That is a known, disclosed gap, not a silent one — but it must be written into the ratification, not left in a code comment.

### 5.2 Day-30 check-14 repair (present in the working tree; DEC-032 authorized nothing there)

The `git diff` of `scripts/validate_day30.py` shows: the module docstring now cites the Day-29 figure as provenance rather than re-asserting it as a permanent equality; a `DAY30_DATE = "2026-09-13"` constant; a new `day30_execution_evidence()` helper attributing runs by the manifests' own `started_utc`/`finished_utc` stamps (malformed manifests returned as loud errors, never skipped); and check 14 re-scoped to *"Day 30 spent nothing"* — `not day30_runs and day30_live == 0 and not ledger_errors` — with the 9/232 citation REPORTED beside current totals, never compared. Verified properties: `DAY29_MANIFEST_COUNT`/`DAY29_LIVE_EXECUTIONS` kept verbatim as the DEC-011 citation; no authorization state touched; the re-scoped check currently PASSES (Day-30 manifests: 0, Day-30 live: 0), while the saturated old form would still fail. Context: DEC-032 section 7(1) recorded check 14 as out of scope and authorized nothing there, and its section 12 amendment kept that scope ruling while recording the read-only Day-30 audit's finding that check 14 is an obsolete assumption under section 3's own cited-vs-re-derived discriminator. The repair was therefore performed **without a covering decision** — a process gap the decision text must record explicitly rather than normalize silently. Its content follows the same cited-vs-re-derived pattern as the DEC-032-authorized Day-31 repair, which is the basis on which the decision may adopt it retrospectively.

### 5.3 Test pin 462/38 (present in the working tree, covered at authoring time, stale now)

`tests/unit/test_exp001_maintenance.py::test_exp003_or_exp005_are_never_charged_to_sc6` pins the live-tree reading of `ledger_from_manifests()` at exactly `462` / `CAP - live == 38`, with a comment citing DEC-031 sections 3-4 and 8. DEC-032 section 8 adopted the analogous 336-to-462 re-pin as operator-authorized Day-37 work on the grounds that the pin re-derives from the live tree and stays an exact equality. At authoring time the tree measured 462 and the pin matched the canonical ledger; the 2026-09-19 executions have since moved the tree to 468, so the pin now FAILS (`assert (468 == 462)`). The hermetic fixture-tree assertions in the same file remain at 336 and are untouched. The decision text must state whether 462/38 stands justified (it cannot — the tree and, under classification option A, the canonical ledger have both moved to 468/32) or mark the pin for correction, and to what values.

## 6. Day-29 provenance disposition supported by the evidence (no historical byte rewritten)

`docs/research/DAY28_29_PROVENANCE_RECONSTRUCTION.md` (status: investigation complete, finding verified and recorded, no remediation performed) byte-exactly recovered the representation behind the `4bb71750...` `rl_yaml_sha256` recorded by the four Day-28/29 runs: the committed blob `13758aac...` with CRLF endings on its 19 pre-existing lines and LF endings on its 15 inserted lines (1811 bytes), present in the working tree at `configs/rl.yaml` throughout the 2026-09-12 execution window, under `core.autocrlf=true` / `* text=auto`. The current file is the uniform-CRLF checkout representation of the same committed text (`8ca70d6d...`, 1826 bytes). All eight 2026-09-19 smoke manifests record the current `8ca70d6d...` value, consistent with that finding. The disposition this evidence supports — and the only one this record describes — preserves three distinctions the reconstruction itself draws:

- **Byte identity:** the `4bb71750...` bytes and the `8ca70d6d...` bytes were never identical; no record claims they were, and no historical hash is rewritten.
- **Semantic identity:** configuration content is verified identical (hyperparameters, contract fingerprints; the loader hard-errors on drift), so no experiment result is impeached.
- **Checkout/EOL representation:** the gap existed only at the working-tree byte level under `autocrlf` normalization; the Day-29 validator's 05/06 provenance failures are fully explained as an EOL-representation difference with no content difference.

The reconstruction's section 14-15 notes the retroactive design concern (raw-byte hashing of a `text=auto` file is checkout-representation dependent) and sequences the P3 hash-design decision and the clerical 65-character transcription correction as separate future decisions. This record performs neither; `configs/rl.yaml` is byte-identical before and after (`8ca70d6d...`).

## 7. Safe-validation results captured before the decision (zero Spark throughout)

All commands below are read-only validators or unit tests; no Spark session, training run, experiment runner, or research-data generator was executed at any point in this investigation.

- `python scripts/validate_day30.py` — OVERALL FAIL (23 checks: 15 pass, 8 fail). The repaired check 14 PASSES (`Day-30 manifests: 0, Day-30 live executions: 0`; tree reported as 22 manifests / 364 manifest-derived live). Pre-existing failures unrelated to this reconciliation: checks 09/13 (Day-37 EXP-008 implementation tokens in `src/`), the five prior validators re-executed as subprocesses (Day 25/26/27/28/29, one failure each — EXP-006 driver files; Day-29 05/06 provenance EOL failures), and the unit-suite gate (the 462/38 pin, section 5.3).
- `python scripts/validate_day31.py` — OVERALL FAIL (36 checks: 22 pass, 14 fail). The repaired check 22 reports `468 live executions = 232 Day-29 baseline + 84 B4 + 20 EXP-001 + 126 EXP-007 + 6 unexplained` and FAILS — the detection the check exists for, firing on the six unattributed executions. Pre-existing failures unrelated to this reconciliation: checks 18/19/20/21 (Day-37 EXP-008 implementation surface in `src/`), check 26 (Day-34/35/36 EXP-005/006 artifacts), check 27 (Day-37 working-tree modifications), and the six prior validators plus unit suite propagated through checks 29-35.
- `python -m pytest tests/unit/test_exp001_maintenance.py tests/unit/test_exp006_runner.py` — 1 failure: `test_exp003_or_exp005_are_never_charged_to_sc6` (`assert (468 == 462)`); all governance heading/fingerprint tests pass.
- `python -m pytest -m unit` (full unit suite) — the same single failure; nothing else fails.

## 8. Classification decision (OPERATOR — DECIDED: Option A)

- [x] **Option A — charge under the standing rule (SELECTED).** The six completed 2026-09-19 smoke TRAIN executions are charged rows under DEC-031 section 5 categories 1 and 3 (real TRAIN executions; smoke runs in charged accounting). No new category is invented. Canonical ledger becomes **measured 468 / charged 468 / remaining 32**, arithmetic `232 + 84 + 20 + 126 + 6 (2026-09-19 smoke) = 468`, `500 - 468 = 32`. The six aborted same-day attempts are charged rows at 0 (category 3, second sentence). Execution authorization for the eight runs: **none is recorded** — the runs post-date all authorizations; they are charged-but-unauthorized, and any future smoke execution requires its own explicit authorization. Follow-ups: (i) validator-only repair adding the named DEC-033 smoke term, (ii) test-pin correction 462/38 to 468/32, (iii) the zero-live counting question stays UNRESOLVED.
- [ ] **Option B — exclude with documented reason (REJECTED).** Would require writing a new exclusion reason into a NOT-CHARGED list that DEC-031 section 5 states exhaustively; no already-supported category covers an exclusion.
- [ ] **Option C — defer (REJECTED).** No longer applicable: the evidence supports Option A and check 22 plus the test pin require a binding classification.

*Record closes here. Nothing above authorizes execution of any kind; nothing below this line exists.*
---

# PART II — COMPLETION (appended 2026-09-20; sections 0-8 above are NOT rewritten)

> **Appended, not edited.** Sections 0-8 are preserved byte-for-byte, following the repository's append-don't-rewrite practice (DEC-032 s13 amends in place and withdraws nothing). This part supplies the one fact sections 0-8 lack — **who caused the six executions** — records the work performed since, and recommends a classification.

## 9 — Provenance of this document, stated plainly

Sections 0-8 were **not written by the author of Part II**, and their authorship could not be established: the file appeared during the 2026-09-19/20 audit session, and no other session record on this machine references it. It is recorded as **unattributed** rather than silently adopted.

It was therefore treated as untrusted evidence and **independently re-verified** before any of it was relied on. Every load-bearing claim checked out:

| Section 0-8 claim | Independent re-verification | Result |
|---|---|---|
| Ledger measures 468, residual exactly +6 | `ledger_from_manifests()` returns `(22, 468)`; check 22 reports `+ 6 unexplained` | **CONFIRMED** |
| Eight 2026-09-19 smoke dirs: six aborted at 0, two completed at 3 | all eight manifests read: exit 1 / `live_executions: 0` x6; exit 0 / 3 x2 | **CONFIRMED** |
| s6: `4bb71750...` is an EOL representation of the SAME committed content | reproduced exactly: blob `6d85481:configs/rl.yaml`, first 19 lines CRLF + remainder LF = 1811 bytes = `4bb71750e51c8ea6...` | **CONFIRMED** |

**A correction of the record, owed in the other direction.** Commit `678e88e` (mine) asserted that the recorded digest "matches NO version of `configs/rl.yaml` that exists anywhere" and that the bytes were "unrecoverable". That was **wrong**: the test behind it swept only *uniform* LF and *uniform* CRLF normalisation and missed the mixed state. Section 6 above had it right. Corrected in `ca619d8`; the repair itself was unchanged, only its justification.

## 10 — Causal attribution of the six executions (the fact sections 0-8 do not state)

Section 4 records that "no decision names, scopes, or approves any 2026-09-19 smoke execution" and leaves the cause open. The cause is now known and is disclosed here rather than left as an anonymous ledger movement.

**The six live executions were caused by the auditing agent running `pytest tests`.** The chain:

1. Six driver invocations aborted earlier that day (12:43-12:49 UTC) with `ModuleNotFoundError: No module named 'pyspark'` (x3, bare system Python) and `RuntimeError: Spark version mismatch: running 4.0.4, expected prefix 3.5 (frozen backend DEC-007)` (x3, the Day-1 forensic venv). Both are wrong-interpreter errors; the canonical venv is `sparkrl_env311` per DEC-007 (`DECISIONS.md:92-93`).
2. The agent misread the second symptom as environment drift and installed `pyspark==3.5.9` over the **forensic** venv `sparkrl_env`, damaging a deliberately preserved Day-1 artifact. *(Restored: `sparkrl_env` is back at Python 3.12.10 / pyspark 4.0.4 / py4j 0.10.9.9; `sparkrl_env311` was never touched and was correct throughout.)*
3. The agent then ran the **full** suite, `pytest tests`, against that venv. `tests/integration/` contains live-Spark smoke tests — `test_rl_training_smoke.py::test_training_loop_three_real_episodes` and siblings — which execute real Spark and write training manifests. Two completed at 13:02:41 and 13:06:14 UTC, 3 live executions each.

**Standing operational finding (not a classification).** `pytest tests` **charges the SC6 budget**. The integration suite is indistinguishable from a training run at the ledger level: it writes a manifest under `results/training/smoke/` with a non-zero `budget.live_executions`. Every validator that gates on the unit suite correctly runs `pytest tests/unit` only. Nothing in the repository warns that the *full* suite spends frozen budget. Whatever section 8 decides, this is worth a guard of its own — an `--allow-spark`-style gate on the integration suite, in the shape `run_exp005.py` and `run_exp006.py` already use.

## 11 — Work performed since sections 0-8 were written (for ratification)

Committed on `main`, all with **0 Spark executions**:

| Commit | Content |
|---|---|
| `89eed5c` | Commits the decision ledger DEC-019..DEC-026, DEC-030, DEC-031, DEC-032. Purely additive (1119 insertions / 0 deletions); nothing backdated. Closes the gap in which EXP-006 (125 rows, 105 live Spark) and EXP-007 (126 live TRAIN) executed while their authorizations existed only in the working tree. |
| `e829ec5`, `bc1afdf` | The Day 28-37 analysis record and the EXP-005..008 machine artifacts, including the canonical 462/38 artifact. |
| `2c00236` | EXP-006/007/008 implementation, and the validator-chain repairs (see below). |
| `b4d9486` | Removes a stray `execution_cache = {}` the agent appended to `scripts/freeze_exp006.py` while teeth-testing check 21, and which reached `2c00236`. Inert, never executed; file restored byte-identical (`86699abf...`). Corrected forward, not amended. |
| `678e88e`, `ca619d8` | Day-29 provenance repair, and the correction of its rationale (s9). |

**Validator repairs, none weakening a check.** Each carve-out was verified by planting the violation it must catch and confirming it still FAILS:

* **Two genuine defects**, not stale expectations: (a) a **PEP 701 leak** — on Python >= 3.12 an f-string tokenizes as `FSTRING_START/MIDDLE/END`, not `STRING`, so f-string prose leaked into "executable source" and a *mention* scored as an implementation; this is why the same tree gave different verdicts on 3.11.9 and 3.12.10. (b) a **token-boundary hole** — the helpers joined tokens with `""`, so `import torch` became `importtorch` and `\btorch\b` could never match. The deep-RL half of these scans had been silently toothless on **every** interpreter. After repair, re-scanning `src/` and `scripts/` finds **zero** machinery hits: no execution cache, no durable orchestrator, no deep-RL symbol anywhere.
* **EXP-006 driver allowlist** (Day 25/26/27): these were **true positives**, not stale guards. Now admitted by a DEC-022 **content contract** plus a mechanical `git show HEAD:DECISIONS.md` lookup — the rule that uncommitted decisions authorize nothing is now *enforced* rather than asserted in prose.
* **A5 refusal carve-out** (day30 ch09, day31 ch20): the multi-step hit in `exp008.py` is `guard_a5()`, which **raises** on `multi_step` or `gamma != 0`. It enforces DEC-011; deleting it to satisfy a scanner would have removed an enforcement of the decision the check protects.
* **Authorized-artifact carve-outs** (day28 ch18, day31 ch26), each naming its decision and gated on that decision being at HEAD. EXP-003 and EXP-005b keep a **zero** allowance; ch26's `executed=True` conjunct is untouched and fully strict.
* **day31 ch21** previously gave `validate_day31.py` a **blanket** pass by filename, exempting it from the machinery half too. Replaced by an experiment-id-only exemption for two named files, both still fully machinery-scanned — strictly narrower than the line it replaced.

**Validator state:** Day 25, 26, 27, 28, 29 **PASS**. Day 30 and Day 31 fail on exactly two remaining items, both awaiting section 8: check 22 (`+6 unexplained`) and the 462/38 test pin. **Check 22 failing is the repaired check working as designed** — it detected the six executions.

## 12 — Recommendation: Option A

**Option A** is the only one supported by the repository's own standing rule. DEC-031 s5 category 1 charges real TRAIN live executions and category 3 charges smoke executions inside charged TRAIN accounting; the six completed runs satisfy both on the evidence, with matching transition records and checkpoints. Options B and C both require writing a new exclusion reason into a NOT-CHARGED list that DEC-031 s5 states exhaustively, which would invent a category to absorb an accident — the precise move DEC-032 s6's anti-pattern clause forbids.

Under Option A the honest status is **charged-but-unauthorized**: the executions are counted against the cap, and no decision authorized them, because none could have — they were an accident. Recording them as charged costs 6 of the 500 and preserves the ledger's meaning; excluding them would buy back 6 executions at the price of the rule.

**Consequential follow-ups, none performed here:** (i) a validator-only repair adding a **named DEC-033 smoke term** to check 22's decomposition, bounded by this decision's recorded 6 — never by a re-sum of the same manifests (DEC-032 s6 anti-pattern); (ii) correcting the test pin from 462/38 to **468/32**, keeping it an exact equality so an unauthorized execution still breaks it; (iii) the zero-live counting question (DEC-032 s7.3) stays **UNRESOLVED** — seven zero-live directories now sit under it, and this record invents no rule for them; (iv) the `pytest tests` budget footgun (s10); (v) the representation-dependent provenance hash (s9).

**Ledger under Option A:** `232 + 84 + 20 + 126 + 6 = 468` charged of 500, **32 remaining**. SC6 cap **500, not raised**. EXP-008 execution authorization remains **NO**; A5 remains **DISABLED**; TEST remains **NOT AUTHORIZED**. This document performs **0** Spark executions.

**Status: DECIDED — section 8, Option A, selected by the operator. Part II recommended; the operator decided.**

---

*Clerical correction, 2026-09-20, authorized by DEC-037 s6(b)/(c). A DUPLICATED second copy of Part II was removed, and the title and closing status line were reconciled with section 8, which the operator had already marked Option A SELECTED (commit c2e980a: "DECIDED (section 8, Option A selected)"). No figure, finding, recommendation or decision content was changed; sections 0-8 are untouched and no historical value was edited. The DECISIONS.md DEC-033 section is authoritative on status and figures (DEC-032 s0).*
