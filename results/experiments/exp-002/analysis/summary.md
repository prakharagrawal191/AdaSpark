# EXP-002 Configuration-Sensitivity Study - Analysis Summary

- analysis version : exp002-analysis/v1
- generated (UTC)  : 2026-09-11T10:05:50.457948+00:00
- spec fingerprint : 9fb5cb51f74fe37f9883a8fdc27636926990d9a8528403fde70c97769b29303e
- grid fingerprint : 97d70dc18a1d5369928964201f2169fd0eebfb8c3c747001900a472885819ba1
- metric           : execution_time_s (execution_time_s is the frozen Day-3 runner clock with warm-up excluded; no other timing is substituted.)
- AQE              : OFF

## Execution

| planned | records | valid | invalid | missing |
|---|---|---|---|---|
| 208 | 208 | 189 | 19 | 0 |

Invalid breakdown: {'FAILED': 19}

## Per-panel configuration sensitivity

| family | scale | complete | n valid | spread (varied) | pooled noise CV | rep rank rho | sensitive |
|---|---|---|---|---|---|---|---|
| F1_agg | small | yes | 26 | 497.9% | 16.45% | 0.97 | YES |
| F1_agg | medium | yes | 26 | 366.9% | 26.53% | 0.97 | YES |
| F2_join | small | yes | 26 | 210.0% | 10.70% | 0.95 | YES |
| F2_join | medium | yes | 26 | 583.1% | 18.29% | 0.98 | YES |
| F3_rdd | small | yes | 25 | 158.7% | 30.07% | 0.55 | YES |
| F3_rdd | medium | NO | 8 | 49.9% | 40.69% | 0.40 | no |
| F5_mixed | small | yes | 26 | 183.9% | 25.24% | 0.98 | YES |
| F5_mixed | medium | yes | 26 | 424.7% | 28.92% | 0.90 | YES |

### F1_agg / small

B0 median (T_ref) = 22.347 s

| config | idx | n | median s | mean s | CV | vs B0 |
|---|---|---|---|---|---|---|
| B0 | ref | 2 | 22.347 | 22.347 | 0.082 | +0.0% |
| G-p2-sp16 | 0 | 2 | 2.587 | 2.587 | 0.022 | -88.4% |
| G-p2-sp32 | 1 | 2 | 3.439 | 3.439 | 0.115 | -84.6% |
| G-p2-sp64 | 2 | 2 | 6.042 | 6.042 | 0.184 | -73.0% |
| G-p2-sp128 | 3 | 2 | 12.528 | 12.528 | 0.074 | -43.9% |
| G-p4-sp16 | 4 | 2 | 2.146 | 2.146 | 0.082 | -90.4% |
| G-p4-sp32 | 5 | 2 | 2.712 | 2.712 | 0.121 | -87.9% |
| G-p4-sp64 | 6 | 2 | 4.003 | 4.003 | 0.055 | -82.1% |
| G-p4-sp128 | 7 | 2 | 8.860 | 8.860 | 0.050 | -60.4% |
| G-p8-sp16 | 8 | 2 | 2.095 | 2.095 | 0.122 | -90.6% |
| G-p8-sp32 | 9 | 2 | 2.310 | 2.310 | 0.034 | -89.7% |
| G-p8-sp64 | 10 | 2 | 3.853 | 3.853 | 0.124 | -82.8% |
| G-p8-sp128 | 11 | 2 | 8.926 | 8.926 | 0.251 | -60.1% |

- spread 4.9790 >= 0.10 and exceeds pooled within-configuration noise 0.1645

### F1_agg / medium

B0 median (T_ref) = 36.670 s

| config | idx | n | median s | mean s | CV | vs B0 |
|---|---|---|---|---|---|---|
| B0 | ref | 2 | 36.670 | 36.670 | 0.272 | +0.0% |
| G-p2-sp16 | 0 | 2 | 6.325 | 6.325 | 0.102 | -82.8% |
| G-p2-sp32 | 1 | 2 | 8.325 | 8.325 | 0.284 | -77.3% |
| G-p2-sp64 | 2 | 2 | 10.112 | 10.112 | 0.217 | -72.4% |
| G-p2-sp128 | 3 | 2 | 21.800 | 21.800 | 0.291 | -40.6% |
| G-p4-sp16 | 4 | 2 | 5.777 | 5.777 | 0.241 | -84.2% |
| G-p4-sp32 | 5 | 2 | 5.297 | 5.297 | 0.128 | -85.6% |
| G-p4-sp64 | 6 | 2 | 7.453 | 7.453 | 0.161 | -79.7% |
| G-p4-sp128 | 7 | 2 | 13.633 | 13.633 | 0.178 | -62.8% |
| G-p8-sp16 | 8 | 2 | 4.692 | 4.692 | 0.231 | -87.2% |
| G-p8-sp32 | 9 | 2 | 4.669 | 4.669 | 0.055 | -87.3% |
| G-p8-sp64 | 10 | 2 | 5.893 | 5.893 | 0.128 | -83.9% |
| G-p8-sp128 | 11 | 2 | 11.340 | 11.340 | 0.136 | -69.1% |

