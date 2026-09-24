"""DEC-043 EXP-009 repetition extension - driver and analysis unit checks.

No Spark, no writes to any result artifact. These pin the properties the
DEC-043 record depends on: the authorized stage table agrees with the
artifact it was derived from, new repetitions cannot collide with or re-run
the DEC-040 record, the statistics are the IMPORTED DEC-040/042 procedure
rather than a re-implementation, and the 1/sqrt(n) prefix trajectory
behaves as the power model says it should on data that is iid by
construction.
"""
from __future__ import annotations

import importlib.util
import json
import random
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[2]
if str(PROJECT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT / "src"))


def _load(name: str, filename: str):
    path = PROJECT / "scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ext():
    return _load("t_run_exp009_ext", "run_exp009_ext.py")


@pytest.fixture(scope="module")
def ana():
    return _load("t_analyze_exp009_ext", "analyze_exp009_ext.py")


# --- authorization table ----------------------------------------------------

def test_stage_table_matches_dec043_section_3(ext):
    """The transcribed DEC-043 s3 table is internally consistent."""
    cumulative = 0
    for stage in ext.STAGES:
        assert stage["executions"] == stage["n"] * 3
        cumulative += stage["executions"]
        assert stage["cumulative"] == cumulative
    assert [s["stage"] for s in ext.STAGES] == [1, 2, 3, 4, 5, 6, 7]
    assert cumulative == 4842
    # stages 1-4 are the DEC-043 s3 recommended target
    assert sum(s["executions"] for s in ext.STAGES[:4]) == 1362


def test_stages_ordered_by_resolution_efficiency(ext):
    """DEC-043 s2: lowest required n first, nothing excluded by duration."""
    ns = [s["n"] for s in ext.STAGES]
    assert ns == sorted(ns)


def test_stage_n_agrees_with_the_source_artifact(ext):
    """Each stage n is the cell's own reps_needed_for_2pp_halfwidth (sysmon)."""
    analysis = ext.load_source_analysis()
    for stage in ext.STAGES:
        assert ext.derived_n(analysis, stage["family"], stage["scale"]) \
            == stage["n"]


def test_source_analysis_pin_refuses_a_different_artifact(ext, tmp_path,
                                                          monkeypatch):
    doc = json.loads(ext.SOURCE_ANALYSIS.read_text(encoding="utf-8"))
    doc["artifact_id"] = "0" * 64
    other = tmp_path / "tampered.json"
    other.write_text(json.dumps(doc), encoding="utf-8")
    monkeypatch.setattr(ext, "SOURCE_ANALYSIS", other)
    with pytest.raises(SystemExit):
        ext.load_source_analysis()


def test_excluded_cell_is_never_a_stage(ext):
    """F3_rdd|medium stays excluded (DEC-040 s6, DEC-042 s2, DEC-043 s5)."""
    staged = {(s["family"], s["scale"]) for s in ext.STAGES}
    assert ("F3_rdd", "medium") not in staged
    assert ext.BASE.EXCLUDED_CELLS == (("F3_rdd", "medium"),)


def test_authorization_is_validation_only(ext):
    """Every staged cell is VALIDATION seed 3; TEST and TRAIN are refused."""
    for stage in ext.STAGES:
        assert ext.BASE.exp009_guard(stage["family"], stage["scale"],
                                     ext.SEED) == "validation"
    with pytest.raises(Exception):
        ext.BASE.exp009_guard("F1_agg", "small", 0)        # TRAIN seed


# --- queue construction -----------------------------------------------------

def _queue(ext, stage_id):
    from sparkrl.spark.config import SparkConfig
    base = SparkConfig.from_yaml(str(PROJECT / ext.BASE.BASE_CONFIG_PATH))
    return ext.build_queue(ext.STAGE_BY_ID[stage_id], base), base


def test_queue_starts_after_the_recorded_repetitions(ext):
    queue, _ = _queue(ext, 1)
    reps = sorted({e["rep"] for e in queue})
    assert reps[0] == ext.BASELINE_REPS + 1 == 6
    assert reps[-1] == ext.BASELINE_REPS + ext.STAGE_BY_ID[1]["n"] == 37
    assert len(queue) == 96


def test_queue_is_rep_major_and_interleaves_conditions(ext):
    """DEC-043 s5 keeps interleaving within (cell, rep) unchanged."""
    queue, _ = _queue(ext, 1)
    names = [c["name"] for c in ext.CONDITIONS]
    for i in range(0, 12, 3):
        assert [e["condition"] for e in queue[i:i + 3]] == names
        assert len({e["rep"] for e in queue[i:i + 3]}) == 1


def test_queue_never_collides_with_the_dec040_record(ext):
    for stage_id in (1, 2, 3, 4):
        queue, _ = _queue(ext, stage_id)
        ext.collision_check(queue)                    # raises on collision


