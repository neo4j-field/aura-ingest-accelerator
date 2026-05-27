# Architecture: aura-ingest-accelerator

## Design Philosophy

The `aura-ingest-accelerator` is designed to be a lightweight, modular framework for high-performance data ingestion into Neo4j Aura. It prioritizes:
- **Streaming**: Data is processed in batches to keep memory usage low, even for large datasets.
- **Modularity**: New data sources can be added by subclassing `BaseSource`.
- **Idempotency**: All imports use `MERGE` patterns to ensure they are safe to re-run.
- **Resilience**: Exponential backoff retries handle transient Neo4j/Aura connectivity issues.

## Data Flow

1.  **Configuration**: `main.py` loads import jobs from `config.yaml`.
2.  **Source Initialization**: A `BaseSource` (e.g., `BigQuerySource`, `GCSSource`) is instantiated for each job.
3.  **Batching**: `Neo4jImporter` requests batches of rows from the source.
4.  **Transformation**: (Optional) Rows are passed through a registered transform function.
5.  **Ingestion**: Batches are executed in Neo4j via `UNWIND $rows AS row`.

## Components

| Component | Responsibility | Key Logic |
| :--- | :--- | :--- |
| `main.py` | CLI entry point, config loading, and source factory. | `run_poc()`, `build_source()`, `TRANSFORMS` |
| `importer.py` | Connectivity, batching, and retry logic. | `Neo4jImporter`, `run_import()`, `_run_batch_with_retry()` |
| `sources/base.py` | Abstract base class for all data sources. | `BaseSource`, `get_batches()` |
| `sources/bigquery_source.py` | Streams data from BigQuery using lazy iterators. | `BigQuerySource` |
| `sources/gcs_source.py` | Streams data from GCS CSV blobs. | `GCSSource` |
| `config.yaml` | Defines import jobs, Cypher, and source parameters. | `imports` list |

## Configuration & Secrets

- **Runtime Config**: `config.yaml`
- **Secrets**: `.env` (Neo4j credentials, GCP service account keys)
- **Environment**: Managed via `uv` and `pyproject.toml`.
