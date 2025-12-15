"""Airflow tasks for historical data fetching."""
from typing import List
import logging

from backend.infrastructure import yahoo_websocket_client
from backend.api.dependencies import get_historical_service
from backend.domain.entities import HistoricalDataCreate

logger = logging.getLogger(__name__)

# Default symbols to fetch
DEFAULT_SYMBOLS = [
    "AAPL", "BTC-USD", "NVDA", "TSLA", "META",
    "AMZN", "GOOGL", "MSFT", "SPY", "QQQ",
    "ETH-USD", "SOL-USD", "AMD", "NFLX", "COIN",
]


def fetch_symbol_historical_data(symbol: str, period: str = "1d") -> dict:
    """Fetch historical data for a single symbol."""
    try:
        logger.info(f"Fetching historical data for {symbol} (period: {period})...")
        data = yahoo_websocket_client.get_historical_data(symbol, period=period)

        if data and data.get("records"):
            service = get_historical_service()
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
            logger.info(f"Successfully inserted {len(records)} records for {symbol}")
            return {
                "status": "success",
                "symbol": symbol,
                "records_inserted": len(records),
            }
        else:
            logger.warning(f"No records found for {symbol}")
            return {
                "status": "no_data",
                "symbol": symbol,
                "records_inserted": 0,
            }
    except Exception as e:
        logger.error(f"Error fetching historical data for {symbol}: {e}")
        return {
            "status": "error",
            "symbol": symbol,
            "error": str(e),
        }


def fetch_all_symbols_historical_data(symbols: List[str] = None, period: str = "1d") -> dict:
    """Fetch historical data for all symbols."""
    if symbols is None:
        symbols = DEFAULT_SYMBOLS

    logger.info(f"Starting historical data fetch for {len(symbols)} symbols...")
    results = []

    for symbol in symbols:
        result = fetch_symbol_historical_data(symbol, period)
        results.append(result)

    logger.info("Historical data fetch completed")
    return {
        "status": "completed",
        "total_symbols": len(symbols),
        "results": results,
    }
