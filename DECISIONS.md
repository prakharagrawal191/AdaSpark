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

---

## DEC-033 | 2026-09-19 | 2026-09-19 smoke ledger classification — Option A: the six completed smoke TRAIN executions are CHARGED; ledger 468/500, remaining 32; charged-but-unauthorized (Day 37)

**Status.** **DECIDED (Option A, selected by the operator; committed `c2e980a`).** Standalone companion artifact: `docs/research/DEC_033_GOVERNANCE_RECONCILIATION.md` (same decision content, self-contained; its Part II is duplicated in the file and its title and closing line still read "DRAFT" — recorded by DEC-037 s6(b)/(c); **this section is authoritative on status and figures**). **Supervisor counter-signature: PENDING** (conventional expectation only, exactly as DEC-020…DEC-026, DEC-031, DEC-032; not a prerequisite under DEC-018 Decision A). **NO SUPERVISOR HAS REVIEWED THIS ENTRY.** This entry performs **0 Spark executions**, trains nothing, executes no TEST, creates no run directory, and modifies no manifest, no result artifact, no implementation file and no prior decision entry. **Supersedes nothing** — DEC-011, DEC-026, DEC-030, DEC-031 and DEC-032 are unchanged.

**0 — Identifier.** `DECISIONS.md` headings run DEC-001…DEC-013, DEC-015…DEC-026, DEC-031, DEC-032; DEC-030 is formally recorded outside this file (DEC-031 s0). Next sequential identifier at the time of decision: **DEC-033**.

**1 — What moved.** DEC-031 recorded the canonical charge **462 / remaining 38** against the frozen SC6 cap **500**, with the invariant `232 + 84 + 20 + 126 = 462`. The live tree then measured **468**. The delta is **exactly +6** and its origin is fully traced to eight 2026-09-19 smoke directories under `results/training/smoke/`: **six aborted attempts** (`…T124348Z`, `…T124413Z`, `…T124425Z`, `…T124736Z`, `…T124832Z`, `…T124900Z`), each `status: failed`, `exit_code: 1`, `live_executions: 0`, 0 transition files, dying before any episode executed; and **two completed runs** (`…T130241Z`, `…T130614Z`), each `status: completed`, `exit_code: 0`, **3 live executions** with 3 matching transition records and a checkpoint. `0+0+0+0+0+0+3+3 = 6`. No other file on the tree contributes an unaccounted live execution.

**2 — Cause, disclosed rather than left anonymous.** The six live executions were caused by an auditing agent running the **full** `pytest tests` suite. `tests/integration/` executes real Spark and writes training manifests under `results/training/smoke/` with non-zero `budget.live_executions`; two invocations completed at 13:02:41 and 13:06:14 UTC. **`pytest tests` charges the SC6 budget.** Every validator that gates on the unit suite correctly runs `tests/unit` only, and nothing in the repository warned that the full suite spends frozen budget. Recorded here as a standing operational finding; the guard for it is a separate decision (DEC-037 s4).

**3 — DECISION: Option A — charge under the standing rule. No new category is invented.** The six completed 2026-09-19 smoke TRAIN executions are **CHARGED ROWS** under **DEC-031 s5 charged-category 1** (TRAIN live executions — real environment transitions consumed by a training run's budget counter, here with matching transition records and checkpoints) and **charged-category 3** (smoke executions inside charged TRAIN accounting — the same category as DEC-011's `(5 runs × 3)` term). The six aborted same-day attempts are **charged rows at 0** under category 3's second sentence: *"A smoke attempt with 0 live executions is still a charged row at 0."* Nothing in DEC-031 s5's NOT-CHARGED list covers any of them: they are not planned-but-unexecuted rows, not cache hits, not EXP-003 validation and not TEST — the TEST seal is untouched and the runs executed TRAIN cells only.

**4 — Canonical ledger under this decision.** `232` (Day-29 baseline, DEC-011 s7) `+ 84` (B4, DEC-016 C / DEC-017) `+ 20` (EXP-001) `+ 126` (EXP-007, DEC-026) `+ 6` (2026-09-19 smoke, this entry) `= **468** of 500`. **Remaining headroom: `500 − 468 = 32`.** The **SC6 cap remains 500 and is NOT raised** — `docs/PLAN.md` line 45 and `configs/rl.yaml` line 17 stand verbatim. DEC-031's chain is not rewritten; this entry adds one named term to it.

> **NOT AN APPROVAL.** "32 remaining" means **only** that 32 charged live TRAIN executions remain under the current global SC6 accounting envelope. It approves **no** execution count, shape, arm set, seed set or schedule.

**5 — Authorization status of the eight runs: CHARGED-BUT-UNAUTHORIZED.** No decision in `DECISIONS.md` (DEC-001 through DEC-032) names, scopes or approves any 2026-09-19 smoke execution; the runs post-date every recorded authorization, and none could have authorized them — they were an accident. **They are counted against the cap and disclosed, not deleted**: deleting an execution record would falsify the thing this ledger exists to protect. **Any future smoke execution requires its own explicit authorization.**

**6 — Why not Option B (exclude) or Option C (defer).** **Option B — REJECTED.** Excluding them would require writing a new exclusion reason into a NOT-CHARGED list that DEC-031 s5 states exhaustively; no already-supported category covers an exclusion, so Option B would invent a category to absorb an accident — the move DEC-032 s6's anti-pattern clause forbids. It would buy back 6 executions at the price of the rule. **Option C — REJECTED.** The evidence supports Option A, and both check 22 and the unit-suite ledger pin require a binding classification.

**7 — Consequential follow-ups (none performed by this entry).** (i) A **validator-only** repair adding a **named, bounded DEC-033 smoke term** to check 22's decomposition — bounded by this entry's recorded **6** and by the two named manifests, **never** by a re-sum of the same manifests that produce `live_total`, which DEC-032 s6 forbids as self-cancelling; anything else must append to `ledger_errors` and FAIL loudly. (ii) Correcting the `tests/unit/test_exp001_maintenance.py` live-tree pin from `462 / 38` to **`468 / 32`**, keeping it an **exact equality** so an unauthorized execution still breaks it; the hermetic fixture-tree siblings stay at 336 and are not touched. (iii) The **zero-live counting question** (DEC-032 s7(3)) stays **UNRESOLVED** by this entry — seven zero-live directories now sit under it and this entry invents no rule for them. (iv) The `pytest tests` budget footgun (s2). (v) The representation-dependent provenance hash.

**8 — What this decision deliberately does NOT decide.** The zero-live manifest **counting** rule; the SC6 cap (500, unchanged); the PLAN line 315 EXP-008 envelope tension (DEC-031 s10, DEC-011 — an internal-PLAN conflict DEC-010's precedence rule cannot arbitrate); the B6 implementation decision; any DEC-030 s12 field; EXP-008 execution authorization; and the retrospective status of any validator repair present in the tree. **`cap_amendment_required` = false. `de_scoping_required` = false.**

**9 — Non-authorization firewall.** **EXP-008 execution authorization = NO.** **Implementation authorization (A3/A4, B6) = NO.** **A5 = DISABLED** (DEC-011; `configs/rl.yaml` `gamma` stays 0.0). **TEST = NOT AUTHORIZED.** **`docs/PLAN.md` = UNCHANGED.** Historical decisions (DEC-001 … DEC-026, DEC-030, DEC-031, DEC-032) = **UNCHANGED**. **Spark / training / TEST executions performed by this entry: 0 / 0 / 0.**

**Status.** **DECIDED — Option A.** The six completed 2026-09-19 smoke TRAIN executions are **CHARGED** under DEC-031 s5 categories 1 and 3; the six aborted same-day attempts are **charged rows at 0**; the canonical ledger is **468 charged of 500, remaining 32**, arithmetic `232 + 84 + 20 + 126 + 6 = 468`; the SC6 cap is **500 and NOT raised**; the eight runs' authorization status is **CHARGED-BUT-UNAUTHORIZED**; `EXP-008 execution authorization = NO`; `A5 = DISABLED`; `TEST = NOT AUTHORIZED`. Supervisor counter-signature: **PENDING** (conventional expectation only; never simulated). **This entry performs 0 Spark executions and trains nothing.**

*End of DEC-033.*

---

## DEC-034 | 2026-09-20 | EXP-008 A3/A4 scope resolution — zero-charge derived ablation; SC6 cap NOT amended; register-line exemption held inapplicable to TRAIN-only work (Day 37/38)

**Decision ID:** DEC-034
**Date:** 2026-09-20
**Scope:** The EXP-008 scope/envelope question only — what shape EXP-008 A3/A4 may take given the SC6 headroom recorded by DEC-033. Nothing else.
**Status:** DECIDED — **EXP-008 execution authorization remains NO.**
**Standalone decision artifact.** The authoritative log entry is this appended DEC-034 section of `DECISIONS.md`; a companion document `docs/research/DEC_034_EXP008_SCOPE_RESOLUTION.md` carries the same decision content, self-contained, following the DEC-031/DEC-032 convention.
**Supersedes nothing.** DEC-010, DEC-011, DEC-012, DEC-017, DEC-018, DEC-020, DEC-026, DEC-030, DEC-031, DEC-032 and DEC-033 are unchanged; no historical decision entry is rewritten.

> **This entry performs 0 Spark executions, trains nothing, executes no TEST, creates no run directory, modifies no result artifact, no manifest, no budget, no ledger, no implementation file and no configuration.**
> **EXP-008 execution authorization = NO. A5 = DISABLED. TEST = NOT AUTHORIZED. `docs/PLAN.md` = UNCHANGED.**

---

**0 — Identifier resolution.** `DECISIONS.md` headings run DEC-001…DEC-026, DEC-031, DEC-032. DEC-030 is formally recorded outside `DECISIONS.md` (`docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md`, sha256 `ec487bf2a84a9c1a6f506bdd83c71b7c7bb7ae2cceaf7e761f000c7201912a5a`). DEC-033 is likewise recorded outside `DECISIONS.md` (`docs/research/DEC_033_GOVERNANCE_RECONCILIATION.md`, sha256 `3e6d0d7c4b5359990ea6ac6766e226d860c5fea2fb0e8639cc73fff645932b21`, committed `c2e980a`); `grep -c "DEC-033" DECISIONS.md` returns **0**. That out-of-ledger recording is the DEC-030 pattern DEC-031 §0 accepted and is **recorded here, not corrected** — DEC-033's identity is preserved unchanged and this entry does not renumber, fold or edit it. The next sequential identifier is therefore **DEC-034**.

**1 — Scope.** (a) whether the register-line exemption reaches EXP-008 A3/A4; (b) what EXP-008 scope is admissible under the SC6 headroom recorded by DEC-033; (c) the charged live TRAIN execution requirement of that scope. Nothing else is in scope. This entry is **not** the B6 implementation decision and **not** an authorization decision.

**2 — Ledger restated, not re-derived.** SC6 cap **500**, unchanged and **not raised** (`docs/PLAN.md` line 45; `configs/rl.yaml` line 17). Cumulative charge **468**; remaining **32**; `232 + 84 + 20 + 126 + 6 = 468`; `500 − 468 = 32` (DEC-033, Option A selected by the operator). This entry **adds no new accounting and changes no figure**.

**3 — The register-line exemption does NOT reach EXP-008 A3/A4. The discriminator is the SPLIT, not the register line.** DEC-031 §10 left this open; DEC-011 held the pot question unarbitrable. Both stand. What this entry establishes is narrower and is fully supported by the existing record: *what made EXP-003, EXP-005, EXP-005b and EXP-006 exempt was never the existence of a register line.* Every exemption in the ledger is stated as an exemption from the **TRAIN** cap for **non-TRAIN** work:

| Exempt line | Split | The sentence that exempts it |
|---|---|---|
| EXP-003 | validation | DEC-012: *"EXP-003 is a separate register line and is NOT charged to SC6's ≤500 **TRAINING** cap (PLAN line 45)"* |
| EXP-005 | TEST | DEC-018 Decision B: *"245 TEST executions, charged to EXP-005's own register line and **outside** the SC6 **TRAIN** cap"* |
| EXP-005b | TEST | DEC-017: *"+70 runs, charged to EXP-005's own register line (PLAN line 312, ~245), NOT to SC6's 500-execution **training** cap"* |
| EXP-006 | TEST | DEC-031 §5: *"EXP-006 TEST — 125/125 **TEST** observations, charged **0**"* |

Against which DEC-031 §5 charged-category 1 reads: *"**TRAIN live executions** — every real environment transition consumed by a training run's budget counter … charged to the training register lines."*

**The decisive counter-example is EXP-007.** `docs/PLAN.md` line 314 registers it on its own line with the **identical** `~300` envelope and the **identical** `ablation table` acceptance column as EXP-008 at line 315. It was charged **126 to SC6** anyway — DEC-031 §6: *"EXP-007 = 126 charge (35+35+35+21 live, **TRAIN-split**, 0 failures, 0 smoke, 14 unexecuted planned rows charging nothing)"*, authorized against SC6 by DEC-026 §10: *"maximum 140 live Spark executions charged to SC6 (remaining 164, headroom 24)."* EXP-008 A3/A4 possesses no property EXP-007 lacked.

**EXP-008 A3/A4 is TRAIN-only, enforced in code.** `src/sparkrl/training/exp008.py` lines 207–214:

```
def guard_split(split: str) -> None:
    """EXP-008 A3/A4 is TRAIN-only: TEST and VALIDATION never enter."""
    if split != TRAIN:
        raise Exp008ScopeError(...)
```

**Recorded finding.** Any charged live TRAIN execution performed under EXP-008 A3/A4 falls inside SC6's subject ("training ≤500", PLAN line 45) and is charged. Routing it to PLAN line 315 instead would require writing a new exclusion reason into DEC-031 §5's exhaustively stated NOT-CHARGED list — the move DEC-032 §6's anti-pattern clause forbids and which DEC-033 §12 already refused on identical grounds. **That route is closed.**

**4 — The PLAN-internal conflict is MOOTED for EXP-008, not arbitrated.** DEC-011 recorded that whether EXP-008's envelope is charged to SC6's ≤500 or to its own ~300 line is *"internal to PLAN; DEC-010's precedence rule cannot arbitrate it."* **This entry does not arbitrate it and claims no authority to.** It does not need to: §5 fixes EXP-008 A3/A4's charged requirement at **0**, and a zero-charge experiment charges the same amount — nothing — under either reading of PLAN. The conflict is therefore **inert for EXP-008 and remains OPEN** for any future experiment that would charge live TRAIN executions. No arbitration is enacted, implied or available to be cited from this entry.

**5 — Decision: EXP-008 A3/A4 is scoped as a ZERO-CHARGE DERIVED ABLATION. Charged live TRAIN executions = 0.**

* **A3 (reward variants)** is produced by recomputation over the already-recorded EXP-002 TRAIN observation store, using the machinery the repository already runs for exactly this purpose: `src/sparkrl/agent/q0.py` builds the offline Q-function from *"the EXP-002 stored run records (`results/experiments/exp-002`), and only TRAIN cells"*, valuing each observation by *"the per-observation FROZEN R3 reward (`sparkrl.rl.reward`), using T_ref from the EXP-002 gate artifact (B0 median, seed 0)"*. The registered A3 comparator — `A3-time-only`, `R = 1.0 · clip((T_ref − T)/T_ref, −1, +1)`, failure `R = −1.0` (DEC-030 §3.2; `src/sparkrl/training/exp008.py` header) — is a function of the same stored fields. Recomputing it consumes **no live Spark execution**.
* **A4 (action-space granularity)** is produced as a structural restriction. `mode4 = {0, 3, 6, 9}` is a strict subset of the frozen 12-action grid (DEC-030 §4.3; `src/sparkrl/rl/action.py` `MODE4_SUBSET`), so a mode4 greedy policy is derivable from any mode12 Q-table by argmax over the subset. No execution is required to derive it.
* **A3-R4-log-ratio is NOT retained under this scope.** It remains INCOMPLETE in the eight respects DEC-030 §3.4 enumerates and is refused before any computation by `IncompleteFormulaError`. Whether R4 is ever retained is DEC-030 §12 field 1 and is **not decided here**.
* **Charged requirement: 0.** This satisfies DEC-031 §11 by the **scope-reduction** route — *"an explicit scope reduction to ≤ [32] charged live TRAIN executions, enacted by its own decision"* — and requires **no cap amendment**. `cap_amendment_required` = **false**.

**6 — Cache hits are not the basis of this decision.** DEC-031 §5 non-charged category 2 (*"Cache hits — a replayed/cached transition consumes no live Spark execution"*) is **not** invoked here and is **not** extended. §5's zero charge rests on the fact that **nothing is executed at all** — no environment step, cached or live, is taken. No policy about cache accounting is created, relaxed or implied.

**7 — What this costs scientifically. Stated plainly, not minimised.**

**This decision does not execute EXP-008 as `docs/PLAN.md` line 315 registered it. It substitutes a derived ablation for a trained one, and it weakens a scientific claim.** A3 under this scope is an ablation of the **offline initialization**, not of **online learning**. RQ4 asks *"How do reward-function variants and action-space granularity affect **learning stability** and final policy quality?"* — the **learning-stability half of RQ4 is UNANSWERED and is left unanswered by this decision.**

Following DEC-011's template verbatim in form: the write-up **must state that A3/A4 were not executed as trained arms and why, making no claim about what they would have shown**, and the learning-dynamics dimension of RQ4 is left unexamined **by decision, and that limitation must be stated as such in the report — it is not a measured result.** No inferential claim, no threshold and no statistic is created by this entry (DEC-030 §8 stands: any EXP-008 analysis *"remains descriptive-only with no thresholds invented"*).

**8 — What survives, and one result available at zero cost.** PLAN line 315's stated acceptance is *"ablation table"*, and a derived ablation table discharges that column. Beyond it, the following is derivable today from signed evidence, with **0** executions, and is recorded as available — **not asserted as a finding, which requires the analysis the B6 and authorization decisions still gate**:

Under the frozen grid mapping `grid_index = parallelism_index × 4 + shuffle_index` (`src/sparkrl/experiments/grid.py` lines 177–188; DEC-030 §4.3), `G-p8-sp16` = index **8** and `G-p8-sp64` = index **10**, and **neither is in `mode4 = {0, 3, 6, 9}`**. Index 8 is byte-identical to the frozen B1 (DEC-016/DEC-017: *"parallelism 8 this is `G-p8-sp16`, byte-identical to the frozen B1"*), is B2 for F1/F2, and is the configuration DEC-020 §A records the statics as having converged on. Index 10 is B2 for F3 (DEC-020 §C). **Two of the three frozen B2 definitions, and B1 itself, are unreachable under the reduced action space.** That is a structural statement about action-space granularity, derived from already-signed artifacts.

**9 — Alternative considered and NOT adopted, recorded so the choice is on the record.** The other route DEC-031 §11 admits is an **explicit cap/PLAN amendment**: raising SC6's cap at `docs/PLAN.md` line 45 under the PLAN header's change-control rule (*"Any change requires a new `DEC-xxx` entry in `DECISIONS.md` and explicit user/supervisor approval"*), and executing EXP-008 at EXP-007 parity (70 charged executions per arm; 3 shared-control arms = 210, 4 arms = 280). **It is the only route that answers RQ4 as registered, and it is defensible.** It is not adopted because **it amends a SUCCESS CRITERION that is currently SATISFIED** (468 ≤ 500) — SC6 would then pass only because the bar moved — and because it erodes the claim `docs/PLAN.md` line 35 identifies as the project's research gap (*"sample-efficient online adaptation (tabular/bandit RL) for Spark config selection"*), line 27 (*"within ≤500 cached executions"*) and line 101 (Candidate C at *"~600–900 total, cache-bounded"* against *"B: Pure online RL — 1000s (infeasible)"*). It would additionally change a load-validated frozen research constant (`configs/rl.yaml` line 17, under the file's own rule that *"these are research constants, NOT tuning parameters. Any disagreement is a hard error"*) and every validator and test pinning 500. **No DEC has ever amended `docs/PLAN.md`**; DEC-031 §15 and DEC-032 §11 both record its sha256 `db5e8210…ee63` as unchanged, re-verified current at this entry's recording. **This entry forecloses nothing: §5's zero-charge scope leaves the amendment route fully open, and a later decision may take it.** Choosing it is the operator's call.

**10 — Also considered, and FORECLOSED by arithmetic and by signed decisions.**

* **Re-scope to fit 32 by consuming R8 scope-ladder rung 3** (`docs/PLAN.md` line 361, *"shrink ablations to A1+A3"*; rungs 2–4 recorded as available by DEC-011). The mechanism is real and rung 3 is genuinely unconsumed. The arithmetic is not favourable: 2 arms × 1 seed × 2 epochs = **28**, or 2 arms × 2 seeds × 1 epoch = **28**, both ≤ 32, but at one epoch each of the 7 T_ref-calibrated TRAIN cells is visited once — **7 of 7 × 12 = 84 (cell, action) pairs, 8.3% coverage**; epsilon under the frozen schedule (1.0 → 0.05, decay 0.95/episode) stands at **0.698** after 7 episodes and **0.488** after 14, against **0.166** for EXP-007's arms and **0.050 / 0.081 / 0.116** for the three main-study policies; the frozen early-stop rule (2 consecutive stable epochs) cannot meaningfully fire; and DEC-011's measured reference is that **175 executions covered only 68.3% of the 5-state footprint**. At one seed there is no cross-seed variance estimate; at two seeds it is n = 1 per cell against the measured noise band (median CV **0.045485**, worst cell **0.118864**, DEC-018 Decision F — the 11.89% band DEC-020 §A used to bound every EXP-005 finding). DEC-020 §A closed **245** TEST executions as descriptive-only with SC2/SC3/SC4 **UNDECIDED**; 28 cannot do better. **It would spend the entire remaining SC6 headroom for a result no stronger than §5's, and leave 4 executions forever.** Rung 3 is therefore **NOT consumed by this entry and remains available under R8.**
* **Charging EXP-008 to its own PLAN line 315 envelope** — **foreclosed by §3.**
* **Not executing EXP-008 at all and recording RQ4 unanswered** (the DEC-011/A5 shape) — viable and honest, but strictly dominated: it costs the same 0 executions as §5 while producing neither the register's ablation-table deliverable nor §8's derivable result.

