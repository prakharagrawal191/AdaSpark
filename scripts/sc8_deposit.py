#!/usr/bin/env python
"""SC8 deposit: build the archival deposit, or install and verify it.

WHAT THIS IS. The executable form of sections 6-8 of
`docs/research/SC8_RAW_OBSERVATION_DEPOSIT_PLAN.md`, as decided by DEC-045.

  build    Inventory this checkout's ignored result tree and its dataset tree,
           and write two archives, one MANIFEST per archive, a deposit README,
           a data-rights statement and SHA256SUMS into a staging directory
           OUTSIDE the repository. Every file is recorded with its size,
           SHA-256 and mtime; every directory above a recorded file with its
           mtime (Day-29 check 08 compares mtimes, DEC-045 item 11).
  install  Verify a staged or downloaded deposit against SHA256SUMS, extract
           it into a fresh clone (results) and a data root (datasets), restore
           every recorded mtime, then verify every file's size, SHA-256 and
           mtime and every directory's mtime against the manifests.

  python scripts/sc8_deposit.py build --stage C:\\sc8\\stage
  python scripts/sc8_deposit.py install --stage C:\\sc8\\stage \\
         --clone C:\\sc8\\v\\adaspark --data-root C:\\sc8\\v\\data
  python scripts/sc8_deposit.py install ... --verify-only   # compare in place

`build` never writes inside the repository (a staging directory inside it is
refused), refuses a dirty tracked tree unless --allow-dirty is given (then the
manifests say so), and FAILS when the inventory differs from the counts DEC-045
pins. `install` never overwrites a file whose bytes differ from the manifest.

0 Spark executions. 0 charged to SC6. TEST untouched. No result artifact,
manifest, ledger or decision entry is modified.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import stat
import subprocess
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
SCHEMA = "adaspark-deposit-manifest/v1"
CHUNK = 1 << 20
QUARANTINE = ".quarantine_"

OBJECTS: dict[str, dict[str, Any]] = {
    "results": {
        "archive": "adaspark-results.zip",
        "manifest": "MANIFEST-results.json",
        "prefix": "adaspark-results",
        "compression": zipfile.ZIP_DEFLATED,
        "git_path": "results",
        "strip": "",                     # archive paths are repository-relative
        "extract_to": "the root of a fresh clone of the source release",
        "expected": (567, 12274797),     # plan section 3 baseline
    },
    "datasets": {
        "archive": "adaspark-datasets.zip",
        "manifest": "MANIFEST-datasets.json",
        "prefix": "adaspark-datasets",
        "compression": zipfile.ZIP_STORED,   # Parquet is already compressed
        "git_path": "data/generated",
        "strip": "data/",                # archive paths are data-root-relative
        "extract_to": "the data root (point SPARKRL_DATA_ROOT at it)",
        "expected": (10582, 5142799957),     # DEC-045 item 9
    },
}
PRINCIPAL_LEDGERS = (
    "results/experiments/exp-005/observations.jsonl",
    "results/experiments/exp-006/observations.jsonl",
    "results/experiments/exp-009/observations.jsonl",
    "results/experiments/exp-009/ext/observations_ext.jsonl",
)
EXCLUDED_REASON = ("datagen retry quarantine; read by no checker; excluded "
                   "from the archive and recorded here (DEC-045 item 9)")

results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool | None, detail: str = "") -> None:
    status = "SKIP" if ok is None else ("PASS" if ok else "FAIL")
    results.append((name, status, detail))
    print("%-44s %-5s %s" % (name, status, detail))


def os_path(p: Path) -> str:
    """A path string that still works past 260 characters on Windows.

    LongPathsEnabled is 0 on the recording machine and two excluded files sit
    beyond the limit, so every open/stat/utime goes through the extended
    prefix. Note: local drive paths only; UNC shares would need \\\\?\\UNC\\.
    """
    s = os.path.abspath(str(p))
    if os.name == "nt" and not s.startswith("\\\\?\\"):
        s = "\\\\?\\" + s
    return s


def sha256_path(p: Path) -> str:
    h = hashlib.sha256()
    with open(os_path(p), "rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def is_inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def safe_rel(rel: str) -> PurePosixPath:
    """A tree-relative posix path, or ValueError.

    Backslashes are refused outright: a Windows join would re-split them into
    real components, so `..\\x` would escape a check that only sees `/`.
    """
    pure = PurePosixPath(rel)
    if (not rel or pure.is_absolute() or ".." in pure.parts
            or ":" in rel or "\\" in rel):
        raise ValueError("refusing a path outside the tree: %r" % rel)
    return pure


def lands_inside(dst: Path, target: Path) -> bool:
    """Lexical containment check, the last guard before any write."""
    base = os.path.abspath(target)
    try:
        return os.path.commonpath([os.path.abspath(dst), base]) == base
    except ValueError:                     # different drives
        return False


def excluded(rel: str) -> bool:
    return any(part.startswith(QUARANTINE) for part in PurePosixPath(rel).parts)


def collect(root: Path, rels: list[str]) -> tuple[list[dict], list[dict], list[dict]]:
    """Inventory `rels` (posix paths relative to `root`).

    Returns (files, directories, excluded): files with size/sha256/mtime_ns,
    every directory above a kept file with its mtime_ns, and excluded files
    with their size/sha256 so that their existence stays on the record.
    """
    names = sorted(set(rels))
    folded: dict[str, str] = {}
    for rel in names:                      # every name is vetted before any I/O
        safe_rel(rel)
        key = rel.casefold()
        if key in folded:
            raise ValueError("paths collide on a case-insensitive filesystem: "
                             "%s / %s" % (folded[key], rel))
        folded[key] = rel
    files: list[dict] = []
    skipped: list[dict] = []
    dirs: set[str] = set()
    for rel in names:
        pure = PurePosixPath(rel)
        st = os.stat(os_path(root / pure), follow_symlinks=False)
        if not stat.S_ISREG(st.st_mode):
            raise ValueError("refusing a non-regular file: %s" % rel)
        entry = {"path": rel, "size": st.st_size, "sha256": sha256_path(root / pure),
                 "mtime_ns": st.st_mtime_ns}
        if excluded(rel):
            skipped.append(dict(entry, reason=EXCLUDED_REASON))
            continue
        files.append(entry)
        dirs.update(str(parent) for parent in pure.parents if str(parent) != ".")
    dir_entries = [{"path": d, "mtime_ns": os.stat(os_path(root / d)).st_mtime_ns}
                   for d in sorted(dirs)]
    return files, dir_entries, skipped


def write_archive(root: Path, files: list[dict], archive: Path, prefix: str,
                  compression: int) -> None:
    """Write `files` under `prefix`, re-hashing each while it is copied."""
    with zipfile.ZipFile(archive, "w", compression=compression,
                         allowZip64=True) as zf:
        for entry in files:
            when = datetime.datetime.fromtimestamp(entry["mtime_ns"] / 1e9)
            info = zipfile.ZipInfo(prefix + entry["path"], date_time=(
                max(when.year, 1980), when.month, when.day,
                when.hour, when.minute, when.second))
            info.compress_type = compression
            h = hashlib.sha256()
            with open(os_path(root / entry["path"]), "rb") as src, \
                    zf.open(info, "w", force_zip64=entry["size"] >= 2 ** 31) as dst:
                for chunk in iter(lambda: src.read(CHUNK), b""):
                    h.update(chunk)
                    dst.write(chunk)
            if h.hexdigest() != entry["sha256"]:
                raise RuntimeError("file changed while packaging: %s" % entry["path"])


def write_json(path: Path, obj: Any) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=True) + "\n")


def write_sums(stage: Path, names: list[str]) -> None:
    lines = ["%s  %s" % (sha256_path(stage / n), n) for n in sorted(names)]
    (stage / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8",
                                      newline="\n")


def verify_sums(stage: Path, required: list[str]) -> bool:
    sums = stage / "SHA256SUMS"
    if not sums.exists():
        check("SHA256SUMS present", False, "missing %s" % sums)
        return False
    listed: dict[str, str] = {}
    for line in sums.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split("  ", 1)
        if len(parts) != 2 or len(parts[0]) != 64:
            check("SHA256SUMS parses", False, "malformed line: %r" % line[:80])
            return False
        listed[parts[1]] = parts[0]
    missing = sorted(set(required) - set(listed))
    bad = sorted(n for n, d in listed.items()
                 if not (stage / n).exists() or sha256_path(stage / n) != d)
    ok = not missing and not bad
    check("SHA256SUMS (%d files)" % len(listed), ok,
          "every listed file matches" if ok else
          "missing=%s mismatched=%s" % (missing[:3], bad[:3]))
    return ok


def install_object(stage: Path, manifest: dict, target: Path,
                   verify_only: bool) -> bool:
    """Extract one archive into `target`, restore mtimes, verify everything."""
    name = manifest["object"]
    prefix = manifest["archive_prefix"]
    wanted = {e["path"]: e for e in manifest["files"]}
    problems: list[str] = []
    if not verify_only:
        seen: set[str] = set()
        with zipfile.ZipFile(stage / manifest["archive"]) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                if not info.filename.startswith(prefix):
                    problems.append("member outside prefix: %s" % info.filename)
                    continue
                rel = info.filename[len(prefix):]
                try:
                    pure = safe_rel(rel)
                except ValueError as exc:
                    problems.append(str(exc))
                    continue
                if rel not in wanted:
                    problems.append("member not in manifest: %s" % rel)
                    continue
                dst = target / pure
                if not lands_inside(dst, target):
                    problems.append("would land outside the target: %s" % rel)
                    continue
                seen.add(rel)
                if os.path.exists(os_path(dst)):
                    if sha256_path(dst) != wanted[rel]["sha256"]:
                        problems.append("refusing to overwrite differing %s" % rel)
                    continue
                os.makedirs(os_path(dst.parent), exist_ok=True)
                with zf.open(info) as src, open(os_path(dst), "wb") as out:
                    for chunk in iter(lambda: src.read(CHUNK), b""):
                        out.write(chunk)
        problems += ["missing from archive: %s" % r for r in sorted(set(wanted) - seen)]
        check("extract %s" % name, not problems,
              "%d files into %s" % (len(seen), target) if not problems
              else "; ".join(problems[:3]))
        if problems:
            return False
        for e in manifest["files"]:
            os.utime(os_path(target / e["path"]), ns=(e["mtime_ns"], e["mtime_ns"]))
        for d in sorted(manifest["directories"],
                        key=lambda d: d["path"].count("/"), reverse=True):
            os.utime(os_path(target / d["path"]), ns=(d["mtime_ns"], d["mtime_ns"]))
    bad_files, bad_times = [], []
    for e in manifest["files"]:
        p = target / e["path"]
        if not os.path.exists(os_path(p)):
            bad_files.append("missing " + e["path"])
            continue
        st = os.stat(os_path(p))
        if st.st_size != e["size"] or sha256_path(p) != e["sha256"]:
            bad_files.append(e["path"])
        if st.st_mtime_ns != e["mtime_ns"]:
            bad_times.append(e["path"])
    for d in manifest["directories"]:
        p = target / d["path"]
        if not os.path.isdir(os_path(p)) or os.stat(os_path(p)).st_mtime_ns != d["mtime_ns"]:
            bad_times.append(d["path"] + "/")
    check("verify %s bytes" % name, not bad_files,
          "%d files: size + SHA-256 match" % len(wanted) if not bad_files
          else "%d differ: %s" % (len(bad_files), bad_files[:3]))
    check("verify %s mtimes" % name, not bad_times,
          "%d files + %d directories match" % (len(wanted), len(manifest["directories"]))
          if not bad_times else "%d differ: %s" % (len(bad_times), bad_times[:3]))
    return not bad_files and not bad_times


def git(*args: str, cwd: Path = PROJECT) -> str:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True,
                          check=True).stdout.decode("utf-8")


def ignored_files(path: str) -> list[str]:
    raw = git("ls-files", "-z", "--others", "-i", "--exclude-standard", "--", path)
    return [p for p in raw.split("\0") if p]


def deposit_readme(commit: str, manifests: dict[str, dict]) -> str:
    rows = "\n".join(
        "| `%s` | %s | %d | %d | %s |" % (m["archive"], name, m["file_count"],
                                          m["byte_count"], m["extract_to"])
        for name, m in manifests.items())
    return """# AdaSpark raw-observation deposit

