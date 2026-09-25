# SC8 raw-observation archival deposit plan

> **Status: PROPOSED — AUTHORIZES NOTHING.** This document plans a future
> archival deposit. It does not authorize an upload, reserve or publish a DOI,
> choose a license, create a public repository, alter `.gitignore`, execute
> Spark, or decide SC7 or SC8. The operator must approve those actions
> separately. No signature is present, inferred, or simulated.
>
> **Amended 2026-09-25 (Amendment 1, §12; amended in place, nothing withdrawn).**
> Passages changed by the amendment carry an `[A1]` marker. The status is
> unchanged: PROPOSED — AUTHORIZES NOTHING.

**Date:** 2026-09-24
**Scope:** preservation and replay of the raw result record needed by the
project's read-only checkers. This plan does not merge EXP-005 into
`docs/report/PAPER_DRAFT_monitoring_overhead.md`; that paper remains scoped to
monitoring overhead and the falsified IID sizing model.

## 1. Why this plan exists

`docs/PLAN.md` line 45 defines SC8 as **tests green; repository reproducible
from a fresh clone**. The tests are green, but the raw result tree is ignored by
`.gitignore` under `results/**`. A fresh clone therefore does not contain the
ledgers, manifests, transition records, and run-local artifacts from which the
committed analyses and governance ledger are checked.

`scripts/verify_reproducibility.py` demonstrates the consequence. On the current
working tree it re-derives or verifies the committed analyses from frozen raw
ledgers. On a fresh clone without those ledgers, its L1 input checks report
FAIL and the script then aborts with `FileNotFoundError` before printing its
summary or its non-SC7 label [A1]. Its
output is **corroboration only** and is explicitly **not an SC7 verdict**: SC7
requires fresh live executions compared within ±5% median. A data deposit is
needed for SC8's fresh-clone property, but it does not adjudicate SC7 and does
not create a live-execution authorization.

The raw result tree is not the only missing input [A1]. The checkers also read
the ignored dataset tree under `data/generated/`, one tracked artifact embeds
an absolute path, and one validator compares filesystem mtimes. §3.1 records
these dependencies and §12.2 measures their effect on a scratch clone.

## 2. Governing constraints

1. **No cap change and no spend.** The SC6 ledger remains **483 / 500**, with
   **17 remaining**. Deposit preparation and replay execute 0 Spark jobs and
   charge 0 to SC6.
2. **Bulk data stays out of Git [A1].** DEC-002 sets the default data root to
   `%USERPROFILE%\sparkrl_data` (overridable by `SPARKRL_DATA_ROOT`) so that
   datasets, event logs, and Spark temporary data stay out of the repository.
   It governs where data lives, not what may be deposited. On the recording
   machine the datasets actually sit in the repository's ignored
   `data/generated/` tree, which the resolver uses as a fallback
   (`src/sparkrl/workloads/resolver.py:73-82`). The raw-result overlay (§6.2)
   holds compact JSON/JSONL/CSV result records only; whether the datasets are
   also deposited is §4 item 9.
3. **No `.gitignore` repair by exception.** The archive is an external,
   versioned overlay. Raw observations are not made tracked merely to make a
   fresh clone self-contained.
4. **Bytes are evidence.** No raw file may be normalized, reformatted,
   redacted, deduplicated, or regenerated in the authoritative deposit. Any
   transformed disclosure copy would be a separately identified derivative and
   could not replace the byte-exact evidence.
5. **No relabeling.** Deposit plus deterministic replay may support SC8 after a
   successful clean-clone test. It never substitutes for SC7's live rerun.
6. **No invented identity or rights.** The repository currently has no Git
   remote, release tag, `LICENSE`, or `CITATION.cff`. Creator identity,
   affiliations, rights, and hosting cannot be inferred.

## 3. Measured baseline

Measurements below were read-only at clean `main` commit
`731871830a08cb70e550533cae900ff0540a38e4`, Python 3.11.9, and PySpark 3.5.9:

