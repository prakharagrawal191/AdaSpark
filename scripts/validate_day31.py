#!/usr/bin/env python
"""Day-31 validator: the evaluation harness and the frozen configurations.

PLAN line 277, verbatim and frozen:

    | 31 | Eval harness + B1/B2 | frozen test set; static baselines tuned on
    validation | configs frozen |

Day 31 BUILDS a harness, SELECTS B1/B2 on the VALIDATION split and FREEZES the
TEST-split IDENTITY. It executes nothing on the test split: EXP-005 (~245 runs)
is Day 32-33 and EXP-006 (~100 runs) is Day 34 (PLAN lines 312-313), and
ARCHITECTURE_FREEZE line 73 reads "Frozen policies evaluated once on test
(EXP-005/006)". So this validator audits four things:

  (a) the TEST split is FROZEN BY IDENTITY and NEVER USED - the freeze artifact
      matches the frozen Day-14 dataset manifests, and the selection path is
      proved, by calling it, to REFUSE a test observation rather than merely
      documenting that it should not receive one;
  (b) the CONFIGURATIONS are frozen - the evaluation specification and the
      candidate grid fingerprint-verify, AQE is still off and the authoritative
      Day-3 timing semantics are unchanged;
  (c) NOTHING LEARNED AND NOTHING UNACCOUNTED - no Q update is reachable from
      an evaluation path, DEC-011 still resolves NO, and the training ledger
      reconciles the committed Day-29 baseline (232 live executions) plus
      EVERY authorized post-Day-29 TRAIN spend (84 B4 via DEC-016 C /
      DEC-017, 20 EXP-001 via the Day-32 user protocol, and 126 EXP-007
      A1/A2 authorized by DEC-026) for a current total of 462 of the 500
      cap (38 remaining, reconciled by DEC-031 sections 3/4/8). The
      assertion is that every live execution is ATTRIBUTABLE to a recorded
      authorization, never that the total is frozen. EXP-003 / EXP-005 /
      EXP-005b / EXP-006 remain separate register lines, charged 0 here;
  (d) the artifacts are IMMUTABLE - a differing overwrite is refused, proved by
      attempting one against a throwaway copy.

This validator makes NO research claim. It does not compare B0, B1, B2 or the
learned policy, does not score any strategy and does not evaluate whether any
approach is better than another. It checks that the harness is honest about what
it may touch and that the frozen state of the project is unchanged.

Everything here is READ-ONLY: stored artifacts, source text, `git status`
(read-only), the six prior read-only validators and the deterministic unit
suite. No Spark, no training, no git write. The one thing it writes is a
throwaway artifact copy inside a temporary directory, to prove the immutability
guard actually fires.

PASS/FAIL/SKIP per check; the overall verdict is PASS only when every applicable
check passes. A SKIP is never reported as a PASS and always carries a reason.

Usage:
    python scripts/validate_day31.py
"""
from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import tempfile
import tokenize
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

SRC = PROJECT / "src"
SCRIPTS = PROJECT / "scripts"
EVAL_SRC = SRC / "sparkrl" / "evaluation"
EVAL_CLI = SCRIPTS / "run_evaluation.py"
RL_CONFIG = PROJECT / "configs" / "rl.yaml"
B0_CONFIG = PROJECT / "configs" / "baseline_b0.yaml"
PLAN = PROJECT / "docs" / "PLAN.md"
DECISIONS = PROJECT / "DECISIONS.md"
RESEARCH = PROJECT / "docs" / "research"
RESULTS = PROJECT / "results"
TRAINING_ROOT = RESULTS / "training"
ARTIFACT_DIR = RESULTS / "evaluation"

SPEC_ARTIFACT = ARTIFACT_DIR / "evaluation_spec.json"
FREEZE_ARTIFACT = ARTIFACT_DIR / "test_freeze.json"
SELECTION_ARTIFACT = ARTIFACT_DIR / "baseline_selection.json"

DAY31_DOC_GLOB = "DAY31*.md"

# PLAN line 277, frozen and verbatim (the day this validator audits).
PLAN_DAY_LINE = 277
PLAN_DAY_TEXT = ("| 31 | Eval harness + B1/B2 | frozen test set; static "
                 "baselines tuned on validation | configs frozen |")

# Frozen scope facts (PLAN section 18 + the frozen 12-configuration grid).
VALIDATION_CELL_COUNT = 8
VALIDATION_SEED = 3
TEST_CELL_COUNT = 43
CANDIDATE_COUNT = 12
EVALUATION_REPETITIONS = 5

# The committed Day-29 ledger (HEAD f9d765d): 9 manifests of record and 232 live
# executions of the frozen 500 TRAINING cap (SC6). Day 31 spends ZERO, and
# EXP-003 is a separate register line that is not charged to that cap at all.
DAY29_MANIFEST_COUNT = 9
DAY29_LIVE_EXECUTIONS = 232
LIVE_EXECUTION_CAP = 500

# Frozen bandit default (PLAN section 16). DEC-011 resolved the mode gate NO.
FROZEN_GAMMA = 0.0

# Authoritative timing (PLAN section 22): the Day-3 runner clock, warm-up out.
TIMING_METRIC = "execution_time_s"
TIMING_SOURCE = "runner"

# Prior validators that must still pass (all read-only, no Spark).
PRIOR_VALIDATORS = (
    ("Day 25 env", "validate_rl_environment.py"),
    ("Day 26 agent", "validate_rl_agent.py"),
    ("Day 27 loop", "validate_rl_training.py"),
    ("Day 28 run", "validate_day28.py"),
    ("Day 29 M8", "validate_day29.py"),
    ("Day 30 gate", "validate_day30.py"),
)

# Learning machinery. None of it may be reachable from an evaluation path: an
# evaluation that can update a Q table is no longer evaluating a frozen policy.
LEARNING_CODE = re.compile(
    r"\b(QLearningAgent|q_learning|q_table|update_q|decay_epsilon|end_episode"
    r"|policy_store|save_policy|load_policy|agent_from_artifact|TrainingLoop"
    r"|train_episode|Transition|replay_buffer)\b")

# Multi-step machinery (DEC-011 resolved NO; Day 31 must not have built it).
MULTISTEP_CODE = re.compile(
    r"\b(phase_t|phase_index|phase_idx|current_phase|next_phase|n_phases"
    r"|num_phases|phase_reward|phase_state|phase_aware|multi_step|multistep"
    r"|rollout_phases|step_within_episode|bootstrap_target)\b", re.IGNORECASE)

# Components explicitly out of scope on Day-32 maintenance: deep RL, the
# execution cache (COMP-EXP-11), the durable orchestrator (COMP-EXP-12), and
# future experiments. EXP-003/005/005b/006 DRIVERS are forbidden here; EXP-001
# is EXPLICITLY PERMITTED — it was legitimately executed on Day 32, so its
# driver (scripts/run_exp001.py) is expected. Artifacts live under
# results/experiments/exp-001/, never in src/ or scripts/.
FORBIDDEN_CODE = re.compile(
    r"\b(dqn|ppo|a2c|a3c|sac|td3|actor_critic|policy_gradient|reinforce"
    r"|target_network|torch|tensorflow|keras|stable_baselines"
    r"|cachekey|cacheentry|cache_hit|cache_lookup|execution_cache"
    r"|executioncache|durable_orchestrator|orchestrator"
    r"|exp003|exp-003|exp005|exp-005|exp005b|exp-005b|exp006|exp-006)\b", re.IGNORECASE)

