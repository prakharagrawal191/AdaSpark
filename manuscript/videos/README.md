# Execution videos folder

Screen recordings of real code running against committed data. Nothing is staged, and none of
the recordings spends a Spark execution (all three use zero-execution modes). Record **after**
the EXP-013/EXP-014 campaigns have finished: screen-recording software adds CPU load, and the
quiet-machine protocol (PLAN §23, DEC-053 §7) forbids other heavy work while a campaign runs.

Suggested tools: Windows Game Bar (Win+Alt+R) or OBS Studio, 1080p, terminal font ≥ 14 pt.
Work from the repository root, with the canonical interpreter (`sparkrl_env311`) activated.

| File | What it shows | Commands | Length |
|---|---|---|---|
| `Video 01 Policy decision trace.mp4` | The governed control loop: B0 → B3 → frozen RL-s0 episodes, with state, action and reward per step, replayed from the logged EXP-012 manifests | `python scripts/demo.py --mode backup` | ~2 min |
| `Video 02 Confirmatory evaluation.mp4` | EXP-013's frozen design and its pre-registered analysis: the queue fingerprint and guards, then the analysis deciding H2/H3 and P1–P8 from the recorded observations | `python scripts/run_exp013.py --plan` then `python scripts/analyze_exp013.py` | ~4 min |
| `Video 03 Reproducibility and build.mp4` | The zero-execution reproducibility harness (16/16), the Day-31 governance gate, and the manuscript build with its completeness self-check (figures, tables, Equation Editor equations, captions) | `python scripts/verify_reproducibility.py`, `python scripts/validate_day31.py`, then (manuscript toolchain) `python manuscript/build_docx.py` | ~5 min |

Narration checklist per video: name the decision that authorizes what is shown (DEC-051, DEC-053,
DEC-046), state that the run spends 0 executions, and point at the artifact the output is read
from (`results/experiments/...`, `results/evaluation/...`).