- spread 3.6687 >= 0.10 and exceeds pooled within-configuration noise 0.2653

### F2_join / small

B0 median (T_ref) = 2.215 s

| config | idx | n | median s | mean s | CV | vs B0 |
|---|---|---|---|---|---|---|
| B0 | ref | 2 | 2.215 | 2.215 | 0.073 | +0.0% |
| G-p2-sp16 | 0 | 2 | 0.748 | 0.748 | 0.034 | -66.2% |
| G-p2-sp32 | 1 | 2 | 0.899 | 0.899 | 0.072 | -59.4% |
| G-p2-sp64 | 2 | 2 | 1.186 | 1.186 | 0.099 | -46.4% |
| G-p2-sp128 | 3 | 2 | 1.672 | 1.672 | 0.099 | -24.5% |
| G-p4-sp16 | 4 | 2 | 0.598 | 0.598 | 0.019 | -73.0% |
| G-p4-sp32 | 5 | 2 | 0.743 | 0.743 | 0.018 | -66.4% |
| G-p4-sp64 | 6 | 2 | 0.871 | 0.871 | 0.030 | -60.7% |
| G-p4-sp128 | 7 | 2 | 1.173 | 1.173 | 0.047 | -47.0% |
| G-p8-sp16 | 8 | 2 | 0.539 | 0.539 | 0.057 | -75.7% |
| G-p8-sp32 | 9 | 2 | 0.586 | 0.586 | 0.031 | -73.6% |
| G-p8-sp64 | 10 | 2 | 0.791 | 0.791 | 0.087 | -64.3% |
| G-p8-sp128 | 11 | 2 | 1.143 | 1.143 | 0.212 | -48.4% |

- spread 2.1004 >= 0.10 and exceeds pooled within-configuration noise 0.1070

### F2_join / medium

B0 median (T_ref) = 16.127 s

| config | idx | n | median s | mean s | CV | vs B0 |
|---|---|---|---|---|---|---|
| B0 | ref | 2 | 16.127 | 16.127 | 0.120 | +0.0% |
| G-p2-sp16 | 0 | 2 | 3.511 | 3.511 | 0.139 | -78.2% |
| G-p2-sp32 | 1 | 2 | 3.594 | 3.594 | 0.081 | -77.7% |
| G-p2-sp64 | 2 | 2 | 4.977 | 4.977 | 0.032 | -69.1% |
| G-p2-sp128 | 3 | 2 | 9.926 | 9.926 | 0.069 | -38.5% |
| G-p4-sp16 | 4 | 2 | 2.026 | 2.026 | 0.207 | -87.4% |
| G-p4-sp32 | 5 | 2 | 2.244 | 2.244 | 0.061 | -86.1% |
| G-p4-sp64 | 6 | 2 | 2.909 | 2.909 | 0.100 | -82.0% |
| G-p4-sp128 | 7 | 2 | 6.083 | 6.083 | 0.163 | -62.3% |
| G-p8-sp16 | 8 | 2 | 1.453 | 1.453 | 0.117 | -91.0% |
| G-p8-sp32 | 9 | 2 | 1.626 | 1.626 | 0.193 | -89.9% |
| G-p8-sp64 | 10 | 2 | 2.443 | 2.443 | 0.215 | -84.9% |
| G-p8-sp128 | 11 | 2 | 5.150 | 5.150 | 0.358 | -68.1% |

- spread 5.8315 >= 0.10 and exceeds pooled within-configuration noise 0.1829

### F3_rdd / small

B0 median (T_ref) = 25.109 s

