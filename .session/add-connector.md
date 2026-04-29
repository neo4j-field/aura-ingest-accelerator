---
Status: active
Date: 2026-04-28
Topic: add-connector
---

# Session: Add a New Data Source Connector
# aura-ingest-accelerator

---

## Goal

Implement a new `sources/<source_name>_source.py` connector that integrates with the
`aura-ingest-accelerator` pipeline. The connector must subclass `BaseSource`, implement
`get_batches()`, be registered in `main.py`, and have a matching entry in `config.yaml`.

---

## Context & Constraints

### Locked decisions
- One file per connector: `sources/<source_name>_source.py`. No subdirectory, no `__init__.py`.
- `get_batches(batch_size: int)` must **yield lists of dicts** — not a generator of scalars,
  not a single dict. Each `yield` produces one batch (a Python `list`).
- Sources are **not auto-discovered**. A new source requires two explicit edits to `main.py`:
  (1) an import statement, and (2) a new `elif` branch in `build_source()`.
- If the source needs a row-level transform, also add an entry to `TRANSFORMS` in `main.py`
  and a `transform` key in the `config.yaml` job.
- The repo uses plain `pip` + `venv`. Do not reference `uv` commands.

### Out of scope
- Modifying `importer.py` or `sources/base.py`.
- Modifying either existing source (`bigquery_source.py`, `gcs_source.py`).
- Changing `config.yaml` structure or the `Neo4jImporter` class.
- CI/CD or testing infrastructure.

---

## Relevant Specs / Schemas / Examples

### `BaseSource` contract (verbatim from `sources/base.py`)
```python
# sources/base.py
from abc import ABC, abstractmethod


class BaseSource(ABC):
    @abstractmethod
    def get_batches(self, batch_size: int):
        """Yields lists of dicts, each of length up to batch_size."""
        pass
```

### New source file layout
```
sources/
└── <source_name>_source.py      # single file — matches existing naming convention
```

No subdirectory. No `__init__.py`. One file, named `<source_name>_source.py`.

### Registration pattern (two edits to `main.py`)

**Edit 1 — add import at the top of `main.py`:**
```python
from sources.<source_name>_source import <SourceName>Source
```

**Edit 2 — add an `elif` branch inside `build_source()`:**
```python
def build_source(cfg: dict):
    source_type = cfg.get("source")
    if source_type == "bigquery":
        return BigQuerySource(cfg["query"])
    elif source_type == "gcs":
        return GCSSource(bucket_name=cfg["bucket"], blob_name=cfg["blob"])
    elif source_type == "<source_name>":                     # add this block
        return <SourceName>Source(cfg["<param1>"], cfg["<param2>"])
    else:
        raise ValueError(
            f"Unknown source type '{source_type}'. "
            f"Valid options: bigquery, gcs, <source_name>"
        )
```

The `source_type` string in the `elif` must match the `source:` value in `config.yaml`.

**Optional Edit 3 — if the source needs a row-level transform, add to `TRANSFORMS`:**
```python
TRANSFORMS = {
    "transform_part_row": transform_part_row,
    "transform_<source_name>_row": transform_<source_name>_row,   # add this
}
```

### `config.yaml` job schema
```yaml
imports:
  - name: "My New Source Import"
    source: <source_name>           # must match the elif key in build_source()
    # source-specific connection keys (query, bucket/blob, connection string, etc.)
    cypher: |
      UNWIND $rows AS row
      MERGE (n:MyLabel {id: row.id})
      SET n.name = row.name
    batch_size: 1000
    transform: transform_<source_name>_row   # omit if no transform needed
```

### Worked skeleton (modeled on `BigQuerySource` — the simpler of the two existing sources)

`BigQuerySource` is the best model: it takes constructor args, opens a lazy row iterator,
and accumulates rows into fixed-size batches before yielding. Adapt this pattern:

```python
# sources/snowflake_source.py  — illustrative; adapt to your actual target system
from sources.base import BaseSource


class SnowflakeSource(BaseSource):
    """
    Streams rows from a Snowflake query in batches.

    Args:
        query:             SQL query string to execute.
        connection_params: Dict with keys: account, user, password, database, schema.
    """

    def __init__(self, query: str, connection_params: dict):
        self.query = query
        self.connection_params = connection_params

    def get_batches(self, batch_size: int):
        batch = []
        for row in self._stream_rows():
            batch.append(dict(row))
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    def _stream_rows(self):
        # Open connection, execute self.query, yield one row at a time as a dict-like object.
        # Close connection/cursor in a finally block.
        raise NotImplementedError
```

Key points from `BigQuerySource` to replicate:
- Accumulate rows into `batch = []`; yield when `len(batch) >= batch_size`; yield the remainder after the loop
- `dict(row)` to normalize driver-specific row objects into plain dicts
- Keep connection setup in `__init__`; keep row iteration in a private helper method

---

## Instructions

1. **Read** `sources/base.py`, `sources/bigquery_source.py`, `sources/gcs_source.py`,
   and `main.py` to understand the full contract before writing any code.

2. **Create** `sources/<source_name>_source.py`:
   - Subclass `BaseSource` from `sources.base`
   - Implement `__init__` — accept all connection/auth params needed to open the source
   - Implement `get_batches(self, batch_size: int)` — yield `list[dict]` batches
   - Use a private helper (e.g. `_stream_rows()`) to keep `get_batches` readable
   - Let exceptions propagate; do not swallow them silently

3. **Add an import** at the top of `main.py`:
   ```python
   from sources.<source_name>_source import <SourceName>Source
   ```

4. **Add an `elif` branch** to `build_source()` in `main.py` for the new source type.
   Also update the `ValueError` message to include the new source name.

5. **Add a job entry** to `config.yaml` under `imports:`:
   ```yaml
   - name: "<Descriptive Import Name>"
     source: <source_name>
     # source-specific keys
     cypher: |
       UNWIND $rows AS row
       MERGE (n:MyLabel {id: row.id})
       SET n.name = row.name
     batch_size: 1000
   ```

6. **Create a MERGE index** in the AuraDB Browser before running the import.
   Use a uniqueness constraint for identity properties:
   ```cypher
   CREATE CONSTRAINT my_label_id_unique IF NOT EXISTS
     FOR (n:MyLabel) REQUIRE n.id IS UNIQUE;
   ```
   Verify with: `SHOW CONSTRAINTS;`

7. **Test with a small batch** — set `batch_size: 10` in `config.yaml` for the new job, then:
   ```python
   from main import run_poc
   run_poc("config.yaml")
   ```
   Check the summary log. Fix any errors before increasing batch size.

8. **Restore** `batch_size` to its production value (typically 500–1000) after the test passes.

---

## Decisions Made This Session

<!-- populated during the session -->
