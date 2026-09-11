"""EXP-002 analysis and sensitivity-gate evaluation (Day 22).

Pure, deterministic analysis over STORED run records. This module never executes
Spark, never re-measures anything, and contains no free parameters: every threshold
comes from the pre-registered spec (``experiments/exp002.yaml``), which was fixed
before the first observation.

What it computes
----------------
* valid / invalid partition of the observations (validity = the Day-19 ``usable``
  rule; invalid runs are reported, never dropped);
* per-(family, scale, configuration) summary of ``execution_time_s`` - the frozen
  Day-3 runner clock, warm-up excluded. No other timing is ever substituted;
* B0-relative absolute and relative differences;
* per-panel configuration spread, with and without the B0 reference;
* repeatability: within-configuration CV, a pooled noise estimate, per-repetition
  spreads, and the rank agreement of the configuration ordering between repetitions;
* the pre-registered sensitivity gate.

Sensitivity criterion (PLAN H1 / SC1 / section 33 / risk R2)
-----------------------------------------------------------
H1: "on shuffle/join-heavy workloads, the action space spans >=10% median
execution-time difference on this hardware"; EXP-002 acceptance: ">=10% spread on
>=2 families"; R2 pivot trigger: "EXP-002 effect <10%".

Operationalised, with no added freedom:

    spread_relative(panel) = (max_c median_c - min_c median_c) / min_c median_c
        over c in the 12 VARIED configurations (scope='varied_only', because H1
        speaks about the action space; B0 is the reference, not a candidate).

    panel is SENSITIVE iff
        panel is complete (every configuration has >= min_valid_runs_per_config
                           valid observations)
        AND spread_relative >= min_relative_spread            (= 0.10, PLAN H1)
        AND spread_relative >  pooled_within_config_cv        (noise guard)

    family is SENSITIVE iff sensitive at >= 1 of its measured scales (family_rule)
    GATE PASSES iff n_families_sensitive >= min_families      (= 2, PLAN section 33)

The noise guard exists because a spread smaller than ordinary run-to-run variation
is not evidence of a configuration effect. PLAN risk R3 / EXP-001 sets the project's
noise criterion at CV <= 10%; EXP-001 was not executed (see the audit document), so
the noise band is estimated from EXP-002's own within-configuration repetitions and
is reported explicitly rather than assumed.

Deliberately NOT done: no significance test is run. With 2 repetitions per cell the
assumptions of a paired rank test over configurations are not met, and the task
forbids decorative statistics. Repeatability is reported directly instead.
"""
from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

from sparkrl.experiments.grid import grid_fingerprint
from sparkrl.experiments.spec import EXPERIMENT_ID, ExperimentSpec

ANALYSIS_VERSION = "exp002-analysis/v1"
GATE_SCHEMA_VERSION = "exp002-gate/v1"

PASS, FAIL = "PASS", "FAIL"
_METRIC = "execution_time_s"   # frozen Day-3 authoritative timing; never substituted


# --------------------------------------------------------------------------
# observations
# --------------------------------------------------------------------------
def is_valid_record(record: dict[str, Any]) -> bool:
    """A record is a valid measured observation iff the Day-19 usable rule holds.

    ``usable`` already encodes: success AND execution_time_s present AND event log
    COMPLETE AND a workload result signature. The status must agree, so a record
    cannot be counted by claiming COMPLETE while its metrics say otherwise.
    """
    metrics = record.get("metrics") or {}
    return bool(metrics.get("usable")) and record.get("status") == "COMPLETED"


def observation(record: dict[str, Any]) -> dict[str, Any]:
    """Flatten a stored record into the fields the analysis uses."""
    spec = record.get("run_spec") or {}
    metrics = record.get("metrics") or {}
    prov = record.get("provenance") or {}
    return {
        "run_id": spec.get("run_id") or metrics.get("run_id"),
        "family": spec.get("family") or metrics.get("family"),
        "scale": spec.get("scale") or metrics.get("scale"),
        "seed": spec.get("seed") if spec.get("seed") is not None else metrics.get("seed"),
        "rep": spec.get("rep"),
        "config_name": spec.get("config_name"),
        "config_grid_index": spec.get("config_grid_index"),
        "config_fingerprint": spec.get("config_fingerprint"),
        "is_reference": bool(spec.get("config_is_reference")),
        "split": spec.get("split"),
        "status": record.get("status"),
        "execution_time_s": metrics.get(_METRIC),
        "execution_time_source": metrics.get("execution_time_source"),
        "usable": bool(metrics.get("usable")),
        "success": bool(metrics.get("success")),
        "timeout": bool(metrics.get("timeout")),
        "error": metrics.get("error"),
        "event_log_status": metrics.get("event_log_status"),
        "task_count": metrics.get("task_count"),
        "failed_task_count": metrics.get("failed_task_count"),
        "shuffle_read_bytes": metrics.get("shuffle_read_bytes"),
        "shuffle_write_bytes": metrics.get("shuffle_write_bytes"),
        "total_spill_bytes": metrics.get("total_spill_bytes"),
        "task_duration_cv": metrics.get("task_duration_cv"),
        "sysmon_sampled": bool(metrics.get("sysmon_sampled")),
        "applied_mismatches": prov.get("applied_mismatches") or [],
    }


