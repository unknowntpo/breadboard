import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from backend.domain.entities import StockPriceCreate
from backend.services.stock_service import StockService
from backend.services.alert_service import AlertService

logger = logging.getLogger(__name__)


class StreamProcessor:
    """Process stock price messages with dependency injection."""

    def __init__(
        self,
        queue: asyncio.Queue,
        stock_service: StockService,
        alert_service: AlertService,
        batch_size: int = 100,
        batch_timeout: float = 1.0,
    ):
        self.queue = queue
        self._stock_service = stock_service
        self._alert_service = alert_service
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.batch: list[StockPriceCreate] = []
        self.is_running = False

    async def _process_message(self, message: Dict[str, Any]) -> None:
        """Process a single message and check for alerts."""
        try:
            symbol = message.get("id", "UNKNOWN")
            price = float(message.get("price", 0.0))
            volume = int(message.get("volume", 0))
            change_percent = float(message.get("change_percent", 0.0))
            timestamp_ms = message.get("time", str(int(datetime.now().timestamp() * 1000)))
            timestamp = datetime.fromtimestamp(int(timestamp_ms) / 1000)

            record = StockPriceCreate(
                timestamp=timestamp,
                symbol=symbol,
                price=price,
                volume=volume,
                change_percent=change_percent,
            )
            self.batch.append(record)

            # Check alert condition
            if self._alert_service.check_alert_condition(symbol, price, change_percent):
                alert = self._alert_service.create_alert(symbol, price, change_percent, timestamp)
                logger.warning(f"ALERT: {symbol} dropped {change_percent:.2f}% to ${price:.2f}")
                await self._alert_service.trigger_alert(alert)

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def _flush_batch(self) -> None:
        """Write accumulated batch to database via service."""
        if not self.batch:
            return

        try:
            self._stock_service.save_prices(self.batch)
            logger.debug(f"Flushed {len(self.batch)} records")
            self.batch = []
        except Exception as e:
            logger.error(f"Error flushing batch: {e}")

    async def run(self) -> None:
        """Main processing loop."""
        self.is_running = True
        logger.info("Stream processor started")

        last_flush = asyncio.get_event_loop().time()

        while self.is_running:
            try:
                # Wait for message with timeout
                try:
                    message = await asyncio.wait_for(
                        self.queue.get(), timeout=self.batch_timeout
                    )
                    await self._process_message(message)
                    self.queue.task_done()
                except asyncio.TimeoutError:
                    pass  # No message, will check batch timeout

                # Check if we should flush the batch
                current_time = asyncio.get_event_loop().time()
                should_flush_by_size = len(self.batch) >= self.batch_size
                should_flush_by_time = (
                    current_time - last_flush >= self.batch_timeout
                )

                if should_flush_by_size or should_flush_by_time:
                    await self._flush_batch()
                    last_flush = current_time

            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                await asyncio.sleep(1)  # Back off on error

        logger.info("Stream processor stopped")

    async def stop(self) -> None:
        """Stop the processor."""
        self.is_running = False
        # Flush any remaining records
        await self._flush_batch()
