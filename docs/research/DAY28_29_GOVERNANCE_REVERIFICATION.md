# Day 28/29 Governance Re-Verification — Day-28/Day-29 Validator Outcomes, rl.yaml Provenance Chain and Checkout-Byte Dependence

**Status:** research-governance record. Findings **verified and recorded**. **No remedy performed.** No validator, manifest, configuration, artifact, ledger or decision entry was modified by this record.

> **Boundary.** This entry performs 0 Spark executions, trains nothing, executes no TEST, creates no run directory, and modifies no result artifact, no manifest, no validator, no configuration file and no decision entry. Its only filesystem effect is this document. Nothing here repairs, prescribes an implementation, or authorizes anything; section 8 records remediation strictly as candidate future work.
>
> **Method.** Every load-bearing claim below was re-verified against the working tree before being recorded: both validators were re-run (each is read-only with respect to the repository — its only file writes are scratch files under the system temp directory, never the project tree), every training manifest named below was re-read, and every hash below was recomputed from raw file bytes via `hashlib.sha256(...read_bytes())`. Where an input finding and the tree disagreed on any detail, the tree was treated as authoritative and the reconciliation is stated explicitly in the relevant section (one such reconciliation exists, in section 4.3).
>
> **Evidence-status legend.** Every claim is labelled **[V] verified** (directly re-established against the tree in this session), **[I] inferred** (a conclusion that follows from verified facts, marked as inference) or **[U] unknown** (a question the available evidence does not answer). No commit ID, timestamp, hash, experiment result or historical file is asserted beyond what this session verified or what the cited artifact itself records.

## 1. Day-28 validator outcome — [V] verified

`python scripts/validate_day28.py` re-run 2026-09-19: OVERALL **FAIL — 19 passed, 0 skipped, 1 failed of 20** (exit 1). The single failure:

    18 no_exp003_005                 FAIL  ['results/experiments/exp-005', 'scripts/run_exp005.py']

* **[V]** The check is defined at `scripts/validate_day28.py:504-510` ("18. EXP-003 / EXP-005 / EXP-005b remain unstarted"). It is a **path-based detector**: it globs `scripts/*exp00[35]*`, `results/experiments/*exp-00[35]*` and `src/**` (`rglob("*exp00[35]*")`) and fails if any path matches. It reads no file content.
* **[V]** Both reported paths genuinely exist: `results/experiments/exp-005` (directory) and `scripts/run_exp005.py`.
* **[V]** The match is mechanical: `run_exp005.py` matches `*exp00[35]*` (the `[35]` character class admits `5`), and `exp-005` matches `*exp-00[35]*`.
* **[V]** Therefore the failure is a **true positive against the current Day-28 validator rule**: the rule asserts that no EXP-003/EXP-005/EXP-005b script or artifact exists, and such paths do exist. This is **not** evidence of a scanner false positive, and this record makes no false-positive claim for check 18.
* **[I]** The rule's premise ("remain unstarted") no longer describes the tree: the EXP-005 work stream has since executed and produced records under `docs/research/` (`DAY33_EXP005_DRY_SLICE.md`, `DAY34_EXP005_ANALYSIS.md`) and artifacts under `results/experiments/exp-005/`. The Day-28 rule predates that work and has not been re-baselined since.
* **Out of scope:** whether check 18 should be re-baselined is remediation, not decided here (section 8, candidate R2). This record decides nothing about it.

## 2. Day-29 validator outcome — [V] verified

`python scripts/validate_day29.py` re-run 2026-09-19: OVERALL **FAIL — 24 checks, 20 pass, 4 fail, 0 skip** (exit 1). The four failures:

    05/06 run seed 0 provenance      FAIL  rl_yaml_sha256 does not match configs/rl.yaml
    05/06 run seed 1 provenance      FAIL  rl_yaml_sha256 does not match configs/rl.yaml
    05/06 run seed 2 provenance      FAIL  rl_yaml_sha256 does not match configs/rl.yaml
    20 no future components          FAIL  found in: src\sparkrl\evaluation\orchestration.py, src\sparkrl\experiments\spec.py, src\sparkrl\rl\env.py

