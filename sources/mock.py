# sources/mock.py
from .base import BaseSource


class MockSource(BaseSource):
    """In-memory source for testing — yields canned rows without any GCP calls."""

    def __init__(self, rows: list[dict]):
        self._rows = rows

    def get_batches(self, batch_size: int):
        for i in range(0, len(self._rows), batch_size):
            yield self._rows[i : i + batch_size]


# Explicit aliases so test configs can name the source type they're standing in for
MockBigQuerySource = MockSource
MockGCSSource = MockSource
