"""Yahoo Finance WebSocket client."""
import asyncio
import json
import logging
from typing import List, Callable, Optional

import websockets
from backend.infrastructure import yahoo_websocket_client

logger = logging.getLogger(__name__)


class YahooWebSocketClient:
    """Yahoo Finance WebSocket client with reconnection."""

    def __init__(
        self,
        symbols: List[str],
        queue: asyncio.Queue,
        broadcast_callback: Callable,
    ):
        self._symbols = symbols
        self._queue = queue
        self._broadcast = broadcast_callback
        self._url = "wss://streamer.finance.yahoo.com/"
        self._headers = {"Origin": "https://finance.yahoo.com"}

    async def run(self) -> None:
        """Main connection loop with reconnection."""
        while True:
            try:
                async with websockets.connect(
                    self._url, additional_headers=self._headers
                ) as ws:
                    logger.info("Connected to Yahoo Finance WebSocket")
                    await ws.send(json.dumps({"subscribe": self._symbols}))
                    logger.info(f"Subscribed to {len(self._symbols)} symbols")

                    async for message in ws:
                        try:
                            decoded = yahoo_websocket_client.decode_message(message)
                            if decoded:
                                try:
                                    self._queue.put_nowait(decoded)
                                except asyncio.QueueFull:
                                    logger.warning("Queue full, dropping message")
                                await self._broadcast({
                                    "type": "price_update",
                                    "data": decoded,
                                })
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")

            except Exception as e:
                logger.error(f"Yahoo WebSocket error: {e}")
                logger.info("Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
