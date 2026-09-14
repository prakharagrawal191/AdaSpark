# Day 32 — Static-Configuration Convergence and State-Space Coverage

**Status:** research analysis, zero Spark executions.
**Scope:** read-only over frozen artifacts. No protocol, policy, config, or DEC
status was modified. No TEST observation data was read.
**Authority:** this document records findings. It decides nothing. Where it
identifies a specification gap or a ledger error, the correction is a governance
action that is *named here and not performed here*.

---

## 0. Evidence levels used throughout

| Level | Meaning |
|---|---|
| **L1** | Directly specified in `docs/PLAN.md` or `DECISIONS.md` |
| **L2** | Derived deterministically/mathematically from L1 facts |
| **L3** | An implementation choice living only in code, not authorized by PLAN/DEC |

Every **L3** item is disclosed explicitly. L3 is not an accusation — much of it is
necessary and some is disclosed by the repository itself. It is marked so that no
implementation choice is read as a specified one.

---

## 1. Static-configuration convergence

### 1.1 B1

| Property | Value | Level |
|---|---|---|
| Selected config | `G-p8-sp16` | L2 (`results/evaluation/baseline_selection.json:138`) |
| Selection split | `validation` | L2 (`:717`), `contains_test_data: false` (`:688`) |
| Metric / statistic | `execution_time_s` / `median`, `lower_is_better` | L1 (PLAN:180) |
| Tie-break | `lowest_grid_index` | **L3** — the artifact itself states "PLAN freezes no tie-break rule for B1/B2" (`:720`) |
| Validation median | 2.381767 s | L2 |

**B1 is the best *eligible* candidate, not the lowest-median candidate.** Eight of
twelve candidates were ruled ineligible for lacking a usable observation on
`F3_rdd/medium/seed3`. Among the excluded was `G-p4-sp16`, whose validation median
was **1.754953 s — lower than the winner's 2.381767 s**. The gate that excluded it,
`MIN_USABLE_PER_CELL = 1` (`src/sparkrl/evaluation/spec.py:80-84`), is **L3**: it
cites no PLAN authority and it is outcome-changing. It was pre-declared before the
measurements existed, which is the correct discipline, but it is a code-level rule.

**B1 is pinned by config NAME, not by config fingerprint.** The string `fingerprint`
occurs exactly once in `baseline_selection.json` (`:699`) and it is the *artifact's*
content hash (`0a0ecbe5…`, equal to `artifact_id`), not a SparkConfig hash. The
SparkConfig fingerprint `285ad990…` is **recomputed at resolve time** from the live
grid plus `configs/baseline_b0.yaml`. Nothing pins `baseline_b0.yaml`'s own
fingerprint in any evaluation artifact, so B1's resolved configuration is contingent
on that file remaining unchanged.

Two *different* 64-char fingerprints exist for the same config name:
`285ad990…` (`SparkConfig.fingerprint()`, includes app_name/driver_memory/warmup/
timeouts/seed) and `f857d8de…` (`ConfigPoint.fingerprint()`, 5 Spark knobs only,
`evaluation_spec.json:255`). "The" fingerprint is therefore ambiguous unless the
definition is named. This document uses the SparkConfig-level one and says so.

### 1.2 B3

| Property | Value | Level |
|---|---|---|
| Formula (as specified) | `partitions = clamp(input_GB × k, 16, 128)` | L1 (PLAN:155) |
| `k` | `1e9 / 134217728` = 7.450580596923828 | L1 (DEC-016 B, `DECISIONS.md:797`) |
| `input_GB` definition | manifest `total_bytes / 1e9`, compressed Parquet | L1 (`DECISIONS.md:789-792`) |
| Parallelism rule | physical core count clamped to {2,4,8} → 8 here | L1 text / **L3** implementation |
| Resolved | `G-p8-sp16`, fp `285ad990…` at every one of the 75 frozen cells | L2 |

Maximum dataset anywhere in the frozen universe **including TEST**:
**0.404228084 GB** (`skew1_large_s2`). Clamp product at that size:
`0.404228084 × 7.450580596923828 = 3.0117…` — far below the 16-partition floor.
B3 therefore returns 16 partitions at **all 75 cells** (train 24, validation 8,
test 43). With parallelism 8 that is `G-p8-sp16`, fingerprint-identical to B1.