* **[V]** The validator emits exactly 24 check rows: numbered checks 01-20, where `05/06 run seed {0,1,2} provenance` is emitted three times by a loop over `M8_SEEDS = (0, 1, 2)` (`scripts/validate_day29.py:406-407`), as is `DEC-010 seed {0,1,2} failure semantics` (line 535). The 20/24 accounting is exact.
* **[V]** The three provenance rows fail **solely** on the comparison at `scripts/validate_day29.py:259-260` (`m.get("rl_yaml_sha256") != rl_yaml_sha256()`); every other provenance sub-check (schema, seeds, status, versions, schedule, frozen hyperparameters, Q0 provenance, contracts) passes for all three runs.
* **[V]** The three gated runs are the Day-29 replicates `train-a0-d0-20260912T112906Z` (seed 0), `train-a1-d0-20260912T115123Z` (seed 1) and `train-a2-d0-20260912T120648Z` (seed 2) — which are also the **three full-state EXP-007 reference runs** (`state-v1.5`, `q0-exp002/v1`; named `FULL-s0/s1/s2` at `scripts/analyze_exp007.py:65-72` and listed as the only three full-state runs in the frozen record by `docs/research/DAY36_EXP007_ANALYSIS.md`). The **fourth** affected run — the Day-28 run of record `train-a0-d0-20260912T083120Z` — is not gated by `validate_day29.py`; it is gated by `validate_day28.py`, which contains no `rl_yaml_sha256` check at all (verified by search).
* **[V]** Check 20 reports exactly `orchestration.py`, `spec.py` and `env.py`. Its mechanism and defect status are the subject of section 3.
* **Interpretation.** The three provenance failures are a **legitimate current provenance failure** — the manifests really do record a hash that today's `configs/rl.yaml` bytes do not produce — and must not be silently read as a research-history violation. Check 20 is the opposite: a scanner/gating defect. The two failure classes are distinct and are kept distinct throughout this record.

## 3. Day-29 check 20 — confirmed scanner/gating defect (PEP-701) — [V] verified mechanism

Check 20 is `scripts/validate_day29.py:528-530`, implemented by `_src_free_of_future_components` (lines 316-346): it strips comments and strings from every `src/**/*.py` file and regex-scans the remainder for `FORBIDDEN_CODE` (defined at lines 103-109, an alternation of deep-RL/cache/orchestrator/EXP-003/005/005b terms). The stripper keeps only tokens whose type is not `tokenize.COMMENT` and not `tokenize.STRING`.