| config | idx | n | median s | mean s | CV | vs B0 |
|---|---|---|---|---|---|---|
| B0 | ref | 2 | 25.109 | 25.109 | 0.672 | +0.0% |
| G-p2-sp16 | 0 | 2 | 13.489 | 13.489 | 0.071 | -46.3% |
| G-p2-sp32 | 1 | 2 | 16.217 | 16.217 | 0.186 | -35.4% |
| G-p2-sp64 | 2 | 2 | 14.299 | 14.299 | 0.117 | -43.1% |
| G-p2-sp128 | 3 | 2 | 15.461 | 15.461 | 0.103 | -38.4% |
| G-p4-sp16 | 4 | 1 | 12.645 | 12.645 | n/a | -49.6% |
| G-p4-sp32 | 5 | 2 | 12.616 | 12.616 | 0.160 | -49.8% |
| G-p4-sp64 | 6 | 2 | 13.926 | 13.926 | 0.135 | -44.5% |
| G-p4-sp128 | 7 | 2 | 12.404 | 12.404 | 0.044 | -50.6% |
| G-p8-sp16 | 8 | 2 | 16.411 | 16.411 | 0.046 | -34.6% |
| G-p8-sp32 | 9 | 2 | 32.093 | 32.093 | 0.480 | +27.8% |
| G-p8-sp64 | 10 | 2 | 17.178 | 17.178 | 0.143 | -31.6% |
| G-p8-sp128 | 11 | 2 | 16.571 | 16.571 | 0.061 | -34.0% |

- spread 1.5873 >= 0.10 and exceeds pooled within-configuration noise 0.3007

### F3_rdd / medium

B0 median (T_ref) = n/a

| config | idx | n | median s | mean s | CV | vs B0 |
|---|---|---|---|---|---|---|
| B0 | ref | 0 | n/a | n/a | n/a | n/a |
| G-p2-sp16 | 0 | 0 | n/a | n/a | n/a | n/a |
| G-p2-sp32 | 1 | 0 | n/a | n/a | n/a | n/a |
| G-p2-sp64 | 2 | 0 | n/a | n/a | n/a | n/a |
| G-p2-sp128 | 3 | 0 | n/a | n/a | n/a | n/a |
| G-p4-sp16 | 4 | 0 | n/a | n/a | n/a | n/a |
| G-p4-sp32 | 5 | 0 | n/a | n/a | n/a | n/a |
| G-p4-sp64 | 6 | 0 | n/a | n/a | n/a | n/a |
| G-p4-sp128 | 7 | 0 | n/a | n/a | n/a | n/a |
| G-p8-sp16 | 8 | 2 | 37.225 | 37.225 | 0.424 | n/a |
| G-p8-sp32 | 9 | 2 | 38.157 | 38.157 | 0.523 | n/a |
| G-p8-sp64 | 10 | 2 | 29.194 | 29.194 | 0.209 | n/a |
| G-p8-sp128 | 11 | 2 | 25.450 | 25.450 | 0.152 | n/a |

- panel incomplete: 9 configuration(s) without 1 valid observation(s): ['B0', 'G-p2-sp16', 'G-p2-sp32', 'G-p2-sp64', 'G-p2-sp128', 'G-p4-sp16', 'G-p4-sp32', 'G-p4-sp64', 'G-p4-sp128']

### F5_mixed / small

B0 median (T_ref) = 3.904 s

| config | idx | n | median s | mean s | CV | vs B0 |
|---|---|---|---|---|---|---|
| B0 | ref | 2 | 3.904 | 3.904 | 0.281 | +0.0% |
| G-p2-sp16 | 0 | 2 | 2.298 | 2.298 | 0.180 | -41.1% |
| G-p2-sp32 | 1 | 2 | 2.458 | 2.458 | 0.243 | -37.0% |
| G-p2-sp64 | 2 | 2 | 2.607 | 2.607 | 0.209 | -33.2% |
| G-p2-sp128 | 3 | 2 | 3.284 | 3.284 | 0.273 | -15.9% |
| G-p4-sp16 | 4 | 2 | 1.522 | 1.522 | 0.230 | -61.0% |
| G-p4-sp32 | 5 | 2 | 1.683 | 1.683 | 0.206 | -56.9% |
| G-p4-sp64 | 6 | 2 | 1.774 | 1.774 | 0.252 | -54.6% |
| G-p4-sp128 | 7 | 2 | 2.081 | 2.081 | 0.255 | -46.7% |
| G-p8-sp16 | 8 | 2 | 1.157 | 1.157 | 0.231 | -70.4% |
| G-p8-sp32 | 9 | 2 | 1.238 | 1.238 | 0.321 | -68.3% |
| G-p8-sp64 | 10 | 2 | 1.220 | 1.220 | 0.224 | -68.7% |
| G-p8-sp128 | 11 | 2 | 1.488 | 1.488 | 0.220 | -61.9% |

