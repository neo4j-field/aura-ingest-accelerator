# Session Handoff: Aura Ingest Accelerator — Mock Testing Layer

**Status:** complete
**Date:** 2025-05-13
**Topic:** aura-ingest-mock-testing
**Repo:** https://github.com/neo4j-field/aura-ingest-accelerator

---

## Goal

Add a pytest-based test suite to `aura-ingest-accelerator` that exercises the full
`config.yaml → main.py → importer.py → Neo4j` pipeline without requiring live GCP
credentials. Deliver: a `tests/` directory with fixtures, mock sources, and at least
three integration-style test cases that run against a local Neo4j CE or Desktop instance via
environment variables. The suite must pass in CI (GitHub Actions) with Neo4j
running as a service container.

---

## Context & Constraints

### Locked Decisions
- Do NOT refactor `BigQuerySource` or `GCSSource` to inject dependencies — instead,
  add `MockBigQuerySource` and `MockGCSSource` in `sources/mock.py` that satisfy the
  `BaseSource` ABC by yielding canned row batches.
- The existing `TRANSFORMS` registry pattern in `main.py` must remain unchanged.
- Tests must be runnable with `uv run pytest` from the repo root.
- Neo4j connection for tests: `NEO4J_URI=bolt://localhost:7687`,
  `NEO4J_USER=neo4j`, `NEO4J_PASSWORD=testpassword` (overridable via env).
- Do not add `pytest-mock` or `unittest.mock` patches to production source files.
  All mocking must be test-local.

### Out of Scope
- Testing GCP ADC credential resolution (requires real GCP — test separately).
- Testing private-link DNS resolution.
- Adding type annotations or refactoring existing source classes.
- Performance/load testing.

### Reference Files
- `sources/base.py` — `BaseSource` ABC to subclass for mocks
- `importer.py` — `Neo4jImporter` class under test
- `main.py` — `run_imports()` entry point, `TRANSFORMS` registry
- `config.yaml` — shape of a valid import config
- `pyproject.toml` — dependency management (uv)

---

## Relevant Specs / Schemas / Examples

### BaseSource ABC (expected interface)
```python
# sources/base.py (inferred from README)
class BaseSource:
    def get_batches(self, batch_size: int):
        # yields List[dict]
        ...
```

### Expected config.yaml shape
```yaml
imports:
  - name: "Test Nodes"
    source: bigquery          # will be overridden in tests to "mock"
    query: "SELECT ..."
    cypher: |
      UNWIND $rows AS row
      MERGE (n:TestNode {id: row.id})
      SET n.name = row.name
    batch_size: 10
```

### Mock source pattern
```python
# sources/mock.py
from sources.base import BaseSource

class MockSource(BaseSource):
    def __init__(self, rows: list[dict]):
        self._rows = rows

    def get_batches(self, batch_size: int):
        for i in range(0, len(self._rows), batch_size):
            yield self._rows[i:i + batch_size]
```

### Test fixture pattern
```python
# tests/conftest.py
import pytest
from neo4j import GraphDatabase
import os

@pytest.fixture(scope="session")
def neo4j_driver():
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "testpassword")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    yield driver
    driver.close()

@pytest.fixture(autouse=True)
def clean_graph(neo4j_driver):
    """Wipe test labels before each test."""
    with neo4j_driver.session() as session:
        session.run("MATCH (n:TestNode) DETACH DELETE n")
        session.run("MATCH (n:TestEdge) DETACH DELETE n")
    yield
```

---

## Instructions

1. **Create `sources/mock.py`** with a `MockSource(BaseSource)` class that accepts
   a `list[dict]` of rows in `__init__` and yields them in batches via
   `get_batches(batch_size)`. Also add `MockBigQuerySource` and `MockGCSSource` as
   thin aliases so that source-type dispatch in tests is explicit.

2. **Update `main.py` source dispatch** to recognise `"mock"` as a valid source
   type (mapping to `MockSource`), guarded behind a flag or only imported when
   `AURA_TEST_MODE=1` is set in env. This avoids polluting the production code path
   while enabling end-to-end tests through the real `run_imports()` function.

