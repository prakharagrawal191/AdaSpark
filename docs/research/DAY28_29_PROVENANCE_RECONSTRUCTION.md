# Day 28/29 Provenance Reconstruction — Byte-Exact Recovery of the `4bb71750…` `configs/rl.yaml` Representation

**Status:** research-governance record. Investigation **complete; finding verified and recorded**. **No remediation performed.** No validator, manifest, configuration, artifact, ledger, decision entry or prior research record was modified by this record. Its only filesystem effect is this document.

> **Boundary.** This entry performs 0 Spark executions, trains nothing, executes no experiment, creates no run directory, and modifies no result artifact, no manifest, no validator, no configuration file and no decision entry. All Git operations were read-only (`cat-file`, `ls-tree`, `rev-list`, `log`, `fsck`, `for-each-ref`, `reflog`); no ref, index state, config or checkout file was altered. All byte-level probes were executed in scratch repositories and scratch files under the system temp directory and were deleted afterwards. The recovered byte string is **not** written into the repository; it is specified below in a form independently reproducible from the existing committed blob.
>
> **Method.** Every load-bearing claim below was re-verified against the working tree or the Git object store in this session, and every hash was computed with `hashlib.sha256` over exact raw bytes. The decisive comparison (section 9.4) is a cryptographic equality between the reconstructed byte string and the value recorded in the four affected manifests.
>
> **Evidence-status legend.** **[V] verified** (directly established against the tree/object store, including exact cryptographic computation), **[I] inferred** (follows from verified facts, marked as inference), **[U] unknown** (the available evidence does not answer). No label was upgraded.
>
> **Prior-record relation.** This record follows `DAY28_29_GOVERNANCE_REVERIFICATION.md` (its section 8 sequences this provenance work first, as candidate P1). It does not modify that record. Two of its quoted hash strings are affected by a transcription artifact noted in section 3.2.

## 1. Purpose and scope

Establish whether the exact `configs/rl.yaml` byte representation corresponding to the `rl_yaml_sha256` value recorded by the four Day-28/29 training runs can be recovered from authoritative repository-local evidence, and if so, where that representation existed at execution time. This is a historical factual investigation. It decides nothing about remediation, validator repair, or any amendment to frozen governance instruments.

## 2. Research question

> What exact `configs/rl.yaml` byte representation produced the recorded value `4bb71750…`, and where did that representation exist at execution time?

**Answer (verified, section 9.4): it was a mixed-line-ending working-tree representation of the Day-27 configuration at `configs/rl.yaml` — the file as committed (blob `13758aac…`) with CRLF endings on its 19 pre-existing lines and LF endings on the 15 inserted lines — 1811 bytes, SHA-256 `4bb71750e51c8ea605f7feaaa368a2f1dcbe4ecd2aacbed0f059f8d18cfb5a14`.** It existed on disk at `configs/rl.yaml` in the working tree throughout the execution window of all nine runs that recorded it (2026-09-12T05:28:36Z → 12:16:24Z).

## 3. Known starting evidence

### 3.1 Carried forward from the prior record

* [V] Current `configs/rl.yaml` hashes (raw bytes) to `8ca70d6dd7df68841c409a4441dc538616206bccea7877b28c73df20e6428b80` (recomputed this session; 1826 bytes, CRLF).
* [V] Eight non-smoke training manifests record exactly two values: `4bb71750…` (4 runs: the Day-28 run of record and the three Day-29 replicates / EXP-007 full-state references) and `8ca70d6d…` (4 runs: the EXP-007 A1/A2 runs of 2026-09-17).
* [V] Exactly two commits have modified `configs/rl.yaml`: `2fef786` (blob `36374c82…`) and `6d85481` (blob `13758aac…`); both committed blobs are LF-only and neither reproduces the target under any uniform representation.
* [V] `core.autocrlf=true` and `* text=auto` are set; `git ls-files --eol` reports `i/lf w/crlf attr/text=auto` for `configs/rl.yaml`.
* [V] The recording mechanism is raw-byte: `src/sparkrl/training/loop.py:643-646` (`_sha256_file` = `hashlib.sha256(Path(path).read_bytes())`), applied at the manifest writer to `Path(DEFAULT_RL_YAML)` = `PROJECT / "configs" / "rl.yaml"` (`src/sparkrl/agent/q_learning.py:43`); `scripts/validate_day29.py:151-154` compares the same way.

