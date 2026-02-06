"""
Notification Service
Pluggable notification system supporting Gotify, generic webhooks, and Apprise.
Sends alerts for errors, torrent completions (with bilan), and system events.
"""
import asyncio
import logging
import json
from typing import Optional, Dict
from enum import Enum
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationLevel(str, Enum):
    """Notification priority levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class NotificationEvent(str, Enum):
    """Events that can trigger notifications"""
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    TORRENT_ARCHIVED = "torrent_archived"
    ANNOUNCE_ERROR = "announce_error"
    TRACKER_ERROR = "tracker_error"
    SYSTEM_ERROR = "system_error"
    TEST = "test"


# Default config
DEFAULT_NOTIFICATION_CONFIG = {
    "enabled": False,
    "gotify": {
        "enabled": False,
        "url": "",
        "token": "",
    },
    "webhook": {
        "enabled": False,
        "url": "",
        "method": "POST",
        "headers": {},
    },
    "events": {
        "system_start": True,
        "system_stop": True,
        "torrent_archived": True,
        "announce_error": False,
        "tracker_error": True,
        "system_error": True,
    },
    "rate_limit": {
        "max_per_minute": 10,
        "cooldown_seconds": 5,
    },
}


class NotificationService:
    """Manages notifications with pluggable backends and rate limiting."""

    def __init__(self):
        self._config: Dict = {}
        self._config_path: Optional[Path] = None
        self._last_sent: Dict[str, float] = {}  # event_type -> timestamp
        self._sent_count_minute: int = 0
        self._minute_reset: float = 0
        self._client: Optional[httpx.AsyncClient] = None

    def load(self):
        """Load notification config from file."""
        self._config_path = settings.CONFIG_DIR / "notifications.json"
        if self._config_path.exists():
            try:
                with open(self._config_path, "r") as f:
                    saved = json.load(f)
                # Merge with defaults for any missing keys
                self._config = {**DEFAULT_NOTIFICATION_CONFIG, **saved}
                # Deep merge nested dicts
                for key in ("gotify", "webhook", "events", "rate_limit"):
                    if key in DEFAULT_NOTIFICATION_CONFIG:
                        self._config[key] = {
                            **DEFAULT_NOTIFICATION_CONFIG[key],
                            **saved.get(key, {}),
                        }
                logger.info(f"📨 Notification config loaded from {self._config_path}")
            except Exception as e:
                logger.error(f"Failed to load notification config: {e}")
                self._config = dict(DEFAULT_NOTIFICATION_CONFIG)
        else:
            self._config = dict(DEFAULT_NOTIFICATION_CONFIG)
            logger.info("📨 No notification config found, using defaults (disabled)")

    def save(self):
        """Persist config to file."""
        if not self._config_path:
            return
        try:
            tmp = self._config_path.with_suffix(".tmp")
            with open(tmp, "w") as f:
                json.dump(self._config, f, indent=2)
            tmp.rename(self._config_path)
            logger.debug("Notification config saved")
        except Exception as e:
            logger.error(f"Failed to save notification config: {e}")

    @property
    def config(self) -> Dict:
        return dict(self._config)

    def update_config(self, new_config: Dict):
        """Update notification config and persist."""
        # Deep merge
        for key, value in new_config.items():
            if isinstance(value, dict) and key in self._config and isinstance(self._config[key], dict):
                self._config[key].update(value)
            else:
                self._config[key] = value
        self.save()
        logger.info("📨 Notification config updated")

    def is_enabled(self) -> bool:
        """Check if notifications are globally enabled."""
        return self._config.get("enabled", False)

    def is_event_enabled(self, event: NotificationEvent) -> bool:
        """Check if a specific event type is enabled."""
        if not self.is_enabled():
            return False
        events = self._config.get("events", {})
        return events.get(event.value, False)

    def _check_rate_limit(self, event: NotificationEvent) -> bool:
        """Check if we're within rate limits. Returns True if allowed."""
        now = asyncio.get_event_loop().time()
        rate_limit = self._config.get("rate_limit", {})
        max_per_min = rate_limit.get("max_per_minute", 10)
        cooldown = rate_limit.get("cooldown_seconds", 5)

        # Reset per-minute counter
        if now - self._minute_reset >= 60:
            self._sent_count_minute = 0
            self._minute_reset = now

        if self._sent_count_minute >= max_per_min:
            logger.warning(f"Rate limit reached ({max_per_min}/min), skipping notification")
            return False

        # Per-event cooldown
        last = self._last_sent.get(event.value, 0)
        if now - last < cooldown:
            logger.debug(f"Cooldown active for {event.value}, skipping")
            return False

        return True

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Backends
    # ------------------------------------------------------------------

    async def _send_gotify(self, title: str, message: str, priority: int = 5) -> bool:
        """Send notification via Gotify."""
        gotify = self._config.get("gotify", {})
        url = gotify.get("url", "").rstrip("/")
        token = gotify.get("token", "")

        if not url or not token:
            logger.warning("Gotify not configured (missing url or token)")
            return False

        endpoint = f"{url}/message?token={token}"
        payload = {
            "title": title,
            "message": message,
            "priority": priority,
        }

        try:
            client = await self._get_client()
            resp = await client.post(endpoint, json=payload)
            if resp.status_code == 200:
                logger.info(f"📨 Gotify notification sent: {title}")
                return True
            else:
                logger.error(f"Gotify error {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Gotify send failed: {e}")
            return False

    async def _send_webhook(self, title: str, message: str, data: Dict) -> bool:
        """Send notification via generic webhook."""
        webhook = self._config.get("webhook", {})
        url = webhook.get("url", "")
        method = webhook.get("method", "POST").upper()
        headers = webhook.get("headers", {})

        if not url:
            logger.warning("Webhook not configured (missing url)")
            return False

        payload = {
            "title": title,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "pyjoal",
            **data,
        }

        try:
            client = await self._get_client()
            if method == "POST":
                resp = await client.post(url, json=payload, headers=headers)
            else:
                resp = await client.request(method, url, json=payload, headers=headers)

            if 200 <= resp.status_code < 300:
                logger.info(f"📨 Webhook notification sent: {title}")
                return True
            else:
                logger.error(f"Webhook error {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Webhook send failed: {e}")
            return False

    # ------------------------------------------------------------------
    # Public notification API
    # ------------------------------------------------------------------

    async def notify(
        self,
        event: NotificationEvent,
        title: str,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        data: Optional[Dict] = None,
    ):
        """Send notification through all enabled backends.

        Args:
            event: Event type (used for filtering and rate limiting)
            title: Notification title
            message: Notification body
            level: Priority level
            data: Extra data for webhook payload
        """
        if not self.is_event_enabled(event) and event != NotificationEvent.TEST:
            return

        if not self._check_rate_limit(event):
            return

        data = data or {}

        # Map level to Gotify priority
        gotify_priority = {
            NotificationLevel.INFO: 4,
            NotificationLevel.WARNING: 6,
            NotificationLevel.ERROR: 8,
            NotificationLevel.SUCCESS: 5,
        }.get(level, 5)

        results = []

        # Send via Gotify
        if self._config.get("gotify", {}).get("enabled"):
            results.append(await self._send_gotify(title, message, gotify_priority))

        # Send via Webhook
        if self._config.get("webhook", {}).get("enabled"):
            results.append(await self._send_webhook(title, message, {**data, "level": level.value, "event": event.value}))

        # Record rate limit tracking
        now = asyncio.get_event_loop().time()
        self._last_sent[event.value] = now
        self._sent_count_minute += 1

        if results:
            success = sum(1 for r in results if r)
            logger.debug(f"Notification '{title}': {success}/{len(results)} backends succeeded")

    # ------------------------------------------------------------------
    # Convenience methods for specific events
    # ------------------------------------------------------------------

    async def notify_system_start(self, torrents_count: int):
        """Send notification when seeding starts."""
        await self.notify(
            NotificationEvent.SYSTEM_START,
            "🟢 PyJOAL Started",
            f"Seeding started with {torrents_count} torrent(s)",
            NotificationLevel.SUCCESS,
            {"torrents_count": torrents_count},
        )

    async def notify_system_stop(self):
        """Send notification when seeding stops."""
        await self.notify(
            NotificationEvent.SYSTEM_STOP,
            "🔴 PyJOAL Stopped",
            "Seeding service has been stopped",
            NotificationLevel.WARNING,
        )

    async def notify_torrent_archived(
        self,
        torrent_name: str,
        reason: str,
        ratio: float,
        uploaded_bytes: int,
        seeding_time_seconds: int,
    ):
        """Send notification when a torrent is archived with full bilan."""
        hours = seeding_time_seconds / 3600
        uploaded_mb = uploaded_bytes / (1024 * 1024)

        if uploaded_mb >= 1024:
            uploaded_str = f"{uploaded_mb / 1024:.2f} GB"
        else:
            uploaded_str = f"{uploaded_mb:.1f} MB"

        if hours >= 24:
            time_str = f"{hours / 24:.1f} days"
        elif hours >= 1:
            time_str = f"{hours:.1f} hours"
        else:
            time_str = f"{seeding_time_seconds / 60:.0f} min"

        message = (
            f"📦 {torrent_name}\n"
            f"Reason: {reason}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"📊 Ratio: {ratio:.2f}\n"
            f"📤 Uploaded: {uploaded_str}\n"
            f"⏱️ Seeding time: {time_str}"
        )

        await self.notify(
            NotificationEvent.TORRENT_ARCHIVED,
            f"📦 Torrent Archived: {torrent_name[:40]}",
            message,
            NotificationLevel.INFO,
            {
                "torrent_name": torrent_name,
                "reason": reason,
                "ratio": ratio,
                "uploaded_bytes": uploaded_bytes,
                "seeding_time_seconds": seeding_time_seconds,
            },
        )

    async def notify_error(self, error_type: str, message: str, details: Optional[Dict] = None):
        """Send notification for errors."""
        event = {
            "announce": NotificationEvent.ANNOUNCE_ERROR,
            "tracker": NotificationEvent.TRACKER_ERROR,
        }.get(error_type, NotificationEvent.SYSTEM_ERROR)

        await self.notify(
            event,
            f"⚠️ PyJOAL Error: {error_type}",
            message,
            NotificationLevel.ERROR,
            details,
        )

    async def send_test(self) -> bool:
        """Send a test notification to verify config."""
        # Temporarily override event check
        old_enabled = self._config.get("enabled", False)
        self._config["enabled"] = True
        try:
            await self.notify(
                NotificationEvent.TEST,
                "🧪 PyJOAL Test",
                "This is a test notification from PyJOAL.\nIf you see this, notifications are working!",
                NotificationLevel.INFO,
                {"test": True},
            )
            return True
        finally:
            self._config["enabled"] = old_enabled


# Global singleton
notification_service = NotificationService()
