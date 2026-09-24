#!/usr/bin/env python
"""EXP-011 corroboration: re-derive the frozen analyses WITHOUT executing Spark.

WHAT THIS IS. The zero-execution half of the reproducibility record. It answers
one question mechanically: *given the frozen observation ledgers and the
analyzers committed to this repository, does re-running the analysis pipeline
today reproduce the committed derived artifacts?*

  L1  the frozen inputs are unchanged (sha256 against the value each analysis
      artifact declares for its own input);
  L2  every committed analyzer re-derives its artifact byte-for-byte (or
      content-identically where the artifact carries a deliberate timestamp);
  L3  the derived artifacts on disk are untouched by this script.

WHY IT IS NOT SC7. SC7 is "re-run reproducibility within +/-5% median" and
`experiments/registry.csv` scopes it to EXP-011, planned day 45. That criterion
is about *fresh live executions* agreeing with the recorded ones, so it cannot
be evaluated by re-analysis: it needs Spark runs, a fresh-machine or
fresh-session protocol, and an authorization this repository does not hold
(SC6 ledger 483/500, TEST = NOT AUTHORIZED). This script does not evaluate SC7
and its verdict is never SC7's verdict. What it does cover is the part of the
reproducibility claim that is *testable without spending an execution* - the
determinism of the path from raw records to reported numbers.

ANALOGUE. `scripts/validate_day29.py::probe_analysis_reproducible` made the
same move for the Day-29 analyzer: it re-derived to a throwaway temp directory
and required the fresh output to equal the stored artifact. This is that check
generalised across the pipeline.

READ-ONLY BY CONSTRUCTION. Every analyzer is invoked with its write targets
redirected into a `tempfile.mkdtemp()` directory (argument where the analyzer
has one, module-global patch where it does not). The script then re-hashes the
real artifacts and FAILS if any of them changed, so a patch that missed a write
path is caught rather than assumed away.

  python scripts/verify_reproducibility.py          # check; exit 1 on any FAIL
  python scripts/verify_reproducibility.py --keep   # keep the temp dirs
  python scripts/verify_reproducibility.py -v       # show per-analyzer output

0 Spark executions. 0 charged to SC6. No TEST row touched. No result artifact,
manifest or decision entry modified.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import platform
import shutil
import statistics
import sys
import tempfile
import time
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT / "scripts"
EVAL = PROJECT / "results" / "evaluation"

results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool | None, detail: str = "") -> None:
    status = "SKIP" if ok is None else ("PASS" if ok else "FAIL")
    results.append((name, status, detail))
    print("%-52s %-5s %s" % (name, status, detail))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_module(name: str, filename: str) -> Any:
    """Load a project script as a module, without running its __main__."""
    path = SCRIPTS / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load %s" % path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def without_lines(text: str, markers: tuple[str, ...]) -> str:
    """Drop whole lines whose stripped form starts with any marker.

    Used only for artifacts that deliberately record when they were written:
    the line is removed from BOTH sides before comparison, so the check is
    still a full-text comparison of everything else. A trailing newline is
    preserved, and a marker that matches nothing leaves the text unchanged -
    both pinned by unit tests, because a helper that quietly reformats would
    turn every comparison into a pass.
    """
    kept = [ln for ln in text.splitlines()
            if not any(ln.strip().startswith(m) for m in markers)]
    if not kept:
        return ""
    return "\n".join(kept) + ("\n" if text.endswith("\n") else "")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(ln) for ln in
            path.read_text(encoding="utf-8").splitlines() if ln.strip()]


# --------------------------------------------------------------------------
# L1 - the frozen inputs are unchanged.
# The expected digest is READ FROM THE ARTIFACT THAT DECLARES IT, so this
# cannot be satisfied by editing a constant here to match a rewritten ledger.
# key=None means "no digest was declared for this input"; the file is hashed
# and reported for the record, and the check is reported SKIP rather than PASS.
# --------------------------------------------------------------------------
FROZEN_INPUTS: tuple[tuple[str, str, str, str | None], ...] = (
    ("exp-005", "results/experiments/exp-005/observations.jsonl",
     "results/evaluation/exp005_analysis.json", "input_observations_sha256"),
    ("exp-006", "results/experiments/exp-006/observations.jsonl",
     "results/evaluation/exp006_analysis.json", "ledger_sha256"),
    ("exp-009 (n=5 baseline)", "results/experiments/exp-009/observations.jsonl",
     "results/evaluation/exp009_ext_analysis.json", "baseline_observations_sha256"),
    # Was key=None (SKIP) until the extension analysis began declaring the
    # digest of the record it was derived from. Those 4842 rows are the
    # primary evidence of EXP-009, so leaving them undeclared meant tampering
    # with them could not be detected here; now they are verified on the same
    # footing as every other frozen input.
    ("exp-009 (DEC-043 extension)",
     "results/experiments/exp-009/ext/observations_ext.jsonl",
     "results/evaluation/exp009_ext_analysis.json", "ext_observations_sha256"),
)


def check_frozen_inputs() -> None:
    for label, rel_ledger, rel_artifact, key in FROZEN_INPUTS:
        ledger = PROJECT / rel_ledger
        if not ledger.exists():
            check("L1 input %s" % label, False, "missing %s" % rel_ledger)
            continue
        got = sha256_file(ledger)
        if key is None:
            check("L1 input %s" % label, None,
                  "%s... (no declared digest; hashed for the record)" % got[:16])
            continue
        declared = json.loads((PROJECT / rel_artifact).read_text(
            encoding="utf-8")).get(key)
        if not isinstance(declared, str):
            check("L1 input %s" % label, False,
                  "%s declares no %s" % (rel_artifact, key))
            continue
        check("L1 input %s" % label, got == declared,
              "%s..." % got[:16] if got == declared
              else "sha256 %s != declared %s" % (got[:16], declared[:16]))


def check_test_separation() -> None:
    """The DEC-043 extension must contain no TEST row and no AQE-on row.

    This is the separation half of the reproducibility claim: a re-analysis can
    only reproduce a confirmatory artifact if the record being analysed is
    still the record that was authorized. The four predicates below are the
    analyzer's own refusals, re-run here independently of it.
    """
    ext = PROJECT / "results/experiments/exp-009/ext/observations_ext.jsonl"
    if not ext.exists():
        check("L1 ext train/test separation", False, "missing %s" % ext.name)
        return
    rows = read_jsonl(ext)
    artifact = json.loads(
        (EVAL / "exp009_ext_analysis.json").read_text(encoding="utf-8"))
    base = read_jsonl(PROJECT / "results/experiments/exp-009/observations.jsonl")

    ids = [r["run_id"] for r in rows]
    problems = []
    if len(rows) != artifact["n_new_observations"]:
        problems.append("row count %d != declared %d"
                        % (len(rows), artifact["n_new_observations"]))
    if len(ids) != len(set(ids)):
        problems.append("duplicate run_id")
    if any(r.get("split") != "validation" for r in rows):
        problems.append("non-validation row present")
    if any(r.get("aqe_enabled") for r in rows):
        problems.append("aqe_enabled true present")
    if any(r.get("authorized_by") != "DEC-043" for r in rows):
        problems.append("row not authorized_by DEC-043")
    overlap = set(ids) & {r["run_id"] for r in base}
    if overlap:
        problems.append("%d run_id(s) re-run from the n=5 baseline"
                        % len(overlap))
    check("L1 ext %d rows, validation-only, DEC-043, AQE-off" % len(rows),
          not problems, "; ".join(problems) if problems else
          "no TEST row, no AQE-on row, %d unique ids" % len(set(ids)))

# --------------------------------------------------------------------------
# L2 - the committed analyzers reproduce the committed artifacts.
# --------------------------------------------------------------------------
def check_exp005_rederivation() -> None:
    """EXP-005's artifact has NO committed analyzer script.

    `results/evaluation/exp005_analysis.json` was produced by an ad-hoc
    read-only pass (Day 34) and carved out as an authorized artifact in
    `scripts/validate_day31.py`. There is nothing to re-run, so its
    descriptive quantities are re-derived here instead, from the frozen
    ledger, under the median rule the artifact itself states: median over
    exactly five usable reps, fewer than five = INCOMPLETE and excluded.
    """
    art = json.loads((EVAL / "exp005_analysis.json").read_text(encoding="utf-8"))
    rows = read_jsonl(PROJECT / "results/experiments/exp-005/observations.jsonl")

    per_cell: dict[str, dict[str, list[float]]] = {}
    coverage: dict[str, dict[str, int]] = {}
    for r in rows:
        arm = r["arm"]
        cov = coverage.setdefault(arm, {"usable": 0, "failed": 0,
                                        "undefined": 0})
        err = r.get("error") or ""
        if r.get("usable"):
            cov["usable"] += 1
            key = "%s|%s|s%d" % (r["family"], r["scale"], r["seed"])
            per_cell.setdefault(key, {}).setdefault(arm, []).append(
                r["execution_time_s"])
        elif err.startswith("INCOMPLETE"):
            cov["undefined"] += 1
        else:
            cov["failed"] += 1

    def cell_sum(cells: list[str], arm: str) -> float | None:
        """Sum the UNROUNDED per-cell medians, then round once.

        The artifact stores 4-decimal sums of full-precision medians; rounding
        each cell first and then summing is off by up to 1e-4 and was the first
        version of this check - it FAILED on B0 and the failure was the
        checker's, not the artifact's.
        """
        vals = []
        for c in cells:
            five = per_cell.get(c, {}).get(arm, [])
            if len(five) != 5:
                return None
            vals.append(statistics.median(five))
        return round(sum(vals), 4)

    problems = []
    arms6 = ("B0", "B1", "B4", "RL-s0", "RL-s1", "RL-s2")
    for arms, cells, field in (
            (arms6, art["common_cells_all_non_b2"],
             "descriptive_sum_of_medians_6cell"),
            (arms6 + ("B2",), art["common_cells_b2"],
             "descriptive_sum_of_medians_b2_3cell")):
        for arm in arms:
            mine = cell_sum(cells, arm)
            theirs = round(art[field][arm], 4)
            if mine is None or abs(mine - theirs) > 1e-9:
                problems.append("%s %s re-derived %s vs %s"
                                % (field, arm, mine, theirs))
    for arm, cov in sorted(coverage.items()):
        want = art["coverage"][arm]
        for k in ("usable", "failed", "undefined"):
            if cov[k] != want[k]:
                problems.append("coverage %s %s %d != %d"
                                % (arm, k, cov[k], want[k]))
    check("L2 exp-005 descriptive re-derivation (no analyzer)",
          not problems,
          "; ".join(problems[:3]) if problems else
          "12 arm-sums + coverage over %d rows, exact at 4 decimals" % len(rows))


def _snapshot(paths: tuple[Path, ...]) -> dict[str, str]:
    return {str(p): sha256_file(p) for p in paths if p.exists()}


def check_analyzer_bytes(label: str, filename: str, out_name: str,
                         module_name: str, out_dir: Path,
                         show: bool, argstyle: str = "out") -> None:
    """Re-run an analyzer with its write target redirected; require byte equality.

    argstyle="out"   the analyzer takes `--out <path>` (exp-007).
    argstyle="proj"  it builds the path from a module-level PROJECT, so PROJECT
                     is repointed at the temp directory while the input path
                     constants it already resolved keep pointing at the real
                     frozen files (exp-006).
    """
    target = EVAL / out_name
    if not target.exists():
        check("L2 %s" % label, False, "missing %s" % out_name)
        return
    mod = load_module(module_name, filename)
    if argstyle == "out":
        dst = out_dir / out_name
        dst.parent.mkdir(parents=True, exist_ok=True)
        with redirect_stdout(sys.stdout if show else io.StringIO()):
            rc = mod.main(["--out", str(dst)])
    else:
        mod.PROJECT = out_dir
        dst = out_dir / "results" / "evaluation" / out_name
        dst.parent.mkdir(parents=True, exist_ok=True)
        with redirect_stdout(sys.stdout if show else io.StringIO()):
            rc = mod.main()
    if rc != 0 or not dst.exists():
        check("L2 %s" % label, False, "analyzer exited %s, no output" % rc)
        return
    same = dst.read_bytes() == target.read_bytes()
    check("L2 %s" % label, same,
          "byte-identical (%s...)" % sha256_file(dst)[:16] if same else
          "RE-DERIVED OUTPUT DIFFERS from %s" % out_name)




def check_exp009_ext(out_dir: Path, show: bool) -> None:
    """EXP-009's analyzer writes to fixed paths, so patch its write targets.

    `artifact_id` is a content hash that deliberately excludes `written_utc`,
    so equality of that field is the artifact's own statement that the content
    is unchanged; the full-text comparison is done with the `written_utc` line
    removed from both sides, which is strictly stronger.
    """
    art_path = EVAL / "exp009_ext_analysis.json"
    fig_dir = PROJECT / "docs" / "figures"
    fig_names = ("exp009_ci_halfwidth_vs_reps.svg",
                 "exp009_regime_structure.svg")
    if not art_path.exists():
        check("L2 exp-009 ext analysis", False, "missing exp009_ext_analysis.json")
        return
    mod = load_module("_vrfy_analyze_exp009_ext", "analyze_exp009_ext.py")
    eval_json = out_dir / "exp009_ext_analysis.json"
    mod.OUT_JSON = out_dir / "analysis_ext.json"
    mod.EVAL_OUT = eval_json
    mod.FIGURE = out_dir / fig_names[0]
    mod.FIGURE_REGIME = out_dir / fig_names[1]
    with redirect_stdout(sys.stdout if show else io.StringIO()):
        rc = mod.main()
    if rc != 0 or not eval_json.exists():
        check("L2 exp-009 ext analysis", False, "analyzer exited %s" % rc)
        return
    fresh = json.loads(eval_json.read_text(encoding="utf-8"))
    stored = json.loads(art_path.read_text(encoding="utf-8"))
    id_ok = fresh["artifact_id"] == stored["artifact_id"]
    text_ok = (without_lines(eval_json.read_text(encoding="utf-8"),
                             ("\"written_utc\"",))
               == without_lines(art_path.read_text(encoding="utf-8"),
                                ("\"written_utc\"",)))
    ok = id_ok and text_ok
    check("L2 exp-009 ext analysis", ok,
          "artifact_id %s, full text minus written_utc, identical"
          % fresh["artifact_id"][:16] if ok else
          "content mismatch (artifact_id_ok=%s, text_ok=%s)" % (id_ok, text_ok))
    for name in fig_names:
        fresh_fig = out_dir / name
        target = fig_dir / name
        if not fresh_fig.exists() or not target.exists():
            check("L2 figure %s" % name, False, "missing on one side")
            continue
        same = fresh_fig.read_bytes() == target.read_bytes()
        check("L2 figure %s" % name, same,
              "byte-identical" if same else "RE-RENDERED FIGURE DIFFERS")


def check_exp002_gate(out_dir: Path, show: bool) -> None:
    """EXP-002's report embeds `generated_utc` and `code_version`.

    It cannot be byte-compared by construction. The volatile fields are named
    and removed on both sides; everything else, including the gate verdict and
    every per-family spread the SC1 claim rests on, must match exactly.
    """
    stored_path = (PROJECT / "results" / "experiments" / "exp-002" /
                   "analysis" / "gate.json")
    if not stored_path.exists():
        check("L2 exp-002 sensitivity gate", False, "missing gate.json")
        return
    mod = load_module("_vrfy_analyze_exp002", "analyze_exp002.py")
    dest = out_dir / "exp002"
    with redirect_stdout(sys.stdout if show else io.StringIO()):
        rc = mod.main(["--out", str(dest)])
    fresh_path = dest / "gate.json"
    if rc != 0 or not fresh_path.exists():
        check("L2 exp-002 sensitivity gate", False, "analyzer exited %s" % rc)
        return
    volatile = ("generated_utc", "code_version")
    stored = json.loads(stored_path.read_text(encoding="utf-8"))
    fresh = json.loads(fresh_path.read_text(encoding="utf-8"))
    for k in volatile:
        stored.pop(k, None)
        fresh.pop(k, None)
    same = (json.dumps(stored, indent=1, sort_keys=True)
            == json.dumps(fresh, indent=1, sort_keys=True))
    check("L2 exp-002 sensitivity gate", same,
          "identical minus %s; verdict=%s, %d families"
          % ("+".join(volatile), stored.get("gate", {}).get("result"),
             len(stored.get("gate", {}).get("families", {}))) if same
          else "gate payload differs (excluding %s)" % "+".join(volatile))


def check_figures(out_dir: Path, show: bool) -> None:
    """Re-render the figure set into a throwaway FIGDIR and byte-compare.

    FIGDIR is patched, and so is PROJECT, because `main()` prints each written
    path relative to PROJECT - with FIGDIR alone the renderer raises
    ValueError before reporting, which is a limitation of the renderer's
    reporting line rather than of the render itself. The input path constants
    (EXP002/EXP005/EXP007) were resolved at import and are untouched.
    """
    mod = load_module("_vrfy_render_project_figures", "render_project_figures.py")
    mod.FIGDIR = out_dir / "figures"
    mod.PROJECT = out_dir
    with redirect_stdout(sys.stdout if show else io.StringIO()):
        rc = mod.main()
    if rc != 0:
        check("L2 figures re-render", False, "renderer exited %s" % rc)
        return
    for name in ("exp002_configuration_sensitivity.svg",
                 "exp005_arm_comparison.svg",
                 "exp007_ablation.svg"):
        fresh = out_dir / "figures" / name
        target = PROJECT / "docs" / "figures" / name
        if not fresh.exists() or not target.exists():
            check("L2 figure %s" % name, False, "missing on one side")
            continue
        same = fresh.read_bytes() == target.read_bytes()
        check("L2 figure %s" % name, same,
              "byte-identical (%d bytes)" % len(fresh.read_bytes()) if same
              else "RE-RENDERED FIGURE DIFFERS")



# --------------------------------------------------------------------------
# L3 - this script changed nothing.
# --------------------------------------------------------------------------
GUARDED: tuple[Path, ...] = (
    EVAL / "exp002_configuration_sensitivity.json",
    EVAL / "exp005_analysis.json",
    EVAL / "exp006_analysis.json",
    EVAL / "exp007_analysis.json",
    EVAL / "exp009_analysis.json",
    EVAL / "exp009_ext_analysis.json",
    PROJECT / "docs" / "figures" / "exp002_configuration_sensitivity.svg",
    PROJECT / "docs" / "figures" / "exp005_arm_comparison.svg",
    PROJECT / "docs" / "figures" / "exp007_ablation.svg",
    PROJECT / "docs" / "figures" / "exp009_ci_halfwidth_vs_reps.svg",
    PROJECT / "docs" / "figures" / "exp009_regime_structure.svg",
    PROJECT / "results" / "experiments" / "exp-002" / "analysis" / "gate.json",
    PROJECT / "results" / "experiments" / "exp-009" / "ext" / "analysis_ext.json",
)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--keep", action="store_true",
                    help="keep the temporary output directory")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="show the analyzers' own stdout")
    args = ap.parse_args(argv)

    print("EXP-011 corroboration - zero-execution reproduction of the derived "
          "artifacts")
    print("=" * 78)

    before = _snapshot(GUARDED)
    out_dir = Path(tempfile.mkdtemp(prefix="exp011_repro_"))
    try:
        check_frozen_inputs()
        check_test_separation()
        check_exp005_rederivation()
        check_analyzer_bytes("exp-006 analysis byte-identical",
                             "analyze_exp006.py", "exp006_analysis.json",
                             "_vrfy_analyze_exp006", out_dir, args.verbose,
                             argstyle="proj")
        check_analyzer_bytes("exp-007 analysis byte-identical",
                             "analyze_exp007.py", "exp007_analysis.json",
                             "_vrfy_analyze_exp007", out_dir, args.verbose)
        check_exp009_ext(out_dir, args.verbose)
        check_exp002_gate(out_dir, args.verbose)
        check_figures(out_dir, args.verbose)
        after = _snapshot(GUARDED)
        changed = sorted(p for p in set(before) | set(after)
                         if before.get(p) != after.get(p))
        check("L3 committed artifacts unchanged by this run", not changed,
              "; ".join(Path(c).name for c in changed) if changed else
              "%d artifacts re-hashed, identical" % len(after))
    finally:
        if args.keep:
            print("\ntemp outputs kept at %s" % out_dir)
        else:
            shutil.rmtree(out_dir, ignore_errors=True)

    failed = [r for r in results if r[1] == "FAIL"]
    skipped = [r for r in results if r[1] == "SKIP"]
    print("-" * 78)
    print("environment: python %s on %s" % (platform.python_version(),
                                            platform.platform()))
    print("0 Spark executions, 0 charged to SC6, TEST untouched.")
    print("This is NOT an SC7 verdict: SC7 needs fresh live executions "
          "compared within +/-5% median, and is not evaluated here.")
    print("OVERALL: %s (%d checks, %d pass, %d fail, %d skip)"
          % ("FAIL" if failed else "PASS", len(results),
             len(results) - len(failed) - len(skipped), len(failed),
             len(skipped)))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

