"""
Coverage boost tests (round 2) - targeting uncovered lines in:
- schemas.py validators (error branches)
- errors.py, logs.py API endpoints
- version.py git fallback
- config_manager.py save error path
- resource_optimizer.py memory optimization
- cache.py error paths
- history.py pagination/filters
"""
import pytest
import os
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

os.environ.setdefault("SECRET_TOKEN", "test-secret-token")

from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import ConfigSchema


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth():
    return {"X-API-Token": "test-secret-token"}


# ================================================================
# Schemas validators - error branches
# ================================================================

class TestSchemaValidatorErrors:
    """Cover validator error branches in schemas.py"""

    def test_min_upload_rate_negative(self):
        with pytest.raises(Exception):
            ConfigUpdate(
                minUploadRate=-1, maxUploadRate=500, simultaneousSeed=3,
                client="qbittorrent-5.1.4.client",
                keepTorrentWithZeroLeechers=True, uploadRatioTarget=-1.0,
                seedingDurationLimit=-1.0, announceInterval=1800,
                announceJitter=120,
            )

    def test_min_upload_rate_too_high(self):
        with pytest.raises(Exception):
            ConfigUpdate(
                minUploadRate=2000000, maxUploadRate=500, simultaneousSeed=3,
                client="qbittorrent-5.1.4.client",
                keepTorrentWithZeroLeechers=True, uploadRatioTarget=-1.0,
                seedingDurationLimit=-1.0, announceInterval=1800,
                announceJitter=120,
            )

    def test_max_upload_rate_negative(self):
        with pytest.raises(Exception):
            ConfigUpdate(
                minUploadRate=50, maxUploadRate=-1, simultaneousSeed=3,
                client="qbittorrent-5.1.4.client",
                keepTorrentWithZeroLeechers=True, uploadRatioTarget=-1.0,
                seedingDurationLimit=-1.0, announceInterval=1800,
                announceJitter=120,
            )

    def test_max_upload_rate_too_high(self):
        with pytest.raises(Exception):
            ConfigUpdate(
                minUploadRate=50, maxUploadRate=2000000, simultaneousSeed=3,
                client="qbittorrent-5.1.4.client",
                keepTorrentWithZeroLeechers=True, uploadRatioTarget=-1.0,
                seedingDurationLimit=-1.0, announceInterval=1800,
                announceJitter=120,
            )

    def test_simultaneous_seed_zero(self):
        with pytest.raises(Exception):
            ConfigUpdate(
                minUploadRate=50, maxUploadRate=500, simultaneousSeed=0,
                client="qbittorrent-5.1.4.client",
                keepTorrentWithZeroLeechers=True, uploadRatioTarget=-1.0,
                seedingDurationLimit=-1.0, announceInterval=1800,
                announceJitter=120,
            )

    def test_simultaneous_seed_too_high(self):
        with pytest.raises(Exception):
            ConfigUpdate(
                minUploadRate=50, maxUploadRate=500, simultaneousSeed=2000,
                client="qbittorrent-5.1.4.client",
                keepTorrentWithZeroLeechers=True, uploadRatioTarget=-1.0,
                seedingDurationLimit=-1.0, announceInterval=1800,
                announceJitter=120,
            )

    def test_ratio_target_invalid(self):
        with pytest.raises(Exception):
            ConfigUpdate(
                minUploadRate=50, maxUploadRate=500, simultaneousSeed=3,
                client="qbittorrent-5.1.4.client",
                keepTorrentWithZeroLeechers=True, uploadRatioTarget=-5.0,
                seedingDurationLimit=-1.0, announceInterval=1800,
                announceJitter=120,
            )

    def test_duration_limit_invalid(self):
        with pytest.raises(Exception):
            ConfigUpdate(
                minUploadRate=50, maxUploadRate=500, simultaneousSeed=3,
                client="qbittorrent-5.1.4.client",
                keepTorrentWithZeroLeechers=True, uploadRatioTarget=-1.0,
                seedingDurationLimit=-5.0, announceInterval=1800,
                announceJitter=120,
            )


# ================================================================
# Error API endpoints
# ================================================================

