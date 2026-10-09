#!/usr/bin/env python
"""EXP-011 corroboration: re-derive the frozen analyses WITHOUT executing Spark.

WHAT THIS IS. The zero-execution half of the reproducibility record. It answers
one question mechanically: *given the frozen observation ledgers and the
analyzers committed to this repository, does re-running the analysis pipeline
today reproduce the committed derived artifacts?*

  I0  integrity from committed files alone: the confirmatory artifacts
      (EXP-013, EXP-014) match their own content hash, their recorded
      analysis-code digests match the code in this checkout, and the frozen
      RL policies match their recorded fingerprints;
  L1  the frozen inputs are unchanged (sha256 against the value each analysis
      artifact declares for its own input);
  L2  every committed analyzer re-derives its artifact byte-for-byte (or
      content-identically where the artifact carries a deliberate timestamp,
      or - for EXP-007 only - once the checkout path it records is mapped
      back to the recorded one, DEC-045); EXP-013 and EXP-014 are re-derived
      in memory through their analyzers' own analyze();
  L3  the derived artifacts on disk are untouched by this script.

L1 and L2 need the raw research records under results/experiments/ and
results/training/, which are git-ignored and await the DEC-045 deposit. In a
fresh clone use --integrity-only: it runs I0 and the EXP-002 re-derivation (that
record is committed) and states that the other re-derivations were not run. In
the default mode a missing raw record is a FAIL, never a SKIP, so deleting a
record from an installed deposit cannot pass.

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
  python scripts/verify_reproducibility.py --integrity-only   # fresh clone
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


# The one machine-dependent field (DEC-045). EXP-007's artifact records the
# absolute directory it was derived from and hashes it into its own
# analysis_fingerprint, so a re-derivation in any other checkout differs in
# exactly that string - and, through it, in the fingerprint.
CHECKOUT_PATH_FIELDS: dict[str, tuple[str, str, str]] = {
    # artifact: (section, key, directory the analyzer defaults the key to)
    "exp007_analysis.json": ("inputs", "training_root", "results/training"),
}


def refingerprint(report: dict[str, Any]) -> str:
    """analyze_exp007.py's analysis_fingerprint, recomputed for `report`.

    Mirrors analyze_exp007.py:539-542: canonical JSON of the whole report
    with analysis_fingerprint set to None. A unit test pins it against the
    committed artifact, so drift from the analyzer's recipe FAILS there.
    """
    body = dict(report, analysis_fingerprint=None)
    payload = json.dumps(body, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def map_checkout_path(mod: Any, out_name: str, fresh: bytes,
                      stored: bytes) -> bytes | None:
    """The fresh artifact with the recorded checkout path put back, or None.

    Only the path is substituted, and only when the fresh value is this
    checkout's own directory and the recorded value is a different one. The
    fingerprint is then recomputed and the report re-serialized with the
    analyzer's own report_json(), so every other byte - every result, claim
    and the fingerprint over them - must still equal the stored file. Any
    failed precondition returns None: a real difference cannot be mapped away.
    """
    spec = CHECKOUT_PATH_FIELDS.get(out_name)
    if spec is None:
        return None
    section, key, rel = spec
    try:
        new = json.loads(fresh.decode("utf-8"))
        old = json.loads(stored.decode("utf-8"))
        got, recorded = new[section][key], old[section][key]
    except (ValueError, KeyError, TypeError):
        return None
    here = str((Path(mod.PROJECT) / rel).resolve())
    if got != here or not isinstance(recorded, str) or recorded == here:
        return None
    new[section][key] = recorded
    new["analysis_fingerprint"] = refingerprint(new)
    return mod.report_json(new).encode("utf-8")


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
    fresh, stored = dst.read_bytes(), target.read_bytes()
    if fresh == stored:
        check("L2 %s" % label, True,
              "byte-identical (%s...)" % sha256_bytes(fresh)[:16])
        return
    mapped = map_checkout_path(mod, out_name, fresh, stored)
    if mapped is not None and mapped == stored:
        section, key, _ = CHECKOUT_PATH_FIELDS[out_name]
        check("L2 %s" % label, True,
              "byte-identical once %s.%s is mapped to the recorded checkout "
              "(%s...)" % (section, key, sha256_bytes(mapped)[:16]))
        return
    check("L2 %s" % label, False,
          "RE-DERIVED OUTPUT DIFFERS from %s" % out_name)




# The tolerance for the one analyzer that is content-exact but not byte-exact
# (see check_exp009_ext): 1e-9 is five to six orders of magnitude above the
# observed 1.7e-15 association noise and far below any change that could move a
# reported figure, since the paper quotes two or three decimal places.
FLOAT_REL_TOL = 1e-9


def self_hashed_id(doc: dict[str, Any]) -> str:
    """The artifact's OWN content-hash convention, applied to it.

    `artifact_id` excludes the fields the document names in
    `artifact_id_excludes`; recomputing it here is what keeps the tolerance
    below from becoming a free pass, because the id still has to hash its own
    document rather than be compared to a constant. The exclude list itself is
    metadata ABOUT the hash, so it is outside the hashed body too - that is the
    convention an independent check verifies on the committed artifact.
    """
    body = {k: v for k, v in doc.items()
            if k not in doc["artifact_id_excludes"]
            and k != "artifact_id_excludes"}
    canon = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canon).hexdigest()


def json_leaf_diffs(fresh: Any, stored: Any,
                    path: str = "") -> list[tuple[str, Any, Any, float]]:
    """Leaf differences as (path, stored, fresh, relative deviation).

    Non-float leaves report an infinite deviation, so a changed string, a
    changed key or a changed list length is always a hard failure and can never
    hide behind a numeric tolerance.
    """
    out: list[tuple[str, Any, Any, float]] = []
    if isinstance(stored, dict) and isinstance(fresh, dict):
        for k in sorted(set(stored) | set(fresh)):
            here = "%s/%s" % (path, k)
            if k not in stored or k not in fresh:
                out.append((here, stored.get(k), fresh.get(k), float("inf")))
            else:
                out += json_leaf_diffs(fresh[k], stored[k], here)
        return out
    if isinstance(stored, list) and isinstance(fresh, list):
        if len(stored) != len(fresh):
            out.append((path + "/length", len(stored), len(fresh),
                        float("inf")))
        for i, (a, b) in enumerate(zip(fresh, stored)):
            out += json_leaf_diffs(a, b, "%s[%d]" % (path, i))
        return out
    if isinstance(stored, float) or isinstance(fresh, float):
        if stored == fresh:
            return out
        denom = max(abs(stored), abs(fresh), 1e-300)
        out.append((path or "/", stored, fresh, abs(stored - fresh) / denom))
        return out
    if stored != fresh:
        out.append((path or "/", stored, fresh, float("inf")))
    return out


def svg_without_artifact_footer(text: str) -> str:
    """An SVG with the embedded analysis hash masked out.

    Both EXP-009 figures stamp the `artifact_id` they were rendered from into
    their footer. That hash is a function of the analysis, so it moves with any
    floating-point association noise in it; masking it is what lets the figure
    check ask the question it is actually about - does the PLOT re-render,
    every number, label and coordinate equal?
    """
    out: list[str] = []
    i = 0
    while True:
        j = text.find("artifact ", i)
        if j < 0:
            out.append(text[i:])
            return "".join(out)
        k = j + len("artifact ")
        out.append(text[i:k])
        token = text[k:k + 16]
        if len(token) == 16 and all(c in "0123456789abcdef" for c in token):
            out.append("<id>")
            i = k + 16
        else:
            i = k


def check_exp009_ext(out_dir: Path, show: bool) -> None:
    """EXP-009's analyzer writes to fixed paths, so patch its write targets.

    This is the ONE analyzer here that re-derives its artifact content-exactly
    but not byte-exactly. Measured on the committed code and this environment
    (2026-09-28): 29 of the artifact's floating-point leaves come back within
    1.7e-15 relative of what is committed - 21 `lag1_autocorrelation` and 8
    `*_loglog_slope` values, about 15 ULP at those magnitudes - so `artifact_id`,
    which hashes the content, moves with them, and the two SVG footers that
    stamp that hash move too.
    Every other leaf is bit-identical: every verdict, median, interval,
    half-width and prefix-trajectory point. The mechanism is association noise
    inside those two derivations; it was not found in the committed code, and
    the committed artifact is the research record, so it is NOT regenerated to
    match the code.

    The comparison therefore keeps CONTENT strict and tolerates the arithmetic:

      * any non-float leaf difference, any structural difference - hard FAIL;
      * a float leaf further than FLOAT_REL_TOL from its committed value -
        hard FAIL;
      * `artifact_id` is not compared to the committed hash (that would fail
        on the ULP noise alone); the fresh document must instead satisfy the
        artifact's own hash convention, which is recomputed here;
      * the figures must re-render identically with the embedded artifact hash
        masked out, i.e. every plotted number, label and coordinate equal.
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
    id_self = self_hashed_id(fresh) == fresh["artifact_id"]
    diffs = [d for d in json_leaf_diffs(fresh, stored)
             if not d[0].startswith("/written_utc")
             and not d[0].startswith("/artifact_id")]
    hard = [d for d in diffs if d[3] > FLOAT_REL_TOL]
    worst = max((d[3] for d in diffs), default=0.0)
    ok = id_self and not hard
    check("L2 exp-009 ext analysis", ok,
          "content-identical to the committed artifact; %d float leaf(s) "
          "re-derived within %.0e (max %.1e), artifact_id re-verified against "
          "its own hash convention"
          % (len(diffs), FLOAT_REL_TOL, worst) if ok else
          ("artifact_id does not hash its own document" if not id_self else
           "%d leaf(s) differ beyond %.0e: %s"
           % (len(hard), FLOAT_REL_TOL,
              "; ".join("%s stored=%r fresh=%r" % (d[0], d[1], d[2])
                        for d in hard[:3]))))
    for name in fig_names:
        fresh_fig = out_dir / name
        target = fig_dir / name
        if not fresh_fig.exists() or not target.exists():
            check("L2 figure %s" % name, False, "missing on one side")
            continue
        a = fresh_fig.read_text(encoding="utf-8")
        b = target.read_text(encoding="utf-8")
        same = a == b
        masked = (not same
                  and svg_without_artifact_footer(a)
                  == svg_without_artifact_footer(b))
        check("L2 figure %s" % name, same or masked,
              "byte-identical" if same else
              ("re-renders identically; only the embedded artifact_id differs"
               if masked else "RE-RENDERED FIGURE DIFFERS"))


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
# --------------------------------------------------------------------------
# EXP-013 / EXP-014, the confirmatory studies (DEC-053, DEC-054).
# I0 uses committed files only; L1/L2 need the raw records. The re-derivation
# calls each analyzer's own analyze() and compares in memory: nothing is
# written, and the analyzers' frozen code is not touched.
# --------------------------------------------------------------------------
CONFIRMATORY: tuple[tuple[str, str, str, str], ...] = (
    # label, analyzer, committed artifact, raw-record directory
    ("exp-013", "analyze_exp013.py", "exp013_analysis.json", "results/experiments/exp-013"),
    ("exp-014", "analyze_exp014.py", "exp014_analysis.json", "results/experiments/exp-014"),
)
RL_ARMS = PROJECT / "models" / "policies" / "exp005_rl_arms.json"


