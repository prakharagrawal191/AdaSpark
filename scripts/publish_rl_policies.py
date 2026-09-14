#!/usr/bin/env python
"""Publish the three Day-29 replicate policies as the EXP-005 RL arms (DEC-015).

M8 FAILED (agreement 0.2000 vs the frozen 0.70), so no single replicate is
defensible as "the" frozen policy. DEC-015 therefore evaluates all three as
separate arms - RL-s0, RL-s1, RL-s2 - and this script moves them from their
per-run checkpoint directories into the published policy store under
``models/policies/``, which PLAN line 159 requires to be frozen before the test
set is opened.

Nothing is retrained, nothing is selected on performance, and no policy content
is altered: each artifact is loaded through the frozen
``sparkrl.agent.policy_store`` API, fingerprint-verified, and written immutably.
Re-running is idempotent - an identical artifact is accepted, a differing one
raises PolicyExistsError.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from sparkrl.agent.policy_store import (DEFAULT_POLICY_DIR, load_policy,  # noqa: E402
                                        policy_fingerprint, save_policy,
                                        verify_compatibility)

MANIFEST = DEFAULT_POLICY_DIR / "exp005_rl_arms.json"
SCHEMA = "exp005-rl-arms/v1"
M8 = PROJECT / "results" / "training" / "analysis" / "day29_policy_agreement.json"

ARMS = {
    "RL-s0": ("results/training/train-a0-d0-20260912T112906Z", 0),
    "RL-s1": ("results/training/train-a1-d0-20260912T115123Z", 1),
    "RL-s2": ("results/training/train-a2-d0-20260912T120648Z", 2),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--write", action="store_true", help="publish the artifacts")
    args = ap.parse_args()

    m8 = json.loads(M8.read_text(encoding="utf-8"))["m8"]["verdict"]
    rows = []
    for arm, (rel, seed) in sorted(ARMS.items()):
        run = PROJECT / rel
        man = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        fp = man["final_policy"]
        pid = fp["policy_id"] if isinstance(fp, dict) else str(fp)
        art = load_policy(pid, run / "checkpoints")       # verifies fingerprint
        verify_compatibility(art)                          # verifies contracts
        assert art["rng_seed"] == seed, f"{arm}: seed mismatch"
        row = {
            "arm": arm, "agent_rng_seed": seed, "policy_id": pid,
            "episodes": art["episodes"], "updates": art["updates"],
            "final_epsilon": art["epsilon"], "states": len(art["q_table"]),
            "source_run": rel, "source_run_id": man["run_id"],
            "learner_config": art["learner_config"],
            "contract_versions": art["contract_versions"],
        }
        if args.write:
            row["published_path"] = str(save_policy(art, DEFAULT_POLICY_DIR)
                                        .relative_to(PROJECT)).replace("\\", "/")
        rows.append(row)
        print("  %-6s %s  episodes=%-3d eps=%.4f states=%d  verified" % (
            arm, pid[:16], art["episodes"], art["epsilon"], len(art["q_table"])))

    body = {
        "schema_version": SCHEMA,
        "decision": "DEC-015",
        "arms": rows,
        "m8": {"status": m8["status"], "metric": m8["metric"],
               "threshold": m8["threshold"]},
        "m8_note":
            "M8 FAILED. These three policies DISAGREE: greedy-policy agreement "
            "is 0.2000 against the frozen 0.70 threshold. They are published as "
            "three separate EXP-005 arms precisely so the disagreement is "
            "reported rather than concealed behind a chosen seed. Publishing "
            "does not repair, supersede or soften the M8 verdict.",
        "evaluation_constraints":
            "Evaluated frozen and greedy. No Q update, no epsilon schedule, no "
            "exploration and no retraining on TEST (PLAN lines 159, 192).",
        "no_research_claim":
            "Publishing establishes nothing about whether any strategy "
            "outperforms another.",
    }
    canon = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    body["fingerprint"] = hashlib.sha256(canon).hexdigest()
    print("  M8: %s metric=%s threshold=%s" % (m8["status"], m8["metric"], m8["threshold"]))
    if args.write:
        DEFAULT_POLICY_DIR.mkdir(parents=True, exist_ok=True)
        tmp = MANIFEST.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(body, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(tmp, MANIFEST)
        print("  manifest: %s (%s)" % (MANIFEST.relative_to(PROJECT), body["fingerprint"][:16]))
    else:
        print("  (dry run - pass --write to publish)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