### 1.3 B4

| Property | Value | Level |
|---|---|---|
| Selected config | `G-p8-sp16` | L2 (`results/evaluation/b4_selection.json`) |
| Artifact id | `0f87744727d1e12d…` | L2 |
| Split / TEST data | `train` / `contains_test_data: false` | L2 |
| Observations | 84 total, 84 usable, 0 failed | L2 |
| Winner median (normalised) | 0.1002 over **n = 12** usable | L2 |
| Runner-up | `G-p8-sp64` at 0.1443 over **n = 4** usable | L2 |

B4's selection rule (metric, statistic, eligibility, tie-break) was pre-registered
in `scripts/run_b4_search.py` **before** the search ran, under DEC-016 C / DEC-017.
The T_ref normalisation of its metric is authorized by DEC-017.

### 1.4 The convergence finding — and what it does *not* establish

> **Finding.** Three separately-specified non-RL selection methods — a validation
> sweep (B1), a rule heuristic (B3), and an equal-budget random search on TRAIN
> (B4) — all resolve to the same configuration, `G-p8-sp16`, with the identical
> SparkConfig fingerprint `285ad990e5bc5b8e691073f7a37e363ebb938b95fff945b64cab2f2820398681`.

This is an empirical and design finding about **this workload universe at this data
scale**. Four caveats are load-bearing and must travel with it:

1. **B3's agreement carries little independent evidential weight.** B3 does not
   *search*; it evaluates a formula whose output is clamped to the floor (16) with
   ~8× headroom before it could differ. It would have agreed with any method that
   selected 16 shuffle partitions. Counting it as a third independent vote
   overstates the evidence.
2. **B4's margin rests on unequal panels.** The winner's median is over 12
   observations; the runner-up's over 4. Uniform draws over 12 actions across 84
   runs give ~7 expected per action, so the winner drew favourably. The 44% margin
   is real but the runner-up's median is poorly estimated.
3. **B1 is not the lowest-median configuration on validation** (§1.1). A different
   eligibility rule would have produced a different B1.
4. **B3's identity to B1 is host-contingent.** Its parallelism comes from a live
   `psutil` physical-core probe at resolve time (`strategies.py:99-110, 131-135`),
   not a frozen constant. On a machine with fewer than 8 physical cores B3 would
   resolve to `G-p4-sp16` or `G-p2-sp16` and would **not** be fingerprint-identical
   to B1. `DECISIONS.md:796` asserts "24 physical cores" as prose; no code pins it.

**The convergence does NOT establish** that `G-p8-sp16` is globally optimal, that
it is optimal on TEST, that RL is better or worse than it, that the action space is
insensitive, or that the hypothesis is confirmed or refuted. Every one of those
requires EXP-005, which is not executed.

**Non-claim recorded for symmetry.** Over the 5 evidence-bearing states × 3 seeds =
15 greedy (state, seed) choices, the RL policies select action 8 (`G-p8-sp16`) in
**4**. Three of those four come from the single state `agg|S|le0` — the least-
evidenced state in the denominator (§3.3). This is a descriptive count. It is
**not** evidence that RL is right, wrong, better, or worse.

---

## 2. B3 provenance — the grid-snapping disclosure

### 2.1 The implementation choice

`b3_partitions()` (`src/sparkrl/evaluation/strategies.py:125-128`) computes
`clamp(gb*k, 16, 128)` and then **snaps** that value onto the nearest of
`(16, 32, 64, 128)`, ties breaking toward the smaller level:

```python
clamped = max(16, min(128, gb * B3_K))
return min((16, 32, 64, 128), key=lambda level: (abs(level - clamped), level))
```

**This snapping is L3.** Neither `snap`, `nearest`, `round`, `quantise` nor
`discretise` appears anywhere in PLAN or DECISIONS in connection with B3. PLAN:155
gives only the continuous clamp. DEC-016 Decision B goes no further than noting the
frozen action levels "are exactly the clamp bounds" (`DECISIONS.md:793-794`) — which
is itself imprecise, since only 16 and 128 are bounds; 32 and 64 are interior levels
the clamp never produces.

