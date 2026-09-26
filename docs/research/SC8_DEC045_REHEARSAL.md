# SC8 deposit rehearsal under DEC-045 §5

> **Status: RECORD — AUTHORIZES NOTHING.** This is the rehearsal DEC-045 §5
> requires before any publication. It is **not** an SC8 demonstration: it ran on
> the recording machine, from an uncommitted tree, before DEC-045 was approved.
> SC8 is demonstrated only by the same run on a clean machine against the
> published records. SC7 is not evaluated.

**Date:** 2026-09-25
**Base commit:** `fc5466c` plus the uncommitted DEC-045 working tree
(`scripts/sc8_deposit.py`, the `verify_reproducibility.py` D10 change, their
tests, `.gitattributes`, `LICENSE` and the DEC-045 entry; this record was
written afterwards).
**Interpreter:** Python 3.11.9, PySpark 3.5.9 (`sparkrl_env311`, with
`PYTHONPATH` set to the clone's `src/` so the clone's code took precedence over
the environment's editable install of the original repository).
**Spark:** 0 executions; `SPARKRL_ALLOW_SPARK` unset. **SC6:** 0 charged,
483/500 unchanged. **TEST:** untouched.

## Procedure

1. `python scripts/sc8_deposit.py build --stage C:\sc8\stage --allow-dirty`
   in the recording checkout. `--allow-dirty` was required because the DEC-045
   files were uncommitted; the manifests record `"tracked_tree_dirty": true`,
   so this build is a rehearsal artefact and must never be published.
2. A scratch clone received the uncommitted DEC-045 files as a local commit;
   a **fresh clone of that scratch clone** was made at `C:\sc8\v\adaspark`, so
   the new `.gitattributes` rule applied at checkout (the EXP-007 artifact was
   checked out with LF endings under `core.autocrlf=true`).
3. `python scripts/sc8_deposit.py install --stage C:\sc8\stage --clone
   C:\sc8\v\adaspark --data-root C:\sc8\v\data`, using the clone's copy of the tool.
4. The plan §8 checks, in the clone, with `SPARKRL_DATA_ROOT=C:\sc8\v\data`.

## Results

| Step | Result |
|---|---|
| build: results inventory | 567 files / 12,274,797 bytes — matches the plan §3 pin |
| build: datasets inventory | 10,582 files / 5,142,799,957 bytes, 598 excluded — matches the DEC-045 D9 pin |
| archives | `adaspark-results.zip` 1,419,654 bytes; `adaspark-datasets.zip` 5,147,403,235 bytes |
| install: `SHA256SUMS` | 6 files, all match |
| install: results | 567 files extracted; sizes, SHA-256 and mtimes of 567 files + 559 directories match |
| install: datasets | 10,582 files extracted; sizes, SHA-256 and mtimes of 10,582 files + 152 directories match |
| `git status --short` after install | empty |
| `pytest tests` | 736 passed, 18 skipped, 0 failed |
| `validate_day31.py` | 36/36 PASS, including Day-29 check 08 and Day-31 check 22 (483/500) |
| `verify_reproducibility.py` | 16/16 PASS, 0 skip; `L2 exp-007` byte-identical once `inputs.training_root` is mapped (DEC-045 D10), landing on the committed file hash `e010072f…` |
| `verify_paper_claims.py` | every checked figure traceable |
| `git status --short` after the checks | empty |
| recording checkout afterwards | `results/` (798 files) and `data/generated/*.json` hash-identical; `git status` unchanged |

Compared with the Amendment 1 dry run (§12.2 of the plan), the three measured
gaps are closed: the dataset inputs (D9), the EXP-007 checkout path (D10) and
the directory mtimes (D11).

## An earlier run

A first rehearsal on the same day, before four review findings were fixed in
`scripts/sc8_deposit.py` (backslash path traversal, a malformed `SHA256SUMS`
line, build ordering, `--verify-only` skipping the checksum check), gave the
same results with 733 tests. The run recorded above is the one on the final
code.

## What remains before SC8

The operator's approval of DEC-045 by name, the D4 creator values, a commit,
then D2/D3 (repository, Zenodo integration, tag, records) and this same
procedure on a clean machine against the published records.
