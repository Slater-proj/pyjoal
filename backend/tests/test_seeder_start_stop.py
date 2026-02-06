"""Tests for seeder_service.py — start, stop, persist, monitor."""
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock
from datetime import datetime, timezone

import os
os.environ.setdefault("SECRET_TOKEN", "test-secret-token")

from app.services.seeder_service import SeederService


def _make_service():
    """Create a SeederService bypassing __init__."""
    svc = object.__new__(SeederService)
    svc._tm = MagicMock()
    svc._cfg = MagicMock()
    svc._cfg._config = {"simultaneousSeed": 2, "client": "test.client"}
    svc._cfg.config = {"simultaneousSeed": 2, "client": "test.client"}
    svc._lock = asyncio.Lock()
    svc.is_running = False
    svc.started_at = None
    svc.client = MagicMock()
    svc.file_watcher = None
    svc._monitor_task = None
    # announcers property delegates to _tm
    svc._tm.announcers = {}
    svc._tm.get_torrents.return_value = []
    svc._tm.has_torrents.return_value = False
    return svc


class TestStart:
    @pytest.mark.asyncio
    async def test_start_basic(self):
        svc = _make_service()
        ann = MagicMock()
        ann.start = AsyncMock()
        ann.is_running = False
        svc._tm.announcers = {"hash1": ann}

        with patch("app.services.seeder_service.history_service"), \
             patch("app.services.seeder_service.websocket_manager") as mock_ws, \
             patch("app.services.seeder_service.notification_service") as mock_ns, \
             patch("app.services.seeder_service.resource_optimizer") as mock_ro:
            mock_ws.broadcast = AsyncMock()
            mock_ns.notify_system_start = AsyncMock()
            mock_ro.periodic_optimization = AsyncMock()
            await svc.start()

        assert svc.is_running is True
        assert svc.started_at is not None
        ann.start.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_start_already_running(self):
        svc = _make_service()
        svc.is_running = True
        with patch("app.services.seeder_service.history_service"):
            await svc.start()
        # should return early without error


class TestStop:
    @pytest.mark.asyncio
    async def test_stop_basic(self):
        svc = _make_service()
        svc.is_running = True
        svc.started_at = datetime.now(timezone.utc)
        # Create a mock announcer
        ann = MagicMock()
        ann.stop = AsyncMock()
        ann.is_running = True
        ann.get_stats.return_value = {"uploaded": 1000, "seedingTime": 60}
        ann.torrent = MagicMock()
        ann.torrent.added_at = datetime.now(timezone.utc)
        ann.torrent.name = "test"
        svc._tm.announcers = {"h1": ann}

        with patch("app.services.seeder_service.history_service"), \
             patch("app.services.seeder_service.websocket_manager") as mock_ws, \
             patch("app.services.seeder_service.notification_service") as mock_ns, \
             patch("app.services.seeder_service.persistence_service") as mock_ps:
            mock_ws.broadcast = AsyncMock()
            mock_ns.notify_system_stop = AsyncMock()
            mock_ns.close = AsyncMock()
            mock_ps.stop_autosave = AsyncMock()
            mock_ps.update = MagicMock()
            await svc.stop()

        assert svc.is_running is False
        ann.stop.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stop_not_running(self):
        svc = _make_service()
        svc.is_running = False
        await svc.stop()  # should return early


class TestPersistAllStats:
    def test_persist_all_stats(self):
        svc = _make_service()
        ann = MagicMock()
        ann.get_stats.return_value = {"uploaded": 5000, "seedingTime": 120}
        ann.torrent.added_at = datetime.now(timezone.utc)
        ann.torrent.name = "test"
        ann.torrent.info_hash = "abc123"
        svc._tm.announcers = {"abc123": ann}

        with patch("app.services.seeder_service.persistence_service") as mock_ps:
            svc._persist_all_stats()
        mock_ps.update.assert_called_once()


class TestStartAnnouncerIfNeeded:
    @pytest.mark.asyncio
    async def test_starts_when_below_limit(self):
        svc = _make_service()
        svc._cfg.config = {"simultaneousSeed": 5, "client": "test.client"}
        ann = MagicMock()
        ann.start = AsyncMock()
        ann.is_running = False
        svc._tm.announcers = {"h1": ann}

        with patch("app.services.seeder_service.settings") as mock_s:
            mock_s.SIMULTANEOUS_SEED = 3
            await svc._start_announcer_if_needed(ann)
        ann.start.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_does_not_start_when_at_limit(self):
        svc = _make_service()
        svc._cfg.config = {"simultaneousSeed": 1, "client": "test.client"}
        running = MagicMock()
        running.is_running = True
        new_ann = MagicMock()
        new_ann.start = AsyncMock()
        new_ann.is_running = False
        svc._tm.announcers = {"h1": running, "h2": new_ann}

        with patch("app.services.seeder_service.settings") as mock_s:
            mock_s.SIMULTANEOUS_SEED = 1
            await svc._start_announcer_if_needed(new_ann)
        new_ann.start.assert_not_awaited()
