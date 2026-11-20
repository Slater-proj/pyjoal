"""
Tests for tracker rejections ('failure reason') and upload/archive name collisions.

- permanent refusals (unregistered torrent, bad passkey...) stop the torrent,
  keep it paused, notify once; resume retries
- transient refusals are retried with backoff, never counted as success
- multi-tracker: a refusal from one tracker moves on to the next
- uploading a torrent never overwrites an existing file
"""
import asyncio
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import bencodepy
import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SECRET_TOKEN", "test-secret-token")

from app.core.config import settings  # noqa: E402
from app.core.tracker_announcer import (  # noqa: E402
    TorrentRejectedError,
    TrackerAnnouncer,
    TrackerFailureError,
    is_permanent_failure,
)
from app.core.tracker_manager import TrackerManager  # noqa: E402


def _make_announcer(trackers=None):
    torrent = Mock()
    torrent.name = "rejected_torrent"
    torrent.size = 10 * 1024 ** 2
    torrent.info_hash = "f" * 40
    torrent.info_hash_bytes = bytes.fromhex("f" * 40)
    trackers = trackers or ["http://private.example.com/announce"]
    torrent.primary_tracker = trackers[0]
    torrent.announce_list = [[t] for t in trackers]
    torrent.added_at = datetime.now(timezone.utc)
    client = Mock()
    client.generate_peer_id.return_value = "-qB4600-abcdefghijkl"
    client.get_session_port.return_value = 51000
    client.get_upload_rate_range.return_value = (30 * 1024, 160 * 1024)
    client.build_announce_url.return_value = "http://private.example.com/announce?x"
    client.get_request_headers.return_value = {}
    client.name = "qBittorrent"
    client.version = "4.6.0"
    with patch("app.core.tracker_announcer.stealth_service") as ss:
        ss.get_session_profile.return_value = {}
        return TrackerAnnouncer(torrent, client, {"seedingOnlyMode": True})


def _http_returning(body: bytes):
    http = AsyncMock()
    http.get.return_value = MagicMock(status_code=200, content=body)
    http.__aenter__.return_value = http
    return http


FAILURE = bencodepy.encode({b"failure reason": b"Unregistered torrent"})
TRANSIENT = bencodepy.encode({b"failure reason": b"Rate limited, slow down"})
OK = bencodepy.encode({b"interval": 1800, b"complete": 1, b"incomplete": 1})


# ---------------------------------------------------------------- classification

class TestClassification:
    @pytest.mark.parametrize("reason", [
        "Unregistered torrent", "Torrent not registered with this tracker",
        "Invalid passkey", "Passkey not found", "Your account has been disabled",
        "Client not allowed", "info_hash not found",
    ])
    def test_permanent(self, reason):
        assert is_permanent_failure(reason)

    @pytest.mark.parametrize("reason", [
        "Rate limited", "Tracker is down for maintenance", "Too many requests", "",
    ])
    def test_transient(self, reason):
        assert not is_permanent_failure(reason)


# ---------------------------------------------------------------- announce behaviour

