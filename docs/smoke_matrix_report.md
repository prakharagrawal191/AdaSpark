# AdaSpark Smoke Matrix Report (Day 2)

Generated 2026-09-07T11:06:44.796651+00:00 — backend: native Windows + Python 3.11 + PySpark 3.5.9 + winutils 3.3.6 shim (DEC-007)

| Test | Name | Status | Detail | Seconds |
|---|---|---|---|---|
| K | HADOOP_HOME + winutils | PASS | C:\Users\prakh\hadoop; winutils 119296 bytes | 0.0 |
| K | bundled Hadoop client | PASS | pyspark 3.5.9; hadoop-client-runtime-3.3.4.jar | 0.0 |
| A0 | session startup time (info) | PASS | 2.82s | 0.0 |
| A | SparkSession creation | PASS | Spark 3.5.9 local[2], appId=local-1788779192649 | 0.0 |
| B | DataFrame creation | PASS | schema=struct<id:bigint,k:bigint,v:double> | 2.876 |
| C | count operation | PASS | count=100 (expected 100) | 0.814 |
| D | small aggregation | PASS | groups=10, sum(v)=618.750, sum of group sums=618.750 | 2.929 |
| E | Parquet write (small) | PASS | C:\Users\prakh\sparkrl_data\tmp\smoke\small.parquet (4096 bytes) | 1.121 |
| F | Parquet read (small) | PASS | count=100 | 0.459 |
| G | Parquet round-trip 1M | PASS | count=1000000, sum(id) src=62437500.000000 back=62437500.000000, sum(v) src=499999500000.0 back=499999500000.0 | 2.516 |
| J | clean Spark shutdown | PASS | stopped app local-1788779192649 | 1.062 |
| H | event-log generation | PASS | local-1788779192649, 977382 bytes | 0.0 |
| I | event-log discovery + strict JSON | PASS | 240 events parsed, 0 bad lines; first=SparkListenerLogStart, last=SparkListenerApplicationEnd | 0.0 |

**Verdict: PASS**

Event log format: uncompressed JSON lines (`spark.eventLog.compress=false`).
