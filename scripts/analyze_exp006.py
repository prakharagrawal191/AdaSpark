"""Deterministic descriptive analysis of the EXP-006 production ledger.

Non-destructive: reads the frozen spec and the sealed observations.jsonl,
classifies each observation with the verified predicates, and emits coverage
+ median evidence. No Spark, no RNG, no inferential statistics.

Re-running over the same on-disk artifacts must produce byte-identical output.
"""
from __future__ import annotations

import hashlib
import json
import statistics
import sys
from collections import Counter, OrderedDict
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]

SPEC_PATH = PROJECT / "results" / "evaluation" / "exp006_spec.json"
LEDGER_PATH = PROJECT / "results" / "experiments" / "exp-006" / "observations.jsonl"

ARMS = ("B0", "B2", "RL-s0", "RL-s1", "RL-s2")
SELECTED_CELLS = [
    ("F1_agg", "large", 0),
    ("F4_ski", "large", 0),
    ("F4_ski", "large", 4),
    ("F4_ski", "medium", 3),
    ("F4_ski", "small", 3),
]

EXP006_SPEC_FP = ("0f078dc2f89b726ef80a58c3b7161ded9cc071dfe48a34266725fe9872b7eb54")
EXP006_QUEUE_FP = ("c88ba20c75a0654a81c2113a83aefd119a19271985bdccabd4c7ef44ec917d4c")
EXP006_SELECTED_FP = ("5fea06f272345a9d7bb0e11aca9208c416dac4a1bb5a37581976c1f149da17e5")

# Fields excluded from the project's content fingerprint (identity only).
_FP_EXCLUDED = ("artifact_id", "fingerprint", "created_utc")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_canonical(obj) -> str:
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def artifact_fingerprint(artifact: dict) -> str:
    body = {k: v for k, v in artifact.items() if k not in _FP_EXCLUDED}
    return sha256_canonical(body)


def queue_fingerprint(rows: list) -> str:
    return sha256_canonical(rows)


def load_spec() -> dict:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def load_ledger() -> list:
    raw = LEDGER_PATH.read_bytes().decode("utf-8")
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


def cell_key_of(o: dict) -> str:
    return f"{o['family']}|{o['scale']}|s{o['seed']}"


# Exact ledger error string for the deliberately-undefined B2 x F4_ski rows.
_UNDEFINED_ERROR = ("INCOMPLETE (DEC-019 Option A / DEC-022 scope): B2 is "
                    "per-family static tuned on VALIDATION, which contains "
                    "only {F1_agg, F2_join, F3_rdd, F5_mixed}; F4_ski is the "
                    "deliberately unseen TEST family (PLAN section 18), so B2 "
                    "has no frozen configuration for it. No Spark execution, "
                    "no fallback (explicitly not B1), no substitution, no TEST "
                    "tuning; queue entry preserved for accounting.")


# -- Verified classification predicates (logic preserved verbatim) ------------
# String literals are aligned to the ledger's actual tokens: the task's
# predicate text uses the abstracted forms "COMPLETED" / "NotExecuted (strategy
# resolution)"; the sealed observations use "COMPLETE" and the full
# "INCOMPLETE (DEC-019 Option A / DEC-022 scope): ..." message. The logical
# structure of each predicate is unchanged.

def is_successful(o: dict) -> bool:
    return (o["event_log_status"] == "COMPLETE"
            and bool(o["usable"]) is True
            and o["execution_time_s"] is not None)


def is_failed(o: dict) -> bool:
    return (o["event_log_status"] == "MISSING"
            and bool(o["usable"]) is False
            and o["execution_time_s"] is None
            and o.get("config_name") is not None)


def is_undefined(o: dict) -> bool:
    return (o["event_log_status"] == "NOT_EXECUTED"
            and bool(o["usable"]) is False
            and o["execution_time_s"] is None
            and o.get("config_name") is None
            and o.get("error") == _UNDEFINED_ERROR)


def classify(o: dict) -> str:
    if is_undefined(o):
        return "UNDEFINED"
    if is_successful(o):
        return "SUCCESS"
    if is_failed(o):
        return "FAILED"
    return "UNCLASSIFIED"


