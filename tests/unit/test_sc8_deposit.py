"""SC8 deposit tooling - round trip, refusals and negative controls (DEC-045).

Drives the real functions of `scripts/sc8_deposit.py` against throwaway trees
in tmp_path. Nothing is read from or written to the repository's results/ or
data/ trees, no git command runs, no Spark, 0 charged to SC6. Pinned here:

  * a round trip restores every byte and every file AND directory mtime;
  * quarantined files are listed with their hashes but never archived;
  * SHA256SUMS catches a tampered archive and a missing required file;
  * install never overwrites a differing file and refuses members that are
    outside the manifest or would land outside the target, including a
    backslash traversal that the manifest itself lists;
  * a malformed SHA256SUMS line is a FAIL, not a crash;
  * build writes nothing unless every inventory matches its pinned counts;
  * --verify-only catches a changed mtime and a changed byte;
  * a staging directory inside the repository is refused before any work.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
import zipfile
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[2]
T0 = 1_700_000_000_000_000_000          # ns, an arbitrary fixed instant
FILES = {
    "results/training/run-a/manifest.json": b'{"a": 1}\n',
    "results/training/run-a/transitions/rep1.json": b"[1, 2]\n",
    "results/experiments/x/observations.jsonl": b'{"r": 1}\n{"r": 2}\n',
    "results/training/.quarantine_old/junk.bin": b"\x00\x01",
}
PREFIX = "adaspark-results/abc123/"


def _load():
    path = PROJECT / "scripts" / "sc8_deposit.py"
    spec = importlib.util.spec_from_file_location("t_sc8_deposit", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def dep():
    return _load()


@pytest.fixture(autouse=True)
def _clear_results(dep):
    dep.results.clear()
    yield
    dep.results.clear()


def _tree(root: Path) -> list[str]:
    """Write FILES with distinct mtimes, then give every directory its own."""
    for i, (rel, data) in enumerate(sorted(FILES.items())):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        os.utime(p, ns=(T0 + i * 10**9, T0 + i * 10**9))
    dirs = {str(parent).replace("\\", "/") for rel in FILES
            for parent in Path(rel).parents if str(parent) != "."}
    for j, d in enumerate(sorted(dirs, key=len, reverse=True)):
        os.utime(root / d, ns=(T0 - (j + 1) * 10**9, T0 - (j + 1) * 10**9))
    return sorted(FILES)


def _package(dep, tmp_path: Path) -> tuple[Path, Path, dict]:
    src, stage = tmp_path / "src", tmp_path / "stage"
    files, dirs, skipped = dep.collect(src, _tree(src))
    stage.mkdir()
    dep.write_archive(src, files, stage / "a.zip", PREFIX, zipfile.ZIP_DEFLATED)
    manifest = {"object": "results", "archive": "a.zip",
                "archive_prefix": PREFIX, "files": files,
                "directories": dirs, "excluded": skipped}
    return src, stage, manifest


def _statuses(dep) -> list[str]:
    return [status for _, status, _ in dep.results]


def test_round_trip_restores_bytes_and_every_mtime(dep, tmp_path):
    src, stage, manifest = _package(dep, tmp_path)
    dst = tmp_path / "dst"
    assert dep.install_object(stage, manifest, dst, verify_only=False)
    assert set(_statuses(dep)) == {"PASS"}
    for e in manifest["files"]:
        assert (dst / e["path"]).read_bytes() == (src / e["path"]).read_bytes()
        assert os.stat(dst / e["path"]).st_mtime_ns == e["mtime_ns"]
    for d in manifest["directories"]:
        assert os.stat(dst / d["path"]).st_mtime_ns == os.stat(src / d["path"]).st_mtime_ns
    assert len(manifest["directories"]) == 6      # quarantine dir not recorded


def test_quarantine_is_listed_with_its_hash_but_never_archived(dep, tmp_path):
    _, stage, manifest = _package(dep, tmp_path)
    (skip,) = manifest["excluded"]
    assert skip["path"] == "results/training/.quarantine_old/junk.bin"
    assert skip["sha256"] == hashlib.sha256(b"\x00\x01").hexdigest()
    with zipfile.ZipFile(stage / "a.zip") as zf:
        assert not any(".quarantine_" in n for n in zf.namelist())
        assert all(n.startswith(PREFIX) for n in zf.namelist())


def test_sha256sums_detects_a_tampered_archive(dep, tmp_path):
    _, stage, _ = _package(dep, tmp_path)
    dep.write_sums(stage, ["a.zip"])
    assert dep.verify_sums(stage, ["a.zip"])
    with open(stage / "a.zip", "ab") as fh:
        fh.write(b"\x00")
    dep.results.clear()
    assert not dep.verify_sums(stage, ["a.zip"])
    assert _statuses(dep) == ["FAIL"]


def test_sha256sums_must_cover_every_required_file(dep, tmp_path):
    _, stage, _ = _package(dep, tmp_path)
    dep.write_sums(stage, ["a.zip"])
    assert not dep.verify_sums(stage, ["a.zip", "MANIFEST-results.json"])


def test_install_refuses_to_overwrite_a_differing_file(dep, tmp_path):
    _, stage, manifest = _package(dep, tmp_path)
    dst = tmp_path / "dst"
    victim = dst / "results/training/run-a/manifest.json"
    victim.parent.mkdir(parents=True)
    victim.write_bytes(b"someone else's bytes")
    assert not dep.install_object(stage, manifest, dst, verify_only=False)
    assert victim.read_bytes() == b"someone else's bytes"


@pytest.mark.parametrize("member", [
    PREFIX + "results/not_in_manifest.json",      # unlisted
    PREFIX + "../../escaped.txt",                 # would leave the target
    "other-prefix/results/x.json",                # outside the prefix
])
def test_install_refuses_members_it_cannot_account_for(dep, tmp_path, member):
    _, stage, manifest = _package(dep, tmp_path)
    with zipfile.ZipFile(stage / "a.zip", "a") as zf:
        zf.writestr(member, b"x")
    dst = tmp_path / "dst"
    assert not dep.install_object(stage, manifest, dst, verify_only=False)
    assert not (tmp_path / "escaped.txt").exists()
    assert "FAIL" in _statuses(dep)


def test_backslash_traversal_is_refused_even_when_the_manifest_lists_it(
        dep, tmp_path):
    """On Windows a join re-splits backslashes, so `..\\` must be refused
    by name, not only `../` - and nothing may be written outside the target."""
    _, stage, manifest = _package(dep, tmp_path)
    evil = "..\\..\\escaped2.txt"
    manifest["files"].append({"path": evil, "size": 1, "mtime_ns": T0,
                              "sha256": hashlib.sha256(b"x").hexdigest()})
    with zipfile.ZipFile(stage / "a.zip", "a") as zf:
        zf.writestr(PREFIX + evil, b"x")
    dst = tmp_path / "dst"
    assert not dep.install_object(stage, manifest, dst, verify_only=False)
    assert not (tmp_path / "escaped2.txt").exists()
    assert not (tmp_path.parent / "escaped2.txt").exists()
    with pytest.raises(ValueError):
        dep.safe_rel(evil)


def test_malformed_sha256sums_line_is_a_failure_not_a_crash(dep, tmp_path):
    _, stage, _ = _package(dep, tmp_path)
    (stage / "SHA256SUMS").write_text("not a checksum line\n", encoding="utf-8")
    assert not dep.verify_sums(stage, ["a.zip"])
    assert _statuses(dep) == ["FAIL"]


def test_build_writes_nothing_when_any_inventory_is_off(dep, tmp_path,
                                                       monkeypatch):
    repo = tmp_path / "repo"
    _tree(repo)
    (repo / "data" / "generated").mkdir(parents=True)
    (repo / "data" / "generated" / "index.json").write_bytes(b"{}")
    kept = {k: v for k, v in FILES.items() if ".quarantine_" not in k}
    objects = {k: dict(v) for k, v in dep.OBJECTS.items()}
    objects["results"]["expected"] = (len(kept), sum(map(len, kept.values())))
    objects["datasets"]["expected"] = (999, 0)          # deliberately wrong
    monkeypatch.setattr(dep, "OBJECTS", objects)
    monkeypatch.setattr(dep, "PROJECT", repo)
    monkeypatch.setattr(dep, "git", lambda *a, **k: "" if a[0] == "status"
                        else "abc123\n")
    monkeypatch.setattr(dep, "ignored_files", lambda path: (
        sorted(FILES) if path == "results" else ["data/generated/index.json"]))
    stage = tmp_path / "stage"
    assert dep.build(stage, allow_dirty=False) == 1
    assert not stage.exists()
    assert _statuses(dep) == ["PASS", "FAIL"]           # results ok, datasets off


def test_verify_only_catches_a_changed_mtime_and_a_changed_byte(dep, tmp_path):
    _, stage, manifest = _package(dep, tmp_path)
    dst = tmp_path / "dst"
    assert dep.install_object(stage, manifest, dst, verify_only=False)
    target = dst / manifest["files"][0]["path"]
    os.utime(target, ns=(T0 + 123, T0 + 123))
    dep.results.clear()
    assert not dep.install_object(stage, manifest, dst, verify_only=True)
    assert _statuses(dep) == ["PASS", "FAIL"]          # bytes fine, mtime not
    target.write_bytes(b"changed")
    dep.results.clear()
    assert not dep.install_object(stage, manifest, dst, verify_only=True)
    assert _statuses(dep)[0] == "FAIL"


def test_collect_refuses_paths_that_leave_the_tree_or_collide(dep, tmp_path):
    (tmp_path / "d").mkdir()
    (tmp_path / "d" / "a.txt").write_bytes(b"a")
    with pytest.raises(ValueError):
        dep.collect(tmp_path, ["../outside.txt"])
    with pytest.raises(ValueError):
        dep.collect(tmp_path, ["d/a.txt", "d/A.txt"])


def test_staging_inside_the_repository_is_refused_before_any_work(dep):
    stage = PROJECT / "_sc8_stage_must_not_exist"
    assert dep.build(stage, allow_dirty=True) == 1
    assert not stage.exists()
    assert _statuses(dep) == ["FAIL"]