**11 — What this decision deliberately does NOT decide.** The **B6 implementation decision** (DEC-030 §15 gate item 3); the **authorization decision** (gate item 4); the **final arm set** (DEC-030 §12 field 1), including whether A3-R4 is ever retained; the **Q0 source per arm** (field 2); the **state schema** (field 3); the **A3 action schema** (field 4); the **A4 control-pairing reward** (field 5); whether A3 and A4 share a basis (field 13); the **statistical governance** of EXP-008 (field 14; DEC-030 §8 stands unchanged); the **R4 complete specification** (field 15); the **amendment mechanism** for the PLAN tension of DEC-031 §10; the classification of the 2026-09-16 and 2026-09-19 **zero-live manifests** (DEC-032 §7.3, still UNRESOLVED); and **`scripts/validate_day30.py` / `validate_day31.py`** maintenance. DEC-030 §12 fields **6–12 and 16** (seeds, TRAIN cells, episode horizon, early-stop rule, AQE confirmation, warm-up, cache behaviour, hyperparameter deviations) are **INAPPLICABLE BY CONSTRUCTION** under §5's zero-execution scope — they are **not** silently resolved, and they **revive in full** if any later decision restores a trained scope. Field **17 (B5 charging rule)** is resolved by §3 and §5 for EXP-008 only.

**12 — Non-authorization firewall (explicit).**

| Item | State recorded by this entry |
|---|---|
| **EXP-008 execution authorization** | **FALSE / NO** |
| **Implementation authorization (A3/A4, B6)** | **FALSE / NO** |
| **EXP-008 charged live TRAIN executions** | **0** |
| **SC6 cap** | **500 — UNCHANGED, NOT RAISED** |
| **SC6 ledger** | **468 charged / 32 remaining — UNCHANGED** |
| **A5** | **DISABLED** (DEC-011; re-affirmed DEC-030 §9, DEC-031 §14); `configs/rl.yaml` `gamma` stays 0.0 |
| **TEST** | **NOT AUTHORIZED** — nothing here opens TEST for anything |
| **R8 scope-ladder rungs 2–4** | **UNCONSUMED — all remain available** |
| **`docs/PLAN.md`** | **UNCHANGED — no line edited** |
| **`configs/rl.yaml`** | **UNCHANGED** |
| **Historical decisions** | **UNCHANGED** — DEC-001 … DEC-026, DEC-030 … DEC-033 are not rewritten; this entry is appended, never substituted |
| **Spark / training / TEST executions performed by this entry** | **0 / 0 / 0** |

**13 — Evidence and fingerprints (read-only; nothing listed here was modified).**

| Source | Role | SHA256 |
|---|---|---|
| `docs/PLAN.md` | SC6 line 45; EXP-007 line 314; EXP-008 line 315; R8 scope tier line 361; header change-control lines 3–7 | `db5e82102833efe6bab8db1adaf1b35ad195faf385e63ab296d50562e349ee63` (**unchanged**; identical to the value DEC-031 §15 and DEC-032 §11 record) |
| `configs/rl.yaml` | `live_execution_cap: 500` (line 17); epsilon schedule (lines 9–11); `early_stop_stable_epochs: 2` | `8ca70d6dd7df68841c409a4441dc538616206bccea7877b28c73df20e6428b80` (**unchanged**) |
| `src/sparkrl/training/exp008.py` | `guard_split` TRAIN-only enforcement (lines 207–214); frozen A3/A4 arm layer | `0a2252b378dda0a630106795ef13287eda86d3a50c0e294ef26f3768bc54ceba` (**unchanged**) |
| `docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md` | DEC-030 identity preserved; §12 fields; §15 gate chain | `ec487bf2a84a9c1a6f506bdd83c71b7c7bb7ae2cceaf7e761f000c7201912a5a` (**unchanged**) |
| `docs/research/DEC_033_GOVERNANCE_RECONCILIATION.md` | canonical 468/32 ledger | `3e6d0d7c4b5359990ea6ac6766e226d860c5fea2fb0e8639cc73fff645932b21` (**unchanged**; committed `c2e980a`) |
| `src/sparkrl/agent/q0.py`, `src/sparkrl/experiments/grid.py`, `src/sparkrl/rl/action.py`, `src/sparkrl/training/ablation.py` | cited for §5 and §8 mechanics | **NOT MODIFIED** |
| `results/training/**/manifest.json` | 22 manifests | **NOT MODIFIED** |

**14 — Validation of this entry (read-only, zero Spark).**

| Check | Result |
|---|---|
| DEC-034 is the next free identifier (`grep` for DEC-033/DEC-034 headings in `DECISIONS.md`) | PASS |
| `DECISIONS.md` appended only; every prior byte intact | PASS |
| DEC-030 / DEC-031 / DEC-032 / DEC-033 artifacts unchanged (SHA256 re-checked) | PASS |
| `docs/PLAN.md`, `configs/rl.yaml` unchanged (SHA256 re-checked) | PASS |
| SC6 cap = 500; charge = 468; remaining = 32; `232+84+20+126+6 = 468` | PASS |
| EXP-008 charged requirement under §5 = 0 ≤ 32; DEC-031 §11 satisfied by scope reduction | PASS |
| No cap amendment enacted | PASS |
| No R8 scope-ladder rung consumed | PASS |
| TRAIN-only enforcement quoted verbatim from `exp008.py:207–214` | PASS |
| No execution, implementation or TEST authorized | PASS |
| A5 remains DISABLED | PASS |
| Spark / training / TEST executions performed | **0 / 0 / 0** |

**Status.** **DECIDED.** The register-line exemption is recorded as turning on the **SPLIT**, not on the existence of a register line, and is therefore **inapplicable** to TRAIN-only EXP-008 A3/A4 — with EXP-007 (own ~300 register line, charged 126 to SC6) as the controlling counter-example. EXP-008 A3/A4 is scoped as a **ZERO-CHARGE DERIVED ABLATION**: charged live TRAIN executions = **0**, satisfying DEC-031 §11 by scope reduction with **no cap amendment**. The DEC-011 PLAN-internal pot conflict is **MOOTED for EXP-008, not arbitrated, and remains OPEN**. The **learning-stability half of RQ4 is UNANSWERED by decision** and must be reported as a stated limitation with no claim about what it would have shown. The cap-amendment alternative (§9) is recorded, **not foreclosed**. `SC6 cap = 500, NOT RAISED`. `Ledger = 468 / 32, unchanged`. `EXP-008 execution authorization = NO`. `A3/A4 implementation = NOT AUTHORIZED`. `A5 = DISABLED`. `TEST = NOT AUTHORIZED`. `PLAN.md = UNCHANGED`. Historical decisions DEC-001 … DEC-026, DEC-030 … DEC-033 = **UNCHANGED**. Supervisor counter-signature: **PENDING** (conventional expectation only; never simulated; not a prerequisite under DEC-018 Decision A). **NO SUPERVISOR HAS REVIEWED THIS ENTRY.** A future review is a new entry; this one is never rewritten. **This entry performs 0 Spark executions and trains nothing.**

*End of DEC-034.*

---

**Ledger supersession note (appended 2026-09-20, before signature).** This entry was drafted against the then-current ledger **468 / 32** (DEC-033). Five completed smoke TRAIN executions dated 2026-09-20 07:37-07:56Z were discovered afterwards and classified by **DEC-038**, making the canonical ledger **483 / 17** at signature. The figure is corrected here rather than in the body, so the drafting chronology stays visible. No conclusion in this entry depends on the difference: the scope resolved here has a charged requirement of **0**, which satisfies any headroom. The change strengthens it - the 28-execution single-epoch alternative rejected in the body no longer fits at all (28 > 17), so that option is now foreclosed by arithmetic as well as by design.

## DEC-035 | 2026-09-20 | EXP-008 A3/A4 implementation decision (B6; DEC-030 s15 gate item 3) - ADOPTED with fields 1/13/14 deferred; execution authorization remains NO (Day 38, C2)

**Decision ID:** DEC-035
**Date:** 2026-09-20
**Scope:** DEC-030 §15 gate-chain item (3) only — the implementation decision resolving B6, with green zero-Spark tests. **Nothing else.**
**Status:** DECIDED — the EXP-008 A3/A4 implementation at HEAD `c2e980a` is ADOPTED as the B6 resolution, with DEC-030 §12 fields **1, 13 and 14** explicitly DEFERRED to the methodology/authorization decisions. **`EXP-008 execution authorization = NO`.**
**Standalone decision artifact.** The authoritative log entry is the appended DEC-035 section of `DECISIONS.md`; this document carries the same decision content, self-contained, so the decision also exists as an addressable artifact (the DEC-031/DEC-032 convention).
**Supersedes nothing.** DEC-030, DEC-031, DEC-032 and DEC-033 are unchanged; no historical decision entry is rewritten. `docs/research/DAY37_EXP008_B6_IMPLEMENTATION_REPORT.md` and `results/evaluation/exp008_b6_implementation.json` are **adopted as evidence and retained byte-identical** — they are B6-time records and are not regenerated.

> **This entry performs 0 Spark executions, trains nothing, executes no TEST, creates no run directory, and modifies no manifest, result, budget, ledger, configuration or implementation file.**
> **EXP-008 execution authorization remains NO. A5 remains DISABLED. TEST remains NOT AUTHORIZED. `docs/PLAN.md` is UNCHANGED. The SC6 cap remains 500 and is NOT raised.**

---

## 0 — Identifier resolution

`DECISIONS.md` headings run **DEC-001 … DEC-026**, plus **DEC-031** (`DECISIONS.md:2113`) and **DEC-032** (`DECISIONS.md:2241`). Two further decisions are formally recorded **outside** `DECISIONS.md`, by the convention DEC-031 §0 established for DEC-030: **DEC-030** (`docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md`) and **DEC-033** (`docs/research/DEC_033_GOVERNANCE_RECONCILIATION.md`; `grep -n "DEC-033" DECISIONS.md` returns **zero** lines). A repository-wide search for `DEC-034` and `DEC-035` returns **nothing**: neither identifier is occupied by any artifact, heading or code reference.

**DEC-035 is the identifier assigned to this entry by the operator's decision-drafting pass.** This entry does **not** claim, reserve, describe or depend on DEC-034; if DEC-034 is recorded by a sibling entry, its content is not read into this one. That DEC-033 currently has no `DECISIONS.md` section is **recorded, not corrected here** — DEC-030 is in the same position and DEC-031 §0 preserved its identity rather than renumbering it.

## 1 — Scope

DEC-030 §15 (`docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md:372`) sets the gate chain: *"(1) this DEC-030; (2) a separate budget DEC resolving B5; (3) a separate implementation DEC resolving B6 with green zero-Spark tests; (4) a separate authorization DEC … with worst-case counts and ledger charge, plus a clean preflight re-run."*

Item (1) is DONE (DEC-030). Item (2) is DONE (DEC-031, as the ledger was later moved by DEC-033). **This entry is item (3), and only item (3).** Item (4) is untouched and remains open.

In scope: (a) what the EXP-008 A3/A4 implementation actually is today; (b) whether its zero-Spark tests are green; (c) which DEC-030 §12 fields the implementation enforces fail-closed and which it does not; (d) whether anything implemented exceeds what DEC-030 froze, and whether A5 is inert; (e) the disposition of the one owed item the B6 report left open. Nothing else.

## 2 — Why a decision is required, and what the existing evidence is

The B6 evidence exists and disclaims decision status in terms. `docs/research/DAY37_EXP008_B6_IMPLEMENTATION_REPORT.md:12`:

> *"This report is **not a decision**. DEC-030 §15 gate-chain item (3) expects a separate decision entry to record B6; this document and its JSON supply the evidence that item needs, nothing more. No DEC number is claimed, no authorization is granted, and no methodological field is frozen here."*

Its §10 row 1 restates the same gap: *"The B6 implementation decision itself (DEC-030 §15 gate item 3) … This report and its JSON are evidence, not a decision entry."* **DEC-035 is that decision entry.** It adds no implementation, changes no code, and invents no methodology.

The adopted evidence is: `docs/research/DAY37_EXP008_B6_IMPLEMENTATION_REPORT.md`, `results/evaluation/exp008_b6_implementation.json`, `src/sparkrl/training/exp008.py`, the additive change to `src/sparkrl/rl/reward.py`, `configs/exp008.yaml`, and the three zero-Spark test files `tests/unit/test_exp008_{scope,action,reward}.py` — all tracked at HEAD `c2e980a` (`git log --oneline -1 -- src/sparkrl/training/exp008.py` → `2c00236 feat(gov): commit the EXP-006/007/008 implementation and repair the validator chain`), working tree clean.

## 3 — What is actually implemented today (established by reading the code, not the report)

**3.1 The arm set — exactly the DEC-030 four, and no A5.**

```python
A3_ARMS  = (ARM_A3_R3, ARM_A3_TIME_ONLY, ARM_A3_R4_LOG_RATIO)   # exp008.py:92
A4_ARMS  = (ARM_A4_MODE4,)                                       # exp008.py:93
ALL_ARMS = A3_ARMS + A4_ARMS                                     # exp008.py:94
```

`ARM_REWARD_FORMULA` (`exp008.py:99-103`) binds each A3 arm to its own reward by arm identity; A4's reward is deliberately absent from that map because DEC-030 §12 field 5 leaves the A4 control pairing unfrozen.


## DEC-039 | 2026-09-21 | EXP-008 authorization decision — zero-charge derived ablation authorized (gate item 4); trained executions remain NOT AUTHORIZED (Day 38/39)

**Decision ID:** DEC-039
**Date:** 2026-09-21
**Scope:** The EXP-008 **authorization decision** only (DEC-030 §15 gate item 4: worst-case counts, ledger charge, clean preflight re-run), plus production of the zero-charge DERIVED ablation exactly as DEC-034 §5 defines it. Nothing else.
**Status:** DECIDED — **zero-charge derived ablation AUTHORIZED and PRODUCED (0 executions, 0 charge); trained EXP-008 execution authorization remains NO.**
**Standalone decision artifact.** Companion document `docs/research/DEC_039_EXP008_AUTHORIZATION_DERIVED_ABLATION.md` carries the same decision content, self-contained (DEC-037/DEC-038 convention). Companion machine artifacts: `results/evaluation/exp008_derived_ablation.json` (fingerprint `18b33979a38e82ef…`) and `results/evaluation/exp008_preflight_rerun.json` (fingerprint `16779a4a4970f8db…`), both written by the deterministic zero-Spark generator `scripts/generate_exp008_derived_ablation.py`.
**Supersedes nothing.** DEC-001…DEC-026, DEC-030…DEC-038 are unchanged; appended, never rewritten.

> **This entry performs 0 Spark executions, trains nothing, executes no TEST, creates no run directory, and modifies no manifest, no prior result artifact, no budget counter and no configuration.**
> **EXP-008 trained-execution authorization = NO. Zero-charge derived ablation = AUTHORIZED. A5 = DISABLED. TEST = NOT AUTHORIZED. SC6 cap = 500, NOT raised. `docs/PLAN.md` = UNCHANGED.**


**3 — The derived ablation as DEC-034 §5 defines it (0 executions).** **A3**: `A3-time-only` (`R = 1.0 · clip((T_ref − T)/T_ref, −1, +1)`, failure `R = −1.0`) recomputed against `A3-R3-frozen` over the already-recorded EXP-002 TRAIN observation store via `src/sparkrl/agent/q0.py`, T_ref from the EXP-002 gate artifact, TRAIN cells only. **A4**: `MODE4_SUBSET = {0, 3, 6, 9}` is a strict subset of the frozen 12-action grid, so the mode4 greedy policy is derived structurally — argmax over the subset of the same mode12 Q-table (tie-break: lowest index), from the `A3-R3-frozen` table per DEC-036 field 5. **A3-R4 is NOT retained** (dropped by DEC-036 §8; registered but not executable; no Q0 under R4 ever existed, none constructed here).

**4 — The ablation table (PLAN line 315's acceptance, zero-charge form; descriptive only — no threshold, no inferential statistic, DEC-030 §8).** 4 state rows × 12 actions = 48 evidence pairs. Greedy actions (mode12): `agg` 8 = G-p8-sp16, `join` 8, `mixed` 9 = G-p8-sp32, `rdd_sort` 7 = G-p4-sp128 — **identical under both reward shapes** (greedy agreement on every state row). **8 of 48 pairs differ in Q-value, all in the `rdd_sort` row (actions 4–11).** Greedy mode4 (from R3): `agg` 9, `join` 9, `mixed` 9, `rdd_sort` 0 = G-p2-sp16. **Structural reachability (DEC-034 §8's available-not-asserted result, now verified and recorded):** mode4 = {G-p2-sp16, G-p2-sp128, G-p4-sp64, G-p8-sp32}; **B1 (`G-p8-sp16`, index 8) is unreachable under the reduced action space; two of the three distinct frozen B2 definitions are unreachable (`G-p8-sp16` for F1_agg/F2_join, and `G-p8-sp64` (index 10) for F3_rdd); `G-p8-sp32` (index 9, F5_mixed) is reachable.** These are descriptions of recorded data, not claims about training.

**5 — Stated limitations (verbatim, part of the deliverable and recorded in the artifact).** (i) **"A3 here ablates the OFFLINE INITIALIZATION, not ONLINE LEARNING."** (ii) **"RQ4 asks about learning stability and final policy quality; the learning-stability half is UNANSWERED by this decision and is reported as a stated limitation, with no claim about what a trained comparison would have shown."** (iii) **"Descriptive only — no threshold and no inferential statistic is computed or asserted (DEC-030 §8)."** The final-policy-quality half of RQ4 is likewise not answered: the derived policies are initializations, not trained policies, and no quality claim is made.

**6 — What this entry does NOT decide.** Whether EXP-008's trained study (PLAN line 315, ~300 runs) is ever executed, and under which branch if so; any change to `docs/PLAN.md` or the register line (the DEC-031 §10 tension stays open; line 315 stays planned and its ~300 trained runs are NOT consumed); the R4 specification (stays dropped and registered); any statistical treatment beyond descriptive reporting; EXP-009/EXP-010; `scripts/validate_day30.py` maintenance; the zero-live manifest classification (DEC-032 §7.3, still UNRESOLVED). DEC-030 §12 fields 6–12 and 16 stay inapplicable by construction and revive in full if a trained scope is ever restored.

**7 — Non-authorization firewall.** EXP-008 trained-execution authorization **NO — UNCHANGED**; zero-charge derived ablation **AUTHORIZED**; worst-case counts **0 / 0**; SC6 cap **500, NOT raised**; ledger **483 / 17 — UNCHANGED**; A5 **DISABLED**; TEST **NOT AUTHORIZED**; R8 rungs 2–4 **UNCONSUMED**; `docs/PLAN.md` **UNCHANGED**; `configs/rl.yaml` **UNCHANGED**; historical decisions **UNCHANGED**; Spark / training / TEST executions performed by this entry **0 / 0 / 0**.

**Status.** **DECIDED.** The DEC-030 §15 gate chain is **complete** (items 1–4 satisfied; item 4 by this entry with worst-case **0** executions, **0** charge, and a **clean preflight re-run**). The zero-charge derived ablation is **AUTHORIZED and PRODUCED** per DEC-034 §5; the ablation table is delivered as PLAN line 315's acceptance in its zero-charge form; **A3-R4 is not retained**; **no DEC-036 branch is selected**. `SC6 cap = 500, NOT raised`. `EXP-008 trained-execution authorization = NO`. `A5 = DISABLED`. `TEST = NOT AUTHORIZED`. `docs/PLAN.md = UNCHANGED`. Historical decisions (DEC-001 … DEC-026, DEC-030 … DEC-038) = **UNCHANGED**. Supervisor counter-signature: **PENDING** (conventional expectation only; never simulated; not a prerequisite under DEC-018 Decision A). **NO SUPERVISOR HAS REVIEWED THIS ENTRY.** A future review is a new entry; this one is never rewritten. **This entry performs 0 Spark executions and trains nothing.**

---

**0 — Identifier resolution.** Headings run DEC-001…DEC-026 and DEC-031…DEC-038 (DEC-030/DEC-033 out-of-ledger per DEC-031 §0 / DEC-034 §0). No DEC-039 artifact exists. The next sequential identifier is **DEC-039**.

**1 — Ledger restated, not re-derived.** SC6 cap **500**, unchanged, **not raised**. Canonical ledger **483 charged / 17 remaining** (`232 + 84 + 20 + 126 + 6 + 15 = 483`; DEC-038). This entry's **worst-case live TRAIN executions = 0**; **worst-case ledger charge = 0**. Ledger after this entry: **483 / 17 — unchanged.**

**2 — The authorization (gate item 4; the gate chain completes).** Gate items 1–3 are satisfied (DEC-030, DEC-031, DEC-035). This entry authorizes **only** the zero-charge derived ablation scoped by DEC-034 §5, with worst-case counts **0** and charge **0**, supported by the clean preflight re-run (`exp008_preflight_rerun.json`: all six blocking findings `B1-A3-UNFROZEN`, `B2-A4-UNFROZEN`, `B3-Q0-UNFROZEN`, `B4-CONTROLS-UNFROZEN`, `B5-BUDGET-EXHAUSTED`, `B6-IMPLEMENTATION-GAP` **RESOLVED**, cited to DEC-030/DEC-031/DEC-033/DEC-034/DEC-035/DEC-036/DEC-038; N1–N6 dispositioned as the record supports). **Trained EXP-008 execution remains NOT AUTHORIZED.** DEC-036 §10 branches **P (210) / R (140) / M (21) are NOT selected** — each exceeds the 17-execution envelope; the branch rule stays frozen and revives under R8 (rungs 2–4 UNCONSUMED). A5 DISABLED (DEC-011). TEST NOT AUTHORIZED.