def partition_observations(records: Iterable[dict[str, Any]]
                           ) -> tuple[list[dict], list[dict]]:
    """Split stored records into (valid, invalid) observations. Nothing is dropped."""
    valid, invalid = [], []
    for record in records:
        obs = observation(record)
        (valid if is_valid_record(record) else invalid).append(obs)
    valid.sort(key=lambda o: str(o["run_id"]))
    invalid.sort(key=lambda o: str(o["run_id"]))
    return valid, invalid


# --------------------------------------------------------------------------
# descriptive statistics
# --------------------------------------------------------------------------
def _round(value, digits: int = 6):
    return None if value is None else round(float(value), digits)


def summarize_times(times: Sequence[float]) -> dict[str, Any]:
    """n / median / mean / std(ddof=1) / CV / min / max. None where undefined."""
    values = [float(t) for t in times if t is not None]
    if not values:
        return {"n": 0, "median_s": None, "mean_s": None, "std_s": None,
                "cv": None, "min_s": None, "max_s": None}
    mean = statistics.mean(values)
    std = statistics.stdev(values) if len(values) > 1 else None
    return {
        "n": len(values),
        "median_s": _round(statistics.median(values)),
        "mean_s": _round(mean),
        "std_s": _round(std),
        "cv": _round(std / mean) if (std is not None and mean) else None,
        "min_s": _round(min(values)),
        "max_s": _round(max(values)),
    }


def spearman_rho(a: Sequence[float], b: Sequence[float]) -> float | None:
    """Spearman rank correlation (stdlib only). None when undefined.

    Ties receive average ranks; the general Pearson-on-ranks form is used so ties
    do not silently bias the result.
    """
    if len(a) != len(b) or len(a) < 2:
        return None

    def ranks(xs: Sequence[float]) -> list[float]:
        order = sorted(range(len(xs)), key=lambda i: xs[i])
        out = [0.0] * len(xs)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                out[order[k]] = avg
            i = j + 1
        return out

    ra, rb = ranks(a), ranks(b)
    ma, mb = statistics.mean(ra), statistics.mean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    da = math.sqrt(sum((x - ma) ** 2 for x in ra))
    db = math.sqrt(sum((y - mb) ** 2 for y in rb))
    if da == 0 or db == 0:
        return None
    return _round(num / (da * db))


def pooled_within_config_cv(times_by_config: dict[str, list[float]]) -> float | None:
    """Pooled within-configuration coefficient of variation (run-to-run noise).

    pooled_sd = sqrt( sum_c (n_c - 1) s_c^2 / sum_c (n_c - 1) ), expressed relative
    to the grand mean of the contributing observations. Returns None when no
    configuration has repeated observations.
    """
    num, dof, contributing = 0.0, 0, []
    for values in times_by_config.values():
        vals = [float(v) for v in values if v is not None]
        if len(vals) < 2:
            continue
        var = statistics.variance(vals)
        num += (len(vals) - 1) * var
        dof += len(vals) - 1
        contributing.extend(vals)
    if dof == 0 or not contributing:
        return None
    grand_mean = statistics.mean(contributing)
    if not grand_mean:
        return None
    return _round(math.sqrt(num / dof) / grand_mean)


