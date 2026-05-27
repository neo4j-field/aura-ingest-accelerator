# tests/test_sources.py
import sys
import os
import io
from itertools import chain
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sources.mock import MockSource
from sources.gcs_source import GCSSource
from sources.bigquery_source import BigQuerySource


class TestMockSource:
    def test_mock_source_batch_count(self, sample_rows):
        """25 rows at batch_size=10 should produce exactly 3 batches."""
        source = MockSource(sample_rows)
        batches = list(source.get_batches(10))
        assert len(batches) == 3

    def test_mock_source_row_integrity(self, sample_rows):
        """All rows across all batches must match the original list — no loss or duplication."""
        source = MockSource(sample_rows)
        all_rows = list(chain.from_iterable(source.get_batches(10)))
        assert all_rows == sample_rows


class TestGCSSourceUnit:
    def test_gcs_source_unit(self):
        """GCSSource should parse CSV rows correctly without a real GCS connection."""
        csv_content = "id,name,status\n1,Alice,active\n2,Bob,inactive\n3,Carol,active\n"

        mock_blob = MagicMock()
        mock_open_cm = MagicMock()
        mock_open_cm.__enter__ = MagicMock(return_value=io.StringIO(csv_content))
        mock_open_cm.__exit__ = MagicMock(return_value=False)
        mock_blob.open.return_value = mock_open_cm

        mock_client = MagicMock()
        mock_client.bucket.return_value.blob.return_value = mock_blob

        env_without_hmac = {
            k: v for k, v in os.environ.items()
            if k not in ("GCP_HMAC_ACCESS_KEY", "GCP_HMAC_SECRET_KEY")
        }
        with patch("sources.gcs_source.storage.Client", return_value=mock_client), \
             patch.dict(os.environ, env_without_hmac, clear=True):
            source = GCSSource("test-bucket", "test.csv")

        batches = list(source.get_batches(10))
        assert len(batches) == 1
        assert batches[0] == [
            {"id": "1", "name": "Alice", "status": "active"},
            {"id": "2", "name": "Bob", "status": "inactive"},
            {"id": "3", "name": "Carol", "status": "active"},
        ]


class TestBigQuerySourceUnit:
    def test_bigquery_source_unit(self):
        """BigQuerySource should yield batches from query results without a real BQ connection."""
        raw_rows = [
            {"id": 1, "name": "Alice", "status": "active"},
            {"id": 2, "name": "Bob", "status": "inactive"},
            {"id": 3, "name": "Carol", "status": "active"},
        ]

        mock_query_job = MagicMock()
        mock_query_job.result.return_value = iter(raw_rows)

        mock_client = MagicMock()
        mock_client.query.return_value = mock_query_job

        with patch("sources.bigquery_source.bigquery.Client", return_value=mock_client):
            source = BigQuerySource("SELECT * FROM test.table")

        batches = list(source.get_batches(10))
        assert len(batches) == 1
        assert batches[0] == raw_rows
