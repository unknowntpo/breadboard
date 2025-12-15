"""ClickHouse database connection management."""
from typing import List, Any, Optional
from clickhouse_driver import Client
import logging

from backend.config import clickhouse_config

logger = logging.getLogger(__name__)


class ClickHouseConnection:
    """Manages ClickHouse database connection."""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        database: str = None,
        user: str = None,
        password: str = None,
    ):
        self.host = host or clickhouse_config.HOST
        self.port = port or clickhouse_config.PORT
        self.database = database or clickhouse_config.DATABASE
        self.user = user or clickhouse_config.USER
        self.password = password or clickhouse_config.PASSWORD
        self._client: Optional[Client] = None

    def connect(self) -> None:
        """Establish connection to ClickHouse."""
        try:
            self._client = Client(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
            )
            logger.info(f"Connected to ClickHouse at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            raise

    def disconnect(self) -> None:
        """Close connection to ClickHouse."""
        if self._client:
            self._client.disconnect()
            self._client = None
            logger.info("Disconnected from ClickHouse")

    def execute(self, query: str, params: Optional[dict] = None) -> List[Any]:
        """Execute a query and return results."""
        if not self._client:
            raise RuntimeError("Not connected to ClickHouse")
        return self._client.execute(query, params or {})

    @property
    def client(self) -> Client:
        """Get underlying client for batch inserts."""
        if not self._client:
            raise RuntimeError("Not connected to ClickHouse")
        return self._client
