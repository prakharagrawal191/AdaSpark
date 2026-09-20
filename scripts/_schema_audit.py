import json
import pathlib
from collections import Counter, defaultdict

P = pathlib.Path("results/experiments/exp-006/observations.jsonl")
rows = [json.loads(l) for l in P.read_text(encoding="utf-8").splitlines() if l.strip()]
print("TOTAL_ROWS", len(rows))

print("\n=== KEY PRESENCE / VALUES ===")
for k in sorted(set().union(*(r.keys() for r in rows))):
    present = sum(1 for r in rows if k in r)
    if present == len(rows):
        print(f"  {k}: present in all {len(rows)} rows")
    else:
        print(f"  {k}: present in {present}/{len(rows)} rows")

print("\n=== usable field ===")
for v, c in Counter(r["usable"] for r in rows).most_common():
    print(f"  usable={v} x {c}")

print("\n=== undefined field ===")
for v, c in Counter(r["undefined"] for r in rows).most_common():
    print(f"  undefined={v} x {c}")

print("\n=== event_log_status ===")
for v, c in Counter(r["event_log_status"] for r in rows).most_common():
    print(f"  event_log_status={json.dumps(v)} x {c}")

print("\n=== execution_time_source ===")
for v, c in Counter(r["execution_time_source"] for r in rows if r["execution_time_source"] is not None).most_common():
    print(f"  execution_time_source={json.dumps(v)} x {c}")

# classification
uses_def = [r for r in rows if r.get("undefined")]
uses_fail = [r for r in rows if (not r.get("usable")) and (not r.get("undefined"))]
uses_ok = [r for r in rows if r.get("usable")]

print("\n=== CLASSIFICATION ===")
print(f"  successful (usable=True): {len(uses_ok)}")
print(f"  failed (usable=False, undefined=False): {len(uses_fail)}")
print(f"  undefined (undefined=True): {len(uses_def)}")
print(f"  TOTAL: {len(uses_ok) + len(uses_fail) + len(uses_def)}")

# Check event_log_status composition
print("\n=== event_log_status x classification ===")
for st in sorted(set(r["event_log_status"] for r in rows)):
    n_ok = sum(1 for r in rows if r["event_log_status"] == st and r.get("usable"))
    n_fail = sum(1 for r in rows if r["event_log_status"] == st and (not r.get("usable")) and (not r.get("undefined")))
    n_undef = sum(1 for r in rows if r["event_log_status"] == st and r.get("undefined"))
    print(f"  event_log_status={json.dumps(st)}: usable={n_ok} failed={n_fail} undefined={n_undef}")

# execution_time_s by class
print("\n=== execution_time_s by class ===")
print("  successful: all populated:", all(r["execution_time_s"] is not None for r in uses_ok))
print("  failed: all null:", all(r["execution_time_s"] is None for r in uses_fail))
print("  undefined: all null:", all(r["execution_time_s"] is None for r in uses_def))

# Find failed rows examples
print("\n=== FAILED SPARK EXAMPLES (first 5) ===")
for r in uses_fail[:5]:
    print(f"--- queue_index={r['queue_index']} arm={r['arm']} family={r['family']} scale={r['scale']} seed={r['seed']} rep={r['rep']} ---")
    print(f"  usable={r['usable']} undefined={r['undefined']}")
    print(f"  event_log_status={r['event_log_status']}")
    print(f"  execution_time_s={r['execution_time_s']}")
    print(f"  execution_time_source={r['execution_time_source']}")
    print(f"  config_name={r['config_name']}")
    print(f"  config_fingerprint={r['config_fingerprint']}")
    err = r.get("error")
    if err:
        print(f"  error[:200]={err[:200]}")
    print()

print("\n=== FAILED event_log_status values ===")
for v, c in Counter(r["event_log_status"] for r in uses_fail).most_common():
    print(f"  {json.dumps(v)} x {c}")

print("\n=== FAILED execution_time_source values ===")
for v, c in Counter(r["execution_time_source"] for r in uses_fail if r["execution_time_source"] is not None).most_common():
    print(f"  {json.dumps(v)} x {c}")

# Per-arm
print("\n=== PER-ARM ===")
for arm in ("B0", "B2", "RL-s0", "RL-s1", "RL-s2"):
    a_ok = [r for r in uses_ok if r["arm"] == arm]
    a_fail = [r for r in uses_fail if r["arm"] == arm]
    a_undef = [r for r in uses_def if r["arm"] == arm]
    print(f"  {arm}: usable={len(a_ok)} failed={len(a_fail)} undefined={len(a_undef)} total={len(a_ok)+len(a_fail)+len(a_undef)}")

# Per-cell (family x scale x seed)
print("\n=== PER-CELL ===")
cells = defaultdict(lambda: {"usable": 0, "failed": 0, "undefined": 0, "total": 0})
for r in rows:
    key = (r["family"], r["scale"], r["seed"])
    cells[key]["total"] += 1
    if r.get("usable"):
        cells[key]["usable"] += 1
    elif r.get("undefined"):
        cells[key]["undefined"] += 1
    else:
        cells[key]["failed"] += 1

for key in sorted(cells):
    c = cells[key]
    if c["total"] > 0:
        print(f"  {key[0]}|{key[1]}|{key[2]}: total={c['total']} usable={c['usable']} failed={c['failed']} undefined={c['undefined']}")

# Error classification for failed
print("\n=== FAILED error classification ===")
cr = [r for r in uses_fail if r.get("error") and "ConnectionRefusedError" in r["error"]]
other = [r for r in uses_fail if not (r.get("error") and "ConnectionRefusedError" in r["error"])]
print(f"  ConnectionRefusedError: {len(cr)}")
print(f"  other errors: {len(other)}")
for r in other:
    print(f"    idx={r['queue_index']} arm={r['arm']} family={r['family']} scale={r['scale']} seed={r['seed']} error_hint={r['error'][:80] if r.get('error') else None}")
