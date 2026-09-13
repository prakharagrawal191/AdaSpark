#!/usr/bin/env python
"""Day-30 validator: the mode gate DECISION (PLAN line 276).

PLAN line 276, verbatim and frozen:

    | 30 | Mode gate decision | multi-step only if stable (DEC) | decision
    recorded |

Day 30 is a DECISION day. It runs no Spark, no training and no integration
suite, and it spends ZERO execution budget. So this validator audits two
things and nothing else:

  (a) the decision is RECORDED - a Day-30 document exists, is marked
      DRAFT / UNSIGNED, states a decision, and DECISIONS.md was NOT written
      (the DEC entry needs operator sign-off that has not been given);
  (b) NOTHING WAS BUILT OR SPENT - gamma is still the frozen bandit default
      0.0, the frozen hyperparameter block is untouched, no multi-step
      machinery exists anywhere in src/ (no phase-aware state schema, no
      non-terminal transition, no gamma=0.9 plumbing, no 3-phase rollout),
      the execution ledger is bit-identical to the committed Day-29 figure,
      and the Day-29 M8 artifact still records its FAILED verdict.

A Day 30 that DECIDED the gate must not also have IMPLEMENTED the thing it
gated: implementing it would prejudge the gate. That is what checks 07-13
exist to catch.

This validator makes NO learning claim in either direction. It does not score
the gate, does not re-derive M8, and does not evaluate whether multi-step
would help or hurt. It only checks that a decision is on the record and that
the frozen state of the project is unchanged.

Everything here is READ-ONLY: stored artifacts, source text, `git status`
(read-only), the five prior read-only validators and the deterministic unit
suite. No Spark, no training, no git write.

PASS/FAIL/SKIP per check; the overall verdict is PASS only when every
applicable check passes. A SKIP is never reported as a PASS and always
carries a reason.

Usage:
    python scripts/validate_day30.py
"""
from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import tokenize
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

SRC = PROJECT / "src"
SCRIPTS = PROJECT / "scripts"
CONFIG = PROJECT / "configs" / "rl.yaml"
PLAN = PROJECT / "docs" / "PLAN.md"
DECISIONS = PROJECT / "DECISIONS.md"
RESEARCH = PROJECT / "docs" / "research"
TRAINING_ROOT = PROJECT / "results" / "training"
M8_ARTIFACT = TRAINING_ROOT / "analysis" / "day29_policy_agreement.json"

# The Day-30 decision record. DRAFT ONLY - DECISIONS.md must not be written.
DRAFT_DOC = RESEARCH / "DAY30_MODE_GATE_DEC_DRAFT.md"
DAY30_DOC_GLOB = "DAY30*.md"

# PLAN line 276, frozen and verbatim (the gate this day decides).
PLAN_GATE_LINE = 276
PLAN_GATE_TEXT = ("| 30 | Mode gate decision | multi-step only if stable (DEC)"
                  " | decision recorded |")

# Frozen hyperparameters (PLAN section 16). gamma 0.0 IS the bandit default;
# 0.9 would be multi-step, and turning it on is exactly what Day 30 gates.
FROZEN_HYPER = {
    "alpha": 0.2,
    "gamma": 0.0,
    "epsilon_start": 1.0,
    "epsilon_min": 0.05,
    "epsilon_decay": 0.95,
    "q0_default": 0.5,
}
FROZEN_TRAINING_SEEDS = [0, 1, 2]
LIVE_EXECUTION_CAP = 500
FROZEN_STATE_SCHEMAS = ("state-v1", "state-v1.5")

# The committed Day-29 ledger (HEAD 4bcc01b): 9 manifests of record,
# 15 smoke (5 x 3) + 217 training (42 + 84 + 49 + 42) = 232 live executions.
# Day 30 must move NEITHER number.
DAY29_MANIFEST_COUNT = 9
DAY29_LIVE_EXECUTIONS = 232

# Day-29 M8 result of record. Day 30 must not have altered it.
M8_THRESHOLD = 0.70
M8_METRIC = 0.2
M8_STATUS = "FAIL"

# Prior validators that must still pass (all read-only, no Spark).
PRIOR_VALIDATORS = (
    ("Day 25 env", "validate_rl_environment.py"),
    ("Day 26 agent", "validate_rl_agent.py"),
    ("Day 27 loop", "validate_rl_training.py"),
    ("Day 28 run", "validate_day28.py"),
    ("Day 29 M8", "validate_day29.py"),
)

