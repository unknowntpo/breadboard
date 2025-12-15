"""FastAPI application - minimal setup with dependency injection."""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.dependencies import init_services, get_stock_service, get_alert_service
from backend.api.routes import health, stocks, history
from backend.api.websocket.realtime import router as ws_router, manager
from backend.repository.clickhouse_client import ClickHouseConnection
from backend.infrastructure.yahoo_client import YahooWebSocketClient
from backend.infrastructure.scheduler import setup_scheduler
from backend.processor import StreamProcessor

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

# Global state (minimal)
message_queue = asyncio.Queue(maxsize=10000)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("Starting application...")

    # Initialize database connection
    connection = ClickHouseConnection()
    connection.connect()

    # Initialize services with DI
    init_services(connection)

    # Set health check dependencies
    health.set_health_dependencies(message_queue, manager)

    # Create processor with DI
    processor = StreamProcessor(
        queue=message_queue,
        stock_service=get_stock_service(),
        alert_service=get_alert_service(),
    )

    # Register WebSocket broadcast for alerts
    async def broadcast_alert(alert):
        await manager.broadcast({"type": "alert", "data": alert.model_dump()})

    get_alert_service().register_callback(broadcast_alert)

    # Start processor
    processor_task = asyncio.create_task(processor.run())

    # Start Yahoo WebSocket client
    yahoo_client = YahooWebSocketClient(
        symbols=SYMBOLS_TO_TRACK,
        queue=message_queue,
        broadcast_callback=manager.broadcast,
    )
    yahoo_task = asyncio.create_task(yahoo_client.run())

    # Setup scheduler
    scheduler = setup_scheduler(SYMBOLS_TO_TRACK)
    scheduler.start()

    # Run initial historical fetch
    asyncio.create_task(
        __import__("backend.infrastructure.scheduler", fromlist=["fetch_historical_data"])
        .fetch_historical_data(SYMBOLS_TO_TRACK)
    )

    logger.info("Application started")
    yield

    # Shutdown
    logger.info("Shutting down...")
    scheduler.shutdown()
    yahoo_task.cancel()
    await processor.stop()
    processor_task.cancel()
    connection.disconnect()
    logger.info("Shutdown complete")


# Create app
app = FastAPI(
    title="Breadboard API",
    description="Real-time stock pricing dashboard API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health.router)
app.include_router(stocks.router)
app.include_router(history.router)
app.include_router(ws_router)