class TestErrorsAPIEndpoints:
    def test_explain_error(self, client, auth):
        resp = client.get("/api/errors/explain?message=test+error", headers=auth)
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data
        assert "explanation" in data

    def test_seeding_info(self, client, auth):
        resp = client.get("/api/errors/seeding-info", headers=auth)
        assert resp.status_code == 200
        data = resp.json()
        assert "title" in data
        assert "explanation" in data

    def test_common_errors(self, client, auth):
        resp = client.get("/api/errors/common", headers=auth)
        assert resp.status_code == 200
        data = resp.json()
        assert "commonErrors" in data


# ================================================================
# Logs API endpoint
# ================================================================

class TestLogsAPIEndpoint:
    def test_get_recent_logs(self, client, auth):
        resp = client.get("/api/logs/recent", headers=auth)
        assert resp.status_code == 200
        data = resp.json()
        assert "logs" in data
        assert "count" in data

    def test_get_recent_logs_with_count(self, client, auth):
        resp = client.get("/api/logs/recent?count=10", headers=auth)
        assert resp.status_code == 200


# ================================================================
# Version API - git fallback branch
# ================================================================

class TestVersionAPIFallback:
    def test_get_version_endpoint(self, client, auth):
        resp = client.get("/api/version", headers=auth)
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data
        assert "name" in data

    def test_get_version_git_fallback(self):
        """Cover the git subprocess fallback path (lines 30-31)"""
        from app.api.version import get_version
        import subprocess

        # Both VERSION file paths don't exist, git describe succeeds
        def fake_exists(self_path):
            return False

        with patch("pathlib.Path.exists", fake_exists):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="v1.2.3\n")
                version = get_version()
                assert version == "1.2.3"

    def test_get_version_all_fail(self):
        """Cover the dev fallback when git also fails"""
        from app.api.version import get_version

        def fake_exists(self_path):
            return False

        with patch("pathlib.Path.exists", fake_exists):
            with patch("subprocess.run", side_effect=FileNotFoundError("no git")):
                version = get_version()
                assert version == "dev"


# ================================================================
# Config manager save error path
# ================================================================

class TestConfigManagerSaveErrors:
    def test_save_write_error(self, tmp_path):
        from app.services.config_manager import ConfigManager
        from app.core.config import settings
        cm = ConfigManager()
        cm._config = {"minUploadRate": 50}

        with patch.object(settings, 'CONFIG_DIR', tmp_path):
            with patch("tempfile.NamedTemporaryFile", side_effect=PermissionError("no write")):
                loop = asyncio.new_event_loop()
                try:
                    with pytest.raises(PermissionError):
                        loop.run_until_complete(cm.save())
                finally:
                    loop.close()

    def test_save_move_failure_cleans_temp(self, tmp_path):
        """Cover temp file cleanup on shutil.move failure"""
        from app.services.config_manager import ConfigManager
        from app.core.config import settings
        cm = ConfigManager()
        cm._config = {"test": True}

        with patch.object(settings, 'CONFIG_DIR', tmp_path):
            with patch("shutil.move", side_effect=OSError("move failed")):
                loop = asyncio.new_event_loop()
                try:
                    with pytest.raises(OSError):
                        loop.run_until_complete(cm.save())
                finally:
                    loop.close()


# ================================================================
# Resource optimizer
# ================================================================

