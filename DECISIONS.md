# Decision Log

Every architectural/environmental decision is recorded here with its rationale.
Format: `DEC-xxx | date | decision | rationale | alternatives rejected`.

## DEC-001 | 2026-09-07 | Virtual environment outside the repository
The venv lives at `%USERPROFILE%\sparkrl_env`, not `<repo>\.venv`.
**Rationale:** the repository sits in a OneDrive-synced folder (risk R9); thousands of
venv files under OneDrive cause sync churn and file locks. Activation is documented in
README.md. *Rejected alternative:* in-repo `.venv`.

## DEC-002 | 2026-09-07 | Bulk data root outside the repository
Datasets, Spark event logs, and Spark temp dirs default to `%USERPROFILE%\sparkrl_data`,
overridable via `SPARKRL_DATA_ROOT`. Resolution is implemented in
`src/sparkrl/utils/paths.py` (no absolute paths hard-coded in code).
**Rationale:** risk R9 (OneDrive interference with bulk IO); keeps the repo lightweight.
The repo `data/` subfolders remain as conventional placeholders (`.gitkeep`).

## DEC-003 | 2026-09-07 | PySpark pinned to 4.0.4
PyPI offers 4.0.0–4.2.0 and the 3.5.x line. Spark 4.0 officially supports Python 3.12 and
Java 17 — both present on this machine. The 4.0.x line is a mature patch series; 4.1/4.2
are newer minors with less ecosystem mileage. **Fallback** if the Day-2 smoke matrix fails
on Windows: Python 3.11 venv + `pyspark==3.5.x`, or WSL2 (per approved plan §39).

## DEC-004 | 2026-09-07 | Source layout: `src/sparkrl/` package
Maps the approved architecture (planning doc §28) onto the Day-1 instruction tree:
- `sparkrl.spark` + `sparkrl.workloads` + `sparkrl.datagen`  ↔ `src/spark/`
- `sparkrl.monitoring` ↔ `src/monitoring/`
- `sparkrl.env` (RL environment) ↔ `src/environment/`
- `sparkrl.agent` ↔ `src/rl/`
- `sparkrl.runner` + `sparkrl.analysis` ↔ `src/optimization/` + `src/evaluation/`
- `sparkrl.utils` ↔ `src/utils/`
Top-level `experiments/` holds the experiment registry and per-experiment YAML configs;
`configs/` holds cross-cutting configuration.

## DEC-005 | 2026-09-07 | Execution backend: native Windows local-mode (PROVISIONAL)
Priority chain: native Windows → WSL2 Ubuntu → Docker. Native Windows is chosen
provisionally (Java 17 + PySpark pip wheel present). Final confirmation happens in the
**Day-2 smoke-test matrix** (Parquet IO, event logs, winutils/Hadoop-native warnings).

## Open items
- Day 3: `docs/RESEARCH_PROBLEM.md` draft (was "Day 2" in earlier draft — superseded by Day-2 completion).

## DEC-006 | 2026-09-07 | Spark-on-Windows native-IO failure — empirical findings (Day 1)
**What was tested (all measured, see `docs/ENVIRONMENT_REPORT.md`):**
1. `pyspark==4.0.4` + Java 17, no HADOOP_HOME → SparkContext startup **hard-fails**
   (`Hadoop 3.4.x Shell.<clinit>` throws when `HADOOP_HOME` is unset on Windows).
2. Adding the winutils shim (cdarlint `hadoop-3.3.6`, `winutils.exe` + `hadoop.dll`) at
   `%USERPROFILE%\hadoop` made session startup, count jobs, aggregation, and event-log
   creation work — but Parquet **writes** still failed with
   `UnsatisfiedLinkError: NativeIO$Windows.access0`, because the 3.3.6 dll doesn't export
   the 3.4.x native symbol and `hadoop.dll` was not loadable from `PATH`.
3. Removing `hadoop.dll` (builtin-java fallback) did **not** bypass the commit-path call.
4. No Hadoop 3.4.x winutils builds exist in the community repos probed (cdarlint: 2.x–3.3.6
   only; kayrnt 3.4.x: 404), so Spark 4.0.4 / Hadoop 3.4.x on Windows is not viable here.

**Root cause of the remaining native-IO error (found Day 2):** `FileUtil.canRead →`
`NativeIO$Windows.access` requires the native `hadoop.dll` to actually load. On Day 1 both
`winutils.exe` and `hadoop.dll` were installed, but `%HADOOP_HOME%\bin` was **never on
`PATH`**, so `System.loadLibrary("hadoop")` could never succeed and every native `access0`
call failed. **The fix is the standard Spark-on-Windows trio: `winutils.exe` + `hadoop.dll`
+ `PATH` entry.**

## DEC-007 | 2026-09-07 | Spark backend freeze — native Windows + PySpark 3.5.9
**Decision.** Backend = native Windows local mode: **Python 3.11.9** (per-user install,
`%LOCALAPPDATA%\Programs\Python\Python311`) + **pyspark==3.5.9** (Hadoop 3.3.4 client) +
**Java 17 Temurin** + **winutils 3.3.6 shim** (`winutils.exe` + `hadoop.dll`) at
`%USERPROFILE%\hadoop` with `HADOOP_HOME` and `%HADOOP_HOME%\bin` on `PATH` (session +
User-persistent). `requirements.txt` re-pinned to the minimal core set
(pyspark 3.5.9, psutil, PyYAML, pytest); research extras moved to
`requirements-research.txt` (Day 13+).

**Evidence — full smoke matrix (A–K) PASS, 13/13:** SparkSession creation · DataFrame ·
count · aggregation · Parquet write/read/round-trip 1M (checksums exact) · event log
240 events / 0 bad lines, `SparkListenerLogStart`→`SparkListenerApplicationEnd` · clean
shutdown. `env_check.py`: OVERALL PASS, 14 checks, 0 failed, 0 warnings. Integration
tests: 2 passed. Backend benchmark (3 reps, deterministic 1M rows): medians
session_start 0.071 s· count 0.094 s· agg 0.29 s· parquet_write 0.427 s· parquet_read
0.152 s· shutdown 0.526 s· peak RSS 0.75–1.03 GB (rep 1 is cold-start). Event log is
**uncompressed JSON**; format documented.

**Alternatives considered:** (a) Spark 4.0.4 + 3.3.6 dll + PATH — dll has no 3.4.x exports
→ rejected (evidence Day 1); (b) builtin-java fallback — doesn't bypass commit path →
rejected; (c) WSL2 Ubuntu — distro not installed, installation delays 1–2 days, adds
platform skew vs the Windows-expectations of the viva → retained as fallback.

**Reason:** PySpark 3.5.9 (Hadoop 3.3.4 client) matches the community 3.3.6 shim within
the same minor line; this deliberately trades Spark 4.0's newer features for a documented,
stably reproducible Windows backend — a correctness/reproducibility choice, not a
feature chase.

**Consequences:** venv `sparkrl_env311` is the canonical interpreter (Day-1 `sparkrl_env`
kept for forensics); all 49 subsequent days run against this stack.

**Rollback path:** (a) revisit Spark 4.0.4 if a 3.4.x-native build emerges, re-gated by the
smoke matrix; (b) WSL2 Ubuntu + PySpark 3.5.x (same pip wheel) if native Windows ever
regresses; (c) Docker Spark image. All paths require re-passing the smoke matrix.

## DEC-008 | 2026-09-09 | Architecture candidate selection (Day 11)

**Selected architecture.** Candidate C — Hybrid offline-init + online adapt + cache
— selected for implementation (provisional, pending Day-12 contracts).
Full evaluation: `docs/architecture/ARCHITECTURE_CANDIDATES.md`.

**Context.** PLAN §31 Day-11 task ("Architecture candidates | A/B/C vs 8
criteria (DEC) | criteria table"); frozen study (RQ0–RQ6, H1–H4, SC1–SC8,
EXP-001…EXP-012 + 005b) must be answerable unchanged on the DEC-007 backend
(single-node PySpark 3.5.9, ≤500 cached executions, 12 actions, AQE-off main).

**Candidates considered.** A: Offline surrogate (grid/BO → static config) —
measure first, deploy one static config, no online learning. B: Pure online
RL — cold-start ε-greedy tabular Q-learning from live executions only.
C: Hybrid — EXP-002 grid calibrates T_ref + pre-initializes Q, then bounded
(≤500) cached online adaptation. (A/B/C headers per PLAN §9 line 97.)

**Eight evaluation criteria (derived — PLAN names no eight explicitly; §5 of
the candidate doc cites the frozen source per criterion; unweighted 1–5 is a
Day-11 convention).** K1 RQ/EXP answerability (§5/§23) · K2 sample efficiency
under budget (§11/§23/§38) · K3 experimental control & reproducibility
(§22/§23/§33) · K4 adaptivity to drift (§2/§6) · K5 schedule/feasibility
(§31/§38–39, DEC-007) · K6 measurement validity (§7/§11/§20) · K7 risk &
Plan-B recoverability (§38–§39) · K8 AQE/baseline comparability (§7/§21–§23).

**Comparison summary (unweighted totals: A 27 · B 27 · C 38; C ≥4 on every
criterion).** A cannot answer RQ1–RQ4 (no policy/state/reward) and concedes
the study untested. B is most adaptive in principle but pays full live cost
per update, starts with uncalibrated T_ref, and has no graceful fallback.
C alone keeps every frozen EXP meaningful unchanged, enforces the ≤500
budget structurally via cache + guard, calibrates reward before learning,
and carries Plan B as a pre-designed operating point (grid + statics
reportable; 4-action/bandit shrink without rewrite).

**Rejected alternatives.** A — rejected: static output cannot test learning,
generalization, or ablations (EXP-004/006/007/008 void). B — rejected:
cold-start cost/variance unfair vs equal-budget baselines; failure strands
sunk RL plumbing with no artifact.

**Research implications.** None — RQs, Hx, SCs, EXPs, scope unchanged (drift
audit clean). EXP-002 becomes load-bearing (sensitivity proof + T_ref + init).

**Engineering implications.** Day-12 contracts must specify: Q-table
schema/init mapping, cache keys, v1.5 state vector, 12-action→SparkConf
table, R3 reward inputs, budget-guard/cache interplay, AQE control surface,
manifest/fingerprint formats, seed + test-set guard. Reuses Day-3
SparkConfig/session/runner/timing/baseline.

**Risks.** Gate fail (→ Plan-B benchmark, no rewrite) · cache
non-determinism (→ fingerprints/manifests/EXP-011) · reward misspecification
(→ R3 primary + A3–A5 ablations) · schedule (phased grid→env/agent→demo).

**Fallback.** Pre-authorized §39 tier 3: 12→4 actions, drop multi-step/LinUCB,
narrow ablations; grid + baseline evidence intact.

**Consequences.** Day 12 freezes component contracts/data flow for C only.
Substantive later changes need a new DEC entry (previous/new design, reason,
affected EXPs/docs, migration impact).

**Status.** DECIDED 2026-09-09 (provisional pending Day-12 freeze; NOT a claim
of empirical superiority — performance decided by EXP-004/005).

## Architecture change control (Day 11/12 freeze rule)

After the Day 11/12 architecture freeze, substantive architectural changes
require a new DECISIONS.md entry specifying previous design, new design,
reason, affected experiments (EXP-ids), affected documentation, and migration
impact. Editorial clarifications need only a commit message note.
## DEC-009 | 2026-09-09 | Architecture freeze — Candidate C contracts and interfaces

**Decision.** Freeze Candidate C (Hybrid offline-init + bounded online adapt +
cache) as the implementation blueprint: 12 components, 14 interfaces, 12 data
contracts, 6 diagrams (ARCHITECTURE_FREEZE.md + COMPONENT_CONTRACTS.md +
ARCHITECTURE_CHECKLIST.md).

**Context.** DEC-008 provisionally selected C; Day-12 open questions (Q-table
schema, cache keys, v1.5 state, 12-action table shape, R3 inputs, guard/cache
interplay, AQE surface, manifest formats, seed + test guard) are answered in
FREEZE §§9–14. No implementation begun (design files only).

**Frozen architecture.** §§5–15: components COMP-SPARK-01…COMP-EXP-12;
RL formulation (v1.5 state, 12 actions, R3 primary, ε-greedy tabular Q,
≤500 cached, grid Q-init); cache key (workload, seed, fingerprint, code +
env versions); baselines B0/B0′/B1–B4/RL identical protocol; AQE flag-only
(off main, on 005b); split tags + Day-31 test gate; F-FAIL (failed configs
never rewarded).

**Component contracts.** Responsibility/Inputs/Outputs/Dependencies/
Configuration/Failure/Logging/Test/Research-role per component
(CONTRACTS §2); conceptual signatures (§1, §3); field tables (§4).
**Data contracts.** 12 objects JSON-serializable with determinism rules.
**Architectural invariants.** Single-node, seeded manifests, config-driven,
12-action bound, T_ref-gated reward, ≤500 guard, deterministic cache,
identical baselines, AQE control, frozen test set, ±5% repro, Plan-B
recoverability; no cluster/K8s/cloud/microservices, no deep RL, no GPU path.
**Experiment compatibility.** EXP-001…EXP-012 (+005b) executable unchanged
(§17 matrix). **Plan-B compatibility.** 4-action bandit subset + benchmark
framing via config selectors, no rewrite (§16).

**Risks.** Cache-key collision/omission (→ fingerprint + versions) ·
leakage (→ split tags + init provenance + date gate) · reward shaping
(→ R3 + A3–A5) · overhead creep (→ overhead_s accounting, EXP-009) ·
schedule (incremental from Day 13: cache → workloads → monitoring → env →
agent; session/config/runner exist).

**Consequences.** Implementation proceeds from these contracts; deviations
need a new DEC entry. Day 13 begins incremental build (NOT full-system).

**Change-control rule.** After this freeze, substantive architecture changes
require a new DECISIONS.md entry: previous design, new design, reason,
affected components, affected experiments, affected docs,
migration/reimplementation impact. Editorial notes need only a commit msg.

**Status.** ARCHITECTURE FROZEN FOR IMPLEMENTATION (design freeze; NOT
empirical validation — performance decided by EXP-004/005).

## DEC-010 | 2026-09-12 | Failed-episode semantics — failure is a first-class observation (Day 29 unblock)

**Decision.** A failed or timed-out episode is a FIRST-CLASS OBSERVATION: the
environment returns the frozen R3 reward of −1, and the tabular Q-update IS
APPLIED with that reward. The Day-27 training loop
(`sparkrl.training.loop.run_training`) already implements exactly this, pinned
by `tests/unit/test_rl_training.py::test_failed_episode_is_recorded_updated_and_the_run_continues`.
No code, no test and no hyperparameter changes under this decision.

