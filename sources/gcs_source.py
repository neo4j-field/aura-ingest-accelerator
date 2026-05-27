# sources/gcs_source.py
import csv
import codecs
import contextlib
import os
from dotenv import load_dotenv
from google.cloud import storage
from .base import BaseSource


class GCSSource(BaseSource):
    """
    Streams rows from a CSV file stored in Google Cloud Storage.

    Supports two authentication paths, selected automatically based on the
    presence of HMAC environment variables:

    **HMAC / S3-interoperability (for environments without ADC)**
        Set GCP_HMAC_ACCESS_KEY and GCP_HMAC_SECRET_KEY in your .env file.
        These are HMAC keys generated from the GCS Console under
        Settings → Interoperability tab. Access key IDs begin with "GOOG".
        Both keys must be present together; supplying only one raises
        ValueError.  When both are set, GCSSource initialises a boto3 S3
        client pointed at https://storage.googleapis.com using s3v4 signing.
        Install the optional dependency with:
            pip install aura-ingest-accelerator[hmac]

    **Application Default Credentials (ADC) — fallback**
        Used when neither HMAC key is set.  Relies on the standard ADC
        resolution chain (GOOGLE_APPLICATION_CREDENTIALS service account
        JSON, gcloud user credentials, Workload Identity, etc.).  Set
        GOOGLE_APPLICATION_CREDENTIALS in your .env to point at a service
        account key file if needed.

    Streams rows directly from GCS using blob.open() (ADC) or boto3
    StreamingBody (HMAC), so memory usage is proportional to batch_size,
    not file size.

    Args:
        bucket_name: GCS bucket name (without gs:// prefix).
        blob_name:   Path to the CSV file within the bucket.
    """

    def __init__(self, bucket_name: str, blob_name: str):
        load_dotenv()

        hmac_access_key = os.getenv("GCP_HMAC_ACCESS_KEY")
        hmac_secret_key = os.getenv("GCP_HMAC_SECRET_KEY")

        if bool(hmac_access_key) != bool(hmac_secret_key):
            raise ValueError(
                "Both GCP_HMAC_ACCESS_KEY and GCP_HMAC_SECRET_KEY must be set "
                "together. Supply both or neither."
            )

        if hmac_access_key and hmac_secret_key:
            try:
                import boto3
                from botocore.config import Config
            except ImportError as exc:
                raise ImportError(
                    "boto3 is required for HMAC-based GCS access. "
                    "Install it with: pip install aura-ingest-accelerator[hmac]"
                ) from exc

            s3_client = boto3.client(
                "s3",
                endpoint_url="https://storage.googleapis.com",
                aws_access_key_id=hmac_access_key,
                aws_secret_access_key=hmac_secret_key,
                config=Config(signature_version="s3v4"),
            )

            @contextlib.contextmanager
            def _hmac_stream():
                resp = s3_client.get_object(Bucket=bucket_name, Key=blob_name)
                body = resp["Body"]
                try:
                    yield codecs.getreader("utf-8")(body)
                finally:
                    body.close()

            self._open_stream = _hmac_stream
        else:
            client = storage.Client()
            blob = client.bucket(bucket_name).blob(blob_name)
            self._open_stream = lambda: blob.open("r", newline="")

    def get_batches(self, batch_size: int):
        with self._open_stream() as f:
            reader = csv.DictReader(f)

            batch = []
            for row in reader:
                batch.append(dict(row))
                if len(batch) >= batch_size:
                    yield batch
                    batch = []
            if batch:
                yield batch