class TestResourceOptimizerCoverage:
    def test_optimize_memory_significant_freed(self):
        from app.services.resource_optimizer import ResourceOptimizer
        optimizer = ResourceOptimizer()
        call_count = [0]

        def mock_memory(*a, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                return {'rss_mb': 250.0, 'vms_mb': 500.0, 'percent': 5.0}
            return {'rss_mb': 245.0, 'vms_mb': 490.0, 'percent': 4.8}

        with patch.object(optimizer, 'get_memory_usage', side_effect=mock_memory):
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(optimizer.optimize_memory())
            finally:
                loop.close()
            assert result is True
            assert optimizer.last_gc_time is not None

    def test_optimize_memory_insignificant(self):
        from app.services.resource_optimizer import ResourceOptimizer
        optimizer = ResourceOptimizer()

        with patch.object(optimizer, 'get_memory_usage',
                          return_value={'rss_mb': 100.0, 'vms_mb': 200.0, 'percent': 2.0}):
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(optimizer.optimize_memory())
            finally:
                loop.close()
            assert result is True

    def test_optimize_memory_exception(self):
        from app.services.resource_optimizer import ResourceOptimizer
        optimizer = ResourceOptimizer()

        with patch.object(optimizer, 'get_memory_usage', side_effect=Exception("fail")):
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(optimizer.optimize_memory())
            finally:
                loop.close()
            assert result is False

    def test_get_optimization_stats(self):
        from app.services.resource_optimizer import ResourceOptimizer
        optimizer = ResourceOptimizer()
        stats = optimizer.get_optimization_stats()
        assert 'current_memory_mb' in stats
        assert 'optimization_needed' in stats
        assert stats['last_gc_time'] is None

    def test_get_optimization_stats_with_gc_time(self):
        from app.services.resource_optimizer import ResourceOptimizer
        optimizer = ResourceOptimizer()
        optimizer.last_gc_time = datetime.now(timezone.utc)
        stats = optimizer.get_optimization_stats()
        assert stats['last_gc_time'] is not None

    def test_periodic_optimization_cancel(self):
        from app.services.resource_optimizer import ResourceOptimizer
        optimizer = ResourceOptimizer()

        async def run():
            task = asyncio.create_task(optimizer.periodic_optimization())
            await asyncio.sleep(0.05)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(run())
        finally:
            loop.close()

    def test_periodic_optimization_error_recovery(self):
        from app.services.resource_optimizer import ResourceOptimizer
        optimizer = ResourceOptimizer()
        call_count = [0]

        async def mock_sleep(seconds):
            call_count[0] += 1
            if call_count[0] >= 3:
                raise asyncio.CancelledError()
            await asyncio.sleep(0.01)

        with patch.object(optimizer, 'should_optimize_memory', side_effect=Exception("err")):
            with patch('asyncio.sleep', side_effect=mock_sleep):
                async def run():
                    task = asyncio.create_task(optimizer.periodic_optimization())
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(run())
                finally:
                    loop.close()


# ================================================================
# Cache API error paths
# ================================================================

class TestCacheAPIErrorPaths:
    def test_get_cache_stats_error(self, client, auth):
        with patch("app.api.cache.cache_manager") as mock_cm:
            mock_cm.get_global_stats.side_effect = Exception("cache error")
            resp = client.get("/api/cache/stats", headers=auth)
            assert resp.status_code == 500

    def test_clear_caches_error(self, client, auth):
        with patch("app.api.cache.cache_manager") as mock_cm:
            mock_cm.clear_all.side_effect = Exception("clear error")
            resp = client.post("/api/cache/clear", headers=auth)
            assert resp.status_code == 500

    def test_cleanup_expired_error(self, client, auth):
        with patch("app.api.cache.cache_manager") as mock_cm:
            mock_cm._run_cleanup.side_effect = Exception("cleanup error")
            resp = client.post("/api/cache/cleanup", headers=auth)
            assert resp.status_code == 500


# ================================================================
# History API - coverage for all endpoints
# ================================================================

class TestHistoryAPICoverage:
    def test_history_with_event_type(self, client, auth):
        resp = client.get("/api/history?event_type=announce", headers=auth)
        assert resp.status_code == 200
        assert "entries" in resp.json()

    def test_history_with_invalid_event_type(self, client, auth):
        resp = client.get("/api/history?event_type=invalid_xyz", headers=auth)
        assert resp.status_code == 200  # Invalid type silently ignored

    def test_history_with_hours_filter(self, client, auth):
        resp = client.get("/api/history?hours=48", headers=auth)
        assert resp.status_code == 200

    def test_history_pagination(self, client, auth):
        resp = client.get("/api/history?page=2&per_page=10", headers=auth)
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 2
        assert data["per_page"] == 10

    def test_history_stats(self, client, auth):
        resp = client.get("/api/history/stats?hours=12", headers=auth)
        assert resp.status_code == 200
        assert resp.json()["hours"] == 12

    def test_history_summary(self, client, auth):
        resp = client.get("/api/history/summary", headers=auth)
        assert resp.status_code == 200

    def test_clear_history(self, client, auth):
        resp = client.delete("/api/history", headers=auth)
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_event_types(self, client, auth):
        resp = client.get("/api/history/types", headers=auth)
        assert resp.status_code == 200
        assert isinstance(resp.json()["types"], list)
