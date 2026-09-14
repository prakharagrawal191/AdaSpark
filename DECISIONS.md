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
