# V4 C3-B — Production Persistence

C3-B turns the C3-A provider-neutral boundary into concrete durable adapters: PostgreSQL JSONB for dataset/session/monitoring/saved-intelligence documents and S3-compatible object storage for uploaded dataset files.

Production requires `V4_PERSISTENCE_MODE=external` plus `V4_DATABASE_URL`, `V4_OBJECT_STORE_BUCKET`, and `V4_OBJECT_STORE_REGION`. External mode never falls back to local runtime storage.

Because the existing dataframe engine consumes filesystem paths, remote dataset objects are materialized into a controlled temporary cache for profiling/analysis.

The existing authentication SQLite database is intentionally unchanged in this checkpoint and remains a separate migration boundary.