class TestFailureReasonHandling:
    @pytest.mark.asyncio
    async def test_failure_reason_is_not_a_success(self):
        ann = _make_announcer()
        with patch("app.core.tracker_announcer.httpx.AsyncClient", return_value=_http_returning(TRANSIENT)), \
             patch("app.core.tracker_announcer.history_service"):
            with pytest.raises(TrackerFailureError):
                await ann._send_announce_stealth("started")
        assert ann.last_announce is None
        assert ann.tracker_mgr._tracker_failures["http://private.example.com/announce"] == 1

    @pytest.mark.asyncio
    async def test_single_tracker_permanent_refusal_rejects_torrent(self):
        ann = _make_announcer()
        with patch("app.core.tracker_announcer.httpx.AsyncClient", return_value=_http_returning(FAILURE)), \
             patch("app.core.tracker_announcer.history_service"):
            with pytest.raises(TorrentRejectedError):
                await ann._send_announce_stealth("started")

    @pytest.mark.asyncio
    async def test_announce_loop_stops_on_rejection(self):
        ann = _make_announcer()
        ann.is_running = True
        ann._seeding_started_at = datetime.now(timezone.utc)
        with patch("app.core.tracker_announcer.httpx.AsyncClient", return_value=_http_returning(FAILURE)), \
             patch("app.core.tracker_announcer.history_service"):
            await asyncio.wait_for(ann._announce_loop(), timeout=5)
        assert ann.is_running is False
        assert ann.rejected_reason == "Unregistered torrent"
        assert "Rejected by tracker" in ann.last_error
        assert ann.get_stats()["rejectedReason"] == "Unregistered torrent"

    @pytest.mark.asyncio
    async def test_other_tracker_used_after_refusal(self):
        ann = _make_announcer(["http://a.example.com/announce", "http://b.example.com/announce"])
        responses = iter([FAILURE, OK])

        def factory(*a, **k):
            return _http_returning(next(responses))

        with patch("app.core.tracker_announcer.httpx.AsyncClient", side_effect=factory), \
             patch("app.core.tracker_announcer.history_service"):
            await ann._send_announce_with_retry()
        assert ann.last_announce is not None
        assert ann.rejected_reason is None
        assert "http://a.example.com/announce" in ann.tracker_mgr._rejected

    @pytest.mark.asyncio
    async def test_udp_tracker_error_classified(self):
        from app.core.udp_tracker import UDPTrackerError
        ann = _make_announcer(["udp://u.example.com:6969/announce"])
        udp = MagicMock()
        udp.announce = AsyncMock(side_effect=UDPTrackerError("Tracker error: unregistered torrent"))
        ann.tracker_mgr.get_or_create_udp_tracker = MagicMock(return_value=udp)
        ann.client.generate_key.return_value = "ABCDEF01"
        with pytest.raises(TorrentRejectedError):
            await ann._send_announce_stealth()


class TestTrackerManagerRejections:
    def test_rejected_tracker_skipped_and_reset(self):
        torrent = Mock()
        torrent.name = "t"
        torrent.primary_tracker = "http://a/announce"
        torrent.announce_list = [["http://a/announce"], ["http://b/announce"]]
        mgr = TrackerManager(torrent, Mock())
        mgr.mark_tracker_rejected("http://a/announce")
        assert mgr.get_next_tracker() == "http://b/announce"
        assert not mgr.all_trackers_rejected()
        mgr.mark_tracker_rejected("http://b/announce")
        assert mgr.all_trackers_rejected()
        mgr.reset_rejections()
        assert mgr.get_next_tracker() == "http://a/announce"


# ---------------------------------------------------------------- seeder service

class TestSeederHandlesRejection:
    @pytest.mark.asyncio
    async def test_rejected_torrent_paused_notified_once_and_resumable(self):
        from app.services.seeder_service import SeederService
        svc = SeederService()
        ann = _make_announcer()
        ann.rejected_reason = "Unregistered torrent"
        svc.announcers = {"f" * 40: ann}
        with patch("app.services.seeder_service.websocket_manager.broadcast", new=AsyncMock()) as bc, \
             patch("app.services.seeder_service.notification_service") as ns, \
             patch("app.services.seeder_service.persistence_service"), \
             patch("app.core.tracker_announcer.stealth_service") as ss:
            ss.get_session_stats.return_value = {}
            ns.notify_error = AsyncMock()
            await svc._handle_rejected_torrents()
            await svc._handle_rejected_torrents()  # second pass: no duplicate notification
            assert ns.notify_error.await_count == 1
            assert bc.await_count == 1
        assert "f" * 40 in svc._paused_torrents

        # not restarted automatically by the seed limit
        svc.is_running = True
        ann.start = AsyncMock()
        await svc._ensure_simultaneous_seed_limit()
        ann.start.assert_not_awaited()

        # explicit resume clears the rejection and retries
        with patch("app.services.seeder_service.websocket_manager.broadcast", new=AsyncMock()):
            await svc.resume_torrent("f" * 40)
        assert ann.rejected_reason is None
        ann.start.assert_awaited_once()


