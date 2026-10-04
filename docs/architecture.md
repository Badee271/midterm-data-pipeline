# Architecture

## Stages

1. **Discovery:** read path, size, and create a unique `run_id`.
2. **Router:** use Python Batch at or below `SMALL_FILE_THRESHOLD_MB`; use PySpark above it.
3. **Raw Load:** write every CSV row to `orders_raw` before quality rules. Each document carries `run_id`, `source_file`, `source_row_number`, `engine_used`, and `raw_record`.
4. **Transform & Quality:** normalize only deterministic values and retain all corrections in an audit trail.
5. **Classification:** route each row to `valid`, `corrected`, or `quarantine`.
6. **Final Load:** upsert valid/corrected records by stable business key `order_id`; store unrepairable records with error codes and raw data.
7. **Metrics:** write counters, throughput, configuration, and consistency checks to `reports/results.json`.

## Idempotency policy

`orders_raw` is historical by `run_id`; replaying a source creates a new raw run for traceability. Business state is idempotent because `orders_validated` has a unique index on `order_id` and uses `update_one(..., upsert=True)`. A replay therefore produces no new business key. `updated_count` and `unchanged_count` make the outcome observable.

## Spark notes

The Spark loader builds an explicit all-string `StructType` from the CSV header. This intentionally preserves dirty values in Raw. It writes a Map-valued `raw_record` with the MongoDB Spark Connector. The connector is passed to `spark-submit --packages` because it is a JVM dependency, not a Python package.
