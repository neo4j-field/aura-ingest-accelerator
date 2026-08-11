# main.py
import os
import yaml
import logging
from typing import Optional
import typer
from rich.console import Console
from rich.logging import RichHandler
from importer import Neo4jImporter
from sources.bigquery_source import BigQuerySource
from sources.gcs_source import GCSSource
from sources.databricks_source import DatabricksSource

# =============================================================================
# CLI & Logging Setup
# =============================================================================

app = typer.Typer(help="Neo4j AuraDB Ingestion Accelerator")
console = Console()

def setup_logging(debug: bool = False):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, console=console, show_path=False)]
    )


# =============================================================================
# Optional transform functions
# =============================================================================

def transform_part_row(row: dict) -> dict | None:
    """
    Example row-level transform for a parts dataset.
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
    elif source_type == "databricks":
        return DatabricksSource(cfg["query"])
    elif source_type == "mock" and os.getenv("AURA_TEST_MODE"):
        from sources.mock import MockSource
        return MockSource(cfg.get("rows", []))
    else:
        raise ValueError(
            f"Unknown source type '{source_type}'. "
            f"Valid options: bigquery, gcs, databricks"
        )


# =============================================================================
# CLI Command
# =============================================================================

@app.command()
def run(
    config_path: str = typer.Option("config.yaml", "--config", "-c", help="Path to config.yaml"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging")
):
    """
    Run the ingestion POC based on the provided configuration file.
    """
    setup_logging(debug)
    
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        console.print(f"❌ [bold red]Error:[/] Config file not found at {config_path}")
        raise typer.Exit(code=1)

    console.print(f"🔍 [bold blue]Starting import jobs from {config_path}...[/]")

    try:
        with Neo4jImporter() as importer:
            for job in config.get("imports", []):
                name = job.get("name", "Unnamed")
                console.print(f"\n🚀 [bold]Job: {name}[/]")

                source = build_source(job)
                transform_fn = TRANSFORMS.get(job.get("transform"))

                importer.run_import(
                    source=source,
                    cypher_query=job["cypher"],
                    batch_size=job.get("batch_size", 1000),
                    transform_fn=transform_fn,
                )
        console.print("\n✅ [bold green]All import jobs completed successfully![/]")
    except Exception as e:
        console.print(f"\n❌ [bold red]Import failed:[/] {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