def relative_spread(medians: dict[str, float]) -> dict[str, Any]:
    """(max - min)/min over configuration medians, with the arg-extrema named."""
    usable = {name: float(v) for name, v in medians.items() if v is not None}
    if len(usable) < 2:
        return {"n_configs": len(usable), "min_s": None, "max_s": None,
                "relative": None, "absolute_s": None, "argmin": None, "argmax": None}
    argmin = min(usable, key=lambda k: usable[k])
    argmax = max(usable, key=lambda k: usable[k])
    lo, hi = usable[argmin], usable[argmax]
    return {
        "n_configs": len(usable),
        "min_s": _round(lo), "max_s": _round(hi),
        "relative": _round((hi - lo) / lo) if lo else None,
        "absolute_s": _round(hi - lo),
        "argmin": argmin, "argmax": argmax,
    }


# --------------------------------------------------------------------------
# panels
# --------------------------------------------------------------------------
def build_panels(valid: Sequence[dict], invalid: Sequence[dict],
                 spec: ExperimentSpec) -> list[dict[str, Any]]:
    """One panel per (family, scale): the unit at which sensitivity is judged."""
    gate = spec.gate
    min_valid = int(gate.get("min_valid_runs_per_config", 1))
    require_complete = bool(gate.get("require_complete_panel", True))
    min_spread = float(gate["min_relative_spread"])
    scope = gate["scope"]

    by_cell: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for obs in valid:
        by_cell[(obs["family"], obs["scale"])].append(obs)
    invalid_by_cell: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for obs in invalid:
        invalid_by_cell[(obs["family"], obs["scale"])].append(obs)

    grid_names = [p.name for p in spec.grid]
    reference = next(p.name for p in spec.grid if p.is_reference)
    varied_names = [p.name for p in spec.grid if not p.is_reference]

    panels: list[dict[str, Any]] = []
    for family in spec.families:
        for scale in spec.scales:
            cell = by_cell.get((family, scale), [])
            times_by_config: dict[str, list[float]] = {n: [] for n in grid_names}
            reps_by_config: dict[str, dict[int, float]] = {n: {} for n in grid_names}
            for obs in cell:
                name = obs["config_name"]
                if name not in times_by_config:
                    continue  # a configuration outside the pre-registered grid
                times_by_config[name].append(float(obs["execution_time_s"]))
                if obs["rep"] is not None:
                    reps_by_config[name][int(obs["rep"])] = float(obs["execution_time_s"])

            stats = {n: summarize_times(v) for n, v in times_by_config.items()}
            b0_median = stats[reference]["median_s"]

            configs = []
            for point in spec.grid:
                s = stats[point.name]
                rel = abs_ = None
                if b0_median not in (None, 0) and s["median_s"] is not None:
                    abs_ = _round(s["median_s"] - b0_median)
                    rel = _round((s["median_s"] - b0_median) / b0_median)
                configs.append({
                    "name": point.name,
                    "grid_index": point.grid_index,
                    "is_reference": point.is_reference,
                    "parallelism": point.parallelism,
                    "shuffle_partitions": point.shuffle_partitions,
                    "fingerprint": point.fingerprint(),
                    "n_valid": s["n"],
                    "median_s": s["median_s"], "mean_s": s["mean_s"],
                    "std_s": s["std_s"], "cv": s["cv"],
                    "min_s": s["min_s"], "max_s": s["max_s"],
                    "rel_diff_from_b0": rel, "abs_diff_from_b0_s": abs_,
                })

            missing = [n for n in grid_names if stats[n]["n"] < min_valid]
            complete = not missing
            varied_medians = {n: stats[n]["median_s"] for n in varied_names}
            all_medians = {n: stats[n]["median_s"] for n in grid_names}
            spread_varied = relative_spread(varied_medians)
            spread_all = relative_spread(all_medians)
            noise = pooled_within_config_cv(
                {n: v for n, v in times_by_config.items() if n in varied_names})
            per_config_cvs = [stats[n]["cv"] for n in varied_names
                              if stats[n]["cv"] is not None]

            # Repeatability: spread computed inside each repetition block, plus the
            # rank agreement of the configuration ordering between repetitions.
            per_rep, rep_vectors = {}, {}
            all_reps = sorted({r for m in reps_by_config.values() for r in m})
            for rep in all_reps:
                medians_this_rep = {n: reps_by_config[n].get(rep) for n in varied_names}
                per_rep[str(rep)] = relative_spread(medians_this_rep)
                rep_vectors[rep] = medians_this_rep
            rank_agreement = None
            if len(all_reps) >= 2:
                r1, r2 = all_reps[0], all_reps[1]
                shared = [n for n in varied_names
                          if rep_vectors[r1].get(n) is not None
                          and rep_vectors[r2].get(n) is not None]
                if len(shared) >= 2:
                    rank_agreement = spearman_rho(
                        [rep_vectors[r1][n] for n in shared],
                        [rep_vectors[r2][n] for n in shared])

            observed = (spread_varied if scope == "varied_only" else spread_all)["relative"]
            reasons: list[str] = []
            if not complete and require_complete:
                reasons.append(
                    f"panel incomplete: {len(missing)} configuration(s) without "
                    f"{min_valid} valid observation(s): {missing}")
            if observed is None:
                reasons.append("configuration spread undefined (insufficient medians)")
            else:
                if observed < min_spread:
                    reasons.append(
                        f"spread {observed:.4f} < required {min_spread:.2f}")
                if noise is not None and observed <= noise:
                    reasons.append(
                        f"spread {observed:.4f} does not exceed pooled within-"
                        f"configuration noise {noise:.4f}")
                elif noise is None:
                    reasons.append(
                        "noise guard not evaluable: no configuration has repeated "
                        "valid observations")

            sensitive = (observed is not None
                         and (complete or not require_complete)
                         and observed >= min_spread
                         and noise is not None and observed > noise)
            if sensitive:
                reasons = [f"spread {observed:.4f} >= {min_spread:.2f} and exceeds "
                           f"pooled within-configuration noise {noise:.4f}"]

            panels.append({
                "family": family, "scale": scale,
                "complete": complete,
                "missing_configs": missing,
                "n_valid": len(cell),
                "n_invalid": len(invalid_by_cell.get((family, scale), [])),
                "configs": configs,
                "b0_median_s": b0_median,
                "t_ref_s": b0_median,   # PLAN sections 15/33: T_ref = default-config median
                "spread": {"varied_only": spread_varied,
                           "including_reference": spread_all},
                "observed_spread": observed,
                "observed_spread_scope": scope,
                "pooled_within_config_cv": noise,
                "median_within_config_cv": (_round(statistics.median(per_config_cvs))
                                            if per_config_cvs else None),
                "per_rep_spread": per_rep,
                "rep_rank_agreement_spearman": rank_agreement,
                "sensitive": sensitive,
                "reasons": reasons,
            })
    return panels


