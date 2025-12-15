"""Alert business logic."""
from typing import Set, Callable
from datetime import datetime
import asyncio
import logging

from backend.domain.entities import Alert

logger = logging.getLogger(__name__)


class AlertService:
    """Business logic for price alerts."""

    def __init__(self, threshold: float = -5.0):
        self._threshold = threshold
        self._callbacks: Set[Callable] = set()

    @property
    def threshold(self) -> float:
        return self._threshold

    def register_callback(self, callback: Callable) -> None:
        """Register alert callback."""
        self._callbacks.add(callback)

    def unregister_callback(self, callback: Callable) -> None:
        """Unregister alert callback."""
        self._callbacks.discard(callback)

    def check_alert_condition(
        self, symbol: str, price: float, change_percent: float
    ) -> bool:
        """Check if price change triggers alert."""
        return change_percent <= self._threshold

    def create_alert(
        self, symbol: str, price: float, change_percent: float, timestamp: datetime
    ) -> Alert:
        """Create alert entity."""
        return Alert(
            type="price_drop",
            symbol=symbol,
            price=price,
            change_percent=change_percent,
            timestamp=timestamp,
            message=f"Alert: {symbol} dropped {change_percent:.2f}%",
        )

    async def trigger_alert(self, alert: Alert) -> None:
        """Trigger all registered callbacks."""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