Three further L3 sub-choices sit inside it, each material:

- **nearest** rather than floor or ceiling. All three are consistent with PLAN:155
  and they give different answers at PLAN-nominal large (raw 22.35 → nearest 16,
  ceiling 32).
- **tie-break toward the smaller level.** `(abs(level - clamped), level)` returns 16
  at exactly `clamped == 24`. This single choice is what moves the divergence
  threshold from 2.147 GB to 3.221 GB.
- **confining B3 to the 12-action grid at all.** `grid.py:236-237` shows a baseline
  need not be a grid point (B0 is not).

### 2.2 A numerical error in signed DEC-017

`DECISIONS.md:880-883` states B3 "diverges from 16 partitions only above **2.147
GB**" and would need a cell "**5.3× larger than anything that exists**".

Those are the **raw formula's** figures. The **implemented** function does not
diverge until **3.221225472 GB** (= 24/k), a margin of **7.97×**, verified:

```
b3_partitions(2.1475)      -> 16      b3_partitions(3.221225472) -> 16
b3_partitions(3.0)         -> 16      b3_partitions(3.2213)      -> 32
```

The error is **conservative** — it understates B3's redundancy — so **no recorded
conclusion is harmed**. But the published number describes the specification, not
the code. Compounding this, the provenance string written into B3 artifacts is
`"clamp(input_GB * 7.450581, 16, 128)"` (`strategies.py:215-218`), with no snapping
term: an auditor reading a B3 manifest would re-derive 2.147 GB and never learn the
code applies 3.221 GB. **Correcting DEC-017 is a governance action; it is named here
and not performed here.**

### 2.3 The integrity note

> At the **actual frozen workload sizes** (0.0386 / 0.1320 / 0.4042 GB), the raw
> clamp products are 0.288 / 0.983 / 3.012 partitions — all below the floor — so the
> raw and snapped readings **both** return 16 and B3 is byte-identical to B1.
> **B3 = B1 is therefore valid for the executed and frozen workload universe, and
> that conclusion does not depend on the snapping choice.**
>
> At **PLAN's nominal large scale** the two readings **disagree**. PLAN:115 specifies
> "S ≈ 0.3 GB, M ≈ 1 GB, **L ≈ 3 GB** Parquet", and 3 GB falls strictly between the
> raw threshold (2.147 GB → 22 partitions, ≠ 16) and the snapped threshold (3.221 GB
> → 16). The implementation choice is therefore **disclosed because it is material to
> hypothetical larger volumes**, not because it changes any result obtained here.

The implementation was **not modified**.

### 2.4 Other B3 discrepancies recorded, not repaired