* **[V]** Under Python 3.12 (PEP-701), f-strings tokenize as `FSTRING_START` / `FSTRING_MIDDLE` / `FSTRING_END` rather than a single `STRING` token. `FSTRING_MIDDLE` — the literal text of an f-string — is **not** `tokenize.STRING`, so f-string literal text escapes the stripper and is scanned by the regex.
* **[V]** Independent re-execution of the same algorithm (same regex, same tokenize-based stripping) over `src/` reproduces the failure exactly: the three files reported by check 20 are the only three files in `src/` that trip the matcher, and in each case the matching token is `FSTRING_MIDDLE` carrying a case-insensitive `EXP-003` mention inside an f-string **error-message literal**:
  * `src/sparkrl/evaluation/orchestration.py` line 40 — `FSTRING_MIDDLE` containing `exp003-` (run-id template text in a f-string);
  * `src/sparkrl/experiments/spec.py` line 91 — `FSTRING_MIDDLE` containing `EXP-003` (validation error-message text);
  * `src/sparkrl/rl/env.py` line 209 — `FSTRING_MIDDLE` containing `EXP-003` (guard-message text naming validation as EXP-003's domain).
* **[V]** All three matches are prose inside string literals, not implementations: no forbidden component is implemented in these files because of that text, and the matcher assigns no semantics beyond token mention.
* **[V]** The sibling Day-28 check (`scripts/validate_day28.py:491-502`, check 17) uses a narrower `FORBIDDEN_CODE` (its alternation omits the `exp003`/`exp-003`/`exp005`/`exp-005`/`exp005b`/`exp-005b` terms entirely) and therefore passes on the same tree — which is why check 17 passes (19/20) while Day-29 check 20 fails (20/24). Day-28's check 18 finds EXP-005 by **path**, a separate detector.
* **[V]** No prior repository record documents this mechanism: a search of `docs/research/*.md` and `DECISIONS.md` for f-string/FSTRING/tokenize/PEP-701 returns nothing. This document is the mechanism's first repository record; the label "PEP-701 / scanner issue" has no prior in-repo occurrence.
* **[V]** The backend is frozen at **Python 3.11.9** by DEC-007 (`DECISIONS.md`, "DEC-007 | 2026-09-07 | Spark backend freeze"); the interpreter that executed both validators in this session is **Python 3.12.10**.
* **[I]** The defect is a property of the validator's matcher combined with the Python-3.12 tokenizer, not of the scanned code: PEP-701 f-string tokenization (`FSTRING_MIDDLE`) is a Python-3.12 tokenizer behavior, so under a 3.11-line tokenizer the same f-string literals would be emitted as `STRING` tokens and stripped by the same code. Check 20's outcome is therefore interpreter-dependent. [U] Which interpreter version the original operator-side observation of this failure used is not recorded anywhere in the repository.
* **Interpretation (bounded).** Check 20's failure is a **scanner/gating defect** (a false positive of the current rule) and is recorded as such — **not** treated as a research-history violation. **Scope note [V]:** `scripts/validate_day31.py:118` chains `validate_day29.py` as a subprocess check, so this defect currently also propagates into the Day-31 governance gate's verdict. Whether and how check 20 should be repaired is remediation, not decided here (section 8, candidate R1).


## 4. rl.yaml provenance chain — [V] verified

### 4.1 The two recorded hashes

All eight training manifests in `results/training/*/manifest.json` (i.e., excluding the six smoke manifests under `results/training/smoke/`, see 4.4) record one of exactly two `rl_yaml_sha256` values:

    4bb71750e51c8ea605f7feaaa368a2f1dcbe4ecd2aacbeed0f059f8d18cfb5a14   (4 runs)
    8ca70d6dd7df68841c409a4441dc538616206bccea7877b28c73df20e6428b80   (4 runs)

* **[V]** The split is exactly 4 + 4, and the run-to-hash mapping is:

| Run directory (`results/training/…`) | `rl_yaml_sha256` | Role |
|---|---|---|
| `train-a0-d0-20260912T083120Z` | `4bb71750…` | Day-28 run of record (42 eps) |
| `train-a0-d0-20260912T112906Z` | `4bb71750…` | Day-29 replicate seed 0 (84 eps); EXP-007 full-state reference FULL-s0 |
| `train-a1-d0-20260912T115123Z` | `4bb71750…` | Day-29 replicate seed 1 (49 eps); EXP-007 full-state reference FULL-s1 |
| `train-a2-d0-20260912T120648Z` | `4bb71750…` | Day-29 replicate seed 2 (42 eps); EXP-007 full-state reference FULL-s2 |
| `train-a0-d0-20260917T055042Z` | `8ca70d6d…` | EXP-007 A1-s0 (35 eps) |
| `train-a1-d0-20260917T060047Z` | `8ca70d6d…` | EXP-007 A1-s1 (35 eps) |
| `train-a0-d0-20260917T061316Z` | `8ca70d6d…` | EXP-007 A2-s0 (35 eps) |
| `train-a1-d0-20260917T062346Z` | `8ca70d6d…` | EXP-007 A2-s1 (21 eps) |

* **[V]** `8ca70d6d…` **is** the current `configs/rl.yaml` byte hash (SHA-256 over `read_bytes()`, recomputed 2026-09-19: `8ca70d6dd7df68841c409a4441dc538616206bccea7877b28c73df20e6428b80`).
* **[V]** The four `4bb71750…` runs are the Day-28 run of record plus the three Day-29 replicates; the latter three are simultaneously the three EXP-007 full-state reference runs. Together with the Day-28 run of record they are the **four runs affected by the provenance failure**: the three Day-29 replicates fail `validate_day29.py` checks `05/06` directly, and the Day-28 run carries the same unreproducible hash (its own validator does not check that field).
* **[I]** The failure detected today is therefore a **current, still-live provenance failure**, not a historical artifact of an already-superseded rule: re-running `validate_day29.py` against this tree fails the same three checks.

### 4.2 Both writers hash raw bytes — the mismatch is byte-level

* **[V]** The training writer records the hash from raw bytes: `src/sparkrl/training/loop.py:773` assigns `"rl_yaml_sha256": _sha256_file(Path(DEFAULT_RL_YAML))`, and `_sha256_file` (lines 643-646) computes `hashlib.sha256(Path(path).read_bytes()).hexdigest()`.
* **[V]** The Day-29 checker compares the same way: `scripts/validate_day29.py:151-154`, `rl_yaml_sha256()` computes `hashlib.sha256((PROJECT / "configs" / "rl.yaml").read_bytes()).hexdigest()`.
* **[V]** Both sides therefore hash the raw byte stream of `configs/rl.yaml`. The mismatch is a **byte-level provenance mismatch** — it cannot be explained away as a semantic YAML-content comparison difference (e.g., key ordering or quoting). The byte sequences differed at the time of recording, and the current bytes differ from the `4bb71750…` runs' recorded bytes.

### 4.3 The byte-variant check over committed history — [V] verified, zero matches

* **[V]** Exactly **two commits** have ever touched `configs/rl.yaml`:
  * `2fef78604b0d1d02f3f7243dd522bfcc552a1f54` (2026-09-12T07:23:13+05:30, "feat(rl): tabular Q-learning agent with EXP-002 offline Q0 init and versioned policy store") — blob `36374c823169…`, **954 bytes**, **LF-only**, no BOM;
  * `6d854816164b49711ba7bdcde5ed37c5c004d037` (2026-09-12T13:54:15+05:30, "feat(rl): Day-27 training loop with epsilon schedule, checkpointing and budget guard") — blob `13758aacade4…`, **1792 bytes**, **LF-only**, no BOM; this is also `HEAD:configs/rl.yaml` (raw blob sha256 `d9a7b29a884b3e9aac314b48fffe19697cbce0e63b09901813cc9580d6a291e3`).
* **[V]** Neither committed blob, under any representation, hashes to `4bb71750…`. The findings as supplied describe an exhaustive byte-variant check across both committed versions — **sixteen candidates tested in total** (LF, CRLF, CR, BOM variants, and trailing-newline variants), none reproducing `4bb71750…`. This session's independent re-enumeration was strictly broader (sixteen candidates per blob, thirty-two in total, plus the two raw blobs) and reaches the same conclusion: **zero matches for `4bb71750…`** and zero matches for any hash other than the blobs' own raw sha256 values. Both enumerations agree; the finding stands.


### 4.4 Scope of the eight-manifest statement — [V] verified

* **[V]** The statement "eight training manifests split into two recorded hashes" refers to the eight manifests directly under `results/training/*/manifest.json`. A further **six smoke manifests** exist under `results/training/smoke/`: five dated 2026-09-12 recording `4bb71750…` and one dated 2026-09-16 recording `8ca70d6d…`. These are outside the "eight training manifests" statement and are recorded here only so the split cannot be misread as the complete manifest inventory. The `8ca70d6d…` value's first appearance in the tree is therefore 2026-09-16 (the smoke run), with the four EXP-007 ablation runs on 2026-09-17.
* **[I]** The Day-28/29 findings remain exactly as stated: eight non-smoke training manifests, 4 + 4.

### 4.5 The unanswerable reconstruction question — [U] unknown

* **[V]** The 2026-09-12 runs executed against an uncommitted working tree: their manifests record `code_version` values `6d85481-dirty` and `8a9ca54-dirty` (both `-dirty`, i.e., not clean commits), and no commit touching `configs/rl.yaml` exists after 2026-09-12T13:54:15+05:30.
* **[V]** No committed version of `configs/rl.yaml` — under any tested byte representation — reproduces `4bb71750…`.
* **[U] The repository cannot currently reconstruct the exact `configs/rl.yaml` byte representation that produced `4bb71750…`, and cannot establish where that representation existed at execution time.** The provenance claim of the four affected runs therefore cannot be independently reconstructed from committed configuration history. This is the central governance finding of this record (interpretation in section 6).
* **[U]** Whether the 2026-09-12 and 2026-09-17 file versions differed semantically (not just in byte representation) is **unknown**: no committed or stored copy of the 2026-09-12 execution-time file exists, so no semantic comparison is possible. No claim either way is made.

## 5. Autocrlf checkout dependence — [V] verified

* **[V]** `core.autocrlf` is `true` in this working copy; `.gitattributes` sets `* text=auto`; `git ls-files --eol` reports `i/lf w/crlf attr/text=auto` for `configs/rl.yaml`.
* **[V]** Byte-level verification: `HEAD:configs/rl.yaml` (blob sha256 `d9a7b29a…`, 1792 bytes) is **LF-only**; the working-tree `configs/rl.yaml` (sha256 `8ca70d6d…`, 1826 bytes) is **CRLF**; the two are **byte-identical after CRLF→LF normalization** (34 lines, 34 CRLF line endings in the working tree, 0 CR-only endings, no BOM in either). The file is byte-identical to the Git version after accounting for checkout line endings.
* **[V]** Initially appearing to differ, then resolving under the autocrlf explanation, is exactly the initial appearance described in the findings; the underlying mechanism is verified: the same logical content exists in the tree in two byte representations (LF in the object database, CRLF at checkout), and both hash differently under the current raw-byte design.
* **[V]** The 2026-09-17 run provenance (`8ca70d6d…`) records the **CRLF** representation — the checkout representation, not the committed LF blob (`d9a7b29a…`).
* **[V]** Consequently, the current byte-hash design (`sha256(read_bytes())` on both the writer side, `loop.py:643-646`, and the checker side, `validate_day29.py:151-154`) is **checkout-representation dependent for text files**: the same logical file content can produce different provenance hashes depending on how Git materialized it into the working tree. This is recorded as a **reproducibility/provenance design fragility**.
* **Explicit non-claim.** This observation does **NOT** prove, and this record does not claim, that Git history was altered, that any file was rewritten in history, or that any tampering occurred. autocrlf is a standard, benign mechanism; the fragility is a property of the hash design, not evidence of any intervention.


## 6. Research-governance interpretation — bounded

This section interprets the verified findings of sections 1-5 and nothing else.

* **No misconduct claim.** Nothing here claims, implies, or licenses an inference of intentional misconduct, fabrication, or corruption — by any person, at any time. The verified facts are equally consistent with an ordinary, unrecorded working-tree edit of `configs/rl.yaml` between the 2026-09-12 runs and the 2026-09-16 smoke run.
* **No scientific-invalidity claim.** Nothing here claims that the four affected runs, or any experiment built on them, are scientifically invalid solely from this evidence. The provenance chain documents one configuration input whose exact byte representation is no longer reconstructable; it does not by itself impeach any measured result.
* **The precise claim.** [V] The repository cannot currently reproduce the exact `configs/rl.yaml` byte representation identified by `4bb71750e51c8ea605f7feaaa368a2f1dcbe4ecd2aacbeed0f059f8d18cfb5a14`; [I] therefore the provenance claim for the four runs recording that hash (the Day-28 run of record and the three Day-29 replicates / EXP-007 full-state reference runs) **cannot be independently reconstructed from committed configuration history**. This is recorded as an **unreproducible configuration-provenance finding** — a governance failure of the provenance chain, in the repository's own vocabulary of byte-fingerprint discipline (cf. DEC-024 §6's "any byte-level change … voids that fingerprint and requires re-verification" and the DEC-021 clerical-correction tradition of recording findings as new entries rather than rewriting history).
* **Class separation.** [V] This finding is about configuration provenance. It is distinct from — and must not be conflated with — the validator/scanner defect of section 3 (a false positive of Day-29 check 20) and the true-positive rule staleness of section 1 (Day-28 check 18). Three failure classes, three dispositions: unreproducible provenance (factual), scanner defect (tooling), stale rule (governance bookkeeping).
* **What would settle it.** [I] Either locating a byte-exact copy of the execution-time `configs/rl.yaml` that hashes to `4bb71750…`, or an operator/supervisor decision recording the reconstruction question as unanswerable with the corresponding provenance caveat attached to the four runs. Neither exists in the tree today; neither is performed by this record.