# ---------------------------------------------------------------- upload / archive collisions

def _torrent_bytes(name: bytes) -> bytes:
    info = {b"name": name, b"length": 1024, b"piece length": 16384, b"pieces": b"\x00" * 20}
    return bencodepy.encode({b"announce": b"http://t.example.com/announce", b"info": info})


class TestUploadCollisions:
    @pytest.fixture
    def env(self, tmp_path, monkeypatch):
        monkeypatch.setattr(settings, "TORRENTS_DIR", tmp_path)
        ss = MagicMock()
        ss.announcers = {}
        ss.add_torrent = AsyncMock()
        with patch("app.api.torrents.seeder_service", ss):
            from app.main import app
            yield TestClient(app), ss, tmp_path

    def test_same_name_different_torrent_keeps_both(self, env):
        client, ss, d = env
        existing = _torrent_bytes(b"first")
        (d / "file.torrent").write_bytes(existing)
        resp = client.post("/api/torrents", headers={"X-API-Token": "test-secret-token"},
                           files={"file": ("file.torrent", _torrent_bytes(b"second"), "application/x-bittorrent")})
        assert resp.status_code == 200, resp.text
        assert (d / "file.torrent").read_bytes() == existing  # untouched
        assert (d / "file (2).torrent").exists()
        added = ss.add_torrent.await_args.args[0]
        assert added.path == d / "file (2).torrent"
        assert not list(d.glob("*.part"))

    def test_duplicate_torrent_rejected_with_409(self, env):
        client, ss, d = env
        content = _torrent_bytes(b"dup")
        from app.core.torrent_parser import Torrent
        (d / "dup.torrent").write_bytes(content)
        existing = Torrent(d / "dup.torrent")
        ss.announcers = {existing.info_hash: MagicMock(torrent=existing)}
        resp = client.post("/api/torrents", headers={"X-API-Token": "test-secret-token"},
                           files={"file": ("other-name.torrent", content, "application/x-bittorrent")})
        assert resp.status_code == 409
        ss.add_torrent.assert_not_awaited()
        assert not (d / "other-name.torrent").exists()
        assert not list(d.glob("*.part"))


class TestArchiveCollisions:
    def test_unique_archive_path(self, tmp_path):
        from app.services.torrent_manager import _unique_archive_path
        p = tmp_path / "x.torrent"
        assert _unique_archive_path(p) == p
        p.write_bytes(b"1")
        assert _unique_archive_path(p) == tmp_path / "x (2).torrent"


class TestPausedTorrentsRespected:
    @pytest.mark.asyncio
    async def test_start_skips_paused_torrents(self):
        from app.services.seeder_service import SeederService
        svc = SeederService()
        a, b = _make_announcer(), _make_announcer()
        a.start, b.start = AsyncMock(), AsyncMock()
        svc.announcers = {"a" * 40: a, "b" * 40: b}
        svc._paused_torrents.add("a" * 40)
        with patch.object(svc, "_monitor_loop", new=AsyncMock()), \
             patch("app.services.seeder_service.websocket_manager.broadcast", new=AsyncMock()), \
             patch("app.services.seeder_service.notification_service") as ns, \
             patch("app.services.seeder_service.history_service"), \
             patch("app.services.seeder_service.resource_optimizer.periodic_optimization", new=AsyncMock()):
            ns.notify_system_start = AsyncMock()
            await svc.start()
        a.start.assert_not_awaited()
        b.start.assert_awaited_once()
        svc.is_running = False

    def test_reload_retries_rejected_but_keeps_manual_pauses(self):
        from app.services.seeder_service import SeederService
        svc = SeederService()
        rejected = _make_announcer()
        rejected.rejected_reason = "Unregistered torrent"
        svc.announcers = {"r" * 40: rejected}
        svc._paused_torrents |= {"r" * 40, "m" * 40}
        svc._rejected_handled.add("r" * 40)
        svc.retry_rejected_torrents()
        assert svc._paused_torrents == {"m" * 40}
        assert rejected.rejected_reason is None
        assert not svc._rejected_handled
