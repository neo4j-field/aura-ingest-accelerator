# main.py
from importer import Neo4jImporter
from sources.bigquery_source import BigQuerySource
from sources.gcs_source import GCSSource  # FIX: was missing


# =============================================================================
# Cypher Queries
# =============================================================================
#
# All queries use the UNWIND $rows AS row pattern.
# The importer passes each batch as {"rows": [...]}.
#
# NODE_QUERY note: the final SET outside ON CREATE / ON MATCH intentionally
# overwrites name and email on every run. Move those properties into ON CREATE
# only if you want them written once and never updated.
# =============================================================================

NODE_QUERY = """
UNWIND $rows AS row
WITH row, datetime() AS now
MERGE (p:ClientNode {id: row.id})
ON CREATE SET
  p.createdAt = now,
  p.updatedAt = now
ON MATCH SET
  p.updatedAt = now
SET p.name = row.name, p.email = row.email
"""

REL_QUERY = """
UNWIND $rows AS row
MATCH (a:ClientNode {id: row.source_id})
MATCH (b:ClientNode {id: row.target_id})
MERGE (a)-[r:INTERACTED_WITH]->(b)
ON CREATE SET r.timestamp = datetime(row.ts)
"""

SUPPLIER_QUERY = """
UNWIND $rows AS row
MERGE (d:Supplier {supplierCode: row.code})
SET d.name = row.name, d.location = row.city
"""


# =============================================================================
# Transform Functions
# =============================================================================

def transform_part_row(row: dict) -> dict | None:
    """
    Example row-level transform for a parts dataset.

    Rules applied:
      - Rows missing 'partnum' are dropped (return None → skipped by importer).
      - 'partnum' is normalized to uppercase.
      - 'is_active' boolean is derived from the 'status' field.
      - A static 'import_source' tag is added for lineage tracking.

    To use:
        importer.run_import(source, NODE_QUERY, transform_fn=transform_part_row)
    """
    if not row.get("partnum"):
        return None  # Returning None signals the importer to skip this row

    return {
        **row,
        "partnum": row["partnum"].upper(),
        "is_active": row.get("status") == "ACTIVE",
        "import_source": "GCS_STAGING_BUCKET",
    }


# =============================================================================
# Import Runs
# =============================================================================

def run_poc():
    # Use as a context manager so the driver is always cleanly closed,
    # even if an exception occurs mid-import.
    with Neo4jImporter() as importer:

        # --- Node Import from BigQuery ---
        print("--- Importing Nodes ---")
        bq_nodes = BigQuerySource(
            "SELECT id, name, email FROM `poc-project.dataset.users` LIMIT 5000"
        )
        importer.run_import(bq_nodes, NODE_QUERY, batch_size=1000)

        # --- Relationship Import from BigQuery ---
        # Lower batch size for relationship writes — each batch requires two
        # MATCH lookups per row, so smaller batches reduce lock contention.
        print("\n--- Importing Relationships ---")
        bq_rels = BigQuerySource(
            "SELECT source_id, target_id, ts FROM `poc-project.dataset.edges` LIMIT 2000"
        )
        importer.run_import(bq_rels, REL_QUERY, batch_size=100)

        # --- GCS CSV Import with inline transform ---
        print("\n--- Importing Suppliers from GCS ---")
        gcs_source = GCSSource(
            bucket_name="my-data-landing",
            blob_name="test_data_2026.csv",
        )
        importer.run_import(
            source=gcs_source,
            cypher_query=SUPPLIER_QUERY,
            batch_size=500,
            transform_fn=lambda r: {**r, "name": r["name"].strip()},
        )


if __name__ == "__main__":
    run_poc()