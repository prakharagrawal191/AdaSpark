"""Pre-execution specification freeze for EXP-006 (DEC-020 s.B/D, DEC-021).

BUILD ONLY - NO SPARK, NO EXECUTION. Reads already-frozen artifacts and writes
exactly ONE immutable pre-execution specification:

    results/evaluation/exp006_spec.json

Authority chain (nothing here is invented):

* DEC-020 s.B/D  - EXP-006 is restricted to the 36 remaining materially
  available frozen TEST cells and is a descriptive generalization study.
* DEC-021 s.1-9  - universe correction (F4_ski|large|s3 was consumed by
  EXP-005), universe != queue, the 5-cell pre-registered subset, the arm map,
  5 repetitions, the 105-execution budget, SC5 NOT EVALUABLE, and the
  DEC-019-class treatment of B2 on F4_ski.

Every executable row's configuration or policy identity is RESOLVED from an
existing frozen artifact:

    B0          configs/baseline_b0.yaml (via strategies.resolve)
    B2          results/evaluation/baseline_selection.json per-family map
    RL-s0/1/2   models/policies/exp005_rl_arms.json (published Q-tables)
    B2 x F4_ski DEC-019 class: undefined, 0 Spark, no fallback, no substitution

Nothing is measured: no timing, no metric, no Spark session, no dataset opened.
The document is sealed with the project's own ``sparkrl.evaluation.freeze``
identity rule (sha256 over canonical JSON excluding
artifact_id/fingerprint/created_utc) and written through
``freeze.write_artifact``, so an existing DIFFERING artifact can never be
overwritten silently.

    python scripts/freeze_exp006.py            # idempotent build
    python scripts/freeze_exp006.py --verify   # rebuild + compare, no write

EXECUTION IS NOT AUTHORIZED BY THIS ARTIFACT (DEC-021 s.14).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT / "src"))

from sparkrl.evaluation.freeze import (artifact_fingerprint,  # noqa: E402
                                       manifest_fingerprint, seal,
                                       write_artifact)

# --- frozen inputs -----------------------------------------------------------
TEST_FREEZE = PROJECT / "results" / "evaluation" / "test_freeze.json"
B0_YAML = PROJECT / "configs" / "baseline_b0.yaml"
RL_MANIFEST = PROJECT / "models" / "policies" / "exp005_rl_arms.json"
EXP005_SPEC = PROJECT / "results" / "experiments" / "exp-005" / "spec.json"
EXP005_LEDGER = PROJECT / "results" / "experiments" / "exp-005" / "observations.jsonl"
EXP005_INSTANCES = PROJECT / "results" / "evaluation" / "exp005_instances.json"
OUT = PROJECT / "results" / "evaluation" / "exp006_spec.json"

SCHEMA_VERSION = "exp006-pre-exec-spec/v1"
PROTOCOL_VERSION = "exp006/v1"
EXPERIMENT_ID = "EXP-006"

#: DEC-021 s.7 - frozen. PLAN s.23 / EVALUATION_REPETITIONS = 5.
REPETITIONS = 5

#: DEC-021 s.6 - canonical arm order, used for queue ordering.
ARMS = ("B0", "B2", "RL-s0", "RL-s1", "RL-s2")
RL_ARMS = ("RL-s0", "RL-s1", "RL-s2")

#: DEC-021 s.4 - F4 cells (scale, seed): large + medium + small coverage plus
#: one further unseen seed condition.
SELECTED_F4 = (("large", 0), ("large", 4), ("medium", 3), ("small", 3))

#: DEC-021 s.5 - one non-F4 cell: lowest environment risk, ties by family order
#: then scale ladder then lowest seed -> F1_agg|large|0 (not an F3 cell).
SELECTED_NON_F4 = ("F1_agg", "large", 0)

#: DEC-021 s.3 - budget identity that must reproduce exactly.
EXPECTED_UNIVERSE = 36
EXPECTED_EXECUTABLE = 105
EXPECTED_UNDEFINED = 20
EXPECTED_ROWS = 125

#: Frozen EXP-005 identity, re-VERIFIED (never written) by this script.
EXPECTED_LEDGER_SHA = ("d928cf5d69fe5af10aac31a2e2a69723278ee0d22729d8109e8b95ae"
                       "703d3ae1")
EXPECTED_INSTANCES_PREFIX = "1c33975a"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_frozen() -> tuple[dict[str, Any], set[tuple[str, str, int]]]:
    """Frozen TEST identity plus the 7 EXP-005-consumed cells."""
    freeze = json.loads(TEST_FREEZE.read_text(encoding="utf-8"))
    exp005 = json.loads(EXP005_SPEC.read_text(encoding="utf-8"))
    consumed = {(i["family"], i["scale"], int(i["dataset_seed"]))
                for i in exp005["instances"]}
    if freeze["cell_count"] != 43:
        raise SystemExit(f"test_freeze cell_count {freeze['cell_count']} != 43")
    if len(consumed) != 7:
        raise SystemExit(f"EXP-005 consumed {len(consumed)} instances != 7")
    return freeze, consumed


def build_universe(freeze: dict[str, Any], consumed: set[tuple[str, str, int]]
                   ) -> list[dict[str, Any]]:
    """The 36 remaining candidates: identity only, canonical order."""
    cells = [(c["family"], c["scale"], int(c["seed"])) for c in freeze["cells"]]
    if len(cells) != len(set(cells)):
        raise SystemExit("test_freeze contains duplicate cell identities")
    missing = consumed - set(cells)
    if missing:
        raise SystemExit(f"EXP-005 instances not in freeze: {sorted(missing)}")
    by_id = {(c["family"], c["scale"], int(c["seed"])): c for c in freeze["cells"]}
    universe = []
    for key in sorted(k for k in by_id if k not in consumed):
        c = by_id[key]
        universe.append({
            "family": c["family"], "scale": c["scale"], "seed": c["seed"],
            "split": c["split"], "dataset_id": c["dataset_id"],
            "dataset_fingerprint": c["dataset_fingerprint"],
            "schema_fingerprint": c["schema_fingerprint"], "skew": c["skew"],
        })
    if len(universe) != EXPECTED_UNIVERSE:
        raise SystemExit(f"remaining universe {len(universe)} != {EXPECTED_UNIVERSE}")
    f4 = sorted((u["scale"], u["seed"]) for u in universe if u["family"] == "F4_ski")
    if f4 != sorted([("large", 0), ("large", 1), ("large", 2), ("large", 4),
                     ("medium", 0), ("medium", 1), ("medium", 2), ("medium", 3),
                     ("small", 0), ("small", 1), ("small", 2), ("small", 3)]):
        raise SystemExit(f"F4 remainder differs from DEC-021 s.1: {f4}")
    return universe


def resolve_identities(universe: list[dict[str, Any]]) -> dict[str, Any]:
    """Resolve each arm's frozen identity from existing artifacts (read-only)."""
    from sparkrl.evaluation.strategies import (StrategyResolutionError,
                                               resolve)
    from sparkrl.experiments.grid import b0_point

    if not universe:
        raise SystemExit("empty universe")
    b0 = resolve("B0", family="F1_agg", scale="large", dataset_seed=0)
    b0_point_fp = b0_point().fingerprint()      # normalized-config sha256
    b0_file_fp = _sha256_file(B0_YAML)          # config file bytes sha256

    # B2 per-family map is frozen; F4_ski must refuse (DEC-019 / DEC-021 s.6).
    b2: dict[str, Any] = {}
    for family in ("F1_agg", "F2_join", "F3_rdd", "F5_mixed"):
        r = resolve("B2", family=family, scale="large", dataset_seed=3)
        b2[family] = {"config_name": r.config_name,
                      "config_fingerprint": r.config_fingerprint}
    if "F4_ski" in b2:
        raise SystemExit("B2 gained an F4_ski configuration - DEC-019 violated")
    try:
        resolve("B2", family="F4_ski", scale="large", dataset_seed=0)
    except StrategyResolutionError:
        pass
    else:
        raise SystemExit("B2 resolved on F4_ski; DEC-019 undefined-class lost")

    manifest = json.loads(RL_MANIFEST.read_text(encoding="utf-8"))
    rl = {a["arm"]: {"policy_id": a["policy_id"],
                     "policy_path": a["published_path"],
                     "agent_rng_seed": a["agent_rng_seed"],
                     "source_run_id": a["source_run_id"]}
          for a in manifest["arms"]}
    if sorted(rl) != sorted(RL_ARMS):
        raise SystemExit(f"RL manifest arms {sorted(rl)} != {sorted(RL_ARMS)}")
    return {
        "B0": {"config_name": b0.config_name,
               "config_fingerprint": b0.config_fingerprint,
               "config_point_fingerprint": b0_point_fp,
               "config_file": "configs/baseline_b0.yaml",
               "config_file_sha256": b0_file_fp,
               "aqe_enabled": False,
               "resolution": "sparkrl.evaluation.strategies.resolve('B0')"},
        "B2": {"by_family": b2,
               "artifact": "results/evaluation/baseline_selection.json",
               "resolution": "sparkrl.evaluation.strategies.resolve('B2', family)",
               "undefined_on": ["F4_ski"]},
        "RL": {"manifest": "models/policies/exp005_rl_arms.json",
               "manifest_fingerprint": manifest["fingerprint"],
               "arms": rl,
               "selection": "frozen Q-table, greedy per state; never retrained"},
        "B3": {"status": "ANALYTIC-ONLY",
               "note": ("DEC-016 Decision B / DEC-017 / DEC-021 s.6 - computed "
                        "from manifests, never queued, never executed")},
    }