| Item | Measured value |
|---|---:|
| tracked source snapshot | 521 files before this plan commit; tree `9dc6c9d60ec670473d4d864c11b0fdbde654c483`; 5,768,867 bytes as committed blobs (5,858,082 in this Windows checkout, `core.autocrlf=true`) [A1] |
| all ignored files under `results/` | **567 files / 12,274,797 bytes** |
| ignored result formats | 529 JSON, 35 JSONL, 1 CSV, 1 Markdown, 1 marker |
| training evidence | 466 files / 2,665,278 bytes / **28 manifests** |
| required EXP-007 runs | 7 run directories / 21 files / 532,994 bytes |

The conservative candidate is **all 567 ignored files under `results/`**. This
preserves successful records together with failed attempts, smoke records,
dry/discarded material, training transitions, and run-local checkpoints. A
hand-selected subset is not proposed because it would make preservation depend
on retrospective usefulness.

Four primary ledgers already pinned by the reproducibility checker are:

| Ledger | Rows | Bytes | SHA-256 |
|---|---:|---:|---|
| `results/experiments/exp-005/observations.jsonl` | 245 | 642,941 | `d928cf5d69fe5af10aac31a2e2a69723278ee0d22729d8109e8b95ae703d3ae1` |
| `results/experiments/exp-006/observations.jsonl` | 125 | 135,540 | `be270c0be60be735e130165b8650d62272aed80f94aba1932140a706ad2eb577` [A1] |
| `results/experiments/exp-009/observations.jsonl` | 117 | 240,352 | `e58a543e5ab42f5ab7bf592e368fb1863bb365906df851e190fadec40bff5ce2` |
| `results/experiments/exp-009/ext/observations_ext.jsonl` | 4,842 | 4,824,965 | `26d878c2d01ad990bad9598448796b10d2ebf26ae2da9a93edf24061b06b799c` |

EXP-007 has no single `results/experiments/exp-007/observations.jsonl`. Its
analyzer reads each named run's `manifest.json`, `episodes.jsonl`, and final
`checkpoints/policy-*.json`. Including all of `results/training/` preserves
those inputs. The SC6 execution ledger is not all under `results/training/`
[A1]: Day-31 check 22 counts 483 = 379 live executions in the 28 training
manifests (232 Day-29 baseline + 126 EXP-007 + 21 DEC-033/DEC-038 smoke) + 84
from the tracked `results/evaluation/b4_selection.json` + 20 from the ignored
`results/experiments/exp-001/summary.json`. The 567-file overlay and the source
release together cover all three.

### 3.1 Inputs outside the raw result tree [A1]

Three further dependencies were found after the plan was committed:

1. **Datasets.** `resolve_dataset` needs `<data root>/generated/index.json`,
   each table's `manifest.json`, and at least one `*.parquet` file per table
   (`src/sparkrl/workloads/resolver.py:72-137`). All of it is ignored under
   `data/**`: `index.json` (40,828 bytes, SHA-256
   `cfe421f281b12186ff8b36a2a390667c7c74a4bf598916d6faa491d1aeed25bc`),
   `summary.json` (604 bytes, SHA-256
   `d7417969bbb482b59fb5f52b53bd4cc268421c464cd8c14f11880c5b5e8934f5`), and
   the 30 physical datasets (60 tables) under `data/generated/datasets/`:
   11,178 files and 5,410,632,172 bytes, comprising 60 manifests, 5,497
   Parquet files, 5,559 `.crc` checksum files, and 62 empty marker files.
   `summary.json` records 5,102,801,202 bytes for the valid tables. Three
   `.quarantine_*` directories left by datagen retries (under
   `skew1.5_large_s1` and `skew1_small_s0`) hold 598 of the files
   (267,873,647 bytes). Two zero-byte files in an abandoned Spark
   `_temporary` directory inside one of them sit at paths of 273 and 278
   characters, beyond the default Windows limit. Day-31 check 02, the
   Day-25/26 environment and agent
   validators, and dataset-resolving unit tests all call the resolver.
2. **EXP-007 artifact path.** The tracked
   `results/evaluation/exp007_analysis.json` records the absolute
   `training_root` `C:\Users\prakh\OneDrive\Desktop\PDS PROJECT\results\training`
   inside its analysis fingerprint
   (`06bb58594939004b4eb7a0c2b0417701f80485ad50a4f62b0c35f33b9641ce36`; file
   SHA-256 `e010072f0254a57e09656e4551d4c3ff3c6903ff9347c721b39d5ea8c0043b68`).
   A re-derivation at any other path differs, so `verify_reproducibility.py`
   check `L2 exp-007 analysis byte-identical` fails outside the original
   checkout.
