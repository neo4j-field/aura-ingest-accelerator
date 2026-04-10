# importer.py
import os
import time
import logging
from neo4j import GraphDatabase, auth as neo4j_auth
from neo4j.exceptions import ServiceUnavailable, TransientError
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


class Neo4jImporter:
    """
    Batch importer for Neo4j / AuraDB.

    Auth priority:
      1. Explicit `auth` argument passed to __init__
      2. NEO4J_TOKEN env var  → bearer token auth
      3. NEO4J_USER + NEO4J_PASSWORD env vars → basic auth

    Supports use as a context manager:
        with Neo4jImporter() as importer:
            importer.run_import(source, cypher)

    For Aura / private-link URIs, use the neo4j+s:// scheme:
        NEO4J_URI=neo4j+s://your-private-endpoint.aura.example.com:7687
    """

    def __init__(self, uri: str = None, auth=None):
        load_dotenv()

        self.uri = uri or os.getenv("NEO4J_URI")
        if not self.uri:
            raise ValueError(
                "No Neo4j URI provided. Set NEO4J_URI in your .env file "
                "or pass uri= to Neo4jImporter()."
            )

        # Auth resolution: explicit arg → bearer token → basic auth
        if auth:
            self.auth = auth
        elif os.getenv("NEO4J_TOKEN"):  # Truthiness check — skips empty string
            self.auth = neo4j_auth.bearer(os.getenv("NEO4J_TOKEN"))
        else:
            user = os.getenv("NEO4J_USER")
            password = os.getenv("NEO4J_PASSWORD")
            if not user or not password:
                raise ValueError(
                    "No auth configured. Set NEO4J_TOKEN or both NEO4J_USER "
                    "and NEO4J_PASSWORD in your .env file."
                )
            self.auth = (user, password)

        self.driver = GraphDatabase.driver(self.uri, auth=self.auth)

        # Fail fast — surface private-link / DNS / credential issues immediately
        # rather than discovering them mid-import.
        try:
            self.driver.verify_connectivity()
            logger.info("Successfully connected to Neo4j at %s", self.uri)
        except Exception as e:
            self.driver.close()
            raise ConnectionError(
                f"Could not connect to Neo4j at '{self.uri}'. "
                f"Check your URI, credentials, and network/private-link config.\n"
                f"Original error: {e}"
            ) from e

    # -------------------------------------------------------------------------
    # Context manager support — ensures driver is always closed
    # -------------------------------------------------------------------------

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False  # Do not suppress exceptions

    def close(self):
        self.driver.close()

    # -------------------------------------------------------------------------
    # Core import logic
    # -------------------------------------------------------------------------

    def run_import(
        self,
        source,
        cypher_query: str,
        batch_size: int = 1000,
        transform_fn=None,
        max_retries: int = 3,
    ):
        """
        Iterates over source.get_batches(), optionally transforms each row,
        and executes cypher_query for each batch via UNWIND $rows AS row.

        Args:
            source:        Any BaseSource subclass (BigQuerySource, GCSSource, …).
            cypher_query:  Cypher using UNWIND $rows AS row.
            batch_size:    Rows per transaction. 500–2000 is typical for Aura.
            transform_fn:  Optional callable(row) → dict | None.
                           Return None to skip a row.
            max_retries:   Retry attempts on transient Neo4j errors (e.g. Aura
                           scaling events).
        """
        total = {"nodes_created": 0, "properties_set": 0, "relationships_created": 0}

        with self.driver.session() as session:
            for i, batch in enumerate(source.get_batches(batch_size), start=1):

                if transform_fn:
                    batch = [transform_fn(row) for row in batch]
                    batch = [r for r in batch if r is not None]  # filter skipped rows

                if not batch:
                    logger.debug("Batch %d: empty after transform, skipping.", i)
                    continue

                summary = self._run_batch_with_retry(
                    session, cypher_query, batch, max_retries
                )

                c = summary.counters
                total["nodes_created"] += c.nodes_created
                total["properties_set"] += c.properties_set
                total["relationships_created"] += c.relationships_created

                logger.info(
                    "Batch %d (%d rows): +%d nodes | +%d props | +%d rels",
                    i,
                    len(batch),
                    c.nodes_created,
                    c.properties_set,
                    c.relationships_created,
                )

        logger.info(
            "Import complete — Totals: %d nodes created | %d properties set | "
            "%d relationships created",
            total["nodes_created"],
            total["properties_set"],
            total["relationships_created"],
        )
        return total

    def _run_batch_with_retry(self, session, cypher: str, batch: list, max_retries: int):
        """
        Executes a single batch with exponential backoff on transient errors.

        Aura can return ServiceUnavailable briefly during internal scaling events.
        Retrying with backoff is the recommended pattern rather than failing the
        entire import.
        """
        for attempt in range(1, max_retries + 1):
            try:
                result = session.run(cypher, {"rows": batch})
                return result.consume()
            except (ServiceUnavailable, TransientError) as e:
                if attempt == max_retries:
                    logger.error(
                        "Batch failed after %d attempts: %s", max_retries, e
                    )
                    raise
                wait = 2 ** attempt
                logger.warning(
                    "Transient error on attempt %d/%d — retrying in %ds: %s",
                    attempt,
                    max_retries,
                    wait,
                    e,
                )
                time.sleep(wait)