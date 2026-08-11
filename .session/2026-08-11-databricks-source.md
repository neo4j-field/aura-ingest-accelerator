---
Status: complete
Date: 2026-08-11
Topic: databricks-source
---

# Session: Add Databricks Connector to aura-ingest-accelerator

## Goal

Implement `sources/databricks_source.py` that streams rows from Databricks Unity
Catalog tables via SQL query into the `aura-ingest-accelerator` pipeline, following
the established `BaseSource` / `build_source()` registration pattern documented in
`.session/add-connector.md`. This connector is for a customer whose Aura POC data
lives entirely in Databricks Unity Catalog managed tables — confirmed no separate
Azure Blob/ADLS connector is needed for this engagement.

---

## Context & Constraints

### Locked decisions
- One file: `sources/databricks_source.py`. No subdirectory, no `__init__.py`.
- `get_batches(batch_size: int)` must yield `list[dict]` batches — matches the
  `BaseSource` contract.
- Registration: import + new `elif` branch in `build_source()` in `main.py`; update
  the `ValueError` message to include `databricks` as a valid source name.
- Uses `databricks-sql-connector` (official Databricks SQL driver). Add as an
  optional-dependency extra `[databricks]` in `pyproject.toml`, mirroring the
  existing `[hmac]` extra already in the repo.
- Lazy-import `databricks.sql` inside the method that needs it (not at module top
  level) — same convention `GCSSource` uses for `boto3`, so the dependency is never
  required unless this source is actually used.
- Auth via Personal Access Token for POC scope: `DATABRICKS_SERVER_HOSTNAME`,
  `DATABRICKS_HTTP_PATH`, `DATABRICKS_TOKEN` read from `.env` via `dotenv`. Never
  hardcode.
- Data source is Unity Catalog managed tables only — standard
  `SELECT ... FROM catalog.schema.table`, no Delta CDC/streaming needed.

### Out of scope
- `azure_source.py` / raw ADLS or Blob Storage ingestion — not needed for this
  customer.
- Modifying `importer.py` or `sources/base.py`.
- Modifying existing sources (`bigquery_source.py`, `gcs_source.py`).
- Delta Lake CDC / streaming ingestion — batch `SELECT` only for POC.
- OAuth / service principal auth — PAT only for now; note as a future enhancement
  if the customer asks.

---

## Relevant Specs / Schemas / Examples

### `BaseSource` contract (verbatim)
```python
# sources/base.py
from abc import ABC, abstractmethod


class BaseSource(ABC):
    @abstractmethod
    def get_batches(self, batch_size: int):
        """Yields lists of dicts, each of length up to batch_size."""
        pass
```

### Worked skeleton (modeled on `BigQuerySource` — closest structural analog)
```python
# sources/databricks_source.py — illustrative; adapt as needed
import os
from sources.base import BaseSource


class DatabricksSource(BaseSource):
    """
    Streams rows from a Databricks Unity Catalog table via SQL query, in batches.

    Authentication uses a Personal Access Token. Set in .env:
        DATABRICKS_SERVER_HOSTNAME
        DATABRICKS_HTTP_PATH   (SQL Warehouse or cluster HTTP path)
        DATABRICKS_TOKEN

    Args:
        query: Standard SQL query string, e.g.
               "SELECT id, name, email FROM main.sales.customers"
    """

    def __init__(self, query: str):
        self.query = query
        self._server_hostname = os.getenv("DATABRICKS_SERVER_HOSTNAME")
        self._http_path = os.getenv("DATABRICKS_HTTP_PATH")
        self._token = os.getenv("DATABRICKS_TOKEN")
        if not all([self._server_hostname, self._http_path, self._token]):
            raise ValueError(
                "Missing Databricks credentials. Set DATABRICKS_SERVER_HOSTNAME, "
                "DATABRICKS_HTTP_PATH, and DATABRICKS_TOKEN in .env."
            )

    def get_batches(self, batch_size: int):
        from databricks import sql  # lazy import — only required if this source is used

        with sql.connect(
            server_hostname=self._server_hostname,
            http_path=self._http_path,
            access_token=self._token,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.arraysize = batch_size
                cursor.execute(self.query)
                while True:
                    rows = cursor.fetchmany(batch_size)
                    if not rows:
                        break
                    yield [row.asDict() for row in rows]
```

Key points from `BigQuerySource` replicated here:
- Lazy row fetch via `fetchmany(batch_size)` loop rather than loading the full
  result set — memory proportional to `batch_size`, not table size.
- `row.asDict()` normalizes the driver's row objects into plain dicts, same role
  `dict(row)` plays in `BigQuerySource`.
- Connection/cursor setup stays inside `get_batches` via context managers so
  nothing leaks if the generator is abandoned early (relevant given the existing
  `GCSSource` known-issue note about abandoned generators).

### `config.yaml` job schema
```yaml
- name: "Databricks Table Import"
  source: databricks
  query: >
    SELECT id, name, email
    FROM main.sales.customers
  cypher: |
    UNWIND $rows AS row
    MERGE (c:Customer {id: row.id})
    SET c.name = row.name, c.email = row.email
  batch_size: 1000
```

