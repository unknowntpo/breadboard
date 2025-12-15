"""ClickHouse implementation of stock repositories."""
from typing import List, Optional
from datetime import datetime
import logging

from backend.domain.interfaces import StockPriceRepository, HistoricalDataRepository
from backend.domain.entities import (
    StockPrice, HistoricalData, StockPriceCreate, HistoricalDataCreate
)
from backend.repository.clickhouse_client import ClickHouseConnection

logger = logging.getLogger(__name__)


class ClickHouseStockPriceRepository(StockPriceRepository):
    """ClickHouse implementation for stock price repository."""

    def __init__(self, connection: ClickHouseConnection):
        self._conn = connection

    def get_latest(self, symbol: str) -> Optional[StockPrice]:
        """Get latest price for a symbol."""
        query = """
        SELECT timestamp, symbol, price, volume, change_percent
        FROM stock_prices
        WHERE symbol = %(symbol)s
        ORDER BY timestamp DESC
        LIMIT 1
        """
        result = self._conn.execute(query, {"symbol": symbol})
        if result:
            row = result[0]
            return StockPrice(
                timestamp=row[0],
                symbol=row[1],
                price=row[2],
                volume=row[3],
                change_percent=row[4],
            )
        return None

    def get_history(self, symbol: str, limit: int = 100) -> List[StockPrice]:
        """Get recent price history for a symbol."""
        query = """
        SELECT timestamp, symbol, price, volume, change_percent
        FROM stock_prices
        WHERE symbol = %(symbol)s
        ORDER BY timestamp DESC
        LIMIT %(limit)s
        """
        results = self._conn.execute(query, {"symbol": symbol, "limit": limit})
        return [
            StockPrice(
                timestamp=row[0],
                symbol=row[1],
                price=row[2],
                volume=row[3],
                change_percent=row[4],
            )
            for row in results
        ]

    def insert(self, record: StockPriceCreate) -> None:
        """Insert a single stock price record."""
        timestamp = record.timestamp or datetime.now()
        query = """
        INSERT INTO stock_prices (timestamp, symbol, price, volume, change_percent)
        VALUES
        """
        self._conn.client.execute(
            query,
            [(timestamp, record.symbol, record.price, record.volume, record.change_percent)]
        )

    def insert_batch(self, records: List[StockPriceCreate]) -> None:
        """Insert multiple stock price records."""
        if not records:
            return
        query = """
        INSERT INTO stock_prices (timestamp, symbol, price, volume, change_percent)
        VALUES
        """
        values = [
            (
                rec.timestamp or datetime.now(),
                rec.symbol,
                rec.price,
                rec.volume,
                rec.change_percent,
            )
            for rec in records
        ]
        self._conn.client.execute(query, values)
        logger.info(f"Inserted {len(records)} stock price records")


class ClickHouseHistoricalRepository(HistoricalDataRepository):
    """ClickHouse implementation for historical data repository."""

    def __init__(self, connection: ClickHouseConnection):
        self._conn = connection

    def get_by_date_range(
        self, symbol: str, start_date: str, end_date: str
    ) -> List[HistoricalData]:
        """Get historical data for a symbol in date range."""
        query = """
        SELECT date, symbol, open, high, low, close, volume
        FROM historical_data
        WHERE symbol = %(symbol)s
          AND date >= %(start_date)s
          AND date <= %(end_date)s
        ORDER BY date ASC
        """
        results = self._conn.execute(
            query, {"symbol": symbol, "start_date": start_date, "end_date": end_date}
        )
        return [
            HistoricalData(
                date=row[0],
                symbol=row[1],
                open_price=row[2],
                high=row[3],
                low=row[4],
                close=row[5],
                volume=row[6],
            )
            for row in results
        ]

    def insert(self, record: HistoricalDataCreate) -> None:
        """Insert a single historical record."""
        query = """
        INSERT INTO historical_data (date, symbol, open, high, low, close, volume)
        VALUES
        """
        self._conn.client.execute(
            query,
            [(record.date, record.symbol, record.open, record.high,
              record.low, record.close, record.volume)]
        )

    def insert_batch(self, records: List[HistoricalDataCreate]) -> None:
        """Insert multiple historical records."""
        if not records:
            return
        query = """
        INSERT INTO historical_data (date, symbol, open, high, low, close, volume)
        VALUES
        """
        values = [
            (rec.date, rec.symbol, rec.open, rec.high, rec.low, rec.close, rec.volume)
            for rec in records
        ]
        self._conn.client.execute(query, values)
        logger.info(f"Inserted {len(records)} historical records")