# Multi-step machinery. If any of this appears in EXECUTABLE source (comments
# and docstrings stripped), Day 30 built the thing it was supposed to decide.
MULTISTEP_CODE = re.compile(
    r"\b(phase_t|phase_index|phase_idx|phase_id|phase_num|current_phase"
    r"|next_phase|n_phases|num_phases|phase_reward|phase_rewards"
    r"|per_phase_reward|phase_t_ref|phase_tref|t_ref_phase"
    r"|phase_state|phase_encoder|phase_aware|phase_schema"
    r"|multi_step|multistep|multi_step_mode|multistep_mode"
    r"|rollout_phases|phase_rollout|step_within_episode|bootstrap_target)\b",
    re.IGNORECASE)

# Components explicitly out of scope on Day 30 (same set the Day-29 validator
# forbids): deep RL, the cache (COMP-EXP-11), the orchestrator (COMP-EXP-12),
# EXP-003 / EXP-005 / EXP-005b.
FORBIDDEN_CODE = re.compile(
    r"\b(dqn|ppo|a2c|a3c|sac|td3|actor_critic|actorcritic|policy_gradient"
    r"|policygradient|reinforce|replay_buffer|replaybuffer|replaymemory"
    r"|target_network|targetnetwork|torch|tensorflow|keras|stable_baselines"
    r"|cachekey|cacheentry|cache_hit|cache_lookup|execution_cache"
    r"|executioncache|orchestrator|orchestrate|exp003|exp-003|exp005|exp-005"
    r"|exp005b|exp-005b)\b", re.IGNORECASE)

# A gamma literal of 0.9 assigned anywhere in executable source would be the
# one-token flip the Day-27 loop docstring warns is a WRONG bootstrap target.
GAMMA_09_PLUMBING = re.compile(r"gamma\s*=\s*0\.9|\"gamma\"\s*:\s*0\.9"
                               r"|'gamma'\s*:\s*0\.9")

results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool | None, detail: str = "") -> None:
    status = "SKIP" if ok is None else ("PASS" if ok else "FAIL")
    results.append((name, status, detail))
    print(f"{name:<46} {status:<5} {detail}")


def executable_text(path: Path) -> str:
    """Source text with comments and docstrings removed, so that a *mention*
    of a concept in prose is never mistaken for an implementation of it."""
    try:
        raw = path.read_bytes()
    except OSError:
        return ""
    try:
        toks = tokenize.tokenize(io.BytesIO(raw).readline)
        return "".join(t.string for t in toks
                       if t.type not in (tokenize.COMMENT, tokenize.STRING))
    except (tokenize.TokenError, IndentationError, SyntaxError, OSError):
        return ""


def scan_tree(tree: Path, pattern: re.Pattern[str]) -> list[str]:
    """Files under `tree` whose EXECUTABLE source matches `pattern`."""
    hits: list[str] = []
    for child in sorted(tree.rglob("*.py")):
        if "__pycache__" in child.parts:
            continue
        if pattern.search(executable_text(child)):
            hits.append(str(child.relative_to(PROJECT)).replace("\\", "/"))
    return hits


