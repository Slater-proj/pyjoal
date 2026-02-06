"""
Tests for SimpleHealthCheck service
"""
import time
from app.services.simple_health import SimpleHealthCheck


class TestSimpleHealth:
    def test_init(self):
        h = SimpleHealthCheck()
        assert h.start_time > 0

    def test_get_health_status(self):
        h = SimpleHealthCheck()
        status = h.get_health_status()
        assert isinstance(status, dict)
        assert "status" in status
        assert status["status"] in ("healthy", "warning", "error")

    def test_health_status_has_checks(self):
        h = SimpleHealthCheck()
        status = h.get_health_status()
        assert "checks" in status

    def test_uptime_seconds(self):
        h = SimpleHealthCheck()
        status = h.get_health_status()
        assert "uptime_seconds" in status
        assert status["uptime_seconds"] >= 0

    def test_caching(self):
        h = SimpleHealthCheck()
        s1 = h.get_health_status()
        s2 = h.get_health_status()
        # Should return cached (same object)
        assert s1 is s2

    def test_force_check_bypasses_cache(self):
        h = SimpleHealthCheck()
        s1 = h.get_health_status()
        s2 = h.get_health_status(force_check=True)
        # Force creates a new dict
        assert s1 is not s2

    def test_issues_and_suggestions(self):
        h = SimpleHealthCheck()
        status = h.get_health_status()
        assert "issues" in status
        assert "suggestions" in status
        assert isinstance(status["issues"], list)
        assert isinstance(status["suggestions"], list)