### 3.2 New finding: transcription artifact in the previously quoted hash

* [V] The **authoritative** value, extracted verbatim from the four affected manifests' `"rl_yaml_sha256"` fields, is 64 hexadecimal characters:
  `4bb71750e51c8ea605f7feaaa368a2f1dcbe4ecd2aacbed0f059f8d18cfb5a14`
* [V] The full-length quotations in `DAY29_TRAINING_REPLICATES_AND_M8_AUDIT.md` and `DAY28_29_GOVERNANCE_REVERIFICATION.md` render it as 65 characters (`…2aacbeed0f059f8d18cfb5a14`, doubled `e`). A SHA-256 hex digest is exactly 64 characters; the 65-character string cannot be a digest and was not produced by any hasher. This is a **transcription artifact in prose records only** — every manifest stores the correct 64-character value. Not repaired here.
* [I] All prior uniform-variant searches (LF / CRLF / CR / BOM / trailing-newline) were structurally incapable of finding the target, because — as established below — the execution-time representation was **mixed** (some lines CRLF, some LF). The prior searches were correct and complete over their search space; the space was too narrow.

## 4. Search performed (inventory)

All locations below were inspected this session. "Tracked" = in Git HEAD/index; "A" = authoritative, "D" = derivative/descriptive, "Amb" = ambiguous.

| Location | Matching content | Tracked | Class |
|---|---|---|---|
| `results/training/train-{a0,a1,a2}-d0-20260912T{083120,112906,115123,120648}Z/manifest.json` | `"rl_yaml_sha256": "4bb71750e51c8ea605f7feaaa368a2f1dcbe4ecd2aacbed0f059f8d18cfb5a14"` | no (gitignored results) | A |
| `results/training/smoke/train-a0-d0-20260912T{052836,081149,081451,081737,082054}Z/manifest.json` | same `4bb71750…` value (5 smoke runs, not previously inventoried) | no | A |
| `results/training/*/manifest.json` — the four 2026-09-17 runs and the nine 2026-09-16/19 smoke runs | `8ca70d6d…` | no | A |
| `manifest.hyperparameters` (all `4bb71750…` runs) | `alpha 0.2, gamma 0.0, epsilon 1.0/0.05/0.95, q0_default 0.5`, `source: "configs/rl.yaml + PLAN section 16"` | no | A |
| `docs/research/DAY28_FIRST_FULL_TRAINING_AUDIT.md`, `DAY29_TRAINING_REPLICATES_AND_M8_AUDIT.md`, `DAY28_29_GOVERNANCE_REVERIFICATION.md` | descriptive quotes of both hashes (two with the 65-char artifact, §3.2) | partially (gov record untracked) | D |
| `scripts/validate_day29.py:151-154`, `src/sparkrl/training/loop.py:643-646,773`, `src/sparkrl/agent/q_learning.py:43` | the raw-byte hash/compare mechanism | yes | A (mechanism) |
| Git object store (726 blobs, 1790 objects, reachable + unreachable) | exactly two rl.yaml-content blobs: `13758aac…` (1792 B, LF), `36374c82…` (954 B, LF) | — | A |
| Local editor checkpoint refs (62, 2026-09-08 → 2026-09-19) | normalized worktree snapshots; `configs/rl.yaml` = `13758aac…` at every snapshot from 2026-09-12T02:52:15Z onward | refs, not on `main` | A |
| Auxiliary worktree copies of `configs/rl.yaml` | current bytes only (`8ca70d6d…`, 1826 B) | no | Amb |
| Editor state files, root-level numbered scratch files, `tmp_*.json` | no configuration content | no | Amb (negative) |
| Whole-tree hash sweep (1271 files, excluding `.git`, `__pycache__`, `.pytest_cache`) | **zero** files hash to `4bb71750…` | — | A (negative) |
| Editor local history (`%APPDATA%\Code`, other editor stores, package stores) | 0 `rl.yaml` history entries | — | A (negative) |
| OneDrive cloud file versioning | not verifiable from repository-local evidence | — | U (unexplored) |

No `.bak`/`.old`/`.orig`/archive file contains configuration content. No file anywhere in the tree or object store reproduces the target hash raw.