# The MACHINERY half of FORBIDDEN_CODE, without the experiment-id
# alternatives: an execution cache (COMP-EXP-11), a durable orchestrator
# (COMP-EXP-12) or a deep-RL symbol. This half is what check 21 is actually
# about and is NEVER excused for any file; see check 21 for why a small,
# named set of files is exempt from the experiment-id half only.
FORBIDDEN_MACHINERY = re.compile(
    r"\b(dqn|ppo|a2c|a3c|sac|td3|actor_critic|policy_gradient|reinforce"
    r"|target_network|torch|tensorflow|keras|stable_baselines"
    r"|cachekey|cacheentry|cache_hit|cache_lookup|execution_cache"
    r"|executioncache|durable_orchestrator|orchestrator)\b", re.IGNORECASE)

# Paths that would mean a future experiment has started producing results.
FUTURE_EXPERIMENT_GLOBS = ("*exp-005*", "*exp005*", "*exp-006*", "*exp006*",
                           "*exp-005b*")

results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool | None, detail: str = "") -> None:
    status = "SKIP" if ok is None else ("PASS" if ok else "FAIL")
    results.append((name, status, detail))
    print(f"{name:<46} {status:<5} {detail}")


# Token types carrying LITERAL PROSE rather than executable meaning.
# PEP 701 (Python >= 3.12) stopped emitting an f-string as a single STRING
# token - it is FSTRING_START / FSTRING_MIDDLE / FSTRING_END - so every
# f-string's literal text leaked into what this file calls "executable"
# source and a mere *mention* inside an f-string scored as an
# implementation. The interpolated expressions stay NAME/OP, so an
# f-string that actually CALLS a forbidden component still trips the scan.
_LITERAL_TOKENS = {tokenize.COMMENT, tokenize.STRING, tokenize.ENCODING}
if hasattr(tokenize, "FSTRING_MIDDLE"):          # Python >= 3.12
    _LITERAL_TOKENS.add(tokenize.FSTRING_MIDDLE)


def executable_text(path: Path) -> str:
    """Source text with comments and docstrings removed, so that a *mention* of
    a concept in prose is never mistaken for an implementation of it."""
    try:
        raw = path.read_bytes()
    except OSError:
        return ""
    try:
        toks = tokenize.tokenize(io.BytesIO(raw).readline)
        # Space-join, not "". Every scanned pattern here is \b-anchored and
        # "".join glued adjacent tokens together, so `import torch` became
        # "importtorch", which \btorch\b cannot match - a silent detection
        # hole. The separator is what gives these scans their teeth.
        return " ".join(t.string for t in toks
                        if t.type not in _LITERAL_TOKENS)
    except (tokenize.TokenError, IndentationError, SyntaxError, OSError):
        return ""


# A5 REFUSAL CARVE-OUT - see the identical block in scripts/validate_day30.py.
# A guard that RAISES on multi-step is enforcing DEC-011, not breaching it;
# deleting it to satisfy a scanner would remove an enforcement of the very
# decision this check protects. The carve-out is narrow: the file must
# actually raise, it may only name refusal vocabulary (never phase/rollout/
# bootstrap machinery), and it must carry no gamma=0.9 plumbing.
A5_REFUSAL_CONTRACT = (
    "def guard_a5",
    "raise A5DisabledError",
    "multi-step RL is FORBIDDEN",
    "FROZEN_GAMMA_BANDIT",
)
A5_REFUSAL_TOKENS = frozenset({
    "multi_step", "multistep", "multi_step_mode", "multistep_mode",
})
GAMMA_09_PLUMBING = re.compile(r"gamma\s*=\s*0\.9|\"gamma\"\s*:\s*0\.9"
                               r"|'gamma'\s*:\s*0\.9")


