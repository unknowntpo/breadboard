"""WebSocket endpoint for real-time updates."""
from typing import List, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections for broadcasting."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict) -> None:
        """Broadcast message to all connected clients."""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting: {e}")


# Singleton manager
manager = ConnectionManager()


@router.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time price updates and alerts."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
