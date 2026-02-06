"""Deep tests for SimpleHealth - uptime, suggestions, tracker health, memory, cpu."""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import time
import os

os.environ.setdefault("SECRET_TOKEN", "test-secret-token")

from app.services.simple_health import SimpleHealthCheck


class TestGetUptime:
    def test_seconds(self):
        h = SimpleHealthCheck.__new__(SimpleHealthCheck)
        h.start_time = time.time() - 30  # 30s ago
        result = h._get_uptime()
        assert result["status"] == "healthy"
        assert "s" in result["value"]

    def test_minutes(self):
        h = SimpleHealthCheck.__new__(SimpleHealthCheck)
        h.start_time = time.time() - 300  # 5min ago
        result = h._get_uptime()
        assert "min" in result["value"]

    def test_hours(self):
        h = SimpleHealthCheck.__new__(SimpleHealthCheck)
        h.start_time = time.time() - 7200  # 2h ago
        result = h._get_uptime()
        assert "h" in result["value"]


class TestGetSuggestions:
    def test_no_issues(self):
        h = SimpleHealthCheck.__new__(SimpleHealthCheck)
        checks = {"memory": {"status": "healthy"}, "tracker_health": {"status": "healthy"}}
        result = h._get_suggestions(checks)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_memory_warning(self):
        h = SimpleHealthCheck.__new__(SimpleHealthCheck)
        checks = {"memory": {"status": "warning"}}
        result = h._get_suggestions(checks)
        assert any("memory" in s.lower() or "Restart" in s for s in result)

    def test_tracker_error(self):
        h = SimpleHealthCheck.__new__(SimpleHealthCheck)
        checks = {"tracker_health": {"status": "error"}}
        result = h._get_suggestions(checks)
        assert len(result) >= 1

    def test_torrent_health_warning(self):
        h = SimpleHealthCheck.__new__(SimpleHealthCheck)
        checks = {"torrent_health": {"status": "warning"}}
        result = h._get_suggestions(checks)
        assert len(result) >= 1


class TestCheckTrackerHealth:
    def test_no_torrents(self):
        h = SimpleHealthCheck.__new__(SimpleHealthCheck)
        with patch("app.services.seeder_service.seeder_service") as mock_ss:
            mock_ss.announcers = {}
            result = h._check_tracker_health()
        assert result["status"] == "healthy"
        assert "No" in result["value"] or "no" in result["message"].lower() or "No" in result["message"]

    def test_all_healthy(self):
        h = SimpleHealthCheck.__new__(SimpleHealthCheck)
        ann = MagicMock()
        ann.last_error = None
        ann.last_error_time = None
        with patch("app.services.seeder_service.seeder_service") as mock_ss:
            mock_ss.announcers = {"a": ann}
            result = h._check_tracker_health()
        assert result["status"] == "healthy"

    def test_high_error_rate(self):
        h = SimpleHealthCheck.__new__(SimpleHealthCheck)
        ann = MagicMock()
        ann.last_error = "Connection timeout"
        ann.last_error_time = datetime.now(timezone.utc)
        with patch("app.services.seeder_service.seeder_service") as mock_ss:
            mock_ss.announcers = {"a": ann}
            result = h._check_tracker_health()
        assert result["status"] in ["error", "warning"]

    def test_old_errors_ignored(self):
        h = SimpleHealthCheck.__new__(SimpleHealthCheck)
        ann = MagicMock()
        ann.last_error = "Old error"
        ann.last_error_time = datetime(2020, 1, 1, tzinfo=timezone.utc)
        with patch("app.services.seeder_service.seeder_service") as mock_ss:
            mock_ss.announcers = {"a": ann}
            result = h._check_tracker_health()
        assert result["status"] == "healthy"


