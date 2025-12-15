"""Health check endpoint."""
import asyncio
from datetime import datetime
from fastapi import APIRouter

from backend.api.schemas import HealthResponse

router = APIRouter()

# These will be set by main.py
message_queue: asyncio.Queue = None
connection_manager = None


def set_health_dependencies(queue: asyncio.Queue, manager) -> None:
    """Set dependencies for health endpoint."""
    global message_queue, connection_manager
    message_queue = queue
    connection_manager = manager


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        queue_size=message_queue.qsize() if message_queue else 0,
        websocket_clients=len(connection_manager.active_connections) if connection_manager else 0,
    )
