# sources/databricks_source.py
import os

from .base import BaseSource


class DatabricksSource(BaseSource):
    """
    Streams rows from a Databricks Unity Catalog table via SQL query, in batches.

    Authentication uses a Personal Access Token. Set in .env:
        DATABRICKS_SERVER_HOSTNAME
        DATABRICKS_HTTP_PATH   (SQL Warehouse or cluster HTTP path)
        DATABRICKS_TOKEN

    Args:
        query: Standard SQL query string, e.g.
               "SELECT id, name, email FROM main.sales.customers"
    """

    def __init__(self, query: str):
        self.query = query
        self._server_hostname = os.getenv("DATABRICKS_SERVER_HOSTNAME")
        self._http_path = os.getenv("DATABRICKS_HTTP_PATH")
        self._token = os.getenv("DATABRICKS_TOKEN")
        if not all([self._server_hostname, self._http_path, self._token]):
            raise ValueError(
                "Missing Databricks credentials. Set DATABRICKS_SERVER_HOSTNAME, "
                "DATABRICKS_HTTP_PATH, and DATABRICKS_TOKEN in .env."
            )

    def get_batches(self, batch_size: int):
        from databricks import sql  # lazy import — only required if this source is used

        with sql.connect(
            server_hostname=self._server_hostname,
            http_path=self._http_path,
            access_token=self._token,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.arraysize = batch_size
                cursor.execute(self.query)
                while True:
                    rows = cursor.fetchmany(batch_size)
                    if not rows:
                        break
                    yield [row.asDict() for row in rows]
