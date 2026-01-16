"""
Tests for WebSocket manager service
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
import asyncio
import json

from app.services.websocket_manager import websocket_manager
from fastapi import WebSocket


class MockWebSocket:
    """Mock WebSocket for testing"""
    def __init__(self):
        self.messages = []
        self.closed = False
        
    async def send_text(self, text: str):
        if not self.closed:
            self.messages.append(text)
    
    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_websocket_manager_connect():
    """Test connecting a WebSocket client"""
    mock_ws = MockWebSocket()
    
    await websocket_manager.connect(mock_ws)
    
    assert mock_ws in websocket_manager.clients


@pytest.mark.asyncio  
async def test_websocket_manager_disconnect():
    """Test disconnecting a WebSocket client"""
    mock_ws = MockWebSocket()
    
    await websocket_manager.connect(mock_ws)
    assert mock_ws in websocket_manager.clients
    
    await websocket_manager.disconnect(mock_ws)
    assert mock_ws not in websocket_manager.clients


@pytest.mark.asyncio
async def test_websocket_manager_broadcast():
    """Test broadcasting a message to all clients"""
    mock_ws1 = MockWebSocket()
    mock_ws2 = MockWebSocket() 
    
    await websocket_manager.connect(mock_ws1)
    await websocket_manager.connect(mock_ws2)
    
    test_data = {"type": "stats", "data": {"isRunning": True}}
    await websocket_manager.broadcast(test_data)
    
    expected_message = json.dumps(test_data)
    assert expected_message in mock_ws1.messages
    assert expected_message in mock_ws2.messages


@pytest.mark.asyncio
async def test_websocket_manager_broadcast_with_disconnected_client():
    """Test broadcasting when one client is disconnected"""
    mock_ws1 = MockWebSocket()
    mock_ws2 = MockWebSocket()
    
    await websocket_manager.connect(mock_ws1) 
    await websocket_manager.connect(mock_ws2)
    
    # Simulate one client disconnecting
    mock_ws1.closed = True
    
    test_data = {"type": "test", "message": "hello"}
    await websocket_manager.broadcast(test_data)
    
    # Disconnected client should be removed automatically
    assert mock_ws1 not in websocket_manager.clients
    assert mock_ws2 in websocket_manager.clients
    
    expected_message = json.dumps(test_data)
    assert expected_message in mock_ws2.messages


@pytest.mark.asyncio
async def test_websocket_manager_broadcast_logs():
    """Test broadcasting log messages"""
    mock_ws = MockWebSocket()
    await websocket_manager.connect(mock_ws)
    
    test_log = "INFO: Test log message"
    await websocket_manager.broadcast_log(test_log)
    
    expected_message = json.dumps({"type": "log", "message": test_log})
    assert expected_message in mock_ws.messages


@pytest.mark.asyncio 
async def test_websocket_manager_start_stop_log_broadcasting():
    """Test starting and stopping log broadcasting"""
    # Start log broadcasting
    await websocket_manager.start_log_broadcasting()
    assert websocket_manager._log_broadcast_task is not None
    
    # Stop log broadcasting  
    await websocket_manager.stop_log_broadcasting()
    assert websocket_manager._log_broadcast_task is None or websocket_manager._log_broadcast_task.cancelled()


@pytest.mark.asyncio
async def test_websocket_manager_cleanup():
    """Test cleanup removes all clients"""
    mock_ws1 = MockWebSocket()
    mock_ws2 = MockWebSocket()
    
    await websocket_manager.connect(mock_ws1)
    await websocket_manager.connect(mock_ws2)
    
    assert len(websocket_manager.clients) == 2
    
    await websocket_manager.cleanup()
    
    assert len(websocket_manager.clients) == 0
    assert mock_ws1.closed
    assert mock_ws2.closed