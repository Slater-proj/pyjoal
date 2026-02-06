"""
Extended tests for notification_service - rate limiting, gotify, webhook, 
convenience methods, test sending
"""
import pytest
import time
from unittest.mock import patch, AsyncMock, MagicMock, mock_open
from pathlib import Path

from app.services.notification_service import (
    NotificationService,
    NotificationLevel,
    NotificationEvent,
    DEFAULT_NOTIFICATION_CONFIG,
)


def _make_service():
    svc = NotificationService()
    return svc


def _enabled_config(**overrides):
    base = {
        "enabled": True,
        "gotify": {"url": "http://gotify:8080", "token": "testtoken"},
        "webhook": {"url": "", "method": "POST", "headers": {}},
        "events": {
            "system_start": True,
            "system_stop": True,
            "torrent_archived": True,
            "error": True,
            "test": True,
        },
    }
    base.update(overrides)
    return base


class TestRateLimiting:
    def test_rate_limit_allows_first_call(self):
        svc = _make_service()
        assert svc._check_rate_limit(NotificationEvent.TEST) is True

    def test_rate_limit_max_per_minute(self):
        import asyncio
        svc = _make_service()
        svc._config["rate_limit"] = {"max_per_minute": 2, "cooldown_seconds": 0}
        svc._sent_count_minute = 2  # Already at limit
        svc._minute_reset = asyncio.get_event_loop().time()  # Just reset
        result = svc._check_rate_limit(NotificationEvent.TEST)
        assert result is False

    def test_rate_limit_per_event_cooldown(self):
        import asyncio
        svc = _make_service()
        svc._config["rate_limit"] = {"max_per_minute": 100, "cooldown_seconds": 60}
        now = asyncio.get_event_loop().time()
        svc._last_sent[NotificationEvent.TEST.value] = now  # Just sent
        result = svc._check_rate_limit(NotificationEvent.TEST)
        assert result is False

    def test_rate_limit_different_events(self):
        svc = _make_service()
        svc._check_rate_limit(NotificationEvent.TEST)
        # Different event should not be rate limited
        result = svc._check_rate_limit(NotificationEvent.SYSTEM_START)
        assert result is True


class TestSendGotify:
    @pytest.mark.asyncio
    async def test_send_gotify_missing_url(self):
        svc = _make_service()
        svc._config = _enabled_config(gotify={"url": "", "token": ""})
        result = await svc._send_gotify("Test", "Hello", 5)
        assert result is False

    @pytest.mark.asyncio
    async def test_send_gotify_success(self):
        svc = _make_service()
        svc._config = _enabled_config()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(svc, "_get_client", new_callable=AsyncMock, return_value=mock_client):
            result = await svc._send_gotify("Test", "Hello", 5)
        assert result is True

    @pytest.mark.asyncio
    async def test_send_gotify_http_error(self):
        svc = _make_service()
        svc._config = _enabled_config()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))

        with patch.object(svc, "_get_client", new_callable=AsyncMock, return_value=mock_client):
            result = await svc._send_gotify("Test", "Hello", 5)
        assert result is False


class TestSendWebhook:
    @pytest.mark.asyncio
    async def test_send_webhook_missing_url(self):
        svc = _make_service()
        svc._config = _enabled_config()
        result = await svc._send_webhook("Test", "Hello", {})
        assert result is False

    @pytest.mark.asyncio
    async def test_send_webhook_success(self):
        svc = _make_service()
        svc._config = _enabled_config(
            webhook={"url": "http://webhook.example.com/hook", "method": "POST", "headers": {}}
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch.object(svc, "_get_client", new_callable=AsyncMock, return_value=mock_client):
            result = await svc._send_webhook("Test", "Hello", {"key": "value"})
        assert result is True


class TestConvenienceMethods:
    @pytest.mark.asyncio
    async def test_notify_system_start(self):
        svc = _make_service()
        svc._config = _enabled_config()
        with patch.object(svc, "notify", new_callable=AsyncMock) as mock_notify:
            await svc.notify_system_start(torrents_count=5)
            mock_notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_system_stop(self):
        svc = _make_service()
        svc._config = _enabled_config()
        with patch.object(svc, "notify", new_callable=AsyncMock) as mock_notify:
            await svc.notify_system_stop()
            mock_notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_error(self):
        svc = _make_service()
        svc._config = _enabled_config()
        with patch.object(svc, "notify", new_callable=AsyncMock) as mock_notify:
            await svc.notify_error("tracker", "Tracker timeout")
            mock_notify.assert_called_once()


class TestNotifyTorrentArchived:
    @pytest.mark.asyncio
    async def test_notify_torrent_archived_gb(self):
        svc = _make_service()
        svc._config = _enabled_config()
        with patch.object(svc, "notify", new_callable=AsyncMock) as mock_notify:
            await svc.notify_torrent_archived(
                torrent_name="Big File",
                reason="Ratio target reached",
                uploaded_bytes=2 * 1024 * 1024 * 1024,  # 2 GB
                ratio=2.5,
                seeding_time_seconds=7200,  # 2 hours
            )
            mock_notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_torrent_archived_mb(self):
        svc = _make_service()
        svc._config = _enabled_config()
        with patch.object(svc, "notify", new_callable=AsyncMock) as mock_notify:
            await svc.notify_torrent_archived(
                torrent_name="Small File",
                reason="Duration limit",
                uploaded_bytes=50 * 1024 * 1024,  # 50 MB
                ratio=0.5,
                seeding_time_seconds=300,  # 5 minutes
            )
            mock_notify.assert_called_once()


class TestSendTest:
    @pytest.mark.asyncio
    async def test_send_test_default(self):
        svc = _make_service()
        svc._config = _enabled_config()
        with patch.object(svc, "_send_gotify", new_callable=AsyncMock, return_value=True):
            result = await svc.send_test()
            assert result is True

    @pytest.mark.asyncio
    async def test_send_test_with_override(self):
        svc = _make_service()
        svc._config = _enabled_config(enabled=False)
        override = _enabled_config()
        with patch.object(svc, "_send_gotify", new_callable=AsyncMock, return_value=True):
            result = await svc.send_test(override_config=override)
            assert result is True
        # Original config should be restored
        assert svc._config["enabled"] is False


class TestLoadSave:
    def test_load_creates_defaults(self):
        svc = _make_service()
        with patch("app.services.notification_service.settings") as mock_settings:
            mock_settings.CONFIG_DIR = Path("/tmp/config_test")
            with patch.object(Path, "exists", return_value=False):
                svc.load()
        assert svc._config["enabled"] is False  # Default is disabled

    def test_update_config(self):
        svc = _make_service()
        svc._config = dict(DEFAULT_NOTIFICATION_CONFIG)
        with patch.object(svc, "save"):
            svc.update_config({"enabled": True})
        assert svc._config["enabled"] is True

    def test_config_property_returns_copy(self):
        svc = _make_service()
        svc._config = {"enabled": True, "key": "value"}
        config = svc.config
        config["enabled"] = False
        assert svc._config["enabled"] is True  # Original unchanged

    def test_is_enabled(self):
        svc = _make_service()
        svc._config = {"enabled": True}
        assert svc.is_enabled() is True
        svc._config = {"enabled": False}
        assert svc.is_enabled() is False
