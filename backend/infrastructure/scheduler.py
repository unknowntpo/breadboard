"""APScheduler setup for batch jobs."""
from typing import List
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import yahoo_websocket_client

from backend.api.dependencies import get_historical_service
from backend.domain.entities import HistoricalDataCreate

logger = logging.getLogger(__name__)


async def fetch_historical_data(symbols: List[str]) -> None:
    """Fetch historical data for all symbols."""
    logger.info("Starting historical data fetch...")
    service = get_historical_service()

    for symbol in symbols:
        try:
            data = yahoo_websocket_client.get_historical_data(symbol, period="1d")
            if data and data.get("records"):
                records = [
                    HistoricalDataCreate(
                        symbol=symbol,
                        date=rec["date"],
                        open=rec["open"],
                        high=rec["high"],
                        low=rec["low"],
                        close=rec["close"],
                        volume=rec["volume"],
                    )
                    for rec in data["records"]
                ]
                service.save_historical_data(records)
                logger.info(f"Inserted {len(records)} records for {symbol}")
        except Exception as e:
            logger.error(f"Error fetching historical for {symbol}: {e}")

    logger.info("Historical data fetch completed")


def setup_scheduler(symbols: List[str]) -> AsyncIOScheduler:
    """Create and configure scheduler."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        lambda: fetch_historical_data(symbols),
        CronTrigger(hour="0,6,12,18"),
        id="fetch_historical",
        name="Fetch historical data every 6 hours",
        replace_existing=True,
    )
    return scheduler
