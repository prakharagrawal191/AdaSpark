# SC8 raw-observation archival deposit plan

> **Status: PROPOSED — AUTHORIZES NOTHING.** This document plans a future
> archival deposit. It does not authorize an upload, reserve or publish a DOI,
> choose a license, create a public repository, alter `.gitignore`, execute
> Spark, or decide SC7 or SC8. The operator must approve those actions
> separately. No signature is present, inferred, or simulated.

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
ledgers. On a fresh clone without those ledgers, its input checks fail. Its
output is **corroboration only** and is explicitly **not an SC7 verdict**: SC7
requires fresh live executions compared within ±5% median. A data deposit is
needed for SC8's fresh-clone property, but it does not adjudicate SC7 and does
not create a live-execution authorization.

## 2. Governing constraints

1. **No cap change and no spend.** The SC6 ledger remains **483 / 500**, with
   **17 remaining**. Deposit preparation and replay execute 0 Spark jobs and
   charge 0 to SC6.
2. **Bulk data stays external.** DEC-002 keeps datasets, event logs, and Spark
   temporary data outside Git. This plan deposits compact JSON/JSONL/CSV result
   records, not Parquet datasets or Spark event logs.
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
| tracked source snapshot | 521 files / 5,858,082 bytes before this plan commit |
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
| `results/experiments/exp-006/observations.jsonl` | 125 | 135,540 | `be270c0be60b735e130165b8650d62272aed80f94aba1932140a706ad2eb577` |
| `results/experiments/exp-009/observations.jsonl` | 117 | 240,352 | `e58a543e5ab42f5ab7bf592e368fb1863bb365906df851e190fadec40bff5ce2` |
| `results/experiments/exp-009/ext/observations_ext.jsonl` | 4,842 | 4,824,965 | `26d878c2d01ad990bad9598448796b10d2ebf26ae2da9a93edf24061b06b799c` |

EXP-007 has no single `results/experiments/exp-007/observations.jsonl`. Its
analyzer reads each named run's `manifest.json`, `episodes.jsonl`, and final
`checkpoints/policy-*.json`. Including all of `results/training/` preserves
those inputs and the complete execution ledger.

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
   local filesystem paths is acceptable. If not, choose public release,
   controlled access, or embargo. Redaction requires a separately governed
   derivative and a disclosed mapping to the authoritative hashes.
7. **Retention and publication date:** public/embargo/restricted visibility and
   the date files may become available.
8. **Citation target:** the exact version DOI for raw results and the immutable
   source commit/release to cite with it.

## 5. Disclosure and rights preflight

A parsed-value scan of the 567-file candidate found the literal local path
`C:\Users\prakh` in 463 files (804 occurrences); 46 files also contain
`OneDrive`. No email address, bearer token, password, passwd, API-key, or
client-secret value was found by the limited pattern scan. This is a triage
result, not proof of privacy or absence of sensitive content: CSV/Markdown and
future files require a separate review, and path disclosure is an operator
choice.

Authoritative deposit files remain byte-exact. If public release of local paths
is unacceptable, the operator must choose controlled access, an embargo, or a
separately labeled derivative. A redacted derivative must carry its own manifest
and hashes and must never be presented as the raw record. In particular, the
four ledger SHA-256 values in §3 would no longer apply to such a derivative.

## 6. Package architecture

Use two independently identified release objects:

### 6.1 Immutable source release

Publish the tracked repository at the approved commit through a public remote,
then create an immutable release/tag. A source archive may also be deposited,
but an archive alone is not described as a clone. The source release must record
its full commit hash and contain the frozen backend files, scripts, checkers,
tests, decision log, report, and tracked derived artifacts.

A GitHub release connected to Zenodo is one possible mechanism, not selected.
Zenodo's official documentation says a new version is a separate record with a
separate persistent identifier, linked to prior and future versions, so a
specific citation can identify immutable files. The project must cite the exact
published version, not only a concept identifier.

### 6.2 Versioned raw-result overlay

Create one open ZIP (or another preservation-friendly, documented format) whose
paths begin `adapspark-results/<release-commit>/results/...`. Store all 567
ignored result files at their repository-relative paths. Do not include the
tracked source tree, `.git`, virtual environments, caches, Spark event logs,
Parquet data, temp directories, OneDrive metadata, or unrelated logs.

Alongside the overlay, include:

- `MANIFEST.json` — schema/version, title, creator metadata placeholder until
  operator-supplied, source commit, source release identifier, build timestamp,
  archive filename, file count, byte count, per-file relative path/size/SHA-256,
  language/format, provenance authority, and explicit SC6 charge of 0;
- `SHA256SUMS` — one line per payload file, including `MANIFEST.json`, using
  paths relative to the archive root;
