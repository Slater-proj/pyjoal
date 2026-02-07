"""
Tests for notification_service.py
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.notification_service import (
    NotificationService,
    NotificationLevel,
    NotificationEvent,
    DEFAULT_NOTIFICATION_CONFIG,
)


def _make_service():
    return NotificationService()


class TestNotificationServiceInit:
    def test_default_config(self):
        svc = _make_service()
        assert svc is not None

    def test_notification_level_values(self):
        assert NotificationLevel.INFO.value == "info"
        assert NotificationLevel.WARNING.value == "warning"
        assert NotificationLevel.ERROR.value == "error"
        assert NotificationLevel.SUCCESS.value == "success"

    def test_notification_event_values(self):
        assert NotificationEvent.SYSTEM_START is not None
        assert NotificationEvent.TEST is not None

    def test_default_config_structure(self):
        assert "enabled" in DEFAULT_NOTIFICATION_CONFIG
        assert "gotify" in DEFAULT_NOTIFICATION_CONFIG
        assert "webhook" in DEFAULT_NOTIFICATION_CONFIG
        assert "events" in DEFAULT_NOTIFICATION_CONFIG


class TestNotificationSending:
    @pytest.mark.asyncio
    async def test_send_disabled(self):
        """When notifications are disabled, notify should be a no-op"""
        svc = _make_service()
        svc._config = {"enabled": False, "events": {"test": False}, "gotify": {"enabled": False}, "webhook": {"enabled": False}}
        # Should not raise
        await svc.notify(
            event=NotificationEvent.TEST,
            title="Test",
            message="Hello",
            level=NotificationLevel.INFO,
        )

    @pytest.mark.asyncio
    async def test_send_gotify_success(self):
        svc = _make_service()
        svc._config = {
            "enabled": True,
            "gotify": {"enabled": True, "url": "http://localhost:8080", "token": "test"},
            "webhook": {"enabled": False, "url": "", "method": "POST", "headers": {}},
            "events": {"test": True},
        }
        with patch("httpx.AsyncClient") as MockClient:
            mock_instance = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_instance.post = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_instance

            await svc.notify(
                event=NotificationEvent.TEST,
                title="Test",
                message="Hello",
                level=NotificationLevel.INFO,
            )


class TestEventFiltering:
    def test_event_disabled(self):
        svc = _make_service()
        svc._config = {
            "enabled": True,
            "events": {"system_start": False},
            "gotify": {"url": "", "token": ""},
            "webhook": {"url": "", "method": "POST", "headers": {}},
        }
        # is_event_enabled should return False
        result = svc.is_event_enabled(NotificationEvent.SYSTEM_START)
        assert result is False

    def test_event_enabled(self):
        svc = _make_service()
        svc._config = {
            "enabled": True,
            "events": {"test": True},
            "gotify": {"url": "", "token": ""},
            "webhook": {"url": "", "method": "POST", "headers": {}},
        }
        result = svc.is_event_enabled(NotificationEvent.TEST)
        assert result is True