### `build_source()` addition
```python
elif source_type == "databricks":
    return DatabricksSource(cfg["query"])
```
Remember to update the trailing `ValueError` message to list `databricks` alongside
`bigquery` and `gcs`.

---

## Instructions

1. Read `sources/base.py`, `sources/bigquery_source.py`, and `build_source()` in
   `main.py` before writing any code.
2. Create `sources/databricks_source.py` implementing `DatabricksSource` per the
   skeleton above.
3. Add a `[databricks]` optional-dependency extra to `pyproject.toml`:
   `databricks-sql-connector>=3.0.0`, mirroring the existing `[hmac]` extra.
4. Add the import and `elif` branch to `build_source()` in `main.py`; update the
   `ValueError` message to include `databricks`.
5. Add `DATABRICKS_SERVER_HOSTNAME`, `DATABRICKS_HTTP_PATH`, `DATABRICKS_TOKEN` to
   `env.sample` with a comment on where to find each (SQL Warehouses → Connection
   Details in the Databricks workspace).
6. Add a job entry to `config.yaml` under `imports:` for the customer's actual
   table, using `batch_size: 10` for the first test run.
7. Test with:
   ```python
   from main import run_poc
   run_poc("config.yaml")
   ```
   Check the summary log; fix any auth/connection errors before increasing
   `batch_size`.
8. Create the identity-property uniqueness constraint in the AuraDB Browser for
   whatever label this import merges on, before running past the test batch.
9. Restore `batch_size` to a production value (typically 500–1000) after the test
   passes.
10. If `pyproject.toml`'s optional extras are documented in `README.md`, add
    `databricks` alongside `hmac`.

---

## Decisions Made This Session

- Implemented `sources/databricks_source.py` matching the skeleton, with one
  deviation: used `from .base import BaseSource` (relative import) instead of
  `from sources.base import BaseSource`, to match the actual convention already
  used by `bigquery_source.py` and `gcs_source.py`.
- Added `[databricks]` extra to `pyproject.toml` (`databricks-sql-connector>=3.0.0`).
- Registered `databricks` in `build_source()` in `main.py`; `DatabricksSource` is
  imported unconditionally at module top (same as `BigQuerySource`/`GCSSource`) —
  safe because the class itself only lazy-imports `databricks.sql` inside
  `get_batches()`, so the extra is never required unless a `databricks` job
  actually runs.
- Added Databricks PAT env vars to `env.sample` with instructions on locating
  each value in the Databricks workspace (SQL Warehouses → Connection Details;
  User Settings → Developer → Access Tokens).
- README.md has no separate "extras" documentation section (only `env.sample`
  documents `[hmac]` inline) — step 10 was a no-op, nothing to update there.
- Added a placeholder `"Databricks Table Import"` job to `config.yaml`
  (`batch_size: 10`, using the illustrative `main.sales.customers` query from
  this session file) marked with a `TODO` — the user deferred providing the
  real customer table/columns/target label to a later session.
- Sanity-checked (no real Databricks credentials available in this
  environment): `DatabricksSource` imports cleanly without
  `databricks-sql-connector` installed, and raises `ValueError` on missing
  credentials as expected. `main.py` imports cleanly via `uv run` and
  `build_source()`'s error message correctly lists `databricks` alongside
  `bigquery, gcs`.
- **Follow-up (same session, after user supplied real .env + Databricks
  trial account)**: end-to-end validated against the user's local Neo4j test
  server (`neo4j://127.0.0.1:7687`) and the Databricks `samples.tpch.customer`
  Unity Catalog sample table (no real customer table available yet):
  - Ran `uv pip install -e ".[databricks]"` — installed `databricks-sql-connector`
    cleanly (pulls in `pandas`/`numpy`/`thrift`/etc. transitively; a
    `pyarrow not installed` warning is expected/benign per the connector — no
    cloud-fetch/arrow features are used here).
  - Source-only smoke test confirmed `DatabricksSource.get_batches()` streams
    and batches real rows correctly.
  - Full pipeline test (`Neo4jImporter` + `DatabricksSource`, bypassing
    `main.py`'s CLI since `config.yaml` still has unconfigured BigQuery/GCS
    jobs) created the `customer_custkey_unique` constraint, imported 20 rows
    in 2 batches, and verified `MATCH (c:Customer) RETURN count(c)` returned 20.
  - Note for local/self-hosted Neo4j: `CREATE CONSTRAINT ... IS UNIQUE` is the
    community/enterprise-agnostic syntax used here — works the same as the
    AuraDB Browser step called for in the original instructions; ran it via
    the driver directly since this target isn't AuraDB.
  - Updated `config.yaml`'s `"Databricks Table Import"` job to the validated
    `samples.tpch.customer` query/cypher and restored `batch_size` to 500
    (from the test value of 10) per instruction step 9. Query still capped
    with `LIMIT 1000` since this is sample/demo data, not the real customer
    table.
  - **Still deferred**: swapping `query`/`cypher` in `config.yaml` for the
    customer's actual Unity Catalog table/columns/target label once provided
    — that's a config-only change at that point, no code changes expected.
    Session left as `draft` pending that.