**3.2 The reward handling.**

* `R3` — unchanged. `RewardCalculator.__init__` takes `formula` as **keyword-only**, defaulting to the frozen `R3` (`src/sparkrl/rl/reward.py:191-192`), so no existing call site changes behaviour. `configs/reward.yaml` is byte-identical at `a52131d5…db1b`.
* `A3-time-only` — implemented exactly as DEC-030 §3.2 froze it: `TIME_ONLY_WEIGHTS` (`reward.py:99`) gives `w_time=1.0, w_task=0.0, w_spill=0.0, w_failure=1.0`, clip `[-1,+1]`, failure `-1.0`, module constants never read from `configs/reward.yaml`. **DEC-030 §3.2's mandatory classification is carried through unchanged and is restated here: time-only is a MULTI-TERM REMOVAL from R3 — the task-imbalance term AND the spill-waste term are removed simultaneously — and no future analysis may attribute an A3-time-only-versus-R3 difference to a single removed term.**
* `A3-R4-log-ratio` — registered, not executable. `REGISTERED_FORMULAS` contains it; `IMPLEMENTED_FORMULAS` (`reward.py:93`) does not. `build_reward_calculator` (`exp008.py:284-301`) raises `IncompleteFormulaError` naming all eight DEC-030 §3.4 unresolved semantics before any computation and before any Spark execution.

**3.3 The action subset — reused, never redefined.**

```python
A4_ACTION_MODE   = MODE4
A4_ACTION_SUBSET = MODE4_SUBSET          # frozenset({0, 3, 6, 9})   exp008.py:108-109
```

`A4_ACTION_SUBSET` **is** the frozen `MODE4_SUBSET` object from `src/sparkrl/rl/action.py`, which is byte-identical at `580cf010…c0528` — the value DEC-030's freeze JSON recorded. `a4_action_configurations()` (`exp008.py:320-339`) derives all four configurations from the frozen `ActionMapper`, preserving original indices and config names. No action is renumbered and no 4-wide table is produced.

**3.4 The guards (all firing before any Spark execution).**

| Guard | Location | Refuses |
|---|---|---|
| `guard_arm` | `exp008.py:177-183` | any arm outside `ALL_ARMS`; routes `A5` to its own error first |
| `guard_a5` | `exp008.py:186-204` | `arm == "A5"`; `multi_step=True`; any `gamma != 0.0` |
| `guard_split` | `exp008.py:207-214` | any split != `TRAIN` |
| `guard_cell` / `guard_train_cells` | `exp008.py:217-243` | cells outside the frozen domain (re-raised as `Exp008ConfigError`) and any non-TRAIN cell |
| `guard_metrics` | `exp008.py:246-257` | metrics carrying `split`/`test_family`/`test_scale`/`test_seed` |
| `guard_agent_seeds` | `exp008.py:260-281` | unset seeds (`Exp008IncompleteError`), non-int, duplicate, empty — **never invents a seed set** |
| `build_reward_calculator` / `guard_reward_variant` | `exp008.py:284-311` | unregistered variants; R4 |
| `guard_action_mode_for_arm` | `exp008.py:342-357` | unset mode; unknown mode; any non-`mode4` mode for the A4 arm |
| `guard_q0_projection` / `guard_q0_source` / `guard_q0_rows` / `guard_q0_for_mode` | `exp008.py:384-438` | every projection; any source outside `q0-exp002/v1` and `q0-neutral/v1`; any Q0 row not 12 wide; any Q0 at all for A3-R4 |
| `arm_config_from_mapping` | `exp008.py:673-721` | unknown configuration keys (closed schema) and wrong value types |

**3.5 The scope constants that ARE fixed, and their DEC-030 authority.**

| Constant | Value | Frozen by |
|---|---|---|
| `FROZEN_DATASET_SEED` (`exp008.py:116`) | `0`, and any other value is refused | DEC-030 §3.2 *"Dataset seed \| 0 (frozen: T_ref calibrated for seed 0 only)"* — a measured fact |
| `q0_projection` | `False`, unconditionally | DEC-030 §5.1 rules 2–4 |
| `Q0_ROWS_WIDE` (`exp008.py:119`) | `12` | DEC-030 §5.4 *"EXISTING FROZEN MAPPING"* |
| A4 action mode | `mode4`, locked | DEC-030 §4.2 / §4.3 |
| A3 arm→reward binding | by arm identity | DEC-030 §3 |
| `EXECUTION_AUTHORIZED` (`exp008.py:78`) | `False`; `SPARK_EXECUTIONS = TRAINING_EXECUTIONS = TEST_EXECUTIONS = 0` | DEC-030 §11; DEC-031 §14 |

## 4 — Zero-Spark tests: GREEN (re-run for this entry)

```
$ python -m pytest tests/unit/test_exp008_scope.py tests/unit/test_exp008_action.py tests/unit/test_exp008_reward.py
103 passed in 0.24s        (exit 0)
```

The 0.24 s wall time is itself evidence that no Spark session was started. The per-file split recorded by the B6 artifact is `test_exp008_scope.py` **50**, `test_exp008_action.py` **32**, `test_exp008_reward.py` **21** = **103**, which matches the re-run total exactly.

**What this entry did NOT run, and does not assert:** the full `tests/unit` suite, any validator in `scripts/` (several regenerate tracked artifacts), any integration test, any training, any TEST, and any Spark. The *"full unit suite green, seven validators PASS"* state reported to this drafting pass is **not re-verified here** and must be re-verified at gate item (4)'s clean preflight re-run, as DEC-030:372 already requires.

**Gate item (3)'s "with green zero-Spark tests" condition is therefore SATISFIED on the evidence this entry itself produced.**

## 5 — What the implementation presumes: NOTHING that DEC-030 left unfrozen (one named consequence)

This was the specific risk B6 exists to surface: a presumption baked into code while the field is marked *"UNFROZEN — SEPARATE DECISION REQUIRED"*. DEC-030 §3.2 does record presumed values for state schema (state-v1.5), action schema (mode12), alpha (0.2), gamma (0.0), epsilon (1.0→0.05 @0.95), AQE (off) and T_ref (EXP-002 TRAIN B0 median). **The implementation inherits none of them.** Every one is a required-but-unset field (`exp008.py:150-166`) and an explicit `null` in the shipped artifact (`configs/exp008.yaml`: `action_mode: null`, `state_schema: null`, `q0_source: null`, `alpha: null`, `gamma: null`, `epsilon_schedule: null`, `aqe_condition: null`, `t_ref_source: null` on all four arms). `validate_configuration()` raises `Exp008IncompleteError` listing them (`exp008.py:625-633`), and `tests/unit/test_exp008_scope.py:138` proves it field by field.

**One named consequence, recorded not hidden.** DEC-030 §12 field 16 covers *"Epsilon schedule / alpha / gamma if deviating from frozen values"*. `gamma` is required-but-unset, but `guard_a5` (`exp008.py:200-204`) then refuses every value except `0.0`. The admissible set for `gamma` is therefore `{0.0}`. That is **not** a new freeze: it is DEC-030 §9's A5 lock (*"`configs/rl.yaml` gamma remains 0.0; DEC-030 makes no change and permits none"*) expressed in code. DEC-035 adopts it as a restatement of the A5 lock and freezes nothing new.

## 6 — DEC-030 §12 coverage: fail-closed on 15 of 18 (16 for A4) — CORRECTION OF RECORD

`A3_REQUIRED_FIELDS` (`exp008.py:150-166`) contains exactly **fifteen** names; `A4_REQUIRED_FIELDS` adds `reward_variant` (`exp008.py:167`), giving **sixteen** for A4. DEC-030 §12 (`…METHODOLOGY_FREEZE.md:333-354`) lists **eighteen** fields.

| §12 # | Field | Representation in code | Fail-closed? |
|---|---|---|---|
| 1 | Final arm set to execute | none — all four arms always present | **NO** |
| 2 | Q0 source per arm | `q0_source` + `guard_q0_source` | YES |
| 3 | State schema per arm | `state_schema` | YES |
| 4 | Action schema for A3 | `action_mode` + `guard_action_mode_for_arm` | YES |
| 5 | Reward arm for A4 control pairing | `reward_variant` (A4 only) | YES (A4) |
| 6 | Seeds | `agent_seeds` + `guard_agent_seeds` | YES |
| 7 | TRAIN cells | `train_cells` + `guard_train_cells` | YES |
| 8 | Episode horizon | `episode_horizon` | YES |
| 9 | Early-stop rule | `early_stop_rule` | YES |
| 10 | AQE condition | `aqe_condition` | YES |
| 11 | Warm-up behavior | `warm_up_behavior` | YES |
| 12 | Cache behavior | `cache_behavior` | YES |
| 13 | Whether A3 and A4 share seeds/cells/horizon | none — a cross-arm field with no per-arm slot | **NO** |
| 14 | Statistical governance | `statistical_governance` field EXISTS but is **not required** | **NO** |
| 15 | R4 complete specification | `IncompleteFormulaError` — strongest enforcement in the module | YES |
| 16 | Epsilon / alpha / gamma deviations | `epsilon_schedule`, `alpha`, `gamma` (see §5) | YES |
| 17 | Live-execution charging rule | `live_execution_charging_rule` | YES |
| 18 | Implementation authorization (B6) | `EXECUTION_AUTHORIZED = False`; this entry | n/a |

**Proved by direct read-only construction, not inferred.** An `A3-time-only` configuration supplying all fifteen required fields, with `statistical_governance`, `execution_budget`, `code_fingerprint`, `t_ref_fingerprint` and `q0_variant` left `None`, makes `validate_configuration()` return normally, `unresolved_fields()` return `()`, and `arm_runtime_kwargs()` return component kwargs including a constructed `RewardCalculator`. The repository's own test records the same behaviour by name: `tests/unit/test_exp008_scope.py:144` — `test_a_fixture_complete_config_validates_without_authorizing_anything`.

> **Correction of record (following the DEC-032 §4 precedent for correcting a work-stream statement without rewriting the artifact).** The B6 report §9.4 states that the implementation *"gives the 18 fields of DEC-030 §12 an explicit, schema-safe, fail-closed representation."* The **explicit** and **schema-safe** halves are accurate — every one of the eighteen appears, and unresolved values are emitted as `null` and listed under `unresolved_fields`. The **fail-closed** half is accurate for fifteen of them (sixteen for A4) and **not** for fields 1, 13 and 14. The B6 report is **not edited**; it is a B6-time record and stands as written. This decision carries the corrected statement.

**Consequence, binding on gate item (4):** `validate_configuration()` passing is **not** methodological completeness and **not** authorization. The authorization DEC must check DEC-030 §12 fields **1, 13 and 14** by hand; the configuration layer will not stop it.

## 7 — Scope-creep audit: nothing implemented exceeds what DEC-030 froze

