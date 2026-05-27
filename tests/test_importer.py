# tests/test_importer.py
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from importer import Neo4jImporter
from sources.mock import MockSource

CYPHER_MERGE_NODE = """
UNWIND $rows AS row
MERGE (n:TestNode {id: row.id})
SET n.name = row.name, n.status = row.status
"""


def _count_nodes(driver, label="TestNode") -> int:
    with driver.session() as session:
        result = session.run(f"MATCH (n:{label}) RETURN count(n) AS cnt")
        return result.single()["cnt"]


def _get_node_names(driver, label="TestNode") -> set[str]:
    with driver.session() as session:
        result = session.run(f"MATCH (n:{label}) RETURN n.name AS name")
        return {r["name"] for r in result}


class TestBasicImport:
    def test_basic_merge(self, neo4j_driver, sample_rows):
        source = MockSource(sample_rows)
        with Neo4jImporter() as importer:
            importer.run_import(source=source, cypher_query=CYPHER_MERGE_NODE)
        assert _count_nodes(neo4j_driver) == 25

    def test_batch_boundary(self, neo4j_driver, sample_rows):
        """Partial final batch (25 rows at batch_size=7 → batches of 7,7,7,4) must not be dropped."""
        source = MockSource(sample_rows)
        with Neo4jImporter() as importer:
            importer.run_import(source=source, cypher_query=CYPHER_MERGE_NODE, batch_size=7)
        assert _count_nodes(neo4j_driver) == 25

    def test_transform_applied(self, neo4j_driver, sample_rows):
        """Transform uppercasing name should be reflected in stored node properties."""
        def transform_upper_name(row: dict) -> dict:
            return {**row, "name": row["name"].upper()}

        local_transforms = {"transform_upper_name": transform_upper_name}

        source = MockSource(sample_rows)
        with Neo4jImporter() as importer:
            importer.run_import(
                source=source,
                cypher_query=CYPHER_MERGE_NODE,
                transform_fn=local_transforms["transform_upper_name"],
            )

        names = _get_node_names(neo4j_driver)
        assert all(name == name.upper() for name in names)
        assert len(names) == 25

    def test_skip_on_none_transform(self, neo4j_driver, sample_rows):
        """Transform returning None for id%5==0 rows should result in only 20 nodes."""
        def skip_multiples_of_five(row: dict) -> dict | None:
            if row["id"] % 5 == 0:
                return None
            return row

        source = MockSource(sample_rows)
        with Neo4jImporter() as importer:
            importer.run_import(
                source=source,
                cypher_query=CYPHER_MERGE_NODE,
                transform_fn=skip_multiples_of_five,
            )
        assert _count_nodes(neo4j_driver) == 20


class TestConnectivity:
    def test_connectivity_error_raises(self):
        """Bad URI must raise ConnectionError immediately, not silently at import time."""
        with pytest.raises(ConnectionError):
            Neo4jImporter(uri="bolt://localhost:9999", auth=("neo4j", "wrongpassword"))
