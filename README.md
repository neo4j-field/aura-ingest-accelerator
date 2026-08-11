# Neo4j AuraDB — POC Jumpstart Kit

A lightweight, modular batch import toolkit for getting data into AuraDB quickly during a proof of concept. Designed for GCP environments (BigQuery, GCS) with private-link connectivity, plus Databricks Unity Catalog.

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
│   ├── gcs_source.py            # Stream rows from a GCS CSV file
│   └── databricks_source.py     # Stream rows from a Databricks Unity Catalog query
├── config.yaml                  # All import jobs — queries, Cypher, batch 
├── env.sample                   # Copy to .env and fill in your values
└── .gitignore
```

---

## Quickstart

Note for Windows Users: To enable AI standards symlinks, ensure you have Developer Mode enabled and clone the repo with 
git clone -c core.symlinks=true <url>

### 1. Prerequisites

- Python 3.11+
- A running AuraDB instance (URI, username, password from the Aura console)
- GCP credentials with access to your BigQuery dataset and/or GCS bucket

### 2. Set Up the Environment

```bash
uv venv
source .venv/bin/activate
uv pip install -e .[dev]
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

Open `poc_walkthrough.ipynb` in Jupyter or Vertex AI Notebooks and run cells top to bottom. It will verify connectivity, preview your data, run a test import, let you explore the imported graph with a few basic Cypher queries, and then run the full import.

Or run directly via CLI:

```bash
uv run python main.py run --config config.yaml
```

---

## How It Works

### Configuration

All import jobs are defined in config.yaml — queries, Cypher, source details, and batch sizes. Credentials stay in .env. This is the only file customers need to edit for a typical POC.

```yaml
imports:
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
source |✅ |bigquery, gcs, or databricks
query | ✅ |(BigQuery / Databricks) Standard SQL query
bucket / blob| ✅ |(GCS)GCS bucket name and file path
cypher |✅ |Cypher using UNWIND $rows AS row
batch_size | — | Rows per transaction (default: 1000)
transform | — | Name of a transform function defined in main.py

### The Importer

`Neo4jImporter` handles the connection, batching, retries, and summary logging. All your Cypher queries use the `UNWIND $rows AS row` pattern — the importer passes each batch as `{"rows": [...]}`.

```python
# Run all jobs defined in config.yaml
uv run python main.py run

# Or point at a different config file
uv run python main.py run --config config_staging.yaml
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
| Databricks | `DatabricksSource(query)` | Unity Catalog managed tables via SQL Warehouse. Streams via `cursor.fetchmany(batch_size)` — memory proportional to batch size, not table size. |

**GCP Authentication:** Both GCP sources use [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials). Set `GOOGLE_APPLICATION_CREDENTIALS` in `.env` to point at a service account key file, or run `gcloud auth application-default login` for local development.

**Required IAM roles:**
- BigQuery: `BigQuery Data Viewer` + `BigQuery Job User`
- GCS: `Storage Object Viewer`

**Databricks Authentication:** Uses a Personal Access Token — no OAuth/service-principal support yet (POC scope). Requires the optional `[databricks]` extra:

```bash
uv pip install -e ".[databricks]"
```

Set in `.env`:

```
DATABRICKS_SERVER_HOSTNAME=your-workspace.cloud.databricks.com
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/xxxxxxxxxxxxxxxx
DATABRICKS_TOKEN=
```

Find these under **SQL Warehouses → (your warehouse) → Connection Details**, and generate a token under **User Settings → Developer → Access Tokens**. The `databricks.sql` driver import is lazy — it's only required when a `databricks` job actually runs, so the extra doesn't need to be installed for GCP-only POCs.

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
| `DATABRICKS_SERVER_HOSTNAME` | — † | SQL Warehouse hostname. Required if using `source: databricks`. |
| `DATABRICKS_HTTP_PATH` | — † | SQL Warehouse HTTP path. Required if using `source: databricks`. |
| `DATABRICKS_TOKEN` | — † | Personal Access Token. Required if using `source: databricks`. |

*`NEO4J_USER` + `NEO4J_PASSWORD` are required unless `NEO4J_TOKEN` is set.
†All three Databricks variables are required together if any `databricks` source job is configured; otherwise omit them entirely.

---

## Data Integrity & Performance: Constraints

Before running your import, you **must** create Uniqueness Constraints on any property used in a `MERGE`. Without them:
1.  Every `MERGE` performs a full label scan, which is slow and gets exponentially slower as data grows.
2.  You risk creating duplicate nodes if multiple batches run in parallel (though this kit is sequential).

Use `IF NOT EXISTS` so the statements are safe to re-run:

```cypher
CREATE CONSTRAINT client_node_id IF NOT EXISTS FOR (p:ClientNode) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT supplier_code  IF NOT EXISTS FOR (d:Supplier)   REQUIRE d.supplierCode IS UNIQUE;
```

Run these in the AuraDB Browser or via a setup script before calling the importer. You can verify what's active at any time with:

```cypher
SHOW CONSTRAINTS;
```

**Rule of thumb:** If it's in the `{id: row.id}` part of your `MERGE`, it needs a constraint. For non-unique properties that you frequently filter on, use a standard index:

```cypher
CREATE INDEX part_status IF NOT EXISTS FOR (p:Part) ON (p.status);
```

---

## Testing

The test suite exercises the full `config.yaml → importer.py → Neo4j` pipeline using in-memory mock sources — no GCP credentials required.

### Prerequisites

- Python 3.11+
- A local Neo4j instance (Neo4j Desktop, CE, or Docker)

### Run Locally

```bash
# 1. Start a local Neo4j instance (Neo4j Desktop or Docker)
# 2. Set connection details in .env (defaults: bolt://localhost:7687, neo4j/testpassword)

uv pip install -e .[dev]
uv run pytest tests/ -v
```

The test suite reads `NEO4J_URI`, `NEO4J_USER`, and `NEO4J_PASSWORD` from your `.env` file (via `python-dotenv`), so no extra environment setup is needed beyond what you already have.

### Test Coverage

| File | What it tests |
|---|---|
| `tests/test_importer.py` | End-to-end ingest: merge, batch boundaries, transforms, skip logic, connectivity errors |
| `tests/test_sources.py` | MockSource batching integrity; GCSSource and BigQuerySource CSV/row parsing (GCP clients mocked) |

### GCP Integration Tests

Tests that hit real BigQuery or GCS are **out of scope** for this suite — they require live GCP credentials and are best run separately in a GCP environment. The mock sources (`MockBigQuerySource`, `MockGCSSource` in `sources/mock.py`) stand in for them during CI.

### CI (GitHub Actions)

The workflow in [`.github/workflows/test.yml`](.github/workflows/test.yml) runs on every push/PR to `develop`. It spins up a `neo4j:5` service container and runs the full suite.

---

## Extending This Kit

As you encounter new data sources in future POCs, add them to `sources/` following the `BaseSource` pattern. Some common candidates:

- `PostgresSource` — SQLAlchemy-based, works with any SQL database
- `S3Source` — mirrors `GCSSource`, swap in `boto3`
- `LocalCSVSource` — useful for quick desktop data loads
- `RestApiSource` — paginated GET with configurable auth

The `importer.py` and Cypher query pattern stay the same regardless of source.