# --------------------------------------------------------------------------
# gate
# --------------------------------------------------------------------------
def evaluate_gate(panels: Sequence[dict], spec: ExperimentSpec) -> dict[str, Any]:
    """Deterministic PASS/FAIL from the panels and the pre-registered criterion."""
    gate = spec.gate
    min_families = int(gate["min_families"])
    family_rule = gate.get("family_rule", "any_scale")

    by_family: dict[str, list[dict]] = defaultdict(list)
    for panel in panels:
        by_family[panel["family"]].append(panel)

    sensitive_families, family_detail = [], {}
    for family in spec.families:
        fam_panels = by_family.get(family, [])
        hits = [p for p in fam_panels if p["sensitive"]]
        is_sensitive = (bool(hits) if family_rule == "any_scale"
                        else bool(fam_panels) and len(hits) == len(fam_panels))
        if is_sensitive:
            sensitive_families.append(family)
        family_detail[family] = {
            "sensitive": is_sensitive,
            "sensitive_scales": [p["scale"] for p in hits],
            "evaluated_scales": [p["scale"] for p in fam_panels],
            "spread_by_scale": {p["scale"]: p["observed_spread"] for p in fam_panels},
        }

    n_sensitive = len(sensitive_families)
    passed = n_sensitive >= min_families

    reasons: list[str] = []
    if passed:
        reasons.append(
            f"{n_sensitive} workload famil{'y' if n_sensitive == 1 else 'ies'} "
            f"({', '.join(sensitive_families)}) show a configuration spread of at least "
            f"{float(gate['min_relative_spread']):.0%} in median {_METRIC} that also "
            f"exceeds pooled within-configuration noise; the criterion requires "
            f"{min_families}.")
    else:
        reasons.append(
            f"only {n_sensitive} famil{'y' if n_sensitive == 1 else 'ies'} met the "
            f"sensitivity criterion; {min_families} required.")
        for family in spec.families:
            for panel in by_family.get(family, []):
                if not panel["sensitive"]:
                    reasons.append(
                        f"{family}/{panel['scale']}: " + "; ".join(panel["reasons"]))

    incomplete = [f"{p['family']}/{p['scale']}" for p in panels if not p["complete"]]
    if incomplete:
        reasons.append(
            "incomplete panels (not evaluable as sensitive): " + ", ".join(incomplete))

    return {
        "criteria": {
            "criterion_id": gate.get("criterion_id"),
            "source": "PLAN H1 / SC1 / section 33 / risk R2 (pre-registered)",
            "metric": _METRIC,
            "statistic": gate.get("statistic", "median"),
            "min_relative_spread": float(gate["min_relative_spread"]),
            "min_families": min_families,
            "scope": gate["scope"],
            "family_rule": family_rule,
            "noise_rule": gate.get("noise_rule"),
            "min_valid_runs_per_config": int(gate.get("min_valid_runs_per_config", 1)),
            "require_complete_panel": bool(gate.get("require_complete_panel", True)),
        },
        "families": family_detail,
        "families_sensitive": sensitive_families,
        "n_families_sensitive": n_sensitive,
        "result": PASS if passed else FAIL,
        "reasons": reasons,
    }


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------
def build_report(records: Sequence[dict[str, Any]], spec: ExperimentSpec,
                 generated_utc: str | None = None,
                 code_version: str | None = None) -> dict[str, Any]:
    """The full machine-readable EXP-002 analysis + gate result.

    Deterministic: identical records + identical spec produce byte-identical JSON,
    apart from the explicitly supplied ``generated_utc`` / ``code_version``
    provenance fields.
    """
    valid, invalid = partition_observations(records)
    panels = build_panels(valid, invalid, spec)
    gate = evaluate_gate(panels, spec)

    planned = {r.run_id for r in spec.plan()}
    seen = {o["run_id"] for o in valid} | {o["run_id"] for o in invalid}
    missing = sorted(planned - seen)
    unexpected = sorted(seen - planned)

    breakdown: dict[str, int] = defaultdict(int)
    for obs in invalid:
        breakdown[str(obs["status"])] += 1

    spec_prints = sorted({r.get("spec_fingerprint") for r in records
                          if r.get("spec_fingerprint")})
    grid_prints = sorted({r.get("grid_fingerprint") for r in records
                          if r.get("grid_fingerprint")})

    return {
        "schema_version": GATE_SCHEMA_VERSION,
        "analysis_version": ANALYSIS_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "generated_utc": generated_utc or datetime.now(timezone.utc).isoformat(),
        "code_version": code_version,
        "spec_fingerprint": spec.fingerprint(),
        "grid_fingerprint": grid_fingerprint(spec.grid),
        "record_spec_fingerprints": spec_prints,
        "record_grid_fingerprints": grid_prints,
        "spec_fingerprint_consistent": spec_prints in ([], [spec.fingerprint()]),
        "metric": _METRIC,
        "metric_note": ("execution_time_s is the frozen Day-3 runner clock with "
                        "warm-up excluded; no other timing is substituted."),
        "execution": {
            "planned_runs": len(planned),
            "records_found": len(records),
            "valid": len(valid),
            "invalid": len(invalid),
            "missing": len(missing),
            "unexpected": len(unexpected),
            "invalid_breakdown": dict(sorted(breakdown.items())),
            "missing_run_ids": missing,
            "unexpected_run_ids": unexpected,
            "invalid_runs": [
                {"run_id": o["run_id"], "family": o["family"], "scale": o["scale"],
                 "config_name": o["config_name"], "rep": o["rep"],
                 "status": o["status"], "timeout": o["timeout"],
                 "event_log_status": o["event_log_status"],
                 "applied_mismatches": o["applied_mismatches"],
                 "error": o["error"]}
                for o in invalid],
        },
        "configurations": [p.to_dict() for p in spec.grid],
        "workloads": list(spec.families),
        "scales": list(spec.scales),
        "seeds": list(spec.seeds),
        "repetitions": spec.repetitions,
        "aqe_enabled": spec.aqe_enabled,
        "split": spec.to_dict()["split"],
        "t_ref_calibration": {
            f"{p['family']}|{p['scale']}": p["t_ref_s"] for p in panels},
        "panels": panels,
        "sensitivity": {
            "families_sensitive": gate["families_sensitive"],
            "n_families_sensitive": gate["n_families_sensitive"],
            "spread_by_panel": {f"{p['family']}|{p['scale']}": p["observed_spread"]
                                for p in panels},
            "noise_by_panel": {f"{p['family']}|{p['scale']}":
                               p["pooled_within_config_cv"] for p in panels},
        },
        "gate": gate,
    }


