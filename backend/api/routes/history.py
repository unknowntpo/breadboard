"""Historical data endpoints."""
from fastapi import APIRouter, Depends, HTTPException
import logging

from backend.api.schemas import HistoricalDataListResponse, HistoricalDataResponse
from backend.api.dependencies import get_historical_service
from backend.services.historical_service import HistoricalService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["history"])


@router.get("/history", response_model=HistoricalDataListResponse)
async def get_history(
    symbol: str,
    start: str,
    end: str,
    service: HistoricalService = Depends(get_historical_service)
) -> HistoricalDataListResponse:
    """Get historical OHLCV data for a symbol."""
    try:
        data = service.get_historical_data(symbol, start, end)
        return HistoricalDataListResponse(
            symbol=symbol.upper(),
            start_date=start,
            end_date=end,
            records=[
                HistoricalDataResponse(
                    date=str(d.date),
                    symbol=d.symbol,
                    open=d.open,
                    high=d.high,
                    low=d.low,
                    close=d.close,
                    volume=d.volume,
                )
                for d in data
            ],
            count=len(data),
        )
    except Exception as e:
        logger.error(f"Error getting history for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