**Context.** Day 27 (audit §12), Day 28 (audit §14) and COMPONENT_CONTRACTS §12
each recorded an unresolved conflict between two frozen documents, and Day 29
blocked on it before executing any replicate. `ARCHITECTURE_FREEZE.md` §11
("Learning: … failed runs skip update") and §12 ("error path, Q-update
skipped"), and the conceptual signature in `COMPONENT_CONTRACTS.md` §3
(`Agent.update(s, a, r, s2) -> None  # skipped on failure episodes`), say the
update is skipped. `docs/PLAN.md` says the opposite in five places: §11 data
flow ("failure/timeout ⇒ reward −1" feeding the Q-update), §13 (missing
features ⇒ "run-failure path (reward −1, logged)"), §14 (timeout guard
"converts pathological configs into reward −1"), §15 where R3 literally
contains the term `− 1.0·1[failure or timeout]`, and §15 stability
("failures capped at −1").

**Precedence rule established here (the missing authority).** `docs/PLAN.md` is
the top-level frozen research plan. `ARCHITECTURE_FREEZE.md` and
`COMPONENT_CONTRACTS.md` are Day-12 implementation artifacts DERIVED from it —
the freeze header states its own sources as "PLAN §§2,5-7,11,20-23,31,33,38-39,44".
Where a derived document contradicts its source, PLAN governs. No such
precedence rule was documented anywhere in the repository before this entry;
that absence is precisely what blocked Day 29, and it is recorded now so the
question cannot recur.

**Supporting evidence for the PLAN reading.** (i) PLAN §6 states the research
objective as learning a policy "within a bounded training budget and WITHOUT
FAILED SUBMITTED CONFIGURATIONS" — an agent can only learn to avoid pathological
configurations if failures reach the learner, so the skip reading leaves that
objective with no learning mechanism. (ii) Under the skip reading the frozen R3
term `− 1.0·1[failure or timeout]` is unreachable by learning, making part of the
frozen reward definition dead. (iii) The F-FAIL invariant is "failed configs MUST
NOT yield POSITIVE reward"; a reward of −1 satisfies it. F-FAIL constrains the
SIGN of the reward, not whether the observation trains.

**Affected components.** COMP-RL-10 (agent) and the Day-27 training loop —
behaviour confirmed, not changed. COMP-RL-08 (reward) unchanged. No
implementation, test, configuration or hyperparameter is modified.

**Affected documents.** `ARCHITECTURE_FREEZE.md` §11/§12 and
`COMPONENT_CONTRACTS.md` §3 are SUPERSEDED ON THIS POINT ONLY. Their original
text is left intact (they are frozen records of what Day 12 decided); a pointer
note referencing this entry is appended to each so the contradiction is no
longer readable as live guidance.

**Affected experiments.** EXP-004 / Days 28-29 training, the Day-30 mode gate,
and EXP-005. Verified at the time of this entry: all 6 stored training
artifacts contain 57 episodes with ZERO failed episodes, so no existing result,
policy, checkpoint or manifest changes under this decision — it is
forward-looking only.

**Consequences.** Day 29 (training replicates, seeds {0,1,2}, M8) is unblocked
and proceeds under the frozen protocol unchanged. Any future run containing a
failed episode will apply the update at reward −1 and must cite this entry.

**Approval.** Recorded by the operator on 2026-09-12 after the Day-29 pre-run
audit presented both readings and the evidence above. Supervisor
counter-signature follows the same pending path as the M2 freeze
(`docs/research/M2_FREEZE.md`, "PROVISIONALLY FROZEN — awaiting supervisor
signature"); this entry is the artifact to counter-sign.

**Status.** DECIDED — PLAN reading confirmed; implementation already conformant.

## DEC-011 | 2026-09-13 | Mode gate — multi-step mode NOT enabled; γ stays 0.0 (Day 30)

**Decision.** The Day-30 mode gate resolves **NO**. Multi-step mode is **not
enabled**. `configs/rl.yaml:8` stays `gamma: 0.0` (bandit — the frozen PLAN
default). Ablation **A5** (γ=0 vs γ=0.9 multi-step) is **not run**, and Day 37
executes **A3 + A4 only**. Scope-tier rung 1 under risk R8 — "drop multi-step"
(PLAN §44 line 361; PLAN line 239) — is hereby **consumed**.

**No PASS/FAIL verdict is emitted on the gate itself.** PLAN line 276 froze no
criterion (see *Criterion* below), so a verdict issued today would be a post-hoc
gate. What is recorded is a decision, which is exactly and only what PLAN line
276's success column requires: *"decision recorded"*.

**No code, test, configuration, hyperparameter or stored result is changed under
this decision.** This entry also records a **plan defect** — a frozen gate with
no criterion — so the question cannot recur, in the manner DEC-010 recorded the
missing precedence rule.

**Context.** PLAN line 276 reads, verbatim:
`| 30 | Mode gate decision | multi-step only if stable (DEC) | decision recorded |`.

A YES would turn on, all FROZEN: the multi-step transition model
`s_t = (context, phase_t, feedback)` across 3 pipeline phases and γ = 0.9 in
place of γ = 0 (PLAN line 119); ablation A5, which PLAN line 188 gates as "only
if the Day-30 gate passed"; Day 37's parenthetical "(A5) … multi-step if gated"
(PLAN line 283); and the F5 phase structure, "F5 has 3 natural phases" (PLAN
line 167).

The gate is an **opt-IN**. Bandit γ = 0 is the frozen *default* (PLAN line 119;
verified at `configs/rl.yaml:8`, `gamma: 0.0  # bandit mode (PLAN section 12);
0.9 = multi-step, gated Day 30`). A NO changes no frozen artifact, invalidates
no stored result, and requires no rollback and no code change. The burden of
proof runs one way only — toward enabling.

**Criterion. NOT frozen by PLAN — and deliberately not invented here.** PLAN
line 276 names no metric, no statistic, no threshold, no denominator, no
artifact and no evidence source; its success column is "decision recorded", not
"gate passed". Adjacent rows do carry numbers (line 275 "policies agree ≥70%
(M8)"; line 267 "median CV ≤10%"), which makes the omission conspicuous rather
than stylistic. Across PLAN, "stable/stability/oscillat*" is numeric exactly
once — line 145's **early-stop** rule, "early stop when the greedy policy is
stable for 2 consecutive epochs" — and that rule is a budget-saving heuristic
which three frozen documents pre-emptively forbid reading as stability evidence:
`COMPONENT_CONTRACTS.md` ("a budget-saving heuristic, never evidence of
convergence"), `docs/research/DAY27_TRAINING_LOOP_AUDIT.md` ("it is not a
convergence test"), and `docs/research/DAY28_FIRST_FULL_TRAINING_AUDIT.md`,
which lists "the policy is optimal or stable" among the claims its artifacts do
not support. No derived frozen document supplies the missing number either.

This gap is a **silence in PLAN itself**, not a PLAN-vs-derived-document
contradiction. **DEC-010's precedence rule therefore has nothing to arbitrate
here**, and is not cited as though it does.

**No criterion is fixed retroactively**, because every candidate number already
exists and was observed before any criterion was written down. Two in-project
precedents govern the shape of that answer. Day 29 fixed the missing half of M8
**in writing before any policy was inspected**
(`results/training/analysis/day29_policy_agreement.json`:
`fixed_before_any_policy_was_inspected: true`, and "a denominator chosen after
seeing the policies would be a chosen result"). Day 28, faced with an undefined
"reward trend up", **refused to emit a PASS** and reported descriptives only.
Day 30's phrase is *more* incomplete than M8's — M8 at least froze a metric name
and a threshold — so the same discipline applies a fortiori.

If the operator prefers a criterion on the record rather than a criterion-free
decision, the honest form is **forward-looking**: signed first, applied only to
evidence produced afterwards. The Day-30 brief proposes C1 (bandit-arm
cross-seed greedy-policy agreement ≥ 0.70 over a pre-specified denominator, at
3 agent seeds) / C2 (the per-decision reward multi-step would learn from is
separable above the project's measured per-execution noise floor) / C3
(affordability at ≥ the per-state density bandit already achieved, and physical
executability of the frozen 12-action grid per phase inside one Spark session).
Signed today it still yields NO — C2 has never been measurable and C3 is refuted
by arithmetic and code facts — but that is a consequence, not the ground this
entry rests on.

**Evidence (MEASURED, with sources). This decision rests on NO stability
measurement.** The stability-flavoured numbers are recorded here as *context*,
explicitly not as gate scores:

1. **Cross-run policy agreement (M8, Day 29).** 0.2000 over the pre-specified
   primary denominator `D_all3` — 1 of 5 evidence-bearing states unanimous —
   against the frozen 0.70 threshold; `verdict.status = FAIL`. Variants, labelled
   in the artifact itself as not verdicts: union-of-tables 0.5000 (8 states,
   inflated by the 3 that no run ever visited), visited-by-any 0.2000, pairwise
   mean 0.26666666666666666. Source:
   `results/training/analysis/day29_policy_agreement.json`.
2. **Within-run early stop.** Fired in 3 of the 4 stored training runs
   (42, 49, 42 episodes); the Day-29 seed-0 replicate ran all 12 epochs /
   84 episodes and never triggered (`runs.*.stop_reason`, same artifact).
3. Items 1 and 2 are both stability-flavoured and both frozen-adjacent, and they
   point in **opposite directions**. Both were observed before any criterion
   existed, so whichever one a criterion selected today would determine the
   answer — which is precisely why neither is used as one.
4. **Evidence density behind the 0.2000.** Episodes per evidence-bearing state:
   16.8 (seed 0), 9.8 (seed 1), 8.4 (seed 2). The single unanimous state
   `state-v1.5|agg|S|le0` carries **1 episode per seed**, and its unanimous
   greedy action 8 **was executed by no seed** (the three seeds ran actions 6, 1
   and 0 there), so that argmax rests on the shared frozen EXP-002 Q0 row.
   **0 of 5** evidence-bearing states therefore have a unanimous greedy action
   that every seed actually ran. This is a **density fact about the
   measurement**; it is **not** a verdict on tabular Q-learning.
5. **Cell coverage at 1×** (recomputed from `visit_counts` in the same
   artifact): of the 5 × 12 = 60-cell footprint, seed 0 covered 26 cells, seed 1
   15, seed 2 19; **union 41 (68.3%)** — 19 cells executed by no seed, after 175
   live episodes across 3 seeds.
6. **Measured per-execution reward noise floor: 0.06938622701884167.** Largest
   repeat-execution reward range over an identical (cell, action, config
   fingerprint): `F5_mixed|small|a4`, n = 4, sample sd 0.03374885985397845, with
   **no policy change involved**. Source:
   `results/training/train-a0-d0-20260912T083120Z/analysis/day28_analysis.json`
   (`max_range`, in the block labelled "MEASURED NOISE FLOOR").
7. **Budget ledger, recomputed from all 9 training manifests:** 15 smoke
   (5 runs × 3) + 217 training (42 + 84 + 49 + 42) = **232** of the frozen 500
   spent, **268 remaining**. The Day-29 validator's deliberately conservative
   figure is **238 consumed / ≤262 remaining** (it adds 6 reconstructed
   unledgered test executions). Both are recorded side by side; neither corrects
   the other. Every manifest carries: "in-run only; the env counter is
   per-process. Cross-run SC6 totals are the SUM over manifests, REPORTED not
   enforced (COMP-EXP-11 deferred)". *Caution for future readers:*
   `train-a0-d0-20260912T083120Z/analysis/day28_analysis.json` still carries its
   then-correct ledger of 57 spent / 443 remaining; quoting it would overstate
   headroom by 175.
8. **Artifact integrity re-verified read-only today:** `scripts/validate_day29.py`
   → OVERALL PASS, 24 checks, 24 pass, 0 fail, 0 skip — including check 18,
   "analysis reproducible — analyzer deterministic; temp output == stored
   artifact". That run wrote no artifact and spent no execution budget.
9. **EXP-001 was never executed** — there is no `results/experiments/exp-001`.
   The project therefore has **no independent run-to-run noise profile** (PLAN
   line 308: 20 runs, CV ≤10%), which limits what any stability criterion could
   ever have been resolved against beyond the measured floor in item 6.

**Grounds the decision does rest on** — code facts, arithmetic over frozen
numbers, and the frozen default. None of them depends on an observed policy.

- **Enabling is a build, not a flag.** The learner half already exists and is
  correct: `src/sparkrl/agent/q_learning.py:226,232` implements both the terminal
  target and the bootstrapping target. Nothing else does. The environment cannot
  emit a non-terminal transition (`src/sparkrl/rl/env.py:300-301` —
  `self._episode = None  # bandit mode: episode terminates`, then
  `return state_after, reward.value, True, False, info`); **0 of 232** recorded
  executions have ever reached the bootstrap branch. The frozen state schema has
  no phase field (`src/sparkrl/rl/state.py:36`,
  `SUPPORTED_SCHEMAS = (SCHEMA_V1, SCHEMA_V15)`), and the frozen `q0-exp002/v1`
  init is keyed on state-v1.5 keys — **INFERRED:** PLAN line 119's `s_t` needs a
  new schema version and that Q0 would not transfer to it. No per-phase
  measurement exists: `src/sparkrl/workloads/families.py:223` `F5Mixed.run()`
  executes all three phases in ONE timed call under ONE config and emits phase
  *names* and row counts, not per-phase times. No per-phase normaliser exists:
  `src/sparkrl/rl/tref.py:60`, `TRefStore` is keyed `f"{family}|{scale}"`. A
  per-phase reward would require a new EXP-002-class calibration that PLAN
  schedules on no day and charges to no register line.
- **The repo's own Day-27 warning.** `src/sparkrl/training/loop.py:654-658`,
  written before this gate: using `state_after` as `Transition.next_state` "is
  harmless only because every bandit episode is terminal and never bootstraps; a
  Day-30 multi-step gate would make it a wrong bootstrap target." Yet
  `AgentConfig.from_yaml` validates γ only against
  `FROZEN_GAMMAS = (0.0, 0.9)` (`q_learning.py:55,94`), so a one-token edit to
  `configs/rl.yaml:8` **loads cleanly** and nothing in env, loop, runner or
  validators rejects it. An explicit recorded NO is the control that keeps that
  edit from happening by accident.
- **A frozen-vs-frozen incompatibility.** Per-phase action changes over the
  frozen 12-action grid (`spark.sql.shuffle.partitions ∈ {16,32,64,128}` ×
  execution parallelism `local[N]` + `spark.default.parallelism ∈ {2,4,8}`, PLAN
  line 127) require a **session restart** whenever parallelism changes (PLAN line
  115: "changing parallelism (`local[N]`) ⇒ session restart") — that is 2 of the
  3 config keys the grid sets. But F5 is defined by a JVM-cached intermediate
  "consumed twice" (PLAN line 115; `families.py:223`), and a restart destroys that
  cache. **Both sides are frozen.** Resolving the conflict requires a **PLAN
  amendment**, which is not a Day-30 decision to make.
- **Arithmetic (INFERRED from frozen numbers; decisive independently of any
  policy observation).** One execution per (state, action) per seed at the frozen
  3 seeds costs: **180** at today's 5-state footprint (67% of the 268 remaining);
  **252** on the F5-only reading (5 − 1 + 3 = 7 states — 94% of the remainder,
  leaving 16); **540** on the all-families reading (15 states — 2.01× the
  remainder and 1.08× the entire frozen 500). The nominal 30-state space would
  need 1080 and cannot be covered once per action per seed inside the full 500.
  All of that is n = 1 per cell against the 0.069386 noise floor of Evidence item
  6, while the existing 5-state footprint is still only 68.3% covered after 175
  executions. An A5 arm at Day-29 scale (252) is 84% of EXP-008's ~300-run
  register line (PLAN line 315) or 94% of the training remainder (PLAN line 45,
  SC6 ≤500) — **PLAN states both pots and reconciles neither**.
- **The asymmetry.** Bandit is the frozen default; a NO is pre-authorised (PLAN
  line 361; PLAN line 239 under R8) and is rung 1 of the scope ladder rather than
  a failure state. PLAN's own feasibility table (line 346) already scores
  multi-step Feas 3 / Value 4 / Cplx 3 / Risk 3, amber "gated Day 30".
  `ARCHITECTURE_FREEZE.md` describes Plan-B as "droppable via config selectors
  only — same components, same manifests, no rewrite". *Note that freeze's exact
  scope:* it is a claim about **dropping**, and for dropping it is accurate; it is
  **not** a claim that *enabling* is config-only, and the code facts above show it
  is not.

**No learning claim, in either direction.** Day 29 failing M8 is **not** evidence
that tabular Q-learning cannot work here, and nothing in these artifacts is
evidence that multi-step would fix or worsen anything. M8 measured bandit-mode
cross-seed agreement; nothing in it is phase-related, and no artifact measures
whether agreement responds to state-space size, discount, or evidence density —
only one density regime has ever been run. No frozen hyperparameter is retuned
and no past result is moved by this entry.

**Affected components.** None modified. COMP-RL-07 (state encoder), COMP-RL-09
(environment) and COMP-RL-10 (agent) stay bandit-only as implemented and tested;
`configs/rl.yaml:8` stays `gamma: 0.0`. The multi-step build named under
*Grounds* — new state schema version, non-terminal env path, phase-segmented
execution, per-phase metrics, per-phase T_ref calibration, per-phase reward,
multi-decision loop — is **not** undertaken. COMP-EXP-11 (cache) and COMP-EXP-12
(orchestrator) remain deferred and are untouched by this entry.

**Affected documents.** None modified. PLAN lines 119, 167, 188, 276, 283, 346
and 361 remain as frozen; this entry records how line 276 is discharged and does
not amend it. **Plan defect recorded:** PLAN line 276 freezes a gate
("multi-step only if stable") whose predicate is defined nowhere in PLAN and
nowhere in any derived frozen document. The defect is recorded here, not
corrected — correcting it would be a PLAN amendment, out of scope for a Day-30
decision. `ARCHITECTURE_FREEZE.md` and `COMPONENT_CONTRACTS.md` are unaffected:
their Plan-B "droppable via config selectors" language describes exactly the path
taken. DEC-010 is cited in this entry only to be **set aside as inapplicable**
(see *Criterion*); nothing in DEC-010 is altered.

**Affected experiments.** **A5 is not run** — PLAN line 188 gates it on this gate
passing. **Day 37** executes A3 + A4 only; PLAN line 283's parenthetical "(A5)"
and "multi-step if gated" already anticipate this. **EXP-008** (RQ4, PLAN line
315, ~300 runs) proceeds with A3 + A4 receiving that whole register line rather
than sharing it. The ablation set becomes **A1–A4**; RQ4 is answered by A3
(reward variants) + A4 (action space) only, and the write-up must state that A5
was not run **and why**, making **no claim about what it would have shown**.
EXP-005, EXP-006, EXP-007 and the Day-31 evaluation harness are unaffected —
they evaluate a frozen policy at the frozen default. No stored manifest, policy,
checkpoint or result is invalidated.

**Consequences.** Days 31–37 proceed unchanged at γ = 0.0, with zero unscheduled
build work. Day 30 spends **0** executions; the ledger stays at 232 by manifest
sum (268 remaining) / 238 conservative (≤262 remaining), all of which remains
available to Days 31–37. Scope-ladder rung 1 is consumed; rungs 2–4 (drop LinUCB
→ shrink ablations to A1+A3 → 4-action space) remain available under R8. The
discount dimension of RQ4 is left unexamined **by decision, and that limitation
must be stated as such in the report** — it is not a measured result. Any future
edit that sets `gamma: 0.9` must cite a superseding DEC entry: the config layer
will not stop it, and this entry is the only control that does.

**What would reopen this.** Reopening requires **new evidence or an explicit PLAN
amendment** — never a re-reading of what is already measured.

1. A PLAN amendment resolving the **restart-vs-cache conflict** (for example by
   restricting per-phase actions to `shuffle.partitions` only — itself a change to
   the frozen 12-action grid).
2. **Per-phase T_ref calibration and per-phase metric extraction actually
   existing**, with a named register line paying for them.
3. Budget headroom sufficient for an A5 arm at **≥ the per-state density bandit
   already achieved** (8.4–16.8 episodes per evidence-bearing state) — which first
   requires the operator to settle whether an A5 retrain is charged to SC6's ≤500
   (PLAN line 45) or to EXP-008's ~300 (PLAN line 315). *That conflict is internal
   to PLAN; DEC-010's precedence rule cannot arbitrate it.*
4. A **signed criterion** (C1/C2/C3 or the operator's own), followed by a
   bandit-arm replicate measurement meeting it **on evidence produced after
   signing**.
5. An **explicit operator override** accepting the build as research cost and
   amending PLAN to schedule it — in which case the gate is not "passed", it is
   **superseded**, and must be recorded as such in a new DEC entry.

**What would NOT reopen it:** re-deriving M8 over a different denominator;
adopting the early-stop rule as the stability criterion after the fact; tuning
any frozen hyperparameter to move a past result.

**Open questions carried to the operator with this entry.**
(i) Is a criterion-free decision on frozen-default / scope-tier grounds
acceptable, or should a numeric criterion be pre-specified? PLAN line 276
requires only "decision recorded", so both discharge it; the choice is the
operator's, not an agent's. (ii) Should the DEC record that EXP-001 was never
run, so the project has no independent run-to-run noise profile? *(Recorded
above, Evidence item 9.)* (iii) Are both budget figures recorded side by side?
*(Yes, Evidence item 7; neither constrains this gate.)* (iv) Is one multi-step
episode **1 or 3** live executions against the 500 cap? Undefined in PLAN, and
it changes A5's cost by 3×. (v) Is multi-step all-families (PLAN line 119) or
F5-only (PLAN line 167)? A 2.14× cost difference, also undefined.

**Approval.** **APPROVED - NO**, option 1, recorded by the operator on
2026-09-13 after the Day-30 evidence brief presented both cases, the criterion
gap, and the recommendation. The operator selected a criterion-free decision on
frozen-default and scope-tier grounds, with forward-looking reopen conditions;
no PASS/FAIL verdict is emitted and no criterion is fixed retroactively.

Supervisor counter-signature follows the same pending path as the M2 freeze
(`docs/research/M2_FREEZE.md`, "PROVISIONALLY FROZEN - awaiting supervisor
signature"); this entry is the artifact to counter-sign.

**Status.** **DECIDED** - mode gate resolved NO; multi-step not enabled; gamma = 0.0 retained; ablation A5 not run; scope-tier rung 1 under risk R8 consumed; plan defect (a frozen gate with no criterion) recorded. No code, test, configuration, hyperparameter or stored result changed. Day-30 execution budget spent: ZERO (ledger unchanged at 232 of 500).

## DEC-012 | 2026-09-13 | EXP-003 budget reconciliation — B1/B2 selection is a separate authorized phase (Day 31)

**Decision.** **APPROVED — Option B.** The PLAN line 310 register estimate of
"~30" is interpreted as the B0/B1/B2 comparison at ONE repetition (3 strategies ×
8 validation cells = 24), and the 96-run B1/B2 selection grid is authorized as a
SEPARATE, REQUIRED phase that the register never budgeted. Authorized validation
spend: **96 (selection) + 120 (EXP-003 comparison at the frozen 5 repetitions) =
216 executions.**

**Context.** Day 31 built the evaluation harness and froze the TEST identity but
could not freeze B1/B2: no seed-3 observation exists anywhere in the repository
(EXP-002 is seed 0/train, training is seeds 0/1/2, baseline is seed 0). B2 is
defined at PLAN line 154 as "best validation-grid config per family", which
cannot be evaluated without a validation grid the register does not fund.

**Plan defect recorded.** PLAN line 310 budgets ~30 for EXP-003 while its own
B1/B2 definitions require 216 — a difference of 186, or 7.2x. The estimate covers
the comparison alone at one repetition and omits the selection grid entirely.
This is recorded, in the manner DEC-010 recorded the missing precedence rule and
DEC-011 the missing gate criterion, so the omission cannot recur silently.

**Budget scope.** EXP-003 is a separate register line and is NOT charged to SC6's
≤500 TRAINING cap (PLAN line 45), which stands at 232/500 and is untouched by
this decision.

**Affected.** EXP-003; Day 31's "configs frozen" deliverable; Day 32 (EXP-005),
which stays blocked until B1/B2 are empirically frozen. No code, hyperparameter or
stored result changes under this entry.

**Approval.** Recorded by the operator on 2026-09-13. Working record:
`docs/research/DEC_012_EXP003_B1B2_RECONCILIATION.md`. Supervisor
counter-signature follows the M2-freeze path.

**Status.** **DECIDED** — 216 validation executions authorized; budget
discrepancy reconciled and recorded as a plan defect.


## DEC-013 | 2026-09-13 | Validation execution gate (Model B) and selection repetitions (1 rep)

**Decision.** Two linked questions, both **APPROVED**:

1. **Selection repetitions — ONE.** Candidate-grid selection is TUNING, not
   evaluation, so the frozen median-of-5 rule does not bind it. B1/B2 selection
   runs at 1 repetition (96 runs); the EXP-003 comparison remains at the frozen 5
   repetitions (120). Textual basis: PLAN line 163 describes the validation split
   as "B1/B2 **tuning** + hyperparameters", while the 5-repetition rule is scoped
   to evaluation (PLAN line 141 "evaluation uses median-of-5 repetitions only";
   line 184 "all evaluation = 5 repetitions"). PLAN never states which rule
   governs selection; that silence is the defect recorded here.

2. **Execution gate — Model B.** The EXP-003 calibration stage supplies its OWN
   split authorization, admitting VALIDATION only. `assert_train_only` is NOT
   widened and keeps its exact semantics: it still refuses every validation and
   every test cell, and still accepts train.

**Why a separate authorization was needed.** Authorizing a BUDGET is not
authorizing an EXECUTION PATH. Verified by running the code:
`sparkrl.experiments.runner.execute_run` called `assert_train_only` first, which
raises `ValueError` for every seed-3 cell, so Spark never started. Approving
DEC-012 alone would have unblocked nothing.

**Implementation, stated precisely.** Model B as drafted said "frozen path
untouched". That is achievable in BEHAVIOUR but not in file bytes: the only
alternatives were an additive parameter on `execute_run` or duplicating the
runner, and duplication is forbidden by the architecture (COMP-SPARK-04 owns
execution). `execute_run` therefore gained ONE keyword-only parameter,
`split_guard`, defaulting to `assert_train_only`, so every pre-existing caller
retains identical behaviour; the default is pinned by a unit test. The
calibration entry point `sparkrl.evaluation.orchestration.execute_validation_run`
passes `authorize_validation_cell` instead. This deviation from the drafted
wording is recorded rather than glossed.

**TEST is unaffected and remains sealed.** No guard admits TEST.
`assert_test_execution_permitted()` raises `TestSplitSealed` unconditionally and
`execute_test_run` is unreachable. TEST execution belongs to EXP-005 (Days 32-33)
and EXP-006 (Day 34), and crossing that boundary needs its own decision.

**Affected.** `sparkrl/experiments/runner.py` (one additive parameter, default
behaviour preserved); `sparkrl/evaluation/orchestration.py`; `.gitignore` (a
Day-31 exception so the TEST-freeze and evaluation-spec artifacts that Days 32-34
must verify fingerprints against are version-controlled, as the EXP-002 record
already is). No hyperparameter, no reward, no policy, no stored result changes.

**Approval.** Recorded by the operator on 2026-09-13. Working record:
`docs/research/DEC_013_VALIDATION_EXEC_GATE_AND_SELECTION_REPS.md`. Supervisor
counter-signature follows the M2-freeze path.

**Status.** **DECIDED** — selection at 1 repetition; validation execution
authorized via a dedicated calibration guard; TRAIN semantics and the TEST seal
both unchanged.

## DEC-015 | 2026-09-14 | EXP-005 RL arm — all three replicates evaluated as separate arms (M8 failed)

**Decision.** **APPROVED.** EXP-005 evaluates the three Day-29 training
replicates as **three separate strategies** - `RL-s0`, `RL-s1`, `RL-s2` - rather
than one "frozen policy". EXP-005's strategy set becomes **nine**: B0, B0', B1,
B2, B3, B4, RL-s0, RL-s1, RL-s2. All three policies are frozen before the test
set is opened (PLAN line 159) and are never retrained (PLAN line 192).

**Context - why a decision was needed at all.** PLAN speaks throughout of *the*
frozen policy, singular (lines 159, 192; ARCHITECTURE_FREEZE line 66 "RL frozen
policy"). Three policies exist. **M8 was the criterion that would have
established the replicates agree closely enough to speak of one policy, and it
FAILED**: greedy-policy agreement 0.2000 over the pre-specified evidence-bearing
denominator, against the frozen 0.70 threshold (DAY29 audit;
`results/training/analysis/day29_policy_agreement.json`). PLAN,
ARCHITECTURE_FREEZE and COMPONENT_CONTRACTS define **no rule** for selecting one
replicate from seeds {0,1,2}, and no prior DEC provides a fallback for an
M8-failing policy family. Proceeding without an explicit decision would have
meant silently promoting one of three disagreeing policies.

**Plan defect recorded.** PLAN requires a single frozen policy but never says how
it is chosen from the frozen training seeds {0,1,2}, and specifies no fallback if
the M8 agreement gate fails. This is the same class of omission as DEC-010 (no
precedence rule), DEC-011 (no gate criterion) and DEC-013 (no selection
repetition rule), and is recorded so it cannot recur silently.

**Why three arms rather than one chosen seed.** Selecting a single replicate
after M8 failed would conceal the disagreement behind a choice, and would answer
RQ2 for one run rather than for the method. Three arms report the replicate
spread as part of the result: if all three beat B0 the claim is materially
stronger than any single seed could support; if they diverge, that divergence is
the honest finding. The rejected alternative - freezing seed 0 on the principled
ground that it is the only replicate to complete the full 84-episode schedule and
reach the frozen epsilon floor of 0.05 (seeds 1 and 2 early-stopped at 49 and 42
episodes with epsilon still 0.0810 and 0.1160) - remains defensible and cheaper,
and is recorded here as the runner-up rather than discarded.

**The three frozen policies** (each verified through
`sparkrl.agent.policy_store.load_policy`; identical frozen contracts: gamma 0.0,
alpha 0.2, action_mode mode12, reward R3, state-v1.5, 8 states):

| arm | policy id | episodes | updates | final epsilon | source run |
|---|---|---|---|---|---|
| RL-s0 | `b801f4a7df200b04` | 84 | 84 | 0.0500 | train-a0-d0-20260912T112906Z |
| RL-s1 | `af41d8ae7a21d81f` | 49 | 49 | 0.0810 | train-a1-d0-20260912T115123Z |
| RL-s2 | `d8fd7b9859d2feea` | 42 | 42 | 0.1160 | train-a2-d0-20260912T120648Z |

**Cost.** Two additional arms over EXP-005's planned seven: 7 instances x 2 x 5
repetitions = **+70 runs**, charged to EXP-005's own register line (PLAN line
312, ~245), NOT to SC6's 500-execution training cap, which stays at 232/500 and
is untouched.

**Constraints that remain in force.** The policies are evaluated frozen and
greedy; no Q update, no epsilon schedule, no exploration and no retraining occurs
on TEST. M8's FAILED verdict is unchanged and must be reported alongside every
RL result: three arms report the disagreement, they do not repair it.

**This decision does NOT authorize TEST execution.** That is DEC-014, still
PENDING SUPERVISOR APPROVAL. EXP-005 also remains blocked on three strategies
that are unimplemented and scheduled on no PLAN day - B0' (AQE-on default), B3
(rule-based adaptive, whose constant `k` in `clamp(input_GB x k, 16, 128)` PLAN
never defines) and B4 (random search) - recorded here as a readiness finding, not
resolved.

**Approval.** Recorded by the operator on 2026-09-14 after the Day-32 readiness
audit presented the four options and their research implications.

**Status.** **DECIDED** - EXP-005 RL arm is three replicate arms; policies frozen
and published to the policy store; no TEST execution authorized by this entry.

## DEC-016 | 2026-09-14 | EXP-005 baseline specifications — A/E/F decided; B/C/D remain open

**Decision.** Three of the six questions raised by the Day-32 baseline audit are
**DECIDED**; three remain **OPEN** and are carried in the working record
`docs/research/DEC_016_BASELINE_SPECIFICATION_GAPS_B0P_B3_B4.md`.

**A — B0' identity. DECIDED.** B0' is the **AQE-on modern/default reference
baseline** of `docs/PLAN.md:152` ("Spark 3.x factory default (AQE enabled)"), NOT
the "static-tuned EXP-003" strategy of `ARCHITECTURE_FREEZE.md:66/:88`, which is
superseded on this point. DEC-010's precedence rule governs: PLAN governs where a
derived Day-12 document contradicts it. Three further documents agree —
`BASELINE_B0.md:37`, `DAY17_BASELINE_AUDIT.md:38`, and the header of
`configs/baseline_b0.yaml` itself, which names "AQE-on ... (B0' / RQ6 / EXP-005b)"
as a separate condition. The ARCHITECTURE_FREEZE reading was additionally
untenable: `PLAN:310` lists EXP-003's strategies as "B0,B1,B2" with no B0', and a
validation-tuned B0' would collide with B1, already defined as "one config tuned
on validation, used everywhere".

**Derivation is mechanical, no constant invented.** `configs/baseline_b0.yaml`
declares every value to be either observability metadata or "Spark's own
out-of-box setting", and annotates `aqe_enabled: false` as "AQE OFF (main study)
- NOT a tuning choice". B0' is therefore B0 with `aqe_enabled: true` and nothing
else changed.

**A2 — AQE role. Already resolved, recorded for completeness.** An AQE-on
baseline inside the AQE-off main study is EXPLICITLY INTENDED: `PLAN:72` states
the contribution as a comparison "incl. random-search-equal-budget **and
AQE-on/off conditions**", and `PLAN:77` fixes AQE off so that *pre-execution
configuration selection is well-defined* - a constraint on strategies that CHOOSE
configurations, not a prohibition on an AQE-on reference point. EXP-005b (Day 38)
remains the distinct full AQE-on condition.

**CONSEQUENCE DISCOVERED WHILE DECIDING A — B0' CANNOT YET EXECUTE.** The frozen
runner blocks AQE-on twice: `runner.py:286` raises "AQE became enabled after
config application (PLAN section 7)", and `verify_applied()` at `runner.py:246`
records "AQE must be OFF". `SparkConfig` itself accepts `aqe_enabled=true`
cleanly. So B0' is now fully specified and its STRATEGY is implementable, but its
EXECUTION requires a further execution-path authorization of exactly the kind
DEC-013 Model B provided for the validation split. This is recorded here and
belongs to DEC-014's execution scope; it is NOT authorized by this entry.

**E — EXP-005 arm count. DECIDED.** The 9-arm scope (B0, B0', B1, B2, B3, B4,
RL-s0, RL-s1, RL-s2) stands on the signed DEC-015, which supersedes
`PLAN:278/:312`'s "7 strategies" **by decision rather than by edit**. `docs/PLAN.md`
is deliberately left unmodified as the historical record, consistent with how
DEC-014 and DEC-015 already describe the supersession, and with DEC-009's
change-control rule placing substantive changes in this ledger.
`PLAN AMENDMENT REQUIRED AFTER SUPERVISOR DECISION` is recorded as outstanding.

**F — Implementation scheduling. DECIDED.** Building B0', B3, B4 and the
`BaselineStrategy` interface is folded explicitly into **Day 32's scope**, which
PLAN otherwise describes only as "EXP-005 main comparison - queue completes". No
day is renumbered and nothing downstream shifts. All four items are buildable
with **no Spark and with TEST sealed** - they are configuration-selection rules,
unit-testable against fixtures exactly as the Day-31 harness was.

**B — B3 specification. DECIDED.** `input_GB` = the dataset manifests'
`total_bytes / 1e9` (compressed Parquet, decimal GB) - the sum
`orders.total_bytes + lineitem.total_bytes` the state encoder already uses
pre-execution, checksummed in frozen manifests, requiring no new measurement.
The clamp targets `spark.sql.shuffle.partitions`, whose frozen action levels
{16, 32, 64, 128} are exactly the clamp bounds. The core-count rule resolves
parallelism to the machine's physical core count clamped to the frozen levels
{2, 4, 8}; this machine has 24 physical cores, so B3 selects parallelism 8.
**`k` = 7.45**, derived as 1e9 / 134217728 - one partition per 128 MB, Spark's
own `spark.sql.files.maxPartitionBytes` default. It is the only candidate
derivable from outside this project.

**B3 COLLAPSES ONTO B1, AND THAT IS RECORDED AS A FINDING, NOT ENGINEERED
AROUND.** Measured dataset sizes are 0.0386 / 0.1320 / 0.4042 GB (S/M/L), so
`clamp(input_GB x 7.45, 16, 128)` yields **16 partitions at every scale**. With
parallelism 8 this is `G-p8-sp16`, byte-identical to the frozen B1. B3 is
therefore a duplicate arm at this project's data volume, and SC3
(`RESEARCH_PROBLEM.md:305`, "not worse than heuristics") reduces in practice to
RL vs B1. The alternative - a larger `k` (256 or 512) chosen so the formula
produces a visible gradient - was REJECTED because no value outside this project
justifies it and it would have been selected after the RL results already
existed. The degeneracy is a fact about the data scale and is reported as one.

*Recorded for the reader: PLAN's scale ladder ("S ~0.3, M ~1, L ~3 GB",
`PLAN:115`) describes LOGICAL volume; at 10.8 bytes/row compressed Parquet,
37.5M rows is ~3 GB uncompressed and 0.404 GB on disk. Both measures are
legitimate and they differ ~7.4x in `k`. This entry pins the on-disk measure
because it is the one the system actually has.*

**C — B4 specification. DECIDED.** B4 is an **equal-budget random search on the
TRAIN split**: **84** uniform draws over the frozen 12-action grid from the
seeded Orchestrator RNG stream, the best selected by **median
`execution_time_s`**, then **frozen before TEST** as an immutable fingerprinted
artifact. N = 84 is RL-s0's training budget - the only arm that completed the
full prescribed 84-episode schedule and reached the frozen epsilon floor of 0.05,
and therefore the only well-defined single referent for "same budget as RL" now
that DEC-015 gives arms of 84, 49 and 42. Searching on TRAIN touches neither
VALIDATION nor TEST. Projected cost: 84 executions, taking the ledger from
232 to 316 of 500.

**D — EXP-005 TEST instance scope. DECIDED.** The seven instances are:

| # | family | scale | dataset seed | unseen dimension |
|---|---|---|---|---|
| 1 | F1_agg | large | 3 | unseen scale L |
| 2 | F2_join | large | 3 | unseen scale L |
| 3 | F3_rdd | large | 3 | unseen scale L |
| 4 | F4_ski | large | 3 | unseen scale L + unseen family |
| 5 | F5_mixed | large | 3 | unseen scale L |
| 6 | F4_ski | small | 4 | unseen family + unseen seed |
| 7 | F4_ski | medium | 4 | unseen family + unseen seed |

All seven verified `split_of() == "test"`. The set covers every unseen dimension
`PLAN:192` names - unseen scale, unseen family, unseen seeds - and was chosen
without reference to any performance measurement. This resolves the 7-vs-43
conflict: the 43 frozen cells remain the TEST IDENTITY, and these 7 are the
EXP-005 INSTANCES drawn from it. `7 x 9 arms x 5 repetitions = 315`, matching
DEC-014's projection.

**GAP THAT NO CHOICE HERE CAN CLOSE:** `PLAN:163` also names "public dataset" and
"F5 with unseen parameters" as TEST material. Neither exists among the 43
enumerated cells nor on disk - no NYC-Taxi dataset was ever generated. EXP-006's
external-validity component is unavailable regardless of this scope decision, and
that is recorded rather than quietly dropped.

**Affected.** B0' becomes implementable as a strategy (execution still gated).
B3 and B4 remain unimplementable. `DEC-014 REQUIRES AMENDMENT BEFORE APPROVAL`
and cannot be soundly approved before Decision D; its execution scope must now
also cover the AQE-on runner guard recorded above. No code, hyperparameter,
policy, budget or stored result changes under this entry.

**Approval.** Recorded by the operator on 2026-09-14. Working record:
`docs/research/DEC_016_BASELINE_SPECIFICATION_GAPS_B0P_B3_B4.md`. Supervisor
counter-signature follows the M2-freeze path.

**Status.** **DECIDED** - all six questions (A-F) resolved on 2026-09-14. B3
collapses onto B1 and is recorded as such; B4 requires an 84-execution TRAIN
search before it is frozen; the seven EXP-005 instances are named. No TEST
execution is authorized by this entry - that remains DEC-014, which may now be
amended to the resolved 7-instance scope and must also cover the AQE-on runner
guard. TEST remains sealed.

## DEC-017 | 2026-09-14 | EXP-005 methodology review — amends DEC-015 and DEC-016 (Day 32)

**Decision.** The master methodology review is **ADOPTED IN FULL**. This entry
amends the signed DEC-015 and DEC-016 rather than rewriting them, per DEC-009's
change-control rule. Four substantive changes, two of which revise decisions the
operator had already signed, and both of which rest on evidence found only during
the review.

**1. B3 is SPECIFIED but NOT EXECUTED as a TEST arm (amends DEC-016 Decision B).**
`k` = 7.4506 stands unchanged. New evidence: B3 diverges from 16 partitions only
above **2.147 GB**, and the largest dataset anywhere in the frozen universe -
train, validation AND test - is **0.4042 GB**. B3 would need a cell **5.3x larger
than anything that exists** before it differed from B1. It is therefore provably
byte-identical to B1 on every cell that will ever be executed, verified by
comparing configuration fingerprints. Running it would spend **35 TEST
executions** measuring a configuration identical to one already in the queue.
B3's specification and its identity to B1 are reported ANALYTICALLY instead.
SC3 ("not worse than heuristics") becomes RL vs B1 **by proof rather than by
omission** - a defensible result, and a more interesting one than a duplicate
column: the literature-standard 128-MB sizing heuristic degenerates to the
validation-tuned static baseline at these data volumes.

**2. B0' executes in EXP-005b, NOT in EXP-005's pooled comparison (amends
DEC-016 Decision A).** Decision A's identity finding is unchanged - B0' is the
AQE-on factory default of PLAN:152. What changes is its placement, on evidence
not weighed when A was signed: `ARCHITECTURE_FREEZE.md:69` states "Main study:
OFF (PLAN section 7). EXP-005b: ON ... Every manifest records aqe_mode; **analysis
never pools across modes**." Pooling an AQE-on arm into a Wilcoxon / Cliff /
Holm comparison against AQE-off arms is prohibited by that frozen rule. There is
also a fairness defect independent of the rule: B0' ADAPTS AT RUNTIME while every
other arm is configuration-frozen pre-execution, which is not a like-for-like
comparison. This supersedes the earlier "EXPLICITLY INTENDED" reading recorded in
DEC-016, which cited PLAN:72/:312 but had not weighed FREEZE:69.

**3. EXP-005 is SEVEN arms (amends DEC-015 and DEC-016 Decision E).** With B3
not executed and B0' moved, the set is **B0, B1, B2, B4, RL-s0, RL-s1, RL-s2**.
The three RL replicate arms stand exactly as DEC-015 established - M8 failed at
0.2000 and collapsing them would conceal the disagreement behind a choice.
Consequence worth stating: this **restores PLAN:278/:312's "7 strategies"
verbatim**, so the `PLAN STRATEGY-COUNT CONFLICT` recorded in DEC-016 Decision E
is DISSOLVED and no PLAN amendment is required. Projected EXP-005 cost returns to
**7 instances x 7 arms x 5 repetitions = 245**, matching the PLAN:312 register
estimate exactly.

**4. The B4 protocol is completed (amends DEC-016 Decision C).** Decision C fixed
the budget, domain, RNG source, metric, freeze point and split, but left the cell
schedule, the seed value and the aggregation rule undefined - which the Day-32
calibration task correctly refused to run against. Completed here:

- **Schedule:** round-robin over the 7 eligible TRAIN cells x 12 cycles = 84,
  mirroring RL-s0's 7 cells x 12 epochs so "equal budget" is equal in
  distribution as well as count.
- **Draw:** action uniform over the frozen 12-action grid, seeded RNG, **seed 0**
  (the parallel to RL-s0).
- **Aggregation:** per-action **median of `execution_time_s / T_ref(cell)`**.
- **Eligibility:** an action needs at least one usable observation; actions with
  none are reported ineligible, never ranked on a shorter panel (Day-31's rule).
- **Budget:** 84, unchanged.

**Why normalisation and not a balanced design.** Cell runtimes span
**2.21 s to 36.67 s - a 16.6x spread** - so a raw per-action median would select
whichever action happened to draw fast cells. Balancing coverage instead would
require exactly one observation per (action, cell) pair, and since 12 x 7 = 84
equals the budget exactly, that degenerates into the exhaustive grid: no longer
random, and a duplicate of EXP-002's TRAIN scan. Normalising by the frozen T_ref
removes the cell effect while keeping the draw genuinely random, and it reuses an
existing frozen mechanism - R3 already normalises by T_ref for precisely this
reason - rather than introducing a new constant.

**5. EXP-005 failure protocol (for DEC-014 to incorporate).** Deterministic and
**no-retry**: a failed execution is a first-class recorded observation; retries
are refused because retrying only failures biases the sample toward
configurations that fail intermittently; medians are taken over USABLE
repetitions only; a cell with fewer than 5 usable repetitions is marked
INCOMPLETE and excluded from pooled statistics with its count reported; a failed
strategy-cell does not block queue completion.

**6. Authorization design (for DEC-014 to incorporate).** Purpose-scoped, in the
shape DEC-013 Model B established: a dedicated EXP-005 entry point supplies its
own `authorize_test_cell` restricted to the seven frozen instances, leaving
`assert_train_only` and `TestSplitSealed` untouched as defaults. The AQE-on
runner authorization stays a SEPARATE clause - different purpose - and under
amendment 2 above it is no longer on EXP-005's critical path at all.

**Affected.** DEC-015 (arm framing), DEC-016 (A, B, C, E). No PLAN edit is
required - amendment 3 removes the only reason one was pending. B1/B2, the RL
policies, gamma, the StateVector, the reward, the action space, the split guards
and TEST all unchanged.

**Budget.** 232/500 now; 316/500 after the authorized B4 search. EXP-005's 245
sits on its own register line, not SC6.

**Approval.** Recorded by the operator on 2026-09-14 after the master
methodology review presented each option with its alternatives and research risk.
Supervisor counter-signature follows the M2-freeze path.

**Status.** **DECIDED** - EXP-005 is seven arms; B3 analytic, B0' in EXP-005b;
the B4 protocol is complete and its 84-execution search is authorized but NOT yet
run. No TEST execution is authorized by this entry; DEC-014 remains PENDING and
must still incorporate items 5 and 6. TEST remains sealed.

---

## DEC-018 - Operator Assumption of the Self-Imposed Supervisor Gate; Resolution of Every Open Decision

**Date.** 2026-09-14 (Day 32). **Supersedes nothing.** Purely additive.

### Context

DEC-014, DEC-015 and DEC-016 each carry a status of PENDING SUPERVISOR
APPROVAL or PENDING SUPERVISOR COUNTER-SIGNATURE. Those gates are controls
**this project created for itself** on Days 31-32. No institutional rule and no
PLAN line imposes them: PLAN line 276 requires only that a decision be
"recorded". Every other entry in this ledger was recorded by the operator.

Meanwhile the *technical* preconditions of DEC-014 are already discharged and
independently verifiable: the three replicate policies are frozen in
`models/policies/` (`policy-af41d8ae7a21d81f`, `policy-b801f4a7df200b04`,
`policy-d8fd7b9859d2feea`, plus `exp005_rl_arms.json`), and the EXP-005 failure
protocol was completed under DEC-017 item 5. Only a signature was outstanding.

### Decision A - the gate is CONVERTED, not satisfied

The operator assumes, for DEC-014, DEC-015 and DEC-016, the role the project
had reserved for a supervisor, and records the consequences of doing so.

**Stated explicitly and permanently: NO SUPERVISOR HAS REVIEWED DEC-014,
DEC-015 OR DEC-016.** This entry does not assert that one has, and no later
entry may be written so as to imply it. Every approval recorded below is an
**operator decision and nothing more**, and anyone auditing this project must
read it that way. If a supervisor reviews this work in future, that review is
recorded as a NEW entry carrying its own date; this entry is never rewritten.

**Rationale.** The gate's purpose was a second pair of eyes on an irreversible
TEST boundary. That purpose is served - imperfectly, but honestly - by the
pre-registration discipline already in force, by the fact that every
precondition is machine-checkable rather than a matter of judgement, and by
this disclosure. It would have been served not at all by a counter-signature
attributed to someone who never read the document. The project's value rests
on its audit trail; a fabricated approval inside that trail would destroy more
than it unblocked.

### Decision B - DEC-014: APPROVED (operator), Option A

TEST is opened **solely and strictly** for the frozen EXP-005 protocol at the
resolved scope: **7 instances x 7 arms x 5 repetitions = 245 TEST
executions**, charged to EXP-005's own register line and **outside** the SC6
TRAIN cap. Preconditions (b) RL policy frozen and (c) failure protocol are
SATISFIED. TEST remains sealed for every other purpose, including EXP-005b and
EXP-006, each of which requires its own decision.

### Decision C - DEC-015: counter-signature discharged by Decision A

The three-replicate disposition stands: RL-s0 (84 episodes), RL-s1 (49),
RL-s2 (42), all gamma = 0.0, TRAIN split, frozen before any TEST execution.
The EXP-005 arm count is **7**, not 9: the later DEC-014 amendment resolving
"9 arms, ~315 runs" to "7 arms, 245 runs" is the operative reading.

### Decision D - DEC-016: APPROVED (operator)

Decisions A through F as already recorded in this ledger. No change to their
content.

### Decision E - the Day-32 EXP-001 work is AUTHORIZED

`scripts/run_exp001.py`, `tests/unit/test_exp001_maintenance.py`,
`results/experiments/exp-001/` and the accompanying amendments to
`scripts/validate_day31.py` and `scripts/validate_rl_environment.py` are
adopted as operator-authorized Day-32 work.

Independently re-verified before adoption: 20 observations, 20 usable, 0
failed; `split` is `train` for all 20; `config_name` is `B0` for all 20;
`dataset_seed` is 0 for all 20; no retry; and the per-cell means, sample
standard deviations and CVs reproduce exactly from `observations.jsonl`.

### Decision F - EXP-001 acceptance statistic, and the noise reference

PLAN contradicts itself: line 308 says "run CV <= 10%", line 267 says
"**median** CV <= 10%". The two are different tests and they disagree here.

**Resolved: the acceptance statistic is the MEDIAN of the per-cell CVs**
(PLAN:267, the Day-22 deliverable row, being the more specific statement of
what the task produces). On that statistic EXP-001 = **0.045485 -> PASS**.

**The failing cell is recorded, not buried.** `F1_agg|small` has CV =
**0.118864**, which exceeds 10%. Under the "run CV" reading EXP-001 would
FAIL. This triggers PLAN risk R3's own prescribed fallback - "more reps;
report variance openly" - and the open report is this entry.

**Binding consequence, and the point of this decision.** The noise reference
used when interpreting EXP-005 is the **conservative per-cell maximum,
CV = 0.1189**, NOT the median. A difference between two EXP-005 arms that is
smaller than the noise band on the relevant cell is **not separable from
measurement noise** and must not be reported as an effect. The project passes
its gate on the median and is held to the maximum downstream. Choosing the
flattering statistic for the gate AND for the interpretation would have been
the error this entry exists to prevent.

Retro-fitting either reading onto EXP-002's already-completed sensitivity gate
is **refused**: EXP-002 declared its own internal noise rule in advance
(`experiments/exp002.yaml`, `noise_rule`) and is not reopened.

### Decision G - DEC-017 numerical correction

DEC-017 states B3 "diverges from 16 partitions only above **2.147 GB**" and
would need a cell "**5.3x larger than anything that exists**". Those are the
**raw formula's** figures. The **implemented** function snaps to the nearest
frozen level and does not diverge until **3.221225472 GB**, a margin of
**7.97x**. Verified: `b3_partitions(3.221225472) == 16`,
`b3_partitions(3.2213) == 32`.

The error is **conservative** - it understates B3's redundancy - so **no
recorded conclusion is harmed**. The corrected figures are 3.221225472 GB and
7.97x. DEC-017's text is not rewritten; this entry is the correction.

### Decision H - B3 grid snapping: DISCLOSED as an implementation choice

The snap-to-nearest-frozen-level rule in `strategies.py:128`, its choice of
*nearest* over floor or ceiling, and its tie-break toward the smaller level are
**implementation choices present only in code**. Nothing in PLAN or this ledger
authorizes them.

They are **disclosed and deliberately NOT repaired.** At the frozen sizes the
raw and snapped readings both return 16, so `B3 = B1` holds for the executed
universe independently of the choice. At PLAN's nominal large scale (~3 GB,
PLAN:115) the two readings **disagree**, which is why the choice is disclosed.
Changing the rule now - after the results that depend on it exist - would be
selection after the fact, which is the precise failure mode this project's
pre-registration discipline exists to prevent.

Also recorded, not repaired: the provenance string written into B3 artifacts
omits the snapping term; `k` is quoted as 7.45 at one point in this ledger and
7.4506 at another (code uses the exact quotient 1e9/134217728); and the
"0.0386 / 0.1320 / 0.4042 GB" size inventory omits the smaller skew=1.5
datasets backing F4_ski (0.0311 / 0.1038 / 0.3114 GB), which also resolve to 16.

### Decision I - B3 execution gate: DIRECTED

DEC-017 rules B3 "SPECIFIED but NOT EXECUTED as a TEST arm", but `resolve("B3")`
returns a usable config with no `execution_gate` provenance key, unlike B0'
which carries an explicit "NOT AUTHORIZED" gate. Nothing mechanically prevents
B3 being queued as an arm.

**Directed:** add the mechanical gate so that the code enforces the decision the
ledger already took. This adds no new decision; it makes an existing one
un-bypassable. EXP-005 runs 7 arms and B3 is not among them.

### Decision J - the state-space size-bin collapse: RECORDED as a limitation

The size-bin boundary is 512 MiB (0.5369 GB). The largest dataset anywhere in
the frozen universe is 0.4042 GB. Therefore **all 75 cells - TRAIN, VALIDATION
and TEST - occupy size bin S**; bins M and L are instantiated nowhere.
Consequences, all arithmetic over frozen numbers:

- reachable states universe-wide = 5 classes x **1** bin x 2 feedback = **10**
- reachable states in TRAIN = 4 x 1 x 2 = **8**
- **20 of the 30 nominal v1.5 states are unreachable by construction**

The 8 rows in each seed's Q-table are therefore the *complete* reachable TRAIN
set, not a sample of it; 4 of those 8 were pre-seeded from the offline EXP-002
Q0 before any episode ran, and exactly 5 states were ever entered.

**The datasets are NOT undersized.** They are PLAN's nominal logical volume
(~3 GB uncompressed at large), measured on disk after Parquet compression
(0.404 GB), exactly as this ledger already pinned for B3. What was never
recorded is that the same on-disk pin **also governs `StateVector`'s size
binning**, where it removes an entire state dimension. That extension is
recorded here explicitly.

**NOT remediated.** Regenerating the datasets at a scale that would exercise
bins M and L would invalidate every frozen artifact in the project - T_ref, the
EXP-002 grid, B1/B2, the three RL policies, the TEST freeze - at Day 32 of 50.
This is recorded as a **stated limitation of the study** and a named item in
Further Work, not as a defect to be fixed.

It follows that EXP-005 will not exercise a new state region: all 43 TEST cells
are bin S, and adding F4_ski raises the reachable set from 8 to 10. Any
EXP-006 claim about "unseen scale" must be qualified accordingly - at the
on-disk measure there is no unseen size bin anywhere in this project.

### Status

**DECIDED** - every open decision in this project is resolved by this entry.
DEC-014, DEC-015 and DEC-016 are APPROVED as **operator** decisions under
Decision A, with the absence of supervisor review recorded permanently and
without euphemism.

**EXP-005 is UNBLOCKED** at 7 instances x 7 arms x 5 repetitions = 245 TEST
executions. TEST opens for EXP-005 alone. EXP-005b and EXP-006 remain sealed
and each requires its own decision. The SC6 TRAIN ledger stands at 336/500 and
is not touched by EXP-005.

## DEC-022 | 2026-09-16 | EXP-006 execution authorization — operator approval, scope-bound to the sealed pre-execution specification

**Status.** **DECIDED (OPERATOR).** **Supervisor counter-signature: PENDING**
(conventional expectation only, exactly as DEC-020/DEC-021; DEC-018 Decision A
converted the self-imposed supervisor gate into an operator decision, and PLAN
line 276 requires only that a decision be "recorded"). **NO SUPERVISOR HAS
REVIEWED THIS ENTRY.** A future review is a new entry; this one is never
rewritten. This entry authorizes **no Spark execution by itself** — it is the
authorization *scope*; execution is performed by the frozen runner under it.

**1 — Governance basis.** DEC-018 Decision B opened TEST "solely and strictly"
for the frozen EXP-005 protocol and left it "sealed for every other purpose,
including EXP-005b and EXP-006, each of which requires its own decision". This
is that decision for EXP-006. DEC-021 §9/§14 froze the cells/arms/reps/budget
and stated `EXECUTION NOT AUTHORIZED` while the machine artifact was pending.
The artifact now exists, is sealed, and re-verifies: prerequisites are
satisfied. EXP-005 is closed descriptive-only (DEC-020 §A) and is not reopened.

**2 — Exact authorized scope (binds to the fingerprint, not to a name).**

* Experiment: **EXP-006**, protocol **`exp006/v1`**.
* Specification: `results/evaluation/exp006_spec.json`, fingerprint
  **`0f078dc2f89b726ef80a58c3b7161ded9cc071dfe48a34266725fe9872b7eb54`**
  (schema `exp006-pre-exec-spec/v1`).
* Queue fingerprint **`c88ba20c75a0654a81c2113a83aefd119a19271985bdccabd4c7ef44ec917d4c`**;
  candidate-universe fingerprint **`6150713d924b7640a9caa7aee66cc11fc781cca3b5a67fcdd91073da989b5ce3`**;
  selected-cells fingerprint **`5fea06f272345a9d7bb0e11aca9208c416dac4a1bb5a37581976c1f149da17e5`**.
* Candidate universe: **36** remaining frozen TEST cells (43 − 7 consumed by
  EXP-005; DEC-021 §1 correction applied). The universe is a pool, **not** the queue.
* Selected execution cells: **5** — `F4_ski|large|s0`, `F4_ski|large|s4`,
  `F4_ski|medium|s3`, `F4_ski|small|s3`, `F1_agg|large|s0`.
* Executable arms: **5** — `B0`, `B2` (where defined), `RL-s0`, `RL-s1`, `RL-s2`.
* Repetitions: **5** per cell×arm.
* Queue: **125** rows, indices 1–125 contiguous, all `split=test`, ordering
  deterministic (cells by family/scale/seed; arms `B0,B2,RL-s0,RL-s1,RL-s2`;
  reps 1–5 ascending).
* **105 executable Spark executions**; **20 undefined non-executable B2×F4_ski
  rows**; **125 total ledger rows**.
* Frozen identities: B0 `9270d2ce…` (AQE-off, `configs/baseline_b0.yaml`);
  B2 F1/F2 `G-p8-sp16` `285ad990…`, F3 `G-p8-sp64` `a40aaa33…`, F5 `G-p8-sp32`
  `c1821b22…` (selection artifact `0a0ecbe5…`); RL-s0 `b801f4a7…`, RL-s1
  `af41d8ae…`, RL-s2 `d8fd7b98…` (manifest `58fac8b0…`). RL seed `2` is a
  distinct arm and is never averaged or promoted.

**3 — What this authorizes, and only this.** Execution of the 105 executable
rows of *that exact artifact* on the frozen runner, against the materials those
rows reference (`data/generated/datasets/skew1_large_s0`,
`skew1.5_large_s0`, `skew1.5_large_s4`, `skew1.5_medium_s3`,
`skew1.5_small_s3` — all present). Any byte-level change to the specification,
queue, selected cells, arms, repetitions, policies, configurations, SC5 status,
or failure semantics **voids this authorization**; a re-freeze is a new entry.

**4 — What this does NOT authorize (explicit).** No scope expansion beyond the
5 cells (in particular no widening toward the 36-cell pool or the ~900-row
full-universe run); no substitution/fallback configuration; no B1 fallback for
B2 on F4_ski; no RL retraining; no retuning of B0/B2/B4 or any policy; **no B3
execution** (B3 stays analytic-only, computed separately from manifests); no
EXP-005b execution (still sealed, separate decision, separate AQE-on ledger, no
pooling); no EXP-006b/EXP-007/EXP-010; no public-dataset or F5-unseen
synthesis; no post-hoc inferential parameters; no modification of EXP-005
artifacts; no TEST-driven selection of anything.

**5 — B2 coverage limitation (carried forward, not relaxed).** B2 has exactly
**one eligible EXP-006 cell — `F1_agg|large|s0` × 5 repetitions = 5 Spark
executions**; its other 20 rows are the DEC-019-class undefined B2×F4_ski rows
(0 Spark, `NOT_EXECUTED`, null configuration, no fallback). B2's EXP-006
denominator is therefore structurally smaller than every other arm's and must be
reported as such; B2 is neither penalised nor credited for undefined rows. The
5 repetitions of one cell are **not** five independent TEST cells and must not
be reported as such.

**6 — SC5.** Retained as **NOT EVALUABLE** under the current frozen definition
(DEC-020 §E, DEC-021 §8): no pre-TEST artifact defines the "seen relative
advantage" the criterion needs, and none is invented from TEST data. EXP-006
consequently yields **descriptive generalization evidence only** — no
significance claim, no winner selection during execution, no H4/SC5 verdict.

**7 — Failure semantics (unchanged).** No retry is added; failures are
first-class observations recorded and reported; fewer than 5 usable reps in a
cell×arm = INCOMPLETE and excluded from pooled statistics (DEC-017 item 5);
missing values are never imputed. The known F3-large Windows `WinError 32`
spill/sort class is **not in this scope** (the selected non-F4 cell is F1-large),
so the slice does not hinge on that environment risk; if any execution fails,
it is preserved as a failure and never converted into an undefined row.

**8 — Status.** **`EXP-006 execution authorization = APPROVED`** (operator),
bound strictly to specification fingerprint `0f078dc2f89b726ef80a58c3b7161ded9cc071dfe48a34266725fe9872b7eb54`.
Sealed state until execution: `EXP-006 QUEUE FROZEN — EXECUTION AUTHORIZED
(scope-bound, DEC-022) — NOT YET EXECUTED`. This entry performs **0 Spark
executions** and modifies no existing artifact.


## DEC-021 | 2026-09-16 | DEC-020 clerical correction; EXP-006 ~100-run representative queue governance

**Status.** **DECIDED (OPERATOR).** No supervisor review; same standing as
DEC-018/DEC-019/DEC-020. **Supervisor counter-signature: PENDING**
(conventional expectation only; a future review is a new entry, this entry
is never rewritten). This entry authorizes **no Spark execution**.

**1 — DEC-020 correction (clerical, not methodological).** DEC-020 §B's F4
remainder list is corrected by deleting `F4_ski | large | s3`, which was
already consumed by EXP-005 (queue 106–140; Day-34 medians published) and
therefore cannot be in the remaining universe. Corrected F4 remainder (12):
large s0/s1/s2/s4 + medium s0/s1/s2/s3 + small s0/s1/s2/s3. All other
families unchanged (F1/F2/F3/F5 × 6 = 24). 43 − 7 = **36 candidate cells**,
verified `test_freeze.json`-exact with zero residual. No history rewritten.

**2 — Universe ≠ queue.** The 36 cells are the candidate TEST universe, NOT
the execution queue. The queue is the 5-cell pre-registered subset below
(§4–5). Full-universe execution would be 36 × 5 × applicable arms = 840
Spark + 60 DEC-019-class undefined rows = 900 ledger rows, a 9× redefinition
of the registered ~100-run scale (PLAN §33) — explicitly NOT authorized.
This subset is frozen before EXP-006 execution, so it is not post-hoc TEST
selection.

**3 — Registered scale respected.** Target ≈100 Spark runs (register
"~100"): 4 F4 cells × 4 arms × 5 reps = 80, plus 1 non-F4 cell × 5 arms ×
5 reps = 25, total **105 Spark executions** (+ 20 DEC-019-class B2/F4
undefined rows if the queue schema represents them = 125 ledger rows).

**4 — F4 selection (deterministic coverage rule, declared before use).**
Rule: smallest set covering {large-scale F4, medium-scale F4, small-scale
F4} plus one additional seed condition, with ties broken by lowest seed
then smallest scale-ladder position. Applied: large s0 (large, lowest seed)
+ large s4 (large, highest unseen seed) + medium s3 (medium, only s3 in
universe besides consumed s4... precisely: medium s3 is the lowest medium
seed not consumed) + small s3 (small, lowest small seed in universe).
Selected F4 cells: **large s0, large s4, medium s3, small s3** — all in
`test_freeze.json` with `split=test`, none consumed by EXP-005, justified
by scale-ladder × seed-spread coverage, never by performance.

**5 — Non-F4 selection.** Rule: unused non-F4 cell, complete 5-arm
applicability, unseen seed/scale combination, lowest environment risk under
the known F3-large WinError-32 class; ties broken by family order
(F1<F2<F3<F5), then scale ladder, then lowest seed. All 24 unused non-F4
cells tie on applicability/unseen-ness, so the rule resolves
deterministically to **F1_agg | large | s0** (first family, largest scale,
lowest seed; non-F3 by the risk preference, frozen before any inspection of
its behavior). No runtime/reward/TEST outcome consulted.

**6 — Arms.** Executable: RL-s0 (`b801f4a7…`), RL-s1 (`af41d8ae…`), RL-s2
(`d8fd7b98…`), B0 (`9270d2ce…`, AQE-off), B2 where defined
(F1/F2 → `G-p8-sp16`, F3 → `G-p8-sp64`, F5 → `G-p8-sp32`; selection artifact
`0a0ecbe5…`). Seeds stay distinct. B3 analytic-only, never queued. F4/B2 =
DEC-019-class undefined (0 Spark, no fallback, no substitution, coverage
reported).

**7 — Repetitions: 5** (PLAN §23; `EVALUATION_REPETITIONS = 5`;
evaluation_spec; EXP-005 precedent). **Failure semantics:** no retry;
failures first-class; <5 usable = incomplete (DEC-017 item 5). F3-large
risk disclosed: the selected non-F4 cell is F1-large (not F3), so the slice
does not hinge on the known risk class; any future F3 failure stays
first-class.

**8 — SC5: NOT EVALUABLE** (DEC-020 §E carried; no pre-TEST seen-advantage
artifact exists). EXP-006 stays descriptive. No inferential parameters
created. No public/F5-unseen substitution; limitation propagates to EXP-010.

**9 — Queue freeze status.** Exact 5-cell list + arms + 5 reps + budget are
frozen by this entry (§3–7). The machine queue artifact
(`results/evaluation/exp006_spec.json` + queue rows with fingerprints,
ordering, provenance) is **NOT created by this entry** — it requires the
pre-execution spec build, which is a separate step. Until then:
`EXP-006 QUEUE FROZEN (cells/arms/reps/budget) — MACHINE ARTIFACT PENDING —
EXECUTION NOT AUTHORIZED`.

## DEC-020 | 2026-09-16 | EXP-005 descriptive closure and EXP-006 conservative scope governance

**Status.** **DECIDED (OPERATOR).** No supervisor review; same standing as
DEC-018/DEC-019. PLAN requires only that a decision be "recorded" (PLAN
header; §31-row-30 "decision recorded"); where a supervisor
counter-signature is conventionally expected it is marked **PENDING** below
and never simulated. This entry authorizes **no Spark execution**.

**A — EXP-005 CLOSED as descriptive TEST evidence.** H2, H3, SC2, SC3, SC4
are **UNDECIDED** — not failed. No Wilcoxon, no Cliff's δ decision, no Holm
decision, no alpha, no minimum-n, no effect threshold, no TEST retuning.
Reason: the frozen protocol names the procedures (PLAN §1/§22–23/§31-row-33)
but freezes no parameters or hypothesis-to-comparison mapping executable for
the actual 7-arm / unequal-coverage structure (6 common cells; 3 for any B2
pair; single "trained policy" vs three frozen RL arms; B3 analytic-only).
No generic defaults are retrofitted. Sealed descriptive findings stand:
245/245 rows (195 usable + 35 F3-large failed + 15 DEC-019 INCOMPLETE),
B1 lowest 6-cell descriptive sum (30.32) with RL-s0 38.15 ≈ B4 38.34 inside
noise on 5/6 cells, B0 far slowest, statics converged on `G-p8-sp16`, RL
seeds timing-spread on identical choices, only above-noise RL-vs-static
pattern the F4 `G-p2-sp16` vs `G-p8-sp16` gap — all bound by the 11.89%
noise band (DEC-018 F).

**B — EXP-006 universe.** Restricted to the **remaining already-defined and
materially available TEST cells**: `test_freeze.json` holds 43 frozen cells;
7 consumed by EXP-005; **36 remain** (F1: large s0/s1/s2/s4 + medium/small
s4; F2: same 6; F3: large s0/s1/s2/s4 + medium/small s4; F4: large
s0/s1/s2/s4 + medium s0/s1/s2/s3 + small s0/s1/s2/s3; F5: large s0/s1/s2/s4
+ medium/small s4). Nothing new is created: no NYC Taxi/public data, no F5
unseen parameters, no synthetic substitute, no replacement family/scale —
none exists among the 43 cells or on disk (carried from DEC-016 D). The
absence propagates to EXP-010/external-validity interpretation.

**C — EXP-006 arms.** Executable: **RL-s0, RL-s1, RL-s2, B0, and B2 where a
frozen definition exists for the family** (F1/F2 → `G-p8-sp16`, F3 →
`G-p8-sp64`, F5 → `G-p8-sp32`). Three RL seeds stay distinct; no averaging,
no post-TEST seed selection or promotion. **B3 stays ANALYTIC-ONLY**
(DEC-017) — never re-queued; any deterministic comparison reported apart
from Spark observations. **B2 stays frozen and unevenly covered**: no
invented F4 config, no B1 fallback, no substitution; F4 cells preserved as
DEC-019-class undefined/incomplete with coverage explicitly reported.

**D — EXP-006 purpose (frozen).** Descriptive generalization evaluation of
the already-trained frozen policies against frozen comparators on unseen
dimensions. Not policy selection, tuning, hyperparameter search, a
replacement EXP-005 inferential test, or significance-seeking. No
retraining, no configuration changes.

**E — SC5: NOT EVALUABLE UNDER CURRENT FROZEN DEFINITION.** H4/SC5 require
"≥50% of seen relative advantage," but no pre-TEST artifact defines that
quantity: TRAIN holds only per-seed run records plus
`day29_policy_agreement.json` (agreement fractions, no advantage baseline);
VALIDATION holds only the B1/B2 selection artifacts (no RL-vs-static seen
advantage); the phrase "relative improvement seen vs unseen" (§25) names a
report shape, not a frozen number. No seen baseline is invented, no TEST
result is used to construct one, no threshold created. If a qualifying
pre-TEST artifact is later found, citing it is a new decision, not an
interpretation.

**F — No inferential retrofit.** DEC-020 specifies no alpha, minimum-n,
δ cutoff, Holm family, or hypothesis mapping. Any future formal testing
needs a separate pre-use methodology amendment. **No inferential result is
retrofitted to EXP-005 after TEST observation.**

**G — Authorization.** `EXP-006 EXECUTION = NOT YET AUTHORIZED`;
`EXP-005b EXECUTION = NOT YET AUTHORIZED`. DEC-018's EXP-005 authorization
does not transfer; DEC-020 is not execution permission. EXP-006 needs a
separate pre-execution freeze (exact queue from the §B universe) plus its
own experiment-specific authorization.

**H — EXP-005b unchanged.** Separate AQE-on experiment, separate ledger, no
pooling with EXP-005 (ARCHITECTURE_FREEZE §13), own authorization required,
no execution here.

**I — F3-large carried as limitation, not auto-exclusion.** EXP-006 does
not drop F3-large cells by default; if in scope and failing, failures are
first-class; omission needs a pre-execution documented reason, never silent
deletion. (Audit note: F3-large s0/s1/s2/s4 remain in the 36-cell universe,
so this rule has live content.)

**Exact queue status.** No exact EXP-006 cell list is frozen anywhere (no
artifact, no register row detail, no script); therefore per the mandate:
`EXP-006 scope = remaining available frozen TEST universe (36 cells above);
exact queue requires a separate pre-execution freeze` before any Spark.

**Supervisor counter-signature: PENDING** (conventional expectation only;
no PLAN line imposes it — see DEC-018 Decision A; a future review is a new
entry, this entry is never rewritten).

## DEC-019 | 2026-09-15 | EXP-005 B2 x unseen-family gap - INCOMPLETE without execution (Option A)

**Status.** **DECIDED (OPERATOR).** No supervisor review; same standing as
DEC-018. Execution state at decision time: **115 of 245** queue entries
accounted for (indices 1-115 contiguous, no duplicates, all `split=test`);
next unexecuted entry is **index 116 = B2 x F4_ski|large|s3**.

**The gap.** B2 is the per-family static baseline tuned on VALIDATION
(PLAN:154; `baseline_selection.json` map: F1_agg/F2_join = G-p8-sp16,
F3_rdd = G-p8-sp64, F5_mixed = G-p8-sp32). VALIDATION contains only
{F1_agg, F2_join, F3_rdd, F5_mixed}. F4_ski is deliberately the unseen TEST
family (PLAN section 18) and never appears in validation. B2 is therefore
**undefined on exactly the family the test set was built to withhold**.
`resolve("B2", family="F4_ski")` raises `StrategyResolutionError` ("no frozen
configuration"), pinned by `tests/unit/test_exp005_strategies.py::test_b2_is_undefined_on_the_unseen_family_f4_ski_dec019`.
Affected: **15 queue entries** - 116-120 (F4_ski|large|s3), 186-190
(F4_ski|small|s4), 221-225 (F4_ski|medium|s4). Same class of omission as
DEC-016's B3/B4 holes; PLAN defines B2 in a way that does not cover the
unseen-family case.

**Decision (Option A of A/B/C/D).** The 15 entries are recorded as
**INCOMPLETE rows with `usable=false`, 0 Spark executions**, error
`INCOMPLETE (DEC-019 Option A): ...`, `event_log_status: NOT_EXECUTED`,
`config_name/config_fingerprint: null`, provenance
`{decision: DEC-019 Option A, status: INCOMPLETE-undefined}`.
The queue is **unchanged at 245 entries** (no deletion, no reorder, no
substitution). Execution continues at index 121 after the first block and
resumes normally through 245, so 130 further ledger rows = 115 Spark runs +
15 INCOMPLETE markers. No fallback config (B would silently redefine B2
mid-experiment), no F4-specific pick (tuning on TEST, forbidden), no queue
amendment (C breaks the 245 accounting), no abort (D refused - the gap is
contained and analysable).

**Analysis consequences (binding).** B2 is analysed on the 4 seen-family
instances only (20 cells x 5 reps usable where the harness succeeds); its
F4_ski cells are reported as **undefined-by-design, not as zero or missing
at random**. Pooled B2 statistics exclude F4_ski. The 15 INCOMPLETE rows are
retained in the ledger so the 245-entry accounting verifies end to end.

**Code.** `scripts/run_exp005.py::run_continuation` handles `B2 x F4_ski`
before resolution (INCOMPLETE write + continue); any *other*
`StrategyResolutionError` aborts with a hard refusal naming the new gap, so
no second undefined case can pass silently. Verified: `--continue --plan`
reports 115 done / 130 to go / next 116 with 0 writes; `py_compile` clean;
`test_exp005_strategies.py` 24 passed + 1 skipped (B4 refusal path
unexercisable now the artifact exists).


## DEC-023 | 2026-09-17 | EXP-007 methodology freeze — A1/A2 state ablation, TRAIN-only, 168 planned live executions (Day 35)

**Status.** **DECIDED (OPERATOR).** No supervisor review; same standing as
DEC-018/DEC-020/DEC-021/DEC-022. **NO SUPERVISOR HAS REVIEWED THIS ENTRY.**
A future review is a new entry; this one is never rewritten. This entry
freezes EXP-007's **methodology only**. **`EXP-007 execution authorized =
NO`** — implementation, runners, training and any TEST evaluation are
separate future tasks requiring their own decisions. This entry performs
**0 Spark executions** and modifies no existing training, TEST or
EXP-005/006 artifact.

**0 — Governance basis.** PLAN §33 (line 314) registers EXP-007 at "~300"
runs; no exact decomposition is frozen anywhere, and per this entry's own
mandate and DEC-021's universe-vs-queue principle, "~300" is explicitly
**NOT executable authority**. The only executable constraints are: the SC6
TRAIN cap (PLAN line 45; ledger **336/500 = 184 remaining** — see §13),
the ablation definitions (PLAN §24 line 188, §31 row 36 line 282), and the
registered acceptance ("ablation table"). Acceptance is artifact-based,
not a numeric pass/fail threshold. No inferential parameters are frozen
(§10). EXP-007 is TRAIN-only (§9).

**1 — A2 wording conflict: resolved under the frozen precedence rule, not
ignored.** The mandate required a STOP if repository evidence contradicted
the interpretation "A2 = retain ONLY runtime feedback state". A
contradicting clause exists: `docs/architecture/ARCHITECTURE_FREEZE.md` §9
(line 55) says "Ablation A1 = context-only, A2 = full v1.5". However the
repository already carries a frozen precedence rule for exactly this
situation (DEC-010, "Precedence rule established here"): PLAN is the
top-level frozen research plan; ARCHITECTURE_FREEZE is a Day-12 document
DERIVED from it; **where a derived document contradicts its source, PLAN
governs**. PLAN contradicts the §9 clause in three independent places:

- PLAN §24 (line 188): "A2 workload-context removed";
- PLAN §31 row 36 (line 282): "retrain context-only / feedback-only";
- PLAN §33 (line 314): EXP-007 hypothesis "context+feedback > context-only".

Applying DEC-010, the PLAN wording governs and §9's "A2 = full v1.5" is
SUPERSEDED on this point only (pointer note appended to
ARCHITECTURE_FREEZE.md in the DEC-010 pattern; original text retained
unaltered). The conflict is therefore **recorded and resolved, not
silently interpreted**, and the mandated A2 reading is literally the PLAN
wording. No STOP condition remains open. A2 = feedback-only is frozen
below. No third A2 encoding is created.

**2 — A1 (exact frozen definition).** The existing frozen `state-v1`
encoder, exactly as implemented in `src/sparkrl/rl/state.py`
(`SCHEMA_V1 = "state-v1"`): `workload_class ∈ {agg, join, rdd_sort,
skew_join, mixed}` (5 values) × `input_size_bin ∈ {S, M, L}` (3 values);
`feedback_bin` absent — schema v1 enforces `feedback_bin is None`.
State cardinality: **5 × 3 = 15**. No new encoding. (Carried from
DEC-018 Decision J as a stated limitation, not remediated: every frozen
dataset resolves to bin S, so at most 5 × 1 = 5 of the 15 states are
reachable in practice.)

**3 — A2 (exact frozen definition).** Read literally from PLAN, "workload-
context state removed" = retain ONLY runtime feedback state. A2 is:
`feedback_bin ∈ {le0, gt0}` (the frozen `FEEDBACK_BINS` of
`src/sparkrl/rl/state.py`). Exactly **2 states**. Workload class is NOT
retained; input size bin is NOT retained. No third A2 encoding exists or
is created. The clean contrast is: full = context + feedback (main-study
reference); A1 = context only (15 states); A2 = feedback only (2 states).

**4 — Q0 initialization (exact frozen rule).** The full-state EXP-002 Q0
table (`q0-exp002/v1`, median-pooled per v1.5 state key) is NOT collapsed,
mapped or projected into A1/A2 keys: no many-to-one Q0 mapping, no
median-pooling across state keys, no arbitrary state-to-state mapping —
no such projection rule was ever frozen, so none is invented. Instead,
both A1 and A2 use the frozen default initialization from
`configs/rl.yaml`: **`q0_default = 0.5`** for every action in every
state. Recorded explicitly: **A1/A2 use identical neutral Q0
initialization so the ablation does not introduce an unfrozen Q0
projection rule.** The main-study RL Q0 is not altered and no existing
frozen policy artifact is modified.

**5 — Control variables (frozen identically across the full-state
reference, A1 and A2).** All values read from the frozen project
artifacts; none invented:

- action space = `mode12` (12 discrete configs; `configs/rl.yaml` + frozen
  manifests `contract_versions.action_mode`);
- reward = R3 (frozen formula, incl. the DEC-010 failure term);
- T_ref = the existing EXP-002 calibration (`exp002-gate:gate.json`,
  `t_ref_gate_sha256`-pinned, identical to every frozen training manifest);
- gamma = 0.0 (bandit mode; DEC-011 — the Day-30 gate failed, A5 stays
  excluded);
- epsilon = 1.0 → 0.05 (`epsilon_start` 1.0, `epsilon_min` 0.05,
  `epsilon_decay` 0.95 applied per episode);
- checkpoint semantics unchanged (episodes 25/50/75/final pattern of the
  frozen runner);
- early-stop rule unchanged (greedy snapshot identical at 3 consecutive
  epoch boundaries; `stable_epochs_required = 2` as in the frozen
  manifests);
- AQE OFF (PLAN §7; AQE-on work is EXP-005b's, sealed separately);
- same Spark runner clock (frozen runner, Day-3 semantics);
- same warmup semantics (executed, discarded, never measured);
- same TRAIN environment (`spark-tuning-env/v1`);
- same cache semantics (cache hits free; live executions only increment
  the budget; COMP-EXP-11);
- same TRAIN dataset set and dataset seed convention (`dataset_seed: 0`).

**6 — Training scope (frozen).** The already-established TRAIN cycle only:

- the **7 eligible TRAIN/T_ref cells** of the frozen main-training
  schedule: `F1_agg|small`, `F1_agg|medium`, `F2_join|small`,
  `F2_join|medium`, `F3_rdd|small`, `F5_mixed|small`, `F5_mixed|medium`
  (`F3_rdd|medium` is excluded in every frozen manifest: `t_ref_null`);
- dataset seed 0;
- same cell ordering as the main training loop
  (`fixed_round_robin_over_sorted_cells`);
- one epoch = one pass over the 7 cells; **42 planned episodes per seed**
  = 6 epochs × 7 cells.

No VALIDATION and no TEST enter training.

**7 — Replication (frozen; disclosed compromise).** A1 seeds = {0, 1};
A2 seeds = {0, 1}. Two seeds per ablation, **not** the main study's three:
a balanced two-ablation three-seed design would cost
2 × 3 × 42 = 252 > 184 remaining, which the budget does not safely permit.
Seed 2 is NOT used. This is a methodological compromise caused by the
already-consumed SC6 budget and is disclosed as a limitation (§12), not
hidden.

**8 — Execution budget (frozen).**

- A1: 2 seeds × 42 planned episodes = **84 planned live executions**;
- A2: 2 seeds × 42 planned episodes = **84 planned live executions**;
- combined planned: 84 + 84 = **168**;
- remaining TRAIN cap: 500 − 336 = **184**;
- headroom: 184 − 168 = **16** live executions.

The registry's "~300" is not interpreted as executable authority. The
existing early-stop mechanism is NOT removed: actual executions may fall
below 42 per seed if the frozen condition triggers earlier; hypothetical
episodes are never counted as executed Spark runs; **planned vs actual is
reported per seed** in the acceptance artifact. Failed episodes remain
first-class observations (DEC-010) and count toward actual executions only
when live.

**9 — No TEST.** EXP-007 is frozen as **TRAIN-only**. No TEST queue, no
TEST authorization, no TEST comparison, no TEST tuning; no EXP-007 TEST
specification is created. TEST remains sealed except as opened by its own
decisions (DEC-018 Decision B for EXP-005; DEC-022 for EXP-006). Any
future TEST evaluation of A1/A2 requires a separate pre-registered
experiment with its own queue and authorization.

**10 — No inference.** EXP-007 analysis is **descriptive**. No alpha, no
p-values, no Wilcoxon, no Cliff's δ, no Holm correction, no effect-size
threshold and no minimum-n is introduced (same discipline as DEC-020 §F).
The output is the frozen ablation table / ablation rows.

**11 — Acceptance (exact artifact requirement).** EXP-007 is accepted when
all of the following exist:

1. A1 training artifacts/rows produced (per seed, existing
   training-artifact format);
2. A2 training artifacts/rows produced (per seed, same format);
3. the exact state definitions of §2 and §3 recorded in the artifacts;
4. actual execution counts recorded (planned vs actual per seed);
5. reward/performance summaries recorded according to the existing
   training artifacts;
6. a comparison table between full state, A1 and A2.

No numerical "A1 wins if..." or "A2 wins if..." threshold is defined.

**12 — Methodological limitations (mandatory disclosure).** The decision
records, and the acceptance artifact must repeat:

1. A1/A2 use **two seeds** rather than the main study's three because only
   184 TRAIN executions remain;
2. the ablation is therefore a **controlled but lower-replication study**;
3. A1/A2 Q0 is **neutral 0.5**, unlike the main study's EXP-002-derived
   Q0, because no valid frozen projection exists for the reduced state
   spaces;
4. **no TEST generalization conclusion will be drawn from EXP-007**.

**13 — Validation (read-only, performed at decision time).**

| Check | Evidence | Result |
|---|---|---|
| `state-v1` exists | `src/sparkrl/rl/state.py` (`SCHEMA_V1`, 5 × 3 = 15, feedback_bin=None enforced) | PASS |
| `state-v1.5` exists | `src/sparkrl/rl/state.py` (`SCHEMA_V15`, v1 × {le0, gt0} = 30) | PASS |
| no existing A2 encoder conflicts with the decision | no A2/feedback-only encoder exists anywhere in the repository (searched); A2 requires the new encoder that implementation must build | PASS |
| TRAIN capacity = 184 | ledger 336/500: EXP-001 `sc6_charge` "20 TRAIN executions (316 -> 336 of 500)"; DEC-018 closing status "SC6 TRAIN ledger stands at 336/500"; DAY33 audit "TRAIN ledger 336 / 500 unchanged" | PASS |
| 168 planned executions fit | 184 − 168 = 16 ≥ 0 | PASS |
| no TEST scope introduced | §9; no TEST artifact created | PASS |
| A5 remains excluded | DEC-011 (Day-30 gate failed; γ stays 0.0; multi-step NOT enabled) | PASS |
| gamma remains 0.0 | `configs/rl.yaml` line 8; DEC-011 | PASS |
| B3 remains analytic-only | DEC-016 B / DEC-017 / DEC-020 §C | PASS |

**14 — What this entry does NOT authorize (explicit).** No A1/A2 code; no
encoder implementation; no execution runner; no training; no TEST; no
registry rewrite (the "~300" register estimate stays as recorded history);
no modification of any existing policy, manifest, EXP-002/005/006
artifact, or the main-study RL Q0. If a machine-readable pre-execution
specification is later wanted, it is a separate freeze with its own
fingerprint, in the DEC-021/DEC-022 pattern.

**Status.** **EXP-007 METHODOLOGY FROZEN (this entry). `EXP-007 execution
authorized = NO`.** Implementation and training are the next separate
tasks, each gated by their own decision. This entry performs **0 Spark
executions**. Supervisor counter-signature: **PENDING** (conventional
expectation only; a future review is a new entry, this entry is never
rewritten).

## DEC-024 | 2026-09-17 | EXP-007 TRAIN authorization gate — REFUSED; SC6 TRAIN ledger / DEC-023 remaining-figure discrepancy recorded (Day 35)

**Status.** **DECIDED (OPERATOR).** No supervisor review; same standing as
DEC-018/DEC-020/DEC-021/DEC-022/DEC-023. **NO SUPERVISOR HAS REVIEWED THIS
ENTRY.** A future review is a new entry; this one is never rewritten. This
entry is the pre-execution authorization gate DEC-023 requires ("training
... requires its own decision"). Result: **the authorization is REFUSED on
the budget check**, and the discrepancy that caused the refusal is recorded
here so it cannot recur silently. This entry performs **0 Spark executions**
and modifies no implementation file, no configuration, no stored artifact
and no prior decision entry (DEC-023 is quoted, never amended).

**1 — Governance rule applied.** DEC-018 Decision A converted the
self-imposed supervisor gate into an operator decision (PLAN requires only
that a decision be "recorded"). Authorization follows the DEC-022 pattern:
operator approval, scope-bound to a fingerprint, voided by any change to the
frozen scope. TEST rules do not transfer to TRAIN automatically (DEC-018
Decision B sealed TEST for every purpose except its own decisions). One
further condition is inherent in authorization: **the frozen plan must fit
the frozen budget.** The SC6 TRAIN cap (PLAN section 16;
`configs/rl.yaml` `live_execution_cap: 500`, frozen-validated) is a hard
research constant; a plan that can exceed it is not authorizable.

**2 — Implementation match verification (PASS, read-only).** The uncommitted
EXP-007 implementation was verified line-by-line against DEC-023: A1 = the
frozen `state-v1` encoder, exactly 15 states, `feedback_bin` absent
(`src/sparkrl/rl/state.py`); A2 = feedback-only `state-v2`, exactly 2 states
(`le0`, `gt0`), no workload class and no size bin (`FeedbackState`,
deliberately outside `SUPPORTED_SCHEMAS`); Q0 = neutral 0.5 for EVERY valid
(state, action) pair (15x12 and 2x12, `q0-neutral/v1`,
`projection_from_exp002 = False`, no EXP-002 record access — proven by
monkeypatch hard-fail); seeds A1 = {0,1}, A2 = {0,1}, seed 2 rejected by
`build_plan`; 42 planned episodes per seed = 6 epochs x 7 cells; the seven
TRAIN/T_ref cells are DERIVED, not hard-coded (`F3_rdd|medium` excluded,
`t_ref_null`); dataset seed 0 enforced; all controls unchanged (mode12, R3,
T_ref, gamma 0.0, epsilon schedule, checkpoint 25, early stop 2 stable
epochs, AQE off, same runner/environment, same cache semantics); failure
semantics carried unchanged (DEC-010 first-class failures; no automatic
retries, substituted runtimes, invented rewards, altered T_ref or fallback
policies). Full unit suite re-run at gate time: 560 collected, exit 0
(559 passed + 1 pre-existing skip), EXP-007 test files included.

**3 — Budget verification (FAIL — the decisive check).** Exact arithmetic,
every line cited:

| Component | Executions | Evidence |
|---|---|---|
| SC6 TRAIN cap | 500 | PLAN section 16; `configs/rl.yaml` line 17 ("frozen cap (PLAN section 16 / SC6); env owns the guard") |
| Day-27/29 training | 232 | DEC-011: "(5 runs x 3) + 217 training ... = **232** of the frozen 500"; confirmed by manifest sum over `results/training/**/manifest.json` at gate time |
| B4 TRAIN calibration | +84 | DEC-016 C: "Projected cost: 84 executions, taking the ledger from 232 to 316 of 500"; executed (commit `9e83742` "B4 TRAIN calibration complete - 84/84") |
| EXP-001 noise calibration | +20 | `results/experiments/exp-001/spec.json`, verbatim: `"sc6_charge": "20 TRAIN executions (316 -> 336 of 500)"`; DEC-018 closing status: "The SC6 TRAIN ledger stands at 336/500"; DAY33 audit: "TRAIN ledger 336 / 500 unchanged" |
| **Recorded spend** | **336** | 232 + 84 + 20 |
| **Remaining** | **164** | 500 − 336 |

DEC-023 froze "remaining TRAIN cap: 500 − 336 = **184**" (section 8, repeated
in sections 0, 7, 12 and 13). That frozen figure equals **500 − 316**, the
ledger state BEFORE the EXP-001 charge; the derivation line as written is
arithmetically false (500 − 336 = **164**), and DEC-023's own section 13
evidence row cites the EXP-001 charge "316 -> 336" while asserting "TRAIN
capacity = 184 ... PASS". The tension was disclosed, not hidden, by the
implementation: `src/sparkrl/training/ablation.py` encodes the frozen figure
184 verbatim with an explicit NOTE that the section 8 ledger citation reads
336/500 and that the frozen figure governs without re-derivation.

EXP-007's combined planned maximum is 84 + 84 = **168 planned live
executions > 164 recorded remaining**. Full planned execution would take the
TRAIN total to 336 + 168 = **504 > 500**, breaching the frozen cap by up to
4 live executions. Nothing technical would prevent this: the env budget
counter is per-process and in-run only; cross-run SC6 totals are "REPORTED
not enforced (COMP-EXP-11 deferred)" (`src/sparkrl/training/loop.py`,
`BUDGET_ENFORCEMENT_NOTE`). Only governance prevents the breach — which is
this gate.

**4 — Decision.** **`EXP-007 TRAIN execution = NOT AUTHORIZED` (REFUSED).**
The frozen EXP-007 scope (DEC-023: the seven TRAIN/T_ref cells, dataset seed
0, A1 seeds {0,1}, A2 seeds {0,1}, 42 planned episodes per seed, combined
168 planned live executions) **does not verifiably fit the recorded
remaining TRAIN capacity (164)**. No partial authorization is granted
either: the episode count and the seed set are frozen by DEC-023, and
re-scoping them is a methodology change requiring its own pre-registered
decision, not a gate by-product.

**5 — What this entry does NOT do (explicit).** No implementation change; no
configuration change; no amendment of DEC-023 (its frozen figures stand as
recorded history; the discrepancy is recorded HERE, in a new entry, in the
DEC-021 clerical-correction tradition — a correction is a new entry, the
corrected entry is never rewritten); no ledger re-derivation and no
re-designation of any executed run (in particular, EXP-001's 20 TRAIN
executions are NOT re-designated as non-charging: they are real TRAIN-split
live Spark executions whose charge is declared by EXP-001's own artifact);
no TEST queue, specification or ledger (**EXP-007 TEST execution = NOT
AUTHORIZED / NOT PART OF EXP-007**, unchanged); no seed 2; no A5 (DEC-011);
no retuning; no inference methodology (EXP-007 output remains DESCRIPTIVE
ONLY, DEC-023 section 10); no scope expansion. Supervisor counter-signature:
**PENDING** (conventional expectation only; never simulated).

**6 — Implementation binding (recorded for the future authorization).** HEAD
commit `5cf0cf850f022750fa7df734328f6807e3546ee9` ("docs(day33): complete
the record correction; fix an error in the correction itself"). DISCLOSED:
DEC-020..DEC-023 and the entire EXP-007 implementation are UNCOMMITTED
working-tree state on top of that commit; no commit was manufactured for
this gate. SHA-256 fingerprints of the binding files at gate time:
`src/sparkrl/rl/state.py` = `3ce6ee042829b4374776617fdf74f1f7a375905d35e414a577823b149911bda0`;
`src/sparkrl/agent/q0.py` = `7d2ffb0c33fc4349a71d3e064781927425092ff86be2eeed595705b3111de195`;
`src/sparkrl/training/ablation.py` = `fe0363535f6c9ef98ba1771fc2afd9f2aed8caa78f4d5f9d31c534bd8857f55a`;
`src/sparkrl/training/loop.py` = `cca3c643c0e2c56e3d6a61c6358bfca771833ac72d57ebd7a5ea3ea79bf2a94b`;
`scripts/run_training.py` = `e9cc044231a2663bd9cbc39eff3c8bb5633df6b98198b3fe343c0e872a3e3fb4`;
`configs/rl.yaml` = `8ca70d6dd7df68841c409a4441dc538616206bccea7877b28c73df20e6428b80`.
Any byte-level change to these files before a future authorization voids
that fingerprint and requires re-verification.

**7 — Unblocking path (recorded, NOT executed here).** A separate operator
decision must either (a) re-derive the feasible EXP-007 scope from the
corrected remaining figure of 164 (fewer planned episodes per seed, or one
seed per arm = 84 planned, headroom 80 — a DEC-023 scope amendment with its
own limitation disclosure), or (b) record a justified ledger reconciliation.
Until such an entry exists, `EXP-007 execution authorized = NO` (unchanged
from DEC-023).

**Status.** **EXP-007 EXECUTION AUTHORIZATION REFUSED (this entry).
`EXP-007 execution authorized = NO` (unchanged from DEC-023). SC6 TRAIN
ledger: 336/500 recorded; 164 remaining; the 168-execution frozen maximum
does not fit.** This entry performs **0 Spark executions**.

## DEC-025 | 2026-09-17 | EXP-007 TRAIN budget reconciliation and execution-horizon amendment (Day 35)

**Status.** **DECIDED (OPERATOR).** No supervisor review; same standing as
DEC-018/DEC-020/DEC-021/DEC-022/DEC-023/DEC-024. **NO SUPERVISOR HAS REVIEWED
THIS ENTRY.** A future review is a new entry; this one is never rewritten.
This entry is the pre-execution scope amendment DEC-024 section 7(a)
anticipates ("re-derive the feasible EXP-007 scope from the corrected
remaining figure of 164 ... a DEC-023 scope amendment with its own limitation
disclosure"). It is a **GOVERNANCE AMENDMENT ONLY**: it amends ONE frozen
field of DEC-023's training scope (episodes per seed 42 → 35) and performs
**0 Spark executions**. It modifies no implementation file, no configuration,
no stored artifact and no prior decision entry — **DEC-023 and DEC-024 are
quoted, never rewritten** (DEC-021 clerical-correction tradition). It does
not itself authorize execution: `EXP-007 execution authorized = NO` remains
unchanged until the implementation amendment and its own future gate.

**1 — Authoritative budget (corrected ledger).** The authoritative SC6 TRAIN
budget is re-derived from repository evidence, superseding DEC-023's frozen
"remaining = 184" figure for forward-looking purposes (the frozen figure
stands as recorded history in DEC-023 and is not edited):

| Component | Executions | Evidence (verified read-only at decision time) |
|---|---|---|
| SC6 TRAIN cap | 500 | PLAN section 16; `configs/rl.yaml` `live_execution_cap: 500` (frozen cap, never raised) |
| Day-27/29 training | 232 | manifest sum over `results/training/**/manifest.json` = 232 (re-summed at decision time; 10 manifests) |
| B4 TRAIN calibration | +84 | DEC-016 C; commit `9e83742` "B4 TRAIN calibration complete - 84/84" (verified in `git log`) |
| EXP-001 noise calibration | +20 | `results/experiments/exp-001/spec.json` verbatim: `"sc6_charge": "20 TRAIN executions (316 -> 336 of 500)"` |
| **Authoritative spent before EXP-007** | **336** | 232 + 84 + 20 |
| **Authoritative remaining** | **164** | 500 − 336 = 164 |

This confirms DEC-024's corrected figure and supersedes DEC-023's
"500 − 336 = 184" as an arithmetic statement (500 − 336 = **164**; the 184
figure equals 500 − 316, the ledger state before the EXP-001 charge). The 20
EXP-001 TRAIN executions are real TRAIN-split live executions and ARE counted
(DEC-024 section 5: they are NOT re-designated as non-charging).

**2 — Previous DEC-023 scope (quoted, not amended).** DEC-023 froze:
A1 seeds {0, 1}; A2 seeds {0, 1}; **42 episodes/seed** = 6 epochs × 7 cells;
A1 = 84 + A2 = 84 = **168 maximum planned live executions** (section 8).
DEC-024 proved that maximum cannot fit the authoritative remaining budget:
168 > 164; full planned execution would take the TRAIN total to
336 + 168 = 504 > 500, breaching the frozen cap by up to 4 live executions.
That is why EXP-007 execution remains blocked; this entry removes the
blockage by shrinking the horizon, not by touching the ledger.

**3 — Corrected scope.** PRESERVED unchanged from DEC-023 (quoted from its
sections 2–7):

- A1 = the frozen `state-v1` encoder (5 × 3 = 15 states, context only,
  `feedback_bin` absent);
- A2 = the frozen feedback-only space (`feedback_bin ∈ {le0, gt0}`,
  exactly 2 states; no workload class, no size bin);
- A1 seeds = {0, 1}; A2 seeds = {0, 1}; seed 2 NOT used;
- the same seven TRAIN/T_ref cells (`F1_agg|small`, `F1_agg|medium`,
  `F2_join|small`, `F2_join|medium`, `F3_rdd|small`, `F5_mixed|small`,
  `F5_mixed|medium`; `F3_rdd|medium` excluded, `t_ref_null`);
- dataset seed 0; same action space (`mode12`); same reward (R3 incl. the
  DEC-010 failure term); same T_ref (EXP-002 calibration, pinned); same
  gamma (0.0); same epsilon schedule (1.0 → 0.05, decay 0.95 per episode);
  same Q0 = neutral `q0_default = 0.5`; same checkpoint semantics; same
  early-stop semantics (`stable_epochs_required = 2`, greedy snapshot at
  consecutive epoch boundaries); same environment (`spark-tuning-env/v1`);
  same cell ordering (`fixed_round_robin_over_sorted_cells`); AQE off;
  same cache semantics (cache hits free; live executions only increment the
  budget); TRAIN-only scope; descriptive-only analysis; A5 excluded
  (DEC-011).

AMENDED — exactly ONE field:

- **episodes per seed: 42 → 35** (= 5 epochs × 7 cells).

**4 — Why 35 episodes (methodological rationale).** Each epoch is one
complete pass over the 7 frozen TRAIN cells in the fixed round-robin order.
Therefore **35 episodes = 5 complete epochs × 7 cells**, preserving the
round-robin cell-cycle structure exactly (every seed sees each of the 7
cells exactly 5 times). Alternatives are rejected:

- **40 is rejected** because 40 is not an integer number of complete 7-cell
  epochs (40 = 5 × 7 + 5); it would truncate the cycle and break the
  round-robin symmetry;
- **42 is rejected** because 42 × 4 runs = 168 > 164 authoritative remaining
  (DEC-024);
- **dropping a seed is rejected** because that would destroy the two-seed
  symmetry frozen in DEC-023 section 7 and asymmetrically punish one
  ablation;
- **fewer than 35 with both seeds kept** was not chosen because 35 is the
  largest integer-epoch horizon that fits (the next integer-epoch candidate
  is 6 × 7 = 42, which does not fit).

**5 — New execution budget (frozen).**

- A1: 2 seeds × 35 planned episodes = **70 maximum live executions**
  (2 × 35 = 70);
- A2: 2 seeds × 35 planned episodes = **70 maximum live executions**
  (2 × 35 = 70);
- combined planned maximum: 70 + 70 = **140**;
- remaining SC6 capacity: 500 − 336 = **164**;
- headroom: 164 − 140 = **24** live executions.

Arithmetic, explicit: 2 × 35 = 70; 70 + 70 = 140; 500 − 336 = 164;
164 − 140 = 24. Full planned execution would take the TRAIN total to
336 + 140 = 476 ≤ 500. **140 is the authoritative EXP-007 maximum.**

**6 — Early stopping (unchanged; 35 is a ceiling, not a guarantee).** The
existing early-stop rule is kept unchanged (greedy snapshot identical at 3
consecutive epoch boundaries; `stable_epochs_required = 2`). 35 is the
**maximum planned horizon per seed**; actual executions can be LESS than 35
per seed if the existing early-stop rule terminates a run earlier. 35 is NOT
treated as a guaranteed execution count. Hypothetical episodes are never
counted as executed Spark runs; **planned vs actual is reported per seed**
in the acceptance artifact (DEC-023 section 11, item 4, unchanged). Failed
episodes remain first-class observations (DEC-010) and count toward actual
executions only when live.

**7 — What this entry does NOT change (explicit).** This amendment does NOT
change: the A1 state definition; the A2 state definition; state
cardinalities (15 and 2); Q0 (neutral 0.5); seeds ({0, 1} per arm; seed 2
and seed 4 unused); the seven TRAIN cells; the dataset seed (0); the action
space (`mode12`); the reward (R3); T_ref; gamma (0.0); the epsilon schedule;
checkpoint behavior; early stopping; AQE (off); cache semantics (cache hits
free); the TRAIN-only scope; the descriptive-only analysis discipline (no
inferential testing); the TEST prohibition; or the A5 exclusion (DEC-011).
**Only the episode horizon changes: 42 → 35.**

**8 — TEST.** `EXP-007 TEST = NOT AUTHORIZED / NOT PART OF EXP-007`
(unchanged from DEC-023 section 9 and DEC-024 section 5). No TEST queue; no
TEST specification; no TEST execution; no transfer of the EXP-006
authorization (DEC-022) or the EXP-005 authorization (DEC-014/DEC-018
Decision B). TEST remains sealed except as opened by its own decisions.

**9 — Acceptance (unchanged from DEC-023 section 11).** The DEC-023
acceptance requirement is kept as-is: A1 rows; A2 rows; the exact state
definitions of DEC-023 sections 2 and 3 recorded in the artifacts; planned
vs actual executions per seed; reward/performance summaries; and a
full-state vs A1 vs A2 comparison table. **No numerical pass/fail threshold
is defined and no inferential testing is introduced** (descriptive only).

**10 — Limitation disclosure (mandatory).** The acceptance artifact must
repeat: (1) the original 42-episode scope of DEC-023 was infeasible after
correcting the SC6 ledger (DEC-024); (2) the revised 35-episode scope is
budget-compliant (140 ≤ 164, headroom 24); (3) both ablations retain two
seeds {0, 1}; (4) **each seed now has five complete TRAIN epochs instead of
six** — a replication-horizon reduction of one epoch per seed, which may
reduce late-episode convergence evidence and makes the ablation a slightly
weaker lower-replication study than DEC-023 §12 already disclosed;
(5) this is a **pre-execution methodology amendment, not a post-result
adjustment** — no result exists to adjust; (6) **no EXP-007 execution has
occurred** (verified: `results/training/` contains no A1/A2 ablation runs;
the ledger sum 232 is unchanged by EXP-007; Spark execution count for
EXP-007 = 0).

**11 — Implementation consequence (NOT implemented here).** This entry does
NOT implement the change. After DEC-025 is recorded, the NEXT SEPARATE task
must update the EXP-007 implementation/planning code from
`42 episodes/seed` to `35 episodes/seed` — specifically the frozen scope
constants in `src/sparkrl/training/ablation.py`
(`ABLATION_EPOCHS = 6` → 5, `SC6_REMAINING = 184` → the authoritative 164,
and the module docstring) — and update the tests accordingly
(`tests/unit/test_exp007_scope.py` Gate F figures: 42 → 35 episodes,
84 → 70 per arm, 168 → 140 combined, 184 → 164 remaining, 16 → 24
headroom). Note: DEC-024 section 6 recorded SHA-256 fingerprints of the
binding files; the implementation-amendment task necessarily voids those
fingerprints and must state so, requiring re-verification at the future
authorization gate. **Do not train during the decision task; training is
not performed here.**

**12 — Validation (read-only, performed at decision time).**

| Check | Evidence | Result |
|---|---|---|
| authoritative remaining budget = 164 | cap 500; spent 336 = 232 (manifest sum over `results/training/**/manifest.json`, re-summed) + 84 (commit `9e83742`) + 20 (`results/experiments/exp-001/spec.json` `"316 -> 336 of 500"`); 500 − 336 = 164 | PASS |
| revised planned maximum = 140 | 2 × 35 = 70 (A1) + 2 × 35 = 70 (A2) = 140 | PASS |
| headroom = 24 | 164 − 140 = 24; 336 + 140 = 476 ≤ 500 | PASS |
| 35 episodes = 5 complete epochs | 1 epoch = 7 TRAIN cells (DEC-023 section 6, `fixed_round_robin_over_sorted_cells`); 35 = 5 × 7 | PASS |
| execution arithmetic is per-episode, NOT 35 × 7 = 245 | `src/sparkrl/training/loop.py` `build_plan`: `budget_limit = int(episodes)` (line 524) — one live execution per episode/cell transition; planned live maximum per seed = **35**, not 245 | PASS |
| 140 fits 164 with no cap breach | 140 ≤ 164; combined full-run TRAIN total 336 + 140 = 476 ≤ 500 | PASS |
| no EXP-007 execution occurred | `results/training/` unchanged (232); 0 Spark executions by this entry | PASS |
| DEC-023/DEC-024 intact | both entries quoted, never edited; only this new entry appended to `DECISIONS.md` | PASS |
| no TEST scope introduced | §8; no TEST artifact created | PASS |
| A5 remains excluded / gamma 0.0 | DEC-011; `configs/rl.yaml` | PASS |

**13 — What this entry does NOT authorize (explicit).** No A1/A2 training
(Spark = 0); no implementation change (the 42 → 35 code change is the next
separate task); no configuration change; no amendment of any prior decision
entry; no ledger re-derivation or re-designation of any executed run
(in particular the 20 EXP-001 TRAIN executions stay charged); no TEST; no
seed 2; no A5; no retuning; no inference methodology; no scope expansion
beyond the single amended field; no raise of the 500 cap. Supervisor
counter-signature: **PENDING** (conventional expectation only; never
simulated).

**Status.** **DEC-025 RECORDED (this entry). EXP-007 TRAIN budget
reconciled: remaining = 164; revised planned maximum = 140; headroom = 24.
Amended field: episodes per seed 42 → 35 (= 5 epochs × 7 cells).
`EXP-007 execution authorized = NO` (unchanged) — the horizon amendment
must first be implemented in the next separate task and pass its own
authorization gate. `EXP-007 TEST = NOT AUTHORIZED / NOT PART OF
EXP-007`. This entry performs 0 Spark executions.**

## DEC-026 | 2026-09-17 | EXP-007 TRAIN authorization — APPROVED (operator), scope-bound to the DEC-025 amended A1/A2 implementation fingerprints (Day 35)

**Status.** **DECIDED (OPERATOR).** **Supervisor counter-signature: PENDING** (conventional expectation only, exactly as DEC-020/DEC-021/DEC-022/DEC-023/DEC-024/DEC-025; DEC-018 Decision A converted the self-imposed supervisor gate into an operator decision, and PLAN line 276 requires only that a decision be "recorded"). **NO SUPERVISOR HAS REVIEWED THIS ENTRY.** A future review is a new entry; this one is never rewritten. This entry is the pre-execution authorization gate that DEC-024 section 7 and DEC-025's closing status require ("the horizon amendment must first be implemented in the next separate task and pass its own authorization gate"). It performs **0 Spark executions**, trains nothing, creates no run directory, creates no TEST artifact, and modifies no prior decision entry, no implementation file, no configuration and no stored artifact.

**0 — Governance basis (the rule actually applied).** DEC-018 Decision A: the supervisor gate this project created for itself was CONVERTED into an operator decision, because PLAN line 276 requires only that a decision be "recorded". Authorization therefore follows the DEC-022 pattern: **operator approval, scope-bound to a fingerprint, voided by any byte-level change to the frozen scope.** No supervisor approval is a prerequisite for TRAIN under the repository's existing convention, and none is simulated. The preconditions DEC-023/DEC-024/DEC-025 set are all now satisfied:

1. methodology frozen (DEC-023);
2. budget reconciled from the authoritative ledger (DEC-025: remaining 164, maximum 140, headroom 24);
3. the amended horizon IMPLEMENTED and independently re-verified (section 6 below);
4. the frozen plan verifiably fits the frozen budget (section 2 below);
5. TRAIN is not TEST: TEST rules do not transfer (DEC-018 Decision B; section 12 below).

**1 — Precondition check: DEC-026 is the next entry and no later decision exists.** The ledger was read in full at gate time (1991 lines; headings DEC-001 ... DEC-025, terminating at DEC-025's status paragraph). **No DEC-026 and no later decision was present before this entry.** The DEC-023 A2 / `ARCHITECTURE_FREEZE.md` §9 wording conflict was already recorded and resolved under DEC-010's precedence rule (DEC-023 section 1) and is NOT reopened here.

**2 — Authoritative budget re-verification (PASS).**

| Component | Executions | Evidence (re-verified read-only at gate time) |
|---|---|---|
| SC6 TRAIN cap | 500 | PLAN section 16 (line 45); `configs/rl.yaml` line 17 `live_execution_cap: 500` (frozen, never raised) |
| Day-27/29 training | 232 | re-summed at gate time over `results/training/**/manifest.json` (10 manifests: 3+3+3+3+3+0+42+84+49+42 = 232) |
| B4 TRAIN calibration | +84 | DEC-016 C; commit `9e83742` "B4 TRAIN calibration complete - 84/84" (verified in `git log`) |
| EXP-001 noise calibration | +20 | `results/experiments/exp-001/spec.json` verbatim: `"sc6_charge": "20 TRAIN executions (316 -> 336 of 500)"` |
| **Authoritative spent** | **336** | 232 + 84 + 20 |
| **Authoritative remaining** | **164** | 500 - 336 = 164 |
| EXP-007 maximum | 140 | A1 2 x 35 = 70; A2 2 x 35 = 70 (DEC-025 section 5) |
| **Headroom** | **24** | 164 - 140 = 24 |

Arithmetic, explicit: 232 + 84 + 20 = 336; 500 - 336 = 164; 2 x 35 = 70; 70 + 70 = 140; 164 - 140 = 24; **336 + 140 = 476 <= 500**. DEC-023 section 8's frozen "remaining = 184" (= 500 - 316, the ledger state BEFORE the EXP-001 charge) is **NOT used** for this gate; it stands only as recorded history inside DEC-023, which is not edited here. Unit tests, dry-run planning calls, skipped tests and hypothetical episodes are **NOT** live Spark executions and charge nothing.

**3 — Exact authorized execution scope (the whole of it).**

* **Experiment:** EXP-007 (`EXP007_ID = "EXP-007"`), TRAIN only, descriptive output only.
* **A1** = the existing frozen `state-v1` context-only encoder, reused unchanged (`src/sparkrl/rl/state.py`, `SCHEMA_V1`): `workload_class` in {agg, join, rdd_sort, skew_join, mixed} (5) x `input_size_bin` in {S, M, L} (3), `feedback_bin` absent (schema v1 forces `feedback_bin is None`). **15 states.**
* **A2** = the frozen feedback-only space (`SCHEMA_V2 = "state-v2"`): `feedback_bin` in {le0, gt0} ONLY; no workload class, no input-size bin; distinct value object `FeedbackState`, deliberately outside `SUPPORTED_SCHEMAS`. **2 states.**
* **Seeds:** A1 = {0, 1}; A2 = {0, 1}. Seed 2 is NOT used; seed 4 is refused; seed semantics stay distinct (`agent_rng_seed` = exploration replicate, `dataset_seed` = workload instance seed).
* **Episodes per seed:** **35** = **5 complete epochs x 7 TRAIN cells** (DEC-025 sections 3-5; the single field amended from DEC-023's 42 = 6 x 7). 35 is a ceiling, not a guarantee (section 8).
* **TRAIN cells (exactly seven, DERIVED from calibrated T_ref intersected with TRAIN, never hard-coded):** `F1_agg|small`, `F1_agg|medium`, `F2_join|small`, `F2_join|medium`, `F3_rdd|small`, `F5_mixed|small`, `F5_mixed|medium`. **`F3_rdd|medium` remains EXCLUDED (`t_ref_null`).** Cell ordering unchanged: `fixed_round_robin_over_sorted_cells`.
* **Dataset seed:** **0** (the only T_ref-calibrated TRAIN dataset seed).
* **Maximum live executions:** **140** = A1 (2 x 35 = 70) + A2 (2 x 35 = 70).
* **Remaining SC6 budget:** **164**; **headroom: 24**.
* **Reference condition (quoted, not re-executed):** the main-study full `state-v1.5` policy — the DEC-023 comparison is full-state vs A1 vs A2; nothing in the main study is re-run, retrained or modified by this authorization.

**4 — Controls (all unchanged; the ablation differs ONLY in the state space).** `mode12` action space; reward **R3** (frozen formula incl. the DEC-010 failure term); **T_ref** = the existing EXP-002 calibration (`results/experiments/exp-002/analysis/gate.json`, `t_ref_gate_sha256`-pinned, identical to every frozen manifest); **gamma = 0.0** (DEC-011 bandit mode; A5 stays excluded); **epsilon** 1.0 -> 0.05 with `epsilon_decay` 0.95 per episode; **checkpoint** semantics unchanged (`checkpoint_every_episodes = 25`); **early stop** semantics unchanged (`EARLY_STOP_STABLE_EPOCHS = 2`, greedy snapshot identical at consecutive epoch boundaries); **AQE OFF** (PLAN section 7; AQE-on remains EXP-005b's, sealed); the same frozen Spark runner clock; the same warmup semantics (executed, discarded, never measured); the same TRAIN environment (`spark-tuning-env/v1`); the same cache semantics (cache hits free; only live executions increment the budget; COMP-EXP-11); **Q0 = neutral 0.5** for EVERY valid (state, action) pair (`q0-neutral/v1`, `projection_from_exp002 = False`, no EXP-002 record access — proven by monkeypatch hard-fail); the neutral Q0 is used by BOTH arms so the ablation introduces no unfrozen Q0 projection.

**5 — Implementation fingerprints (RE-FINGERPRINTED at this gate; DEC-024's three amended-file hashes are VOID per DEC-025 section 11).**

| File | SHA-256 at this gate | Status vs DEC-024 section 6 |
|---|---|---|
| `src/sparkrl/training/ablation.py` | `69ab9c40e1688405b8b6f795783ada7fbf26c753bacb76d0aba215b7fb5b216a` | **AMENDED** (42 -> 35; 184 -> 164); DEC-024 hash `fe036353...` VOID |
| `src/sparkrl/training/loop.py` | `b513238d5148a16cc8e39283526082b0c199fee5ad7a00326d95f4ad3983a611` | **AMENDED** (variant guards/limits); DEC-024 hash `cca3c643...` VOID |
| `scripts/run_training.py` | `69a4752d527e8d023075f97617d99e4be54a331c19be468dba2ef7badfb18ec5` | **AMENDED** (`--variant` help text 35/35); DEC-024 hash `e9cc0442...` VOID |
| `src/sparkrl/rl/state.py` | `3ce6ee042829b4374776617fdf74f1f7a375905d35e414a577823b149911bda0` | **UNCHANGED** — identical to DEC-024 |
| `src/sparkrl/agent/q0.py` | `7d2ffb0c33fc4349a71d3e064781927425092ff86be2eeed595705b3111de195` | **UNCHANGED** — identical to DEC-024 |
| `configs/rl.yaml` | `8ca70d6dd7df68841c409a4441dc538616206bccea7877b28c73df20e6428b80` | **UNCHANGED** — identical to DEC-024 |

HEAD is commit `5cf0cf850f022750fa7df734328f6807e3546ee9`; as DEC-024 section 6 disclosed, DEC-020..DEC-026 and the entire EXP-007 implementation are UNCOMMITTED working-tree state on top of it (no commit was manufactured for this gate). **Any byte-level change to any of the six files above, to the A1/A2 definitions, to the seven-cell set, to the five-epoch horizon, to the seeds, to the dataset seed or to any control in section 4 VOIDS this authorization; a re-freeze is a new entry.**

**6 — Implementation re-verification against DEC-025 (read-only, PASS).** `src/sparkrl/training/ablation.py`: `ABLATION_SEEDS = (0, 1)`; `ABLATION_EPOCHS = 5`; `ABLATION_TRAIN_CELLS = 7`; `ABLATION_EPISODES_PER_SEED = 35`; `SC6_LIVE_CAP = 500`; `SC6_LEDGER_CITED = "336/500"`; `SC6_REMAINING = 164`; `planned_executions("A1") == planned_executions("A2") == 70`; `combined_planned() == 140`; `sc6_headroom() == 24`; DEC-023's frozen 184/16 are retained only as documented history. `src/sparkrl/training/loop.py` (`build_plan`): a variant plan accepts `agent_rng_seed` in {0, 1} ONLY (seed 2 refused with an explicit "seed 2 is NOT used" message; seed 4 refused), refuses more than 35 planned episodes (`BudgetPlanError`), defaults `budget_limit` to the planned episode count so a variant run can never exceed 35 live executions, refuses `budget_limit > 500`, refuses any TEST cell and any non-TRAIN dataset seed (`dataset_seed=3` by SPLIT, seeds 1/2 by T_REF CALIBRATION, only seed 0 calibrated), and DERIVES the seven cells (never hard-coded) with `F3_rdd|medium` excluded as `t_ref_null`; the main-study path (`variant=None`, `SCHEMA_V15`, EXP-002 Q0) is untouched. `scripts/run_training.py` exposes `--variant {A1, A2}` with the amended 35-episodes help text and no epsilon/alpha/gamma/checkpoint flag; its default remains the main study. `src/sparkrl/rl/state.py`: `SCHEMA_V2` is feedback-only, outside `SUPPORTED_SCHEMAS`; `SUPPORTED_SCHEMAS` is still the frozen `(state-v1, state-v1.5)` pair. `src/sparkrl/agent/q0.py`: `build_neutral_q0` writes `q0_default = 0.5` for all 15x12 / 2x12 pairs, reads no EXP-002 record store (monkeypatch hard-fail proves it), and the main-study `build_q0_from_exp002` is untouched.

**7 — Non-Spark validation performed at this gate (PASS).**

| Check | Command | Result |
|---|---|---|
| EXP-007 unit tests | `python -m pytest tests/unit/test_exp007_state.py tests/unit/test_exp007_scope.py tests/unit/test_exp007_q0.py tests/unit/test_exp007_parity.py` | **75 passed** (32 state + 17 scope + 10 q0 + 16 parity), 0 failed |
| Full unit suite | `python -m pytest tests/unit` | **560 passed, 1 skipped, exit 0** |
| The single skip | `tests/unit/test_exp005_strategies.py:100` — "B4 search artifact exists; refusal path not exercisable" | the **pre-existing** skip already documented in DEC-024 section 2; NOT EXP-007 related, NO new skip, NO new failure |
| Integration tests | deliberately NOT run | no Spark runtime invoked |
| `scripts/run_training.py` | NOT invoked (not even `--dry-run`) | no plan object created against a real runner |

**8 — No live EXP-007 artifacts exist (verified at gate time).** `results/training/**/manifest.json` holds exactly 10 manifests whose `budget.live_executions` sum to **232** (3+3+3+3+3+0 smoke, 42+84+49+42 main study), and every one of them has an EMPTY `variant` field: **no A1/A2 ablation run directory exists**. No path under `results/` matches `exp-007`/`exp007`; no EXP-007 training manifest exists; no EXP-007 production ledger file exists anywhere in the repository; no TEST queue file exists; no EXP-007 TEST specification exists (`results/**/*spec*.json` = evaluation_spec, exp006_spec, exp-001, exp-002, exp-002-discarded-pass1, exp-005 only). The only EXP-007 artifacts in the repository are implementation and test files. **EXP-007 Spark executions to date = 0.**

**9 — Execution-count semantics (binding on the execution report).** **140 is the MAXIMUM PLANNED number of live executions, NOT a guaranteed actual count.** The existing early-stop rule is retained unchanged and may terminate a seed's run before episode 35, and per-episode step guards may abort before executing; actual executions can therefore be LESS than 140. Hypothetical, planned, cached, skipped or failed-before-execution episodes are never counted as executed Spark runs. Failed episodes remain first-class observations (DEC-010) and count toward actual executions only when live. The eventual EXP-007 execution report MUST separately report, per arm and per seed and in total: **planned**, **attempted**, **successful**, **failed**, **early-stopped**, plus actual live executions. **140 actual runs must never be fabricated if early stopping or failure reduces the count.**

**10 — What this authorizes, and ONLY this.** Execution — on the frozen runner, by the frozen loop, under the fingerprints of section 5 — of **EXP-007 TRAIN A1/A2**: A1 seeds {0, 1} at 35 planned episodes per seed; A2 seeds {0, 1} at 35 planned episodes per seed; the seven TRAIN/T_ref cells of section 3; dataset seed 0; maximum **140** live Spark executions charged to SC6 (remaining 164, headroom 24). Any byte-level change to the bound implementation, scope or controls **voids this authorization**; a re-freeze is a new entry. This entry performs **0 Spark executions** and is the authorization *scope* only; the runs themselves are performed by the frozen runner under it.

**11 — What this authorization does NOT permit (explicit and exhaustive).** DEC-026 does NOT permit:

* TEST execution of any kind;
* TEST artifact creation (no TEST queue, no TEST specification, no TEST ledger, no TEST comparison, no TEST tuning, no generalization conclusion);
* seed 2 (and no seed other than 0 and 1);
* more than 35 episodes per seed;
* more than **140** total EXP-007 live executions (the frozen 500 cap is never raised and no partial over-run is authorized);
* changing the A1 or the A2 state definitions (15 states / 2 feedback-only states, exact);
* changing Q0 (neutral 0.5 for every valid pair);
* changing the reward (R3);
* changing T_ref;
* changing gamma (0.0);
* changing the epsilon schedule (1.0 -> 0.05, decay 0.95);
* changing checkpoint or early-stop semantics;
* changing the TRAIN cell set (the seven cells of section 3);
* adding `F3_rdd|medium` (it stays excluded, `t_ref_null`);
* retuning of any kind;
* **A5** (DEC-011: the Day-30 mode gate failed; gamma stays 0.0; no multi-step);
* **B3 empirical execution** (B3 stays analytic-only, DEC-016 B / DEC-017 / DEC-020 C);
* **EXP-005b** (still sealed, separate decision, separate AQE-on ledger);
* **EXP-006** again (already authorized by DEC-022 under its own scope-bound fingerprint; this entry neither re-authorizes nor modifies it);
* **any other experiment** (EXP-001, EXP-002, EXP-003, EXP-004, EXP-005, EXP-008 ... EXP-012), and specifically EXP-008's A3/A4 register line;
* retraining, re-freezing, deleting or overwriting any existing policy, manifest, run directory, checkpoint, EXP-001/002/005/006 artifact or ledger entry;
* any inferential analysis of EXP-007 (output stays DESCRIPTIVE ONLY, DEC-023 section 10);
* any byte-level change to the frozen implementation files of section 5 during execution (such a change voids the authorization and requires re-verification).

**12 — TEST.** **`EXP-007 TEST authorization = NOT AUTHORIZED / NOT PART OF EXP-007`** (unchanged from DEC-023 section 9, DEC-024 section 5 and DEC-025 section 8). EXP-007 is TRAIN-only; no TEST queue, specification or ledger is created. **No authorization from DEC-018 Decision B (EXP-005) or DEC-022 (EXP-006) transfers to EXP-007**, and this entry neither opens nor closes TEST for anything: TEST remains sealed except as opened by its own decisions.

**13 — Acceptance at execution time (unchanged from DEC-023 section 11 / DEC-025 section 9).** The execution artifact must provide: A1 rows per seed; A2 rows per seed; the exact DEC-023 sections 2-3 state definitions recorded; planned vs actual executions per seed (section 9 above); reward/performance summaries in the existing training-artifact format; a full-state vs A1 vs A2 comparison table; and the mandatory limitation disclosure of DEC-023 section 12 + DEC-025 section 10 (two seeds, five epochs per seed, neutral Q0, no TEST generalization claim, and the 42 -> 35 amendment as a pre-execution correction). **No numerical pass/fail threshold and no inferential statistic is introduced.**

**14 — Validation of this entry (performed after recording it).**

| Check | Evidence | Result |
|---|---|---|
| DEC-026 appears exactly once | heading count in `DECISIONS.md` | PASS |
| DEC-023 / DEC-024 / DEC-025 remain intact | byte-identical prefix: the pre-DEC-026 copy `_decisions_before` has SHA-256 `24f049cd6f4fbd7eb9b3a593117f4cf6ab04bddfd13515f8d2a6e80394a54ffc` and its text equals the same range in the amended file character-for-character; DECISIONS.md was only APPENDED to | PASS |
| implementation hashes match section 5 | `Get-FileHash -Algorithm SHA256` re-run on all six files after recording | PASS (all six identical) |
| budget = 164 remaining | 500 - 336 (232 + 84 + 20); manifest re-sum = 232 | PASS |
| maximum = 140 | 2 x 35 (A1) + 2 x 35 (A2) | PASS |
| headroom = 24 | 164 - 140; 336 + 140 = 476 <= 500 | PASS |
| no execution artifact created | `results/training/**` still 10 manifests summing 232 with empty `variant`; no `exp-007`/`exp007` path; no TEST queue; no TEST specification | PASS |
| no Spark ran | this entry executed only file hashing, directory/text reads and `python -m pytest tests/unit` | PASS |

**Status.** **`EXP-007 TRAIN execution authorization = APPROVED`** (operator), bound strictly to the six implementation fingerprints of section 5 and to the DEC-025 amended scope (A1/A2 as defined, seeds {0, 1} per arm, 35 episodes per seed = 5 epochs x 7 cells, the seven TRAIN cells, dataset seed 0, **maximum 140 live executions**, remaining budget **164**, headroom **24**). Sealed state until execution: `EXP-007 TRAIN — EXECUTION AUTHORIZED (scope-bound, DEC-026) — NOT YET EXECUTED`. `EXP-007 TEST = NOT AUTHORIZED / NOT PART OF EXP-007`. Supervisor counter-signature: **PENDING** (conventional expectation only; never simulated, and not a prerequisite under DEC-018 Decision A). **This entry performs 0 Spark executions and trains nothing.**

## DEC-031 | 2026-09-18 | EXP-008 / SC6 budget reconciliation — authoritative charge 462/500, remaining 38, no cap amendment, no de-scope, no authorization (Day 37, B5)

**Status.** **DECIDED (B5 budget decision recorded).** **Supervisor counter-signature: PENDING** (conventional expectation only, exactly as DEC-020/DEC-021/DEC-022/DEC-023/DEC-024/DEC-025/DEC-026; DEC-018 Decision A converted the self-imposed supervisor gate into an operator decision, and PLAN line 276 requires only that a decision be "recorded"). **NO SUPERVISOR HAS REVIEWED THIS ENTRY.** A future review is a new entry; this one is never rewritten. This entry performs **0 Spark executions**, trains nothing, executes no TEST, creates no run directory, and modifies no result artifact, no implementation file, no configuration and no prior decision entry.

**0 — Governance basis and the DEC-number resolution (checked against the repository, not assumed).**

* `DECISIONS.md` headings end at **DEC-026** (the ledger was read in full at recording time; no later heading exists).
* **DEC-030 is already formally recorded as a decision OUTSIDE `DECISIONS.md`**: `docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md` (`Decision ID: DEC-030`; `Status: DECIDED — methodology frozen; execution NOT authorized`) with machine artifact `results/evaluation/exp008_methodology_freeze.json`. Its **identity is preserved unchanged** — this entry does not renumber it, does not fold it into another number, and does not edit it.
* No `DEC-027`, `DEC-028` or `DEC-029` decision artifact exists anywhere in the working tree, in `.kilo/worktrees/**`, or in any git object reachable from `main` or from the Cline checkpoint refs (searched by heading and by string). The prose references to "DEC-027..032 drafts" in the Day-37 preflight/audit artifacts are **non-authoritative evidence** and occupy no identifier.
* Therefore the highest formally used decision identifier is **030** and the **next sequential identifier is DEC-031** — selected because it is the next sequential ID after a formally recorded decision, **not** because any draft file used that number. (DEC-030 §10's phrase "(DEC-031 or equivalent)" for a future *authorization* decision remains satisfied by its own "or equivalent" clause; that decision remains separate and, when created, will carry its own later identifier. No text of DEC-030 is changed.)
* **Content authority.** This entry records the accounting already established, verified and published by `docs/research/DAY37_EXP008_BUDGET_RECONCILIATION.md` (SHA256 `3ab808c8…dcd9e` as published; after this entry's **additive** DEC-031 identifier note in that report's header its hash is `edba9f93…ff9b4d`, with **no accounting text changed**) and `results/evaluation/exp008_budget_reconciliation.json` (SHA256 `bd67da1735aaaa9d62ac977f2874034dca1f70db7da849db436b2ca939a596c5`, 33 236 bytes), reconstructed by the deterministic zero-Spark runner `scripts/reconcile_exp008_budget.py`. **This entry adds no new accounting and changes no figure.**

**1 — Scope.** EXP-008 / SC6 budget reconciliation only: (a) the SC6 counting rule actually applied by the decision chain; (b) the current cumulative charge; (c) the currently remaining capacity; (d) the classification of historical/stale figures; and (e) the conditional any future EXP-008 specification must satisfy. Nothing else is in scope.

**2 — SC6 cap: 500 charged live TRAIN executions.** Unchanged and **not raised**. Sources: `docs/PLAN.md` line 45 (*"SC6 = training ≤500 executions, monitoring overhead ≤5% of job time"*) and `configs/rl.yaml` line 17 (`live_execution_cap: 500 # frozen cap (PLAN section 16 / SC6); env owns the guard`). It is **one global cap**, not a per-run and not a per-experiment cap; cross-run totals are *reported*, not enforced in code (`src/sparkrl/training/loop.py`, `BUDGET_ENFORCEMENT_NOTE`: cross-run SC6 totals are "the SUM over manifests, REPORTED not enforced (COMP-EXP-11 deferred)"), which is exactly why the cap is enforced by decision governance. `docs/PLAN.md` and `configs/rl.yaml` are **not** modified by this entry.

**3 — Current authoritative cumulative charge: 462.** Continuous with the recorded decision chain and machine-reconstructed from raw manifests/artifacts:

| Component | Executions | Authority |
|---|---|---|
| Existing charged TRAIN main-training manifest chain, **including 15 charged smoke executions** | **232** | DEC-011: *"(5 runs × 3) + 217 training (42 + 84 + 49 + 42) = 232 of the frozen 500"*; re-summed from `results/training/**/manifest.json` (10 manifests: 3+3+3+3+3+0+42+84+49+42) |
| B4 TRAIN calibration | **84** | DEC-016 C (*"taking the ledger from 232 to 316 of 500"*); `results/evaluation/b4_selection.json` `budget: 84`, `split: "train"`; commit `9e83742` |
| EXP-001 TRAIN noise calibration | **20** | `results/experiments/exp-001/spec.json`: `"sc6_charge": "20 TRAIN executions (316 -> 336 of 500)"` |
| EXP-007 A1/A2 live TRAIN executions | **126** | DEC-026 authorization scope; four 2026-09-17 manifests `35 + 35 + 35 + 21 = 126` |
| **Cumulative charge** | **462** | 232 + 84 + 20 + 126 |

**4 — Exact accounting chain.** `232 + 84 + 20 + 126 = 462`. Independent cross-check: `358 (all 14 manifests, live) + 84 + 20 = 462`, and `358 − 126 = 232` reproduces DEC-011. **Remaining capacity: `500 − 462 = 38`.**

**5 — Charging and non-charging categories (the rule as actually applied, now formally recorded).**

**CHARGED (counts against SC6):**

1. **TRAIN live executions** — every real environment transition consumed by a training run's budget counter (`live_executions` in the run manifest), charged to the training register lines.
2. **Failed live executions** — a failed execution still consumes a Spark run and therefore consumes budget; failure changes the reward (DEC-010), not the charge.
3. **Smoke executions when they are part of charged TRAIN accounting** — DEC-011's `(5 runs × 3)` term charges them; the **15 live smoke executions are inside the 232 chain**. A smoke attempt with 0 live executions is still a charged row at 0.
4. **The non-manifest TRAIN charges bound by decision** — B4's 84 (DEC-016 C) and EXP-001's 20 (its own spec, kept charged by DEC-024 §5).

**NOT CHARGED:**

1. **Undefined/unexecuted planned rows** — e.g. EXP-007's 14 unexecuted planned rows, EXP-006's 20 undefined B2×F4_ski rows (DEC-019 class), and every planned row that never ran. Plan is not charge.
2. **Cache hits** — a replayed/cached transition consumes no live Spark execution.
3. **EXP-003 validation** — `results/evaluation/validation_observations.json` (96 observations): separate register line, validation split, charged **0**.
4. **EXP-005 TEST** — 245/245 TEST observations, charged **0** (TEST seal, DEC-018 Decision B).
5. **EXP-006 TEST** — 125/125 TEST observations, charged **0**.
6. **EXP-002 historical sensitivity-grid executions** — 208 recorded attempts (192 grid + 16 reference; 189 COMPLETED + 19 FAILED), executed *before* the SC6 ledger existed; **no DEC ever charges them**, and no retroactive re-designation is made here (that would require a new decision).

**6 — Explicit per-item statement.** **EXP-002 = 0 charge. EXP-003 validation = 0 charge. EXP-005 TEST = 0 charge. EXP-006 TEST = 0 charge. EXP-007 = 126 charge** (35+35+35+21 live, TRAIN-split, 0 failures, 0 smoke, 14 unexecuted planned rows charging nothing). **Smoke executions are included in the charged 232 chain** (DEC-011). **Failed live executions consume budget** — the rule is recorded; EXP-007 itself executed 0 failures, so the rule alters no current figure.

**7 — Historical / stale figures, and why each is not the current authoritative headroom.**

| Figure | What it is | Why it is not the current authoritative figure |
|---|---|---|
| **343** | Non-smoke manifest subtotal (`42+84+35+35+49+35+21+42`) | Arithmetically correct **as a manifest subtotal**, but it is **not the SC6 ledger**: it omits the 15 smoke live executions DEC-011 explicitly charged, and it omits B4's 84 and EXP-001's 20, which are not manifests at all. **Non-smoke manifest subtotal, not the authoritative ledger.** |
| **379** | Preflight "spent before EXP-008" basis (`343 + 20 + 16`) | **Stale/contradictory basis.** It drops the 15 charged smoke executions (contra DEC-011) and B4's 84 (contra DEC-016 C) while adding 16 EXP-002 B0 reference runs that **no decision ever charged** — a cherry-picked subset of EXP-002's 208 recorded runs. No decision authorizes this basis. |
| **121** | `500 − 379` ("nominal TRAIN-only" remaining) | **Stale consequence of the 379 basis**; it inherits every defect above. Not a rounding difference from 38 — it is a different *category mix*. |
| **−89** | Preflight claim of "DEC-chain post-EXP-007 remaining" | **Not reproducible and internally inconsistent with its own stated chain**: the same artifact states "336 spent pre-007, remaining 164; EXP-007 executed 126", which yields `164 − 126 = 38`, not −89. No derivation, component list or ledger entry for −89 exists anywhere; the unexplained gap is 127 executions. Recorded as **unresolvable from cited evidence** — not silently discarded — and superseded by the reconstructed 38. |
| **164** | DEC-024 §3 / DEC-025 §1 remaining **before** the EXP-007 execution (`500 − 336`) | **Historically correct for its date, now superseded** by the 126 live executions performed under DEC-026's authorization. A time-slice, not an error; DEC-025 remains unedited. |
| **24** | DEC-025 §12 / DEC-026 §3 headroom at authorization time (`164 − 140`) | **Historical headroom under the earlier EXP-007 authorization envelope**: computed against the planned *maximum* 140, not against the executed 126. Superseded by execution; DEC-025 and DEC-026 remain unedited. |

For completeness, the reconciliation additionally classified `184` (DEC-023's arithmetically wrong "500 − 336 = 184", already corrected by DEC-024 §3/§6 and DEC-025 §1), `519` (illustrative `379 + 140`) and `−229` (illustrative, truncated derivation) as **stale or illustrative**. None is authoritative; none is rewritten here.

**8 — Current remaining headroom: 38 charged live TRAIN executions.** `500 − 462 = 38`, reproducible two independent ways (`500 − 462`; and `500 − (358 manifests + 84 + 20)`).

> **NOT AN APPROVAL.** "38 remaining" means **only** that **38 charged live TRAIN executions remain under the current global SC6 accounting envelope**. It does **not** mean — and must never be reported as — "38 A3/A4 executions approved". This entry approves **no** A3/A4 execution count, shape, arm set, seed set or schedule.

**9 — No cap amendment enacted. No de-scoping enacted.** The SC6 cap remains **500**; `docs/PLAN.md` line 45 and `configs/rl.yaml` line 17 stand verbatim. Nothing is de-scoped: no EXP-008 arm, seed, cell or register line is removed or reduced. For this decision `cap_amendment_required` = **false** and `de_scoping_required` = **false**.

**10 — PLAN-internal scope/envelope tension (recorded as a governance dependency; NOT resolved here).** `docs/PLAN.md` line 315 registers EXP-008 with an envelope of **~300** executions (*"EXP-008 | RQ4 | design matters | Train/Test | A3, A4, A5 | ~300 | ablation table | planned"*), while PLAN line 45 caps SC6 at **500** and 462 is already charged. DEC-011 already recorded that whether EXP-008's envelope is charged to SC6's ≤500 or to its own ~300 line is an **internal-PLAN conflict that DEC-010's precedence rule cannot arbitrate**. This entry records that tension as a dependency; it does **not** decide the amendment mechanism, does **not** amend PLAN, does **not** raise the cap and does **not** re-scope EXP-008.

> **Current accounting is unambiguous; the remaining 38-execution capacity is authoritative. Any future EXP-008 specification exceeding that capacity requires a separate scope/cap governance action before execution authorization.**

**11 — Explicit future trigger.** A future **frozen** EXP-008 specification whose **charged** live TRAIN execution requirement **exceeds 38** **cannot be authorized** under the current SC6 envelope without a **separate governance decision** — either an explicit **cap/PLAN amendment** or an explicit **scope reduction** to ≤ 38 charged live TRAIN executions, enacted by its own decision (a new DEC entry plus, for a cap change, the PLAN header's change-control amendment). No such amendment and no such reduction exists today, and neither is created by this entry.

**12 — Relationship to DEC-030.** **DEC-030 remains unchanged** — not rewritten, not superseded, not reinterpreted. This entry resolves **only** the B5 budget question DEC-030 §10 explicitly deferred (*"B5 is NOT resolved by DEC-030. Budget reconciliation is a separate required decision."*). This decision **does not alter A3/A4 methodology** and does not change DEC-030's arm tables, isolation verdicts, A5 lock, statistical-governance position or `execution authorization: NO`.

**13 — What this decision deliberately does NOT decide** (each remains governed by DEC-030 and subsequent decisions): the **A3 number of seeds**; the **A4 number of seeds**; the **episode horizon**; the **A3/A4 arm count**; the **Q0 source**; the **execution schedule**; the **implementation design**; the **final experiment scope**; the statistical governance of EXP-008; the completeness of A3-R4; and the amendment mechanism for the PLAN tension in §10. This entry freezes only the **charging rule** and the **remaining capacity** (B5) — nothing else. It is **not** the B6 implementation decision and **not** an authorization decision.

**14 — Non-authorization firewall (explicit).**

| Item | State recorded by this entry |
|---|---|
| **EXP-008 execution authorization** | **FALSE / NO** |
| **Implementation authorization** (A3/A4, B6) | **FALSE / NO** — A3/A4 remain **UNIMPLEMENTED** |
| **A5** | **DISABLED / excluded** (DEC-011; re-affirmed DEC-016 §7, DEC-023 §2, DEC-024 A5 row, DEC-025 §7, DEC-030 §9); `configs/rl.yaml` `gamma` stays 0.0 |
| **TEST** | **NOT AUTHORIZED** — no TEST queue, specification or ledger is created; nothing here opens TEST for anything |
| **`docs/PLAN.md`** | **UNCHANGED** — no line edited |
| **Historical decisions** | **UNCHANGED** — DEC-001 … DEC-026 and DEC-030 are not rewritten; this entry is appended, never substituted |
| **Spark / training / TEST executions performed by this entry** | **0 / 0 / 0** |

**15 — Evidence and fingerprints (read-only; nothing listed here was modified except that this entry is appended).**

| Source | Role | SHA256 (at recording time) |
|---|---|---|
| `docs/research/DAY37_EXP008_BUDGET_RECONCILIATION.md` | reconciliation report + decision content | `3ab808c8…dcd9e` as published; `edba9f93…ff9b4d` after the additive DEC-031 identifier note (accounting text unchanged) |
| `results/evaluation/exp008_budget_reconciliation.json` | machine artifact — **retained byte-identical, NOT modified by this entry** | `bd67da1735aaaa9d62ac977f2874034dca1f70db7da849db436b2ca939a596c5` (33 236 bytes) |
| `docs/PLAN.md` | SC6 (line 45); EXP-008 envelope (line 315) | `db5e82102833efe6bab8db1adaf1b35ad195faf385e63ab296d50562e349ee63` (**unchanged**) |
| `configs/rl.yaml` | `live_execution_cap: 500` (line 17) | `8ca70d6dd7df68841c409a4441dc538616206bccea7877b28c73df20e6428b80` (**unchanged**) |
| `docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md` | DEC-030 identity preserved | `ec487bf2…01912a5a` (**unchanged**) |
| `DECISIONS.md` | this entry appended; every prior byte intact | `313e6f0353670bef42e1c10bbfa3069dfc29d5e348617d81b1add5d2dde957e9` **before** this append (the value recorded inside the reconciliation JSON, which is retained unchanged) |

Note: the reconciliation JSON records the `DECISIONS.md` fingerprint as of **its own** run (`313e6f03…`). This entry appends to `DECISIONS.md`, so that recorded field now describes the pre-DEC-031 state. That is expected, is **not** an accounting change, and is why the JSON is **retained rather than regenerated**: re-running the runner would change only that fingerprint field, while every accounting number would remain **462 / 38**.

**16 — Validation of this entry (performed after recording it; read-only, zero Spark).**

| Check | Evidence | Result |
|---|---|---|
| New DEC ID unique | heading scan of `DECISIONS.md` + repository-wide search for `DEC-031` | PASS |
| No historical DEC text changed | pre-edit copy byte-identical prefix; `DECISIONS.md` only appended to | PASS |
| DEC-030 unchanged | SHA256 of the DEC-030 artifact unchanged | PASS |
| SC6 cap = 500 | `docs/PLAN.md` line 45; `configs/rl.yaml` line 17 | PASS |
| cumulative charge = 462 | reconciliation JSON `cumulative_charge`; charge-table sum | PASS |
| remaining = 38 | `500 − 462` | PASS |
| accounting chain sums exactly | `232 + 84 + 20 + 126 = 462` | PASS |
| charged categories represented | §5 / §6 | PASS |
| non-charged categories represented | §5 / §6 | PASS |
| stale figures classified | §7 (343, 379, 121, −89, 164, 24) | PASS |
| no A3/A4 execution scope authorized | §8 note; §14 table | PASS |
| no implementation authorized | §14 table | PASS |
| A5 remains disabled | §14 table | PASS |
| TEST remains unauthorized | §14 table | PASS |
| PLAN remains unchanged | `docs/PLAN.md` SHA256 `db5e8210…` re-checked after recording | PASS |
| deterministic validation passes | read-only, zero-Spark check script re-parsed `DECISIONS.md` + the reconciliation JSON and asserted every figure and classification above | PASS |

**Validation detail (recorded at recording time).** The read-only check script ran **twice, with byte-identical output on both runs** (**55/55** checks passed); it parsed `DECISIONS.md`, the pre-edit copy, `docs/PLAN.md`, `configs/rl.yaml`, the reconciliation JSON, both Day-37 documents and the Cline checkpoint snapshot of the B5 report (proving the report was changed **additively only**, delta = 0 characters of accounting text). The pre-edit `DECISIONS.md` copy used for the append-only proof stayed in the session temp directory and was **not** added to the repository. `python -m pytest tests/unit/test_exp006_runner.py` — the existing governance test that enforces DEC-022 heading uniqueness and fingerprint binding against `DECISIONS.md` — still passes **31/31** after the append.

**Status.** **B5 budget decision recorded: `SC6 cap = 500`; `authoritative cumulative charge = 462`; `remaining = 38`; `232 + 84 + 20 + 126 = 462`; no cap amendment enacted; no de-scoping enacted.** `EXP-008 execution authorization = NO`. `A3/A4 implementation = NOT AUTHORIZED / NOT IMPLEMENTED`. `A5 = DISABLED`. `TEST = NOT AUTHORIZED`. `PLAN.md = UNCHANGED`. Historical decisions (DEC-001 … DEC-026, DEC-030) = **UNCHANGED**. Supervisor counter-signature: **PENDING** (conventional expectation only; never simulated, and not a prerequisite under DEC-018 Decision A). **This entry performs 0 Spark executions and trains nothing.**


## DEC-032 | 2026-09-18 | Day-31 validator ledger reconciliation (DEC-031 follow-up) — check-22 assumption recorded OBSOLETE; validator-only repair AUTHORIZED for a separate later task, NOT performed here (Day 37)

**Status.** **DECIDED.** Standalone companion artifact: `docs/research/DEC_032_DAY31_VALIDATOR_LEDGER_RECONCILIATION.md` (same content, self-contained). **Supervisor counter-signature: PENDING** (conventional expectation only, exactly as DEC-020..DEC-026 and DEC-031; not a prerequisite under DEC-018 Decision A). **NO SUPERVISOR HAS REVIEWED THIS ENTRY.** This entry performs **0 Spark executions**, trains nothing, executes no TEST, creates no run directory, and modifies no result artifact, no manifest, no budget, no ledger, no implementation file, no configuration and no prior decision entry. **`scripts/validate_day31.py` is NOT modified by this entry.**

**0 — Identifier.** `DECISIONS.md` headings run DEC-001…DEC-026 plus DEC-031; DEC-030 is formally recorded outside this file. No DEC-027/028/029/032/033 artifact exists — the "DEC-027..032 drafts" named in the Day-37 preflight/methodology artifacts are non-authoritative worktree drafts occupying no identifier (DEC-031 §0). Next sequential identifier: **DEC-032**.

**1 — The stale assumption.** `scripts/validate_day31.py` check 22 (lines 721–731) asserts `n_manifests == DAY29_MANIFEST_COUNT (9)` AND `unexplained == 0` AND `live_total <= 500` AND `not ledger_errors`, where `unexplained = live_total − DAY29_LIVE_EXECUTIONS(232) − b4_spent − exp001_spent`. Against the live tree: `n_manifests = 14` (≠ 9, FALSE); `unexplained = 462 − 232 − 84 − 20 = 126` (≠ 0, FALSE); `live_total = 462 ≤ 500` (TRUE); no ledger errors (TRUE). The formula carries subtrahends for B4 (84) and EXP-001 (20) but **has never been given a term for EXP-007**; the residual 126 is exactly EXP-007's authorized spend.

**`DAY29_MANIFEST_COUNT = 9` was overtaken by two LATER additions — the signed Day-29 baseline itself is unchanged.** (a) **A later zero-live artifact that is NOT part of that baseline:** a tenth manifest directory appeared on **2026-09-16** — `results/training/smoke/train-a0-d0-20260916T043003Z` (`live_executions: 0`, `exit_code: 1`) — **three days after DEC-011 was signed on 2026-09-13**, so it is **not** a Day-29 baseline artifact. DEC-011 §7's baseline is, and remains, **9 manifests / 232 live executions**; this entry does not reinterpret it. DEC-031 §3 later re-summed that same **232** total across **"10 manifests: 3+3+3+3+3+0+42+84+49+42"** — a *live-total* re-sum whose tenth row contributes **+0** — and that wording must **not** be read as enlarging the signed baseline to ten. DEC-031 §5 charged-category 3 supplies only a charging rule: *"A smoke attempt with 0 live executions is still a charged row at 0."* The row broke the count clause on 2026-09-16, one day before any EXP-007 execution, adding nothing to live totals and charging nothing. (b) **By DEC-026's authorized execution:** EXP-007 added **4** manifests carrying 126 live executions. **9 historical Day-29 baseline manifests + 1 later zero-live aborted-smoke manifest + 4 later EXP-007 manifests = 14 current manifest directories.** The two clauses decayed on different dates for different reasons.

**2 — Canonical values (restated from DEC-031; nothing re-derived, no figure changed).** SC6 cap **500** (unchanged, not raised); **historical Day-29 baseline 9 manifests / 232 live** (DEC-011 §7, signed 2026-09-13 — unchanged, not reinterpreted); **1 later zero-live aborted-smoke manifest (2026-09-16): 0 live, 0 charged, authorization attribution ABSENT**; B4 **84** (DEC-016 C / DEC-017); EXP-001 **20**; EXP-007 **126** over **4** later manifests, 35+35+35+21 (DEC-026 scope; DEC-031 §3); **current manifest directories 14** (9 + 1 + 4); live executions represented by manifests **358** (232 + 0 + 126); **cumulative charge 462**; **remaining headroom 38** (DEC-031 §§4, 8). DEC-032 charges **0**.

**3 — Semantic status: OBSOLETE ASSUMPTION, not a historical invariant.** The repository's own discriminator is written in `src/sparkrl/training/ablation.py:49–55` — of `SC6_LEDGER_CITED = "336/500"` / `SC6_REMAINING = 164` it says **"the ledger is never re-derived here"** (`tests/unit/test_exp007_scope.py:76` pins the same pair "# historical ledger, cited"). **CITED** figures (ablation.py's 336/500 and 164, DEC-023 §8's 184, DEC-025 §1's 164, DEC-024/026's 24) record the ledger as of a date, are chronology, and **must not be touched** — DEC-031 §7 already classifies 164 as *"Historically correct for its date, now superseded … A time-slice, not an error; DEC-025 remains unedited."* **RE-DERIVED** assertions measure the live tree every run; check 22 does not cite a figure, it computes one. Its own comment (lines 693–701) disclaims the frozen reading: the assertion is *"that Day-31 created no training run and that every execution above the Day-29 baseline is attributable to those authorized spends, **NEVER that the total is frozen**."* Conjunct classification: `n_manifests == 9` = manifest-count consistency (run-existence proxy, catches a run that charged zero); `unexplained == 0` = unexplained-spend detection, the mechanism implementing unauthorized-execution protection; `live_total <= 500` = canonical current-ledger cap validation; `not ledger_errors` = anti-undercount integrity guard. **No conjunct preserves a historical figure** — 232 appears only as an addend in a decomposition, never as an equality target; the strict historical pin (`live_total == 232`) lives in the sibling `scripts/validate_day30.py` check 14, a different artifact (§7). **Decisive: check 22 is SATURATED** — it fails today and would fail identically with one more unauthorized execution (127 instead of 126), so its pass/fail bit carries **zero information** about unauthorized execution. Its protective function is **dead, not preserved**; repair restores it, inaction does not conserve it.

**4 — Precedent `9e83742` / `715a7d3`: METHOD transfers, AUTHORIZATION does not.** Check 22 has been amended **twice**, both times because an authorized spend invalidated its expectation. `9e83742` (2026-09-14, DEC-017's +84) states in its body: *"Day-31 check 22 asserted the ledger was frozen at the Day-29 figure, which DEC-017's authorized spend legitimately invalidated. **It now asserts what it always meant** … **An unexplained execution would still fail it.**"* `715a7d3` added the `exp001_spent` subtrahend for EXP-001's +20. **Method (transfers):** RETAIN the historical constants — `DAY29_MANIFEST_COUNT` and `DAY29_LIVE_EXECUTIONS` are byte-identical across `9e83742` — and DERIVE each authorized spend from its artifact, asserting residual `unexplained == 0`; never re-pin a constant to a new total. **Authorization (does not transfer):** `9e83742` touched exactly two files and carried **no `DECISIONS.md` entry at all**; `715a7d3` amended check 22 in the same commit that recorded DEC-018 Decision E, which adopted it **retrospectively**. Demonstrated practice is **amend-first, ratify-concurrently-or-never** — not decision-first. **CORRECTION OF RECORD:** an earlier Day-37 statement in this work-stream asserted that the `9e83742` repair "was previously done under an explicit decision." That is **wrong** and is corrected here — `9e83742` was never ratified. DEC-018 Decision E (`DECISIONS.md:1034–1039`) is past-tense, scoped to the EXP-001 change set, and is the only decision sentence in this ledger naming a validator. Two facts further distinguish today: the precedent's defect was *undercounting* (B4 invisible to the ledger) whereas EXP-007's 126 is fully counted and only the expectation is stale; and `9e83742` deliberately preserved the manifest-count clause intact — the very clause today's tree breaks, for a reason unrelated to EXP-007.

**5 — Why a decision is recorded, and what is NOT claimed.** No existing decision authorizes this repair: DEC-031 contains the word "validator" **zero** times and §13 states *"This entry freezes only the charging rule and the remaining capacity (B5) — nothing else … not the B6 implementation decision and not an authorization decision"* with §14 setting Implementation authorization = FALSE/NO; DEC-026 §11's "explicit and exhaustive" not-permitted list never mentions validators or downstream staleness (its §7 recorded a pre-execution baseline of *"560 passed, 1 skipped, exit 0"* that its own authorized 126 executions then falsified); `scripts/validate_day30.py` is named in no decision or research document. **NOT CLAIMED:** the repository has **no written rule** requiring a decision before amending a validator — the only change-control rule (`DECISIONS.md:161–166`, restated by DEC-009) is scoped to *"substantive architectural changes"* and holds *"Editorial clarifications need only a commit message note"*; and `scripts/validate_day31.py:842` already pre-names `scripts/validate_day30.py,  # validator maintenance` inside check 27's authorized-modified-file allowlist, a standing **validator maintenance** category that has never been adjudicated. **DEC-032 does not decide whether that carve-out would have sufficed.** It is recorded because the operator required an explicit decision first, and because an explicit record is strictly safer than an unadjudicated carve-out.

**6 — Authorized repair (NOT performed here).** Following DEC-025 §11's *"Implementation consequence (NOT implemented here)"* template, the **NEXT SEPARATE task** is authorized to make a **validator-only, minimal, local** repair to `scripts/validate_day31.py` check 22 and the comment/docstring text directly describing its assumptions (`:24–28`, `:96–101`, `:693–701`). The repair **MUST**: (1) follow the `9e83742` method — retain `DAY29_MANIFEST_COUNT` / `DAY29_LIVE_EXECUTIONS` as named historical addends, add an EXP-007 term, derive each authorized spend from its own artifact, never hard-code a new total; (2) keep `unexplained == 0` as the detection mechanism; (3) account for the count as **9 historical Day-29 baseline + 1 later zero-live aborted-smoke manifest (2026-09-16) + 4 later EXP-007 = 14 current manifest directories**, preserving the distinction between historical baseline, later manifests, live-execution totals and budget charging — never an opaque `9 → 14` re-pin and never an enlargement of DEC-011's signed 9-manifest baseline, and with no silent assumption about whether a zero-live manifest counts (§7.3 records that gap as unresolved); (4) preserve the invariant below.

> **BINDING INVARIANT.** After the repair, a live TRAIN execution **not attributable to a recorded authorization** must still make check 22 **FAIL loudly**. Concretely: today's tree must evaluate `462 − 232 − 84 − 20 − 126 = 0` → PASS, and one additional unattributable execution must evaluate to `1` → FAIL.

> **ANTI-PATTERN THE REPAIR MUST AVOID.** The EXP-007 term must **not** be an unbounded re-sum of the same manifests that already produce `live_total`. `live_total` includes the EXP-007 manifests; a subtrahend computed by re-summing them without an independent authorized bound makes `unexplained` **identically zero by construction**, silently absorbing arbitrary growth and destroying unexplained-spend detection while the check shows green. The term must be bounded by an independent authorized source — DEC-026's authorized maximum **140** and DEC-031's recorded **126** are both available.

The repair **MUST NOT**: weaken, delete, skip, xfail or bypass check 22; remove or raise the `live_total <= 500` ceiling; remove the `not ledger_errors` guard; convert a strict failure into a warning; hard-code a passing value not derived from the canonical ledger; change any manifest, result, budget or ledger artifact; or alter authorization state.

**7 — Explicitly OUT of scope (recorded, not resolved).** (1) **`scripts/validate_day30.py` check 14** — also failing, under **strict equality** (`n_manifests == 9` AND `live_total == 232` vs live 14/358), strictly more brittle than check 22 and with no authorized-growth term; its constants are headed *"Day 30 must move NEITHER number"*, a genuine historical-preservation framing that `9e83742` deliberately left alone. Different artifact, different semantic status; needs its own audit and its own decision. **DEC-032 authorizes nothing there.** (2) **Propagation** — `scripts/validate_day31.py:907–913` re-executes the six prior validators as subprocesses (checks 29–34), so day30's failure reaches day31 independently of check 22; repairing check 22 alone will **not** make `validate_day31.py` exit 0. (3) **The 2026-09-16 aborted zero-live smoke manifest** (`results/training/smoke/train-a0-d0-20260916T043003Z`) — Established facts, and only these: the manifest **exists**; it records **0 live executions**; it **charged 0**; it **post-dates DEC-011** (2026-09-16 vs 2026-09-13); and its own reconciliation instruction (`budget_accounting: "uncertain: the in-flight execution may or may not have completed; count records under transitions/ to reconcile"`) refers to a `transitions/` directory that **does not exist**, so the reconciliation it prescribes is unperformable. DEC-031's live/budget accounting therefore **cannot** be read as evidence that this row was a Day-29 baseline artifact. DEC-031 §3 carries it only as an anonymous `+0` term inside a live-total re-sum; it is **not** part of DEC-011's signed Day-29 baseline (§1). **UNRESOLVED GOVERNANCE GAP — not resolved here.** The repository currently has **no written rule** answering: *should an aborted / zero-live manifest count toward a manifest-count invariant?* DEC-031 §5 charged-category 3 supplies a **charging** rule only ("still a charged row at 0"); it says nothing about counting. No decision names this run directory or attributes it to an authorized activity. This amendment **invents no policy** for zero-live manifests and **redesigns no ledger**. (4) **DEC-026 §8's defunct discriminator** — it asserts *"every one of them has an EMPTY `variant` field"*, but **no** manifest carries a `variant` key at all, before or after EXP-007; the real key is `exp007_variant`. Recorded, **not corrected**; DEC-026 is historical and is not rewritten. (5) Every EXP-008 matter — DEC-030 methodology, DEC-031 budget, the B6 implementation decision, R4 semantics, Q0 provenance, any DEC-030 §12 field, and EXP-008 execution authorization. All untouched.

**8 — Retrospective coverage of the already-performed test repair.** Following DEC-018 Decision E's retrospective-adoption precedent: the live-tree ledger assertion in `tests/unit/test_exp001_maintenance.py::test_exp003_or_exp005_are_never_charged_to_sc6` was re-pinned from `336 / 164` to `462 / 38` earlier on 2026-09-18 under operator instruction, **before any decision covered it**. That change is **adopted here as operator-authorized Day-37 work**, on the §3 reasoning (it re-derives from the live tree; it does not cite a historical figure) and subject to the §6 invariant (the pin was not weakened — it remains an exact equality and an unauthorized execution still breaks it). Its hermetic fixture-tree sibling assertions correctly remain at 336 and were not touched. This is recorded because `docs/research/DAY37_EXP008_B6_IMPLEMENTATION_REPORT.md` §8 and §10 row 5 had classified that repair as *"a DEC-031 follow-up, not an implementation-only change"* — owed work requiring a decision that did not then exist. **DEC-032 is that decision.** The B6 report and `results/evaluation/exp008_b6_implementation.json` are **NOT regenerated**: they are correct as B6-time records and their historical status is preserved.

**9 — Why this authorizes no experiment execution.** This entry authorizes an edit to an **assertion about already-recorded history**. It creates no run directory, no queue, no specification, no schedule; grants no Spark, training, validation or TEST execution; does not raise the SC6 cap (500, unchanged); does not change the cumulative charge (462, unchanged) or the remaining headroom (38, unchanged); and charges **0** executions. A validator that reads the ledger cannot spend it. **EXP-008 execution authorization = NO.**

**10 — Why this is bookkeeping, not methodology.** No reward, action space, state schema, Q0, T_ref, seed, split, horizon, hyperparameter, DEC-030 §12 field or statistical procedure is touched. The repair changes **what a validator expects the ledger to read** — an arithmetic expectation about executions that already happened under DEC-026's authorization and that DEC-031 has already reconciled. Under the repository's own cited-vs-re-derived discriminator (§3), reconciling a measurement's expectation with the canonical ledger is bookkeeping.

**11 — Fingerprints (read-only; nothing listed was modified by this entry).** `docs/PLAN.md` `db5e82102833efe6bab8db1adaf1b35ad195faf385e63ab296d50562e349ee63` (**unchanged**); `configs/rl.yaml` `8ca70d6dd7df68841c409a4441dc538616206bccea7877b28c73df20e6428b80` (**unchanged**); DEC-030 artifact `ec487bf2a84a9c1a6f506bdd83c71b7c7bb7ae2cceaf7e761f000c7201912a5a` (**unchanged**); DEC-031 artifact `af5c18216c6fdbcba86c891934a4b2d1026a32c4e2ada91eee91f7c8ab12852c` (**unchanged**); `results/evaluation/exp008_budget_reconciliation.json` `bd67da1735aaaa9d62ac977f2874034dca1f70db7da849db436b2ca939a596c5` (**unchanged, byte-identical**); `scripts/validate_day31.py` **NOT MODIFIED**; `scripts/validate_day30.py` **NOT MODIFIED**; `results/training/**/manifest.json` **NOT MODIFIED**. **Working-tree disclosure:** DEC-030, DEC-031 and DEC-032 are uncommitted working-tree state on top of HEAD `5cf0cf850f022750fa7df734328f6807e3546ee9` (`git show HEAD:DECISIONS.md | grep -c "DEC-031"` returns 0), so any future repair citing DEC-031/DEC-032 cites an authority that presently exists only in the working tree — disclosed here, matching DEC-024 §6 / DEC-026's disclosure of the same condition.

**Status.** **DECIDED.** The Day-31 check-22 ledger assumption is recorded as an **OBSOLETE ASSUMPTION**, superseded by DEC-031's canonical ledger (**462 / 38**; baseline recounted to **10** manifests; **14** total). A **validator-only, minimal, invariant-preserving** repair to `scripts/validate_day31.py` check 22 is **AUTHORIZED for a separate later task** and is **NOT performed by this entry**. `scripts/validate_day30.py`, the 2026-09-16 smoke-run attribution and DEC-026 §8's defunct discriminator are **recorded as open items, out of scope, and not resolved**. `EXP-008 execution authorization = NO`. `A5 = DISABLED`. `TEST = NOT AUTHORIZED`. `docs/PLAN.md = UNCHANGED`. Historical decisions (DEC-001 … DEC-026, DEC-030, DEC-031) = **UNCHANGED**. **This entry performs 0 Spark executions and trains nothing.**


**12 — Amendment record (2026-09-18, chronology correction; this entry amended in place, nothing withdrawn).** §§1, 2 and 6(3) previously treated DEC-031 §3's *"10 manifests"* wording as if the canonical **Day-29 baseline** were ten manifests, and instructed the future Day-31 repair to account for the count as *"10 baseline + 4 EXP-007 = 14."* That silently backdated a **2026-09-16** artifact into a baseline signed **2026-09-13**, and would have put a future validator in direct textual conflict with signed DEC-011 §7 (*"recomputed from all **9** training manifests"*). Corrected to three distinct strata, never collapsed: **historical Day-29 baseline 9 manifests / 232 live** (DEC-011 §7, unchanged); **+ 1 later zero-live aborted-smoke manifest (2026-09-16), 0 live, 0 charged, attribution ABSENT, counting rule UNRESOLVED**; **+ 4 later EXP-007 manifests / 126 live** (DEC-026); **= 14 current manifest directories / 358 live represented by manifests**; plus B4 **84** and EXP-001 **20** gives the canonical **462**, remaining **38** (DEC-031 §§4, 8, unchanged). This amendment does not reinterpret DEC-011's historical ledger, invents no accounting policy for zero-live manifests, redesigns no ledger, modifies neither DEC-030 nor DEC-031, touches neither validator, regenerates no freeze artifact and changes no authorization. The §6 invariant is retained verbatim (`462−232−84−20−126 = 0` PASS; `463−...= 1` FAIL), as is its anti-pattern clause forbidding a self-cancelling subtrahend. Separately recorded, not re-decided: §7.1's provisional description of `validate_day30.py` as *"a genuine historical-preservation framing"* is **superseded as to characterization** by the completed read-only Day-30 audit (which found check 14 an obsolete assumption under §3's own discriminator, and found `9e83742` left it alone because it still passed); §7.1's **scope ruling stands** — DEC-032 authorizes nothing for `validate_day30.py`. **0 Spark executions; trains nothing; EXP-008 execution authorization remains NO.**