## 5. Git-object findings

* [V] `git cat-file --batch-all-objects` enumerates **1790 objects / 726 blobs**. Every blob was extracted and hashed raw: **none** equals `4bb71750…` or `8ca70d6d…` (both are CRLF-bearing working-tree representations; the store holds only normalized LF content — expected under `autocrlf=true`).
* [V] `configs/rl.yaml` content exists as exactly **two** blobs in the entire store, including all unreachable objects:
  * `36374c823169cb39a899e62d472486ddda3397a3` — 954 bytes, 19 lines, LF-only, no BOM, final newline; raw SHA-256 `7b526d53616f2297b1071e927b119aaeb508bad54df8dd6e70421cba0431201b`; its uniform CRLF variant hashes `882e6c8f44dcde8df1a7c8e512c29fe4349cf0ddf94c7a87ceef6c7b53bd814bd` (973 bytes).
  * `13758aacade45c241f74daa857101cf2cf286562` — 1792 bytes, 34 lines, LF-only, no BOM, final newline; raw SHA-256 `d9a7b29a884b3e9aac314b48fffe19697cbce0ee63b09901813cc9580d6a291e3`; its uniform CRLF variant hashes **`8ca70d6dd7df68841c409a4441dc538616206bccea7877b28c73df20e6428b80`** (1826 bytes) — exactly the current working-tree file and the value recorded by the 2026-09-17 runs.
* [V] `git fsck --unreachable --no-reflogs` reports 71 unreachable commits. All are editor-checkpoint / stash-machinery commits (checkpoint commits, `index on …`, `untracked files on …`); `ls-tree` over each shows `configs/rl.yaml` = `13758aac…` at every entry — dangling history contains **no** third rl.yaml content and **no** target bytes.
* [V] `git rev-list --all` (which includes all 62 local checkpoint refs and `refs/heads/main`) walks every commit; `ls-tree configs/rl.yaml` over all of them yields only the two blobs above.
* [V] Structure of the Day-27 change (difflib over the two blobs): **pure insertion** — `old[1..19]` equal to `new[1..19]`; `new[20..34]` inserted (the `training:` block). Nothing else changed.

## 6. Archived/copy findings

* [V] Whole-project hash sweep: all 1271 files (excluding `.git`, `__pycache__`, `.pytest_cache`; files >50 MB skipped) hashed raw — **no** file equals `4bb71750…`. No exact copy survives anywhere in the tree.
* [V] Auxiliary worktree copies of `configs/rl.yaml` = current bytes (`8ca70d6d…`). Editor state files contain no configuration snapshot. No backup/archive/notebook contains the target bytes (inventory, section 4).
* [V] VS Code and other editor local history directories exist but contain **0** entries referencing `rl.yaml` for this project (`entries.json` scan).
* [U] OneDrive cloud version history (the project resides under OneDrive) is not examinable from repository-local evidence and was not accessed. It could in principle hold an independent copy; given the byte-exact recovery below, it is no longer load-bearing.

## 7. Embedded-metadata findings

* [V] The affected manifests contain **no** serialized YAML, config dump, environment snapshot, or command-line echo of the configuration. `manifest.files` lists only run-artifact paths (`checkpoints`, `episodes.jsonl`, `transitions`). The configuration payload is limited to `manifest.hyperparameters` (6 frozen values + source string) and `manifest.contract_versions` / `q0_provenance`.
* [I] The recorded hyperparameters and contract fingerprints of the `4bb71750…` runs are identical to those of the `8ca70d6d…` runs, and the loader hard-errors on any disagreement with the frozen values (`RLConfigError`; `loop.py:153-188`). The execution-time file was therefore **semantically equivalent** to the current file. A fortiori this holds for the recovered bytes below, which are textually identical to the current file modulo line endings.

## 8. Timestamp and source-state findings

All timestamps UTC (commit dates converted from the recorded epoch offsets). Filesystem mtimes not used.