**7.1 Exactly one governed source file changed.** `src/sparkrl/rl/reward.py` (now `e98a1351…fd95`; DEC-030's recorded pre-B6 fingerprint `0c5e67f4…9798` remains a correct historical record of the earlier state). DEC-030 §13 anticipated precisely this: *"Current `sparkrl.rl.reward` implements exactly one frozen formula (R3) and refuses any other — an additive, default-preserving extension would be required."* Every other DEC-030-fingerprinted file is byte-identical to its recorded value: `action.py` `580cf010…c0528`, `q0.py` `7d2ffb0c…de195`, `q_learning.py` `1c5fab89…bb31`, `loop.py` `b513238d…83611`, `ablation.py` `69ab9c40…b5216a`. `docs/PLAN.md` `db5e8210…ee63`, `configs/rl.yaml` `8ca70d6d…8b80`, `configs/reward.yaml` `a52131d5…db1b` — all unchanged.

**7.2 No runner exists, by design.** `loop.py` is untouched; B6 report §7 states why: *"Doing so would require choosing a seed set, a cell set, a horizon and an early-stop rule — every one of which DEC-030 §12 leaves unresolved — so any wiring would have had to invent methodology."* `tests/unit/test_exp008_scope.py:393` (`test_module_never_imports_spark_or_a_runner`) passes; the module's imports are `yaml`, `sparkrl.agent.q0`, `sparkrl.experiments.spec`, `sparkrl.rl.action`, `sparkrl.rl.reward` — no `pyspark`, no `sparkrl.rl.env`, no `subprocess`.

**7.3 Two surfaces recorded, neither a creep, both disclosed.**

* `arm_runtime_kwargs()` (`exp008.py:645-667`) returns a live `RewardCalculator` and component kwargs for a validated configuration. It is the closest thing in the change to executable machinery. It builds nothing, launches nothing and grants nothing; it is recorded so the authorization gate knows what surface it is fingerprinting.
* `arm_scope_summary()` (`exp008.py:776`) emits `"executable": arm != ARM_A3_R4_LOG_RATIO`, i.e. `true` for three arms. In that dict the word means **"this arm's reward formula can be constructed"**, nothing more; the same dict carries `execution_authorized: False`, `spark_executions: 0`, `training_executions: 0`, `test_executions: 0` (`exp008.py:787-790`). **No consumer may read that key as an authorization signal.**

**7.4 A narrowing relative to PLAN, stated so it is never mistaken for a de-scoping.** `docs/PLAN.md:315` registers EXP-008 with split *"Train/Test"* and arms *"A3, A4, A5"*. The implementation is TRAIN-only by hard guard and contains no A5. **This decision does NOT amend PLAN and does NOT de-scope EXP-008.** `docs/PLAN.md` is unchanged. The TRAIN-only guard binds the A3/A4 implementation layer only; any TEST component of EXP-008 would require its own decision and its own treatment of the TEST seal (PLAN §18: *"no test metric influences training or tuning"*; DEC-018 Decision B). Refusing TEST is the conservative direction and is left in place.

## 8 — A5 is genuinely inert

Four independent facts, each checked: (a) `A5` is absent from `ALL_ARMS` (`exp008.py:92-94`); (b) `guard_a5` (`exp008.py:186-204`) raises `A5DisabledError` for the `A5` arm, for `multi_step=True`, and for any `gamma != 0.0`; (c) `configs/exp008.yaml:26-27` states *"A5 is DISABLED … and is not representable here at all"*, and `load_exp008_config` refuses unknown arms (`exp008.py:181-184`); (d) `configs/rl.yaml:8` still reads `gamma: 0.0` and the file is byte-identical at `8ca70d6d…8b80`. Three tests assert it: `test_a5_arm_is_refused`, `test_multi_step_and_non_zero_gamma_are_refused`, `test_a5_is_absent_from_the_scope_summary_arms`. **A5 remains DISABLED** (DEC-011; re-affirmed DEC-016 §7, DEC-023 §2, DEC-024 A5 row, DEC-025 §7, DEC-030 §9). Nothing here opens multi-step RL.

## 9 — The B6 report's one owed item is DISCHARGED (§8 / §10 row 5)

The B6 report classified the stale SC6 pin in `tests/unit/test_exp001_maintenance.py::test_exp003_or_exp005_are_never_charged_to_sc6` as owed work needing a decision: *"Re-pinning a governance ledger constant to `462`/`38` is a DEC-031 follow-up, not an implementation-only change"* (§8), repeated as §10 row 5. Two later decisions discharged it, in sequence:

1. **DEC-032 §8** adopted the `336/164 → 462/38` re-pin as operator-authorized Day-37 work, *"on the same reasoning as §3 (the assertion re-derives from the live tree; it does not cite a historical figure) and subject to the same invariant as §6 (the pin was not weakened — it remains an exact equality)"*, and named the B6 report as the reason for recording it: *"the B6 implementation report (§8, §10 row 5) had classified that repair as 'a DEC-031 follow-up' … **DEC-032 is that decision.**"*
2. **DEC-033** then charged the six completed 2026-09-19 smoke TRAIN executions under DEC-031 §5 categories 1 and 3, moving the canonical ledger to `232 + 84 + 20 + 126 + 6 = 468`, remaining `500 − 468 = 32`, with follow-up (ii) *"correcting the test pin from 462/38 to 468/32, keeping it an exact equality so an unauthorized execution still breaks it."*

The pin now reads `tests/unit/test_exp001_maintenance.py:161` — `assert live == 468 and CAP - live == 32` — an exact equality, unweakened, with the hermetic fixture-tree assertions correctly left at 336. **B6 §10 row 5 is closed. DEC-035 re-opens nothing and re-decides nothing about the ledger.**

## 10 — CITED versus RE-DERIVED: the B6 artifacts are frozen as evidence

Applying the DEC-032 §3 discriminator: `docs/research/DAY37_EXP008_B6_IMPLEMENTATION_REPORT.md` and `results/evaluation/exp008_b6_implementation.json` **CITE** figures as of 2026-09-18 — `cumulative_charge: 462`, `remaining_headroom: 38`, `decisions_md_fingerprint: 7579e551…`, and a `pre_existing_failures` entry for the ledger test that has since been repaired. They do not re-derive anything from the live tree.

**They are therefore CITED historical records and are NOT edited, NOT regenerated and NOT corrected.** This restates DEC-032 §8's ruling verbatim in effect: *"The B6 report and `results/evaluation/exp008_b6_implementation.json` are **not** regenerated: they are correct as B6-time records and their historical status is preserved."*

**The current canonical ledger is DEC-033's: charged 468 of 500, remaining 32.** No reader may take the B6 JSON's `462/38` as current headroom. This entry changes no ledger figure and charges 0.

## 11 — WHAT IS DECIDED

1. **B6 is RESOLVED.** The EXP-008 A3/A4 implementation at HEAD `c2e980a` — `src/sparkrl/training/exp008.py`, the additive `src/sparkrl/rl/reward.py` extension, `configs/exp008.yaml`, the two `__init__` re-export blocks, and the three zero-Spark test files — is **ADOPTED** as the implementation DEC-030 §15 gate item (3) requires. DEC-030 §15's *"with green zero-Spark tests"* condition is **satisfied**: 103/103 passed, exit 0, 0.24 s, re-run for this entry (§4).
2. **Adoption is retrospective**, following DEC-018 Decision E and DEC-032 §8: the code was written and committed before any decision covered it. It is adopted as operator-authorized Day-37 work, on the evidence of §§3–8, not ratified blindly.
3. **DEC-030 §12 fields 1, 13 and 14 are explicitly DEFERRED** to the methodology/authorization decisions and are recorded as **NOT** enforced by the configuration layer (§6). Fields 2–12 and 15–17 are enforced fail-closed per arm.
4. **`validate_configuration()` passing is not authorization and not methodological completeness.** Recorded as binding on gate item (4).
5. **The DEC-030 §3.2 multi-term-removal classification stands** and is restated: A3-time-only removes the task-imbalance AND spill-waste terms simultaneously; no analysis may attribute a difference to a single removed term.
6. **B6 report §10 row 5 is discharged** by DEC-032 §8 as amended by DEC-033 (§9).
7. **The B6 report and JSON are frozen as CITED evidence** and are not regenerated (§10).

## 12 — Authorized but NOT performed here (following DEC-025 §11 / DEC-032 §6)

A **validator-only, minimal, local** repair is AUTHORIZED for a **separate later task**: `scripts/validate_day31.py:1015` currently reads `"exp008_b6_implementation.json": "DEC-031",` inside `AUTHORIZED_ARTIFACTS`, while DEC-031 §13 states *"It is **not** the B6 implementation decision."* Once DEC-035 is at HEAD, the correct attribution for that artifact is **DEC-035**.

**The repair MUST:** change only the attribution string for that one artifact key; leave `exp008_methodology_freeze.json` → `DEC-030`, `exp008_preflight_audit.json` → `DEC-030` and `exp008_budget_reconciliation.json` → `DEC-031` untouched; and preserve `_authorized()`'s requirement that the named decision be present at HEAD.

**The repair MUST NOT:** weaken, delete, skip or bypass any check; add any artifact to the allowlist; change any ledger, manifest, result or budget artifact; or alter authorization state. **It is NOT performed by this entry**, and this entry does not modify `scripts/validate_day31.py`.

## 13 — What this decision deliberately does NOT decide

* **EXP-008 execution authorization** — gate item (4). Not granted, not prepared, not implied.
* **DEC-030 §12 fields 1–14 and 16–17** — every one remains UNFROZEN and REQUIRES A SEPARATE DECISION. Naming fields 1, 13 and 14 in §6 **resolves none of them**; it records that the code will not catch them.
* **Field 15 / the A3-R4-log-ratio arm** — its eight unresolved semantics are not frozen here. The arm can never become configuration-complete as the code stands; either a decision freezes all eight, or field 1 drops it from the executed arm set. DEC-035 does neither.
* **The PLAN-internal scope/envelope tension.** `docs/PLAN.md:315` registers EXP-008 at **~300** executions; the canonical remaining headroom is **32** (DEC-033). DEC-031 §10 recorded this as an unresolved governance dependency and DEC-011 held it to be an internal-PLAN conflict DEC-010's precedence rule cannot arbitrate. **DEC-035 does not resolve it, does not raise the cap, does not amend PLAN and does not de-scope EXP-008.** No amount of implementation creates executions that do not exist.
* **Statistical governance** (§12 field 14) — DEC-030 §8's position stands: until a governing DEC exists, any EXP-008 analysis that ever runs is descriptive-only with no invented thresholds.
* **The zero-live manifest counting rule** (DEC-032 §7.3) — still UNRESOLVED; untouched here.
* **`scripts/validate_day30.py`** and every other validator beyond the one attribution line in §12.
* **DEC-034**, whatever it may be. Not read, not assumed, not depended on.

## 14 — Non-authorization firewall (explicit)

| Item | State recorded by this entry |
|---|---|
| **EXP-008 execution authorization** | **FALSE / NO** |
| **A5** | **DISABLED / excluded** (DEC-011; re-affirmed DEC-016 §7, DEC-023 §2, DEC-024 A5 row, DEC-025 §7, DEC-030 §9); `configs/rl.yaml` `gamma` stays `0.0` |
| **TEST** | **NOT AUTHORIZED** — no TEST queue, specification or ledger is created; the TRAIN-only guards are strengthened by adoption, never relaxed |
| **Implementation authorization (B6)** | **GRANTED by this entry, for implementation only** — A3/A4 are IMPLEMENTED-AND-ADOPTED, and remain **UNAUTHORIZED IN EXECUTION** |
| **SC6 cap** | **500 — unchanged, not raised** (`docs/PLAN.md:45`; `configs/rl.yaml:17`) |
| **Canonical ledger** | **468 charged / 32 remaining** (DEC-033) — restated, not re-derived, not changed |
| **`docs/PLAN.md`** | **UNCHANGED** — no line edited |
| **Historical decisions** | **UNCHANGED** — DEC-001 … DEC-026, DEC-030, DEC-031, DEC-032, DEC-033 are not rewritten; this entry is appended, never substituted |
| **Spark / training / TEST executions performed by this entry** | **0 / 0 / 0** |

## 15 — Evidence and fingerprints (read-only; nothing listed was modified by this entry)

| Source | Role | SHA256 |
|---|---|---|
| `src/sparkrl/training/exp008.py` | the adopted scope layer (36 504 bytes) | `0a2252b378dda0a630106795ef13287eda86d3a50c0e294ef26f3768bc54ceba` |
| `configs/exp008.yaml` | the inert fail-closed configuration artifact | `7b0f3999c08398df2cb956dceed312b32706fc3dca1f33815663bbedbb4cd2d4` |
| `src/sparkrl/rl/reward.py` | the one changed governed source; additive A3 registry | `e98a1351c42fc2303a4590afc62ed7d485754c43176b8f1b86b57fd77b67fd95` |
| `tests/unit/test_exp008_scope.py` | 50 zero-Spark tests | `815192962246cbfbb3bd8a1e9676fb09193e2c5419f137701bf7e6b703167d8c` |
| `tests/unit/test_exp008_action.py` | 32 zero-Spark tests | `e781ca7d10c92121c081f078ca90a81b8150d52c683b05641c71485178535443` |
| `tests/unit/test_exp008_reward.py` | 21 zero-Spark tests | `20c2d45f5144fe709808bde2e626b9d217110975f83faa5662eb575f13e75a35` |
| `docs/research/DAY37_EXP008_B6_IMPLEMENTATION_REPORT.md` | adopted evidence — **retained, not regenerated** | `65cbe165fd05e1475f3d66bdd3d9ea971b6366bf85c644a4510c4277e87f0541` |
| `results/evaluation/exp008_b6_implementation.json` | adopted evidence — **retained byte-identical** | `b6cf45148fcb8d45902b9b81fef86efe5a484886e5dab3cc13cbe7c4f93871b2` |
| `src/sparkrl/rl/action.py` | reused verbatim | `580cf010f17b2cb0f7c3b7967d4fb560b7f973028e8a1909123e7d337f4c0528` (**unchanged**) |
| `src/sparkrl/agent/q0.py` | no Q0 builder added | `7d2ffb0c33fc4349a71d3e064781927425092ff86be2eeed595705b3111de195` (**unchanged**) |
| `src/sparkrl/agent/q_learning.py` | 12-wide rows unchanged | `1c5fab897f8f652b90cd9011b1d84846459f041d31565c9652c4edd578d9bb31` (**unchanged**) |
| `src/sparkrl/training/loop.py` | **no EXP-008 wiring** | `b513238d5148a16cc8e39283526082b0c199fee5ad7a00326d95f4ad3983a611` (**unchanged**) |
| `src/sparkrl/training/ablation.py` | EXP-007 layer, pattern reused only | `69ab9c40e1688405b8b6f795783ada7fbf26c753bacb76d0aba215b7fb5b216a` (**unchanged**) |
| `docs/PLAN.md` | SC6 line 45; EXP-008 envelope line 315 | `db5e82102833efe6bab8db1adaf1b35ad195faf385e63ab296d50562e349ee63` (**unchanged**) |
| `configs/rl.yaml` | `gamma: 0.0`; `live_execution_cap: 500` | `8ca70d6dd7df68841c409a4441dc538616206bccea7877b28c73df20e6428b80` (**unchanged**) |
| `configs/reward.yaml` | frozen R3 weights | `a52131d5a0de63ef06d3dd5b181f1bbeda326df3ffffbd2ae1c69ed96571db1b` (**unchanged**) |
| `docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md` | DEC-030 identity preserved | `ec487bf2a84a9c1a6f506bdd83c71b7c7bb7ae2cceaf7e761f000c7201912a5a` (**unchanged**) |
| `docs/research/DEC_031_EXP008_SC6_BUDGET_RECONCILIATION.md` | DEC-031 | `af5c18216c6fdbcba86c891934a4b2d1026a32c4e2ada91eee91f7c8ab12852c` (**unchanged**) |
| `docs/research/DEC_032_DAY31_VALIDATOR_LEDGER_RECONCILIATION.md` | DEC-032 | `142bcd86b54ad7c369e8f10c7914c07372e63b93520e8e2780e2a68c25ad506d` (**unchanged**) |
| `docs/research/DEC_033_GOVERNANCE_RECONCILIATION.md` | DEC-033 — canonical 468/32 | `3e6d0d7c4b5359990ea6ac6766e226d860c5fea2fb0e8639cc73fff645932b21` (**unchanged**) |
| `scripts/validate_day31.py` | the §12 attribution line — **NOT MODIFIED by this entry** | out of scope; repair authorized for a later task |
| `DECISIONS.md` | this entry appended; every prior byte intact | `849197ed5b9d2ca192db68e14bef80916d2ef55af48b5105a3f39301e919953e` **before** this append |

Repository state at recording: branch `main`, HEAD `c2e980a` (*"gov(DEC-033): Option A — the six 2026-09-19 smoke executions are charged; ledger 468/32"*), working tree **clean** (`git status --porcelain` empty).

## 16 — Validation of this entry (read-only, zero Spark)

| Check | Method | Result |
|---|---|---|
| DEC-035 identifier free | heading scan of `DECISIONS.md` + repository-wide search for `DEC-034`/`DEC-035` | PASS (both unoccupied) |
| `DECISIONS.md` appended only | prior bytes intact; append-only | PASS |
| DEC-030 / DEC-031 / DEC-032 / DEC-033 artifacts unchanged | SHA256 re-checked (§15) | PASS |
| `docs/PLAN.md`, `configs/rl.yaml`, `configs/reward.yaml` unchanged | SHA256 re-checked | PASS |
| Zero-Spark EXP-008 tests green | `python -m pytest tests/unit/test_exp008_{scope,action,reward}.py` | **PASS — 103 passed, 0.24 s, exit 0** |
| Only `reward.py` changed among DEC-030-fingerprinted sources | SHA256 of action/q0/q_learning/loop/ablation vs recorded values | PASS |
| No EXP-008 runner exists | `loop.py` byte-identical; module imports no `pyspark`/`env`/`subprocess` | PASS |
| §12 field coverage measured, not assumed | read-only construction of a 15-field-complete config; `unresolved_fields()` → `()` with `statistical_governance=None` | PASS (15/18; 16/18 for A4) |
| A5 inert | four independent refusals + unchanged `gamma: 0.0` | PASS |
| No execution authorized | §13, §14 | PASS |
| Ledger unchanged | 468/32 restated from DEC-033; charged by this entry: **0** | PASS |
| Full unit suite / validator chain | **NOT RE-RUN by this entry** — deferred to gate item (4)'s clean preflight | NOT ASSERTED |
| Spark / training / TEST executions performed | — | **0 / 0 / 0** |

**Status.** **DECIDED.** DEC-030 §15 gate-chain item **(3) is SATISFIED**: the EXP-008 A3/A4 implementation is **ADOPTED** as the B6 resolution on green zero-Spark tests (**103/103, exit 0**), with DEC-030 §12 fields **1, 13 and 14** recorded as **NOT** fail-closed in the configuration layer and **explicitly deferred**, and with fifteen fields (sixteen for A4) enforced required-but-unset. One validator-only attribution repair is **AUTHORIZED for a separate later task and NOT performed here**. `EXP-008 execution authorization = NO`. `A5 = DISABLED`. `TEST = NOT AUTHORIZED`. `SC6 cap = 500, not raised`. `Canonical ledger = 468 charged / 32 remaining (DEC-033)`. `docs/PLAN.md = UNCHANGED`. Historical decisions (DEC-001 … DEC-026, DEC-030, DEC-031, DEC-032, DEC-033) = **UNCHANGED**. Supervisor counter-signature: **PENDING** (conventional expectation only; never simulated; not a prerequisite under DEC-018 Decision A). **NO SUPERVISOR HAS REVIEWED THIS ENTRY.** **This entry performs 0 Spark executions and trains nothing.**

*End of DEC-035.*

---

**Ledger supersession note (appended 2026-09-20, before signature).** This entry was drafted against the then-current ledger **468 / 32** (DEC-033). Five completed smoke TRAIN executions dated 2026-09-20 07:37-07:56Z were discovered afterwards and classified by **DEC-038**, making the canonical ledger **483 / 17** at signature. The figure is corrected here rather than in the body, so the drafting chronology stays visible. No conclusion in this entry depends on the difference: it adopts an implementation and charges nothing; EXP-008 execution authorization remains NO either way.

## DEC-036 | 2026-09-20 | EXP-008 A3/A4 methodological field resolution - all eighteen DEC-030 s12 fields; A3-R4 DROPPED as unspecifiable; execution authorization remains NO (Day 38, C3)

**Decision ID:** DEC-036
**Date:** 2026-09-20
**Scope:** The eighteen methodological fields that `docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md` §12 marks *"UNFROZEN — SEPARATE DECISION REQUIRED"*. **Nothing else.**
**Status:** DECIDED — sixteen fields resolved unconditionally; the two count-driving fields (6 seeds, 8 horizon) resolved as a frozen RULE plus three fully specified branches, one of which a separate decision selects. **`EXP-008 execution authorization = NO`.**
**Standalone decision artifact.** The authoritative log entry is the appended DEC-036 section of `DECISIONS.md`; this document carries the same decision content, self-contained, so the decision also exists as an addressable artifact (the DEC-031/DEC-032 convention).
**Supersedes nothing.** DEC-030, DEC-031, DEC-032 and DEC-033 are unchanged; no historical decision entry is rewritten. `docs/PLAN.md` is **UNCHANGED**.

> **This entry performs 0 Spark executions, trains nothing, executes no TEST, creates no run directory, and modifies no manifest, no result artifact, no configuration, no implementation file and no prior decision entry.**
> **EXP-008 execution authorization remains NO. A5 remains DISABLED. TEST remains NOT AUTHORIZED.**

---

## 0 — Identifier resolution and batch context

`DECISIONS.md` headings run DEC-001…DEC-026, DEC-031, DEC-032. DEC-030 is formally recorded outside `DECISIONS.md` (`docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md`, `Decision ID: DEC-030`). **DEC-033 is likewise recorded as a standalone artifact only** (`docs/research/DEC_033_GOVERNANCE_RECONCILIATION.md`, *"STATUS: DECIDED — Option A selected by the operator"*) and has **no section in `DECISIONS.md`** — recorded here as an observation, **not corrected by this entry**. DEC-034 and DEC-035 are the identifiers assigned to the sibling budget and B6 entries of the same Day-38 governance batch; **DEC-036 claims neither of them, cites neither as signed, and takes no effect on either.**

## 1 — Scope

DEC-030 §15: *"Any methodological field marked 'UNFROZEN — SEPARATE DECISION REQUIRED' must be resolved by such a DEC before authorization."* This entry is that DEC for all eighteen §12 fields. It resolves methodology only. It is **not** the B6 implementation decision, **not** a budget decision and **not** an authorization decision.

## 2 — Method, and the rule this entry obeys

Each field is placed in exactly one class:

* **INHERIT** — the project already holds a frozen value that applies unchanged. The frozen value and its authority (file:line, decision id) are given. **Inheriting is not inventing**; a field is only inherited where the value demonstrably already exists.
* **CHOOSE** — a real choice with no frozen default. Options and reasoning are given.
* **ALREADY RESOLVED** — by DEC-031/DEC-033 (field 17) or by the separate B6 decision (field 18).
* **DROP** — the element cannot be specified without invention, so it is removed from the executable set rather than guessed.

**No threshold, statistic, formula, weight or policy absent from the record is created by this entry.** Where a field could only be settled by invention, it is dropped and the cost is stated. CITED historical figures are not edited anywhere (the DEC-032 §3 discriminator); every figure below is either restated from a signed decision or re-derived from the live tree and labelled as such.

## 3 — Canonical figures restated (not re-derived, not changed)

| Quantity | Value | Authority |
|---|---|---|
| SC6 cap | **500**, **not raised** | `docs/PLAN.md` line 45; `configs/rl.yaml` line 17 |
| Cumulative charge | **468** | DEC-033 Option A: `232 + 84 + 20 + 126 + 6 = 468` |
| Remaining headroom | **32** | `500 − 468` (DEC-033) |
| PLAN EXP-008 envelope | **~300** | `docs/PLAN.md` line 315 — an internal-PLAN tension DEC-011 and DEC-031 §10 record and do **not** resolve |

**This entry adds no accounting and changes no figure.**

## 4 — The unit of account (evidence, not assumption)

Every execution count below rests on three facts already in the repository:

1. **One episode = one charged live execution.** `docs/architecture/ARCHITECTURE_FREEZE.md`: *"Episode: one cached-or-live execution + update"*; `src/sparkrl/rl/env.py:284` increments the counter once per step; `:300` *"bandit mode: episode terminates"*. EXP-007's four manifests read `35 / 35 / 35 / 21` live against 35 planned episodes per seed.
2. **One epoch = one full pass over the planned cells.** `configs/rl.yaml:27` `epoch_definition: "one_full_pass_over_the_planned_cell_cycle"`; `src/sparkrl/training/loop.py:232-233`, `episodes_per_epoch` is DERIVED `== len(cells)`.
3. **No cache exists.** `src/sparkrl/rl/env.py:29-30`: *"the cache itself is COMP-EXP-11 (deferred, Day 26+), so every … step is a live execution and `info[\"cached\"]` is always False."* The frozen *"cache hits free"* rule therefore has no live content and reduces no count.

Therefore **charged live TRAIN executions = arms × seeds × epochs × cells**, with `cells = 7` (§6, field 7).

## 5 — Resolution of all eighteen fields

| # | Field (DEC-030 §12) | Class | Resolution | Authority |
|---|---|---|---|---|
| 1 | Final arm set; whether A3-R4 is retained | **CHOOSE** | **Three executable arms: `A3-R3-frozen`, `A3-time-only`, `A4-mode4`. `A3-R4-log-ratio` is DROPPED from the executable arm set** and retained as REGISTERED-BUT-UNEXECUTABLE | §8 |
| 2 | Q0 source per arm | **CHOOSE** | **`q0-exp002/v1` for all three arms**, uniformly; A4 uses 12-wide rows with selection restricted to {0,3,6,9}, no projection | §7.2 |
| 3 | State schema per arm | **INHERIT** | **`state-v1.5`** (30 states) for all arms | `src/sparkrl/rl/state.py:73` `STATE_VERSION = "state-v1.5"`; every Day-29 manifest `contract_versions.state_schema = state-v1.5`; DEC-030 §6.1 primary row |
| 4 | Action schema for A3 | **INHERIT** | **`mode12`** (all 12 frozen actions) for both A3 arms | `src/sparkrl/rl/action.py:30`; `docs/architecture/ARCHITECTURE_FREEZE.md` COMP-RL-07; DEC-030 §4.1 |
| 5 | Reward arm for A4 control pairing | **CHOOSE** | **R3**, and A4-mode4's control **is** the `A3-R3-frozen` arm (same run set, same seeds, same cells, same horizon) | §7.3 |
| 6 | Seeds (count + identities) | **CHOOSE — conditional** | **Rule frozen:** seeds are an ascending **prefix of the frozen PLAN §16 set {0,1,2}**; no seed outside it, no re-ordering, no invented seed. **Value: branch-selected (§10).** | `configs/rl.yaml:16` `training_seeds: [0, 1, 2]`; DEC-023/DEC-025 used the prefix {0,1} |
| 7 | TRAIN cells | **INHERIT (forced)** | **The seven T_ref-calibrated TRAIN cells at dataset seed 0**: `F1_agg|small`, `F1_agg|medium`, `F2_join|small`, `F2_join|medium`, `F3_rdd|small`, `F5_mixed|small`, `F5_mixed|medium`; `F3_rdd|medium` excluded (`t_ref_null`). **No subset is admissible** (§7.5) | `src/sparkrl/training/loop.py:392-396`; DEC-025 §3; the same seven appear in `results/training/train-a0-d0-20260912T112906Z/episodes.jsonl` |
| 8 | Episode horizon | **CHOOSE — conditional** | **Rule frozen:** the horizon is an **integer number of complete 7-cell epochs**; a non-integer horizon is inadmissible because it truncates the round-robin cycle. **Value: branch-selected (§10).** | DEC-025 §4 (*"40 is rejected because 40 is not an integer number of complete 7-cell epochs"*) |
| 9 | Early-stop rule | **INHERIT** | **`stable_epochs_required = 2`; greedy snapshot identical at 3 consecutive epoch boundaries.** Inert below 3 epochs (§10 note) | `configs/rl.yaml:29`; `src/sparkrl/training/loop.py:60,100`; PLAN §16 |
| 10 | AQE condition | **INHERIT** | **`aqe_enabled = false`** for every arm; AQE-on is EXP-005b and is never pooled with this study | `configs/spark.yaml:14`; `src/sparkrl/rl/action.py:97-99` (post-application guard raises); `ARCHITECTURE_FREEZE` §13 |
| 11 | Warm-up behaviour | **INHERIT** | **`warmup_runs: 2`, `warmup_micro_job: true`, warm-up excluded from the timed region**; unchanged from the frozen runner | `configs/spark.yaml:19-20`; `src/sparkrl/experiments/runner.py:422-429` (a spec disagreeing with the base config is refused); `ARCHITECTURE_FREEZE` COMP-SPARK-04 |
| 12 | Cache behaviour | **INHERIT** | **No execution cache (COMP-EXP-11 deferred).** Every step is a live execution; `cached` is always False; the "cache hits free" rule is retained verbatim and reduces nothing | `src/sparkrl/rl/env.py:29-30,123,284`; DEC-025 §3 |
| 13 | Whether A3 and A4 share seeds/cells/horizon | **CHOOSE** | **YES — A3 and A4 share the seed set, the seven cells, the horizon, the early-stop rule and the R3 control arm.** The shared control is what makes A4's isolation claim exact | §7.3 |
| 14 | Statistical governance | **CHOOSE (forced by norm)** | **DESCRIPTIVE-ONLY. No p-value threshold, no effect-size cutoff, no Holm family, no minimum-n, no superiority threshold, no inferential test.** Any future formal testing requires a separate pre-use methodology amendment | §9; DEC-020 A and F; DEC-026 §13; DEC-030 §8 |
| 15 | R4 complete specification | **DROP** | **Not specifiable without invention → A3-R4 is dropped from the executable arm set** (see field 1). R4 stays REGISTERED in PLAN §24 and refused pre-computation in code | §8 |
| 16 | Epsilon / alpha / gamma | **INHERIT** | **alpha = 0.2; gamma = 0.0; epsilon 1.0 → 0.05, decay 0.95 per episode. NO deviation for any arm.** gamma is additionally locked | `configs/rl.yaml:7-11`; PLAN §16; DEC-011; DEC-030 §9; `src/sparkrl/training/exp008.py` `guard_a5` refuses any gamma ≠ 0.0 |
| 17 | Live-execution charging rule and headroom (B5) | **ALREADY RESOLVED** | By **DEC-031 §5** (charging categories) and **§8** (headroom), re-based by **DEC-033** to **468 charged / 32 remaining** of the unchanged cap 500 | DEC-031; DEC-033 |
| 18 | Implementation authorization (B6) | **ALREADY RESOLVED — by the separate B6 decision, when signed** | **Not resolved as of this entry's date.** The evidence exists (`docs/research/DAY37_EXP008_B6_IMPLEMENTATION_REPORT.md`; `results/evaluation/exp008_b6_implementation.json`) and states of itself *"This report is **not a decision**"*. **DEC-036 grants no implementation authorization** | DEC-030 §15 gate item (3) |

## 6 — The INHERIT fields: proof that each frozen value exists and applies

Each value below is already in force for the main study and for EXP-007; EXP-008 A3/A4 adopt it **unchanged**, so no control differs between the treatment arms and the frozen design except the factor each arm is testing.

* **state-v1.5 / mode12 (fields 3, 4).** Both are the primary-study values (`state.py:73`; `action.py:30`) and are recorded in every Day-28/29 manifest (`contract_versions.state_schema = state-v1.5`, `contract_versions.action_mode = mode12`). Pinning A3 to mode12 is load-bearing: if A3 varied the action space, A3 and A4 would confound each other, contrary to DEC-030 §6.
* **The seven cells (field 7).** `loop.py:392-396` refuses any TRAIN cell without a calibrated T_ref at dataset seed 0 and names `F3_rdd|medium` as the null one; `env.step` would raise `TRefMissing`. The set is therefore forced by calibration, not chosen for convenience.
* **Early-stop (field 9).** `configs/rl.yaml:29` is frozen-validated `== 2` by `loop.py:164-167`; the rule text is `loop.py:100`.
* **AQE off (field 10).** `configs/spark.yaml:14`; `action.py:97-99` raises `"AQE became enabled after action application (PLAN section 7)"` — the control is enforced in code, not merely declared.
* **Warm-up (field 11).** `configs/spark.yaml:19-20`; `runner.py:422-429` refuses to run a design whose declared warm-up policy differs from the executed one. SC6 charges **env-level live executions**, exactly as every one of the 468 already-charged executions was counted; this entry changes no charging rule.
* **Cache (field 12).** `env.py:29-30`. Recorded so that no future reader mistakes the inherited *"cache hits free"* clause for a budget reduction.
* **alpha / gamma / epsilon (field 16).** `configs/rl.yaml:7-11`, matching PLAN §16 verbatim. gamma = 0.0 is the A5 lock and is re-affirmed, not re-decided.

## 7 — The CHOOSE fields

**7.1 — Field 1, the arm set.** Three executable arms: `A3-R3-frozen` (R3, mode12), `A3-time-only` (the DEC-030 §3.2 multi-term removal, mode12), `A4-mode4` (R3, mode4 = {0,3,6,9}). `A3-R4-log-ratio` is dropped (§8). DEC-030 §3.2's mandatory classification is carried forward verbatim: **time-only is a MULTI-TERM REMOVAL from R3, not a one-factor ablation** — the task-imbalance and spill-waste terms are removed simultaneously, so no observed difference is attributable to either term alone. This statement must appear in any analysis of that arm.

**7.2 — Field 2, Q0 source: `q0-exp002/v1` for every arm.**

* It exists at the right shape: `src/sparkrl/agent/q0.py:64-78` builds it with a `state-v1.5` encoder and 12-wide rows; `configs/rl.yaml:13` `q0_source: "exp002"`.
* It is admissible for every retained arm under the already-implemented policy (`src/sparkrl/training/exp008.py` `q0_policy`, `allowed_sources = (q0-exp002/v1, q0-neutral/v1)`).
* For A4 it is DEC-030 §5.4's **"EXISTING FROZEN MAPPING"**: rows stay 12 wide, columns {0,3,6,9} are used as-is, **no projection, no pooling, no construction**.
* **One source across all arms holds Q0 constant**, which removes DEC-030 §6.1 confound 2 (*"differing Q0 sources across arms would confound reward effects with initialization"*) by construction.

Rejected alternatives, with reasons: **`q0-neutral/v1`** — `build_neutral_q0` accepts only `"A1"` or `"A2"` (`q0.py:239-250`), so no neutral table exists for `state-v1.5`; creating one is new implementation work outside the B6 scope, which recorded *"No new Q0 builder may be added (DEC-030 §5); B6 added none."* The EXP-007 neutral-Q0 precedent does **not** transfer: `q0.py:190-196` records that A1/A2 went neutral because the EXP-002 table could not be mapped onto their 15- and 2-state spaces — a dimensional problem that does not arise here. **Per-arm reward-matched Q0** (rebuilding from the same EXP-002 TRAIN records under each arm's own reward) — refused: it is post-hoc Q0 construction (DEC-030 §5.1 rule 2), and it would make Q0 differ across arms, reinstating exactly the confound the uniform choice removes.

> **Limitation, recorded and binding on any future analysis.** `q0-exp002/v1` was derived from EXP-002 TRAIN records scored under the frozen **R3** reward. For `A3-time-only` this is initialization computed under a different reward from the one the arm optimizes — DEC-030 §5.3 calls that *"methodologically defensible IF frozen"*. This entry freezes it and requires the limitation to be disclosed wherever that arm is reported.

**7.3 — Fields 5 and 13, the A4 control and sharing.** A4-mode4's control reward is **R3**, and its control arm **is** `A3-R3-frozen`. A3 and A4 share the seed set, the seven cells, the horizon and the early-stop rule. This makes DEC-030 §6.2's requirement — *"All other factors must equal the control arm"* — exactly true rather than approximately true, and it removes one arm's worth of executions from every branch in §10. DEC-030 §6.2 confound 3 is carried forward unrepaired and **must be reported, not corrected**: ε-greedy over 4 actions versus 12 yields different exploration coverage under the same schedule; that is inherent to the factor.

**7.4 — Field 14.** See §9.

**7.5 — Why no cell subset is admissible.** A smaller cell set would cut every count proportionally, and is refused: no artifact, decision or criterion selects a subset of the seven, so choosing one would be an invented selection rule; and a subset would break comparability with the main study, with EXP-007 and with the R3 control. The cell count stays 7.

## 8 — Field 15: A3-R4 is DROPPED from the executable arm set

**What the record supplies for R4:** the name and the formula, and nothing else — `docs/PLAN.md` §24 (*"R4 log-ratio"*) and `docs/architecture/ARCHITECTURE_FREEZE.md` (*"R4 = −ln(T/T_ref) ablation-only"*).

**What the record does not supply** — the eight semantics enumerated by DEC-030 §3.4 and pinned in code at `src/sparkrl/rl/reward.py:111-120`: `failure_rule`, `coefficients`, `clipping`, `edge_T_le_0`, `edge_T_ref_le_0`, `edge_failures_timeouts`, `edge_missing_execution_time`, `term_structure_vs_time_only`. `configs/reward.yaml` holds R3 weights only. No DEC supplies any of them.

**Why none can be derived.** The failure rule is the clearest case: R3's `−1.0` failure constant is commensurate with a reward clipped to `[−1, +1]`, whereas `−ln(T/T_ref)` is unbounded in both directions. Carrying `−1.0` across is a **scale decision with no authority behind it**, not a derivation. The same applies to clipping (R4 has none), to `T ≤ 0` (undefined), and to whether R4 is a functional-form change of the time term or also a multi-term removal — DEC-030 §3.4 lists that last question as unresolved, and it changes what the arm even measures.

**Decision.** `A3-R4-log-ratio` is **DROPPED from the EXP-008 executable arm set**. It remains **REGISTERED** — `docs/PLAN.md` §24 is **not amended**, the enum stays in `src/sparkrl/rl/reward.py:85`, and the code keeps failing closed before any computation (`reward.py:197-206`, `IncompleteFormulaError`). A later decision may freeze all eight semantics from a real authority and reinstate the arm; this entry does not.

> **This weakens the scientific claim, and the entry says so in those words.** A3 as executed becomes a **two-way** reward comparison (time-only vs frozen R3), not the **three-way** comparison PLAN §24 registers. RQ4's reward-design question is answered for coefficient/term removal only, and **not at all for functional form**. Any A3 report must state that the R4 log-ratio variant was never executed and why. **No success criterion is amended by this**: PLAN line 45 (SC6) and PLAN line 315 stand verbatim, and SC1–SC8 are untouched.

## 9 — Field 14: statistical governance — DESCRIPTIVE-ONLY

**Frozen:** EXP-008 A3/A4 analysis is **descriptive**. Per-arm and per-cell medians and the registered ablation table; coverage and failures reported as first-class; no inferential test and **no threshold of any kind**.

**Explicitly NOT created by this entry:** p-value threshold, alpha, effect-size cutoff, Cliff's δ decision rule, Holm family definition, multiple-testing scope, minimum successful cells, superiority threshold, hypothesis-to-comparison mapping.

**Authority for following this rather than inventing a procedure.** DEC-020 A closed EXP-005 with *"H2, H3, SC2, SC3, SC4 are **UNDECIDED** — not failed. No Wilcoxon, no Cliff's δ decision, no Holm decision, no alpha, no minimum-n, no effect threshold … No generic defaults are retrofitted."* DEC-020 F: *"Any future formal testing needs a separate pre-use methodology amendment."* DEC-026 §13 applied the same rule to the most recent ablation: *"No numerical pass/fail threshold and no inferential statistic is introduced."* DEC-030 §8 records that the Day-37 audit's proposed Wilcoxon/Holm procedure is *"EVIDENCE, not authority; it is not adopted here."* This entry adopts none of it either.

**Consequence, stated plainly.** RQ4 receives a **descriptive** answer, not a tested one. That matches what `docs/PLAN.md` line 315 registers as EXP-008's deliverable (*"ablation table"*), so no registered deliverable is lost; but no claim of statistical significance may ever be attached to EXP-008 A3/A4 under this entry.

## 10 — Fields 6 and 8: the count-driving fields, the arithmetic, and the conditional freeze

**Frozen unconditionally (the rule):** horizon = an integer number of complete 7-cell epochs (DEC-025 §4); seeds = an ascending prefix of the frozen `{0, 1, 2}` (`configs/rl.yaml:16`); the same seeds and horizon for every arm (field 13).

**The arithmetic** (`arms × seeds × epochs × 7`, per §4; worst case = planned, since early stop can only reduce):

| Shape (per arm) | 2 arms | 3 arms | 4 arms | Fits inside 32? |
|---|---|---|---|---|
| 1 seed × 1 epoch = **7** | 14 | **21** | 28 | **yes** (all three) |
| 1 seed × 2 epochs = **14** | **28** | 42 | 56 | only 2 arms |
| 2 seeds × 1 epoch = **14** | **28** | 42 | 56 | only 2 arms |
| 1 seed × 3 epochs = **21** | 42 | 63 | 84 | no |
| 2 seeds × 2 epochs = **28** | 56 | 84 | 112 | no |
| 1 seed × 5 epochs = **35** | 70 | 105 | 140 | no |
| **2 seeds × 5 epochs = 70** (EXP-007 parity, DEC-025 §5) | 140 | **210** | 280 | no |

**Two facts the operator should read off this table.** First, **the complete list of shapes that fit inside the 32 remaining executions is: 14, 21 and 28** — nothing else. Second, the EXP-007-parity shape for the three-arm set is **210**, and PLAN line 315's registered envelope is **~300**; neither is within a factor of six of what exists.

**Early-stop note.** The frozen rule needs three consecutive epoch boundaries (`loop.py:100`). At 1 or 2 epochs it **cannot fire**, so worst case equals actual. At 5 epochs it can (EXP-007's A2 seed 1 stopped at 21 of 35).

**The three branches. The authorization decision selects exactly one; DEC-036 selects none.**

* **Branch P — PARITY (210 worst case).** 3 arms × seeds {0,1} × 5 epochs × 7 cells. Requires a separate scope/cap governance action making ≥210 charged live TRAIN executions available, exactly as DEC-031 §11 requires. **This is the only branch DEC-036 endorses methodologically**: it is the EXP-007 shape, and it is the only branch in which each arm has a replicate and a learning phase.
* **Branch R — REUSE-PARITY (140 worst case).** 2 new arms (`A3-time-only`, `A4-mode4`) × seeds {0,1} × 5 epochs × 7 cells; the `A3-R3-frozen` control is **read from the already-charged 2026-09-12 training records, truncated episode-for-episode to 35 episodes**, at **0 additional charge**. Those records match on everything: `results/training/train-a0-d0-20260912T112906Z/manifest.json` and `train-a1-d0-20260912T115123Z/manifest.json` carry `reward_formula = R3`, `state_schema = state-v1.5`, `action_mode = mode12`, `q0_version = q0-exp002/v1`, `dataset_seed = 0`, `t_ref_gate_sha256 = e30a7b0c953d…`, the same seven cells in the same round-robin order and the same epsilon trajectory (`episodes.jsonl` episode 1 ε = 1.0, episode 8 ε = 0.6983). **Cost, which must be stated if this branch is taken:** the control was measured on 2026-09-12 under `code_version 8a9ca54-dirty`, the treatment arms would run later under the post-B6 tree, so every A3/A4 difference confounds the intended factor with cross-session timing drift against the 11.89% noise band DEC-018 F recorded. **Admissible; not recommended as the default.**
* **Branch M — MINIMUM (21 worst case), the only branch that fits today.** 3 arms × seed {0} × 1 epoch × 7 cells = 21, leaving 11. **ARITHMETICALLY ADMISSIBLE, METHODOLOGICALLY NOT RECOMMENDED.** With one seed and one epoch: each arm sees each cell exactly once; ε never falls below `0.95^7 = 0.6983` (`configs/rl.yaml:9-11`), so most actions are random; there is no replicate; and the early-stop rule cannot fire. **This weakens the scientific claim to the point of removing it**: the result would be a 21-execution random-policy probe, not an ablation of a trained policy, and it cannot support RQ4. It would also consume 21 of the 32 executions the project has left. (`docs/PLAN.md` lines 316-320 register EXP-009/010/011/012 with envelopes ~20/~25/~60/~10; **no decision states whether any of them charges SC6**, and this entry asserts nothing about them.)

**DEC-036 selects no branch.** Selection belongs to the authorization decision (DEC-030 §15 gate item 4), because it depends on capacity this entry has no power to create.

## 11 — What this decision deliberately does NOT decide

The branch selection (§10); the execution schedule; the authorization itself; any budget figure, charging rule or cap amendment; the amendment mechanism for the PLAN line 45 vs line 315 tension (DEC-031 §10, DEC-011); the B6 implementation authorization; R4's semantics (dropped, not specified); A5 in any form; TEST for anything; any statistical threshold; and the counting rule for zero-live manifests (DEC-032 §7.3, still open). It also does not decide whether Branch R's reuse is acceptable — it records the option and its confound.

## 12 — Gate-chain status after this entry

| Gate (DEC-030 §15) | State |
|---|---|
| (1) DEC-030 methodology freeze | **DONE** |
| (2) separate budget DEC resolving B5 | **DONE** — DEC-031, re-based by DEC-033 to 468/32 |
| (3) separate implementation DEC resolving B6 with green zero-Spark tests | **NOT DONE** — evidence exists; **DEC-036 does not supply it** |
| (4) separate authorization DEC with worst-case counts, ledger charge and a clean preflight re-run | **NOT DONE** — and blocked by capacity, not by methodology, once this entry is signed |
| §12's eighteen fields | **RESOLVED by this entry**, with fields 6 and 8 frozen as a rule plus three branches |

**Implementation consequence (NOT implemented here; DEC-025 §11 template).** The B6 report §7 refused to wire EXP-008 into `src/sparkrl/training/loop.py` because *"Doing so would require choosing a seed set, a cell set, a horizon and an early-stop rule — every one of which DEC-030 §12 leaves unresolved."* This entry removes that cause for the cell set, the early-stop rule and the horizon rule, and supplies the seed rule. A **separate later task** may therefore wire an EXP-008 runner **without inventing methodology** — under the B6 decision's authorization, not this one, and it must remain incapable of granting execution authorization.

## 13 — Non-authorization firewall (explicit)

| Item | State recorded by this entry |
|---|---|
| **EXP-008 execution authorization** | **FALSE / NO** |
| **Implementation authorization (A3/A4, B6)** | **FALSE / NO** — not granted here |
| **A5** | **DISABLED** (DEC-011; re-affirmed DEC-016 §7, DEC-023 §2, DEC-024, DEC-025 §7, DEC-030 §9); `configs/rl.yaml` `gamma` stays 0.0 |
| **TEST** | **NOT AUTHORIZED** — no TEST queue, specification or ledger is created |
| **SC6 cap** | **500 — not raised, not amended** |
| **Ledger** | **468 charged / 32 remaining — restated, not re-derived, not changed** |
| **`docs/PLAN.md`** | **UNCHANGED** — no line edited; R4 remains registered in §24 |
| **`configs/*.yaml`, `src/**`, `scripts/**`** | **UNCHANGED** — no file modified by this entry |
| **Historical decisions** | **UNCHANGED** — DEC-001 … DEC-026, DEC-030, DEC-031, DEC-032, DEC-033 are not rewritten; this entry is appended |
| **Spark / training / TEST executions performed by this entry** | **0 / 0 / 0** |

## 14 — Evidence (read-only; nothing listed was modified)

| Source | Role |
|---|---|
| `docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md` §12 (lines 337-354), §15 (line 372) | the eighteen fields and the gate chain |
| `docs/PLAN.md` line 45 (SC6), line 143 (§16 hyperparameters), line 188 (§24 ablations), line 315 (EXP-008 envelope) | registered intent; **unchanged** |
| `configs/rl.yaml` lines 7-11, 13, 16, 17, 27, 29 | alpha/gamma/epsilon, q0 source, seeds, cap, epoch definition, early stop |
| `configs/reward.yaml`, `configs/spark.yaml` lines 14, 19-20 | R3 weights; AQE off; warm-up policy |
| `src/sparkrl/rl/state.py:73`; `action.py:30,35,97-99`; `env.py:29-30,284,300`; `reward.py:85,111-120,197-206` | state schema, action grid, AQE guard, cache/step/budget semantics, R4 refusal |
| `src/sparkrl/agent/q0.py:47,64-78,190-196,239-250` | `q0-exp002/v1`; why the neutral builder is A1/A2-only |
| `src/sparkrl/training/loop.py:60,100,232-233,392-396` | early stop, epoch/cell derivation, the seven-cell refusal |
| `src/sparkrl/training/exp008.py` | the B6 scope layer; required-but-unset fields; Q0 policy; A5 guard |
| `results/training/train-a0-d0-20260912T{083120,112906}Z`, `train-a1-d0-20260912T115123Z`, `train-a2-d0-20260912T120648Z` (manifests + `episodes.jsonl`) | the existing charged R3/mode12/state-v1.5/q0-exp002 runs cited by Branch R |
| `docs/research/DEC_031_…md`; `DEC_032_…md`; `DEC_033_GOVERNANCE_RECONCILIATION.md`; `DAY37_EXP008_B6_IMPLEMENTATION_REPORT.md` | budget, validator, ledger re-base, B6 evidence |
| `DECISIONS.md` DEC-011, DEC-018 A/F, DEC-020 A/F, DEC-023, DEC-025 §§1-6, DEC-026 §13 | gamma lock, operator gate, descriptive-closure norm, EXP-007 scope and arithmetic |

**Working-tree disclosure.** DEC-033 exists as a standalone artifact with no `DECISIONS.md` section (§0). Any future entry citing DEC-033's 468/32 cites an authority in that form. Disclosed, not hidden, matching DEC-031 §15 / DEC-032 §11.

## 15 — Validation of this entry (read-only, zero Spark)

| Check | Result |
|---|---|
| DEC-036 is the identifier assigned to this cluster; no DEC-036 exists elsewhere | PASS (§0) |
| All eighteen DEC-030 §12 fields appear exactly once in the §5 table | PASS |
| Every INHERIT field cites a frozen value with a file:line | PASS (§5, §6) |
| No threshold, statistic, weight, formula or policy invented | PASS (§2, §8, §9) |
| No CITED historical figure edited | PASS (DEC-032 §3 discriminator) |
| Canonical figures restated, none re-derived | PASS (500 / 468 / 32) |
| Execution arithmetic derived from cited mechanics | PASS (§4, §10) |
| No execution authorized; no branch selected | PASS (§10, §13) |
| `docs/PLAN.md`, `configs/**`, `src/**`, `scripts/**`, all manifests and results unmodified | PASS |
| EXP-008 = NO; A5 = DISABLED; TEST = NOT AUTHORIZED | PASS (§13) |
| Spark / training / TEST executions performed | **0 / 0 / 0** |

**Status.** **DECIDED.** All eighteen DEC-030 §12 fields are resolved: **eleven INHERIT** (state-v1.5; mode12; the seven T_ref-calibrated cells; early stop at 2 stable epochs; AQE off; warm-up 2 + micro-job; no cache; alpha 0.2; gamma 0.0; epsilon 1.0 → 0.05 @ 0.95 — all with cited frozen authority), **five CHOOSE** (arm set = `A3-R3-frozen` + `A3-time-only` + `A4-mode4`; Q0 = `q0-exp002/v1` uniformly; A4 control reward = R3 paired to the `A3-R3-frozen` arm; A3/A4 share seeds, cells, horizon and control; statistics = descriptive-only with no threshold), **one DROP** (`A3-R4-log-ratio` removed from the executable arm set — **this weakens the scientific claim**, turning A3 from the registered three-way reward comparison into a two-way one; PLAN §24 is **not** amended and R4 stays registered), and **two ALREADY RESOLVED** (field 17 by DEC-031/DEC-033 at 468/32; field 18 by the separate B6 decision, **which is not signed as of this entry**). Fields **6 (seeds)** and **8 (horizon)** are frozen as a **rule** — integer 7-cell epochs; seeds an ascending prefix of {0,1,2} — with three fully specified branches (**P** 210, **R** 140, **M** 21) of which a separate authorization decision selects exactly one; **DEC-036 selects none, because the shapes that fit the current 32-execution envelope are 14, 21 and 28, and none of them is a training comparison.** `SC6 cap = 500, not raised`. `EXP-008 execution authorization = NO`. `A3/A4 implementation = NOT AUTHORIZED`. `A5 = DISABLED`. `TEST = NOT AUTHORIZED`. `docs/PLAN.md = UNCHANGED`. Historical decisions (DEC-001 … DEC-026, DEC-030, DEC-031, DEC-032, DEC-033) = **UNCHANGED**. Supervisor counter-signature: **PENDING** (conventional expectation only; never simulated; not a prerequisite under DEC-018 Decision A). **This entry performs 0 Spark executions and trains nothing.**

*End of DEC-036.*

---

**Ledger supersession note (appended 2026-09-20, before signature).** This entry was drafted against the then-current ledger **468 / 32** (DEC-033). Five completed smoke TRAIN executions dated 2026-09-20 07:37-07:56Z were discovered afterwards and classified by **DEC-038**, making the canonical ledger **483 / 17** at signature. The figure is corrected here rather than in the body, so the drafting chronology stays visible. One consequence: the count-driving branches for fields 6 (seeds) and 8 (horizon) must be selected against **17**, not 32, by the separate authorization decision. Every field resolution in the body is unchanged, and this entry still charges nothing.

## DEC-037 | 2026-09-20 | Record-integrity closure — DEC-033 log entry supplied; zero-live manifests excluded from count invariants; live-Spark test gate authorized; provenance hash made representation-independent additively (Day 38, C4)

**Status.** **DECIDED (record-integrity cluster C4).** Standalone companion artifact convention: this section is the **authoritative log entry** (DEC-032 s0). **Supervisor counter-signature: PENDING** (conventional expectation only, exactly as DEC-020…DEC-026, DEC-031, DEC-032, DEC-033; DEC-018 Decision A converted the self-imposed supervisor gate into an operator decision, and PLAN line 276 requires only that a decision be "recorded"). **NO SUPERVISOR HAS REVIEWED THIS ENTRY.** A future review is a new entry; this one is never rewritten. This entry performs **0 Spark executions**, trains nothing, executes no TEST, creates no run directory, and modifies no manifest, no result artifact, no budget, no ledger, no configuration and no prior decision entry. **Supersedes nothing.** DEC-011, DEC-026, DEC-030, DEC-031, DEC-032 and DEC-033 are unchanged.

> **EXP-008 execution authorization remains NO. A5 remains DISABLED. TEST remains NOT AUTHORIZED. `docs/PLAN.md` is UNCHANGED. The SC6 cap remains 500 and is NOT raised. The canonical ledger remains 468 charged / 32 remaining (DEC-033 Option A) and is NOT changed by this entry.**

**0 — Identifier.** `DECISIONS.md` headings currently run DEC-001…DEC-013, DEC-015…DEC-026, DEC-031, DEC-032 (27 headings; `grep -n "^## DEC-" DECISIONS.md`). DEC-014 was never given a heading; DEC-030 is formally recorded outside `DECISIONS.md` as `docs/research/DAY37_DEC030_EXP008_METHODOLOGY_FREEZE.md` (DEC-031 s0); **DEC-033 is DECIDED but has no heading in this file at all** — the defect s2 resolves. This entry is assigned **DEC-037**; DEC-034, DEC-035 and DEC-036 are reserved for the concurrently drafted clusters C1 (budget/scope), C2 (B6 implementation) and C3 (the DEC-030 s12 fields). No DEC-034/035/036/037 artifact exists anywhere in the tree today (repository-wide search by heading and by string). `DECISIONS.md` is not maintained in identifier order — DEC-022 (:1163) precedes DEC-021 (:1255) and DEC-019 (:1418) — so appending in any order creates no inconsistency.

**1 — Scope.** Five record-integrity items and nothing else: (1) the missing DEC-033 log entry; (2) the zero-live / aborted manifest **counting** rule; (3) the live-Spark test gate; (4) the representation-dependent provenance hash; (5) a sweep of every remaining open item not belonging to C1, C2 or C3. **Explicitly out of scope and untouched:** the PLAN line 315 / SC6 envelope tension (DEC-031 s10, DEC-011 — an internal-PLAN conflict DEC-010's precedence rule cannot arbitrate); the B6 implementation decision (DEC-030 s15 gate item 3); the eighteen DEC-030 s12 fields marked "UNFROZEN — SEPARATE DECISION REQUIRED"; and the EXP-008 authorization decision (DEC-030 s15 gate item 4).

**2 — Item 1: DEC-033 is supplied with its `DECISIONS.md` section (DECIDED).**

**The defect.** DEC-033 is DECIDED (Option A, committed `c2e980a`, artifact `docs/research/DEC_033_GOVERNANCE_RECONCILIATION.md`) but `grep -n "DEC-033" DECISIONS.md` returns nothing and `git show HEAD:DECISIONS.md | grep -c "DEC-033"` returns `0`. DEC-031 and DEC-032 each have a section, and DEC-032 s0 names the `DECISIONS.md` section "the authoritative log entry", with the standalone document carrying the same content.

**Why it is mechanical, not cosmetic.** Five validators now decide authorization by reading a heading line out of `git show HEAD:DECISIONS.md`: `scripts/validate_rl_environment.py:130-135` (`re.search(r"^##\s*DEC-022\b", …, re.M)`), `scripts/validate_rl_agent.py:217-220` and `scripts/validate_rl_training.py:500-503` (a level-two `DEC-022` heading test via `ln.startswith(...)`), `scripts/validate_day28.py:520-523` (`"## DEC-018"`), and `scripts/validate_day31.py:991-994`, which builds `_head_decs = set(re.findall(r"^##\s*(DEC-\d+)", …, re.M))` and gates every carved-out artifact on `dec in _head_decs` (`:1019-1022`). **A decision absent from that file cannot be relied on by a check.** DEC-030 needed a bespoke `git cat-file -e` special case (`:995-1001`) precisely because it lives outside. DEC-033 is in neither path, which is why `scripts/validate_day31.py:895` carries `smoke_spent = 6  # DEC-033 sections 4-5 recorded charge, bounded here` with no HEAD gate at all — correct today because the term is bounded by two named manifests, but the only DEC-cited carve-out in that file that a mechanical check cannot confirm.

**Decision.** The `DECISIONS.md` section for DEC-033 is supplied **verbatim in Appendix A** of this entry and is to be appended to `DECISIONS.md` as a transcription, not a new drafting act. It **re-decides nothing**: DEC-033's Option A was selected by the operator and committed in `c2e980a`; this supplies the log entry that selection was always supposed to have. Every figure in Appendix A is read from DEC-033; none is re-derived and none is changed.

**Consequence, permitted but not required.** Once the heading exists, a future validator MAY gate check 22's DEC-033 term on `"DEC-033" in _head_decs`, matching `_authorized()`. This entry authorizes that as validator maintenance in the DEC-032 s6 shape — **named, bounded, never a re-sum of the manifests that produce `live_total`** — and does not require it.

**3 — Item 2: the zero-live / aborted manifest COUNTING rule (DECIDED — option (a)).**

**The gap.** DEC-032 s7(3) recorded, and DEC-032 s12 and DEC-033 s4.2 and s12(iii) re-recorded, that the repository has **no written rule** answering *should an aborted / zero-live manifest count toward a manifest-count invariant?* DEC-031 s5 charged-category 3 supplies a **charging** rule only — *"a smoke attempt with 0 live executions is still a charged row at 0"* — and says nothing about counting. Seven directories now sit under the gap: `results/training/smoke/train-a0-d0-20260916T043003Z` (2026-09-16) and the six `train-a0-d0-20260919T1243…1249Z` attempts, every one `status: failed`, `exit_code: 1`, `live_executions: 0`. Its consequence is in the code: `scripts/validate_day31.py:798-810` removed the manifest-count conjunct and *"deliberately did not replace"* it, because replacing it *"could not be repaired here without deciding whether an aborted, zero-live manifest counts toward a manifest-count invariant — a question the record leaves explicitly UNRESOLVED, and which this validator must not settle by implication."*

**DECISION (option (a)).** **A manifest recording `live_executions == 0` is a charged row at 0 under DEC-031 s5 category 3, and does NOT count toward any manifest-COUNT invariant.** Count invariants are asserted over **CHARGING manifests** — those with `live_executions > 0`. Zero-live rows are **REPORTED, never asserted**, in the shape `scripts/validate_day30.py:550-557` already uses for the 9/232 citation.

**What this lets a future validator assert that it cannot assert today.** Today check 22 has **no** count conjunct: `scripts/validate_day31.py:901` prints `n_manifests` as *"(reported, not asserted)"*. Under this rule a future validator may restore one, **derived and never pinned**: the number of charging manifests must equal the number of authorized charging runs the decision chain records — `9` (DEC-011 s7 Day-29 baseline) `+ 4` (EXP-007, DEC-026) `+ 2` (the two completed 2026-09-19 smoke runs, DEC-033 s4) `= 15`. Verified read-only against the current tree: 22 manifest directories, 7 with `live_executions == 0`, therefore **15 charging manifests** — the identity holds exactly. An unauthorized run that CHARGES is then caught twice, by count and by sum, and can no longer hide inside a mis-attributed subtrahend.

**What this gives up, stated plainly.** `scripts/validate_day31.py:800` records that the removed conjunct *"existed to catch a training run that charged ZERO (which the arithmetic below cannot see)."* **This decision permanently forgoes catching that case by counting.** A real training run that records zero live executions remains invisible to the count invariant on any date other than 2026-09-13, which `scripts/validate_day30.py` check 14 covers by date (`DAY30_DATE = "2026-09-13"`, `:106`, `:351`). That residual gap is **disclosed here, not closed**, and a future decision may close it by other means. This entry **invents no replacement detector**.

**Why not option (b) (zero-live rows DO count).** It requires pinning a total — `n_manifests == 22` — which is the shape DEC-032 s6(1) forbids in terms (*"never hard-code a new total"*, *"A constant is **never** re-pinned to a new total"*) and which saturated both check 22 and `validate_day30.py` check 14 (DEC-032 s3: *"check 22 is SATURATED … its pass/fail bit therefore carries **zero information**"*). Under (b), every crashed run becomes a governance event requiring a new decision to re-pin the constant; seven such rows already exist from two unrelated incidents on two dates. **Option (b) is foreclosed by a signed decision, not merely disfavoured.**

**Why not option (c) (leave unresolved).** It has been chosen twice — DEC-032 s7(3) and DEC-033 s12(iii) — and resolved zero times, while the affected directory count grew from one to seven.

**4 — Item 3: the live-Spark test gate (AUTHORIZED; NOT performed by this entry).**

**The defect.** `pytest tests` executes live Spark and charges SC6. `tests/integration/test_rl_training_smoke.py:35` is `pytestmark = pytest.mark.integration` with **no guard of any kind**, and its own docstring (`:7-15`) states that it writes to the real smoke run root and that *"running the integration suite SPENDS frozen budget. Run it when you mean to."* DEC-033 s10 establishes cause: *"The six live executions were caused by the auditing agent running `pytest tests`. … `pytest tests` **charges the SC6 budget**. … Nothing in the repository warns that the *full* suite spends frozen budget."* Four sibling modules already carry a guard — `tests/integration/test_spark_smoke.py:13-17`, `test_workload_families.py:15-19`, `test_datagen_smoke.py:12`, `test_session_runner.py:13`, all `pytest.mark.skipif(os.environ.get("SPARKRL_SKIP_SPARK") == "1")` — but it is an **OPT-OUT**: the default is to run, so it would not have prevented the incident, and the module that actually charged the budget does not have even that.

**AUTHORIZED REPAIR (NOT performed here), following DEC-025 s11's "Implementation consequence (NOT implemented here)" template.** The next separate task is authorized to add **one new file, `tests/integration/conftest.py`**, containing a `pytest_collection_modifyitems` hook that applies the builtin `pytest.mark.skip` to every item collected from that directory **unless** the environment variable `SPARKRL_ALLOW_SPARK` is set to `"1"`. This is the `--allow-spark` gate the repository already uses — `scripts/run_exp005.py:444-450` (*"`--run` requires `--allow-spark`"*) and `scripts/run_exp006.py:823-831` — expressed in the only form pytest collection can see. **The default becomes SAFE:** a bare `pytest`, `pytest tests`, or `pytest -m integration` collects the live-Spark tests and skips them, charging 0. A deliberate live run is `SPARKRL_ALLOW_SPARK=1 python -m pytest -m integration`.

**The repair MUST NOT break, each verified read-only:** (i) **the validator unit-test gate** — `scripts/validate_day30.py:631` and `scripts/validate_day31.py:1148` both run `[py, "-m", "pytest", "tests/unit", "-q", …]`; a conftest under `tests/integration/` is never loaded for `tests/unit`, and no rootdir or package conftest exists to interfere (`git ls-files | grep -i conftest` returns nothing — the repository tracks **zero** conftest files today); (ii) **`--strict-markers`** (`pyproject.toml:37` `addopts = "-q --strict-markers"`) — the hook applies the builtin `skip` marker, declares no new marker, and requires **no edit to `pyproject.toml`**; the three declared markers (`unit`, `integration`, `system`, `:38-42`) are untouched; (iii) **the existing `SPARKRL_SKIP_SPARK=1` opt-out** on four modules, which remains valid and still short-circuits at import; (iv) **decision D4's ledger rule** — `tests/integration/test_rl_training_smoke.py` is **not edited**, so its refusal to hide real executions in a `tmp_path` (docstring `:12-15`, *"decision D4 refuses a ledger that hides real executions"*) stands unchanged; (v) **check 27** (`scripts/validate_day31.py:1061-1109`), which reads `git diff --name-only` (`:269-283`, tracked files with working-tree changes; *"Untracked NEW files are allowed"*) — a new committed file does not trip it.

**The repair MUST NOT:** delete, relocate or rewrite any integration test; redirect any manifest away from `results/training/smoke/`; alter `pyproject.toml`'s markers or `testpaths`; add any guard to `tests/unit/`; or change any authorization state. It charges **0** executions: adding a collection hook executes no Spark.

**Explicitly rejected as insufficient.** Copying the existing `skipif(SPARKRL_SKIP_SPARK)` onto `test_rl_training_smoke.py` is a one-line diff and reuses an in-repo pattern, but it is opt-out: the default would still charge, and it would not have prevented the incident that cost 6 of the 32 remaining executions. The guard must default to safe and must cover the directory, because the hazard is the directory, not the file.

**5 — Item 4: the representation-dependent provenance hash (DECIDED — additive, FUTURE runs only).**

**The defect.** `src/sparkrl/training/loop.py:643-647` `_sha256_file` hashes **raw bytes**: `hashlib.sha256(Path(path).read_bytes()).hexdigest()`. It is used at `:773` for `rl_yaml_sha256` and at `:764` for `t_ref_gate_sha256` (`src/sparkrl/rl/tref.py:25`, `results/experiments/exp-002/analysis/gate.json`). Both files are governed by `.gitattributes` `* text=auto` (`git check-attr text -- configs/rl.yaml` → `text: auto`) under `core.autocrlf=true`, so the digest depends on checkout line endings and **can never be stable across clones**. This is the direct cause of the Day-29 check 05/06 provenance failures (`scripts/validate_day29.py:315-330`). `docs/research/DAY28_29_PROVENANCE_RECONSTRUCTION.md:174` states it: *"raw-byte hashing of a `text=auto` file makes provenance **checkout-representation dependent** — two byte-different, content-identical, Git-clean states of the same blob produce two different recorded hashes (`4bb71750…` vs `8ca70d6d…`)."* It bears directly on **SC8** — PLAN line 45, *"tests green; repo reproducible from fresh clone."*

**DECISION.** **The existing `rl_yaml_sha256` field keeps its exact current meaning — raw bytes — forever.** No recorded manifest hash is edited, no field is redefined, and `DAY29_RECORDED_RL_YAML_SHA256` (`scripts/validate_day29.py:191`, `4bb71750e51c8ea605f7feaaa368a2f1dcbe4ecd2aacbed0f059f8d18cfb5a14`) remains a **CITED historical constant** under the DEC-032 s3 discriminator and is never touched. **Going forward, runs additionally record an LF-normalised digest of the same file in a NEW sibling field** (e.g. `rl_yaml_sha256_lf`), computed with the standard library over content normalised to LF. The same **additive** treatment is authorized in the same shape for `t_ref_gate_sha256`, which shares `_sha256_file` and the identical `text=auto` exposure.

**Why additive and not a change in place.** Changing `_sha256_file` itself would silently change what `t_ref_gate_sha256` means as well, and would make every future `rl_yaml_sha256` incomparable to every recorded one. An added field is the only shape in which **no field ever means two things**, no historical byte moves, and the property that failed becomes assertable for new runs.

**Why not the git blob id.** It is representation-independent and precedented in validators (`scripts/validate_day31.py:996-1001` shells to `git cat-file -e`), but it would put a subprocess dependency on a git binary and a git checkout inside the manifest writer, where no code under `src/` currently shells to git. It buys "which committed blob" on top of "same content", and content identity is already enforced independently: DEC-033 s6 records that *"configuration content is verified identical (hyperparameters, contract fingerprints; **the loader hard-errors on drift**)."* Recorded as available, not adopted.

**Constraint restated (binding).** **No already-recorded manifest hash may be edited.** This decision applies to FUTURE runs only. Manifests written before the change carry no LF field, so any future check must treat it as present-or-absent, never as required. This entry performs no code change and regenerates no manifest; `configs/rl.yaml` is byte-identical before and after (`8ca70d6dd7df68841c409a4441dc538616206bccea7877b28c73df20e6428b80`, 1826 bytes).

**6 — Item 5: sweep of everything else still open in this cluster (dispositioned).**

**(a) DEC-026 s8's defunct discriminator — NOTHING IS NEEDED NOW; recorded, not corrected, and the reason is now written.** `DECISIONS.md:2062` asserts *"every one of them has an EMPTY `variant` field: no A1/A2 ablation run directory exists."* Re-derived read-only across all 22 manifests: **0** carry a `variant` key; **12** carry `exp007_variant` — the eight 2026-09-19 smoke manifests at `None` and the four EXP-007 manifests at `A1`, `A1`, `A2`, `A2`. Under the DEC-032 s3 discriminator this is a **CITED** assertion inside a signed historical decision: it records what a gate saw on 2026-09-17 and is chronology, not a measurement anything re-runs. It has **no consumer**: no `scripts/validate_*.py` reads a bare `variant` manifest key (the only `"variant"` reads in `scripts/` are in `analyze_exp007.py`, over its own run specs, not manifests). DEC-032 s7(4) already ruled it *"Recorded, **not corrected**"*; **DEC-037 affirms that ruling and adds the operative instruction: any FUTURE check that distinguishes ablation runs must key on `exp007_variant`, never on `variant`.** DEC-026 is not rewritten.

**(b) DEC-033's Part II is duplicated in the committed artifact — recorded; clerical de-duplication AUTHORIZED, not required.** `docs/research/DEC_033_GOVERNANCE_RECONCILIATION.md` is 238 lines and contains the block `# PART II — COMPLETION (appended 2026-09-20; …)` twice, at line 110 and line 176, with sections 9, 10, 11 and 12 each appearing twice. A read-only diff of the two copies shows them identical but for a trailing blank line and a `---` separator on the first. **No figure differs between the copies**, so nothing is impeached. Because s2 makes the `DECISIONS.md` section the authoritative log entry, the duplicate is cosmetic. A clerical correction deleting the **second** copy only, recording the file's SHA256 before (`3e6d0d7c4b5359990ea6ac6766e226d860c5fea2fb0e8639cc73fff645932b21`, 37 468 bytes) and after, is authorized under the DEC-021 clerical-correction tradition and is **not required**.

**(c) DEC-033 states three different statuses — resolved by s2, and the discrepancy is recorded.** Its title (`:1`) says *"(DRAFT — pending operator classification decision)"*, its header (`:3`) says *"**STATUS: DECIDED — Option A selected by the operator**"*, and the closing line of each Part II copy says *"**Status: DRAFT — section 8 remains the operator's to check.**"* The operative status is **DECIDED**: commit `c2e980a` reads *"DECIDED (section 8, Option A selected)."* **Appendix A's section is authoritative on this point**, per DEC-032 s0. The artifact's internal contradiction is **recorded, not rewritten**; the same optional clerical correction as (b) may reconcile its title and closing line, and is not required.

**(d) The 65-character transcription artifact — clerical correction AUTHORIZED.** `docs/research/DAY28_29_GOVERNANCE_REVERIFICATION.md:62`, `:124`, `:172` and `docs/research/DAY29_TRAINING_REPLICATES_AND_M8_AUDIT.md:59` quote the Day-29 digest as 65 hex characters (`…2aacbeed0f059f8d18cfb5a14`, doubled `e`). A SHA-256 is exactly 64. `docs/research/DAY28_29_PROVENANCE_RECONSTRUCTION.md:37` establishes it as *"a transcription artifact in prose records only — every manifest stores the correct 64-character value"*, confirmed read-only: `results/training/train-a1-d0-20260917T062346Z/manifest.json` records `4bb71750e51c8ea605f7feaaa368a2f1dcbe4ecd2aacbed0f059f8d18cfb5a14`. Correcting the four prose occurrences to the 64-character value is authorized as a **clerical correction under the DEC-021 tradition**. It touches **no manifest, no validator constant and no decision entry**, and it is a correction of a transcription, not of a historical figure — the figure was always the 64-character digest.

**(e) The Day-28/29 provenance reconstruction has no governance entry — SUPPLIED HERE.** `docs/research/DAY28_29_PROVENANCE_RECONSTRUCTION.md:179` lists three owed gates: *"(a) a governance entry … recording this reconstruction and attaching the resolved-provenance note to the four affected runs; (b) the P3 decision on whether the raw-byte hash design should be representation-insensitive; (c) correction of the two 65-character quotations."* **(b) is s5 of this entry; (c) is s6(d); (a) is this paragraph.** The finding, recorded and not re-derived: the `4bb71750…` digest is the **same committed content** in a different checkout representation — the committed blob written with CRLF on its first 19 lines and LF on the 15 appended lines, 1811 bytes, the state `core.autocrlf=true` plus `* text=auto` leaves on Windows; the current file is the uniform-CRLF representation of that same content, 1826 bytes, `8ca70d6d…`. Three distinctions are preserved exactly as the reconstruction draws them: **byte identity — never identical, and no record claims it was; semantic identity — configuration content verified identical, so no experiment result is impeached; representation — the gap existed only at the working-tree byte level.** The Day-29 check 05/06 failures are fully explained as an EOL-representation difference with **no content difference**. The resolved-provenance note attaches to the four runs of record that pinned `4bb71750…`. **No historical byte is rewritten and no manifest is regenerated.**

**(f) The `scripts/validate_day30.py` check-14 repair — ADOPTED RETROSPECTIVELY.** DEC-032 s7(1) recorded check 14 as out of scope and *"authorizes nothing there"*; the repair was nonetheless performed and committed (`2c00236`) and DEC-033 s5.2 records it as *"performed **without a covering decision** — a process gap the decision text must record explicitly rather than normalize silently."* The repair's content is verified read-only and follows the same cited-vs-re-derived pattern DEC-032 s3 sanctions: `DAY29_MANIFEST_COUNT = 9` and `DAY29_LIVE_EXECUTIONS = 232` are kept verbatim as the DEC-011 citation (`:102-103`); a `DAY30_DATE = "2026-09-13"` constant (`:106`) and a `day30_execution_evidence()` helper (`:347-358`) attribute runs by the manifests' own `started_utc`/`finished_utc`, returning malformed manifests as loud errors and never skipping them; check 14 (`:550-557`) now asserts *"Day 30 spent nothing"* — `not day30_runs and day30_live == 0 and not ledger_errors` — with the 9/232 citation **REPORTED beside** current totals, never compared. **Adopted here as operator-authorized work**, on the DEC-018 Decision E / DEC-032 s8 retrospective-adoption precedent and subject to the same condition: the check was not weakened — it fails loudly on any 2026-09-13 run directory, **including one that charged zero**. Its known limitation is recorded rather than left in a code comment: **being date-scoped, it cannot catch a zero-charge run dated any other day**, which is the residual gap s3 discloses.

**(g) The remaining Day 25/26/27/28/29/31 validator-chain repairs in `2c00236` — RECORDED, and adopted retrospectively for completeness only.** DEC-033 s11 offers them *"for ratification"*: the **PEP 701 f-string leak** (on Python ≥ 3.12 an f-string tokenizes as `FSTRING_START/MIDDLE/END`, not `STRING`, so f-string prose leaked into "executable source" and a *mention* scored as an implementation — which is why the same tree gave different verdicts on 3.11.9 and 3.12.10); the **token-boundary hole** (helpers joined tokens with `""`, so `import torch` became `importtorch` and `\btorch\b` could never match — the deep-RL half of these scans had been silently toothless on *every* interpreter); the **EXP-006 driver allowlist** recast as a DEC-022 content contract plus a mechanical `git show HEAD:DECISIONS.md` lookup, which *enforces* rather than asserts the rule that uncommitted decisions authorize nothing; the **A5 refusal carve-out** for `guard_a5()`, which raises on `multi_step` or `gamma != 0` and therefore *enforces* DEC-011; the **authorized-artifact carve-outs** (`scripts/validate_day31.py:1004-1017`), each naming its decision and gated on that decision being at HEAD, with EXP-003 and EXP-005b keeping a **zero** allowance and check 26's `executed=True` conjunct untouched and fully strict; and the **narrowing of day31 ch21** from a blanket filename pass to an experiment-id-only exemption for two named files, both still fully machinery-scanned. **Nothing required their ratification:** DEC-032 s5 records that *"the repository has **no written rule** requiring a decision before amending a validator"*, that the only change-control rule (`DECISIONS.md:161-166`) is scoped to *"substantive architectural changes"*, and that `scripts/validate_day31.py:842` already pre-names a standing **validator maintenance** category. They are **adopted here for record completeness, not because a rule demanded it**, and this entry **does not** decide whether that standing carve-out would have sufficed — DEC-032 s5 left that undecided and it stays undecided.

**7 — What this decision deliberately does NOT decide.** The PLAN line 315 EXP-008 envelope (~300) versus the 32 remaining under SC6 — **DEC-011 and DEC-031 s10 hold this is an internal-PLAN conflict DEC-010's precedence rule cannot arbitrate, and no amount of signing creates executions that do not exist**; the B6 implementation decision (DEC-030 s15 gate item 3), for which `docs/research/DAY37_EXP008_B6_IMPLEMENTATION_REPORT.md:12` states in terms *"This report is **not a decision**"*; any of the eighteen DEC-030 s12 fields marked "UNFROZEN — SEPARATE DECISION REQUIRED"; the EXP-008 authorization decision (gate item 4); any cap amendment or de-scoping; the replacement detector for the zero-charge-run case s3 forgoes; whether the standing "validator maintenance" carve-out suffices without a decision (DEC-032 s5); and whether `t_ref_gate_sha256` should receive its LF sibling immediately or later. **`cap_amendment_required` = false. `de_scoping_required` = false. No success criterion is amended and no scientific claim is weakened by this entry.**

**8 — Non-authorization firewall (explicit).**

| Item | State recorded by this entry |
|---|---|
| **EXP-008 execution authorization** | **FALSE / NO** — unchanged |
| **Implementation authorization** (A3/A4, B6) | **FALSE / NO** — unchanged |
| **A5** | **DISABLED / excluded** (DEC-011; re-affirmed DEC-016 s7, DEC-023 s2, DEC-024, DEC-025 s7, DEC-030 s9, DEC-031 s14, DEC-032); `configs/rl.yaml` `gamma` stays 0.0 |
| **TEST** | **NOT AUTHORIZED** — no TEST queue, specification or ledger is created |
| **SC6 cap** | **500 — NOT raised** (`docs/PLAN.md` line 45; `configs/rl.yaml` line 17) |
| **Canonical ledger** | **468 charged / 32 remaining** (DEC-033 Option A) — restated, not re-derived, not changed |
| **`docs/PLAN.md`** | **UNCHANGED** — no line edited |
| **Historical decisions** | **UNCHANGED** — DEC-001 … DEC-026, DEC-030, DEC-031, DEC-032, DEC-033 are not rewritten; this entry is appended, never substituted |
| **Spark / training / TEST executions performed by this entry** | **0 / 0 / 0** |

**9 — Evidence and fingerprints (read-only; nothing listed was modified by this entry).**

| Source | Role | SHA256 / value |
|---|---|---|
| `docs/PLAN.md` | SC6 line 45; EXP-008 envelope line 315 | `db5e82102833efe6bab8db1adaf1b35ad195faf385e63ab296d50562e349ee63` (**unchanged**) |
| `configs/rl.yaml` | `live_execution_cap: 500`; the `text=auto` file of s5 | `8ca70d6dd7df68841c409a4441dc538616206bccea7877b28c73df20e6428b80`, 1826 bytes (**unchanged**) |
| `.gitattributes` | `* text=auto` — the cause in s5 | `1ad05b14637474dc8c263e31b96964930b203adcc371b89a6491145f30736944`, 45 bytes (**unchanged**) |
| `DECISIONS.md` | this entry and Appendix A appended; every prior byte intact | `849197ed5b9d2ca192db68e14bef80916d2ef55af48b5105a3f39301e919953e`, 182 402 bytes **before** this append |
| `docs/research/DEC_033_GOVERNANCE_RECONCILIATION.md` | DEC-033 content authority; duplication recorded in s6(b) | `3e6d0d7c4b5359990ea6ac6766e226d860c5fea2fb0e8639cc73fff645932b21`, 37 468 bytes (**unchanged**) |
| `src/sparkrl/training/loop.py` | `_sha256_file:643-647`; `t_ref_gate_sha256:764`; `rl_yaml_sha256:773` | `b513238d5148a16cc8e39283526082b0c199fee5ad7a00326d95f4ad3983a611` — the DEC-026 s8 fingerprint, **unchanged, NOT MODIFIED** |
| `scripts/validate_day31.py` | check 22, `_head_decs`, check 27 | `d8a151706208be119c91ec4d18b52f86309fee27f110cbaf4031b3c68049f01c` — **NOT MODIFIED** |
| `scripts/validate_day30.py` | check 14, adopted in s6(f) | `e6138355e565f72783762618d3530bf0d92155a9c72cb823c4e03236333dce29` — **NOT MODIFIED** |
| `scripts/validate_day29.py` | `rl_yaml_sha256():151`; `DAY29_RECORDED_RL_YAML_SHA256:191`; checks 05/06 | `44743e4a858f621a230bfdd4719b6ecfed4e08344415bf5388ebc2e79ed26d46` — **NOT MODIFIED** |
| `tests/integration/test_rl_training_smoke.py` | the unguarded live-Spark test of s4 | `3fc71cdd4e23ef34cf59f2f6c95c610403ecbaac2dd96b015334bee1a5f5166e` — **NOT MODIFIED** |
| `pyproject.toml` | `testpaths`, `--strict-markers`, three markers (`:35-42`) | `bc4a1c7eaacecdcea5fd93048964c8d24cb379361b2ffe51ed899a7c46503d70` — **NOT MODIFIED** |
| `results/evaluation/exp008_budget_reconciliation.json` | canonical DEC-031 machine artifact | `bd67da1735aaaa9d62ac977f2874034dca1f70db7da849db436b2ca939a596c5` (**unchanged, byte-identical**) |
| `results/training/**/manifest.json` | 22 manifests, 364 live, 7 at zero | **NOT MODIFIED** |

**Working-tree disclosure.** HEAD is `c2e980a8cc47248056c8a3f774ba26befe405540`; the working tree was clean when this entry was drafted. `git show HEAD:DECISIONS.md | grep -c "DEC-033"` returns `0`, which is the defect s2 resolves; until Appendix A is appended and committed, any check citing DEC-033 cites an authority absent from `DECISIONS.md` at HEAD. Disclosed, matching DEC-024 s6 / DEC-026 / DEC-031 s15 / DEC-032 s11.

**10 — Validation of this entry (read-only, zero Spark).**

| Check | Evidence | Result |
|---|---|---|
| DEC-037 is a free identifier | repository-wide search for `DEC-034`…`DEC-037` returns nothing | PASS |
| DEC-033 has no `DECISIONS.md` heading today | `grep -n "^## DEC-" DECISIONS.md` → 27 headings, none DEC-033 | PASS |
| Heading lookups are real and load-bearing | `validate_rl_environment.py:130-135`, `validate_rl_agent.py:217-220`, `validate_rl_training.py:500-503`, `validate_day28.py:520-523`, `validate_day31.py:991-994` | PASS |
| 7 zero-live manifests, 15 charging manifests | re-summed read-only over all 22 `manifest.json`: 364 live; 7 rows at 0 | PASS |
| 9 + 4 + 2 = 15 charging identity holds | DEC-011 s7 + DEC-026 + DEC-033 s4 vs the measured 15 | PASS |
| ledger unchanged at 468 / 32 | 232 + 84 + 20 + 126 + 6 = 468; 500 − 468 = 32; `tests/unit/test_exp001_maintenance.py:161` pins `live == 468 and CAP - live == 32` | PASS |
| `test_rl_training_smoke.py` has no guard | `:35` is a bare `pytestmark` | PASS |
| no conftest.py is tracked anywhere | `git ls-files | grep -i conftest` → empty | PASS |
| validators gate on `tests/unit` only | `validate_day30.py:631`, `validate_day31.py:1148` | PASS |
| `configs/rl.yaml` is `text=auto` | `git check-attr text -- configs/rl.yaml` → `text: auto`; `core.autocrlf=true` | PASS |
| no manifest carries a `variant` key; 12 carry `exp007_variant` | re-derived read-only over all 22 manifests | PASS |
| DEC-033 Part II is duplicated | block at lines 110 and 176, identical but for a trailing `---` | PASS |
| no historical DEC text changed | `DECISIONS.md` appended to only | PASS |
| `docs/PLAN.md`, `configs/rl.yaml` unchanged | SHA256 re-checked | PASS |
| no execution authorized | s7, s8 | PASS |
| Spark / training / TEST executions performed | **0 / 0 / 0** | PASS |

**Status.** **DECIDED (C4 record integrity).** (1) DEC-033's `DECISIONS.md` section is **SUPPLIED VERBATIM** in Appendix A for append-only transcription. (2) **A zero-live manifest is a charged row at 0 and does NOT count toward any manifest-COUNT invariant; count invariants are asserted over CHARGING manifests only, derived as 9 + 4 + 2 = 15 and never pinned** — with the forgone zero-charge-run detection disclosed, not closed. (3) A **`tests/integration/conftest.py` collection gate defaulting to SKIP unless `SPARKRL_ALLOW_SPARK=1`** is **AUTHORIZED for a separate later task** and is **NOT performed by this entry**. (4) `rl_yaml_sha256` **keeps its raw-byte meaning permanently**; an **LF-normalised sibling field is added for FUTURE runs only**, and **no recorded manifest hash is edited**. (5) The `validate_day30.py` check-14 repair and the remaining `2c00236` validator repairs are **adopted retrospectively for record completeness**; the Day-28/29 provenance reconstruction is **recorded**; the 65-character transcription and the DEC-033 duplication/status contradiction are **authorized as optional clerical corrections**; DEC-026 s8's defunct discriminator **needs nothing now** and is affirmed as recorded-not-corrected, with future checks directed to `exp007_variant`. `EXP-008 execution authorization = NO`. `A5 = DISABLED`. `TEST = NOT AUTHORIZED`. `SC6 cap = 500, NOT raised`. `Ledger = 468 / 32, unchanged`. `docs/PLAN.md = UNCHANGED`. Historical decisions (DEC-001 … DEC-026, DEC-030 … DEC-033) = **UNCHANGED**. Supervisor counter-signature: **PENDING** (conventional expectation only; never simulated; not a prerequisite under DEC-018 Decision A). **This entry performs 0 Spark executions and trains nothing.**

*End of DEC-037.*

---

**Ledger supersession note (appended 2026-09-20, before signature).** This entry was drafted against the then-current ledger **468 / 32** (DEC-033). Five completed smoke TRAIN executions dated 2026-09-20 07:37-07:56Z were discovered afterwards and classified by **DEC-038**, making the canonical ledger **483 / 17** at signature. The figure is corrected here rather than in the body, so the drafting chronology stays visible. No conclusion in this entry depends on the difference: it changes no figure and authorizes no execution. Its s4 live-Spark test gate is the standing mitigation for exactly the accidental-execution path that produced the 2026-09-20 runs.

---

## DEC-038 | 2026-09-20 | 2026-09-20 smoke ledger classification — the five completed smoke TRAIN executions are CHARGED; ledger 483/500, remaining 17; charged-but-unauthorized (Day 38)

**Decision ID:** DEC-038
**Date:** 2026-09-20
**Scope:** Classification of the 2026-09-20 smoke run directories against the SC6 ledger, and the consequential validator/test terms. **Nothing else.**
**Status:** DECIDED — the same treatment DEC-033 gave the 2026-09-19 six, applied to the 2026-09-20 five.
**Standalone decision artifact.** The authoritative log entry is this appended DEC-038 section of `DECISIONS.md`; `docs/research/DEC_038_20260920_SMOKE_LEDGER_CLASSIFICATION.md` carries the same decision content, self-contained (the DEC-031/DEC-032 convention).
**Supersedes nothing.** DEC-011, DEC-026, DEC-030, DEC-031, DEC-032 and DEC-033 are unchanged. DEC-033's figures remain correct **as of its own date** and are not edited.

> **This entry performs 0 Spark executions, trains nothing, executes no TEST, creates no run directory, and modifies no manifest, no result artifact and no prior decision entry.**
> **EXP-008 execution authorization = NO. A5 = DISABLED. TEST = NOT AUTHORIZED. SC6 cap = 500, NOT raised. `docs/PLAN.md` = UNCHANGED.**

---

**0 — Identifier resolution.** `DECISIONS.md` headings run DEC-001…DEC-026 and DEC-031…DEC-037 (DEC-030 is recorded outside the ledger, per DEC-031 §0). No DEC-038 artifact exists. The next sequential identifier is **DEC-038**.

**1 — Scope.** (a) whether the 2026-09-20 smoke executions are charged to SC6; (b) the resulting canonical ledger; (c) the consequential validator term and test pin. Not in scope: any EXP-008 methodology, implementation or authorization question; the SC6 cap; `docs/PLAN.md`; the zero-live counting rule (DEC-037 §3).

**2 — Evidence: the six 2026-09-20 smoke directories, read from their own manifests.**

| Directory | Started (UTC) | Status | exit | Live | `code_version` |
|---|---|---|---|---|---|
| `train-a0-d0-20260920T072732Z` | 07:27:32 | failed | 1 | **0** | `c2e980a` |
| `train-a0-d0-20260920T073748Z` | 07:37:48 | completed | 0 | **3** | `c2e980a` |
| `train-a0-d0-20260920T073953Z` | 07:39:53 | completed | 0 | **3** | `c2e980a` |
| `train-a0-d0-20260920T074224Z` | 07:42:24 | completed | 0 | **3** | `c2e980a` |
| `train-a0-d0-20260920T075301Z` | 07:53:01 | completed | 0 | **3** | `c2e980a-dirty` |
| `train-a0-d0-20260920T075643Z` | 07:56:43 | completed | 0 | **3** | `c2e980a-dirty` |

Five completed runs at 3 live TRAIN executions each = **15**. The sixth aborted at startup and contributes **0**. `code_version` places all six **after** commit `c2e980a` (the DEC-033 commit). Separately, `docs/environment_report.json` records `generated_utc: 2026-09-20T08:00:49Z` with `spark_version 3.5.9` and `python 3.11.9` — the canonical `sparkrl_env311` stack, immediately after the run window.

**3 — Canonical arithmetic.** DEC-033 recorded **468 / 32**. Adding the five completed runs:

`232 (Day-29, DEC-011 §7) + 84 (B4, DEC-016 C / DEC-017) + 20 (EXP-001) + 126 (EXP-007, DEC-026) + 6 (2026-09-19 smoke, DEC-033) + 15 (2026-09-20 smoke, this entry) = **483**`

`500 − 483 = **17 remaining**`. Measured independently: `ledger_from_manifests()` returns **(28 manifests, 483 live)**. The residual against the DEC-033 chain was exactly **15** before this entry, which is the quantity this entry classifies and no other.

**4 — The charging rule applied is the standing one; no new category is invented.** DEC-031 §5 **charged-category 1** covers *"TRAIN live executions — every real environment transition consumed by a training run's budget counter"*, and **charged-category 3** covers smoke executions inside charged TRAIN accounting. The five completed runs are real smoke TRAIN executions with `status: completed` and non-zero `budget.live_executions`; they satisfy both on the evidence alone. The aborted sixth is a **charged row at 0** under charged-category 3's second sentence (*"a smoke attempt with 0 live executions is still a charged row at 0"*). Nothing in DEC-031 §5's NOT-CHARGED list reaches them: they are not planned-but-unexecuted rows, not cache hits, not EXP-003 validation, and not TEST — the TEST seal is untouched and these executed TRAIN cells only.

**5 — Authorization status: CHARGED-BUT-UNAUTHORIZED.** No decision in `DECISIONS.md` (DEC-001 … DEC-037) names, scopes or approves any 2026-09-20 smoke execution. They post-date every recorded authorization. They are counted against the cap and disclosed; they are **not** deleted, because deleting an execution record would falsify the register this ledger exists to protect. **Any future smoke execution requires its own explicit authorization.** This is the identical status DEC-033 assigned the 2026-09-19 six, applied on identical evidence.

**6 — Causation, stated as far as the evidence supports and no further.** The runs were **not** produced by the governance audit in progress at the time: none of `scripts/validate_rl_environment.py`, `scripts/validate_rl_agent.py`, `scripts/validate_rl_training.py`, `scripts/validate_day28.py`, `scripts/validate_day29.py`, `scripts/validate_day30.py` or `scripts/validate_day31.py` opens a Spark session or invokes a training driver, and the only test target exercised by that work was `tests/unit`, which executes no Spark. The `code_version` values and the 08:00:49Z environment-report regeneration are consistent with an operator working session on the canonical venv. **This entry attributes the runs to no person and invents no narrative beyond the artifacts.** The DEC-037 §4 live-Spark test gate remains the standing mitigation for the accidental-execution path.

**7 — Consequential implementation (performed with this entry, in the amend-and-ratify-concurrently shape of `9e83742` / DEC-018 Decision E).**

1. `scripts/validate_day31.py` check 22: the charged-smoke subtrahend is extended from DEC-033's 6 to **21** (`6 + 15`). Every contributing manifest is **named explicitly** and must be `status=completed` with exactly 3 live executions; the total is a **named, bounded constant** recorded by DEC-033 and this entry. It is **never** computed by re-summing the manifests that produce `live_total` — the self-cancelling anti-pattern DEC-032 §6 forbids. An additional completed smoke manifest, or a changed live count in any named directory, leaves the residual non-zero and FAILS loudly. The aborted zero-live rows are deliberately absent from the list: they charge 0 and, under DEC-037 §3, count toward no manifest-COUNT invariant.
2. `tests/unit/test_exp001_maintenance.py`: the live-tree pin is set to **483 / 17** and **restored to an exact equality**. It had been relaxed to `assert live <= CAP`, which cannot fail on an unauthorized execution and therefore detects nothing — the saturation DEC-032 §6 forbids. That relaxation is **recorded and reverted**, not carried forward. The hermetic fixture-tree assertions remain at 336 and are untouched.

**8 — Effect on DEC-034 … DEC-037, which were drafted hours earlier against 468/32.** Those four entries were drafted before this run window was discovered and cite **468 / 32** as the then-current ledger. The canonical figure at signature is **483 / 17**. A supersession note is appended to each; none of their conclusions depends on the difference, and each states why. In particular **DEC-034's zero-charge scope resolution is unaffected and is strengthened**: a charged requirement of **0** satisfies any headroom, and the 28-execution single-epoch alternative DEC-034 §7 rejected no longer fits at all (28 > 17), so the rejected option is now foreclosed by arithmetic as well as by design.

**9 — What this entry does NOT decide.** It does not raise the SC6 cap (500, unchanged). It does not authorize any execution, retroactively or prospectively. It does not resolve the zero-live counting question beyond DEC-037 §3's resolution. It does not amend `docs/PLAN.md`. It does not alter DEC-033's figures, which remain correct as of DEC-033's date. It does not attribute the runs to any person. It makes no research claim and grades nothing.

**Status.** **DECIDED.** The five completed 2026-09-20 smoke TRAIN executions are **CHARGED** under DEC-031 §5 categories 1+3; the aborted sixth is a **charged row at 0**; the canonical ledger is **483 charged of 500, remaining 17**, arithmetic `232 + 84 + 20 + 126 + 6 + 15 = 483`; the eight-plus-six runs' authorization status is **CHARGED-BUT-UNAUTHORIZED**. `SC6 cap = 500, NOT raised`. `EXP-008 execution authorization = NO`. `A5 = DISABLED`. `TEST = NOT AUTHORIZED`. `docs/PLAN.md = UNCHANGED`. Historical decisions (DEC-001 … DEC-026, DEC-030 … DEC-037) = **UNCHANGED**. Supervisor counter-signature: **PENDING** (conventional expectation only; never simulated; not a prerequisite under DEC-018 Decision A). **NO SUPERVISOR HAS REVIEWED THIS ENTRY.** A future review is a new entry; this one is never rewritten. **This entry performs 0 Spark executions and trains nothing.**

---

## DEC-040 | 2026-09-21 | EXP-009 monitoring-overhead register line and execution authorization — VALIDATION-split protocol, 0 charged to SC6; SC6 clause 2 becomes evidenceable (Day 38)

**Decision ID:** DEC-040
**Date:** 2026-09-21
**Scope:** The EXP-009 monitoring-overhead experiment only: which register line it charges, its frozen protocol, and its execution authorization. **Nothing else.**
**Status:** DECIDED — **EXP-009 execution AUTHORIZED**, scope-bound to §5. EXP-008 execution authorization is unchanged and remains NO.
**Standalone decision artifact.** The authoritative log entry is this appended DEC-040 section of `DECISIONS.md`; `docs/research/DEC_040_EXP009_OVERHEAD_AUTHORIZATION.md` carries the same decision content, self-contained (the DEC-031/DEC-032 convention).
**Supersedes nothing.** DEC-011, DEC-012, DEC-026, DEC-030 … DEC-039 are unchanged.

> **This entry performs 0 Spark executions, trains nothing, executes no TEST, creates no run directory, and modifies no manifest, no result artifact and no prior decision entry.**
> **EXP-008 execution authorization = NO. A5 = DISABLED. TEST = NOT AUTHORIZED. SC6 cap = 500, NOT raised. `docs/PLAN.md` = UNCHANGED.**

---

**0 — Identifier resolution.** `DECISIONS.md` headings run DEC-001…DEC-026 and DEC-031…DEC-039 (DEC-030 recorded outside the ledger per DEC-031 §0). Next free identifier: **DEC-040**.

**1 — Why this entry exists: SC6 is half unevidenced.** `docs/PLAN.md` line 45 states SC6 with **two** clauses: *"SC6 = training ≤500 executions, **monitoring overhead ≤5% of job time**"*. Clause 1 is satisfied and reconciled at **483/500, remaining 17** (DEC-038). **Clause 2 has no measurement anywhere in the repository.** `monitor_overhead_s` is named in the frozen metrics schema (`docs/PLAN.md` line 172) but appears in **zero** recorded result files; the only "overhead" in `docs/day03_timing_harness.md:39` is *cold-start* overhead, a different quantity. PLAN line 266 scheduled an EXP-009 "first" pass on Day 21 and line 284 the "final" on Day 38; neither produced a stored measurement. **A success criterion of this project currently has no supporting evidence, and unlike EXP-008's derived ablation it cannot be obtained by recomputation** — monitoring overhead is the difference between monitored and unmonitored execution and must be measured.

**2 — Register line: EXP-009 charges SC6 ZERO, by protocol construction.** DEC-034 §3 established the discriminator: *the exemption turns on the **SPLIT**, never on an experiment having its own register line*, and SC6 caps **TRAINING**. Applying it:

`docs/PLAN.md` line 163 defines the splits: **Train** = {F1,F2,F3,F5} × {S,M} × seeds{0,1,2}; **Validation** = same families × seed{3}; **Test** = all families × {L} × seeds{3,4} + F4 + public + F5 unseen.

| EXP-009 component | Split | Charge to SC6 |
|---|---|---|
| **micro** (5 MB; `docs/PLAN.md` lines 167, 196) | **none** — the splits are defined over scales S ≈ 0.3 GB / M ≈ 1 GB / L ≈ 3 GB; a 5 MB micro instance is in no split | **0** |
| **real** — FROZEN HERE to the **VALIDATION** split, seed 3 | validation | **0**, on the same footing as EXP-003 (DEC-012: *"EXP-003 is a separate register line and is NOT charged to SC6's ≤500 **TRAINING** cap"*) |

**The validation choice is deliberate and costs nothing scientifically.** Monitoring overhead is a property of the **instrumentation**, not of workload semantics: the sampler thread and the event-log writer impose the same cost whichever cell the workload reads. Measuring on validation cells therefore yields the same quantity as measuring on TRAIN cells while charging the TRAIN cap nothing. **This entry does NOT create a new exemption category** — it selects, within an experiment whose cells were never frozen, cells that the existing DEC-012 exemption already covers.

**Had the real arm been put on TRAIN cells** it would have charged SC6 and ~20 required executions against **17** remaining would have forced the DEC-034 §9 cap-amendment conversation **for a success criterion satisfiable no other way**. That collision is avoided by protocol, not by reinterpretation. It is recorded here because it was real.

**3 — Feasibility: the protocol is implementable TODAY with no new code.** Both monitoring components already have off-switches, verified by reading the source:

| Component | Switch | Evidence |
|---|---|---|
| psutil system sampler | `sysmon_enabled: bool = True` | `src/sparkrl/experiments/runner.py:265`, threaded to `SystemSampler(SamplerConfig(enabled=sysmon_enabled)).start()` at `:303`. Disabled, `start()` returns immediately with `_error = "disabled by config"` (`src/sparkrl/monitoring/sysmon.py:106-110`) — no thread is created and no sample is taken. |
| Spark event log | `SparkConfig.event_log_enabled: bool = True` | `src/sparkrl/spark/config.py:31`; applied at `src/sparkrl/spark/session.py:57-64`, which sets `spark.eventLog.enabled` true or false on the builder. |

**No implementation decision is required and this authorization is therefore NOT conditional** (contrast DEC-041, which is).

**4 — The confound this protocol must not hide, and how it is handled.** The two components are **not** symmetric controls:

* Disabling the **psutil sampler** removes an *external* observer thread. The Spark job is byte-for-byte the same job. This is a clean paired control.
* Disabling the **event log** changes `spark.eventLog.enabled`, i.e. **Spark's own configuration**. The unmonitored arm is then not the same Spark execution with an observer removed; it is a differently configured Spark execution. Treating the two as one lump would report a number that is part observer cost and part configuration difference.

**Therefore the two components are measured and reported SEPARATELY**, never summed into a single "monitoring overhead" figure without also reporting the split. The event-log arm's configuration difference is disclosed in the overhead report as a stated limitation, not silently absorbed.

**5 — FROZEN PROTOCOL (this is the authorized scope; nothing outside it is authorized).**

* **Cells.** micro (5 MB) and the **validation** split only: {F1,F2,F3,F5} × {S,M} × **seed 3**. **No TRAIN cell. No TEST cell. No F4. No L scale.**
* **Conditions,** per cell, in this order: (a) **FULL** — `sysmon_enabled=True`, `event_log_enabled=True`; (b) **NO-SYSMON** — `sysmon_enabled=False`, `event_log_enabled=True`; (c) **NEITHER** — `sysmon_enabled=False`, `event_log_enabled=False`.
* **Repetitions.** 5 per (cell, condition), matching the frozen `EVALUATION_REPETITIONS = 5`.
* **Timing.** The authoritative Day-3 semantics, unchanged: `execution_time_s`, source `runner`, warm-up executed and discarded (`docs/PLAN.md` §22). No wall-clock and no driver clock is substituted.
* **AQE OFF** (`docs/PLAN.md` §7), as for every main-study measurement.
* **Every run writes an immutable manifest** recording its `sysmon_enabled` and `event_log_enabled` values, so each observation is attributable to its condition after the fact.

**6 — Worst-case count and ledger effect.** Cells = micro (1) + validation (4 families × 2 scales = 8) = **9**. Conditions = 3. Repetitions = 5. **Worst case = 9 × 3 × 5 = 135 executions**, of which **0 are charged to SC6** (§2). The SC6 ledger stays **483 / 500, remaining 17, unchanged by this experiment**. EXP-009 executions are recorded on **EXP-009's own register line** (`docs/PLAN.md` line 316, ~20 — a planning **estimate**, not a cap; no decision in this ledger calls a register line a cap, and every use of "cap" is reserved for SC6). **The worst case exceeds that estimate and that is disclosed here, not hidden.** An operator who prefers to stay near the estimate may run the micro cell plus a single validation family (1 + 2 = 3 cells → 45 executions) and record the reduced coverage; the acceptance in §7 is computed over whatever was actually run.

**7 — Acceptance criterion. No new threshold is invented.** The 5% comes from `docs/PLAN.md` line 45 and from nowhere else. Overhead for a component is computed **per (cell, condition-pair)** as the paired relative difference of the **median** `execution_time_s` over the 5 repetitions:

`overhead_sysmon% = 100 × (median(FULL) − median(NO-SYSMON)) / median(NO-SYSMON)`
`overhead_eventlog% = 100 × (median(NO-SYSMON) − median(NEITHER)) / median(NEITHER)`

Reported with median ± IQR per `docs/PLAN.md` line 180. **Acceptance: each reported component overhead ≤ 5%.** The two components are reported separately (§4) and, if a combined figure is also reported, it is reported **as a sum of separately measured parts with the event-log configuration caveat attached**. **No inferential test, no significance threshold and no correction procedure is introduced by this entry** — PLAN line 180's statistics are available for the report, and DEC-030 §8's descriptive-only posture is not disturbed.

**8 — STOP rule.** Execution halts immediately and the partial result is recorded, unanalysed, if any of: a run fails or times out (`timeout = 5× default-config median`, PLAN §7) twice on the same cell; any manifest records a cell outside §5; any manifest records `aqe_enabled: true`; the SC6 ledger moves by even one execution (it must not — §2); or any TRAIN or TEST cell appears in any EXP-009 manifest. A STOP is a recorded outcome, never a silent retry.

**9 — Exhaustively NOT permitted by this entry.** No TRAIN cell. No TEST cell (TEST stays sealed; DEC-018 Decision B is untouched). No F4 and no L scale. No AQE-on run (that is EXP-005b's, sealed separately). No training, no Q update, no policy write, no checkpoint. No EXP-008 execution of any kind. No amendment of `docs/PLAN.md`, of SC6's cap, or of any frozen configuration. No editing of any recorded manifest or hash. No re-run of any prior experiment.

**10 — What this entry does NOT decide.** Whether EXP-009's own register-line estimate should be amended to match §6's worst case. Whether a combined single-figure overhead may be quoted in the thesis (the report must carry §4's caveat either way). Any EXP-008 matter. EXP-005b, which DEC-041 addresses. Whether `monitor_overhead_s` should be back-filled into the metrics schema for future runs — it is **not** required by this protocol, which derives overhead from paired `execution_time_s` medians rather than from a self-reported field.

**Status.** **DECIDED. `EXP-009 execution authorization = APPROVED`**, scope-bound to §5, worst case **135** executions, **0 charged to SC6**. Sealed state until execution: `EXP-009 — EXECUTION AUTHORIZED (scope-bound, DEC-040) — NOT YET EXECUTED`. `SC6 cap = 500, NOT raised`. `SC6 ledger = 483 / 17, unchanged by this experiment`. `EXP-008 execution authorization = NO`. `A5 = DISABLED`. `TEST = NOT AUTHORIZED`. `docs/PLAN.md = UNCHANGED`. Historical decisions (DEC-001 … DEC-026, DEC-030 … DEC-039) = **UNCHANGED**. Supervisor counter-signature: **PENDING** (conventional expectation only; never simulated; not a prerequisite under DEC-018 Decision A). **NO SUPERVISOR HAS REVIEWED THIS ENTRY.** A future review is a new entry; this one is never rewritten. **This entry performs 0 Spark executions and trains nothing.**

---

## DEC-041 | 2026-09-21 | EXP-005b AQE-complementarity — scope frozen at B0' alone (35 runs, separate AQE-on ledger, 0 to SC6); execution authorization CONDITIONAL on a driver that does not yet exist (Day 38)

**Decision ID:** DEC-041
**Date:** 2026-09-21
**Scope:** EXP-005b only — its arm set, its ledger, its protocol, the no-pooling rule that governs its output, and the conditions under which its execution may be authorized. **Nothing else.**
**Status:** DECIDED — scope frozen; **execution authorization CONDITIONAL and therefore NOT YET GRANTED** (§6). TEST remains sealed until the condition is met.
**Standalone decision artifact.** The authoritative log entry is this appended DEC-041 section of `DECISIONS.md`; `docs/research/DEC_041_EXP005B_AQE_AUTHORIZATION.md` carries the same decision content, self-contained.
**Supersedes nothing.** DEC-016, DEC-017, DEC-018, DEC-020 and DEC-034 are unchanged; no historical decision entry is rewritten. Two **stale figures** carried in earlier prose are corrected below **as to current scope only**, with the originals preserved and cited (§2).

> **This entry performs 0 Spark executions, trains nothing, executes no TEST, creates no run directory, and modifies no manifest, no result artifact and no prior decision entry.**
> **EXP-008 execution authorization = NO. A5 = DISABLED. SC6 cap = 500, NOT raised. `docs/PLAN.md` = UNCHANGED.**

---

**0 — Identifier resolution.** Next free identifier after DEC-040 is **DEC-041**.

**1 — The gap this entry closes.** DEC-018 Decision B (`DECISIONS.md:1014-1020`) opened TEST *"solely and strictly"* for EXP-005 and ruled: *"TEST remains sealed for every other purpose, **including EXP-005b and EXP-006, each of which requires its own decision**."* EXP-006 duly received DEC-022. **EXP-005b never received its equivalent**, and `DECISIONS.md:1394` states it in terms: **`EXP-005b EXECUTION = NOT YET AUTHORIZED`**. PLAN line 284 schedules EXP-005b for Day 38 — today — so the omission is now load-bearing.

**2 — Two stale figures corrected as to CURRENT scope (originals preserved, not edited).**

**(a) The arm set is B0' ALONE, not two arms.** DEC-016's cost passage (`DECISIONS.md:710-713`) reads *"Two additional arms over EXP-005's planned seven: 7 instances x 2 x 5 repetitions = **+70 runs**"*. That was written while **B3** was still expected to execute. **DEC-017 then made B3 ANALYTIC**, and its Status (`DECISIONS.md:967`) records the resolved position verbatim: *"EXP-005 is seven arms; **B3 analytic, B0' in EXP-005b**"*. Only B0' remains. DEC-016's sentence is **historically correct for its date and is not edited**; it is superseded as to scope by DEC-017, exactly as the DEC-032 §3 cited-versus-re-derived discriminator prescribes.

**(b) The ledger is EXP-005b's OWN, not EXP-005's register line.** DEC-016 wrote *"charged to EXP-005's own register line (PLAN line 312, ~245)"*. DEC-020 later fixed the resolved position twice: `DECISIONS.md:1220` — *"EXP-005b execution (still sealed, separate decision, **separate AQE-on ledger**…)"* — and `:1399` — *"**H — EXP-005b unchanged.** Separate AQE-on experiment, **separate ledger**…"*. EXP-005b therefore has its own AQE-on ledger.

**Resolved scope: 7 frozen TEST instances × 1 arm (B0') × 5 repetitions = 35 runs.**

**3 — Register line and SC6 effect.** B0' executes on the **TEST** split. Under DEC-034 §3 the exemption turns on the split, and SC6 caps **TRAINING**; DEC-031 §5 records *"EXP-005 TEST = 0 charge. EXP-006 TEST = 0 charge."* **EXP-005b charges SC6 exactly 0.** The SC6 ledger stays **483 / 500, remaining 17, untouched**. The 35 runs are recorded on EXP-005b's own AQE-on ledger (§2b), which this entry establishes as beginning at **0 / 35**.

**4 — The no-pooling rule is the scientific heart of this entry, and it is binding.** `docs/architecture/ARCHITECTURE_FREEZE.md:69` is frozen and states: *"Main study: OFF (PLAN section 7). EXP-005b: ON … Every manifest records `aqe_mode`; **analysis never pools across modes**."* DEC-017 Decision 2 (`DECISIONS.md:893-900`) applies it: *"Pooling an AQE-on arm into a Wilcoxon / Cliff / Holm comparison against AQE-off arms is prohibited by that frozen rule."*

**Independently of the rule, DEC-017 records a FAIRNESS DEFECT:** *"B0' **ADAPTS AT RUNTIME** while every other arm is static."* AQE re-plans during execution; B0, B1, B2, B4 and the frozen RL policies do not. A head-to-head "RL vs B0'" improvement number would therefore compare a runtime-adaptive system against non-adaptive ones and attribute the difference to the wrong cause.

**What is admissible:** a **descriptive, within-mode** report of B0' against the AQE-on reference point, and a **stated-limitation** discussion of AQE complementarity. **What is INADMISSIBLE and is forbidden by this entry:** any pooled statistic across `aqe_mode`; any Wilcoxon, Cliff's δ or Holm-corrected comparison spanning AQE-on and AQE-off arms; any headline claim of the form "RL beats B0'" or "B0' beats RL"; and any substitution of B0' for B0 in the EXP-005 main comparison. **An EXP-005b that produced a pooled number would produce a number nobody may legitimately use, which is worse than not running it.**

**5 — Implementation readiness: NO DRIVER EXISTS.** `scripts/run_exp005.py:54` declares `ARMS = ("B0", "B1", "B2", "B4", "RL-s0", "RL-s1", "RL-s2")` — **seven arms, no B0'** — and its own header at `:19` states the reason: *"B3 is analytical only; **B0' belongs to EXP-005b**"*. The exclusion is deliberate, and the DEC-018B content contract that three validators enforce is written against that seven-arm set. **There is today no code path that executes a B0' TEST arm.**

`configs/baseline_b0_prime.yaml` **does** exist and freezes the configuration mechanically — its header records that it is `configs/baseline_b0.yaml` *"with exactly ONE value changed: `aqe_enabled` false -> true"*, introducing no tuning value. The **configuration** is ready; the **driver** is not.

**6 — THEREFORE THE EXECUTION AUTHORIZATION IS CONDITIONAL, AND IS NOT GRANTED BY THIS ENTRY.** Authorizing the execution of code that has not been written is precisely the defect DEC-030 §15's gate chain exists to prevent. Following that chain's shape, **EXP-005b execution may be authorized by a separate later decision once, and only once, ALL of the following hold:**

1. an EXP-005b driver exists that executes **B0' only** over the **7 frozen TEST instances** at **5 repetitions**, opening **no new TEST cell**;
2. it carries a content contract in the DEC-018B shape, so that filename alone never authorizes, and it refuses to run without an explicit Spark gate;
3. it writes `aqe_mode` into **every** manifest and refuses to emit any pooled statistic (§4);
4. its zero-Spark tests are green and the full validator chain still passes;
5. that later decision records worst-case counts (**35**), the ledger charge (**0** to SC6; 35 to EXP-005b's own ledger) and a clean preflight.

Until then: **`EXP-005b EXECUTION = NOT AUTHORIZED`** and **TEST remains SEALED**, exactly as DEC-018 Decision B left it.

**7 — TEST-seal discipline for the eventual execution.** The opened cells are the **same 7 frozen EXP-005 TEST instances** whose identity is pinned by `results/evaluation/exp005_instances.json` and `test_freeze.json`. **No new TEST cell is unsealed by EXP-005b, ever.** TEST re-seals on completion. No TEST metric may influence training or tuning (`docs/PLAN.md` line 163).

**8 — Exhaustively NOT permitted by this entry.** No execution of any kind. No TEST cell is opened now. No new TEST instance is ever added. No B0' substitution into EXP-005's pooled comparison. No pooled cross-mode statistic. No retraining, no Q update, no policy write. No amendment of `docs/PLAN.md`, SC6, `configs/baseline_b0.yaml` or `configs/baseline_b0_prime.yaml`. No edit to DEC-016's or DEC-017's recorded text. No EXP-008 execution.

**9 — What this entry does NOT decide.** Whether the EXP-005b driver should extend `run_exp005.py` or be a separate script (an implementation decision). Whether B3's analytic treatment should be revisited. Whether EXP-005b's 35 runs should appear in `docs/PLAN.md`'s register (PLAN is unchanged). Any EXP-009 matter — DEC-040 covers it. Whether AQE complementarity warrants a thesis chapter section of its own.

**Status.** **DECIDED.** EXP-005b scope is frozen at **B0' alone, 7 instances × 5 repetitions = 35 runs**, on a **separate AQE-on ledger**, **0 charged to SC6**. The **no-pooling rule and the runtime-adaptivity fairness defect are binding on any analysis**. **`EXP-005b EXECUTION = NOT AUTHORIZED`** — the authorization is **CONDITIONAL** on §6's five conditions, chief among them a driver that does not exist (`scripts/run_exp005.py:54` excludes B0' deliberately). `TEST = SEALED`. `SC6 cap = 500, NOT raised`. `SC6 ledger = 483 / 17, unchanged`. `EXP-008 execution authorization = NO`. `A5 = DISABLED`. `docs/PLAN.md = UNCHANGED`. Historical decisions (DEC-001 … DEC-026, DEC-030 … DEC-040) = **UNCHANGED**. Supervisor counter-signature: **PENDING** (conventional expectation only; never simulated; not a prerequisite under DEC-018 Decision A). **NO SUPERVISOR HAS REVIEWED THIS ENTRY.** A future review is a new entry; this one is never rewritten. **This entry performs 0 Spark executions and trains nothing.**