- `k` is quoted as **7.45** at `DECISIONS.md:797` and **7.4506** at `:880` ("stands
  unchanged" — against a value the prior entry never wrote). Code uses the exact
  quotient. No numerical consequence.
- `DECISIONS.md:802`'s "0.0386 / 0.1320 / 0.4042 GB (S/M/L)" lists only the skew=1
  datasets. The skew=1.5 datasets backing F4_ski — which supply 3 of the 7 EXP-005
  TEST instances — are smaller and unlisted (0.0311 / 0.1038 / 0.3114 GB). All still
  resolve to 16 partitions; the conclusion is unaffected, the inventory incomplete.
- **B3 carries no execution gate in code.** DEC-017 rules B3 "SPECIFIED but NOT
  EXECUTED as a TEST arm", yet `strategies.py:43` lists B3 in `IMPLEMENTED` and
  `resolve("B3")` returns a usable config with no `execution_gate` provenance key —
  unlike B0′, which carries an explicit "NOT AUTHORIZED" gate (`strategies.py:196`).
  Nothing mechanically prevents B3 from being queued as an arm. **Flagged as a
  safety gap; not modified.**
- `DECISIONS.md:855` ("B3 and B4 remain unimplementable") is a stale remnant inside
  the entry that supersedes it.

---

## 3. State-space coverage and the M8 limitation

### 3.1 The state universe, and how much of it is reachable

The frozen v1.5 abstraction is **30 states** = 5 workload classes × 3 size bins × 2
feedback bins (PLAN:123; `StateVector.space_size(SCHEMA_V15)` = 30). **L1/L2.**

The size-bin boundary is `_S_UPPER = 512 MiB = 0.5369 GB` (`state.py:52-54`,
implementing PLAN:123's "S<512MB, M 0.5–2GB, L>2GB").

**The largest dataset anywhere in the frozen universe is 0.4042 GB.** Therefore:

| Size bin | Cells in the entire frozen universe |
|---|---|
| **S** | **75** (train, validation *and* test) |
| M | **0** — never instantiated anywhere |
| L | **0** — never instantiated anywhere |

**`input_size_bin` is a constant across the whole study.** This is structural, not a
sampling artifact. It follows that:

- reachable states **universe-wide** = 5 classes × **1** bin × 2 feedback = **10**
- reachable states **in TRAIN** (F4_ski is a TEST-only family) = 4 × 1 × 2 = **8**
- **20 of the 30 states are unreachable by construction**, and 22 are unreachable
  from TRAIN. No training schedule of any length could have entered them.

Every state key in the Day-29 artifact contains `|S|`, confirming this directly.

### 3.2 What the 8 and the 5 actually are

The naive phrasing "8 states were instantiated during training" is **wrong**, and
the correction matters:

| Quantity | Count | What it is |
|---|---|---|
| Rows in each seed's final `q_table` | **8** | = the reachable TRAIN set (§3.1) |
| …of which pre-seeded from offline EXP-002 Q₀ **before any episode ran** | **4** | all four `\|le0\|` rows (`pairs_initialized: 4`) |
| …entered by no episode in any seed | **3** | `join\|S\|le0`, `mixed\|S\|le0`, `rdd_sort\|S\|le0` |
| States **ever entered** during training | **5** | — |
| **Evidence-bearing** (`D_all3`: visited ≥1 episode by **all three** seeds) | **5** | the M8 denominator |

"Evidence-bearing" means **visited by all three runs**, not "present in all three
tables" — all 8 rows are present in all three tables. The distinction is exactly
what the pre-registration was written to protect: an unvisited row still holds the
*shared* frozen Q₀ and would agree trivially.

### 3.3 M8, and why the denominator matters

**M8 = 0.2000**, threshold 0.70, recorded **FAIL** (`day29_policy_agreement.json`).
Numerator **1**, denominator **5**.

With a denominator of 5, one state is worth exactly **1/5 = 20 percentage points**.
The metric cannot take any value other than {0.0, 0.2, 0.4, 0.6, 0.8, 1.0}; the 0.70
threshold is not attainable at all — the nearest reachable values are 0.6 and 0.8.
Four of the five states would have to agree to pass.

**The pre-registration prevented a 2.5× inflation.** The transparency variant
`V1_D_union_any` (denominator = all 8 union rows) reports **exactly 0.5** — and
three of its four "agreeing" states are the never-visited Q₀ rows that agree for
free. Choosing that denominator after seeing the data would have reported 50%
instead of 20% on the strength of rows no run ever entered.

**The strongest caveat, and it is the repository's own.** The single unanimous state
`agg|S|le0` was entered exactly **once per seed**, each seed trying exactly **one**
action — and the actions they actually executed were **6, 1 and 0**, none of them
action 8. Its unanimous greedy action 8 therefore **rests on the shared frozen
EXP-002 Q₀ row, which no seed updated**. As `DAY30_MODE_GATE_AUDIT.md:220-226`
already records: **0 of 5 evidence-bearing states have a unanimous greedy action
that every seed actually ran.**

So M8's numerator is not a state where three replicates independently learned the
same answer. It is a state where three replicates shared an initialization and
barely touched it. The four *well-explored* states (11–24 episodes per seed) all
disagree.

### 3.4 The correct framing

> **The M8 statistic is constrained by sparse empirical coverage of the frozen state
> abstraction.**
>
> M8 = 0.20 is the recorded, pre-registered result and it stands. It is computed over
> a denominator of 5 evidence-bearing states — which is not a sampling shortfall but
> the near-complete reachable TRAIN subspace (§3.1), of which one state's agreement
> is attributable to shared initialization rather than to learning (§3.3).

This is a **limitation statement, not an invalidation**. M8 is not recomputed, its
denominator is not re-chosen, and the FAIL is not softened. Specifically **not
claimed**: that M8 is wrong, that RL is unstable, that RL is stable, that tabular
Q-learning converges or fails to converge, or that a larger state space would have
produced a different verdict.

### 3.5 L3 disclosures in the M8 computation

PLAN:275 freezes only the phrase "policies agree ≥ 70% (M8)" and the 0.70 threshold.
Everything operational is **L3**, and the artifact discloses this itself:

- the denominator `D_all3`, the unanimity numerator, and the four variants
- the greedy tie-break "lowest action index" (frozen Day-26 rule) — in neither PLAN
  nor DECISIONS
- `NO_FEEDBACK_BIN = "le0"` (`state.py:59`), a "Day-25 documented convention" that
  appears in neither PLAN nor DECISIONS and is load-bearing for this exact number
- `"fixed_before_any_policy_was_inspected": true` is **self-asserted**; it is not
  independently verifiable from version control

The pre-registration is the right discipline and it demonstrably worked (§3.3). It
is recorded here as L3 because PLAN did not specify it.

---

## 4. The unifying root cause

B3's degeneracy (§1.2) and the state-space collapse (§3.1) are **the same fact**:

> The size measure fed to both the B3 rule and `size_bin_of()` is **on-disk
> compressed Parquet bytes**. At that measure the entire frozen universe spans
> 0.031–0.404 GB, which is below B3's 16-partition clamp floor **and** below the
> state abstraction's S/M boundary.

`DECISIONS.md:812-817` already governs this choice for B3 and states it plainly:
PLAN's ladder "describes LOGICAL volume; at 10.8 bytes/row compressed Parquet,
37.5M rows is ~3 GB uncompressed and 0.404 GB on disk. Both measures are legitimate
and they differ ~7.4× in k. This entry pins the on-disk measure because it is the
one the system actually has."

**The datasets are not undersized relative to PLAN.** They are PLAN's nominal
logical volume, measured on disk after compression. What is *not* recorded anywhere
is that pinning the on-disk measure also collapses `input_size_bin` to a constant
and reduces the effective state space from 30 to 10 (8 in TRAIN). That consequence
is documented here for the first time.

**Open governance question (not decided here):** `DECISIONS.md:812` pins the on-disk
measure for **B3**. Whether that pin was ever intended to govern `StateVector`'s
size binning — where it removes an entire state dimension — has not been decided.

---

## 5. What remains unanswered

EXP-005 is still required to determine whether state-dependent RL choices provide
any measurable benefit over the static baselines on the frozen TEST split. Nothing
in this document speaks to that question, and nothing in it should be read as
anticipating the answer.

Consequences of §1 and §3 for how EXP-005 should be *interpreted* when it runs:

- **B3 is a duplicate arm** of B1 at this data scale, so SC3 ("not worse than
  heuristics") reduces in practice to RL vs B1. DEC-017 already rules B3 specified
  but not executed.
- **EXP-005 will not exercise a new state region.** All 43 TEST cells are size bin S
  (§3.1). Adding F4_ski raises the reachable set from 8 to 10 states, not beyond.
  EXP-006's "unseen scale" generalization claim should be checked against this: at
  the on-disk measure there is no unseen *size bin* anywhere in the project.
- **The RL-vs-static comparison is a comparison at one size bin**, and any claim of
  context-sensitivity rests on workload class and feedback bin only.

---

## 6. Provenance of this document

Zero Spark executions. No TEST observation data read. No file outside
`docs/research/` created or modified by this analysis. Verification was performed
directly against frozen artifacts and, in parallel, by independent read-only
checks; a planned adversarial-refutation pass did not complete,
so findings here that rest on a single unrefuted source are marked as such above by
their L1/L2/L3 level and file:line citation rather than by a verification verdict.

Artifacts read: `results/evaluation/baseline_selection.json`,
`results/evaluation/b4_selection.json`, `results/evaluation/evaluation_spec.json`,
`results/training/analysis/day29_policy_agreement.json`, the Day-14 dataset
manifests, `docs/PLAN.md`, `DECISIONS.md`, `docs/research/DAY30_MODE_GATE_AUDIT.md`,
and `src/sparkrl/{rl,evaluation,experiments}/`.