- spread 1.8391 >= 0.10 and exceeds pooled within-configuration noise 0.2524

### F5_mixed / medium

B0 median (T_ref) = 32.759 s

| config | idx | n | median s | mean s | CV | vs B0 |
|---|---|---|---|---|---|---|
| B0 | ref | 2 | 32.759 | 32.759 | 0.332 | +0.0% |
| G-p2-sp16 | 0 | 2 | 11.400 | 11.400 | 0.380 | -65.2% |
| G-p2-sp32 | 1 | 2 | 11.216 | 11.216 | 0.284 | -65.8% |
| G-p2-sp64 | 2 | 2 | 10.648 | 10.648 | 0.068 | -67.5% |
| G-p2-sp128 | 3 | 2 | 21.654 | 21.654 | 0.289 | -33.9% |
| G-p4-sp16 | 4 | 2 | 5.297 | 5.297 | 0.047 | -83.8% |
| G-p4-sp32 | 5 | 2 | 6.310 | 6.310 | 0.145 | -80.7% |
| G-p4-sp64 | 6 | 2 | 6.252 | 6.252 | 0.009 | -80.9% |
| G-p4-sp128 | 7 | 2 | 10.786 | 10.786 | 0.110 | -67.1% |
| G-p8-sp16 | 8 | 2 | 4.833 | 4.833 | 0.335 | -85.2% |
| G-p8-sp32 | 9 | 2 | 4.127 | 4.127 | 0.160 | -87.4% |
| G-p8-sp64 | 10 | 2 | 4.475 | 4.475 | 0.194 | -86.3% |
| G-p8-sp128 | 11 | 2 | 7.896 | 7.896 | 0.172 | -75.9% |

- spread 4.2469 >= 0.10 and exceeds pooled within-configuration noise 0.2892

## Sensitivity gate

Criterion (H1/SC1, PLAN H1 / SC1 / section 33 / risk R2 (pre-registered)): relative spread of per-configuration median execution_time_s across the varied_only configuration set must be >= 10% and must exceed pooled within-configuration noise, on at least 2 workload families (any_scale).

**RESULT: PASS**

- 4 workload families (F1_agg, F2_join, F3_rdd, F5_mixed) show a configuration spread of at least 10% in median execution_time_s that also exceeds pooled within-configuration noise; the criterion requires 2.
- incomplete panels (not evaluable as sensitive): F3_rdd/medium

## Invalid / failed observations (recorded, never dropped)

| run_id | status | event log | error |
|---|---|---|---|
| exp002-f3-rdd-medium-s0-b0-r1 | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: J |
| exp002-f3-rdd-medium-s0-b0-r2 | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: J |
| exp002-f3-rdd-medium-s0-g-p2-sp128-r1 | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: J |
| exp002-f3-rdd-medium-s0-g-p2-sp128-r2 | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: J |
| exp002-f3-rdd-medium-s0-g-p2-sp16-r1 | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: J |
| exp002-f3-rdd-medium-s0-g-p2-sp16-r2 | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: J |
| exp002-f3-rdd-medium-s0-g-p2-sp32-r1 | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: J |
| exp002-f3-rdd-medium-s0-g-p2-sp32-r2 | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: J |
| exp002-f3-rdd-medium-s0-g-p2-sp64-r1 | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: J |
| exp002-f3-rdd-medium-s0-g-p2-sp64-r2 | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: J |
| exp002-f3-rdd-medium-s0-g-p4-sp128-r1 | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: J |
| exp002-f3-rdd-medium-s0-g-p4-sp128-r2 | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: J |
| exp002-f3-rdd-medium-s0-g-p4-sp16-r1 | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: J |
| exp002-f3-rdd-medium-s0-g-p4-sp16-r2 | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: J |
| exp002-f3-rdd-medium-s0-g-p4-sp32-r1 | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: J |
| exp002-f3-rdd-medium-s0-g-p4-sp32-r2 | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: J |
| exp002-f3-rdd-medium-s0-g-p4-sp64-r1 | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: J |
| exp002-f3-rdd-medium-s0-g-p4-sp64-r2 | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: J |
| exp002-f3-rdd-small-s0-g-p4-sp16-r1 | FAILED | COMPLETE | Py4JJavaError: An error occurred while calling z:org.apache.spark.api.python.PythonRDD.collectAndServe. : org.apache.spark.SparkException: J |