- `README.md` — citation, exact source commit, Python/PySpark/OS requirements,
  extraction layout, verification commands, and the SC7-versus-SC8 limitation;
- `LICENSE-DATA` or an explicit rights statement selected by the operator;
- `CITATION.cff` only after creator and rights metadata are supplied.

`MANIFEST.json` must list the four §3 ledger hashes and the EXP-007 run IDs.
It must not claim a DOI until the repository has issued one. Timestamps and
archive compression bytes may vary, but every extracted payload-file hash must
match the authoritative local file.

## 7. Packaging procedure (future, after operator approval)

1. Confirm a clean working tree and record `git rev-parse HEAD`; abort on any
   tracked modification.
2. Create the release only from the approved source commit. Do not package a
   dirty tree or OneDrive live state.
3. Enumerate ignored result files with a null-delimited command such as
   `git ls-files --others -i --exclude-standard -z -- results`; reject paths
   outside `results/`, symlinks, devices, and duplicate normalized paths.
4. Hash each file with SHA-256 from raw bytes. Parse every `.json` and `.jsonl`
   record to reject malformed JSON while preserving original bytes in the
   payload. Confirm the expected 567 files / 12,274,797 bytes at the recorded
   baseline; a later approved result change requires a new inventory and plan
   amendment, never a silent update to this count.
5. Run the disclosure scan and obtain explicit operator approval for public,
   embargoed, or controlled release. Do not redact in place.
6. Build the source release and raw overlay. Generate `MANIFEST.json`,
   `SHA256SUMS`, README, and rights files from a temporary staging directory
   outside the repository; do not add generated archives to this working tree.
7. Download/reopen the staged archive in a second temporary directory, verify
   every `SHA256SUMS` line, and compare every extracted path and hash with the
   authoritative source. Any mismatch aborts publication.
8. Create a draft deposit, enter operator-supplied metadata, preview it, and
   have a second person check title, creators, rights, version, source commit,
   and visible disclosure. Publishing remains a separate operator action.

## 8. Fresh-clone acceptance test

The deposit is not accepted merely because a file uploaded successfully. On a
clean machine or clean temporary directory, with live Spark disabled:

```powershell
$env:SPARKRL_ALLOW_SPARK=$null
& "$HOME\sparkrl_env311\Scripts\python.exe" -m pytest tests
& "$HOME\sparkrl_env311\Scripts\python.exe" scripts/validate_day31.py
& "$HOME\sparkrl_env311\Scripts\python.exe" scripts/verify_reproducibility.py
& "$HOME\sparkrl_env311\Scripts\python.exe" scripts/verify_paper_claims.py
```

The replay must use a fresh clone of the immutable public source release. Verify
`SHA256SUMS`; extract the overlay only into the clone's ignored `results/`
paths; then require:

- `git status --short` remains empty after extraction (the overlay is ignored);
- tests have **0 failures** (the observed 718-pass/18-skip count is a
  baseline, not a pass criterion; skip counts vary by test selection and
  interpreter);
- `validate_day31.py` passes 36/36, including the 483/500 ledger and sealed
  TEST/split checks;
- `verify_reproducibility.py` passes 16/16 with 0 skips and still labels itself
  non-SC7;
- `verify_paper_claims.py` traces all checked claims;
- no input, derived artifact, policy, or figure is modified by replay; and
- a human records the exact DOI, version, source commit, archive SHA-256,
  platform, interpreter, commands, outputs, and date in the next report or
  decision amendment.

A failed check stops the deposit claim. Fix the source or packaging process in
a new disclosed revision; do not relax a checker, threshold, warning policy, or
test guard to obtain green output.

## 9. Acceptance matrix and claim boundaries

| Question | Evidence required | What it does not establish |
|---|---|---|
| Are authoritative raw records preserved? | exact source commit, 567-file inventory, per-file SHA-256, immutable version DOI | fresh Spark agreement |
| Can a fresh clone reproduce committed analyses? | clean clone + overlay + 16/16 reproduction checker + 73 traceable claims | SC7 |
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
grant a license, establish repository policy, or authorize publication.

## 11. Stop point

**STOP.** The plan is complete, but packaging and publication remain blocked on
the §4 operator decisions. No DOI is reserved or claimed. No external upload,
public remote, release, license, or signature is created. The next governed step
is a new decision recording those choices; until then, the correct state is:

- SC8: **NOT YET demonstrated from a fresh clone**;
- SC7: **NOT STARTED / not evaluated by this plan**;
- SC6: **483 / 500, 17 remaining, unchanged**;
- TEST: **untouched**; and
- raw observations: **preserved locally, not deposited**.
