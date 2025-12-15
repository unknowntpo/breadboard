"""Repository interfaces (Ports) - abstraction for data access."""
from abc import ABC, abstractmethod
from typing import List, Optional

from backend.domain.entities import StockPrice, HistoricalData, StockPriceCreate, HistoricalDataCreate


class StockPriceRepository(ABC):
    """Interface for stock price data access."""

    @abstractmethod
    def get_latest(self, symbol: str) -> Optional[StockPrice]:
        """Get latest price for a symbol."""
        pass

    @abstractmethod
    def get_history(self, symbol: str, limit: int = 100) -> List[StockPrice]:
        """Get recent price history for a symbol."""
        pass

    @abstractmethod
    def insert(self, record: StockPriceCreate) -> None:
        """Insert a single stock price record."""
        pass

    @abstractmethod
    def insert_batch(self, records: List[StockPriceCreate]) -> None:
        """Insert multiple stock price records."""
        pass


class HistoricalDataRepository(ABC):
    """Interface for historical OHLCV data access."""

    @abstractmethod
    def get_by_date_range(
        self, symbol: str, start_date: str, end_date: str
    ) -> List[HistoricalData]:
        """Get historical data for a symbol in date range."""
        pass

    @abstractmethod
    def insert(self, record: HistoricalDataCreate) -> None:
        """Insert a single historical record."""
        pass

    @abstractmethod
    def insert_batch(self, records: List[HistoricalDataCreate]) -> None:
        """Insert multiple historical records."""
        pass