## 7. Status matrix update — [V] statuses as stated

Compact update of the verification-matrix rows touched by this re-verification. "Previously" refers to the operator-side verification tracking prior to this session (these rows and the "violations: 0" statement live outside the repository and have no in-repo prior record — verified by search):

| # | Row | Previously | Now | Basis |
|---|---|---|---|---|
| 1 | Day 28 `18 no_exp003_005` | UNRESOLVED | **RESOLVED — true positive** on `no_exp003_005` (paths genuinely exist; path-based detector) | §1 [V] |
| 2 | Day 29 `20 no future components` (PEP-701/scanner row) | UNRESOLVED | **CONFIRMED scanner defect** (`FSTRING_MIDDLE` escaping the string stripper; not a research-history violation) | §3 [V] |
| 3 | Day 29 `05/06 run seed {0,1,2} provenance` | UNRESOLVED | **RESOLVED — legitimate current provenance failure** (`rl_yaml_sha256` mismatch is real, byte-level, and live) | §2, §4 [V] |
| 4 | Prior statement "violations: 0" | Stated | **No longer supportable** — the provenance chain contains a verified unreproducibility finding (`4bb71750…` not reconstructable from committed history) | §4.3, §4.5 [V] |
| 5 | autocrlf checkout dependence | (not previously tracked) | **Newly identified** — byte-hash design is checkout-representation dependent for text files; recorded as a reproducibility/provenance design fragility, **not** as evidence of history alteration | §5 [V] |


