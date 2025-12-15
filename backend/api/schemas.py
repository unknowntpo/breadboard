"""API request/response schemas (DTOs)."""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


# Response models
class StockPriceResponse(BaseModel):
    """Response for single stock price."""
    timestamp: datetime
    symbol: str
    price: float
    volume: int
    change_percent: float


class HistoricalDataResponse(BaseModel):
    """Response for single historical record."""
    date: str
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class HistoricalDataListResponse(BaseModel):
    """Response for historical data list."""
    symbol: str
    start_date: str
    end_date: str
    records: List[HistoricalDataResponse]
    count: int


class RecentPricesResponse(BaseModel):
    """Response for recent price history."""
    symbol: str
    records: List[StockPriceResponse]
    count: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    queue_size: int
    websocket_clients: int


class AlertResponse(BaseModel):
    """Alert event response."""
    type: str
    symbol: str
    price: float
    change_percent: float
    timestamp: str
    message: str


# WebSocket message schemas
class WebSocketMessage(BaseModel):
    """Base WebSocket message."""
    type: str
    data: Optional[dict] = None


class PriceUpdateMessage(WebSocketMessage):
    """Real-time price update message."""
    type: str = "price_update"


class AlertMessage(WebSocketMessage):
    """Alert notification message."""
    type: str = "alert"