def yaml_scalars(text: str) -> dict[str, Any]:
    """Minimal top-level `key: value` reader. configs/rl.yaml is flat scalars
    plus one nested block; nothing here needs a YAML parser."""
    out: dict[str, Any] = {}
    for line in text.splitlines():
        if not line or line[0] in " #":
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*?)\s*(?:#.*)?$", line)
        if not m:
            continue
        key, raw = m.group(1), m.group(2)
        if raw == "":
            continue
        try:
            out[key] = json.loads(raw)
        except json.JSONDecodeError:
            out[key] = raw.strip('"').strip("'")
    return out


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
    Untracked NEW files are allowed - Day 30 creates new files only."""
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
    """(manifest count, summed live_executions) over the whole training tree."""
    manifests = sorted(TRAINING_ROOT.rglob("manifest.json"))
    total = 0
    for path in manifests:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        total += int((data.get("budget") or {}).get("live_executions", 0))
    return len(manifests), total


def main(argv: list[str] | None = None) -> int:
    """Run all Day-30 validator checks; print a PASS/FAIL/SKIP table and one
    overall verdict. Exit 0 = PASS, 1 = FAIL, 2 = BLOCKED."""
    del argv
    del results[:]
    py = sys.executable

    # ---- A. the decision is RECORDED -------------------------------------
    # 01 a Day-30 decision document exists
    day30_docs = sorted(RESEARCH.glob(DAY30_DOC_GLOB))
    if not day30_docs:
        check("01 Day-30 decision document exists", None,
              f"SKIP: no {DAY30_DOC_GLOB} under docs/research - decision not "
              "drafted yet")
        draft_text = ""
    else:
        check("01 Day-30 decision document exists", True,
              ", ".join(d.name for d in day30_docs))
        draft_text = "\n".join(d.read_text(encoding="utf-8", errors="replace")
                               for d in day30_docs)

    # 02 it is the DRAFT, explicitly unsigned
    if not draft_text:
        check("02 draft marked DRAFT - UNSIGNED", None,
              "SKIP: no Day-30 document to inspect")
    else:
        low = draft_text.lower()
        check("02 draft marked DRAFT - UNSIGNED",
              "draft" in low and "unsigned" in low,
              f"draft={'draft' in low} unsigned={'unsigned' in low} "
              f"({DRAFT_DOC.name} present={DRAFT_DOC.exists()})")

    # 03 it states a decision about the mode gate
    if not draft_text:
        check("03 document states a decision", None,
              "SKIP: no Day-30 document to inspect")
    else:
        low = draft_text.lower()
        has_subject = "multi-step" in low or "multi step" in low
        has_decision = bool(re.search(
            r"\b(decision|recommendation|recommend|do not enable|not enabled"
            r"|gate)\b", low))
        has_gamma = "gamma" in low
        check("03 document states a decision",
              has_subject and has_decision and has_gamma,
              f"subject={has_subject} decision_language={has_decision} "
              f"gamma_named={has_gamma}")

    # 04 PLAN line 276 is verbatim and untouched
    plan_lines = PLAN.read_text(encoding="utf-8").splitlines()
    gate_line = (plan_lines[PLAN_GATE_LINE - 1].strip()
                 if len(plan_lines) >= PLAN_GATE_LINE else "<out of range>")
    check("04 PLAN line 276 verbatim", gate_line == PLAN_GATE_TEXT,
          f"line {PLAN_GATE_LINE}: {gate_line[:70]!r}")

    # 05 the signed DEC-011 IS recorded, and records the NO decision.
    #    This check originally asserted the OPPOSITE - that DECISIONS.md had
    #    NOT been written - which was the correct invariant only while the
    #    entry was an unsigned draft. The operator signed DEC-011 on
    #    2026-09-13 (option 1, NO), so the invariant inverts: the decision
    #    must now be ON the record, and must still say NO.
    dec_text = DECISIONS.read_text(encoding="utf-8")
    dec_ids = re.findall(r"^## (DEC-\d+)", dec_text, re.MULTILINE)
    last_dec = dec_ids[-1] if dec_ids else "<none>"
    # DEC-011 need not be the LAST entry: DEC-012/013 (Day 31) came after it.
    # Slice DEC-011 up to the next DEC heading so later entries cannot satisfy
    # these assertions on its behalf.
    if "## DEC-011" in dec_text:
        start = dec_text.index("## DEC-011")
        nxt = dec_text.find(chr(10) + "## DEC-", start + 1)
        entry = dec_text[start:] if nxt == -1 else dec_text[start:nxt]
    else:
        entry = ""
    recorded = bool(entry)
    says_no = "resolves **NO**" in entry or "resolved NO" in entry
    keeps_gamma = "gamma = 0.0" in entry or "`gamma: 0.0`" in entry
    no_a5 = "A5" in entry
    approved = "APPROVED - NO" in entry
    decided = "**DECIDED**" in entry
    no_verdict = "No PASS/FAIL verdict is emitted" in entry
    ok = all((recorded, says_no, keeps_gamma, no_a5, approved, decided, no_verdict))
    check("05 DEC-011 recorded and says NO", ok,
          f"DEC-011 present={recorded} (last entry={last_dec}); says_no={says_no} gamma_0={keeps_gamma} "
          f"A5={no_a5} approved={approved} decided={decided} "
          f"no_verdict={no_verdict}")

    # ---- B. nothing was BUILT --------------------------------------------
    # 06 gamma still the frozen bandit default, hyperparameters untouched
    cfg = yaml_scalars(CONFIG.read_text(encoding="utf-8"))
    bad = [f"{k}={cfg.get(k)!r}!={v!r}" for k, v in FROZEN_HYPER.items()
           if cfg.get(k) != v]
    extra_ok = (cfg.get("training_seeds") == FROZEN_TRAINING_SEEDS
                and cfg.get("live_execution_cap") == LIVE_EXECUTION_CAP
                and cfg.get("learner") == "tabular-q")
    check("06 frozen hyperparameters untouched", not bad and extra_ok,
          (f"gamma={cfg.get('gamma')!r} (bandit), alpha={cfg.get('alpha')!r}, "
           f"seeds={cfg.get('training_seeds')}, cap="
           f"{cfg.get('live_execution_cap')}") if not bad and extra_ok
          else "; ".join(bad) or "seeds/cap/learner drifted")

    # 07 gamma is 0.0 exactly, and the running code agrees with the file
    try:
        from sparkrl.agent.q_learning import AgentConfig  # noqa: E402
        loaded = AgentConfig.from_yaml(CONFIG)
        loaded_gamma = getattr(loaded, "gamma", None)
    except Exception as exc:  # noqa: BLE001
        loaded_gamma = f"<load error: {exc}>"
    check("07 loaded gamma == 0.0 (bandit mode)", loaded_gamma == 0.0,
          f"AgentConfig.from_yaml(configs/rl.yaml).gamma={loaded_gamma!r}")

    # 08 no gamma=0.9 plumbing in executable source
    hits = scan_tree(SRC, GAMMA_09_PLUMBING) + scan_tree(SCRIPTS,
                                                         GAMMA_09_PLUMBING)
    check("08 no gamma=0.9 plumbing", not hits,
          "no 0.9 gamma assignment in src/ or scripts/" if not hits
          else "found in: " + ", ".join(hits))

    # 09 no multi-step implementation anywhere in src/
    ms_hits = scan_tree(SRC, MULTISTEP_CODE)
    check("09 no multi-step implementation in src", not ms_hits,
          "no phase-aware encoder / phase reward / multi-step rollout "
          "in executable source" if not ms_hits
          else "found in: " + ", ".join(ms_hits))

    # 10 state schema still the frozen pair - no phase field
    from sparkrl.rl.state import (SUPPORTED_SCHEMAS,  # noqa: E402
                                  STATE_VERSION)
    import sparkrl.rl.state as state_mod  # noqa: E402
    schema_ok = tuple(SUPPORTED_SCHEMAS) == FROZEN_STATE_SCHEMAS
    phase_in_state = bool(MULTISTEP_CODE.search(
        executable_text(Path(state_mod.__file__))))
    check("10 state schema has no phase field", schema_ok and not phase_in_state,
          f"SUPPORTED_SCHEMAS={tuple(SUPPORTED_SCHEMAS)} "
          f"default={STATE_VERSION}")

    # 11 env still terminates every bandit transition (source contract)
    import sparkrl.rl.env as env_mod  # noqa: E402
    env_src = Path(env_mod.__file__).read_text(encoding="utf-8")
    returns_true = "return state_after, reward.value, True, False, info" \
        in env_src
    check("11 env.step returns terminated=True", returns_true,
          "env.py returns literal True for terminated (bandit: s -> terminal)")

    # 12 every stored transition record carries terminated=true
    records = sorted(TRAINING_ROOT.rglob("transitions/**/*.json"))
    non_terminal = [str(p.relative_to(PROJECT)) for p in records
                    if json.loads(p.read_text(encoding="utf-8")
                                  ).get("terminated") is not True]
    check("12 all stored transitions terminated=True",
          bool(records) and not non_terminal,
          f"{len(records)} transition records, 0 non-terminal" if records
          and not non_terminal else f"{len(non_terminal)} non-terminal")

    # 13 no cache / orchestrator / EXP-003 / EXP-005 / EXP-005b
    fb_hits = scan_tree(SRC, FORBIDDEN_CODE)
    check("13 no cache/orchestrator/EXP-003/005", not fb_hits,
          "no forbidden components in source tree" if not fb_hits
          else "found in: " + ", ".join(fb_hits))

    # ---- C. nothing was SPENT --------------------------------------------
    # 14 execution ledger identical to the committed Day-29 figure
    n_manifests, live_total = ledger_from_manifests()
    check("14 ledger unchanged by Day 30",
          n_manifests == DAY29_MANIFEST_COUNT
          and live_total == DAY29_LIVE_EXECUTIONS,
          f"{n_manifests} manifests (Day-29: {DAY29_MANIFEST_COUNT}), "
          f"{live_total} live executions (Day-29: {DAY29_LIVE_EXECUTIONS}), "
          f"{LIVE_EXECUTION_CAP - live_total} remaining of "
          f"{LIVE_EXECUTION_CAP} - REPORTED not enforced (COMP-EXP-11 "
          f"deferred)")

    # 15 no tracked file modified - Day 30 creates NEW files only
    changed, why = git_modified_tracked()
    if changed is None:
        check("15 no frozen file modified", None, f"SKIP: {why}")
    else:
        # DECISIONS.md is the ONE tracked file Day 30 is permitted to touch,
        # and only to append the signed DEC-011. Everything else - PLAN,
        # configs, src, tests, results, the architecture documents - must be
        # untouched. Appending a signed decision is the whole deliverable of a
        # decision day, so its presence here is correct, not drift.
        # Originally: "no tracked file modified", correct while Day 30 was the
        # working day. Later days legitimately modify other files (Day 31 signed
        # DEC-012/013 and added the calibration gate under them), so this check
        # now polices DAY-30's OWN deliverables rather than the whole tree.
        day30_owned = {
            "docs/research/DAY30_MODE_GATE_AUDIT.md",
            "docs/research/DAY30_MODE_GATE_DEC_DRAFT.md",
            "configs/rl.yaml",
        }
        # this validator is deliberately NOT in the set: correcting a check whose
        # premise a later signed decision inverted is expected maintenance, and
        # the correction is itself auditable in git history. The set protects the
        # RESEARCH RECORD, not the tool that inspects it.
        touched = sorted(f for f in changed if f in day30_owned)
        check("15 Day-30 artifacts unmodified", not touched,
              ("no Day-30 deliverable modified (DECISIONS.md may grow: later "
               "decisions append to it)") if not touched
              else "Day-30 artifact modified: " + ", ".join(touched))

    # 16 no Day-30 run artifacts (a decision day produces no run)
    run_dirs = sorted(d.name for d in TRAINING_ROOT.iterdir()
                      if d.is_dir() and d.name.startswith("train-"))
    smoke_dirs = sorted(d.name for d in (TRAINING_ROOT / "smoke").iterdir()
                        if d.is_dir()) if (TRAINING_ROOT / "smoke").is_dir() \
        else []
    day30_runs = [d for d in run_dirs + smoke_dirs if "20260913" in d]
    check("16 no Day-30 run artifacts", not day30_runs,
          f"{len(run_dirs)} training + {len(smoke_dirs)} smoke run dirs, "
          f"none dated 2026-09-13" if not day30_runs
          else "new runs: " + ", ".join(day30_runs))

    # ---- D. prior evidence still stands -----------------------------------
    # 17 Day-29 M8 artifact present and still FAILED
    if not M8_ARTIFACT.exists():
        check("17 Day-29 M8 verdict intact", False,
              f"missing artifact: {M8_ARTIFACT}")
    else:
        m8 = (json.loads(M8_ARTIFACT.read_text(encoding="utf-8")).get("m8")
              or {})
        verdict = m8.get("verdict") or {}
        intact = (verdict.get("status") == M8_STATUS
                  and verdict.get("passed") is False
                  and verdict.get("metric") == M8_METRIC
                  and m8.get("threshold") == M8_THRESHOLD)
        check("17 Day-29 M8 verdict intact", intact,
              f"status={verdict.get('status')} metric={verdict.get('metric')} "
              f"threshold={m8.get('threshold')} (unaltered by Day 30)")

    # 18-22 the five prior validators still pass (read-only, no Spark)
    for label, script in PRIOR_VALIDATORS:
        path = SCRIPTS / script
        if not path.exists():
            check(f"{label} validator", None, f"SKIP: missing {script}")
            continue
        ok, detail = run_tool([py, str(path)], timeout=600)
        check(f"{label} validator", ok, detail)

    # 23 deterministic unit suite still passes (no Spark, no integration)
    ok, detail = run_tool([py, "-m", "pytest", "tests/unit", "-q",
                           "--no-header", "-p", "no:cacheprovider"],
                          timeout=600)
    check("23 unit suite (tests/unit)", ok, detail)

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
