"""
WebSocket Manager
Manages WebSocket connections and broadcasts with intelligent batching
"""
from fastapi import WebSocket
from typing import List, Dict, Any
import json
import logging
import asyncio
from datetime import datetime
import time
from collections import defaultdict

from app.core.cache_manager import cache_manager

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        """Initialize manager with batching support"""
        self.active_connections: List[WebSocket] = []
        self._log_broadcast_task: asyncio.Task | None = None
        self._running = False
        
        # Batching and throttling
        self._message_buffer: Dict[str, Dict[str, Any]] = {}
        self._last_batch_send = defaultdict(float)
        self._batch_interval = 0.1  # Ultra-rapide: 100ms batching pour réactivité maximale
        self._throttle_intervals = {
            'stats_update': 1.0,      # Ultra-réactif: 1/seconde pour stats 
            'torrents_update': 1.5,   # Très réactif: 1/1.5s pour liste torrents
            'logs': 0.5               # Rapide: 2/seconde pour logs
        }
    
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
        """Background task to broadcast logs to WebSocket clients - optimized event-driven"""
        from app.services.log_stream_service import log_handler
        
        try:
            while self._running:
                # Optimized: Get logs with longer timeout to reduce CPU polling
                new_logs = log_handler.get_new_logs(timeout=1.0)  # Increased from 0.5s to 1.0s
                
                if new_logs and self.active_connections:
                    # Broadcast logs to all connected clients
                    await self.broadcast({
                        "type": "logs",
                        "data": new_logs
                    })
                
                # Optimized: Only sleep if no logs found to reduce unnecessary wake-ups
                if not new_logs:
                    await asyncio.sleep(0.5)  # Longer sleep when no activity
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
        """Broadcast message with intelligent batching and throttling"""
        message_type = message.get('type', 'unknown')
        
        # Check if we should throttle this message type
        if self._should_throttle(message_type):
            logger.debug(f"🎯 Throttled {message_type} message")
            return
        
        # Add to buffer for batching (if applicable)
        if self._should_batch(message_type):
            self._add_to_batch(message_type, message)
            return
        
        # Send immediately for time-sensitive messages
        await self._send_immediate(message)
    
    def _should_throttle(self, message_type: str) -> bool:
        """Check if message should be throttled"""
        throttle_interval = self._throttle_intervals.get(message_type, 0)
        if throttle_interval <= 0:
            return False
            
        current_time = time.time()
        last_sent = self._last_batch_send[message_type]
        
        if (current_time - last_sent) < throttle_interval:
            return True
            
        self._last_batch_send[message_type] = current_time
        return False
    
    def _should_batch(self, message_type: str) -> bool:
        """Check if message type should be batched"""
        # Batch frequent updates, send alerts/events immediately
        batchable_types = {'stats_update', 'torrents_update', 'logs'}
        return message_type in batchable_types
    
    def _add_to_batch(self, message_type: str, message: Dict):
        """Add message to batch buffer"""
        # Override previous message of same type (latest wins)
        self._message_buffer[message_type] = message
        
        # Schedule batch send if not already scheduled
        if not hasattr(self, '_batch_task') or self._batch_task.done():
            self._batch_task = asyncio.create_task(self._send_batched_delayed())
    
    async def _send_batched_delayed(self):
        """Send batched messages after delay"""
        await asyncio.sleep(self._batch_interval)
        
        if self._message_buffer:
            # Send all buffered messages
            for message_type, message in self._message_buffer.items():
                await self._send_immediate(message)
                logger.debug(f"📦 Sent batched {message_type}")
            
            # Clear buffer
            self._message_buffer.clear()
    
    async def _send_immediate(self, message: Dict):
        """Send message immediately to all connections"""
        if not self.active_connections:
            return
            
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
    
    async def broadcast_high_priority(self, message: Dict):
        """Broadcast high priority message immediately (bypass throttling)"""
        await self._send_immediate(message)
    
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