| When (UTC) | Event | rl.yaml evidence |
|---|---|---|
| 2026-09-12T01:53:13Z | `2fef786` committed (Day-26 agent) | blob `36374c82…` committed |
| 2026-09-12T02:52:15Z | Editor checkpoint 30 (session `zm8qp`) | snapshot tree has `configs/rl.yaml` = `13758aac…` — the Day-27 `training:` block already on disk, pre-commit [V] |
| 2026-09-12T05:28:36Z | smoke run `…T052836Z` (`2fef786-dirty`) | **earliest recorded `4bb71750…`** [V] |
| 2026-09-12T05:47:48Z / 05:49:39Z | Editor checkpoints 31 / 32 | snapshot tree still `13758aac…` [V] |
| 2026-09-12T08:11:49Z–08:21:24Z | four smoke runs | all record `4bb71750…` [V] |
| 2026-09-12T08:24:15Z | `6d85481` committed (Day-27 loop) | blob `13758aac…` committed [V] |
| 2026-09-12T08:31:20–08:42:29Z | **Day-28 run of record** (`6d85481-dirty`) | records `4bb71750…` [V] |
| 2026-09-12T09:12:37Z | `8a9ca54` committed (Day-28 analysis commit) | tree `13758aac…` [V]; this is the code-version base of the Day-29 replicates' `8a9ca54-dirty` markers |
| 2026-09-12T10:54:52Z | Editor checkpoint (session `4gn1c`/1) | snapshot tree `13758aac…` [V] |
| 2026-09-12T11:29:06Z–12:16:24Z | **three Day-29 replicates / EXP-007 full-state references** (`8a9ca54-dirty`) | all record `4bb71750…` [V] |
| 2026-09-12T12:16:24Z → 2026-09-16T04:30:03Z | **transition window** | no commit touches `configs/rl.yaml` in this window (none after `6d85481`); the 09-16 smoke run is the first `8ca70d6d…` record [V] |
| 2026-09-17T05:50:42Z–06:30:30Z | four EXP-007 A1/A2 runs | all record `8ca70d6d…` [V] |

* [V] The Day-28/29 runs did **not** run against a stale checkout of an older commit: the on-disk content already contained the Day-27 block before the first `4bb71750…` record (checkpoint 30), and the runs' `contract_versions` / hyperparameters match the Day-27 configuration.
* [I] Source-state interpretation of `-dirty`: every affected run recorded a `-dirty` code version, and the tree was in fact continuously dirty (17 modified files even today). Before `6d85481`, `configs/rl.yaml` itself was genuinely uncommitted-modified (checkpoint 30 proves it). After `08:24:15Z`, however, Git considered `configs/rl.yaml` **clean** — under `autocrlf=true`, the mixed-EOL working file normalizes to the committed blob, so `git status` reports no change even though the raw bytes differ from the blob and from the uniform-CRLF checkout. The `-dirty` markers therefore neither prove nor detect the byte-level state; they are uninformative about this question, as the prior record warned.
* [U] Which exact operation converted the file to uniform CRLF (`8ca70d6d…`) during the transition window — any checkout/reset/stash-pop/editor normalization produces it — is not recorded anywhere.

## 9. Autocrlf findings — and the reconstruction

### 9.1 The current representation is fully explained by autocrlf

* [V] `SHA-256(CRLF(13758aac-content)) = 8ca70d6d…` — computed over the blob's content with every `\n` replaced by `\r\n` (1826 bytes). The current working file is exactly this: the `autocrlf=true` + `* text=auto` checkout representation of the committed blob, verified byte-for-byte against the on-disk file.

### 9.2 Uniform representations are excluded

* [V] Over both committed blobs, in this session and reproducing the prior record's enumeration: uniform LF, uniform CRLF, uniform CR, ±BOM, ±final-newline — **no** uniform representation of either blob hashes to `4bb71750…` (all values recorded in sections 5–6 and in the probe transcripts).

### 9.3 Mixed line endings normalize invisibly — mechanism verified

* [V] In a scratch repository under `%TEMP%` configured identically to this project (`core.autocrlf=true`, `.gitattributes` = `* text=auto`), staging working files whose line endings are **mixed** (CRLF on a subset of lines) produces blob `13758aac…` exactly, while the raw on-disk bytes hash to different values (e.g. a half-CRLF variant: 1809 bytes, raw SHA-256 prefix `bd8913ae…`; a "final-line-CRLF" variant: 1793 bytes, `c9b5f308…`). I.e. **a mixed-EOL working file is invisible to Git's content tracking while hashing differently raw** — precisely the observed pattern (checkpoint/commit snapshots show `13758aac…`; the training loop's raw-byte hash records `4bb71750…`).
* [V] Control cases: a file missing its final newline does **not** normalize back to `13758aac…` (stages as `b8347469…`), and BOM-bearing content would stage to a different blob (BOM survives conversion) — both classes are excluded by the snapshot evidence, not merely untested.

