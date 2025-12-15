"""Domain entities - core business objects."""
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field


class StockPrice(BaseModel):
    """Real-time stock price entity."""
    timestamp: datetime
    symbol: str
    price: float
    volume: int = 0
    change_percent: float = 0.0

    class Config:
        from_attributes = True


class HistoricalData(BaseModel):
    """Daily OHLCV data entity."""
    date: date
    symbol: str
    open: float = Field(alias="open_price")
    high: float
    low: float
    close: float
    volume: int

    class Config:
        from_attributes = True
        populate_by_name = True


class Alert(BaseModel):
    """Price alert entity."""
    type: str = "price_drop"
    symbol: str
    price: float
    change_percent: float
    timestamp: datetime
    message: str


class StockPriceCreate(BaseModel):
    """DTO for creating stock price records."""
    symbol: str
    price: float
    volume: int = 0
    change_percent: float = 0.0
    timestamp: Optional[datetime] = None


class HistoricalDataCreate(BaseModel):
    """DTO for creating historical data records."""
    symbol: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