Source commit: `{commit}` (cite it together with this record's version DOI).
Built by `scripts/sc8_deposit.py` under DEC-045; plan:
`docs/research/SC8_RAW_OBSERVATION_DEPOSIT_PLAN.md`.

| Archive | Object | Files | Bytes | Extract to |
|---|---|---:|---:|---|
{rows}

Every file's size, SHA-256 and mtime, and every directory's mtime, is listed in
the matching `MANIFEST-*.json`. `SHA256SUMS` covers every other file here.

## Reproduce (Windows, the recording platform)

1. Python 3.11.9, Java 17 (Temurin) and the winutils 3.3.6 shim; a fresh
   virtual environment with `requirements.txt` and `requirements-research.txt`.
2. Clone the source release at the commit above (Git for Windows default,
   `core.autocrlf=true`), `cd` into it, `pip install -e .`.
3. `python scripts/sc8_deposit.py install --stage <this folder> --clone <clone> --data-root <data root>`
   verifies `SHA256SUMS`, extracts both archives, restores every recorded
   mtime and verifies every byte and mtime. Use short paths (for example
   `C:\\sc8\\...`); long paths are disabled by default on Windows.
4. Set `SPARKRL_DATA_ROOT=<data root>`, clear `SPARKRL_ALLOW_SPARK`, then run
   `python -m pytest tests`, `python scripts/validate_day31.py`,
   `python scripts/verify_reproducibility.py` and
   `python scripts/verify_paper_claims.py`; `git status --short` must stay empty.

## What this does and does not establish

It supports SC8 (repository reproducible from a fresh clone): the committed
analyses re-derive from these frozen records with no Spark execution. It is
NOT SC7, which requires fresh live executions compared within +/-5% median.

## Disclosure

Files are byte-exact. They contain the recording machine's local paths
(`C:\\Users\\prakh\\...`), its hostname and Spark error text; nothing was
redacted, because redaction would break the pinned hashes.

## Rights

Data: CC BY 4.0 (see `LICENSE-DATA`). Code: Apache-2.0, in the source release.
""".format(commit=commit, rows=rows)


LICENSE_DATA = """The data in this deposit (the archives adaspark-results.zip and
adaspark-datasets.zip and their MANIFEST files) is licensed under the Creative
Commons Attribution 4.0 International License (CC BY 4.0).
Legal code: https://creativecommons.org/licenses/by/4.0/legalcode
Summary: https://creativecommons.org/licenses/by/4.0/

The source code that produced and checks it is released separately under the
Apache License 2.0 (LICENSE in the source release).
"""


def build(stage: Path, allow_dirty: bool) -> int:
    stage = stage.resolve()
    if is_inside(stage, PROJECT):
        check("staging directory outside repository", False, str(stage))
        return 1
    if stage.exists() and any(stage.iterdir()):
        check("staging directory empty", False, str(stage))
        return 1
    dirty = git("status", "--porcelain", "--untracked-files=no").strip()
    if dirty and not allow_dirty:
        check("clean tracked tree", False, "commit first, or --allow-dirty "
              "for a rehearsal (never for publication)")
        return 1
    commit = git("rev-parse", "HEAD").strip()
    tree = git("rev-parse", "HEAD^{tree}").strip()
    inventories: dict[str, tuple] = {}
    for name, spec in OBJECTS.items():         # every inventory before any write
        strip = spec["strip"]
        root = PROJECT / strip if strip else PROJECT
        rels = [r[len(strip):] for r in ignored_files(spec["git_path"])]
        files, dirs, skipped = collect(root, rels)
        count, size = len(files), sum(e["size"] for e in files)
        ok = (count, size) == spec["expected"]
        check("inventory %s" % name, ok, "%d files / %d bytes, %d excluded%s"
              % (count, size, len(skipped),
                 "" if ok else "; expected %d / %d" % spec["expected"]))
        if not ok:
            return 1
        inventories[name] = (root, files, dirs, skipped, count, size)
    stage.mkdir(parents=True, exist_ok=True)
    created = datetime.datetime.now(datetime.timezone.utc).isoformat()
    manifests: dict[str, dict] = {}
    for name, spec in OBJECTS.items():
        root, files, dirs, skipped, count, size = inventories[name]
        prefix = "%s/%s/" % (spec["prefix"], commit)
        write_archive(root, files, stage / spec["archive"], prefix,
                      spec["compression"])
        manifest = {
            "schema": SCHEMA, "object": name, "created_utc": created,
            "source_commit": commit, "source_tree": tree,
            "tracked_tree_dirty": bool(dirty),
            "archive": spec["archive"], "archive_prefix": prefix,
            "extract_to": spec["extract_to"],
            "file_count": count, "byte_count": size,
            "files": files, "directories": dirs, "excluded": skipped,
            "authority": "DEC-045", "spark_executions": 0, "sc6_charge": 0,
            "doi": None,
        }
        if name == "results":
            by_path = {e["path"]: e["sha256"] for e in files}
            manifest["principal_ledgers"] = {p: by_path[p] for p in PRINCIPAL_LEDGERS}
            art = json.loads((PROJECT / "results" / "evaluation" /
                              "exp007_analysis.json").read_text(encoding="utf-8"))
            manifest["exp007_run_ids"] = sorted(
                {r["run_id"] for r in art["inputs"]["runs"]}
                | {r["run_id"] for r in art["inputs"]["full_state_reference_runs"]})
        write_json(stage / spec["manifest"], manifest)
        manifests[name] = manifest
        check("archive %s" % name, True, "%s (%d bytes)" % (
            spec["archive"], (stage / spec["archive"]).stat().st_size))
    (stage / "README.md").write_text(deposit_readme(commit, manifests),
                                     encoding="utf-8", newline="\n")
    (stage / "LICENSE-DATA").write_text(LICENSE_DATA, encoding="utf-8", newline="\n")
    names = [s["archive"] for s in OBJECTS.values()] + \
        [s["manifest"] for s in OBJECTS.values()] + ["README.md", "LICENSE-DATA"]
    write_sums(stage, names)
    check("SHA256SUMS", True, "%d files, commit %s" % (len(names), commit[:12]))
    return 0


def install(stage: Path, targets: dict[str, Path | None], verify_only: bool) -> int:
    required = [s["archive"] for n, s in OBJECTS.items() if targets.get(n)] + \
        [s["manifest"] for n, s in OBJECTS.items() if targets.get(n)]
    if not verify_sums(stage, required):       # manifests are checked in both modes
        return 1
    ok = True
    for name, spec in OBJECTS.items():
        target = targets.get(name)
        if target is None:
            continue
        manifest = json.loads((stage / spec["manifest"]).read_text(encoding="utf-8"))
        ok = install_object(stage, manifest, target, verify_only) and ok
        if name == "results" and (target / ".git").exists():
            clean = not git("status", "--porcelain", cwd=target).strip()
            check("git status clean in clone", clean,
                  "overlay is ignored" if clean else "tracked tree changed")
            ok = ok and clean
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="write the deposit into a staging directory")
    b.add_argument("--stage", required=True, type=Path)
    b.add_argument("--allow-dirty", action="store_true",
                   help="rehearsal only; the manifests record the dirty tree")
    i = sub.add_parser("install", help="verify, extract and check a deposit")
    i.add_argument("--stage", required=True, type=Path)
    i.add_argument("--clone", type=Path, help="fresh clone to receive results/")
    i.add_argument("--data-root", type=Path, help="directory to receive generated/")
    i.add_argument("--verify-only", action="store_true",
                   help="compare existing trees; extract and restore nothing")
    args = ap.parse_args(argv)
    print("SC8 deposit - %s" % args.cmd)
    print("=" * 78)
    if args.cmd == "build":
        rc = build(args.stage, args.allow_dirty)
    else:
        if args.clone is None and args.data_root is None:
            ap.error("give --clone and/or --data-root")
        rc = install(args.stage, {"results": args.clone, "datasets": args.data_root},
                     args.verify_only)
    failed = [r for r in results if r[1] == "FAIL"]
    print("-" * 78)
    print("0 Spark executions, 0 charged to SC6, TEST untouched.")
    print("OVERALL: %s (%d checks, %d fail)" % ("FAIL" if failed or rc else "PASS",
                                               len(results), len(failed)))
    return 1 if failed or rc else 0


if __name__ == "__main__":
    raise SystemExit(main())
