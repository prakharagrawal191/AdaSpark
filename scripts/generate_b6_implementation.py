"""Regenerate ``results/evaluation/exp008_b6_implementation.json`` (B6 record).

DETERMINISTIC AND READ-ONLY EXCEPT FOR ITS OWN OUTPUT. This runner performs
**0 Spark executions**, trains nothing, executes no TEST, creates no run
directory, and authorizes nothing: EXP-008 execution authorization is an
EXTERNAL governance decision and remains **NO** (DEC-030 section 11; DEC-031
section 14). Re-running it on an unchanged tree rewrites the same bytes.

It records what the B6 implementation task produced: which DEC-030 frozen
rules are now implemented, which DEC-030 unresolved fields remain explicitly
required-but-unset, which guards exist, and the fingerprints proving that
PLAN.md, DEC-030, DEC-031 and every prior experiment artifact are unchanged.

Usage::

    python scripts/generate_b6_implementation.py          # write
    python scripts/generate_b6_implementation.py --check   # verify only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
OUT_PATH = PROJECT / "results" / "evaluation" / "exp008_b6_implementation.json"

SCHEMA_VERSION = "exp008-b6-implementation/v1"
TASK_ID = "B6"
DATE = "2026-09-18"

# --- files the B6 implementation task touched --------------------------------
# "b6" = created or edited to implement DEC-030's frozen A3/A4 methodology.
# "pre_b6" = already modified in the working tree by EXP-007 (DEC-023/025/026)
# before B6 began; listed for completeness, NOT attributed to B6.
CHANGED_FILES: tuple[tuple[str, str, str], ...] = (
    ("src/sparkrl/rl/reward.py", "modified", "b6"),
    ("src/sparkrl/rl/__init__.py", "modified", "b6"),
    ("src/sparkrl/training/__init__.py", "modified", "b6"),
    ("src/sparkrl/training/exp008.py", "created", "b6"),
    ("configs/exp008.yaml", "created", "b6"),
    ("tests/unit/test_exp008_reward.py", "created", "b6"),
    ("tests/unit/test_exp008_action.py", "created", "b6"),
    ("tests/unit/test_exp008_scope.py", "created", "b6"),
    ("scripts/generate_b6_implementation.py", "created", "b6"),
    ("docs/research/DAY37_EXP008_B6_IMPLEMENTATION_REPORT.md", "created", "b6"),
)

CHANGE_REASONS: dict[str, str] = {
    "src/sparkrl/rl/reward.py":
        "DEC-030 s3: additive A3 variant registry - R3 unchanged, "
        "A3-time-only implemented exactly, A3-R4-log-ratio registered but "
        "refused before any computation (IncompleteFormulaError).",
    "src/sparkrl/rl/__init__.py":
        "Re-exports the additive reward symbols; no behaviour.",
    "src/sparkrl/training/__init__.py":
        "Re-exports the EXP-008 scope layer; no behaviour.",
    "src/sparkrl/training/exp008.py":
        "DEC-030 s3/4/5/6/9/12: the non-executing EXP-008 scope layer - arm "
        "registry, fail-closed arm configuration schema, Q0 policy, TRAIN-only "
        "and A5 guards, and the run-manifest provenance record.",
    "configs/exp008.yaml":
        "DEC-030 s12: schema-safe representation of the frozen A3/A4 arms in "
        "which every unresolved methodological field is an explicit null.",
    "tests/unit/test_exp008_reward.py":
        "Zero-Spark proof of the A3 reward semantics (R3 unchanged; time-only "
        "exact; R4 non-executable).",
    "tests/unit/test_exp008_action.py":
        "Zero-Spark proof of the A4 action semantics (mode12 unchanged; mode4 "
        "= {0,3,6,9}; original indices preserved; non-mode4 rejected).",
    "tests/unit/test_exp008_scope.py":
        "Zero-Spark proof of the Q0 policy, TRAIN/TEST guards, A5 lock, "
        "fail-closed configuration and provenance completeness.",
    "scripts/generate_b6_implementation.py":
        "Deterministic, read-only generator for this artifact.",
    "docs/research/DAY37_EXP008_B6_IMPLEMENTATION_REPORT.md":
        "The B6 implementation report required by the task.",
}

# --- files that MUST be byte-identical to their governing record -------------
# Each entry: (path, expected SHA256, where the expectation is recorded).
IMMUTABLE: tuple[tuple[str, str, str], ...] = (
    ("docs/PLAN.md",
     "db5e82102833efe6bab8db1adaf1b35ad195faf385e63ab296d50562e349ee63",
     "DEC-031 s15"),
    ("configs/rl.yaml",
     "8ca70d6dd7df68841c409a4441dc538616206bccea7877b28c73df20e6428b80",
     "DEC-031 s15"),
    ("configs/reward.yaml",
     "a52131d5a0de63ef06d3dd5b181f1bbeda326df3ffffbd2ae1c69ed96571db1b",
     "exp008_methodology_freeze.json source_document_fingerprints"),
    ("docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md",
     "ec487bf2a84a9c1a6f506bdd83c71b7c7bb7ae2cceaf7e761f000c7201912a5a",
     "exp008_methodology_freeze.json dec030_fingerprint"),
    ("results/evaluation/exp008_budget_reconciliation.json",
     "bd67da1735aaaa9d62ac977f2874034dca1f70db7da849db436b2ca939a596c5",
     "DEC-031 s15 (retained byte-identical)"),
    ("src/sparkrl/rl/action.py",
     "580cf010f17b2cb0f7c3b7967d4fb560b7f973028e8a1909123e7d337f4c0528",
     "exp008_methodology_freeze.json (frozen 12-action grid; A4 reuses it)"),
    ("src/sparkrl/agent/q0.py",
     "7d2ffb0c33fc4349a71d3e064781927425092ff86be2eeed595705b3111de195",
     "exp008_methodology_freeze.json (primary + neutral Q0 untouched)"),
    ("src/sparkrl/agent/q_learning.py",
     "1c5fab897f8f652b90cd9011b1d84846459f041d31565c9652c4edd578d9bb31",
     "exp008_methodology_freeze.json (learner untouched)"),
    ("src/sparkrl/rl/state.py",
     "3ce6ee042829b4374776617fdf74f1f7a375905d35e414a577823b149911bda0",
     "exp008_methodology_freeze.json (state schemas untouched)"),
    ("src/sparkrl/rl/env.py",
     "66ff0497ebdf594d33936215a06c2197a5c3ed6301ddffe170486e20b251e975",
     "exp008_methodology_freeze.json (environment untouched)"),
    ("src/sparkrl/training/loop.py",
     "b513238d5148a16cc8e39283526082b0c199fee5ad7a00326d95f4ad3983a611",
     "exp008_methodology_freeze.json (training loop untouched)"),
    ("src/sparkrl/training/ablation.py",
     "69ab9c40e1688405b8b6f795783ada7fbf26c753bacb76d0aba215b7fb5b216a",
     "exp008_methodology_freeze.json (EXP-007 scope untouched)"),
    ("results/evaluation/exp007_analysis.json",
     "e010072f0254a57e09656e4551d4c3ff3c6903ff9347c721b39d5ea8c0043b68",
     "EXP-007 output - must not be altered by B6"),
)

# Recorded by the Phase-11 zero-Spark validation run (pytest, no Spark, no
# integration tests). Numbers are collected-test counts.
TEST_SUMMARY: dict[str, object] = {
    "runner": "python -m pytest tests/unit",
    "spark_used": False,
    "integration_tests_run": False,
    "new_tests": {
        "tests/unit/test_exp008_reward.py": 21,
        "tests/unit/test_exp008_action.py": 32,
        "tests/unit/test_exp008_scope.py": 50,
    },
    "new_tests_total": 103,
    "new_tests_passed": 103,
    "new_tests_failed": 0,
    "regression_suite": {
        "scope": "tests/unit (full)",
        "before_b6": {"passed": 559, "failed": 1, "skipped": 1},
        "after_b6": {"passed": 662, "failed": 1, "skipped": 1},
    },
    "regression_checks": {
        "tests/unit/test_rl_reward.py": 14,
        "tests/unit/test_rl_action.py": 8,
        "tests/unit/test_rl_agent.py": 11,
        "tests/unit/test_rl_q0.py": 8,
        "tests/unit/test_rl_state.py": 18,
        "tests/unit/test_rl_training.py": 49,
        "tests/unit/test_exp007_parity.py": 16,
        "tests/unit/test_exp007_q0.py": 10,
        "tests/unit/test_exp007_scope.py": 17,
        "tests/unit/test_exp007_state.py": 32,
    },
    "pre_existing_failures": [
        {
            "test": ("tests/unit/test_exp001_maintenance.py::"
                     "test_exp003_or_exp005_are_never_charged_to_sc6"),
            "status": "FAILING BEFORE AND AFTER B6 - unchanged by B6",
            "cause": ("the test pins the pre-EXP-007 SC6 ledger (336 live / "
                      "164 remaining); the real ledger now reads 462 / 38 "
                      "because EXP-007 executed 126 charged live TRAIN "
                      "executions (336 + 126 = 462), exactly as DEC-031 "
                      "records"),
            "b6_related": False,
            "evidence": ("it reads scripts/validate_day31.py and "
                         "results/training/**/manifest.json only; neither is "
                         "in the B6 changed-file set, and validate_day31.py "
                         "imports nothing from sparkrl"),
            "disposition": ("NOT repaired by B6: re-pinning a governance "
                            "ledger constant is a DEC-031 follow-up, outside "
                            "an implementation-only task"),
        },
    ],
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def head() -> str:
    out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT,
                         capture_output=True, text=True, check=True)
    return out.stdout.strip()


def build() -> dict:
    from sparkrl.rl.reward import (FORMULA_A3_R4_LOG_RATIO,
                                   FORMULA_A3_TIME_ONLY, FORMULA_ID,
                                   IMPLEMENTED_FORMULAS,
                                   R4_UNRESOLVED_SEMANTICS,
                                   REGISTERED_FORMULAS, TIME_ONLY_WEIGHTS)
    from sparkrl.training import exp008

    immutable = []
    for rel, expected, source in IMMUTABLE:
        actual = sha256(PROJECT / rel)
        immutable.append({"path": rel, "expected_sha256": expected,
                          "actual_sha256": actual,
                          "unchanged": actual == expected,
                          "expectation_recorded_in": source})

    changed = []
    for rel, kind, owner in CHANGED_FILES:
        p = PROJECT / rel
        changed.append({
            "path": rel, "change": kind, "attributed_to": owner,
            "sha256": sha256(p) if p.exists() else None,
            "bytes": p.stat().st_size if p.exists() else None,
            "reason": CHANGE_REASONS[rel],
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "task": TASK_ID,
        "date": DATE,
        "scope": ("EXP-008 A3/A4 implementation support only (B6). "
                  "Implementation-only: no execution, no authorization."),
        "repository_head": head(),
        "authority_chain": [
            "docs/PLAN.md",
            "DECISIONS.md (through DEC-031)",
            "docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md",
            "docs/research/DEC_031_EXP008_SC6_BUDGET_RECONCILIATION.md",
            "results/evaluation/exp008_preflight_audit.json",
            "results/evaluation/exp008_budget_reconciliation.json",
            "experiments/registry.csv",
        ],
        "dec030_fingerprint": sha256(
            PROJECT / "docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md"),
        "dec031_fingerprint": sha256(
            PROJECT / "docs/research/DEC_031_EXP008_SC6_BUDGET_RECONCILIATION.md"),
        "decisions_md_fingerprint": sha256(PROJECT / "DECISIONS.md"),
        "changed_files": changed,
        "unchanged_files": immutable,
        "reward_variants": {
            "registered": list(REGISTERED_FORMULAS),
            "implemented": list(IMPLEMENTED_FORMULAS),
            "registered_but_not_executable": [FORMULA_A3_R4_LOG_RATIO],
            FORMULA_ID: {
                "status": "UNCHANGED (frozen primary reward)",
                "default": True,
                "weights_source": "configs/reward.yaml (validator-enforced)",
            },
            FORMULA_A3_TIME_ONLY: {
                "status": "IMPLEMENTED",
                "formula": "R = 1.0 * clip((T_ref - T) / T_ref, -1, +1)",
                "failure_value": -1.0,
                "weights": dict(TIME_ONLY_WEIGHTS),
                "classification": ("MULTI-TERM REMOVAL from R3 - the "
                                   "task-imbalance term AND the spill-waste "
                                   "term are removed simultaneously; this is "
                                   "explicitly NOT a one-factor ablation"),
                "removed_terms": ["task_imbalance", "spill_waste"],
            },
            FORMULA_A3_R4_LOG_RATIO: {
                "status": "REGISTERED, NOT EXECUTABLE",
                "registered_formula": "R4 = -ln(T / T_ref)",
                "refusal": "IncompleteFormulaError raised at construction",
                "substitution": ("none - R3 behaviour, clipping and failure "
                                 "transformation are never silently applied"),
            },
        },
        "action_modes": {
            "implemented": ["mode12", "mode4"],
            "mode12": {"status": "UNCHANGED", "actions": list(range(12))},
            "mode4": {
                "status": "REUSED from the frozen Plan-B definition "
                          "(sparkrl.rl.action.MODE4_SUBSET) - never redefined",
                "subset": sorted(exp008.A4_ACTION_SUBSET),
                "rejected_actions": list(exp008.NON_A4_ACTIONS),
                "indices_preserved": True,
                "renumbered": False,
                "configurations": [dict(c)
                                   for c in exp008.a4_action_configurations()],
            },
        },
        "q0_policy": {
            "projection_invented": False,
            "pooling_invented": False,
            "rows_collapsed": False,
            "new_learned_q0": False,
            "test_derived_q0": False,
            "primary_study_q0_changed": False,
            "rows_wide": exp008.Q0_ROWS_WIDE,
            "per_arm": {arm: exp008.q0_policy(arm) for arm in exp008.ALL_ARMS},
        },
        "unresolved_semantics": {
            "r4": list(R4_UNRESOLVED_SEMANTICS),
            "per_arm_required_but_unset": {
                arm: list(exp008.required_fields(arm))
                for arm in exp008.ALL_ARMS
            },
            "representation": ("explicit null in configs/exp008.yaml and None "
                               "on Exp008ArmConfig; listed in every "
                               "provenance record under 'unresolved_fields'"),
            "behaviour": ("fail closed - Exp008IncompleteError before any "
                          "Spark execution; no hidden default is chosen"),
        },
        "guards": {
            "train_only_split": "guard_split / guard_cell / guard_train_cells",
            "test_metrics_refused": "guard_metrics",
            "a5_blocked": "guard_a5 (arm, multi_step, gamma != 0.0)",
            "unsupported_reward_refused": "build_reward_calculator",
            "incomplete_r4_refused": "RewardCalculator.__init__",
            "unsupported_q0_refused": "guard_q0_source",
            "q0_projection_refused": "guard_q0_projection",
            "q0_row_width_enforced": "guard_q0_rows / guard_q0_for_mode",
            "non_mode4_actions_refused": "ActionMapper._validate / guard_action",
            "a4_locked_to_mode4": "guard_action_mode_for_arm",
            "closed_config_schema": "arm_config_from_mapping",
            "authorization_mechanism_present": False,
            "all_refusals_pre_spark": True,
        },
        "defaults_preserved": {
            "reward_default_formula": FORMULA_ID,
            "action_mode_default": "mode12",
            "gamma": 0.0,
            "live_execution_cap": 500,
            "primary_training_path_changed": False,
            "a1_a2_path_changed": False,
            "baseline_path_changed": False,
            "exp005_exp006_path_changed": False,
        },
        "test_summary": TEST_SUMMARY,
        "budget": {
            "sc6_cap": 500,
            "cumulative_charge": 462,
            "remaining_headroom": 38,
            "charged_by_b6": 0,
            "source": "DEC-031 sections 3, 4 and 8",
        },
        "a5_status": exp008.A5_STATUS,
        "execution_authorized": False,
        "execution_authorization": "NO",
        "implementation_is_authorization": False,
        "spark_execution_count": 0,
        "training_execution_count": 0,
        "test_execution_count": 0,
        "artifacts_modified": {
            "plan_md": False,
            "decisions_md": False,
            "dec030": False,
            "dec031": False,
            "budget_json": False,
            "exp007_json": False,
            "training_artifacts": False,
            "experiment_results": False,
        },
        "new_decisions_required": [
            {
                "id": "B6 implementation decision",
                "why": ("DEC-030 section 15 gate chain item (3) expects a "
                        "separate decision entry recording B6 with green "
                        "zero-Spark tests; this artifact supplies the "
                        "evidence, it is NOT the decision"),
            },
            {
                "id": "R4 complete specification",
                "why": ("DEC-030 section 12 field 15 - until it is frozen, "
                        "A3-R4-log-ratio cannot be constructed or computed"),
            },
            {
                "id": "Every DEC-030 section 12 field (1-18)",
                "why": ("each remains required-but-unset; the configuration "
                        "fails closed until a later decision supplies it"),
            },
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="verify the stored artifact instead of writing")
    args = parser.parse_args()

    payload = build()
    text = json.dumps(payload, indent=2, sort_keys=True,
                      ensure_ascii=False) + "\n"

    drifted = [e["path"] for e in payload["unchanged_files"]
               if not e["unchanged"]]
    if drifted:
        print("DRIFT: files that must be unchanged were modified:", file=sys.stderr)
        for path in drifted:
            print(f"  {path}", file=sys.stderr)
        return 2

    if args.check:
        if not OUT_PATH.exists():
            print(f"missing: {OUT_PATH}", file=sys.stderr)
            return 1
        same = OUT_PATH.read_text(encoding="utf-8") == text
        print("DETERMINISTIC" if same else "DIFFERS")
        return 0 if same else 1

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(text, encoding="utf-8")
    print(f"wrote {OUT_PATH} ({len(text.encode('utf-8'))} bytes)")
    print(f"sha256 {hashlib.sha256(text.encode('utf-8')).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