## 8. Remediation sequencing and candidates — recorded, NOT performed

**Sequencing constraint [I, from verified facts].** Provenance reconstruction must be handled **before** ordinary scanner/allowlist cleanup. Rationale from verified facts: the provenance question (what exact byte representation produced `4bb71750…`, and where did it exist at execution time?) is a **factual question about historical experiment configuration** — it is either answerable from evidence that exists somewhere outside the committed history, or it is permanently unanswerable and must be recorded as such with a caveat attached to the four affected runs. Scanner/allowlist cleanup (a Day-28 rule re-baseline, a Day-29 check-20 matcher repair) is ordinary tooling work that can be done at any time and changes nothing about the historical facts. Resolving the tooling items first would risk the impression that the governance ledger is clean once validators pass, while the provenance question remains open. No implementation of any repair is prescribed or authorized here.

**Candidates (unordered within their class; each requires its own decision and is NOT performed by this record):**

* **P-class (provenance, sequenced first):**
  * **P1** — Exhaust all sources outside committed history for a byte-exact execution-time `configs/rl.yaml` (editor history, backups, OneDrive file versioning, other clones), and verify by hashing to `4bb71750…`. If found, the provenance chain is reconstructed and the finding downgrades to "reconstructed after the fact".
  * **P2** — If P1 fails, record an operator/supervisor decision stating the representation is unreconstructable from committed history, attaching an explicit provenance caveat to the four affected runs (Day-28 run of record; Day-29 replicates / EXP-007 full-state references), in the DEC-021 clerical-correction tradition (new entry, history never rewritten).
  * **P3** — Separately and only after P1/P2: decide whether the raw-byte hash design should be amended (e.g., hashing a canonicalized representation, or hashing the committed blob), with full re-verification of any fingerprint that such an amendment voids. This touches frozen governance instruments (DEC-024 §6 fingerprints) and carries its own re-verification obligation.
