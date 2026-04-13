# sources/gcs_source.py
import csv
import io
from google.cloud import storage
from .base import BaseSource


class GCSSource(BaseSource):
    """
    Streams rows from a CSV file stored in Google Cloud Storage.

    NOTE: The current implementation downloads the full blob into memory before
    parsing. This is acceptable for POC-scale files (< a few hundred MB).
    For very large files, consider using blob.open() with a streaming reader
    instead of download_as_text().

    Authentication uses Application Default Credentials (ADC).
    Set GOOGLE_APPLICATION_CREDENTIALS in your .env to point at a
    service account key file.

    Args:
        bucket_name: GCS bucket name (without gs:// prefix).
        blob_name:   Path to the CSV file within the bucket.
    """

    def __init__(self, bucket_name: str, blob_name: str):
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        self.blob = self.bucket.blob(blob_name)

    def get_batches(self, batch_size: int):
        stream = self.blob.download_as_text()
        reader = csv.DictReader(io.StringIO(stream))

        batch = []
        for row in reader:
            batch.append(dict(row))
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch