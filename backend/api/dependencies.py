"""FastAPI dependency injection setup."""
from typing import Optional

from backend.repository.clickhouse_client import ClickHouseConnection
from backend.repository.stock_repository import (
    ClickHouseStockPriceRepository,
    ClickHouseHistoricalRepository,
)
from backend.services.stock_service import StockService
from backend.services.historical_service import HistoricalService
from backend.services.alert_service import AlertService


# Application state (set during lifespan)
_connection: Optional[ClickHouseConnection] = None
_stock_service: Optional[StockService] = None
_historical_service: Optional[HistoricalService] = None
_alert_service: Optional[AlertService] = None


def init_services(connection: ClickHouseConnection) -> None:
    """Initialize all services with connection."""
    global _connection, _stock_service, _historical_service, _alert_service
    _connection = connection

    stock_repo = ClickHouseStockPriceRepository(connection)
    historical_repo = ClickHouseHistoricalRepository(connection)

    _stock_service = StockService(stock_repo)
    _historical_service = HistoricalService(historical_repo)
    _alert_service = AlertService(threshold=-5.0)


def get_connection() -> ClickHouseConnection:
    """Get database connection."""
    if _connection is None:
        raise RuntimeError("Services not initialized")
    return _connection


def get_stock_service() -> StockService:
    """Get stock service dependency."""
    if _stock_service is None:
        raise RuntimeError("Services not initialized")
    return _stock_service


def get_historical_service() -> HistoricalService:
    """Get historical service dependency."""
    if _historical_service is None:
        raise RuntimeError("Services not initialized")
    return _historical_service


def get_alert_service() -> AlertService:
    """Get alert service dependency."""
    if _alert_service is None:
        raise RuntimeError("Services not initialized")
    return _alert_service