class TestCheckMemory:
    def test_normal_memory(self):
        h = SimpleHealthCheck.__new__(SimpleHealthCheck)
        with patch("app.services.simple_health.psutil", create=True) as mock_ps:
            proc = MagicMock()
            proc.memory_info.return_value = MagicMock(rss=50 * 1024 * 1024)  # 50MB
            mock_ps.Process.return_value = proc
            result = h._check_memory()
        assert result["status"] == "healthy"

    def test_high_memory(self):
        h = SimpleHealthCheck.__new__(SimpleHealthCheck)
        with patch("app.services.simple_health.psutil", create=True) as mock_ps:
            proc = MagicMock()
            proc.memory_info.return_value = MagicMock(rss=300 * 1024 * 1024)  # 300MB
            mock_ps.Process.return_value = proc
            result = h._check_memory()
        assert result["status"] == "warning"

    def test_critical_memory(self):
        h = SimpleHealthCheck.__new__(SimpleHealthCheck)
        with patch("app.services.simple_health.psutil", create=True) as mock_ps:
            proc = MagicMock()
            proc.memory_info.return_value = MagicMock(rss=600 * 1024 * 1024)  # 600MB
            mock_ps.Process.return_value = proc
            result = h._check_memory()
        assert result["status"] == "error"


class TestCheckCpu:
    def test_normal_cpu(self):
        h = SimpleHealthCheck.__new__(SimpleHealthCheck)
        with patch("app.services.simple_health.psutil", create=True) as mock_ps:
            proc = MagicMock()
            proc.cpu_percent.return_value = 10.0
            mock_ps.Process.return_value = proc
            result = h._check_cpu()
        assert result["status"] == "healthy"

    def test_high_cpu(self):
        h = SimpleHealthCheck.__new__(SimpleHealthCheck)
        with patch("app.services.simple_health.psutil", create=True) as mock_ps:
            proc = MagicMock()
            proc.cpu_percent.return_value = 60.0
            mock_ps.Process.return_value = proc
            result = h._check_cpu()
        assert result["status"] == "warning"

    def test_critical_cpu(self):
        h = SimpleHealthCheck.__new__(SimpleHealthCheck)
        with patch("app.services.simple_health.psutil", create=True) as mock_ps:
            proc = MagicMock()
            proc.cpu_percent.return_value = 95.0
            mock_ps.Process.return_value = proc
            result = h._check_cpu()
        assert result["status"] == "error"


class TestGetStatus:
    def test_get_status_all_healthy(self):
        h = SimpleHealthCheck.__new__(SimpleHealthCheck)
        h.start_time = time.time()
        h._cached_status = None
        h._last_check = 0
        with patch.object(h, "_check_memory", return_value={"status": "healthy", "value": "50MB", "message": "OK"}), \
             patch.object(h, "_check_cpu", return_value={"status": "healthy", "value": "5%", "message": "OK"}), \
             patch.object(h, "_check_tracker_health", return_value={"status": "healthy", "value": "3 torrents", "message": "OK"}), \
             patch.object(h, "_check_torrent_health", return_value={"status": "healthy", "value": "3 OK", "message": "OK"}):
            status = h.get_health_status(force_check=True)
        assert status["status"] == "healthy"

    def test_get_status_with_warning(self):
        h = SimpleHealthCheck.__new__(SimpleHealthCheck)
        h.start_time = time.time()
        h._cached_status = None
        h._last_check = 0
        with patch.object(h, "_check_memory", return_value={"status": "warning", "value": "250MB", "message": "High"}), \
             patch.object(h, "_check_cpu", return_value={"status": "healthy", "value": "5%", "message": "OK"}), \
             patch.object(h, "_check_tracker_health", return_value={"status": "healthy", "value": "3", "message": "OK"}), \
             patch.object(h, "_check_torrent_health", return_value={"status": "healthy", "value": "OK", "message": "OK"}):
            status = h.get_health_status(force_check=True)
        assert status["status"] == "warning"

    def test_get_status_with_error(self):
        h = SimpleHealthCheck.__new__(SimpleHealthCheck)
        h.start_time = time.time()
        h._cached_status = None
        h._last_check = 0
        with patch.object(h, "_check_memory", return_value={"status": "error", "value": "600MB", "message": "Critical"}), \
             patch.object(h, "_check_cpu", return_value={"status": "healthy", "value": "5%", "message": "OK"}), \
             patch.object(h, "_check_tracker_health", return_value={"status": "healthy", "value": "3", "message": "OK"}), \
             patch.object(h, "_check_torrent_health", return_value={"status": "healthy", "value": "OK", "message": "OK"}):
            status = h.get_health_status(force_check=True)
        assert status["status"] == "error"
