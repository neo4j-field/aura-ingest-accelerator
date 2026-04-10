# sources/base.py
from abc import ABC, abstractmethod


class BaseSource(ABC):
    @abstractmethod
    def get_batches(self, batch_size: int):
        """Yields lists of dicts, each of length up to batch_size."""
        pass