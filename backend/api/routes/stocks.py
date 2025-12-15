"""Stock price endpoints."""
from fastapi import APIRouter, Depends, HTTPException
import logging

from backend.api.schemas import StockPriceResponse, RecentPricesResponse
from backend.api.dependencies import get_stock_service
from backend.services.stock_service import StockService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["stocks"])


@router.get("/stocks/{symbol}", response_model=StockPriceResponse)
async def get_stock(
    symbol: str,
    service: StockService = Depends(get_stock_service)
) -> StockPriceResponse:
    """Get latest price for a symbol."""
    try:
        price = service.get_latest_price(symbol)
        if not price:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        return StockPriceResponse(
            timestamp=price.timestamp,
            symbol=price.symbol,
            price=price.price,
            volume=price.volume,
            change_percent=price.change_percent,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stock {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stocks/{symbol}/recent", response_model=RecentPricesResponse)
async def get_recent_prices(
    symbol: str,
    limit: int = 100,
    service: StockService = Depends(get_stock_service)
) -> RecentPricesResponse:
    """Get recent price history for a symbol."""
    try:
        prices = service.get_recent_prices(symbol, limit)
        return RecentPricesResponse(
            symbol=symbol.upper(),
            records=[
                StockPriceResponse(
                    timestamp=p.timestamp,
                    symbol=p.symbol,
                    price=p.price,
                    volume=p.volume,
                    change_percent=p.change_percent,
                )
                for p in prices
            ],
            count=len(prices),
        )
    except Exception as e:
        logger.error(f"Error getting recent prices for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