### 9.4 Byte-exact reconstruction — target reproduced

* [V] **Construction.** Take blob `13758aac…` content (the Day-27 text). Lines 1–19 (exactly the lines equal to the Day-26 blob — the pre-existing file) end with CRLF; lines 20–34 (exactly the inserted `training:` block) end with LF; the file ends with a final LF on line 34. Total: 1792 + 19 = **1811 bytes**.
* [V] **Result.** `SHA-256` of those bytes = **`4bb71750e51c8ea605f7feaaa368a2f1dcbe4ecd2aacbed0f059f8d18cfb5a14`** — equal, character-for-character, to the `"rl_yaml_sha256"` value stored in all four affected training manifests **and** all five 2026-09-12 smoke manifests (extracted verbatim and compared programmatically; equality is `True`).
* [V] **Consistency.** Staging the reconstructed bytes in the scratch repository (same `autocrlf`/attributes) yields blob `13758aac…` — matching every checkpoint snapshot and both commits of the window, and explaining why Git saw a clean file.
* [V] **Uniqueness.** The construction is principled (diff-derived: CRLF on the unchanged Day-26 lines, LF on the inserted lines — the signature of an editor/tool writing the new block with LF endings into an existing CRLF file), not searched for. Its collision-free match with a 256-bit recorded value identifies the historical byte string: any different byte sequence would hash differently. [I] The generative narrative (which tool wrote which endings when) is interpretation; the bytes themselves are not.
* [I] Consequently `autocrlf` **explains the target hash**: not through any uniform conversion, but through the interaction of (a) a CRLF working file predating the Day-27 edit, (b) an LF-written insertion, and (c) Git's checkin normalization hiding the mixture. A pure `autocrlf` checkout artifact alone cannot produce it (9.2).

### 9.5 Independent reproduction recipe

1. `git cat-file blob 13758aacade45c241f74daa857101cf2cf286562` (at any commit from `6d85481` to HEAD) → 1792-byte LF text `T` with 34 lines.
2. Emit: for lines 1–19 of `T`, `line + b"\r\n"`; for lines 20–34, `line + b"\n"`.
3. `hashlib.sha256(result).hexdigest()` → `4bb71750e51c8ea605f7feaaa368a2f1dcbe4ecd2aacbed0f059f8d18cfb5a14` (1811 bytes).
4. Cross-check: stage the result in a scratch repo with `core.autocrlf=true` and `* text=auto` → blob OID `13758aacade45c241f74daa857101cf2cf286562`.

## 10. Candidate explanation matrix

| # | Candidate explanation | Verdict | Basis |
|---|---|---|---|
| 1 | Recorded hash is wrong / typo in manifests | **Excluded** | manifests store a well-formed 64-char digest, recorded live by `loop.py:773` from raw bytes [V] |
| 2 | Malice / falsification / history rewrite | **Excluded as unnecessary and unsupported** | a mundane, fully reconstructed mechanism explains every observation; no evidence of intent anywhere in the chain [V/I] |
| 3 | Run used an older commit's `rl.yaml` (`36374c82…`) | **Excluded** | content differs (no `training:` block; loop requires it); no representation of it hashes to target [V] |
| 4 | Uniform EOL/BOM/newline variant of the Day-27 content | **Excluded** | exhaustive enumeration, both sessions — no match [V] |
| 5 | Uniform representation of any object in the store | **Excluded** | all 726 blobs hashed raw; uniform variants of rl.yaml-like blobs enumerated — no match [V] |
| 6 | Semantically different configuration (different values/comments) | **Excluded** | checkpoints captured the normalized content as `13758aac…` throughout the window; hyperparameters/contracts identical [V] |
| 7 | Mixed line endings (CRLF Day-26 lines + LF inserted block) | **Confirmed — byte-exact** | SHA-256 equality with all nine manifests' recorded value (§9.4) [V] |
| 8 | Editor/OneDrive/backup copy as an independent source | **Moot** | no copy exists locally; recovery achieved from committed history + recorded hash [V/U] |

