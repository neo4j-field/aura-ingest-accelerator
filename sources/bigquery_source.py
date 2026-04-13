# sources/bigquery_source.py
from google.cloud import bigquery
from .base import BaseSource


class BigQuerySource(BaseSource):
    """
    Streams rows from a BigQuery query in batches.

    Authentication uses Application Default Credentials (ADC).
    Set GOOGLE_APPLICATION_CREDENTIALS in your .env to point at a
    service account key file, or run `gcloud auth application-default login`
    for local development.

    Args:
        query:      Standard SQL query string.
        project_id: GCP project ID. If omitted, inferred from ADC credentials.
    """

    def __init__(self, query: str, project_id: str = None):
        self.client = bigquery.Client(project=project_id)
        self.query = query

    def get_batches(self, batch_size: int):
        query_job = self.client.query(self.query)
        rows = query_job.result()  # Lazy iterator — rows are NOT all loaded into memory

        batch = []
        for row in rows:
            batch.append(dict(row))
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch