"""Stock price business logic."""
from typing import List, Optional
import logging

from backend.domain.interfaces import StockPriceRepository
from backend.domain.entities import StockPrice, StockPriceCreate

logger = logging.getLogger(__name__)


class StockService:
    """Business logic for stock price operations."""

    def __init__(self, repository: StockPriceRepository):
        self._repository = repository

    def get_latest_price(self, symbol: str) -> Optional[StockPrice]:
        """Get latest price for a symbol (uppercase normalized)."""
        return self._repository.get_latest(symbol.upper())

    def get_recent_prices(self, symbol: str, limit: int = 100) -> List[StockPrice]:
        """Get recent price history."""
        return self._repository.get_history(symbol.upper(), limit)

    def save_prices(self, records: List[StockPriceCreate]) -> None:
        """Save batch of price records."""
        self._repository.insert_batch(records)