3. **Filesystem mtimes.** `scripts/validate_day29.py` check 08 ("Day-28
   artifacts untouched") requires the newest mtime under the Day-28 run
   directory, directories included, to be no later than the oldest mtime
   under the Day-29 run directories (lines 511-521). `validate_day31.py` runs
   `validate_day29.py` as a sub-validator. Content hashes alone do not carry
   this property through an archive.

§12.2 measures each dependency's effect separately. Items 9-11 in §4 record the
operator decisions they require.

## 4. Required operator decisions before packaging

The following are unresolved and must be answered explicitly:

1. **Public source home:** institution repository, GitHub, GitLab, or another
   service that supports cloning an exact commit/tag.
2. **Immutable source release:** release name and commit to be published. It
   must include the plan commit and all later approved changes, but no ignored
   result bytes added to Git.
3. **Data host:** Zenodo or an institutional/domain repository. Zenodo is a
   candidate, not selected.
4. **Creator metadata:** creator name(s), ORCID or other identifier,
   affiliation, and contributor/contact roles.
5. **Rights:** separate or blanket license for code and data, if any. Absence
   of a repository license is not converted into permission.
6. **Disclosure decision:** whether public release of byte-exact files that carry
   local filesystem paths or the hostname (§5) [A1] is acceptable. If not,
   choose public release, controlled access, or embargo. Redaction requires a separately governed
   derivative and a disclosed mapping to the authoritative hashes.
7. **Retention and publication date:** public/embargo/restricted visibility and
   the date files may become available.
8. **Citation target:** the exact version DOI for raw results and the immutable
   source commit/release to cite with it.

Items 9-12 were added by Amendment 1 [A1]. The §8 acceptance test cannot pass
until items 9-11 are settled; §12.2 measures the effect of each.

9. **Dataset inputs.** The checkers need the dataset index, manifests, and
   Parquet files described in §3.1 item 1. Options: (a) deposit the dataset
   tree as a third, separately hashed release object, stating whether the
   three quarantine directories are included (§6.3); (b) regenerate the
   datasets on the replay machine and verify them against the manifest
   checksums. Datagen executes Spark, which §2 item 1 excludes from deposit
   preparation and replay, so (b) needs a decision that separately authorizes
   the datagen execution, states its SC6 treatment, and has it completed and
   verified before the Spark-disabled replay begins; (c) pre-register the
   dataset-dependent checks as a disclosed exception, which leaves SC8 only
   partly demonstrated. Option (a) involves no execution and keeps bytes exact.
10. **EXP-007 artifact path.** Options: (a) replay at the identical absolute
    path `C:\Users\prakh\OneDrive\Desktop\PDS PROJECT`, disclosed as not a
    clean-directory test; (b) re-derive `results/evaluation/exp007_analysis.json`
    with a repository-relative `training_root` under a new decision. That needs
    no execution, but the artifact's fingerprint and file hash change, and the
    values cited in `docs/research/DAY36_EXP007_ANALYSIS.md` become historical;
    (c) accept `verify_reproducibility.py` at 15/16 as a pre-registered known
    failure.
11. **File and directory mtimes.** Options: (a) record every file and directory
    mtime in `MANIFEST.json`, restore them after extraction (by an archive
    format that preserves them or by applying the recorded values), and
    verify them. ZIP's basic timestamp field has 2-second
    resolution and its extended fields are optional; Python's `zipfile`
    restores no mtimes, and many extractors do not restore directory mtimes.
    (b) Replace the mtime comparison in `validate_day29.py` check 08 under a new
    decision.
12. **Disclosure scope of the source release.** The public source release
    itself carries the local path in 220 tracked files, the hostname `Prakhar`
    in 21 tracked files (57 occurrences), and the author `prakh <prakh@local>`
    on all 78 commits (§5). Choose public disclosure or controlled hosting.
    Rewriting history is not an option: it would change every commit hash the
    record cites.

## 5. Disclosure and rights preflight

A parsed-value scan of the 567-file candidate [A1] decodes every `.json`
document and every `.jsonl` line and searches all keys and string values. It
finds the literal local path `C:\Users\prakh` in 465 files (1,632
occurrences: 880 in `.json` files and 752 in `.jsonl` files). Two of the §3
hash-pinned ledgers are among them: `exp-005/observations.jsonl` (560
occurrences) and `exp-009/observations.jsonl` (192). Two files also carry 94
double-escaped occurrences (`C:\\Users\\prakh`) inside nested exception text.
46 files contain `OneDrive`. The previously reported 463 files and 804
occurrences were wrong. The hostname `Prakhar`, which is also a personal first
name, appears 47 times in the same two ledgers, always as
`(Prakhar executor driver)` in Spark error text [A1]. No email address, bearer
token, password/passwd, API-key, or client-secret pattern matched in any file.
The three non-JSON files (one CSV, one Markdown, one marker) were scanned as
raw text. This is a triage result, not proof of privacy or absence of
sensitive content, and path or name disclosure is an operator choice. The same
identifiers appear in the tracked source release (§4 item 12).

Authoritative deposit files remain byte-exact. If public release of local paths
is unacceptable, the operator must choose controlled access, an embargo, or a
separately labeled derivative. A redacted derivative must carry its own manifest
and hashes and must never be presented as the raw record. In particular, the
four ledger SHA-256 values in §3 would no longer apply to such a derivative.
Because the EXP-005 and EXP-009 baseline ledgers carry both the path and the
hostname, any redaction necessarily breaks their pinned hashes [A1].

## 6. Package architecture

Use two independently identified release objects, plus a third for the
datasets if §4 item 9 selects option (a) [A1]:

### 6.1 Immutable source release

Publish the tracked repository at the approved commit through a public remote,
then create an immutable release/tag. A source archive may also be deposited,
but an archive alone is not described as a clone. The source release must record
its full commit hash and contain the frozen backend files, scripts, checkers,
tests, decision log, report, and tracked derived artifacts.

A GitHub release connected to Zenodo is one possible mechanism, not selected.
Zenodo's official documentation says a new version is a separate record with a
separate persistent identifier, linked to prior and future versions. That does
not make a published version's files immutable [A1]. Zenodo's manage-files page
allows the files of a published record to be edited within 30 days of
publication without changing its DOI (its create-new-upload page says 45
days), and later "in duly justified cases", including exposure of personal
data. Integrity therefore rests on the recorded SHA-256 values, not on the DOI
alone. The project must cite the exact published version, not only a concept
identifier, and must never use the in-place file-edit route: any file change
goes through a new version.

### 6.2 Versioned raw-result overlay

Create one open ZIP (or another preservation-friendly, documented format) whose
paths begin `adaspark-results/<release-commit>/results/...` [A1]. Store all 567
ignored result files at their repository-relative paths. Do not include the
tracked source tree, `.git`, virtual environments, caches, Spark event logs,
Parquet data, temp directories, OneDrive metadata, or unrelated logs.

Alongside the overlay, as separate files in the deposit rather than inside the
archive [A1], include:

- `MANIFEST.json` — schema/version, title, creator metadata placeholder until
  operator-supplied, source commit, source release identifier, build timestamp,
  archive filename, file count, byte count, per-file path relative to the
  repository root with size, SHA-256, and mtime, per-directory mtime (subject
  to §4 item 11) [A1], language/format, provenance authority, and explicit SC6
  charge of 0;
- `SHA256SUMS` — deposit-level checksums: one line for the archive and one for
  each other deposited file (`MANIFEST.json`, `README.md`, rights file),
  verified before extraction. The 567 payload hashes live in `MANIFEST.json`
  and are verified after extraction [A1];
- `README.md` — citation, exact source commit, Python/PySpark/OS requirements,
  extraction layout including the command that strips the
  `adaspark-results/<release-commit>/` prefix [A1], verification commands, and
  the SC7-versus-SC8 limitation;
- `LICENSE-DATA` or an explicit rights statement selected by the operator;
- `CITATION.cff` only after creator and rights metadata are supplied.

`MANIFEST.json` must list the four §3 ledger hashes and the EXP-007 run IDs.
It must not claim a DOI until the repository has issued one. Archive
compression bytes may vary. After extraction, all 567 payload hashes in
`MANIFEST.json` must match the authoritative local files, and file and
directory mtimes must match their recorded values unless §4 item 11 decides
otherwise [A1].

### 6.3 Dataset release object (only if §4 item 9 selects option (a)) [A1]

A separately identified archive of the dataset tree, structured like §6.2: its
own `MANIFEST.json` (per-file path relative to the data root, with size,
SHA-256, and mtime, plus per-directory mtimes), deposit-level `SHA256SUMS`, and
`README.md`. It records whether the three quarantine directories of §3.1
item 1 are included, and its manifests and index fall under the §7 step 5
disclosure scan. Two of its paths exceed 260 characters, so it must be built
and verified with long-path-aware tooling.

## 7. Packaging procedure (future, after operator approval)

1. Confirm a clean working tree and record `git rev-parse HEAD`; abort on any
   tracked modification.
2. Create the release only from the approved source commit. Do not package a
   dirty tree or OneDrive live state.
3. Enumerate ignored result files with a null-delimited command such as
   `git ls-files --others -i --exclude-standard -z -- results`; reject paths
   outside `results/`, symlinks, devices, and duplicate normalized paths. If
   §4 item 9 selects a dataset deposit, enumerate and hash that tree the same
   way as a separate release object, reading paths beyond 260 characters with
   long-path-aware tooling [A1].
4. Hash each file with SHA-256 from raw bytes. Parse every `.json` and `.jsonl`
   record to reject malformed JSON while preserving original bytes in the
   payload. Confirm the expected 567 files / 12,274,797 bytes at the recorded
   baseline; a later approved result change requires a new inventory and plan
   amendment, never a silent update to this count.
5. Run the disclosure scan, covering local paths, the hostname, and the
   tracked source release (§5, §4 item 12) [A1], and obtain explicit operator
   approval for public, embargoed, or controlled release. Do not redact in
   place.
6. Build the source release and raw overlay. Generate `MANIFEST.json`,
   `SHA256SUMS`, README, and rights files from a temporary staging directory
   outside the repository; do not add generated archives to this working tree.
7. Download/reopen the staged archive into a second temporary directory with a
   short root such as `C:\sc8v\` [A1]: long paths are disabled on the
   recording machine (`LongPathsEnabled = 0`), and prefixed archive paths
   reach 160 characters. Verify every `SHA256SUMS` line before extraction.
   After extraction, restore the recorded mtimes as §4 item 11 decides, since
   extraction alone may not restore them, then compare every extracted path,
   hash, and recorded mtime with the authoritative source [A1]. Any mismatch
   aborts publication.
8. Create a draft deposit, enter operator-supplied metadata, preview it, and
   have a second person check title, creators, rights, version, source commit,
   and visible disclosure. Publishing remains a separate operator action.

## 8. Fresh-clone acceptance test

The deposit is not accepted merely because a file uploaded successfully. The
replay runs on a clean machine or in a clean temporary directory, with live
Spark disabled, in this order [A1]:

1. **Environment.** Install Python 3.11.9, Java 17 (Temurin), and the winutils
   3.3.6 shim named in `requirements.txt`. Create a fresh virtual environment,
   install the pinned `requirements.txt` and `requirements-research.txt`, and
   record `python -V`, `pyspark.__version__`, and `pip freeze`. Do not reuse an
   environment with an editable install of another checkout: the recording
   machine's `sparkrl_env311` has one pointing at the original repository.
2. **Source.** Clone the immutable public source release at its tag, change
   into the clone, and run `pip install -e .` there. Check that
   `python -c "import sparkrl; print(sparkrl.__file__)"` resolves inside the
   clone.
3. **Data.** Verify the deposit-level `SHA256SUMS`. Extract the overlay into
   the clone's ignored `results/` paths, stripping the
   `adaspark-results/<release-commit>/` prefix. Verify every payload hash;
   subject to §4 item 11, restore and then verify every recorded mtime.
   Provide the dataset inputs as §4 item 9 decides, and point
   `SPARKRL_DATA_ROOT` at them.
4. **Checks.** With the clone as the working directory:

   ```powershell
   $env:SPARKRL_ALLOW_SPARK = $null
   python -m pytest tests
   python scripts/validate_day31.py
   python scripts/verify_reproducibility.py
   python scripts/verify_paper_claims.py
   git status --short
   ```

Then require:

- `git status --short` remains empty after extraction and after the checks
  (the overlay is ignored) [A1];
- tests have **0 failures** (the observed 718-pass/18-skip count is a
  baseline, not a pass criterion; skip counts vary by test selection and
  interpreter);
- `validate_day31.py` passes 36/36, including the 483/500 ledger and sealed
  TEST/split checks;
- `verify_reproducibility.py` passes 16/16 with 0 skips and still labels itself
  non-SC7; outside the original absolute path this requires §4 item 10 [A1];
- `verify_paper_claims.py` traces all checked claims;
- no input, derived artifact, policy, or figure is modified by replay; and
- a human records the exact DOI, version, source commit, archive SHA-256,
  platform, interpreter, commands, outputs, and date in the next report or
  decision amendment.

A failed check stops the deposit claim. Fix the source or packaging process in
a new disclosed revision; do not relax a checker, threshold, warning policy, or
test guard to obtain green output. §12.2 lists the failures measured on a
scratch clone before items 9-11 were decided. They are expected until those
decisions are made and carried out, and none of them may be cleared by
relaxing a checker [A1].

## 9. Acceptance matrix and claim boundaries

| Question | Evidence required | What it does not establish |
|---|---|---|
| Are authoritative raw records preserved? | exact source commit, 567-file inventory, per-file SHA-256, immutable version DOI | fresh Spark agreement |
| Can a fresh clone reproduce committed analyses? | clean clone + overlay + dataset inputs (§4 item 9) + an EXP-007 resolution (§4 item 10) + restored mtimes (§4 item 11) + 16/16 reproduction checker + 73 traceable claims [A1] | SC7 |
| Are tests green without live Spark? | 0 failures; report actual pass/skip counts | integration/live-Spark tests |
| Is the SC6 ledger intact? | Day-31 check 22: 483/500, 17 remaining | permission to spend |
| Is monitoring-overhead evidence intact? | DEC-040/042/043 artifacts and validators | SC6 clause 2 as a whole |
| Is EXP-005 inferentially adjudicated? | no; DEC-020 A leaves H2/H3 and SC2–SC4 UNDECIDED | any inferential claim about the learned policies |
| Has SC7 passed? | no; it requires separately authorized fresh live executions | — |

The deposit may make the project record more complete and independently
auditable. It must not convert a descriptive EXP-005 result into an inferential
verdict, make the undecided EXP-009 cell decided, or imply that re-analysis is a
live reproduction.

## 10. Repository guidance consulted

Official Zenodo documentation was consulted on 2026-09-24:

- Deposit workflow and publication/DOI timing:
  https://help.zenodo.org/docs/deposit/create-new-upload/
- DOI reservation and registration at publication:
  https://help.zenodo.org/docs/deposit/describe-records/reserve-doi/
- File limits, open formats, archive guidance, and post-publication versioning:
  https://help.zenodo.org/docs/deposit/manage-files/
- Version-specific persistent identifiers:
  https://help.zenodo.org/docs/deposit/manage-versions/
- GitHub integration overview:
  https://help.zenodo.org/docs/github/

These sources support the candidate workflow only. They do not select Zenodo,
grant a license, establish repository policy, or authorize publication. The
post-publication file-edit statements cited in §6.1 come from the
manage-files and create-new-upload pages above, as read on 2026-09-24 during
the review that led to Amendment 1 [A1].

## 11. Stop point

**STOP.** The plan is complete, but packaging and publication remain blocked on
the §4 operator decisions. No DOI is reserved or claimed. No external upload,
public remote, release, license, or signature is created. The next governed step
is a new decision recording those choices; until then, the correct state is:

- SC8: **NOT YET demonstrated from a fresh clone**;
- SC7: **NOT STARTED / not evaluated by this plan**;
- SC6: **483 / 500, 17 remaining, unchanged**;
- TEST: **untouched**;
- raw observations: **preserved locally, not deposited**; and
- Amendment 1: the §8 acceptance test is additionally blocked on §4 items
  9-11, and packaging on item 12 [A1].

## 12. Amendment record (2026-09-25; amended in place, nothing withdrawn) [A1]

This plan was committed at `9a627cf` on 2026-09-24. A review of that commit on
2026-09-24 and 2026-09-25 found factual errors, plus three missing inputs that
make the §8 acceptance test unreachable as written. This amendment corrects the
errors in place, marks each changed passage `[A1]`, and adds §3.1, §4 items
9-12, §6.3, and this section. **No conclusion is withdrawn:** SC8 remains not
demonstrated, SC7 not started, SC6 at 483/500 with 17 remaining, and TEST
sealed. The amendment makes no upload, DOI, remote, license, `.gitignore`
change, Spark execution, or SC6 charge.

### 12.1 Corrections

The table lists every change to text that existed at `9a627cf`. Wholly new
text (§3.1, §4 items 9-12, §6.3, §12, and the added sentences in §1, §5, and
§10) is marked `[A1]` where it appears.

| Where | As committed | As amended |
|---|---|---|
| §3, EXP-006 ledger hash | `be270c0be60b735e…` (63 hex digits; one dropped) | `be270c0be60be735e…eb577`, the file's SHA-256 and the value `verify_reproducibility.py` prints |
| §3, source snapshot | 5,858,082 bytes, basis unstated | 5,768,867 committed blob bytes; 5,858,082 is this Windows checkout under `core.autocrlf=true`; tree hash added |
| §3, execution ledger | `results/training/` holds "the complete execution ledger" | 483 = 379 (training manifests) + 84 (B4, tracked) + 20 (EXP-001, ignored) |
| §5, disclosure counts | 463 files / 804 occurrences | 465 files / 1,632 occurrences, plus 94 double-escaped; hostname `Prakhar` 47 times |
| §1, fresh-clone behavior | "its input checks fail" | L1 checks FAIL, then the script aborts with `FileNotFoundError` |
| §2 item 2, DEC-002 | read as limiting the deposit | DEC-002 sets the default data root; the datasets actually sit in the ignored `data/generated/` |
| §4 item 6, disclosure decision | local filesystem paths only | local paths or the hostname |
| §6 intro | "two independently identified release objects" | two, plus a dataset object if §4 item 9 selects (a) |
| §6.1, Zenodo | "a specific citation can identify immutable files" | published files can be edited for 30-45 days without a DOI change, and later in justified cases |
| §6.2, archive | root `adapspark-results/`; `SHA256SUMS` placement ambiguous; "timestamps may vary" | `adaspark-results/`; deposit-level and payload hash sets separated; mtimes recorded and verified |
| §7 steps 3, 5, 7 | — | dataset enumeration; hostname and source-release scan; short extraction root; mtimes restored before comparison |
| §8 procedure | commands listed before the clone and extraction steps; reused `sparkrl_env311` | ordered steps, starting from a fresh environment |
| §8 criteria | `git status` empty after extraction; `verify_reproducibility.py` 16/16 | `git status` empty after extraction and after the checks; 16/16 outside the original path needs §4 item 10; §12.2 failures expected until items 9-11 are settled |
| §9, fresh-clone row | clean clone + overlay + checkers | adds dataset inputs, an EXP-007 resolution, and restored mtimes |
| §11, final state | — | §8 test blocked on items 9-11, packaging on item 12 |

### 12.2 Measured fresh-clone dry run

The §8 checks were run on 2026-09-25 in a scratch clone of `9a627cf` on the
recording machine, adding one input at a time. This is a diagnostic, not an
SC8 demonstration or a deposit simulation.

| Check | Clone only | + `results/` overlay | + dataset inputs | + original mtimes |
|---|---|---|---|---|
| `verify_reproducibility.py` | aborts after 5 L1 FAILs | 15/16 (L2 exp-007) | 15/16 | 15/16 |
| `verify_paper_claims.py` | refuses: input missing | 73 claims OK | 73 claims OK | not rerun |
| `validate_day29.py` | not run | 23/24 (check 08) | 23/24 (check 08) | 24/24 |
| `validate_day31.py` | 28/36 | 30/36 | 33/36 | 34/36 |
| failing Day-31 checks | 02, 22, Day 25, 26, 28, 29, 30, 35 | 02, Day 25, 26, 29, 30, 35 | Day 29, 30, 35 | Day 30, 35 |
| `pytest tests` (failed / passed / skipped) | not run | 23 / 695 / 18 | 2 / 716 / 18 | 2 / 716 / 18 |
| `git status --short` in the clone | empty | empty | empty | empty |

With the dataset inputs and mtimes supplied, every remaining failure traces to
§3.1 item 2, the EXP-007 absolute path. That covers `verify_reproducibility.py`
check L2 and the two unit tests that exercise it,
`test_analyzer_byte_comparison_passes_on_an_exact_copy` and
`test_main_reports_pass_and_does_not_evaluate_sc7`. `validate_day30.py` check
23 and `validate_day31.py` check 35 fail because they run that unit suite. The
21 other test failures under the overlay alone were all `FileNotFoundError` on
the dataset index. Each of §4 items 9, 10, and 11 is therefore necessary on its
own.

Conditions:

- **Interpreter:** `sparkrl_env311` with `PYTHONPATH` set to the clone's `src/`,
  so the clone's code took precedence over the environment's editable install
  of the original repository. `SPARKRL_ALLOW_SPARK` was unset.
- **Dataset inputs:** for the first two conditions, `SPARKRL_DATA_ROOT` pointed
  at an empty directory. For the last two, it pointed at a scratch mirror
  holding `index.json`, `summary.json`, the 60 manifests, and the smallest real
  Parquet file of each table (47,090,209 bytes). The resolver checks only that
  Parquet files exist, so this isolates the dependency without copying 5.4 GB;
  it is not a candidate deposit.
- **Overlay and mtimes:** the overlay was copied with file mtimes preserved and
  new directory mtimes, as a plain extraction leaves them. The last condition
  copies all 1,484 file and directory mtimes under `results/` from the
  recording tree.
- **Safety:** 0 Spark executions. The recording tree's `results/` (798 files)
  and `data/generated/*.json` were hash-identical before and after.

### 12.3 Incident during the review

During the review on 2026-09-24, an editor plugin hook (installed 2026-08-19)
re-executed fragments of the
reviewers' shell commands through `cmd.exe` in the repository directory. It
truncated this document's working copy to 96 lines, created three empty files
at the repository root, and deleted the ignored `data/generated/index.json` and
`summary.json`. The document was restored from Git and the empty files were
deleted. On 2026-09-25 the operator restored both JSON files from the OneDrive
recycle bin. Their hashes are in §3.1 item 1, and the index's recorded
`created_utc`, 2026-09-10T05:17:48Z, matches its file modification time. All
798 files under `results/` were verified byte-identical against a hash baseline
taken before the damage. No Spark execution occurred and nothing was charged to
SC6. The plugin was disabled on 2026-09-25. It was also installed during the
DEC-033 and DEC-038 smoke-execution incidents; whether its replays contributed
to either has not been investigated.

### 12.4 Method

Every number this amendment introduces or corrects was re-derived on 2026-09-25
by a read-only measurement script run with `sparkrl_env311` against the working
tree at `9a627cf`:

- SHA-256 over raw bytes, and row counts as non-empty lines;
- snapshot sizes from `git ls-tree -r -l` and from `stat` of the same paths;
- ledger parts as the sum of `budget.live_executions` over the 28 training
  manifests, plus `observation_counts.total` of the B4 and EXP-001 files;
- the disclosure scan as described in §5;
- source-release counts from `git grep -l -I -i -E 'c:[\/]+users[\/]+prakh' HEAD`,
  `git grep -c -I Prakhar HEAD`, and `git log --format='%an <%ae>'`.

Two items come from other tools:

- the dataset-tree counts in §3.1 item 1 (files, Parquet, `.crc`, empty
  markers, quarantine directories, long paths) come from a PowerShell
  `Get-ChildItem -Recurse -Force` enumeration. The script's Python directory
  walk cannot see paths beyond 260 characters while `LongPathsEnabled = 0`, so
  it reports 11,176 files and 5,496 Parquet files, missing the two zero-byte
  long-path files, with an identical byte total of 5,410,632,172;
- the attribution of the last `validate_day30.py` failure in §12.2 to its
  check 23 comes from a separate run of that validator under the final
  dry-run condition.

The ignored result tree is identical at `731871830a08` and `9a627cf` (567 files,
12,274,797 bytes), so §3's other values stand. The script and its JSON output
are kept outside the repository.