def test_queue_carries_the_condition_flags_into_every_row(ext):
    queue, _ = _queue(ext, 1)
    by_cond = {e["condition"]: e for e in queue[:3]}
    assert (by_cond["FULL"]["sysmon_enabled"],
            by_cond["FULL"]["event_log_enabled"]) == (True, True)
    assert (by_cond["NO-SYSMON"]["sysmon_enabled"],
            by_cond["NO-SYSMON"]["event_log_enabled"]) == (False, True)
    assert (by_cond["NEITHER"]["sysmon_enabled"],
            by_cond["NEITHER"]["event_log_enabled"]) == (False, False)


def test_queue_refuses_aqe(ext):
    queue, base = _queue(ext, 1)
    assert base.aqe_enabled is False
    assert all(e["config_name"] == "B0" for e in queue)


def test_baseline_record_is_pinned(ext):
    """The DEC-040/042 observations must be byte-identical to the signature."""
    ext.check_baseline_untouched()                    # raises if it moved


# --- analysis ---------------------------------------------------------------

def test_statistics_are_imported_not_reimplemented(ana):
    """Every statistic must be DEFINED IN analyze_exp009.py, not re-typed here.

    Loading that file a second time yields a distinct module object, so the
    property is checked on the defining source file rather than by identity.
    """
    canonical = _load("t_analyze_exp009_c", "analyze_exp009.py")
    for fn in (ana.bootstrap_ci, ana.adjudicate, ana.required_n,
               ana.overhead, ana.iqr):
        assert fn.__code__.co_filename.endswith("analyze_exp009.py")
    assert ana.bootstrap_ci.__code__.co_code \
        == canonical.bootstrap_ci.__code__.co_code
    assert ana.adjudicate.__code__.co_code \
        == canonical.adjudicate.__code__.co_code
    assert ana.THRESHOLD_PCT == canonical.THRESHOLD_PCT == 5.0
    assert ana.BOOTSTRAP_RESAMPLES == canonical.BOOTSTRAP_RESAMPLES == 4000
    assert ana.BOOTSTRAP_SEED == canonical.BOOTSTRAP_SEED == 0


def test_prefix_grid_contains_the_decisive_points(ana, ext):
    ks = ana.prefix_grid(37, 32)
    assert ks[0] == ext.BASELINE_REPS == 5
    assert 32 in ks                     # the authorized n DEC-043 s7 predicts
    assert ks[-1] == 37                 # the pooled n


def _rows(fam, scale, conds, reps, seed, base_s, cv, stage=None):
    """Synthetic timing-valid observations, iid by construction."""
    rng = random.Random(seed)
    out = []
    for rep in reps:
        for cond, mult in conds.items():
            out.append({
                "run_id": "x-%s-%s-%s-r%d" % (fam, scale, cond, rep),
                "family": fam, "scale": scale, "condition": cond, "rep": rep,
                "split": "validation", "timing_valid": True, "error": None,
                "execution_time_source": "runner", "aqe_enabled": False,
                "authorized_by": "DEC-043", "stage": stage,
                "execution_time_s": base_s * mult
                * (1.0 + rng.gauss(0.0, cv)),
            })
    return out


def test_samples_are_returned_in_repetition_order(ana):
    rows = _rows("F5_mixed", "medium", {"FULL": 1.0}, [3, 1, 2], 7, 10.0, 0.05)
    got = ana.samples(rows, "F5_mixed", "medium", "FULL")
    want = [r["execution_time_s"] for r in sorted(rows, key=lambda r: r["rep"])]
    assert got == want


def test_halfwidth_shrinks_as_one_over_sqrt_n_on_iid_data(ana, ext):
    """The power model must hold where its assumption holds by construction.

    This is the control for the DEC-043 s7 test: if the analysis reported a
    slope far from -0.5 on data that IS independent, a departure measured on
    the real runs would say nothing about the noise.
    """
    conds = {"FULL": 1.02, "NO-SYSMON": 1.0, "NEITHER": 1.0}
    base = _rows("F5_mixed", "medium", conds, range(1, 6), 11, 22.5, 0.08)
    new = _rows("F5_mixed", "medium", conds, range(6, 38), 12, 22.5, 0.08,
                stage=1)
    cell = ana.analyse_cell(ext.STAGE_BY_ID[1], base, new)
    traj = cell["power_model"]["sysmon_trajectory"]
    assert len(traj) >= 5
    assert cell["n_per_condition_pooled_min"] == 37
    assert traj[0]["n_per_condition"] == 5
    assert traj[-1]["ci_halfwidth_pp"] < traj[0]["ci_halfwidth_pp"]
    slope = cell["power_model"]["sysmon_loglog_slope"]
    assert slope is not None and -0.85 < slope < -0.2
    assert cell["power_model"]["predicted_loglog_slope"] == -0.5


