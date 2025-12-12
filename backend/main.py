import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import websockets

from backend.db import db_client
from backend.processor import StreamProcessor
import yahoo_websocket_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
SYMBOLS_TO_TRACK = [
    "AAPL", "BTC-USD", "NVDA", "TSLA", "META",
    "AMZN", "GOOGL", "MSFT", "SPY", "QQQ",
    "ETH-USD", "SOL-USD", "AMD", "NFLX", "COIN",
]

# Global state
message_queue = asyncio.Queue(maxsize=10000)
processor: Optional[StreamProcessor] = None
ws_connections: set[WebSocket] = set()
yahoo_ws_task: Optional[asyncio.Task] = None
processor_task: Optional[asyncio.Task] = None
scheduler: Optional[AsyncIOScheduler] = None


class ConnectionManager:
    """Manage WebSocket connections for broadcasting updates."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")


manager = ConnectionManager()


async def yahoo_websocket_handler():
    """Connect to Yahoo Finance WebSocket and push messages to queue."""
    url = "wss://streamer.finance.yahoo.com/"
    headers = {"Origin": "https://finance.yahoo.com"}

    logger.info(f"Connecting to Yahoo Finance WebSocket: {url}")

    while True:
        try:
            async with websockets.connect(url, additional_headers=headers) as websocket:
                logger.info("Connected to Yahoo Finance WebSocket")

                # Subscribe to symbols
                subscribe_message = json.dumps({"subscribe": SYMBOLS_TO_TRACK})
                await websocket.send(subscribe_message)
                logger.info(f"Subscribed to {len(SYMBOLS_TO_TRACK)} symbols")

                # Listen for messages
                async for message in websocket:
                    try:
                        # Decode protobuf message
                        decoded = yahoo_websocket_client.decode_message(message)

                        if decoded:
                            # Put in queue for processing
                            try:
                                message_queue.put_nowait(decoded)
                            except asyncio.QueueFull:
                                logger.warning("Queue full, dropping message")

                            # Broadcast to WebSocket clients
                            await manager.broadcast({
                                "type": "price_update",
                                "data": decoded
                            })

                    except Exception as e:
                        logger.error(f"Error processing Yahoo message: {e}")

        except Exception as e:
            logger.error(f"Yahoo WebSocket connection error: {e}")
            logger.info("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)


async def fetch_historical_data():
    """Fetch historical OHLCV data for all symbols (runs every 6 hours)."""
    logger.info("Starting historical data fetch...")

    for symbol in SYMBOLS_TO_TRACK:
        try:
            # Fetch 1 day of historical data
            data = yahoo_websocket_client.get_historical_data(symbol, period="1d")

            if data and data.get("records"):
                records_to_insert = []
                for record in data["records"]:
                    records_to_insert.append({
                        "symbol": symbol,
                        "date": record["date"],
                        "open": record["open"],
                        "high": record["high"],
                        "low": record["low"],
                        "close": record["close"],
                        "volume": record["volume"],
                    })

                db_client.insert_historical_data_batch(records_to_insert)
                logger.info(f"Inserted {len(records_to_insert)} historical records for {symbol}")

        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")

    logger.info("Historical data fetch completed")


async def alert_broadcast_callback(alert_data: Dict[str, Any]):
    """Callback to broadcast alerts to WebSocket clients."""
    await manager.broadcast({
        "type": "alert",
        "data": alert_data
    })


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global processor, yahoo_ws_task, processor_task, scheduler

    # Startup
    logger.info("Starting up FastAPI application...")

    # Connect to ClickHouse
    db_client.connect()

    # Create stream processor
    processor = StreamProcessor(
        queue=message_queue,
        batch_size=100,
        batch_timeout=1.0,
        alert_threshold=-5.0
    )

    # Register alert callback
    processor.register_alert_callback(alert_broadcast_callback)

    # Start processor task
    processor_task = asyncio.create_task(processor.run())
    logger.info("Stream processor started")

    # Start Yahoo WebSocket client
    yahoo_ws_task = asyncio.create_task(yahoo_websocket_handler())
    logger.info("Yahoo WebSocket client started")

    # Start scheduler for historical data fetch
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        fetch_historical_data,
        CronTrigger(hour="0,6,12,18"),  # Run at 0:00, 6:00, 12:00, 18:00
        id="fetch_historical",
        name="Fetch historical data every 6 hours",
        replace_existing=True
    )
    scheduler.start()
    logger.info("Scheduler started for historical data fetch")

    # Run initial historical data fetch
    asyncio.create_task(fetch_historical_data())

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down...")

    # Stop scheduler
    if scheduler:
        scheduler.shutdown()

    # Stop Yahoo WebSocket
    if yahoo_ws_task:
        yahoo_ws_task.cancel()

    # Stop processor
    if processor:
        await processor.stop()

    if processor_task:
        processor_task.cancel()

    # Disconnect from ClickHouse
    db_client.disconnect()

    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Breadboard API",
    description="Real-time stock pricing dashboard API",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "queue_size": message_queue.qsize(),
        "websocket_clients": len(manager.active_connections)
    }


@app.get("/api/v1/stocks/{symbol}")
async def get_stock(symbol: str):
    """Get latest price for a symbol."""
    try:
        price_data = db_client.get_latest_price(symbol.upper())
        if not price_data:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        return price_data
    except Exception as e:
        logger.error(f"Error getting stock {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/history")
async def get_history(symbol: str, start: str, end: str):
    """Get historical OHLCV data for a symbol."""
    try:
        data = db_client.get_historical_data(symbol.upper(), start, end)
        return {
            "symbol": symbol.upper(),
            "start_date": start,
            "end_date": end,
            "records": data,
            "count": len(data)
        }
    except Exception as e:
        logger.error(f"Error getting history for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/stocks/{symbol}/recent")
async def get_recent_prices(symbol: str, limit: int = 100):
    """Get recent price history for a symbol."""
    try:
        data = db_client.get_price_history(symbol.upper(), limit)
        return {
            "symbol": symbol.upper(),
            "records": data,
            "count": len(data)
        }
    except Exception as e:
        logger.error(f"Error getting recent prices for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time price updates and alerts."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Echo back (for ping/pong)
            await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