## 11. Final classification

**A — EXACTLY RECONSTRUCTED.** The exact raw bytes producing `4bb71750…` were recovered (1811 bytes, §9.4), their SHA-256 equals the authoritative manifest value, and their provenance is established: they were the on-disk bytes of `configs/rl.yaml` in this working tree, in continuous existence from before 2026-09-12T02:52:15Z until at least 2026-09-12T12:16:24Z, at execution time of all nine runs that recorded the hash. (Standard SHA-256 collision-resistance assumed; the only residual interpretive element is the generative story of *how* the mixed endings arose, which does not affect the identification of the bytes or their location.)

## 12. What is established

* [V] The exact 1811-byte representation and its hash equality with all nine affected manifests.
* [V] The execution-time location: `configs/rl.yaml`, working tree, throughout 2026-09-12T05:28:36Z–12:16:24Z (and already present at 02:52:15Z per checkpoint 30).
* [V] The committed history contains the same text normalized (blob `13758aac…`); the raw-byte provenance gap existed only at the working-tree byte level, caused by mixed line endings under `autocrlf` normalization.
* [V] The current `8ca70d6d…` file is the uniform-CRLF checkout representation of the same blob — textually identical to the historical file.
* [V] The transition to uniform CRLF occurred between 2026-09-12T12:16:24Z and 2026-09-16T04:30:03Z with no commit involved.
* [V] The four affected runs' configuration was semantically identical to the current frozen configuration (identical hyperparameters and contract fingerprints; loader hard-errors on drift).
* [V] The full-length hash quotations in two prior research records carry a 65-character transcription artifact (§3.2).

## 13. What remains unknown

* [U] Which tool or operation wrote the `training:` block with LF endings (the generative mechanism of §9.4 is inferred from the byte structure, not from a recorded action).
* [U] Which operation or event produced the uniform-CRLF rewrite in the transition window.
* [U] OneDrive cloud version history was not examined (out of repository-local scope; no longer load-bearing).
* [U] Whether any process re-verified raw bytes between 08:24:15Z and the runs — immaterial to the finding, unrecorded if it happened.

## 14. Impact on reproducibility / governance

* [I] **The provenance chain for the four Day-28/29 runs is reconstructable and intact**: the execution-time configuration is byte-identifiable, semantically identical to the frozen configuration, and its normalized form is committed. No experiment result is impeached by this finding; the earlier "unreproducible configuration-provenance finding" is hereby **resolved by reconstruction**, and the Day-29 validator's `05/06` provenance failures are fully explained as an EOL-representation difference between the run-time file and the current checkout, with no content difference.
* [I] The finding retroactively validates the prior record's design concern: raw-byte hashing of a `text=auto` file makes provenance **checkout-representation dependent** — two byte-different, content-identical, Git-clean states of the same blob produce two different recorded hashes (`4bb71750…` vs `8ca70d6d…`). The Day-31 gate inherits these failures via `validate_day31.py:118` until a decision (prior record's P3 class) changes either the file representation or the hash design. Nothing here performs or prescribes that change.
* [V] The 65-character transcription artifact (§3.2) is a documentation-fidelity defect in two research records; it does not affect any manifest or validator.

## 15. Recommended next factual gate

Per the prior record's sequencing, this completes candidate **P1** (byte-exact recovery succeeded; P2's "unanswerable" branch is moot). The remaining gates are decisions, not facts: (a) a governance entry (DEC-021 clerical-correction tradition) recording this reconstruction and attaching the resolved-provenance note to the four affected runs; (b) the P3 decision on whether the raw-byte hash design should be representation-insensitive; (c) correction of the two 65-character quotations as a clerical matter. None is performed or authorized by this record.

## 16. Statement on remediation

**No remediation was performed.** `configs/rl.yaml` was not modified; no validator, manifest, artifact, ledger, decision entry or prior research record was changed; the recovered bytes were written only to a temporary file outside the repository and deleted after verification; no commit, branch, ref, or index change was made. The repository's only new filesystem artifact from this investigation is this document.

---

*Record closes here. Nothing above authorizes execution of any kind; nothing below this line exists.*