def test_pooling_keeps_every_repetition(ana, ext):
    conds = {"FULL": 1.0, "NO-SYSMON": 1.0, "NEITHER": 1.0}
    base = _rows("F5_mixed", "medium", conds, range(1, 6), 3, 22.5, 0.05)
    new = _rows("F5_mixed", "medium", conds, range(6, 38), 4, 22.5, 0.05,
                stage=1)
    cell = ana.analyse_cell(ext.STAGE_BY_ID[1], base, new)
    for cond in ("FULL", "NO-SYSMON", "NEITHER"):
        assert cell["n_per_condition_new"][cond] == 32
        assert cell["n_per_condition_pooled"][cond] == 37


def test_a_straddling_interval_is_inconclusive_in_both_directions(ana):
    """DEC-042's interval rule, unchanged."""
    assert ana.adjudicate(6.7, (-6.4, 14.8), 5.0) == "INCONCLUSIVE"
    assert ana.adjudicate(1.2, (0.4, 2.1), 5.0) == "PASS"
    assert ana.adjudicate(9.0, (6.1, 12.0), 5.0) == "FAIL"


def test_figure_is_written_as_self_contained_svg(ana, ext, tmp_path,
                                                 monkeypatch):
    conds = {"FULL": 1.02, "NO-SYSMON": 1.0, "NEITHER": 1.0}
    base = _rows("F5_mixed", "medium", conds, range(1, 6), 21, 22.5, 0.08)
    new = _rows("F5_mixed", "medium", conds, range(6, 38), 22, 22.5, 0.08,
                stage=1)
    cell = ana.analyse_cell(ext.STAGE_BY_ID[1], base, new)
    out = tmp_path / "fig.svg"
    monkeypatch.setattr(ana, "FIGURE", out)
    ana.write_figure([cell], {"artifact_id": "a" * 64})
    svg = out.read_text(encoding="utf-8")
    assert svg.startswith("<svg") and svg.rstrip().endswith("</svg>")
    assert "F5_mixed|medium" in svg
    assert "target (DEC-043 s7)" in svg          # the reference threshold
    assert "1/sqrt(n)" in svg                    # the model reference
    assert "http://" not in svg.replace("http://www.w3.org/2000/svg", "")


# --- the write-up claim verifier -------------------------------------------

@pytest.fixture(scope="module")
def verifier():
    return _load("t_verify_paper_claims", "verify_paper_claims.py")


def test_verifier_passes_on_the_real_write_ups(verifier):
    """The committed documents must agree with the committed artifact."""
    assert verifier.main.__call__ is not None
    import sys as _sys
    argv = _sys.argv
    _sys.argv = ["verify_paper_claims.py"]
    try:
        assert verifier.main() == 0
    finally:
        _sys.argv = argv


def test_verifier_actually_fails_on_a_wrong_document(verifier, tmp_path,
                                                     monkeypatch):
    """A checker that cannot fail is worse than no checker.

    Feed it a document that contradicts the artifact and require a non-zero
    exit, so a future vacuous pass cannot go unnoticed.
    """
    bad = tmp_path / "wrong.md"
    bad.write_text("The overhead was 99.999% and nothing else.",
                   encoding="utf-8")
    monkeypatch.setattr(verifier, "DOCS", (bad,))
    import sys as _sys
    argv = _sys.argv
    _sys.argv = ["verify_paper_claims.py"]
    try:
        assert verifier.main() == 1
    finally:
        _sys.argv = argv


def test_verifier_normalises_typographic_minus(verifier):
    """Negative numbers are written with U+2212 in the prose, not '-'."""
    assert verifier.norm("\u22120.167%") == "-0.167%"
    assert verifier.norm("7.11\u00d7") == "7.11x"


def test_ext_artifact_id_is_a_content_hash(ana):
    """Re-analysis of the same observations must yield the same artifact_id.

    DEC-042 s3 states that re-analysis "reproduces byte-identically". That was
    not checkable while a wall-clock timestamp sat inside the hashed body:
    artifact_id changed on every run although no measured value did, so it
    signalled changes that had not happened. The id now hashes content only.
    """
    import hashlib as _h
    import json as _j
    doc = _j.loads(ana.OUT_JSON.read_text(encoding="utf-8"))
    assert doc["artifact_id_excludes"] == ["written_utc", "artifact_id"]
    body = {k: v for k, v in doc.items()
            if k not in ("artifact_id", "artifact_id_excludes", "written_utc")}
    canon = _j.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    assert _h.sha256(canon).hexdigest() == doc["artifact_id"]