3. **Create `tests/conftest.py`** with:
   - `neo4j_driver` session-scoped fixture (reads NEO4J_URI/USER/PASSWORD from env
     with safe defaults)
   - `clean_graph` autouse fixture that deletes all `:TestNode` and `:TestRelNode`
     nodes before each test
   - A `sample_rows` fixture returning 25 dicts with keys `id` (int), `name` (str),
     `status` (str)

4. **Create `tests/test_importer.py`** with these test cases:
   - `test_basic_merge` — ingest 25 rows via `Neo4jImporter`, assert all 25
     `:TestNode` nodes exist with correct properties
   - `test_batch_boundary` — use `batch_size=7` with 25 rows; assert 25 nodes (tests
     that partial final batch is not dropped)
   - `test_transform_applied` — register a `transform_upper_name` in a local
     TRANSFORMS dict that uppercases `row["name"]`; run via mock config; assert all
     node `.name` values are uppercase
   - `test_skip_on_none_transform` — transform returns `None` for rows where
     `id % 5 == 0`; assert only 20 nodes are created (skip logic works)
   - `test_connectivity_error_raises` — instantiate `Neo4jImporter` with a bad URI;
     assert it raises a connection error immediately (not silently at import time)

5. **Create `tests/test_sources.py`** with:
   - `test_mock_source_batch_count` — verify correct number of batches for 25 rows
     at batch_size=10 (should be 3)
   - `test_mock_source_row_integrity` — verify no rows lost or duplicated across
     all batches
   - `test_gcs_source_unit` — mock `google.cloud.storage.Client` using
     `unittest.mock.patch`; feed in a CSV string; assert `GCSSource.get_batches()`
     yields the expected dicts (this tests the CSV parsing without real GCS)
   - `test_bigquery_source_unit` — mock `google.cloud.bigquery.Client` using
     `unittest.mock.patch`; simulate `query_job.result()` returning an iterable of
     row objects; assert `BigQuerySource.get_batches()` yields correct dicts

6. **Add `requirements-dev.txt` entries** if not already present: `pytest`,
   `pytest-env` (for env var injection in pytest.ini), and confirm
   `neo4j` driver is already listed.

7. **Create `.github/workflows/test.yml`** GitHub Actions workflow:
   - Trigger: `push` to `develop`, PRs to `develop`
   - Services: `neo4j:5` container with `NEO4J_AUTH=neo4j/testpassword` and
     health check on port 7687
   - Steps: checkout → setup Python 3.11 → `uv pip install -e .[dev]` →
     `uv run pytest tests/ -v`
   - Set env vars: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `AURA_TEST_MODE=1`

8. **Add a `pytest.ini` or `[tool.pytest.ini_options]` in `pyproject.toml`** with:
   - `testpaths = ["tests"]`
   - `env = ["AURA_TEST_MODE=1"]` (requires pytest-env)

9. **Run `uv run pytest tests/ -v`** locally; confirm all tests pass before
   committing. Document any failures as issues on the repo.

10. **Update `README.md`** to add a "Testing" section explaining how to run the
    suite locally with a local Neo4j CE or Desktop instance, and that GCP integration tests
    require real credentials (to be added separately).

---

## Decisions Made This Session

- **neo4j driver API fix required:** `neo4j` 6.x removed the `auth` submodule; `auth.bearer()` became the top-level `bearer_auth()`. Fixed in `importer.py` as a prerequisite for tests to collect.
- **`sys.path` injection in test files:** Root-level modules (`importer`, `sources`) are not an installed package, so test files prepend the project root to `sys.path` explicitly rather than adding a root `conftest.py` or changing `pyproject.toml` package config.
- **`clean_graph` runs pre-test only:** The autouse fixture wipes `TestNode`/`TestRelNode` before each test but not after, leaving the DB empty after the suite. Nodes are only visible mid-run.
- **Coverage flags removed from `addopts`:** The original `--cov=aura_ingest_accelerator` targeted a non-existent package; removed to avoid collection errors. Coverage can be re-added once the package structure is resolved.
- **`MockBigQuerySource`/`MockGCSSource` as aliases:** Implemented as simple aliases to `MockSource` rather than distinct classes — the ABC only requires `get_batches`, and both stand-ins yield identical dict batches.
- **`test_connectivity_error_raises` uses port 9999:** Localhost port 9999 is reliably not listening, giving an immediate TCP refusal rather than a DNS-based timeout.