def report_json(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, sort_keys=True)


def render_summary(report: dict[str, Any]) -> str:
    """Human-readable summary, generated from the same report object as gate.json."""
    out: list[str] = []
    ex = report["execution"]
    gate = report["gate"]
    out.append(f"# EXP-002 Configuration-Sensitivity Study - Analysis Summary\n")
    out.append(f"- analysis version : {report['analysis_version']}")
    out.append(f"- generated (UTC)  : {report['generated_utc']}")
    out.append(f"- spec fingerprint : {report['spec_fingerprint']}")
    out.append(f"- grid fingerprint : {report['grid_fingerprint']}")
    out.append(f"- metric           : {report['metric']} ({report['metric_note']})")
    out.append(f"- AQE              : {'ON' if report['aqe_enabled'] else 'OFF'}\n")

    out.append("## Execution\n")
    out.append(f"| planned | records | valid | invalid | missing |")
    out.append(f"|---|---|---|---|---|")
    out.append(f"| {ex['planned_runs']} | {ex['records_found']} | {ex['valid']} "
               f"| {ex['invalid']} | {ex['missing']} |\n")
    if ex["invalid_breakdown"]:
        out.append(f"Invalid breakdown: {ex['invalid_breakdown']}\n")

    out.append("## Per-panel configuration sensitivity\n")
    out.append("| family | scale | complete | n valid | spread (varied) | "
               "pooled noise CV | rep rank rho | sensitive |")
    out.append("|---|---|---|---|---|---|---|---|")
    for p in report["panels"]:
        spread = p["observed_spread"]
        noise = p["pooled_within_config_cv"]
        rho = p["rep_rank_agreement_spearman"]
        out.append(
            f"| {p['family']} | {p['scale']} | {'yes' if p['complete'] else 'NO'} "
            f"| {p['n_valid']} | {'n/a' if spread is None else f'{spread:.1%}'} "
            f"| {'n/a' if noise is None else f'{noise:.2%}'} "
            f"| {'n/a' if rho is None else f'{rho:.2f}'} "
            f"| {'YES' if p['sensitive'] else 'no'} |")
    out.append("")

    for p in report["panels"]:
        if p["b0_median_s"] is None and p["n_valid"] == 0:
            continue
        out.append(f"### {p['family']} / {p['scale']}\n")
        b0_txt = ("n/a" if p["b0_median_s"] is None
                  else format(p["b0_median_s"], ".3f") + " s")
        out.append(f"B0 median (T_ref) = {b0_txt}\n")
        out.append("| config | idx | n | median s | mean s | CV | vs B0 |")
        out.append("|---|---|---|---|---|---|---|")
        for c in p["configs"]:
            med = "n/a" if c["median_s"] is None else format(c["median_s"], ".3f")
            mean = "n/a" if c["mean_s"] is None else format(c["mean_s"], ".3f")
            cv = "n/a" if c["cv"] is None else format(c["cv"], ".3f")
            rel = ("n/a" if c["rel_diff_from_b0"] is None
                   else format(c["rel_diff_from_b0"], "+.1%"))
            idx = "ref" if c["is_reference"] else str(c["grid_index"])
            out.append(f"| {c['name']} | {idx} | {c['n_valid']} | {med} | {mean} "
                       f"| {cv} | {rel} |")
        out.append("")
        for reason in p["reasons"]:
            out.append(f"- {reason}")
        out.append("")

    out.append("## Sensitivity gate\n")
    crit = gate["criteria"]
    out.append(f"Criterion ({crit['criterion_id']}, {crit['source']}): relative spread of "
               f"per-configuration median {crit['metric']} across the "
               f"{crit['scope']} configuration set must be >= "
               f"{crit['min_relative_spread']:.0%} and must exceed pooled within-"
               f"configuration noise, on at least {crit['min_families']} workload "
               f"families ({crit['family_rule']}).\n")
    out.append(f"**RESULT: {gate['result']}**\n")
    for reason in gate["reasons"]:
        out.append(f"- {reason}")
    out.append("")
    if ex["invalid_runs"]:
        out.append("## Invalid / failed observations (recorded, never dropped)\n")
        out.append("| run_id | status | event log | error |")
        out.append("|---|---|---|---|")
        for r in ex["invalid_runs"]:
            err = (r["error"] or "")[:140].replace("|", "/").replace("\n", " ")
            out.append(f"| {r['run_id']} | {r['status']} | {r['event_log_status']} "
                       f"| {err} |")
        out.append("")
    return "\n".join(out)