* **R-class (scanner/allowlist, sequenced after P1/P2):**
  * **R1** — Repair Day-29 check 20's matcher to account for PEP-701 tokenization (e.g., also stripping `FSTRING_MIDDLE` literals), or relocate the `EXP-003` mentions it flags; re-verify that the repair does not open a detection hole in the forbidden-component rule. The validator/allowlist repair category has precedent in DEC-032's "validator-only repair authorized for a separate later task" convention.
  * **R2** — Re-baseline or formally re-scope Day-28 check 18 (and its sibling checks in `validate_rl_training.py` / `validate_rl_agent.py`, which share the detector pattern) so that the assertion matches the current, post-EXP-005 reality of the tree.
  * **R3** — Decide how the Day-31 gate should treat the Day-29 subprocess chain (`validate_day31.py:118`) while check 20's defect is unresolved.

**Explicitly not decided here:** which candidates to adopt, their ordering beyond the P-before-R constraint, and any amendment to any frozen decision. Those are separate decisions with their own authority chain.


## 9. Verification method and evidence inventory — [V] verified

What this session did to establish the findings (all non-mutating):

* **Validator re-runs.** Both validators were executed: `python scripts/validate_day28.py` → 19/20, exit 1; `python scripts/validate_day29.py` → 20/24, exit 1. Both are read-only **with respect to the repository**: neither writes any file inside the project tree (verified by inspecting both scripts for file-writing calls — the only writes are scratch files under the system temp directory, used by their analysis-reproducibility probes: `validate_day28.py:458` `tempfile.TemporaryDirectory()`, `validate_day29.py:159-160` `tempfile.mkdtemp`), and their re-runs modified nothing under the project. The validator output tables quoted in sections 1 and 2 are verbatim from these re-runs.
* **Manifest re-reads.** All eight non-smoke training manifests re-read: the 4 + 4 `rl_yaml_sha256` split of section 4.1, the `code_version` values of section 4.5, and the roles of each run are read from `results/training/*/manifest.json` directly. All six smoke manifests re-read for the section 4.4 scope note.
* **Byte-level checks.** `configs/rl.yaml` hashed from raw bytes (working tree and `git cat-file blob` for both committed blobs); `git ls-files --eol`, `git config core.autocrlf`, `.gitattributes` read; CRLF→LF normalization comparison performed; the full EOL/BOM/trailing-newline variant enumeration over both committed blobs (zero matches for `4bb71750…`).
* **Source inspection.** `scripts/validate_day28.py` (check 18 at 504-510; check 17's narrower `FORBIDDEN_CODE`), `scripts/validate_day29.py` (`FORBIDDEN_CODE` at 103-109; `rl_yaml_sha256()` at 151-154; `provenance_ok` at 236-268; `_src_free_of_future_components` at 316-346; check 20 emission at 528-530), `src/sparkrl/training/loop.py` (`_sha256_file` at 643-646; manifest writer at 773), `scripts/analyze_exp007.py` (`FULL_STATE_RUNS` at 65-72), `scripts/validate_day31.py` (Day-29 subprocess chain at 118).
* **Independent scanner re-execution.** The Day-29 check-20 algorithm (same regex, same tokenize stripping) re-implemented outside the repository (in a temporary directory, not the working tree) and executed over `src/` — reproducing exactly the three files and confirming `FSTRING_MIDDLE` as the escaping token type in each.
* **Prior-record searches.** `docs/research/*.md` and `DECISIONS.md` searched for UNRESOLVED-matrix rows, "violations: 0", f-string/FSTRING/tokenize/PEP-701 mentions, and any prior documentation of the provenance mismatch — no prior in-repo record exists for any of them.

## 10. Open factual question

> **What exact `configs/rl.yaml` byte representation produced `4bb71750e51c8ea605f7feaaa368a2f1dcbe4ecd2aacbeed0f059f8d18cfb5a14`, and where did that representation exist at execution time?**

**The current committed history does not answer this question.** [V] Both committed blobs are LF-only and neither hashes to `4bb71750…` under any of the tested byte representations (section 4.3); [V] no commit touched `configs/rl.yaml` after 2026-09-12, while the 09-12 runs record `-dirty` code versions (section 4.5). Until a byte-exact execution-time copy is located (candidate P1) or the question is formally recorded as unanswerable (candidate P2), the provenance chain for the Day-28 run of record and the three Day-29 replicates / EXP-007 full-state reference runs carries an unreconstructed configuration-provenance caveat.

---

*Record closes here. Nothing above authorizes execution of any kind; nothing below this line exists.*