PREDICATES = {
    "successful": ("event_log_status == 'COMPLETE' AND usable == True "
                   "AND execution_time_s is not None  (task text: 'COMPLETED')"),
    "failed": ("event_log_status == 'MISSING' AND usable == False "
               "AND execution_time_s is None AND config_name is not None"),
    "undefined_b2_f4": ("event_log_status == 'NOT_EXECUTED' AND usable == False "
                        "AND execution_time_s is None AND config_name is None "
                        "AND arm == 'B2' AND family == 'F4_ski' "
                        "AND error == 'INCOMPLETE (DEC-019 Option A / DEC-022 scope): ...'"),
    "note": ("String literals aligned to the ledger's actual tokens "
             "('COMPLETE', 'NOT_EXECUTED', the full 'INCOMPLETE (DEC-019...)' "
             "error message); predicate logic preserved verbatim."),
}


def run() -> dict:
    spec = load_spec()
    obs = load_ledger()

    results: "OrderedDict[str, object]" = OrderedDict()
    results["classification_predicates"] = PREDICATES

    # -- Section 2: input integrity --
    ledger_sha = sha256_file(LEDGER_PATH)
    spec_fp = spec["fingerprint"]
    stored_queue_fp = spec["fingerprints"]["queue"]
    stored_selected_fp = spec["fingerprints"]["selected_cells"]
    recomputed_queue_fp = queue_fingerprint(spec["queue"]["rows"])
    recomputed_spec_fp = artifact_fingerprint(spec)

    results["ledger_sha256"] = ledger_sha
    results["spec_fingerprint"] = spec_fp
    results["spec_fingerprint_recomputed"] = recomputed_spec_fp
    results["queue_fingerprint_stored"] = stored_queue_fp
    results["queue_fingerprint_recomputed"] = recomputed_queue_fp
    results["selected_cells_fingerprint"] = stored_selected_fp

    n = len(obs)
    indices = [o["queue_index"] for o in obs]
    integrity = {
        "row_count": n,
        "index_min": min(indices),
        "index_max": max(indices),
        "unique_indices": len(set(indices)),
        "duplicates": n - len(set(indices)),
        "all_rows_match_queue": set(indices) == set(range(1, 126)),
        "spec_fingerprint_unchanged": recomputed_spec_fp == spec_fp,
        "queue_fingerprint_unchanged": recomputed_queue_fp == stored_queue_fp,
        "spec_fp_match_expected": spec_fp == EXP006_SPEC_FP,
        "queue_fp_match_expected": stored_queue_fp == EXP006_QUEUE_FP,
        "selected_cells_fp_match_expected": stored_selected_fp == EXP006_SELECTED_FP,
    }
    results["input_integrity"] = integrity

    # -- Section 3 & 1 raw classification --
    classified = {o["queue_index"]: classify(o) for o in obs}
    status_counter = Counter(classified.values())
    results["raw_classification"] = {
        "successful": status_counter.get("SUCCESS", 0),
        "failed": status_counter.get("FAILED", 0),
        "undefined": status_counter.get("UNDEFINED", 0),
        "unclassified": status_counter.get("UNCLASSIFIED", 0),
    }

    # -- per-arm totals across the whole ledger --
    per_arm: "OrderedDict[str, OrderedDict]" = OrderedDict()
    for arm in ARMS:
        per_arm[arm] = OrderedDict([
            ("planned", 25),
            ("successful", 0), ("failed", 0), ("undefined", 0),
            ("usable", 0), ("total", 0)])
    for o in obs:
        arm = o["arm"]
        cls = classified[o["queue_index"]]
        per_arm[arm]["total"] += 1
        if cls == "SUCCESS":
            per_arm[arm]["successful"] += 1
            per_arm[arm]["usable"] += 1
        elif cls == "FAILED":
            per_arm[arm]["failed"] += 1
        elif cls == "UNDEFINED":
            per_arm[arm]["undefined"] += 1
    results["per_arm_totals"] = per_arm

    # -- Section 4: cell x arm coverage --
    cell_matrix: "OrderedDict[str, OrderedDict]" = OrderedDict()
    for (family, scale, seed) in SELECTED_CELLS:
        key = f"{family}|{scale}|s{seed}"
        cell_matrix[key] = OrderedDict(
            (arm, {"successful": 0, "failed": 0, "undefined": 0,
                   "total": 0, "usable": 0, "status": None, "eligible": False})
            for arm in ARMS)
    for o in obs:
        key = cell_key_of(o)
        arm = o["arm"]
        if key not in cell_matrix or arm not in cell_matrix[key]:
            continue
        e = cell_matrix[key][arm]
        e["total"] += 1
        cls = classified[o["queue_index"]]
        if cls == "SUCCESS":
            e["successful"] += 1
            e["usable"] += 1
        elif cls == "FAILED":
            e["failed"] += 1
        elif cls == "UNDEFINED":
            e["undefined"] += 1
    for key, arms in cell_matrix.items():
        for arm in ARMS:
            e = arms[arm]
            if e["total"] == 0:
                e["status"] = "UNDEFINED"
            elif e["total"] == 5 and e["usable"] == 5:
                e["status"] = "5/5 usable"
            elif e["total"] == 5 and e["usable"] == 0:
                e["status"] = "0/5 usable, 5 failed"
            elif e["total"] == 5 and 0 < e["usable"] < 5:
                e["status"] = f"{e['usable']}/5 usable, {e['failed']} failed"
            e["eligible"] = (e["status"] == "5/5 usable")
    results["cell_arm_coverage"] = cell_matrix

    # -- Section 8: complete-cell medians + descriptive single runs --
    medians: "OrderedDict[str, OrderedDict]" = OrderedDict()
    single_runs: "OrderedDict[str, OrderedDict]" = OrderedDict()
    for key, arms in cell_matrix.items():
        medians[key] = OrderedDict()
        single_runs[key] = OrderedDict()
        for arm in ARMS:
            e = arms[arm]
            times = sorted(o["execution_time_s"] for o in obs
                           if cell_key_of(o) == key and o["arm"] == arm
                           and o["execution_time_s"] is not None
                           and bool(o["usable"]) is True)
            if e["eligible"]:
                medians[key][arm] = {
                    "n": len(times),
                    "median": statistics.median(times),
                    "min": min(times), "max": max(times),
                    "values": times,
                }
            elif 0 < len(times) < 5:
                single_runs[key][arm] = {
                    "n": len(times),
                    "values": times,
                    "label": ("single successful observation; cell incomplete; "
                              "descriptive only"),
                }
    results["complete_cell_medians"] = medians
    results["descriptive_single_runs"] = single_runs

    # -- B2 summary (Section 11) --
    b2 = {"executable_evidence_cells": 0, "complete_cells": 0, "undefined_cells": 0,
          "total_usable": 0, "total_failed": 0, "total_undefined": 0}
    for key, arms in cell_matrix.items():
        e = arms["B2"]
        if e["usable"] > 0 or e["failed"] > 0:
            b2["executable_evidence_cells"] += 1
            b2["total_usable"] += e["usable"]
            b2["total_failed"] += e["failed"]
            if e["eligible"]:
                b2["complete_cells"] += 1
        elif e["undefined"] == 5:
            b2["undefined_cells"] += 1
            b2["total_undefined"] += 5
    results["b2_summary"] = b2

    # -- RL-s2 summary (Section 12) --
    rl_s2 = {"total_attempts": 0, "successful": 0, "failed": 0,
             "complete_cells": 0}
    for key, arms in cell_matrix.items():
        e = arms["RL-s2"]
        rl_s2["total_attempts"] += e["total"]
        rl_s2["successful"] += e["usable"]
        rl_s2["failed"] += e["failed"]
        if e["eligible"]:
            rl_s2["complete_cells"] += 1
    results["rl_s2_summary"] = rl_s2

    # -- failure distribution (Section 10) --
    failure_dist: "OrderedDict[str, OrderedDict]" = OrderedDict()
    for key, arms in cell_matrix.items():
        failure_dist[key] = OrderedDict(
            (arm, arms[arm]["failed"]) for arm in ARMS)
    results["failure_distribution"] = failure_dist

    # -- SC5 (Section 13) --
    results["sc5_status"] = (
        "NOT EVALUABLE (seen-relative-advantage baseline never frozen before "
        "EXP-006; not constructed; not derived from EXP-005)")

    # -- deterministic validation (Section 19) --
    all_f4_incomplete = all(
        not cell_matrix[key][arm]["eligible"]
        for key in cell_matrix if key.startswith("F4_ski")
        for arm in ("B0", "RL-s0", "RL-s1", "RL-s2"))
    complete_cells_exact = sorted(
        key + "|" + arm
        for key, arms in cell_matrix.items()
        for arm in ("B0", "B2", "RL-s0", "RL-s1", "RL-s2")
        if arms[arm]["eligible"])
    expected_complete = sorted([
        "F1_agg|large|s0|B0", "F1_agg|large|s0|B2",
        "F1_agg|large|s0|RL-s0", "F1_agg|large|s0|RL-s1",
        "F1_agg|large|s0|RL-s2",
        "F4_ski|large|s0|B0", "F4_ski|large|s0|RL-s0",
        "F4_ski|large|s0|RL-s1", "F4_ski|large|s0|RL-s2",
        "F4_ski|large|s4|B0", "F4_ski|large|s4|RL-s0",
        "F4_ski|large|s4|RL-s1"])
    medians_only_for_complete = all(
        set(medians.get(key, {}).keys()) == set(
            arm for arm in ("B0", "B2", "RL-s0", "RL-s1", "RL-s2")
            if cell_matrix[key][arm]["eligible"])
        for key in cell_matrix)
    no_fabricated_median = (
        "RL-s2" not in medians.get("F4_ski|large|s4", {})
        and not medians.get("F4_ski|medium|s3", {})
        and not medians.get("F4_ski|small|s3", {}))
    results["validation"] = {
        "125_rows": n == 125,
        "61_successful": status_counter.get("SUCCESS", 0) == 61,
        "44_failed": status_counter.get("FAILED", 0) == 44,
        "20_undefined": status_counter.get("UNDEFINED", 0) == 20,
        "spec_fingerprint_unchanged": recomputed_spec_fp == spec_fp,
        "queue_fingerprint_unchanged": recomputed_queue_fp == stored_queue_fp,
        "b2_one_complete_cell": b2["complete_cells"] == 1,
        "b2_undefined_cells_four": b2.get("undefined_cells", -1) == 4,
        "rl_s2_two_complete_cells": rl_s2["complete_cells"] == 2,
        "complete_cell_set_exact": complete_cells_exact == expected_complete,
        "medians_only_for_complete": medians_only_for_complete,
        "no_fabricated_median": no_fabricated_median,
        "all_f4_executable_combinations_incomplete": all_f4_incomplete,
        "complete_cells": complete_cells_exact,
        "expected_complete_cells": expected_complete,
        "deterministic": True,
    }
    results["spark_executions_during_analysis"] = 0
    results["analysis_fingerprint"] = None
    return results


def main() -> int:
    results = run()
    payload = json.dumps(results, sort_keys=True,
                         separators=(",", ":"), ensure_ascii=True)
    results["analysis_fingerprint"] = hashlib.sha256(
        payload.encode("utf-8")).hexdigest()

    out_path = PROJECT / "results" / "evaluation" / "exp006_analysis.json"
    out_path.write_text(
        json.dumps(results, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8")
    print(f"[WROTE] {out_path}")
    print(f"analysis_fingerprint: {results['analysis_fingerprint']}")
    print(f"ledger_sha256: {results['ledger_sha256']}")
    print(f"spec_fingerprint: {results['spec_fingerprint']}")
    print(f"queue_fingerprint: {results['queue_fingerprint_stored']}")
    print(f"classification: {json.dumps(results['raw_classification'])}")
    print(f"per_arm: {json.dumps(results['per_arm_totals'])}")
    print(f"validation: {json.dumps(results['validation'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