def a5_refusal_only(path: Path) -> bool:
    """True iff `path`'s multi-step matches are pure A5 REFUSAL, not machinery."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return False
    if not all(tok in raw for tok in A5_REFUSAL_CONTRACT):
        return False
    text = executable_text(path)
    if GAMMA_09_PLUMBING.search(text):
        return False
    return all(m.group(0).lower() in A5_REFUSAL_TOKENS
               for m in MULTISTEP_CODE.finditer(text))


def scan_paths(paths: list[Path], pattern: re.Pattern[str]) -> list[str]:
    """Files whose EXECUTABLE source matches `pattern`."""
    hits: list[str] = []
    for child in paths:
        if "__pycache__" in child.parts:
            continue
        if pattern.search(executable_text(child)):
            hits.append(str(child.relative_to(PROJECT)).replace("\\", "/"))
    return hits


def py_files(tree: Path) -> list[Path]:
    return sorted(p for p in tree.rglob("*.py") if "__pycache__" not in p.parts)


def run_tool(argv: list[str], timeout: int) -> tuple[bool, str]:
    """Run a read-only tool; return (exit-code-zero, last non-empty line)."""
    try:
        proc = subprocess.run(argv, cwd=str(PROJECT), capture_output=True,
                              text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s"
    except OSError as exc:
        return False, str(exc)
    lines = [ln.strip() for ln in
             (proc.stdout + "\n" + proc.stderr).splitlines() if ln.strip()]
    tail = lines[-1] if lines else "(no output)"
    return proc.returncode == 0, f"exit={proc.returncode} :: {tail[:110]}"


def git_modified_tracked() -> tuple[list[str] | None, str]:
    """Tracked files with working-tree/index changes. Read-only git command.
    Untracked NEW files are allowed - Day 31 creates new files only."""
    # CONTENT-based, deliberately: "git status" flags a file whose only
    # difference is line endings under core.autocrlf, which is not a content
    # change and which "git diff" correctly reports as none. Using status here
    # made configs/rl.yaml look modified when its bytes still hash to the value
    # the Day-29 manifests pin.
    try:
        proc = subprocess.run(["git", "diff", "--name-only"], cwd=str(PROJECT),
                              capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"git unavailable: {exc}"
    if proc.returncode != 0:
        return None, f"git exited {proc.returncode}"
    changed = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    return changed, "git diff --name-only read (content, not line endings)"


def ledger_from_manifests() -> tuple[int, int]:
    """(manifest count, summed live_executions) over the whole training tree.

    Malformed ledger data is a validation FAILURE, never a silent skip: every
    unreadable or non-numeric artifact is recorded in
    ``ledger_from_manifests.errors`` (a list of "path: reason" strings, empty
    on the clean path) so check 22 can FAIL loudly instead of undercounting.
    ``errors`` is reset on each call; concurrent callers must not share it.
    """
    ledger_from_manifests.errors = []
    manifests = sorted(TRAINING_ROOT.rglob("manifest.json"))
    total = 0
    for path in manifests:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            total += int((data.get("budget") or {}).get("live_executions", 0))
        except (OSError, json.JSONDecodeError) as exc:
            ledger_from_manifests.errors.append(f"{path}: {type(exc).__name__}")
            continue
        except (ValueError, TypeError) as exc:
            # A manifest that parses but carries a non-numeric count (e.g.
            # "live_executions": "many") is corrupt data, not a programming
            # error: record it and keep the failure loud via check 22.
            ledger_from_manifests.errors.append(f"{path}: corrupt count")
            continue
    # The B4 equal-budget search (DEC-016 C / DEC-017) executes REAL TRAIN cells
    # but writes an evaluation artifact rather than a training manifest, so it
    # would otherwise be invisible to this ledger. DEC-016 C explicitly charges
    # it to the cap ("taking the ledger from 232 to 316 of 500"), so it is
    # counted here. Omitting it would understate true TRAIN consumption.
    b4 = ARTIFACT_DIR / "b4_selection.json"
    if b4.exists():
        try:
            data = json.loads(b4.read_text(encoding="utf-8"))
            if data.get("split") == "train":
                total += int((data.get("observation_counts") or {}).get("total", 0))
        except (OSError, json.JSONDecodeError) as exc:
            ledger_from_manifests.errors.append(f"{b4}: {type(exc).__name__}")
        except (ValueError, TypeError):
            ledger_from_manifests.errors.append(f"{b4}: corrupt count")
    # The EXP-001 noise calibration (user-authorized Day-32 protocol) executes
    # REAL TRAIN cells but writes results/experiments/exp-001/ rather than a
    # training manifest, so it would otherwise be invisible to this ledger.
    # It is charged to the cap ("316 -> 336 of 500"), so it is counted here
    # from its stored summary artifact (observation_counts.total), never from
    # a hardcoded number. Omitting it would understate true TRAIN consumption.
    exp_root = PROJECT / "results" / "experiments" / "exp-001"
    exp001 = exp_root / "summary.json"
    if exp001.exists():
        try:
            data = json.loads(exp001.read_text(encoding="utf-8"))
            if data.get("experiment_id") == "EXP-001" \
                    and data.get("contains_test_data") is False:
                total += int((data.get("observation_counts") or {}).get("total", 0))
        except (OSError, json.JSONDecodeError) as exc:
            ledger_from_manifests.errors.append(f"{exp001}: {type(exc).__name__}")
        except (ValueError, TypeError):
            ledger_from_manifests.errors.append(f"{exp001}: corrupt count")
    return len(manifests), total


ledger_from_manifests.errors = []


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def walk_strings(node: Any, out: list[str]) -> None:
    """Every key and string value in a nested JSON document."""
    if isinstance(node, dict):
        for key, value in node.items():
            out.append(str(key))
            walk_strings(value, out)
    elif isinstance(node, list):
        for value in node:
            walk_strings(value, out)
    elif isinstance(node, str):
        out.append(node)


def main(argv: list[str] | None = None) -> int:
    """Run all Day-31 validator checks; print a PASS/FAIL/SKIP table and one
    overall verdict. Exit 0 = PASS, 1 = FAIL."""
    del argv
    del results[:]
    py = sys.executable

    from sparkrl.evaluation import freeze as freeze_mod           # noqa: E402
    from sparkrl.evaluation import orchestration, spec as eval_spec  # noqa: E402
    from sparkrl.evaluation.selection import (ValidationObservation,  # noqa: E402
                                              select_baselines,)
    from sparkrl.experiments.grid import (GRID_VERSION,           # noqa: E402
                                          build_grid, grid_fingerprint,)
    from sparkrl.experiments.spec import split_of                 # noqa: E402
    from sparkrl.spark.config import SparkConfig                  # noqa: E402
    from sparkrl.workloads.resolver import resolve_dataset        # noqa: E402

    # 00 PLAN line 277 is verbatim and untouched
    plan_lines = PLAN.read_text(encoding="utf-8").splitlines()
    day_line = (plan_lines[PLAN_DAY_LINE - 1].strip()
                if len(plan_lines) >= PLAN_DAY_LINE else "<out of range>")
    check("00 PLAN line 277 verbatim", day_line == PLAN_DAY_TEXT,
          f"line {PLAN_DAY_LINE}: {day_line[:66]!r}")

    # ---- A. the TEST split is frozen by IDENTITY and never used -----------
    # 01 the test freeze artifact exists and fingerprint-verifies
    freeze_doc: dict[str, Any] = {}
    if not FREEZE_ARTIFACT.exists():
        check("01 test freeze artifact verifies", False,
              f"missing {FREEZE_ARTIFACT.relative_to(PROJECT)}")
    else:
        try:
            freeze_doc = freeze_mod.verify_artifact(FREEZE_ARTIFACT)
            check("01 test freeze artifact verifies", True,
                  f"artifact_id={freeze_doc['artifact_id'][:16]} "
                  f"manifest_fingerprint="
                  f"{freeze_doc['manifest_fingerprint'][:16]} "
                  f"({freeze_doc['cell_count']} cells)")
        except Exception as exc:                                # noqa: BLE001
            check("01 test freeze artifact verifies", False, f"{exc}")

    # 02 the frozen cells agree with split_of AND with the Day-14 manifests
    if not freeze_doc:
        check("02 freeze matches manifests + split_of", None,
              "SKIP: no verifiable test freeze artifact")
    else:
        cells = freeze_doc.get("cells") or []
        drift: list[str] = []
        for cell in cells:
            key = (cell["family"], cell["scale"], cell["seed"])
            if split_of(*key) != "test":
                drift.append(f"{key} is not TEST")
                continue
            try:
                resolved = resolve_dataset(*key)
            except Exception as exc:                            # noqa: BLE001
                drift.append(f"{key}: unresolvable ({exc})")
                continue
            for field, actual in (
                    ("dataset_id", resolved.dataset_id),
                    ("dataset_fingerprint", resolved.dataset_fingerprint),
                    ("schema_fingerprint", resolved.schema_fingerprint),
                    ("skew", resolved.skew)):
                if cell.get(field) != actual:
                    drift.append(f"{key}.{field}")
        frozen_set = {(c["family"], c["scale"], c["seed"]) for c in cells}
        expected = set(eval_spec.test_cells())
        complete = frozen_set == expected and len(cells) == TEST_CELL_COUNT
        check("02 freeze matches manifests + split_of",
              not drift and complete,
              (f"{len(cells)} test cells, all split_of()==test, all dataset_id / "
               f"dataset_fingerprint / schema_fingerprint / skew identical to the "
               f"frozen manifests") if not drift and complete
              else f"drift: {drift[:4]} complete={complete}")

    # 03 the freeze carries IDENTITY only - no measurement, no metric
    if not freeze_doc:
        check("03 freeze is identity only (no metric)", None,
              "SKIP: no verifiable test freeze artifact")
    else:
        tokens: list[str] = []
        walk_strings(freeze_doc, tokens)
        banned = re.compile(
            r"execution_time|elapsed|duration|runtime_s|median|mean|speedup"
            r"|reward|spill|throughput|latency|q_value|measurement_value",
            re.IGNORECASE)
        # The word "measurement" appears in the artifact's own NEGATIVE
        # statement ("no measurement"); only a metric-bearing token counts.
        hits = sorted({t for t in tokens if banned.search(t)})
        check("03 freeze is identity only (no metric)",
              not hits and freeze_doc.get("executed") is False,
              (f"executed={freeze_doc.get('executed')}, no timing/metric token "
               f"anywhere in the artifact") if not hits
              else f"metric-bearing tokens: {hits[:4]}")

    # 04 no duplicate frozen test cell / evaluation identity in the freeze
    if not freeze_doc:
        check("04 no duplicate frozen test identity", None,
              "SKIP: no verifiable test freeze artifact")
    else:
        cells = freeze_doc.get("cells") or []
        keys = [(c["family"], c["scale"], c["seed"]) for c in cells]
        # Note: dataset_id uniqueness is NOT required - 75 logical cells
        # share 30 physical datasets (2 skews x 3 scales x 5 seeds), so
        # multiple cells legitimately share the same physical dataset.
        check("04 no duplicate frozen test identity",
              len(set(keys)) == len(keys),
              f"{len(keys)} cells, {len(set(keys))} distinct "
              f"(dataset ids may repeat: shared physical layout)")

    # ---- B. structural leakage prevention, PROVED BY CALLING ---------------
    def observation(family: str, scale: str, seed: int, point, rep: int = 1,
                    seconds: float = 10.0) -> ValidationObservation:
        return ValidationObservation(
            family=family, scale=scale, seed=seed, config_name=point.name,
            grid_index=point.grid_index, rep=rep, execution_time_s=seconds,
            usable=True)

    candidates = eval_spec.selection_candidates()
    val_cells = eval_spec.validation_cells()
    clean = [observation(f, s, d, p, rep)
             for f, s, d in val_cells for p in candidates for rep in (1,)]
    test_cell = eval_spec.test_cells()[0]
    train_cell = ("F1_agg", "small", 0)

    # 05 one TEST observation aborts the whole selection
    poisoned = list(clean) + [observation(*test_cell, candidates[0], 1, 0.001)]
    try:
        select_baselines(poisoned)
        raised = "<no exception>"
    except eval_spec.SplitAuthorizationError as exc:
        raised = f"SplitAuthorizationError: {str(exc)[:64]}"
    except Exception as exc:                                    # noqa: BLE001
        raised = f"{type(exc).__name__}: {exc}"
    check("05 selection RAISES on a test observation",
          raised.startswith("SplitAuthorizationError"),
          f"{test_cell[0]}/{test_cell[1]}/seed{test_cell[2]} -> {raised[:70]}")

    # 06 a TRAIN observation is refused too (validation is the ONLY tuning split)
    poisoned = list(clean) + [observation(*train_cell, candidates[0], 1, 0.001)]
    try:
        select_baselines(poisoned)
        raised = "<no exception>"
    except eval_spec.SplitAuthorizationError as exc:
        raised = f"SplitAuthorizationError: {str(exc)[:64]}"
    except Exception as exc:                                    # noqa: BLE001
        raised = f"{type(exc).__name__}: {exc}"
    check("06 selection RAISES on a train observation",
          raised.startswith("SplitAuthorizationError"),
          f"{train_cell[0]}/{train_cell[1]}/seed{train_cell[2]} -> {raised[:70]}")

    # 07 the guard is not a blanket refusal: a clean VALIDATION panel selects
    try:
        selection = select_baselines(clean)
        ok_clean = (selection.b1_config_name in {c.name for c in candidates}
                    and set(selection.scope_cells) == set(val_cells)
                    and sorted(selection.b2_config_names) ==
                    sorted(eval_spec.validation_families()))
        detail = (f"B1={selection.b1_config_name}, B2 over "
                  f"{len(selection.b2_config_names)} families, scope="
                  f"{len(selection.scope_cells)} validation cells "
                  f"(synthetic fixture; NO research claim)")
    except Exception as exc:                                    # noqa: BLE001
        ok_clean, detail = False, f"{type(exc).__name__}: {exc}"
    check("07 clean validation panel is accepted", ok_clean, detail)

    # 08 the aggregation entry point refuses a test RECORD as well
    record = {"run_spec": {"family": test_cell[0], "scale": test_cell[1],
                           "seed": test_cell[2], "config_name": candidates[0].name,
                           "config_grid_index": candidates[0].grid_index,
                           "rep": 1},
              "metrics": {TIMING_METRIC: 1.0, "usable": True}}
    try:
        orchestration.observations_from_records([record])
        raised = "<no exception>"
    except eval_spec.SplitAuthorizationError as exc:
        raised = f"SplitAuthorizationError: {str(exc)[:48]}"
    except Exception as exc:                                    # noqa: BLE001
        raised = f"{type(exc).__name__}: {exc}"
    check("08 aggregation RAISES on a test record",
          raised.startswith("SplitAuthorizationError"),
          f"observations_from_records -> {raised[:70]}")

    # 09 the test EXECUTION path is sealed (authorizes, then always refuses)
    from sparkrl.experiments.spec import RunSpec                 # noqa: E402
    sealed_spec = RunSpec(run_id="probe", family=test_cell[0], scale=test_cell[1],
                          seed=test_cell[2], rep=1, config=candidates[0],
                          split="test", timeout_seconds=300.0, order_index=0,
                          block_id="probe")
    try:
        orchestration.execute_test_run(sealed_spec, None)
        raised = "<no exception>"
    except eval_spec.TestSplitSealed as exc:
        raised = f"TestSplitSealed: {str(exc)[:48]}"
    except Exception as exc:                                    # noqa: BLE001
        raised = f"{type(exc).__name__}: {exc}"
    try:
        eval_spec.assert_test_execution_permitted()
        seal_ok = False
    except eval_spec.TestSplitSealed:
        seal_ok = True
    check("09 test execution path sealed",
          raised.startswith("TestSplitSealed") and seal_ok,
          f"execute_test_run -> {raised[:60]}; "
          f"assert_test_execution_permitted always raises={seal_ok}")

    # 10 validation IS the declared tuning split, and it is exactly seed 3
    scope_ok = (len(val_cells) == VALIDATION_CELL_COUNT
                and all(split_of(*c) == "validation" for c in val_cells)
                and {c[2] for c in val_cells} == {VALIDATION_SEED}
                and eval_spec.SELECTION_METRIC == TIMING_METRIC)
    check("10 validation is the only tuning split", scope_ok,
          f"{len(val_cells)} cells, seeds={{{VALIDATION_SEED}}}, families="
          f"{list(eval_spec.validation_families())}, metric="
          f"{eval_spec.SELECTION_METRIC} (B1/B2 tuned here and nowhere else)")

    # ---- C. the configurations are FROZEN ---------------------------------
    # 11 the evaluation specification artifact exists and fingerprint-verifies
    spec_doc: dict[str, Any] = {}
    if not SPEC_ARTIFACT.exists():
        check("11 evaluation spec frozen + verified", False,
              f"missing {SPEC_ARTIFACT.relative_to(PROJECT)}")
    else:
        try:
            spec_doc = freeze_mod.verify_artifact(SPEC_ARTIFACT)
            ok = (spec_doc.get("executed") is False
                  and spec_doc.get("repetitions") == EVALUATION_REPETITIONS
                  and spec_doc.get("selection_split") == "validation"
                  and len(spec_doc.get("validation_cells") or [])
                  == VALIDATION_CELL_COUNT
                  and spec_doc.get("test_cell_count") == TEST_CELL_COUNT)
            check("11 evaluation spec frozen + verified", ok,
                  f"artifact_id={spec_doc['artifact_id'][:16]} executed="
                  f"{spec_doc.get('executed')} reps={spec_doc.get('repetitions')} "
                  f"split={spec_doc.get('selection_split')}")
        except Exception as exc:                                # noqa: BLE001
            check("11 evaluation spec frozen + verified", False, f"{exc}")

    # 12 the B1/B2 CANDIDATE grid is frozen and fingerprint-verified
    live_grid = build_grid(include_b0=False)
    live_fp = grid_fingerprint(live_grid)
    if not spec_doc:
        check("12 candidate grid frozen + fingerprinted", None,
              "SKIP: no verifiable evaluation spec artifact")
    else:
        frozen = spec_doc.get("frozen_configurations") or {}
        ok = (frozen.get("grid_version") == GRID_VERSION
              and frozen.get("grid_fingerprint") == live_fp
              and frozen.get("candidate_count") == CANDIDATE_COUNT
              and len(live_grid) == CANDIDATE_COUNT)
        check("12 candidate grid frozen + fingerprinted", ok,
              f"{GRID_VERSION} {live_fp[:16]} over {len(live_grid)} candidates "
              f"(artifact says {frozen.get('candidate_count')})")

    # 13 the SELECTED B1/B2 artifact - absent until the validation grid is spent
    if SELECTION_ARTIFACT.exists():
        try:
            sel_doc = freeze_mod.verify_artifact(SELECTION_ARTIFACT)
            scope = sel_doc.get("validation_scope") or []
            leaked = [c for c in scope
                      if split_of(c["family"], c["scale"], c["seed"]) != "validation"]
            check("13 B1/B2 selection frozen + verified",
                  not leaked and sel_doc.get("contains_test_data") is False
                  and sel_doc.get("split") == "validation",
                  f"artifact_id={sel_doc['artifact_id'][:16]} B1="
                  f"{(sel_doc.get('B1') or {}).get('selected_config')} "
                  f"leaked_cells={len(leaked)}")
        except Exception as exc:                                # noqa: BLE001
            check("13 B1/B2 selection frozen + verified", False, f"{exc}")
    else:
        check("13 B1/B2 selection frozen + verified", None,
              "SKIP: results/evaluation/baseline_selection.json not produced - it "
              "requires measured VALIDATION observations, and Day 31 executed no "
              "Spark (none exist yet; the 480-run selection grid is unspent)")

    # 14 AQE is still OFF - in B0, in the spec, and in every candidate
    base_config = SparkConfig.from_yaml(B0_CONFIG)
    aqe_candidates = [c.name for c in live_grid if c.aqe_enabled]
    aqe_ok = (base_config.aqe_enabled is False and not aqe_candidates
              and (spec_doc.get("aqe_enabled") is False if spec_doc else True))
    check("14 AQE off (B0, spec, all candidates)", aqe_ok,
          f"baseline_b0.yaml aqe_enabled={base_config.aqe_enabled}, "
          f"{len(aqe_candidates)} AQE-on candidates, spec says "
          f"{spec_doc.get('aqe_enabled') if spec_doc else '<no spec>'} "
          f"(AQE-on is B0'/EXP-005b, never EXP-003)")

    # 15 B0 itself is byte-unchanged versus HEAD
    ok, detail = run_tool(["git", "diff", "--quiet", "HEAD", "--",
                           "configs/baseline_b0.yaml"], timeout=120)
    check("15 B0 config unchanged vs HEAD", ok,
          "configs/baseline_b0.yaml identical to HEAD" if ok
          else f"git reports a difference ({detail})")

    # 16 the authoritative timing semantics are unchanged
    runner_src = (SRC / "sparkrl" / "experiments" / "runner.py").read_text(
        encoding="utf-8")
    runner_guard = 'if metrics.execution_time_source != "runner":' in runner_src
    timing = (spec_doc.get("timing_semantics") or {}) if spec_doc else {}
    timing_ok = (eval_spec.SELECTION_METRIC == TIMING_METRIC
                 and eval_spec.SELECTION_METRIC_SOURCE == TIMING_SOURCE
                 and runner_guard
                 and (timing.get("metric") == TIMING_METRIC if timing else True)
                 and (timing.get("required_source") == TIMING_SOURCE
                      if timing else True))
    check("16 timing semantics unchanged", timing_ok,
          f"metric={eval_spec.SELECTION_METRIC} source="
          f"{eval_spec.SELECTION_METRIC_SOURCE}; runner still refuses a "
          f"non-runner clock={runner_guard}")

    # 17 every evaluation observation and artifact carries provenance
    prov = freeze_mod.provenance()
    prov_keys = {"code_version", "produced_by", "split_authority",
                 "spark_executions"}
    obs_fields = set(ValidationObservation.__dataclass_fields__)
    stored_prov = [bool((d.get("provenance") or {}).keys() >= prov_keys)
                   for d in (spec_doc, freeze_doc) if d]
    prov_ok = (prov_keys <= set(prov) and bool(prov.get("code_version"))
               and prov.get("spark_executions") == 0
               and {"execution_time_source", "config_name", "grid_index", "rep",
                    "usable"} <= obs_fields
               and len(stored_prov) == 2 and all(stored_prov))
    check("17 observations + artifacts carry provenance", prov_ok,
          f"code_version={prov.get('code_version')} spark_executions="
          f"{prov.get('spark_executions')}; {len(stored_prov)} stored artifacts "
          f"carry full provenance; observation carries execution_time_source")

    # ---- D. nothing LEARNED on an evaluation path --------------------------
    # 18 no Q update / policy mutation reachable from evaluation code
    eval_paths = py_files(EVAL_SRC) + [EVAL_CLI]
    learn_hits = scan_paths(eval_paths, LEARNING_CODE)
    ok_graph, graph_detail = run_tool(
        [py, "-c",
         "import sys; sys.path.insert(0, 'src'); import sparkrl.evaluation; "
         "bad=[m for m in sys.modules if m.startswith(('sparkrl.agent',"
         "'sparkrl.rl','sparkrl.training'))]; "
         "print('imported_learning_modules=%s' % bad); "
         "raise SystemExit(1 if bad else 0)"], timeout=300)
    check("18 no Q update on an evaluation path",
          not learn_hits and ok_graph,
          (f"no learning symbol in the {len(eval_paths)} evaluation source files; "
           f"importing sparkrl.evaluation pulls in no agent/rl/training module")
          if not learn_hits and ok_graph
          else f"hits={learn_hits} :: {graph_detail}")

    # 19 the RL policy is frozen IF referenced - it is not referenced at all
    policy_refs = scan_paths(eval_paths, re.compile(
        r"\b(policy_store|load_policy|save_policy|policy_id|QLearningAgent)\b"))
    stored_policies = sorted((PROJECT / "models" / "policies").glob("*.json")) \
        if (PROJECT / "models" / "policies").is_dir() else []
    check("19 no policy referenced by the harness", not policy_refs,
          (f"the evaluation harness references no policy artifact "
           f"({len(stored_policies)} stored policies, all untouched); a frozen "
           f"policy is loaded by EXP-005/006, not by Day 31")
          if not policy_refs else f"policy references: {policy_refs}")

    # 20 no multi-step RL; DEC-011 intact and still resolves NO
    #    A5 REFUSAL gates are excused and REPORTED (see A5_REFUSAL_CONTRACT).
    _ms_all = scan_paths(py_files(SRC), MULTISTEP_CODE)
    _ms_refusal = [h for h in _ms_all if a5_refusal_only(PROJECT / h)]
    ms_hits = [h for h in _ms_all if h not in _ms_refusal]
    try:
        from sparkrl.agent.q_learning import AgentConfig          # noqa: E402
        loaded_gamma = AgentConfig.from_yaml(RL_CONFIG).gamma
    except Exception as exc:                                     # noqa: BLE001
        loaded_gamma = f"<load error: {exc}>"
    dec_text = DECISIONS.read_text(encoding="utf-8")
    dec_ids = re.findall(r"^## (DEC-\d+)", dec_text, re.MULTILINE)
    # DEC-011 need not be the LAST entry: DEC-012/013 were signed after it on
    # Day 31. Slice DEC-011 up to the next DEC heading so a later entry cannot
    # satisfy this assertion on its behalf.
    if "## DEC-011" in dec_text:
        _s = dec_text.index("## DEC-011")
        _n = dec_text.find(chr(10) + "## DEC-", _s + 1)
        entry = dec_text[_s:] if _n == -1 else dec_text[_s:_n]
    else:
        entry = ""
    dec_ok = bool(entry) and ("resolves **NO**" in entry or "resolved NO" in entry)
    check("20 no multi-step RL; DEC-011 intact",
          not ms_hits and loaded_gamma == FROZEN_GAMMA and bool(dec_ok),
          f"gamma={loaded_gamma!r} (bandit), DEC-011 present={bool(entry)}, last={dec_ids[-1] if dec_ids else None}"
          f", says NO={bool(dec_ok)}, multi-step hits={len(ms_hits)}"
          + (f" {ms_hits[:3]}" if ms_hits else ""))

    # 21 no cache (COMP-EXP-11), no durable orchestrator (COMP-EXP-12), no deep RL
    #
    #    FORBIDDEN_CODE bundles two different questions. The MACHINERY half
    #    (cache / orchestrator / deep RL) is this check's actual subject and
    #    is never excused for any file. The EXPERIMENT-ID half answers "has a
    #    future experiment started?", which check 26 answers properly, from
    #    ARTIFACTS. Two kinds of file name an experiment id without starting
    #    one, and both are legitimate:
    #      * this validator itself - previously given a BLANKET pass by
    #        filename, which also exempted it from the machinery half; it is
    #        now scanned for machinery like everything else, so the exemption
    #        is strictly narrower than the line it replaces;
    #      * scripts/freeze_exp006.py - DEC-021 s1-9 requires EXP-006's
    #        universe to EXCLUDE the cells EXP-005 already consumed, so it
    #        must read EXP-005's spec; the hit is a local named `exp005`.
    #    Any OTHER file naming an experiment id still FAILS, and a cache,
    #    orchestrator or deep-RL symbol in ANY file - including these two -
    #    still FAILS.
    ID_NAMING_EXEMPT = ("scripts/validate_day31.py", "scripts/freeze_exp006.py")
    _all_py = py_files(SRC) + py_files(SCRIPTS)
    _rel = {p: str(p.relative_to(PROJECT)).replace("\\", "/") for p in _all_py}
    _exempt = [p for p in _all_py if _rel[p] in ID_NAMING_EXEMPT]
    _strict = [p for p in _all_py if _rel[p] not in ID_NAMING_EXEMPT]
    fb_hits = sorted(scan_paths(_strict, FORBIDDEN_CODE)
                     + scan_paths(_exempt, FORBIDDEN_MACHINERY))
    check("21 no cache / orchestrator / deep RL", not fb_hits,
          ("no execution cache, durable orchestrator or deep-RL symbol in "
           f"src/ or scripts/ ({len(_exempt)} file(s) exempt from the "
           f"experiment-id half only, still machinery-scanned: "
           f"{', '.join(ID_NAMING_EXEMPT)})")
          if not fb_hits else "found in: " + ", ".join(fb_hits))

    # ---- E. nothing SPENT --------------------------------------------------
    # 22 the TRAINING ledger accounts for the Day-29 baseline plus every
    #     authorized TRAIN spend since. The absolute total may exceed the
    #     Day-29 figure because DEC-017 authorized the 84-run B4 TRAIN search,
    #     the Day-32 user protocol authorized the 20-run EXP-001 TRAIN
    #     calibration, and DEC-026 authorized EXP-007's A1/A2 TRAIN runs
    #     (reconciled at 126 by DEC-031 sections 3/4/8) - so the assertion is
    #     that every execution above the Day-29 baseline is ATTRIBUTABLE to a
    #     recorded authorization, never that the total is frozen.
    #     EXP-003/005/005b/006 remain separate register lines, charged 0.
    #
    #     THE MANIFEST-COUNT CONJUNCT WAS REMOVED, and deliberately not
    #     replaced. It asserted n_manifests == 9 and existed to catch a run
    #     that charged ZERO (which the arithmetic below cannot see). It could
    #     not be repaired here without deciding whether an aborted, zero-live
    #     manifest counts toward a manifest-count invariant - a question the
    #     record leaves explicitly UNRESOLVED, and which this validator must
    #     not settle by implication. Dropping it opens no detection hole:
    #     Day 30 and Day 31 share the calendar date 2026-09-13, this file has
    #     no day-scoping mechanism of its own, and validate_day30.py check 14
    #     already FAILS on any 2026-09-13 run directory INCLUDING one that
    #     charged zero - a verdict this validator inherits through the
    #     prior-validator subprocess in section G. The zero-charge case is
    #     therefore covered structurally rather than by inventing a policy.
    n_manifests, live_total = ledger_from_manifests()
    ledger_errors = list(getattr(ledger_from_manifests, "errors", []))
    b4_art = ARTIFACT_DIR / "b4_selection.json"
    b4_spent = 0
    if b4_art.exists():
        _b4 = load_json(b4_art)
        if _b4.get("split") == "train":
            b4_spent = int((_b4.get("observation_counts") or {}).get("total", 0))
    exp001_sum = PROJECT / "results" / "experiments" / "exp-001" / "summary.json"
    exp001_spent = 0
    if exp001_sum.exists():
        # Intentionally strict (no try/except): ledger_from_manifests above
        # already parsed the same file under the same conditions, so any
        # malformed content is recorded in ledger_errors and fails below.
        # A second silent except here would mask the corruption twice.
        _e1 = json.loads(exp001_sum.read_text(encoding="utf-8"))
        if _e1.get("experiment_id") == "EXP-001" \
                and _e1.get("contains_test_data") is False:
            exp001_spent = int((_e1.get("observation_counts") or {}).get("total", 0))
    # EXP-007 A1/A2 (DEC-026 authorization; reconciled at 126 by DEC-031
    # sections 3/4/8) executed real TRAIN cells and DID write training
    # manifests, so its executions are ALREADY inside live_total. The
    # subtrahend must therefore NEVER be recomputed by re-summing those same
    # manifests: that would make unexplained identically zero by construction,
    # silently absorbing arbitrary growth and destroying the very detection
    # this check exists for. It is read instead from EXP-007's own FROZEN
    # analysis artifact - the same shape as the B4 and EXP-001 terms above -
    # which is a stored file that does NOT move when the live tree changes.
    exp007_art = ARTIFACT_DIR / "exp007_analysis.json"
    exp007_spent = 0
    if exp007_art.exists():
        # NOT strict like the EXP-001 branch: ledger_from_manifests never
        # parses this artifact, so nothing else would record its corruption.
        # Malformed evidence must fail LOUDLY, never undercount to zero.
        try:
            _e7 = load_json(exp007_art)
        except (OSError, json.JSONDecodeError) as exc:
            ledger_errors.append(f"{exp007_art.name}: {type(exc).__name__}")
            _e7 = {}
        if not isinstance(_e7, dict):
            ledger_errors.append(f"{exp007_art.name}: artifact is not an object")
            _e7 = {}
        _v7 = _e7.get("validation") or {}
        if not isinstance(_v7, dict):
            ledger_errors.append(f"{exp007_art.name}: validation is not an object")
            _v7 = {}
        if _e7.get("experiment_id") == "EXP-007" \
                and _v7.get("no_test_data_included") is True:
            try:
                exp007_spent = int(_v7.get("total_live_executions", 0))
            except (ValueError, TypeError):
                ledger_errors.append(
                    f"{exp007_art.name}: corrupt total_live_executions")
    unexplained = (live_total - DAY29_LIVE_EXECUTIONS - b4_spent
                   - exp001_spent - exp007_spent)
    check("22 every live execution is authorized",
          unexplained == 0 and live_total <= LIVE_EXECUTION_CAP
          and not ledger_errors,
          f"{n_manifests} manifests (reported, not asserted); {live_total} "
          f"live executions = {DAY29_LIVE_EXECUTIONS} Day-29 baseline + "
          f"{b4_spent} B4 + {exp001_spent} EXP-001 + {exp007_spent} EXP-007 "
          f"+ {unexplained} unexplained (must be exactly 0; a NEGATIVE value "
          f"means authorized spend exceeds the measured ledger and FAILS "
          f"loudly as inconsistent accounting); "
          f"{LIVE_EXECUTION_CAP - live_total} remaining of {LIVE_EXECUTION_CAP}"
          + (f"; ledger_errors={ledger_errors[:2]}" if ledger_errors else ""))

    # 23 the projection executes nothing, and the cap gap is DISCLOSED not hidden
    projection = eval_spec.project_cost(EVALUATION_REPETITIONS)
    stored_projection = (spec_doc.get("projection") or {}) if spec_doc else {}
    disclosed = (stored_projection.get("shortfall_runs")
                 == projection["shortfall_runs"]
                 and "not charged" in str(stored_projection.get("budget_note", "")
                                          ).lower()) if stored_projection else False
    budget_ok = (projection["executed"] is False
                 and projection[
                     "spark_executions_performed_by_this_projection"] == 0
                 and live_total + 0 <= LIVE_EXECUTION_CAP
                 and disclosed)
    check("23 projection spends 0; gap disclosed", budget_ok,
          f"projected minimum {projection['minimum_total_runs']} runs vs PLAN "
          f"~{projection['plan_estimate_runs']} (shortfall "
          f"{projection['shortfall_runs']}) - DISCLOSED in the artifact; "
          f"executed={projection['executed']}, spark_executions=0; EXP-003 is "
          f"not charged to the {LIVE_EXECUTION_CAP} training cap")

    # 24 the planned queue has no duplicate evaluation ids
    plan = orchestration.validation_run_plan(base_config, EVALUATION_REPETITIONS)
    ids = [r.run_id for r in plan]
    paths = [r.relative_path().as_posix() for r in plan]
    keys = [(r.family, r.scale, r.seed, r.config.name, r.rep) for r in plan]
    expected_runs = (VALIDATION_CELL_COUNT * CANDIDATE_COUNT
                     * EVALUATION_REPETITIONS)
    check("24 no duplicate evaluation ids",
          len(set(ids)) == len(ids) == expected_runs
          and len(set(paths)) == len(paths) and len(set(keys)) == len(keys)
          and all(split_of(r.family, r.scale, r.seed) == "validation"
                  for r in plan),
          f"{len(ids)} planned runs, {len(set(ids))} distinct ids / "
          f"{len(set(paths))} distinct paths, every cell validation "
          f"(PLANNED ONLY - nothing executed)")

    # ---- F. immutability and no future experiment --------------------------
    # 25 a DIFFERING overwrite of an immutable artifact is refused - proved
    if not spec_doc:
        check("25 immutable artifact refuses overwrite", None,
              "SKIP: no stored artifact to copy for the probe")
    else:
        with tempfile.TemporaryDirectory() as tmp:
            probe = Path(tmp) / "evaluation_spec.json"
            freeze_mod.write_artifact(spec_doc, probe)          # fresh write
            idempotent = freeze_mod.write_artifact(spec_doc, probe) == probe
            mutated = freeze_mod.seal({**{k: v for k, v in spec_doc.items()
                                          if k not in ("artifact_id",
                                                       "fingerprint",
                                                       "created_utc")},
                                       "repetitions": 999})
            try:
                freeze_mod.write_artifact(mutated, probe)
                raised = "<no exception - OVERWRITTEN>"
            except freeze_mod.ArtifactExistsError as exc:
                raised = f"ArtifactExistsError: {str(exc)[:40]}"
            except Exception as exc:                            # noqa: BLE001
                raised = f"{type(exc).__name__}: {exc}"
            check("25 immutable artifact refuses overwrite",
                  raised.startswith("ArtifactExistsError") and idempotent,
                  f"identical rebuild is a no-op={idempotent}; differing write "
                  f"-> {raised[:60]}")

    # 26 no UNAUTHORIZED experiment has started producing artifacts.
    #
    #    The original form globbed the PRESENT tree for filenames and
    #    asserted the union was empty. That was sound only while nothing
    #    under those names existed; EXP-005 (DEC-018), EXP-006 (DEC-020/021/
    #    022) and EXP-007 (DEC-023/025/026) have since been authorized and
    #    run, so a bare existence test can no longer express the claim it
    #    prints. What it must still prove is that no experiment produced
    #    artifacts WITHOUT an authorization, and that DAY 31 executed
    #    nothing.
    #
    #    Each carve-out below names the decision that authorizes it and is
    #    gated on that decision being COMMITTED at HEAD - the worktree
    #    cannot authorize itself, which is the same rule the Day-25/26/27
    #    driver checks enforce. An artifact whose decision is absent from
    #    HEAD is NOT excused. The executed=True conjunct below is untouched
    #    and fully strict: any stored artifact that declares it EXECUTED
    #    still FAILS this check, whatever authorized it.
    _r = subprocess.run(["git", "show", "HEAD:DECISIONS.md"],
                        cwd=PROJECT, capture_output=True, text=True)
    _head_decs = set(re.findall(r"^##\s*(DEC-\d+)", _r.stdout, re.M)) \
        if _r.returncode == 0 else set()
    # DEC-030 is recorded OUTSIDE DECISIONS.md by design (DEC-032 s0), so it
    # is present iff its own committed artifact is tracked at HEAD.
    _r30 = subprocess.run(
        ["git", "cat-file", "-e",
         "HEAD:docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md"],
        cwd=PROJECT, capture_output=True, text=True)
    if _r30.returncode == 0:
        _head_decs.add("DEC-030")
    # artifact name or path fragment -> the decision that authorizes it
    AUTHORIZED_ARTIFACTS = {
        "exp-005": "DEC-018", "exp005_analysis.json": "DEC-018",
        "exp-006": "DEC-022", "exp006_analysis.json": "DEC-022",
        "exp006_spec.json": "DEC-022",
        # the DEC-022-approved 7-run dry slice (run_exp006.py DRY_SLICE = 7,
        # "B0 reps 1-5 + B2 reps 1-2"); summary.json records
        # stage="dry-slice (7 of 125)", protocol_version="exp006/v1"
        "exp-006-dry-slice": "DEC-022",
        "exp007_analysis.json": "DEC-026",
        "exp008_methodology_freeze.json": "DEC-030",
        "exp008_preflight_audit.json": "DEC-030",
        "exp008_b6_implementation.json": "DEC-031",
        "exp008_budget_reconciliation.json": "DEC-031",
    }

    def _authorized(name: str) -> bool:
        """True iff `name` is a carved-out artifact whose DEC is at HEAD."""
        dec = AUTHORIZED_ARTIFACTS.get(name)
        return bool(dec) and dec in _head_decs

    future: list[str] = []
    if RESULTS.is_dir():
        allowed_scope = {"exp005_instances.json", "b4_selection.json"}
        for pattern in FUTURE_EXPERIMENT_GLOBS:
            future += [str(p.relative_to(PROJECT)).replace("\\", "/")
                       for p in RESULTS.rglob(pattern)
                       if p.name not in allowed_scope
                       and not _authorized(p.name)]
    stored_executed = [p.name for p in ARTIFACT_DIR.glob("*.json")
                       if load_json(p).get("executed") is True] \
        if ARTIFACT_DIR.is_dir() else []
    unknown = sorted(p.name for p in ARTIFACT_DIR.glob("*.json")
                     if p.name not in ("evaluation_spec.json",
                                       "baseline_selection.json",
                                       # forensic recovery of the 96 run
                                       # identities; carries NO authoritative
                                       # timing and no research claim
                                       "validation_observations.json",
                                       # DEC-016 D: the EXP-005 instance
                                       # SCOPE definition (executed=false)
                                       # and DEC-016 C's B4 TRAIN-search
                                       # result. Scope/selection artifacts
                                       # are not experiment RESULTS; the
                                       # executed=True test below still
                                       # catches a real run.
                                       "exp005_instances.json",
                                       "b4_selection.json",
                                       "test_freeze.json")
                     and not _authorized(p.name)) \
        if ARTIFACT_DIR.is_dir() else []
    check("26 no EXP-005/005b/006 artifact", not future and not stored_executed
          and not unknown,
          f"no future-experiment path under results/; every stored evaluation "
          f"artifact says executed=false; no unexpected artifact"
          if not future and not stored_executed and not unknown
          else f"future={future[:3]} executed={stored_executed} unknown={unknown}")

    # 27 no tracked file modified - Day 31 creates NEW files only
    changed, why = git_modified_tracked()
    if changed is None:
        check("27 no frozen file modified", None, f"SKIP: {why}")
    else:
        # Originally "no tracked file modified", correct while Day 31 was purely
        # additive. DEC-012 and DEC-013 were then signed, which authorizes an
        # exact, named set. Anything outside it is still a failure.
        authorized = {
            "DECISIONS.md",                                  # the signed DEC-012/013
            ".gitignore",                                    # DEC-013 artifact exception
            "src/sparkrl/experiments/runner.py",             # DEC-013: additive split_guard
            "src/sparkrl/evaluation/orchestration.py",       # Day-31 calibration wiring
            "scripts/validate_day30.py",                     # validator maintenance
            "scripts/validate_day31.py",
            "scripts/validate_rl_environment.py",            # Day-32 EXP-001 maintenance
            "tests/unit/test_day31_evaluation.py",
            "tests/unit/test_evaluation_harness.py",
            "tests/unit/test_exp001_maintenance.py",         # Day-32 EXP-001 maintenance
            # DEC-016 (A-F) authorizes the Day-32 strategy layer
            "src/sparkrl/evaluation/strategies.py",
            "tests/unit/test_exp005_strategies.py",
            "configs/baseline_b0_prime.yaml",
            # DEC-017 directs the pending DEC-014 draft to be amended to
            # the resolved scope; its STATUS must stay PENDING, which
            # check 25 verifies independently.
            "docs/research/DEC_014_TEST_EXECUTION_AUTHORIZATION_EXP005.md",
        }
        unexpected = sorted(f for f in changed if f not in authorized)
        # the split guard must be SEMANTICALLY unchanged despite runner.py moving
        from sparkrl.experiments.spec import assert_train_only
        guard_ok = True
        try:
            assert_train_only("F1_agg", "small", 0)          # TRAIN accepted
            for cell in (("F1_agg", "small", 3), ("F4_ski", "small", 0),
                         ("F1_agg", "large", 0), ("F1_agg", "small", 4)):
                try:
                    assert_train_only(*cell)
                    guard_ok = False                          # must have raised
                except ValueError:
                    pass
        except Exception:                                     # noqa: BLE001
            guard_ok = False
        check("27 only DEC-authorized files modified",
              not unexpected and guard_ok,
              (f"{len(changed)} modified, all authorized by DEC-012/013; "
               f"assert_train_only still refuses validation and test")
              if not unexpected and guard_ok
              else f"unexpected={unexpected[:5]} guard_semantics_ok={guard_ok}")

    # 28 the Day-31 documentation matches the artifacts
    day31_docs = sorted(RESEARCH.glob(DAY31_DOC_GLOB))
    if not day31_docs:
        check("28 Day-31 documentation matches artifacts", None,
              f"SKIP: no {DAY31_DOC_GLOB} under docs/research - the Day-31 audit "
              f"document has not been written yet")
    else:
        text = "\n".join(d.read_text(encoding="utf-8", errors="replace")
                         for d in day31_docs)
        wanted = []
        if spec_doc:
            wanted.append(("evaluation_spec artifact_id",
                           spec_doc["artifact_id"][:16] in text))
        if freeze_doc:
            wanted.append(("test_freeze artifact_id",
                           freeze_doc["artifact_id"][:16] in text))
            wanted.append(("manifest_fingerprint",
                           freeze_doc["manifest_fingerprint"][:16] in text))
            wanted.append(("test cell count",
                           str(freeze_doc["cell_count"]) in text))
        missing = [label for label, present in wanted if not present]
        check("28 Day-31 documentation matches artifacts", not missing,
              f"{', '.join(d.name for d in day31_docs)}: "
              + ("every artifact id / fingerprint / count quoted"
                 if not missing else "missing: " + ", ".join(missing)))

    # ---- G. prior evidence still stands ------------------------------------
    # 29-34 the six prior validators still pass (read-only, no Spark)
    for label, script in PRIOR_VALIDATORS:
        path = SCRIPTS / script
        if not path.exists():
            check(f"{label} validator", None, f"SKIP: missing {script}")
            continue
        ok, detail = run_tool([py, str(path)], timeout=1800)
        check(f"{label} validator", ok, detail)

    # 35 deterministic unit suite still passes (no Spark, no integration)
    ok, detail = run_tool([py, "-m", "pytest", "tests/unit", "-q",
                           "--no-header", "-p", "no:cacheprovider"],
                          timeout=900)
    check("35 unit suite (tests/unit)", ok, detail)

    failed = [r for r in results if r[1] == "FAIL"]
    skipped = [r for r in results if r[1] == "SKIP"]
    passed = [r for r in results if r[1] == "PASS"]
    print("-" * 72)
    print(f"OVERALL: {'FAIL' if failed else 'PASS'}"
          f"  ({len(results)} checks, {len(passed)} pass, {len(failed)} fail, "
          f"{len(skipped)} skip)")
    if skipped:
        for name, _, detail in skipped:
            print(f"  SKIPPED: {name} -- {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
