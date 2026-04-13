# Neo4j AuraDB — POC Jumpstart Kit

A lightweight, modular batch import toolkit for getting data into AuraDB quickly during a proof of concept. Designed for GCP environments (BigQuery, GCS) with private-link connectivity.

> **Not an ETL framework.** This is intentionally minimal — a clean starting point you can adapt, not a platform you have to learn.

---

## What's Included

```
├── importer.py                  # Core Neo4j batch importer
├── main.py                      # Example import runs — start here
├── poc_walkthrough.ipynb        # Step-by-step Jupyter walkthrough
├── sources/
│   ├── base.py                  # BaseSource ABC — extend this for new sources
│   ├── bigquery_source.py       # Stream rows from a BigQuery query
│   └── gcs_source.py            # Stream rows from a GCS CSV file
├── config.yaml                  # All import jobs — queries, Cypher, batch 
├── env.sample                   # Copy to .env and fill in your values
└── .gitignore
```

---

## Quickstart

### 1. Prerequisites

- Python 3.11+
- A running AuraDB instance (URI, username, password from the Aura console)
- GCP credentials with access to your BigQuery dataset and/or GCS bucket

### 2. Set Up the Environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install neo4j python-dotenv google-cloud-bigquery google-cloud-storage db-dtypes
```

### 3. Configure Credentials

```bash
cp env.sample .env
# Edit .env with your AuraDB URI and GCP credentials
```

For AuraDB, always use the `neo4j+s://` URI scheme (TLS is required):

```
NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io:7687
```

For private-link endpoints, use your private DNS alias instead:

```
NEO4J_URI=neo4j+s://your-private-link-dns:7687
```

### 4. Run the Walkthrough

Open `poc_walkthrough.ipynb` in Jupyter or Vertex AI Notebooks and run cells top to bottom. It will verify connectivity, preview your data, and run a test import before going full scale.

Or run directly:

```bash
python main.py
```

---

## How It Works

### Configuration

All import jobs are defined in config.yaml — queries, Cypher, source details, and batch sizes. Credentials stay in .env. This is the only file customers need to edit for a typical POC.

```yaml
yamlimports:
  - name: "Client Nodes"
    source: bigquery
    query: >
      SELECT id, name, email FROM `your-project.your-dataset.users`
    cypher: |
      UNWIND $rows AS row
      MERGE (p:ClientNode {id: row.id})
      SET p.name = row.name
    batch_size: 1000
```

Each job entry supports:
| Key | Required | Description |
|---|---|---|
name | - | for logging output
source |✅ |bigquery or gcs
query | ✅ |(BigQuery)Standard SQL query
bucket / blob| ✅ |(GCS)GCS bucket name and file path
cypher |✅ |Cypher using UNWIND $rows AS row
batch_size | — | Rows per transaction (default: 1000)
transform | — | Name of a transform function defined in main.py

### The Importer

`Neo4jImporter` handles the connection, batching, retries, and summary logging. All your Cypher queries use the `UNWIND $rows AS row` pattern — the importer passes each batch as `{"rows": [...]}`.

```python
f# Run all jobs defined in config.yaml
python main.py

# Or point at a different config file
from main import run_poc
run_poc("config_staging.yaml")
```

### Adding a Transform

Define a function in main.py, register it in the TRANSFORMS dict, then reference it by name in config.yaml:

```yaml
- name: "Parts"
  source: gcs
  transform: transform_part_row
  ...
```

```python
# main.py
def transform_part_row(row):
    if not row.get("partnum"):
        return None  # skip rows with no ID
    return {**row, "partnum": row["partnum"].upper()}

TRANSFORMS = {"transform_part_row": transform_part_row}
```

### Adding a New Data Source

Subclass `BaseSource` and implement `get_batches()`:

```python
from sources.base import BaseSource

class MyCustomSource(BaseSource):
    def get_batches(self, batch_size: int):
        # yield lists of dicts
        ...
```

---

## Data Sources

| Source | Class | Notes |
|---|---|---|
| BigQuery | `BigQuerySource(query, project_id=None)` | Uses ADC. `query_job.result()` is a lazy iterator — rows are not loaded into memory all at once. |
| GCS CSV | `GCSSource(bucket_name, blob_name)` | Downloads full blob before parsing. Fine for POC-scale files. |

**GCP Authentication:** Both sources use [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials). Set `GOOGLE_APPLICATION_CREDENTIALS` in `.env` to point at a service account key file, or run `gcloud auth application-default login` for local development.

**Required IAM roles:**
- BigQuery: `BigQuery Data Viewer` + `BigQuery Job User`
- GCS: `Storage Object Viewer`

---

## Private-Link Notes

If your AuraDB instance is on a private link:

1. Confirm the private DNS alias resolves from your compute environment before running anything
2. `Neo4jImporter.__init__()` calls `verify_connectivity()` immediately on startup — you'll get a clear error at that point rather than a timeout mid-import
3. On Vertex AI Notebooks, confirm VPC peering to the AuraDB region is active
4. The `neo4j+s://` scheme is required regardless of whether you're on public or private endpoints

---

## Configuration Reference

| Variable | Required | Description |
|---|---|---|
| `NEO4J_URI` | ✅ | AuraDB connection URI. Must use `neo4j+s://` scheme. |
| `NEO4J_USER` | ✅ * | Database username (default: `neo4j`) |
| `NEO4J_PASSWORD` | ✅ * | Database password |
| `NEO4J_TOKEN` | — | Bearer token. If set, takes precedence over user/password. |
| `GOOGLE_APPLICATION_CREDENTIALS` | — | Path to GCP service account key JSON. Optional if using ADC. |

*`NEO4J_USER` + `NEO4J_PASSWORD` are required unless `NEO4J_TOKEN` is set.

---

## Indexing

Create indexes on any property used in a `MERGE` before you run your import. Without them, every `MERGE` performs a full label scan — at POC scale this is slow, at production scale it can stall the import entirely.

Use `IF NOT EXISTS` so the statements are safe to re-run:

```cypher
CREATE INDEX client_node_id IF NOT EXISTS FOR (p:ClientNode) ON (p.id);
CREATE INDEX supplier_code  IF NOT EXISTS FOR (d:Supplier)    ON (d.supplierCode);
```

Run these in the AuraDB Browser or via a setup script before calling `run_import()`. You can verify what's active at any time with:

```cypher
SHOW INDEXES;
```

**Rule of thumb:** any property that appears in a `MERGE (n:Label {property: value})` clause needs an index. Properties only referenced in `SET` do not (necessarily).

---

## Extending This Kit

As you encounter new data sources in future POCs, add them to `sources/` following the `BaseSource` pattern. Some common candidates:

- `PostgresSource` — SQLAlchemy-based, works with any SQL database
- `S3Source` — mirrors `GCSSource`, swap in `boto3`
- `LocalCSVSource` — useful for quick desktop data loads
- `RestApiSource` — paginated GET with configurable auth

The `importer.py` and Cypher query pattern stay the same regardless of source.