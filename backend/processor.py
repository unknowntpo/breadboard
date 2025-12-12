import asyncio
from typing import Dict, Any, Optional, Set
from datetime import datetime
import logging

from backend.db import db_client

logger = logging.getLogger(__name__)


class StreamProcessor:
    """Process stock price messages from the queue and write to ClickHouse."""

    def __init__(
        self,
        queue: asyncio.Queue,
        batch_size: int = 100,
        batch_timeout: float = 1.0,
        alert_threshold: float = -5.0,
    ):
        self.queue = queue
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.alert_threshold = alert_threshold  # Alert on price drop >= 5%
        self.batch: list[Dict[str, Any]] = []
        self.alert_callbacks: Set[callable] = set()
        self.is_running = False

    def register_alert_callback(self, callback: callable) -> None:
        """Register a callback to be called when an alert is triggered."""
        self.alert_callbacks.add(callback)

    def unregister_alert_callback(self, callback: callable) -> None:
        """Unregister an alert callback."""
        self.alert_callbacks.discard(callback)

    async def _trigger_alert(self, alert_data: Dict[str, Any]) -> None:
        """Trigger all registered alert callbacks."""
        for callback in self.alert_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert_data)
                else:
                    callback(alert_data)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")

    async def _process_message(self, message: Dict[str, Any]) -> None:
        """Process a single message and check for alerts."""
        try:
            # Extract relevant fields
            symbol = message.get("id", "UNKNOWN")
            price = float(message.get("price", 0.0))
            volume = int(message.get("volume", 0))
            change_percent = float(message.get("change_percent", 0.0))
            timestamp_ms = message.get("time", str(int(datetime.now().timestamp() * 1000)))

            # Convert timestamp from milliseconds to datetime
            timestamp = datetime.fromtimestamp(int(timestamp_ms) / 1000)

            # Create record for batch insert
            record = {
                "timestamp": timestamp,
                "symbol": symbol,
                "price": price,
                "volume": volume,
                "change_percent": change_percent,
            }

            self.batch.append(record)

            # Check for alert condition (price drop >= threshold)
            if change_percent <= self.alert_threshold:
                alert_data = {
                    "type": "price_drop",
                    "symbol": symbol,
                    "price": price,
                    "change_percent": change_percent,
                    "timestamp": timestamp.isoformat(),
                    "message": f"Alert: {symbol} dropped {change_percent:.2f}%",
                }
                logger.warning(
                    f"ALERT: {symbol} dropped {change_percent:.2f}% to ${price:.2f}"
                )
                await self._trigger_alert(alert_data)

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    async def _flush_batch(self) -> None:
        """Write accumulated batch to ClickHouse."""
        if not self.batch:
            return

        try:
            db_client.insert_stock_prices_batch(self.batch)
            logger.debug(f"Flushed {len(self.batch)} records to ClickHouse")
            self.batch = []
        except Exception as e:
            logger.error(f"Error flushing batch to ClickHouse: {e}")
            # Keep batch for retry on next iteration

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
