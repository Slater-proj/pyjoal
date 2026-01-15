"""
WebSocket Manager
Manages WebSocket connections and broadcasts
"""
from fastapi import WebSocket
from typing import List, Dict
import json
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        """Initialize manager"""
        self.active_connections: List[WebSocket] = []
        self._log_broadcast_task: asyncio.Task | None = None
        self._running = False
    
    async def start_log_broadcasting(self):
        """Start broadcasting logs to WebSocket clients"""
        if self._running:
            return
        
        self._running = True
        self._log_broadcast_task = asyncio.create_task(self._log_broadcast_loop())
        logger.info("📡 Started log broadcasting")
    
    async def stop_log_broadcasting(self):
        """Stop broadcasting logs"""
        self._running = False
        if self._log_broadcast_task:
            self._log_broadcast_task.cancel()
            try:
                await self._log_broadcast_task
            except asyncio.CancelledError:
                pass
        logger.info("📡 Stopped log broadcasting")
    
    async def _log_broadcast_loop(self):
        """Background task to broadcast logs to WebSocket clients"""
        from app.services.log_stream_service import log_handler
        
        try:
            while self._running:
                # Get new logs (non-blocking)
                new_logs = log_handler.get_new_logs(timeout=0.5)
                
                if new_logs and self.active_connections:
                    # Broadcast logs to all connected clients
                    await self.broadcast({
                        "type": "logs",
                        "data": new_logs
                    })
                
                # Small sleep to prevent CPU spinning
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in log broadcast loop: {e}", exc_info=True)
    
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
