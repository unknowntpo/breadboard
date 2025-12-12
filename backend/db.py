from typing import List, Dict, Any, Optional
from datetime import datetime
from clickhouse_driver import Client
import logging

from backend.config import clickhouse_config

logger = logging.getLogger(__name__)


class ClickHouseClient:
    """ClickHouse database client for stock data."""

    def __init__(self):
        self.host: str = clickhouse_config.HOST
        self.port: int = clickhouse_config.PORT
        self.database: str = clickhouse_config.DATABASE
        self.user: str = clickhouse_config.USER
        self.password: str = clickhouse_config.PASSWORD
        self.client: Optional[Client] = None

    def connect(self) -> None:
        """Establish connection to ClickHouse."""
        try:
            self.client = Client(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
            )
            logger.info(f"Connected to ClickHouse at {self.host}:{self.port} as {self.user}")
        except Exception as e:
            logger.error(f"Failed to connect to ClickHouse: {e}")
            raise

    def disconnect(self) -> None:
        """Close connection to ClickHouse."""
        if self.client:
            self.client.disconnect()
            logger.info("Disconnected from ClickHouse")

    def execute(self, query: str, params: Optional[tuple] = None) -> List:
        """Execute a query and return results."""
        if not self.client:
            raise RuntimeError("Not connected to ClickHouse")

        try:
            return self.client.execute(query, params or ())
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def insert_stock_price(
        self,
        symbol: str,
        price: float,
        volume: int,
        change_percent: float,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Insert a stock price record."""
        if timestamp is None:
            timestamp = datetime.now()

        query = """
        INSERT INTO stock_prices (timestamp, symbol, price, volume, change_percent)
        VALUES
        """

        self.client.execute(query, [(timestamp, symbol, price, volume, change_percent)])

    def insert_stock_prices_batch(self, records: List[Dict[str, Any]]) -> None:
        """Insert multiple stock price records in batch."""
        if not records:
            return

        query = """
        INSERT INTO stock_prices (timestamp, symbol, price, volume, change_percent)
        VALUES
        """

        values = [
            (
                rec.get("timestamp", datetime.now()),
                rec["symbol"],
                rec["price"],
                rec.get("volume", 0),
                rec.get("change_percent", 0.0),
            )
            for rec in records
        ]

        self.client.execute(query, values)
        logger.info(f"Inserted {len(records)} records")

    def insert_historical_data(
        self,
        symbol: str,
        date: str,
        open_price: float,
        high: float,
        low: float,
        close: float,
        volume: int,
    ) -> None:
        """Insert historical OHLCV data."""
        query = """
        INSERT INTO historical_data (date, symbol, open, high, low, close, volume)
        VALUES
        """

        self.client.execute(
            query, [(date, symbol, open_price, high, low, close, volume)]
        )

    def insert_historical_data_batch(self, records: List[Dict[str, Any]]) -> None:
        """Insert multiple historical data records in batch."""
        if not records:
            return

        query = """
        INSERT INTO historical_data (date, symbol, open, high, low, close, volume)
        VALUES
        """

        values = [
            (
                rec["date"],
                rec["symbol"],
                rec["open"],
                rec["high"],
                rec["low"],
                rec["close"],
                rec["volume"],
            )
            for rec in records
        ]

        self.client.execute(query, values)
        logger.info(f"Inserted {len(records)} historical records for batch")

    def get_latest_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get the latest price for a symbol."""
        query = """
        SELECT timestamp, symbol, price, volume, change_percent
        FROM stock_prices
        WHERE symbol = %(symbol)s
        ORDER BY timestamp DESC
        LIMIT 1
        """

        result = self.client.execute(query, {"symbol": symbol})
        if result:
            row = result[0]
            return {
                "timestamp": row[0],
                "symbol": row[1],
                "price": row[2],
                "volume": row[3],
                "change_percent": row[4],
            }
        return None

    def get_historical_data(
        self, symbol: str, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Get historical OHLCV data for a symbol in a date range."""
        query = """
        SELECT date, symbol, open, high, low, close, volume
        FROM historical_data
        WHERE symbol = %(symbol)s
          AND date >= %(start_date)s
          AND date <= %(end_date)s
        ORDER BY date ASC
        """

        results = self.client.execute(
            query, {"symbol": symbol, "start_date": start_date, "end_date": end_date}
        )

        return [
            {
                "date": str(row[0]),
                "symbol": row[1],
                "open": row[2],
                "high": row[3],
                "low": row[4],
                "close": row[5],
                "volume": row[6],
            }
            for row in results
        ]

    def get_price_history(
        self, symbol: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent price history for a symbol."""
        query = """
        SELECT timestamp, symbol, price, volume, change_percent
        FROM stock_prices
        WHERE symbol = %(symbol)s
        ORDER BY timestamp DESC
        LIMIT %(limit)s
        """

        results = self.client.execute(query, {"symbol": symbol, "limit": limit})

        return [
            {
                "timestamp": row[0],
                "symbol": row[1],
                "price": row[2],
                "volume": row[3],
                "change_percent": row[4],
            }
            for row in results
        ]


# Global client instance
db_client = ClickHouseClient()
