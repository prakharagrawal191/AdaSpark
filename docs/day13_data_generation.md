# Day 13 Data Generation

## Purpose

Provide a reproducible, deterministic synthetic-data substrate for later Spark workloads. Day 13 produces the data generator, canonical schema, scale ladder, Zipf skew, checksums, and manifests. It does **not** implement workload families (Day 14+) or run experiments.

## Canonical Schema

One reusable schema (`datagen-v1`) with two tables — `orders` and `lineitem` — from which later workload families derive views. No per-workload schemas are created.

### orders

| Column | Type | Meaning | Nullable | Domain | Rule |
|--------|------|---------|----------|--------|------|
| order_key | long | Primary key, dense | NO | [0, N_orders) | row index |
| cust_key | long | Customer key — skew driver | NO | [0, K_cust) | Zipf(s, K_cust) from seeded stream |
| order_day | int | Day-of-year | NO | [0, 365) | (order_key * 2654435761 + seed) % 365 |

### lineitem

| Column | Type | Meaning | Nullable | Domain | Rule |
|--------|------|---------|----------|--------|------|
| line_key | long | Primary key, dense | NO | [0, N_lineitem) | row index |
| order_key | long | FK into orders — join-skew driver | NO | [0, N_orders) | Zipf(s, N_orders) from seeded stream, mod N_orders |
| part_key | long | Part key — uniform contrast | NO | [0, P_part) | uniform int from stream |
| quantity | int | Line quantity | NO | [1, 50] | uniform int from stream |
| extended_price | double | Line price | NO | > 0 | quantity * (10.0 + (part_key % 90)) |

## Scale Ladder

| Scale | Lineitem rows | Target size | Research ladder |
|-------|---------------|-------------|-----------------|
| micro | 5,000 | fixture-only | No (test fixture only) |
| small | 3,000,000 | ~0.3 GB | Yes |
| medium | 10,000,000 | ~1.0 GB | Yes |
| large | 30,000,000 | ~3.0 GB | Yes |

## Scale Ladder

| Scale | Lineitem rows | Target size | Research ladder |
|-------|---------------|-------------|-----------------|
| micro | 5,000 | fixture-only | No (test fixture only) |
| small | 3,000,000 | ~0.3 GB | Yes |
| medium | 10,000,000 | ~1.0 GB | Yes |
| large | 30,000,000 | ~3.0 GB | Yes |

Lineitem:orders row ratio = 4:1. `micro` is fixture-only and not part of the research ladder. Actual output sizes are recorded in each dataset manifest.

### Scale row target derivation

Row counts come from the frozen PLAN.md §11 target sizes (0.3 / 1.0 / 3.0 GB) converted to lineitem row counts using the generator convention **lineitem rows : orders rows = 4 : 1** and an approximate per-row raw footprint. These are the **row-count anchors** the generator implements; Parquet-compressed on-disk size is recorded per dataset in the manifest and inventory.
Lineitem:orders row ratio = 4:1. `micro` is fixture-only and not part of the research ladder. Actual output sizes are recorded in each dataset manifest.
Schema fingerprint: SHA-256 over the canonical DDL string `table(col:type,...)@datagen-v1`.
## Generation Algorithm

1. Build `GenerationSpec(table, scale, rows, seed, skew, key_cardinality, part_cardinality, chunk_rows)`.
2. For each row index `i` in `[0, rows)`:


## Chunking / Memory Strategy

Generate in chunks (default 100,000 rows). Each chunk:

1. Materialize rows as a list of tuples (in-memory, bounded by chunk size).
2. Fold the canonical checksum contribution for the chunk.
3. Write as a Spark DataFrame to the output directory.
4. Discard the list and DataFrame.
5. Move to the next chunk.

Peak memory is O(chunk_rows), independent of total N. A 3 GB dataset is never held entirely in RAM. Chunks are appended to a single Parquet directory so the full dataset is readable as one table.

## Checksum Definition

## Manifest Schema

`DatasetManifest` (JSON-serializable, sorted keys):

| Field | Type | Description |
|-------|------|-------------|
| dataset_id | str | Human-readable dataset identifier |
| generator_version | str | `datagen-v1` |
| schema_version | str | `datagen-v1` |
| schema_fingerprint | str | SHA-256 of canonical DDL |
| scale | str | micro / small / medium / large |
| table | str | orders / lineitem |
| row_count | int | Number of rows |
| seed | int | Generation seed |
| zipf_parameter | float | Skew parameter s |
| key_cardinality | int | Key domain size |
| file_format | str | parquet |
| file_count | int | Number of Parquet part files |
| total_bytes | int | Sum of Parquet file sizes |
| checksum | str | FNV-1a 64-bit hex |
| generation_fingerprint | str | SHA-256 over spec identity |
| code_version | str | Generator code version (e.g., git hash) |
| generation_timestamp | str | ISO-8601 UTC — metadata only, never part of identity |

## Reproducibility Procedure

1. Choose `GenerationSpec` (table, scale, seed, skew, cardinalities, chunk_rows).
2. Generate → Parquet + checksum + manifest.
3. Record `generation_fingerprint` and `checksum` in the experiment manifest.
4. To reproduce: use the same `GenerationSpec`. The canonical checksum must match.

Changing **one** parameter (seed or skew) changes the fingerprint and checksum.

## Validation

Reusable validation functions (`sparkrl.datagen.validate`):

- `validate_spec_rows`: row-level domain/range/null checks on a head sample.
- `skew_direction_ok`: top-decile share > 10% for `s > 0` (statistical, not exact-frequency).
- `regeneration_checksum`: full-spec canonical checksum (chunk-size free).
- `full_validation`: aggregates row rules + skew sanity + manifest consistency.
- `validate_manifest`: cross-checks manifest identity against live spec + checksum.

Zipf validation is statistical: key domain correct, skew direction correct, reproducible under seed. Exact per-key frequencies are **not** required (sampling variation).

## Git / Data Storage Policy

- **In Git**: schema definitions, generation specs, manifests (where appropriate), tiny fixtures, validation code, documentation.
- **Not in Git**: large generated Parquet datasets, temporary generator output, local experiment data.

`.gitignore` excludes `data/**` (bulk data lives in the external `SPARKRL_DATA_ROOT`). The generator CLI `--out` must point outside Git-tracked directories.

Generated datasets are identified by content checksum + manifest, not by filesystem path or timestamp.
Canonical content checksum: FNV-1a 64-bit over the per-row encoding `col|col|...` (floats `repr`'d, ints/strings `str`'d), joined by `\n`, folded in row-index order.

The checksum is over canonical row content, **not** over Parquet bytes (which embed writer metadata and may differ across writers/versions). The canonical checksum is the reproducibility anchor.

Checksum result: `{"fnv1a_hex": "<16-hex-digit>", "row_count": N}`.
   - Replay the seeded RNG stream from draw 0 to the row's draw offset (orders: 1 draw; lineitem: 3 draws).
   - Draw Zipf keys and uniform values per the schema rules.
3. The row is fully determined by `(i, spec)` — chunking only slices the index range.