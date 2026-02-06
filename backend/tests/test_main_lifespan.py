"""Tests for main.py — lifespan, background tasks, WS endpoint."""
import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

import os
os.environ.setdefault("SECRET_TOKEN", "test-secret-token")


class TestBackgroundTorrentStartup:
    @pytest.mark.asyncio
    async def test_startup_with_torrents(self):
        from app.main import _background_torrent_startup
        with patch("app.main.seeder_service") as mock_ss, \
             patch("app.main.websocket_manager") as mock_ws:
            mock_ws.broadcast = AsyncMock()
            mock_ss.load_torrents = AsyncMock()
            mock_ss.has_torrents.return_value = True
            mock_ss.start = AsyncMock()
            await _background_torrent_startup()
        mock_ss.start.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_startup_no_torrents(self):
        from app.main import _background_torrent_startup
        with patch("app.main.seeder_service") as mock_ss, \
             patch("app.main.websocket_manager") as mock_ws:
            mock_ws.broadcast = AsyncMock()
            mock_ss.load_torrents = AsyncMock()
            mock_ss.has_torrents.return_value = False
            mock_ss.start = AsyncMock()
            await _background_torrent_startup()
        mock_ss.start.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_startup_start_fails(self):
        from app.main import _background_torrent_startup
        with patch("app.main.seeder_service") as mock_ss, \
             patch("app.main.websocket_manager") as mock_ws:
            mock_ws.broadcast = AsyncMock()
            mock_ss.load_torrents = AsyncMock()
            mock_ss.has_torrents.return_value = True
            mock_ss.start = AsyncMock(side_effect=RuntimeError("error"))
            await _background_torrent_startup()
        # Should not crash

    @pytest.mark.asyncio
    async def test_startup_exception(self):
        from app.main import _background_torrent_startup
        with patch("app.main.seeder_service") as mock_ss, \
             patch("app.main.websocket_manager") as mock_ws:
            mock_ws.broadcast = AsyncMock()
            mock_ss.load_torrents = AsyncMock(side_effect=Exception("boom"))
            await _background_torrent_startup()
        # Should broadcast error status


class TestBackgroundClientUpdate:
    @pytest.mark.asyncio
    async def test_update_success(self):
        from app.main import _background_client_update
        with patch("app.main.update_clients_on_startup", new_callable=AsyncMock):
            await _background_client_update()

    @pytest.mark.asyncio
    async def test_update_failure(self):
        from app.main import _background_client_update
        with patch("app.main.update_clients_on_startup", new_callable=AsyncMock, side_effect=Exception("fail")):
            await _background_client_update()


class TestWebSocketEndpoint:
    def test_ws_wrong_token(self):
        from app.main import app
        from starlette.testclient import TestClient
        client = TestClient(app, headers={"X-API-Token": "test-secret-token"})
        with pytest.raises(Exception):
            with client.websocket_connect("/ws?token=wrong"):
                pass

    def test_ws_valid_token_ping(self):
        from app.main import app
        from starlette.testclient import TestClient
        client = TestClient(app, headers={"X-API-Token": "test-secret-token"})
        with client.websocket_connect("/ws?token=test-secret-token") as ws:
            ws.send_text("ping")
            data = ws.receive_text()
            assert data == "pong"
