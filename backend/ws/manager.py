import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.connections: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.add(ws)
        logger.info(f"Client connected. Total: {len(self.connections)}")

    def disconnect(self, ws: WebSocket):
        self.connections.discard(ws)
        logger.info(f"Client disconnected. Total: {len(self.connections)}")

    async def broadcast(self, event_type: str, data: dict):
        message = json.dumps({"type": event_type, "data": data, "timestamp": datetime.now(timezone.utc).isoformat()})
        dead = set()
        for ws in self.connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        self.connections -= dead


manager = ConnectionManager()