def lf_sha256(path: Path) -> str:
    """The analyzers' own LF-normalised digest (DEC-037 s4)."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def artifact_self_hash(doc: dict[str, Any]) -> str:
    """artifact_id as both analyzers compute it: sha256 of the doc without it."""
    body = {k: v for k, v in doc.items() if k != "artifact_id"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str)
                          .encode("utf-8")).hexdigest()


def check_confirmatory_integrity() -> None:
    for label, _, art, _ in CONFIRMATORY:
        doc = json.loads((EVAL / art).read_text(encoding="utf-8"))
        check("I0 %s artifact self-hash" % label,
              artifact_self_hash(doc) == doc.get("artifact_id"),
              "%s..." % str(doc.get("artifact_id"))[:16])
        code = doc.get("analysis_code_sha256") or {}
        drift = sorted(rel for rel, want in code.items()
                       if not (PROJECT / rel).exists() or lf_sha256(PROJECT / rel) != want)
        deviation = doc.get("analysis_code_deviation")
        check("I0 %s analysis code = frozen digest" % label,
              bool(code) and not drift and not deviation,
              "drifted: %s" % ", ".join(drift) if drift else
              "recorded deviation: %s" % deviation if deviation else
              "%d file(s) match, no recorded deviation" % len(code))
    sys.path.insert(0, str(PROJECT / "src"))
    from sparkrl.agent.policy_store import policy_fingerprint
    arms = json.loads(RL_ARMS.read_text(encoding="utf-8"))["arms"]
    bad = [a["arm"] for a in arms if policy_fingerprint(json.loads(
        (PROJECT / a["published_path"]).read_text(encoding="utf-8"))) != a["policy_id"]]
    check("I0 frozen RL policies = recorded fingerprints", not bad,
          "mismatch: %s" % ", ".join(bad) if bad else "%d policies match" % len(arms))


def check_confirmatory_rederivation(show: bool) -> None:
    for label, analyzer, art, raw in CONFIRMATORY:
        spec_path = PROJECT / raw / "spec.json"
        obs_path = PROJECT / raw / "observations.jsonl"
        if not (spec_path.exists() and obs_path.exists()):
            check("L1 input %s" % label, False,
                  "missing %s/ (raw research record; see --integrity-only)" % raw)
            continue
        stored_text = (EVAL / art).read_text(encoding="utf-8")
        stored = json.loads(stored_text)
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        obs_sha = lf_sha256(obs_path)
        inputs_ok = (obs_sha == stored.get("input_observations_sha256")
                     and spec.get("artifact_id") == stored.get("spec_artifact_id"))
        check("L1 input %s" % label, inputs_ok,
              "%s..." % obs_sha[:16] if inputs_ok else
              "observations or spec differ from the digests the artifact declares")
        if not inputs_ok:
            continue
        mod = load_module("_vrfy_" + analyzer[:-3], analyzer)
        code = {rel: lf_sha256(PROJECT / rel) for rel in stored["analysis_code_sha256"]}
        with redirect_stdout(sys.stdout if show else io.StringIO()):
            doc = mod.analyze(spec, read_jsonl(obs_path), obs_sha, code)
        fresh = json.dumps(doc, indent=1, sort_keys=True, default=str) + "\n"
        same = fresh == stored_text.replace("\r\n", "\n")
        check("L2 %s analysis re-derived" % label, same,
              "content-identical (%s...)" % doc.get("artifact_id", "")[:16] if same
              else "RE-DERIVED OUTPUT DIFFERS from %s" % art)


GUARDED: tuple[Path, ...] = (
    EVAL / "exp013_analysis.json",
    EVAL / "exp014_analysis.json",
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
    ap.add_argument("--integrity-only", action="store_true",
                    help="fresh clone: check committed artifacts only (I0 and the "
                         "committed EXP-002 record); skip re-derivations that need "
                         "the raw research records")
    args = ap.parse_args(argv)

    print("EXP-011 corroboration - zero-execution reproduction of the derived "
          "artifacts" + (" (integrity only)" if args.integrity_only else ""))
    print("=" * 78)

    def guarded(label: str, fn: Any, *fn_args: Any) -> None:
        """Report a missing raw record as a FAIL that names it, not a traceback."""
        try:
            fn(*fn_args)
        except FileNotFoundError as exc:
            missing = Path(str(exc.filename))
            try:
                missing = missing.relative_to(PROJECT)
            except ValueError:
                pass
            check(label, False, "missing %s (raw research record; see "
                  "--integrity-only)" % missing.as_posix())

    before = _snapshot(GUARDED)
    out_dir = Path(tempfile.mkdtemp(prefix="exp011_repro_"))
    try:
        check_confirmatory_integrity()
        if args.integrity_only:
            check_exp002_gate(out_dir, args.verbose)
        else:
            check_frozen_inputs()
            guarded("L1 ext train/test separation", check_test_separation)
            guarded("L2 exp-005 descriptive re-derivation (no analyzer)",
                    check_exp005_rederivation)
            guarded("L2 exp-006 analysis byte-identical", check_analyzer_bytes,
                    "exp-006 analysis byte-identical", "analyze_exp006.py",
                    "exp006_analysis.json", "_vrfy_analyze_exp006", out_dir,
                    args.verbose, "proj")
            guarded("L2 exp-007 analysis byte-identical", check_analyzer_bytes,
                    "exp-007 analysis byte-identical", "analyze_exp007.py",
                    "exp007_analysis.json", "_vrfy_analyze_exp007", out_dir,
                    args.verbose)
            guarded("L2 exp-009 ext analysis", check_exp009_ext, out_dir, args.verbose)
            check_exp002_gate(out_dir, args.verbose)
            guarded("L2 figures re-render", check_figures, out_dir, args.verbose)
            check_confirmatory_rederivation(args.verbose)
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
    if args.integrity_only:
        print("Integrity only: the L1/L2 re-derivations need the raw research "
              "records (DEC-045 deposit) and were NOT run.")
    print("OVERALL: %s (%d checks, %d pass, %d fail, %d skip)"
          % ("FAIL" if failed else "PASS", len(results),
             len(results) - len(failed) - len(skipped), len(failed),
             len(skipped)))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

