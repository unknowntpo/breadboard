"""Historical data business logic."""
from typing import List
import logging

from backend.domain.interfaces import HistoricalDataRepository
from backend.domain.entities import HistoricalData, HistoricalDataCreate

logger = logging.getLogger(__name__)


class HistoricalService:
    """Business logic for historical data operations."""

    def __init__(self, repository: HistoricalDataRepository):
        self._repository = repository

    def get_historical_data(
        self, symbol: str, start_date: str, end_date: str
    ) -> List[HistoricalData]:
        """Get historical OHLCV data for date range."""
        return self._repository.get_by_date_range(
            symbol.upper(), start_date, end_date
        )

    def save_historical_data(self, records: List[HistoricalDataCreate]) -> None:
        """Save batch of historical records."""
        self._repository.insert_batch(records)
