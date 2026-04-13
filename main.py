# main.py
import yaml
from importer import Neo4jImporter
from sources.bigquery_source import BigQuerySource
from sources.gcs_source import GCSSource


# =============================================================================
# Optional transform functions
# =============================================================================
# Map a transform function name (as used in config.yaml) to a callable.
# Return None to skip a row; otherwise return the (modified) row dict.
# =============================================================================

def transform_part_row(row: dict) -> dict | None:
    """
    Example row-level transform for a parts dataset.

    Rules applied:
      - Rows missing 'partnum' are dropped (return None → skipped by importer).
      - 'partnum' is normalized to uppercase.
      - 'is_active' boolean is derived from the 'status' field.
      - A static 'import_source' tag is added for lineage tracking.
    """
    if not row.get("partnum"):
        return None
    return {
        **row,
        "partnum": row["partnum"].upper(),
        "is_active": row.get("status") == "ACTIVE",
        "import_source": "GCS_STAGING_BUCKET",
    }


# Register transforms here — key must match 'transform' value in config.yaml
TRANSFORMS = {
    "transform_part_row": transform_part_row,
}


# =============================================================================
# Source factory
# =============================================================================

def build_source(cfg: dict):
    source_type = cfg.get("source")
    if source_type == "bigquery":
        return BigQuerySource(cfg["query"])
    elif source_type == "gcs":
        return GCSSource(bucket_name=cfg["bucket"], blob_name=cfg["blob"])
    else:
        raise ValueError(
            f"Unknown source type '{source_type}'. "
            f"Valid options: bigquery, gcs"
        )


# =============================================================================
# Config-driven import runner
# =============================================================================

def run_poc(config_path: str = "config.yaml"):
    with open(config_path) as f:
        config = yaml.safe_load(f)

    with Neo4jImporter() as importer:
        for job in config.get("imports", []):
            name = job.get("name", "Unnamed")
            print(f"\n--- {name} ---")

            source = build_source(job)
            transform_fn = TRANSFORMS.get(job.get("transform"))  # None if not specified

            importer.run_import(
                source=source,
                cypher_query=job["cypher"],
                batch_size=job.get("batch_size", 1000),
                transform_fn=transform_fn,
            )


if __name__ == "__main__":
    run_poc()