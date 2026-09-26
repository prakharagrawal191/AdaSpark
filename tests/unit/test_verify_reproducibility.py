"""EXP-011 corroboration harness - detection logic, negative controls included.

`scripts/verify_reproducibility.py` is only worth running if it CAN fail. These
tests drive the REAL production check functions against throwaway fixture trees
(monkeypatched module constants) and against the frozen ledgers read-only, and
they pin the properties the harness's verdict depends on:

  * the expected input digest is READ FROM THE ARTIFACT that declares it, so
    rewriting a ledger cannot be laundered by editing a constant in the script;
  * a re-derived sum that is off by one unit FAILS - checked by corrupting a
    copy of the artifact, not the artifact;
  * the "< 5 usable reps = INCOMPLETE" median rule really excludes a cell
    rather than quietly averaging four observations;
  * a stale or edited stored artifact FAILS the byte comparison;
  * EXP-007's recorded checkout path is the ONLY thing ever mapped (DEC-045):
    a relocated artifact passes, a relocated one with an edited result and a
    matching recomputed fingerprint still fails.

No Spark, no TEST row, no write outside tmp_path, 0 charged to SC6.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[2]
if str(PROJECT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT / "src"))

EXP005_LEDGER = PROJECT / "results" / "experiments" / "exp-005" / "observations.jsonl"
EXP005_ARTIFACT = PROJECT / "results" / "evaluation" / "exp005_analysis.json"


def _load():
    path = PROJECT / "scripts" / "verify_reproducibility.py"
    spec = importlib.util.spec_from_file_location("t_verify_reproducibility", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def vrfy():
    return _load()


@pytest.fixture(autouse=True)
def _clear_results(vrfy):
    vrfy.results.clear()
    yield vrfy.results
    vrfy.results.clear()


def _verdicts(mod) -> list[tuple[str, str, str]]:
    """(name, status, detail) for every check recorded so far."""
    return list(mod.results)


def _outcomes(mod) -> list[tuple[str, str]]:
    return [(name, status) for name, status, _ in mod.results]


def _copy_real_exp005_artifact(dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(EXP005_ARTIFACT.read_bytes())
    return dest


# --- helpers ---------------------------------------------------------------

def test_without_lines_drops_only_the_named_fields(vrfy):
    text = 'a\n "written_utc": "x",\n "artifact_id": "y",\n'
    assert vrfy.without_lines(text, ('"written_utc"',)) == \
        'a\n "artifact_id": "y",\n'
    # a marker that matches nothing removes nothing (no silent full deletion)
    assert vrfy.without_lines(text, ('"nope"',)) == text
    # the trailing newline survives the edit, so the comparison stays textual
    assert vrfy.without_lines(text, ('a',)).endswith("\n")


def test_sha256_helpers_agree(vrfy, tmp_path):
    blob = tmp_path / "b.bin"
    blob.write_bytes(b"sparkrl")
    assert vrfy.sha256_file(blob) == vrfy.sha256_bytes(b"sparkrl")
    assert vrfy.sha256_file(blob) == hashlib.sha256(b"sparkrl").hexdigest()


# --- L1: the expected digest comes from the artifact, not from the script ----

def _frozen_fixture(tmp_path: Path, monkeypatch, vrfy, declared: str | None):
    """A one-entry FROZEN_INPUTS table over a throwaway ledger + artifact."""
    ledger = tmp_path / "results" / "exp" / "observations.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text('{"arm": "B0"}\n', encoding="utf-8")
    artifact = tmp_path / "eval" / "analysis.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(json.dumps({"input_observations_sha256": declared}),
                        encoding="utf-8")
    monkeypatch.setattr(vrfy, "PROJECT", tmp_path)
    monkeypatch.setattr(vrfy, "FROZEN_INPUTS", (
        ("fixture", "results/exp/observations.jsonl", "eval/analysis.json",
         "input_observations_sha256"),))
    return vrfy.sha256_file(ledger)


def test_accepts_the_digest_the_artifact_declares(vrfy, tmp_path, monkeypatch):
    good = _frozen_fixture(tmp_path, monkeypatch, vrfy, None)
    monkeypatch.setattr(vrfy, "FROZEN_INPUTS", (
        ("fixture", "results/exp/observations.jsonl", "eval/analysis.json",
         "input_observations_sha256"),))
    artifact = tmp_path / "eval" / "analysis.json"
    artifact.write_text(json.dumps({"input_observations_sha256": good}),
                        encoding="utf-8")
    vrfy.check_frozen_inputs()
    assert _outcomes(vrfy) == [("L1 input fixture", "PASS")]


def test_rejects_a_ledger_that_disagrees_with_its_declared_digest(
        vrfy, tmp_path, monkeypatch):
    _frozen_fixture(tmp_path, monkeypatch, vrfy, "0" * 64)
    vrfy.check_frozen_inputs()
    assert _outcomes(vrfy) == [("L1 input fixture", "FAIL")]


def test_missing_ledger_is_a_failure_not_a_skip(vrfy, tmp_path, monkeypatch):
    monkeypatch.setattr(vrfy, "PROJECT", tmp_path)
    monkeypatch.setattr(vrfy, "FROZEN_INPUTS", (
        ("gone", "results/exp/observations.jsonl", "eval/analysis.json",
         "input_observations_sha256"),))
    vrfy.check_frozen_inputs()
    assert _outcomes(vrfy) == [("L1 input gone", "FAIL")]


def test_artifact_declaring_no_digest_is_a_failure(vrfy, tmp_path, monkeypatch):
    """A null/missing declared digest must FAIL, not crash the harness."""
    _frozen_fixture(tmp_path, monkeypatch, vrfy, None)
    vrfy.check_frozen_inputs()
    (name, status, detail), = _verdicts(vrfy)
    assert (name, status) == ("L1 input fixture", "FAIL")
    assert "declares no" in detail


def test_undeclared_digest_is_reported_skip_with_the_hash(vrfy, tmp_path,
                                                          monkeypatch):
    digest = _frozen_fixture(tmp_path, monkeypatch, vrfy, "0" * 64)
    monkeypatch.setattr(vrfy, "FROZEN_INPUTS", (
        ("fixture", "results/exp/observations.jsonl", "eval/analysis.json",
         None),))
    vrfy.check_frozen_inputs()
    (name, status, detail), = _verdicts(vrfy)
    assert (name, status) == ("L1 input fixture", "SKIP")
    assert digest[:16] in detail




# --- L2: the EXP-005 descriptive re-derivation ------------------------------

def test_exp005_rederivation_matches_the_frozen_ledger(vrfy):
    """245 sealed rows, 7 arms, no analyzer script exists for this artifact."""
    vrfy.check_exp005_rederivation()
    (name, status, detail), = _verdicts(vrfy)
    assert name.startswith("L2 exp-005")
    assert status == "PASS", detail
    assert "245 rows" in detail


@pytest.mark.parametrize("field,arm,delta", [
    ("descriptive_sum_of_medians_6cell", "B0", 1.0),
    ("descriptive_sum_of_medians_6cell", "RL-s2", -0.5),
    ("descriptive_sum_of_medians_b2_3cell", "B2", 0.25),
])
def test_exp005_rederivation_detects_a_tampered_sum(vrfy, tmp_path, monkeypatch,
                                                    field, arm, delta):
    art = json.loads(EXP005_ARTIFACT.read_text(encoding="utf-8"))
    art[field][arm] = round(art[field][arm] + delta, 4)
    dest = tmp_path / "exp005_analysis.json"
    dest.write_text(json.dumps(art), encoding="utf-8")
    monkeypatch.setattr(vrfy, "EVAL", tmp_path)
    vrfy.check_exp005_rederivation()
    assert _verdicts(vrfy)[0][1] == "FAIL"


def test_exp005_rederivation_detects_tampered_coverage(vrfy, tmp_path,
                                                       monkeypatch):
    art = json.loads(EXP005_ARTIFACT.read_text(encoding="utf-8"))
    art["coverage"]["B0"]["usable"] += 1
    dest = tmp_path / "exp005_analysis.json"
    dest.write_text(json.dumps(art), encoding="utf-8")
    monkeypatch.setattr(vrfy, "EVAL", tmp_path)
    vrfy.check_exp005_rederivation()
    assert _verdicts(vrfy)[0][1] == "FAIL"


def test_exp005_cell_with_four_usable_reps_is_excluded(vrfy, tmp_path,
                                                       monkeypatch):
    """DEC-017 item 5: median over EXACTLY five usable reps.

    A synthetic ledger where one of the six common cells has only four usable
    reps must FAIL rather than silently averaging four observations.
    """
    cells = json.loads(EXP005_ARTIFACT.read_text(
        encoding="utf-8"))["common_cells_all_non_b2"]
    arms7 = ("B0", "B1", "B2", "B4", "RL-s0", "RL-s1", "RL-s2")
    rows = []
    for c in cells:
        family, scale, seed = c.split("|")
        for arm in arms7:
            for rep in range(1, 6):
                if c == cells[0] and rep == 5:
                    continue          # four usable reps in this cell
                rows.append({"arm": arm, "family": family, "scale": scale,
                             "seed": int(seed[1:]), "rep": rep, "usable": True,
                             "execution_time_s": 1.0 + rep})
    ledger = tmp_path / "results" / "experiments" / "exp-005"
    ledger.mkdir(parents=True)
    (ledger / "observations.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    art = {"common_cells_all_non_b2": cells, "common_cells_b2": [],
           "descriptive_sum_of_medians_6cell": {a: 0.0 for a in arms7},
           "descriptive_sum_of_medians_b2_3cell": {a: 0.0 for a in arms7},
           "coverage": {a: {"usable": 0, "failed": 0, "undefined": 0}
                        for a in arms7}}
    eval_dir = tmp_path / "eval"
    eval_dir.mkdir()
    (eval_dir / "exp005_analysis.json").write_text(json.dumps(art),
                                                   encoding="utf-8")
    monkeypatch.setattr(vrfy, "PROJECT", tmp_path)
    monkeypatch.setattr(vrfy, "EVAL", eval_dir)
    vrfy.check_exp005_rederivation()
    (name, status, detail), = _verdicts(vrfy)
    assert status == "FAIL"


# --- L2: byte comparison, the exp-002 volatile-field rule, the figures -------

def _stored_copy(tmp_path: Path, name: str, mutate=None) -> Path:
    """A throwaway stand-in for the stored artifact the check compares against.

    With no mutation the copy is byte-exact, so the comparison tests the
    analyzer rather than the JSON serializer.
    """
    eval_dir = tmp_path / "eval"
    eval_dir.mkdir(exist_ok=True)
    real = PROJECT / "results" / "evaluation" / name
    if mutate is None:
        (eval_dir / name).write_bytes(real.read_bytes())
        return eval_dir
    data = json.loads(real.read_text(encoding="utf-8"))
    mutate(data)
    (eval_dir / name).write_text(
        json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return eval_dir


def test_analyzer_byte_comparison_passes_on_an_exact_copy(vrfy, tmp_path,
                                                          monkeypatch):
    eval_dir = _stored_copy(tmp_path, "exp007_analysis.json")
    monkeypatch.setattr(vrfy, "EVAL", eval_dir)
    vrfy.check_analyzer_bytes("t", "analyze_exp007.py", "exp007_analysis.json",
                              "t_exp007_ok", tmp_path / "out", False)
    assert _outcomes(vrfy)[0][1] == "PASS"


def test_analyzer_byte_comparison_detects_an_edited_artifact(
        vrfy, tmp_path, monkeypatch):
    """A single flipped field must FAIL - the check is not a smoke test."""
    def mutate(data):
        data["claims"]["supported"][0] = "tampered for the negative control"
    eval_dir = _stored_copy(tmp_path, "exp007_analysis.json", mutate)
    monkeypatch.setattr(vrfy, "EVAL", eval_dir)
    vrfy.check_analyzer_bytes("t", "analyze_exp007.py", "exp007_analysis.json",
                              "t_exp007_bad", tmp_path / "out", False)
    assert _outcomes(vrfy)[0] == ("L2 t", "FAIL")


# --- L2: EXP-007's recorded checkout path (DEC-045) --------------------------

EXP007_ARTIFACT = PROJECT / "results" / "evaluation" / "exp007_analysis.json"
ELSEWHERE = "X:\\elsewhere\\PDS PROJECT\\results\\training"


def test_refingerprint_reproduces_the_committed_fingerprint(vrfy):
    """The verifier's copy of the fingerprint recipe must match the analyzer's.

    If it drifted, the mapped comparison would silently compare against a
    different formula; this pins it to the value the analyzer actually wrote.
    """
    art = json.loads(EXP007_ARTIFACT.read_text(encoding="utf-8"))
    assert vrfy.refingerprint(art) == art["analysis_fingerprint"]


def _exp007_bytes(mod, vrfy, root: str, mutate=None) -> bytes:
    """The committed exp-007 report as the analyzer would write it at `root`."""
    art = json.loads(EXP007_ARTIFACT.read_text(encoding="utf-8"))
    art["inputs"]["training_root"] = root
    if mutate is not None:
        mutate(art)
    art["analysis_fingerprint"] = vrfy.refingerprint(art)
    return mod.report_json(art).encode("utf-8")


def _relocated_copy(vrfy, tmp_path: Path, mutate=None) -> Path:
    """A stored exp-007 artifact as if recorded in a different checkout."""
    mod = vrfy.load_module("t_exp007_ser", "analyze_exp007.py")
    eval_dir = tmp_path / "eval"
    eval_dir.mkdir(exist_ok=True)
    (eval_dir / "exp007_analysis.json").write_bytes(
        _exp007_bytes(mod, vrfy, ELSEWHERE, mutate))
    return eval_dir


def test_exp007_recorded_in_another_checkout_passes_once_mapped(
        vrfy, tmp_path, monkeypatch):
    monkeypatch.setattr(vrfy, "EVAL", _relocated_copy(vrfy, tmp_path))
    vrfy.check_analyzer_bytes("t", "analyze_exp007.py", "exp007_analysis.json",
                              "t_exp007_moved", tmp_path / "out", False)
    (name, status, detail), = _verdicts(vrfy)
    assert status == "PASS", detail
    assert "mapped to the recorded checkout" in detail


def test_exp007_mapping_does_not_hide_a_changed_result(vrfy, tmp_path,
                                                      monkeypatch):
    """A relocated artifact with an edited result - and a fingerprint
    recomputed to match it - must still FAIL: only the path is ever mapped."""
    def mutate(data):
        data["validation"]["total_live_executions"] += 1
    monkeypatch.setattr(vrfy, "EVAL", _relocated_copy(vrfy, tmp_path, mutate))
    vrfy.check_analyzer_bytes("t", "analyze_exp007.py", "exp007_analysis.json",
                              "t_exp007_forged", tmp_path / "out", False)
    assert _outcomes(vrfy)[0] == ("L2 t", "FAIL")


def test_map_checkout_path_refuses_every_other_difference(vrfy):
    mod = vrfy.load_module("t_exp007_map", "analyze_exp007.py")
    here = str((mod.PROJECT / "results" / "training").resolve())
    local, moved = (_exp007_bytes(mod, vrfy, here),
                    _exp007_bytes(mod, vrfy, ELSEWHERE))
    name = "exp007_analysis.json"
    # an artifact with no recorded checkout path is never mapped
    assert vrfy.map_checkout_path(mod, "exp006_analysis.json", local, moved) is None
    # the fresh value must be this checkout's own directory
    assert vrfy.map_checkout_path(
        mod, name, _exp007_bytes(mod, vrfy, "Y:\\other"), moved) is None
    # a stored value that already is this checkout leaves nothing to map
    assert vrfy.map_checkout_path(mod, name, local, local) is None
    # unreadable input is refused, not guessed at
    assert vrfy.map_checkout_path(mod, name, b"not json", moved) is None
    # the legitimate case lands exactly on the stored bytes
    assert vrfy.map_checkout_path(mod, name, local, moved) == moved


def test_exp002_gate_is_compared_without_its_volatile_fields(vrfy, tmp_path):
    vrfy.check_exp002_gate(tmp_path, False)
    (name, status, detail), = _verdicts(vrfy)
    assert status == "PASS", detail
    assert "generated_utc+code_version" in detail
    assert "verdict=PASS" in detail


def test_figures_re_render_byte_identically_and_leave_the_originals_alone(vrfy):
    fig_dir = PROJECT / "docs" / "figures"
    names = ("exp002_configuration_sensitivity.svg",
             "exp005_arm_comparison.svg", "exp007_ablation.svg")
    before = {n: vrfy.sha256_file(fig_dir / n) for n in names}
    import tempfile
    with tempfile.TemporaryDirectory(prefix="t_repro_fig_") as tmp:
        vrfy.check_figures(Path(tmp), False)
    assert [s for _, s, _ in vrfy.results] == ["PASS"] * 3
    assert {n: vrfy.sha256_file(fig_dir / n) for n in names} == before


def test_main_reports_pass_and_does_not_evaluate_sc7(vrfy, capsys, monkeypatch):
    """End-to-end, but with the 45 s EXP-009 re-run replaced by a stub.

    The full pipeline is run as a recorded command, not from the unit suite;
    what is pinned here is that `main` aggregates the checks and that its
    output never claims an SC7 verdict, which needs live executions.
    """
    monkeypatch.setattr(vrfy, "check_exp009_ext",
                        lambda out_dir, show: vrfy.check("L2 stub", True, "ok"))
    rc = vrfy.main([])
    text = capsys.readouterr().out
    assert rc == 0
    assert "NOT an SC7 verdict" in text
    assert "0 Spark executions, 0 charged to SC6" in text
    assert "OVERALL: PASS" in text
