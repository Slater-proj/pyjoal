"""
WebSocket Manager
Manages WebSocket connections and broadcasts
"""
from fastapi import WebSocket
from typing import List, Dict
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        """Initialize manager"""
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        """Accept new connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"🔌 WebSocket connected (total: {len(self.active_connections)})")
    
    async def disconnect(self, websocket: WebSocket):
        """Remove connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"🔌 WebSocket disconnected (total: {len(self.active_connections)})")
    
    async def broadcast(self, message: Dict):
        """Broadcast message to all connections"""
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()
        
        # Convert to JSON
        json_message = json.dumps(message)
        
        # Send to all connections
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json_message)
            except Exception as e:
                logger.warning(f"⚠️  Failed to send to WebSocket: {e}")
                disconnected.append(connection)
        
        # Remove disconnected
        for connection in disconnected:
            await self.disconnect(connection)
    
    async def send_personal(self, websocket: WebSocket, message: Dict):
        """Send message to specific connection"""
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()
        
        json_message = json.dumps(message)
        
        try:
            await websocket.send_text(json_message)
        except Exception as e:
            print(f"⚠️  Failed to send to WebSocket: {e}")
            await self.disconnect(websocket)


# Global manager instance
websocket_manager = WebSocketManager()
