"""
Tests for WebSocket manager service
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
import asyncio
import json

from app.services.websocket_manager import WebSocketManager
from fastapi import WebSocket


class MockWebSocket:
    """Mock WebSocket for testing"""
    def __init__(self):
        self.messages = []
        self.closed = False
        
    async def accept(self):
        """Accept the WebSocket connection"""
        pass
        
    async def send_text(self, text: str):
        if not self.closed:
            self.messages.append(text)
    
    async def send_json(self, data: dict):
        if not self.closed:
            self.messages.append(json.dumps(data))
    
    async def close(self):
        self.closed = True


@pytest.fixture
def ws_manager():
    """Create a fresh WebSocketManager for each test"""
    return WebSocketManager()


@pytest.mark.asyncio
async def test_websocket_manager_connect(ws_manager):
    """Test connecting a WebSocket client"""
    mock_ws = MockWebSocket()
    
    await ws_manager.connect(mock_ws)
    
    assert mock_ws in ws_manager.active_connections


@pytest.mark.asyncio  
async def test_websocket_manager_disconnect(ws_manager):
    """Test disconnecting a WebSocket client"""
    mock_ws = MockWebSocket()
    
    await ws_manager.connect(mock_ws)
    assert mock_ws in ws_manager.active_connections
    
    await ws_manager.disconnect(mock_ws)
    assert mock_ws not in ws_manager.active_connections


@pytest.mark.asyncio
async def test_websocket_manager_broadcast(ws_manager):
    """Test broadcasting a message to all clients"""
    mock_ws1 = MockWebSocket()
    mock_ws2 = MockWebSocket() 
    
    await ws_manager.connect(mock_ws1)
    await ws_manager.connect(mock_ws2)
    
    test_data = {"type": "stats", "data": {"isRunning": True}}
    # Use _send_immediate to bypass throttling
    await ws_manager._send_immediate(test_data)
    
    # Check that both received a message containing the type
    assert len(mock_ws1.messages) > 0
    assert len(mock_ws2.messages) > 0
    assert "stats" in mock_ws1.messages[0]
    assert "stats" in mock_ws2.messages[0]


@pytest.mark.asyncio
async def test_websocket_manager_broadcast_with_disconnected_client(ws_manager):
    """Test broadcasting when one client fails to receive"""
    mock_ws1 = MockWebSocket()
    mock_ws2 = MockWebSocket()
    
    await ws_manager.connect(mock_ws1) 
    await ws_manager.connect(mock_ws2)
    
    # Make ws1 raise an error on send
    async def failing_send(text):
        raise Exception("Connection lost")
    mock_ws1.send_text = failing_send
    
    test_data = {"type": "test", "message": "hello"}
    await ws_manager._send_immediate(test_data)
    
    # Disconnected client should be removed
    assert mock_ws1 not in ws_manager.active_connections
    assert mock_ws2 in ws_manager.active_connections


@pytest.mark.asyncio
async def test_websocket_manager_broadcast_logs(ws_manager):
    """Test broadcasting log messages"""
    mock_ws = MockWebSocket()
    await ws_manager.connect(mock_ws)
    
    test_log = "INFO: Test log message"
    await ws_manager.broadcast_log(test_log)
    
    # Check that message contains the log
    assert len(mock_ws.messages) > 0
    received = json.loads(mock_ws.messages[0])
    assert received["type"] == "log"
    assert received["message"] == test_log


@pytest.mark.asyncio 
async def test_websocket_manager_start_stop_log_broadcasting(ws_manager):
    """Test starting and stopping log broadcasting"""
    # Start log broadcasting
    await ws_manager.start_log_broadcasting()
    assert ws_manager._log_broadcast_task is not None
    
    # Stop log broadcasting  
    await ws_manager.stop_log_broadcasting()
    # Task should be None or cancelled
    assert ws_manager._log_broadcast_task is None


@pytest.mark.asyncio
async def test_websocket_manager_cleanup(ws_manager):
    """Test cleanup removes all clients"""
    mock_ws1 = MockWebSocket()
    mock_ws2 = MockWebSocket()
    
    await ws_manager.connect(mock_ws1)
    await ws_manager.connect(mock_ws2)
    
    assert len(ws_manager.active_connections) == 2
    
    await ws_manager.cleanup()
    
    assert len(ws_manager.active_connections) == 0
    assert mock_ws1.closed
    assert mock_ws2.closed