def select_instances(universe: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The 5 pre-registered execution cells, in canonical (family, scale, seed)."""
    by_key = {(u["family"], u["scale"], u["seed"]): u for u in universe}
    wanted = [SELECTED_NON_F4] + [("F4_ski", s, k) for s, k in SELECTED_F4]
    selected = []
    for key in wanted:
        if key not in by_key:
            raise SystemExit(f"selected cell not in remaining universe: {key}")
        cell = dict(by_key[key])
        if cell["split"] != "test":
            raise SystemExit(f"selected cell is not split=test: {key}")
        if cell["family"] == "F4_ski":
            cell["unseen_dimension"] = "unseen family F4 (skew 1.5)"
            cell["arms_applicable"] = list(ARMS)
            # DEC-019 Option A class: the B2 identity is preserved as a row so
            # the queue stays auditable, but it is never executable.
            cell["executable_arms"] = ["B0"] + list(RL_ARMS)
            cell["undefined_arms"] = ["B2"]
            cell["decided_by"] = "DEC-021 s.4"
        else:
            cell["unseen_dimension"] = "unseen scale L for a non-F4 family"
            cell["arms_applicable"] = list(ARMS)
            cell["executable_arms"] = list(ARMS)
            cell["undefined_arms"] = []
            cell["decided_by"] = "DEC-021 s.5"
        selected.append(cell)
    selected.sort(key=lambda c: (c["family"], c["scale"], c["seed"]))
    if len(selected) != 5:
        raise SystemExit(f"selected {len(selected)} cells != 5")
    return selected


def row_identity(arm: str, cell: dict[str, Any], identities: dict[str, Any]
                 ) -> dict[str, Any]:
    """Frozen identity for one row; B2 on F4_ski is undefined (DEC-019 class)."""
    family = cell["family"]
    if arm == "B0":
        ident = identities["B0"]
        return {"kind": "config", "config_name": ident["config_name"],
                "config_fingerprint": ident["config_fingerprint"]}
    if arm == "B2":
        entry = identities["B2"]["by_family"].get(family)
        if entry is None:
            return {"kind": "undefined",
                    "reason": ("DEC-019 Option A / DEC-021 s.6: no frozen B2 "
                               "configuration exists for the unseen family "
                               "F4_ski; 0 Spark, no fallback, no substitution"),
                    "executable": False}
        return {"kind": "config", "config_name": entry["config_name"],
                "config_fingerprint": entry["config_fingerprint"]}
    entry = identities["RL"]["arms"][arm]
    return {"kind": "policy", "policy_id": entry["policy_id"],
            "policy_path": entry["policy_path"]}


def build_queue(selected: list[dict[str, Any]], identities: dict[str, Any]
                ) -> list[dict[str, Any]]:
    """Deterministic instance-major queue: (family, scale, seed), arms, rep 1-5."""
    queue: list[dict[str, Any]] = []
    index = 0
    for cell in selected:
        for arm in cell["arms_applicable"]:
            for rep in range(1, REPETITIONS + 1):
                index += 1
                ident = row_identity(arm, cell, identities)
                queue.append({
                    "queue_index": index, "arm": arm,
                    "family": cell["family"], "scale": cell["scale"],
                    "dataset_seed": cell["seed"], "rep": rep, "split": "test",
                    "executable": ident["kind"] != "undefined",
                    "identity": ident,
                    "provenance": {
                        "decision": "DEC-021 (cells/arms/reps/budget)",
                        "spec": "results/evaluation/exp006_spec.json",
                        "split_authority": "sparkrl.experiments.spec.split_of",
                    },
                })
    return queue


def build_document() -> dict[str, Any]:
    """Assemble the sealed pre-execution specification (deterministic)."""
    freeze, consumed = load_frozen()
    universe = build_universe(freeze, consumed)
    identities = resolve_identities(universe)
    selected = select_instances(universe)
    queue = build_queue(selected, identities)

    executable = [r for r in queue if r["executable"]]
    undefined = [r for r in queue if not r["executable"]]
    f4_cells = [c for c in selected if c["family"] == "F4_ski"]
    non_f4 = [c for c in selected if c["family"] != "F4_ski"]

    # DEC-021 s.3 budget identity, recomputed from the queue itself.
    f4_spark = len(f4_cells) * 4 * REPETITIONS       # 4 cells x 4 arms x 5
    non_f4_spark = len(non_f4) * 5 * REPETITIONS     # 1 cell  x 5 arms x 5
    budget = {
        "f4_component": {"cells": len(f4_cells), "arms": 4, "reps": REPETITIONS,
                         "spark_executions": f4_spark,
                         "rule": "4 F4 cells x 4 executable arms (B0+RL-s0/s1/s2)"
                                 " x 5 reps"},
        "non_f4_component": {"cells": len(non_f4), "arms": 5, "reps": REPETITIONS,
                             "spark_executions": non_f4_spark,
                             "rule": "1 non-F4 cell x 5 executable arms "
                                     "(B0+B2+RL-s0/s1/s2) x 5 reps"},
        "planned_spark_executions": f4_spark + non_f4_spark,
        "undefined_rows": len(undefined),
        "total_queue_observations": len(queue),
        "register_scale": ("PLAN s.33 / registry: EXP-006 '~100' runs; 105 "
                           "planned Spark executions is the frozen "
                           "approximately-100 target (DEC-021 s.3). The 36-cell "
                           "universe x 5 reps x all arms would be ~900 rows and "
                           "is NOT this experiment."),
    }
    if budget["planned_spark_executions"] != EXPECTED_EXECUTABLE:
        raise SystemExit("budget spark count != 105")
    if budget["undefined_rows"] != EXPECTED_UNDEFINED:
        raise SystemExit("undefined row count != 20")
    if budget["total_queue_observations"] != EXPECTED_ROWS:
        raise SystemExit("total queue observations != 125")
    counts: dict[str, int] = {}
    for row in queue:
        counts[row["arm"]] = counts.get(row["arm"], 0) + 1

    doc: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "protocol_version": PROTOCOL_VERSION,
        "split": "test",
        "split_policy": ("DESCRIPTIVE generalization study only. The TEST set "
                         "stays frozen; no TEST metric retunes, selects, or "
                         "trains anything; the 3 RL policies are used exactly as "
                         "published before the test set was opened."),
        "purpose": ("DEC-021 s.4: descriptive generalization evaluation of the "
                    "already-trained frozen RL policies against the available "
                    "frozen comparators on previously unseen dimensions. NOT a "
                    "policy-selection, tuning, hyper-parameter-search, "
                    "significance-seeking, or EXP-005-replacement experiment."),
        "authorized_by": {
            "decisions": ["DEC-020", "DEC-021"],
            "execution_authorized": False,
            "authorization_note": ("DEC-021 s.14: freezing this specification "
                                   "does NOT authorize execution. EXP-006 QUEUE "
                                   "FROZEN - EXECUTION NOT AUTHORIZED. A separate "
                                   "experiment-specific authorization entry is "
                                   "required before any Spark run."),
        },
        "repetitions": REPETITIONS,
        "repetitions_basis": ("PLAN s.23 ('all evaluation = 5 repetitions x fixed "
                              "seeds, medians analyzed'); "
                              "sparkrl.evaluation.spec.EVALUATION_REPETITIONS = 5; "
                              "results/evaluation/evaluation_spec.json; EXP-005 "
                              "precedent (results/experiments/exp-005/spec.json)."),
        "candidate_universe": {
            "definition": ("DEC-020 s.B / DEC-021 s.2: the REMAINING already-"
                           "defined and materially available frozen TEST cells. "
                           "This is a candidate pool, NOT the execution queue."),
            "source_artifact": "results/evaluation/test_freeze.json",
            "source_cell_count": 43,
            "consumed_by_exp005": 7,
            "remaining_count": len(universe),
            "correction": ("DEC-021 s.1: F4_ski|large|s3 was consumed by EXP-005 "
                           "and is therefore excluded from the remainder; the "
                           "correct F4 remainder is 12 cells."),
            "cells": universe,
        },
        "selected_cells": {
            "count": len(selected),
            "selection_rule": ("DEC-021 s.4-s.5 deterministic coverage rule, "
                               "declared BEFORE execution and independent of any "
                               "runtime, reward, or TEST outcome."),
            "cells": selected,
        },
        "arms": {
            "executable": list(ARMS),
            "rl_seeds_distinct": True,
            "identities": identities,
            "b3": ("analytic-only, never queued, never executed "
                   "(DEC-016 B / DEC-017 / DEC-021 s.6)"),
        },
        "applicability": {
            "rule": ("Every selected cell runs every arm for which a frozen "
                     "identity exists: B0 and RL-s0/s1/s2 everywhere; B2 only "
                     "where the frozen per-family B2 configuration exists."),
            "b2_undefined_on": ["F4_ski"],
            "per_cell": [{"family": c["family"], "scale": c["scale"],
                          "seed": c["seed"], "arms": c["arms_applicable"],
                          "executable_arms": c["executable_arms"],
                          "undefined_arms": c["undefined_arms"]}
                         for c in selected],
        },
        "queue_ordering": ("Deterministic and non-random: selected cells sorted "
                           "by (family, scale, seed); within a cell the canonical "
                           "arm order " + repr(list(ARMS)) + "; repeats 1-5 "
                           "ascending. No random or outcome-derived order."),
        "incomplete_semantics": ("A cell/arm is COMPLETE only if all 5 planned "
                                 "reps are usable. Fewer than 5 usable reps => "
                                 "INCOMPLETE, excluded from any pooled statistic "
                                 "(DEC-017 item 5). Missing values are never "
                                 "imputed (no zero/mean/worst-case/retry/B1 "
                                 "substitute)."),
        "failure_protocol": ("Failures are first-class observations recorded and "
                             "reported; no retry is added by this specification. "
                             "A failed execution never becomes an undefined row, "
                             "and an undefined row is never reported as a "
                             "failure. F3-large-class spill/sort failures stay "
                             "first-class (DEC-020 s.I, DEC-021 s.9)."),
        "undefined_semantics": ("B2 x F4_ski rows are UNDEFINED-BY-DESIGN "
                                "(DEC-019 Option A class): the row is preserved in "
                                "the queue for accounting, executed 0 times, "
                                "carries config_name=null and fingerprints=null, "
                                "execution_time=null, "
                                "event_log_status=NOT_EXECUTED, and is excluded "
                                "from B2's pooled statistics for those cells. No "
                                "fallback to B1 and no configuration substitution "
                                "is permitted."),
        "sc5": {
            "status": "NOT EVALUABLE",
            "reason": ("DEC-020 s.E / DEC-021 s.10: PLAN s.25's SC5 requires "
                       "'>=50% of its seen relative advantage', and no pre-TEST "
                       "artifact in the repository defines that seen advantage. "
                       "No value is derived from TEST data and no new threshold is "
                       "invented, so SC5 is not evaluable under the current frozen "
                       "definition. EXP-006 therefore yields descriptive "
                       "generalization evidence only."),
        },
        "excluded_from_this_experiment": {
            "b3": "analytic-only (not a TEST arm)",
            "b1_b4": ("not EXP-006 arms - (DEC-021 s.7 lists exactly "
                      "RL-s0/s1/s2 + B0 + B2-where-defined)"),
            "public_dataset": ("never generated and materially unavailable; not "
                               "substituted (DEC-020 s.B, DEC-021 s.11)"),
            "f5_unseen_parameters": ("never generated; not synthesized "
                                     "(DEC-020 s.B, DEC-021 s.11)"),
            "consumed_exp005_instances": sorted(
                [f"{f}|{s}|{k}" for f, s, k in consumed]),
        },
        "no_analysis_rule": ("No statistical or performance conclusion is drawn "
                             "from this specification; it contains no measurement "
                             "and no metric. No winner selection, no arm ranking, "
                             "no inferential test, and no EXP-005 retrofit."),
        "provenance": {
            "decisions": ["DEC-020", "DEC-021", "DEC-019 (B2 undefined class)"],
            "inputs": {
                "test_freeze.json": _sha256_file(TEST_FREEZE),
                "exp005_instances_consumed": ("results/experiments/exp-005/"
                                              "spec.json"),
                "baseline_b0.yaml": _sha256_file(B0_YAML),
                "exp005_rl_arms.json": _sha256_file(RL_MANIFEST),
            },
            "produced_by": "scripts/freeze_exp006.py (pre-execution freeze)",
            "spark_executions": 0,
        },
    }

    doc["queue"] = {
        "ordering": doc["queue_ordering"],
        "count": len(queue),
        "executable": len(executable),
        "undefined": len(undefined),
        "counts_by_arm": counts,
        "rows": queue,
    }
    doc["budget"] = budget
    doc["fingerprints"] = {
        "universe": manifest_fingerprint(universe),
        "selected_cells": manifest_fingerprint(
            [{"family": c["family"], "scale": c["scale"], "seed": c["seed"]}
             for c in selected]),
        "queue": queue_fingerprint(queue),
    }
    doc["total_runs"] = len(queue)
    doc["tail_digest_note"] = ("Reproducibility: re-running this builder on the "
                               "same frozen inputs must reproduce the same "
                               "fingerprints; only created_utc may differ.")
    return seal(doc)


def queue_fingerprint(rows: list[dict[str, Any]]) -> str:
    """sha256 over the queue rows alone (canonical JSON)."""
    canonical = json.dumps(rows, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    verify = "--verify" in args
    doc = build_document()
    fingerprint = doc["fingerprint"]
    rows = doc["queue"]["rows"]

    print(f"{EXPERIMENT_ID} pre-execution specification")
    print(f"  candidate universe      : {doc['candidate_universe']['remaining_count']} cells "
          f"(43 frozen - 7 consumed by EXP-005)")
    print(f"  selected execution cells: {doc['selected_cells']['count']}")
    print(f"  planned Spark executions: {doc['budget']['planned_spark_executions']}")
    print(f"  undefined (B2 x F4) rows: {doc['budget']['undefined_rows']}")
    print(f"  total queue observations: {doc['budget']['total_queue_observations']}")
    print(f"  repetitions             : {doc['repetitions']}")
    print(f"  queue fingerprint       : {doc['fingerprints']['queue']}")
    print(f"  universe fingerprint    : {doc['fingerprints']['universe']}")
    print(f"  artifact fingerprint    : {fingerprint}")
    print(f"  tail row {len(rows)}                : "
          f"{json.dumps(rows[-1], sort_keys=True, separators=(',', ':'))}")
    print("  SC5                     : "
          f"{doc['sc5']['status']}")
    print("  spark executions        : 0 (build only)")

    if verify:
        if not OUT.exists():
            print(f"VERIFY FAILED: {OUT} does not exist")
            return 1
        existing = json.loads(OUT.read_text(encoding="utf-8"))
        if existing.get("fingerprint") != fingerprint:
            print("VERIFY FAILED: stored fingerprint differs from recomputed")
            return 1
        print(f"VERIFY OK: {OUT.name} reproduces bit-identically "
              f"({fingerprint[:16]}...)")
        return 0

    write_artifact(doc, OUT)
    print(f"[WROTE] {OUT}")
    print("EXP-006 QUEUE FROZEN - EXECUTION NOT AUTHORIZED (DEC-021 s.14)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())